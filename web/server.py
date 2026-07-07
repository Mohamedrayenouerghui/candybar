"""
web/server.py — thin HTTP server for CandyBarV2 admin web app.

Routes:
  GET  /              → public.html  (read-only customer page)
  GET  /admin         → admin.html   (PIN-protected staff page)
  POST /api/pin       → {"pin":"XXXX"} → {"ok": true/false}
  POST /api/publish   → {"topic":"display/…","payload":"…"} → {"ok": true}
  POST /api/logo      → multipart file upload → {"ok": true, "path": "…"}
  POST /api/background → multipart file upload → {"ok": true}
  POST /api/font      → multipart file upload → {"ok": true, "family": "…"}
  GET  /api/state     → current display state JSON
  GET  /api/stats     → device health/usage JSON
  GET  /api/fonts     → list registered fonts
  GET  /uploads/<f>   → serve uploaded files

No heavy frameworks — pure stdlib http.server with a custom handler.
"""

import http.server
import json
import mimetypes
import os
import re
import socket

from PySide6.QtCore import QFile, QStandardPaths

MAX_LOGO_BYTES = 2 * 1024 * 1024   # 2 MB
MAX_BG_BYTES   = 5 * 1024 * 1024   # 5 MB
MAX_FONT_BYTES = 2 * 1024 * 1024   # 2 MB

PORT      = 8080
SERVE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = ""  # set in run() before server starts

# These are injected by run() so Handler methods can reference them
_mqtt_client        = None
_display_persistence = None
_usage_stats        = None
_font_manager       = None


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _parse_multipart(content_type: str, content_length: int, rfile):
    """
    Manual multipart/form-data parser (replaces deprecated cgi.FieldStorage).
    Returns dict with 'fields' and 'files' keys.
    """
    boundary_match = re.search(r'boundary=([^;]+)', content_type)
    if not boundary_match:
        return None
    boundary = boundary_match.group(1).strip().strip('"')
    boundary_bytes = ('--' + boundary).encode('utf-8')

    data = rfile.read(content_length)
    parts = data.split(boundary_bytes)

    result = {'fields': {}, 'files': {}}
    for part in parts[1:-1]:
        if not part or part == b'--\r\n':
            continue
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1:
            continue
        headers = part[:header_end].decode('utf-8', errors='ignore')
        body = part[header_end + 4:]
        disp_match = re.search(
            r'Content-Disposition: form-data; name="([^"]+)"(?:; filename="([^"]+)")?',
            headers
        )
        if not disp_match:
            continue
        name = disp_match.group(1)
        filename = disp_match.group(2)
        if filename:
            result['files'][name] = {'filename': filename, 'data': body.rstrip(b'\r\n')}
        else:
            result['fields'][name] = body.decode('utf-8', errors='ignore').rstrip('\r\n')
    return result


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[admin-web] {self.address_string()} {fmt % args}")

    # ── routing ───────────────────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            self._serve_file("public.html")
        elif path == "/admin":
            self._serve_file("admin.html")
        elif path.startswith("/uploads/"):
            self._serve_static(os.path.join(UPLOAD_DIR, path[len("/uploads/"):]))
        elif path == "/favicon.ico":
            self._serve_qrc(":/app/res/image/favicon.ico", "image/x-icon")
        elif path.startswith("/api/bg_thumb/"):
            bg_id = path[len("/api/bg_thumb/"):]
            if bg_id and all(c.isalnum() or c == '_' for c in bg_id):
                self._serve_qrc(f":/app/res/image/{bg_id}.jpg", "image/jpeg")
            else:
                self._send(404, "text/plain", b"Not found")
        elif path == "/api/state":
            self._json_response(self._build_state())
        elif path == "/api/stats":
            self._json_response(_usage_stats.as_dict())
        elif path == "/api/fonts":
            self._handle_get_fonts()
        else:
            self._serve_file(path.lstrip("/"))

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/pin":
            self._handle_pin()
        elif path == "/api/publish":
            self._handle_publish()
        elif path == "/api/logo":
            self._handle_upload("logo", MAX_LOGO_BYTES, (".png", ".jpg", ".jpeg", ".svg"))
        elif path == "/api/background":
            self._handle_upload("background", MAX_BG_BYTES, (".png", ".jpg", ".jpeg"))
        elif path == "/api/font":
            self._handle_font()
        else:
            self._send(404, "text/plain", b"Not found")

    # ── POST handlers ─────────────────────────────────────────────────────

    def _handle_pin(self):
        body = self._read_json()
        if body is None:
            return
        entered = str(body.get("pin", "")).strip()
        correct = str(_display_persistence.get_pin()).strip()
        ok = entered == correct
        print(f"[pin] entered={entered!r} correct={correct!r} ok={ok}")
        self._json_response({"ok": ok})

    def _handle_publish(self):
        body = self._read_json()
        if body is None:
            return
        topic   = str(body.get("topic", ""))
        payload = str(body.get("payload", ""))
        if not topic.startswith("display/"):
            self._json_response({"ok": False, "error": "bad topic"})
            return

        key      = topic[len("display/"):]
        category = _display_persistence.load("category", "A")

        # Persist — two keys need type coercion, everything else is a direct save
        if key == "adminPin":
            _display_persistence.set_pin(payload)
        elif key == "fontSize":
            _display_persistence.save("fontSize", int(payload))
        elif key in ("numberFontSize", "categoryFontSize", "facilityFontSize", "bannerFontSize", "nowServingFontSize"):
            _display_persistence.save(key, int(payload))
        elif key == "logoSize":
            _display_persistence.save("logoSize", int(payload))
        elif key == "audioVolumeStep":
            _display_persistence.save("audioVolumeStep", int(payload))
        else:
            _display_persistence.save(key, payload)

        # Push to QML display (works without a broker)
        _mqtt_client.direct_command(key, payload)
        # Also publish via MQTT if connected
        _mqtt_client.publish(f"display/{category}/{key}", payload)

        if key == "currentNumber":
            _usage_stats.record_number_change()

        self._json_response({"ok": True})

    def _handle_upload(self, field: str, max_bytes: int, allowed_exts: tuple):
        """Generic file upload handler for logo and background."""
        ctype          = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > max_bytes:
            self._json_response({"ok": False, "error": f"file too large (max {max_bytes // (1024*1024)} MB)"})
            return
        try:
            parsed = _parse_multipart(ctype, content_length, self.rfile)
            if not parsed or field not in parsed['files']:
                self._json_response({"ok": False, "error": "no file"})
                return
            file_item = parsed['files'][field]
            data      = file_item['data']
            ext       = os.path.splitext(file_item['filename'])[1].lower()
            if len(data) > max_bytes:
                self._json_response({"ok": False, "error": "file too large"})
                return
            if ext not in allowed_exts:
                self._json_response({"ok": False, "error": f"unsupported format (allowed: {', '.join(allowed_exts)})"})
                return
            dest_path = os.path.join(UPLOAD_DIR, f"{field}{ext}")
            with open(dest_path, "wb") as f:
                f.write(data)
            category = _display_persistence.load("category", "A")
            if field == "logo":
                _display_persistence.save("logoPath", dest_path)
                _mqtt_client.direct_command("logoSource", dest_path)
                _mqtt_client.publish(f"display/{category}/logoSource", dest_path)
            else:
                _display_persistence.save("backgroundImage", dest_path)
                _mqtt_client.direct_command("backgroundImage", dest_path)
                _mqtt_client.publish(f"display/{category}/backgroundImage", dest_path)
            self._json_response({"ok": True, "url": f"/uploads/{field}{ext}", "path": dest_path})
        except Exception as exc:
            self._json_response({"ok": False, "error": str(exc)})

    def _handle_font(self):
        ctype          = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_FONT_BYTES:
            self._json_response({"ok": False, "error": "file too large (max 2 MB)"})
            return
        try:
            parsed = _parse_multipart(ctype, content_length, self.rfile)
            if not parsed or 'font' not in parsed['files']:
                self._json_response({"ok": False, "error": "no file"})
                return
            file_item = parsed['files']['font']
            data      = file_item['data']
            ext       = os.path.splitext(file_item['filename'])[1].lower()
            if len(data) > MAX_FONT_BYTES:
                self._json_response({"ok": False, "error": "file too large"})
                return
            if ext not in (".ttf", ".otf"):
                self._json_response({"ok": False, "error": "unsupported format (only TTF/OTF)"})
                return
            temp_path = os.path.join(UPLOAD_DIR, f"temp_font_upload{ext}")
            with open(temp_path, "wb") as f:
                f.write(data)
            family = _font_manager.registerFont(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if not family:
                self._json_response({"ok": False, "error": "invalid font file or registration failed"})
                return
            self._json_response({"ok": True, "family": family})
        except Exception as exc:
            self._json_response({"ok": False, "error": str(exc)})

    def _handle_get_fonts(self):
        try:
            fonts = [
                {"family": f["family"], "url": f"/uploads/fonts/{f['filename']}", "filename": f["filename"]}
                for f in _font_manager.listFonts()
            ]
            self._json_response({"ok": True, "fonts": fonts})
        except Exception as exc:
            self._json_response({"ok": False, "error": str(exc)})

    # ── state builder ─────────────────────────────────────────────────────

    def _build_state(self) -> dict:
        p = _display_persistence
        logo_path = p.logo_path()
        logo_url  = f"/uploads/{os.path.basename(logo_path)}" if logo_path and os.path.exists(logo_path) else ""

        bg_path = p.background_path()
        if not bg_path:
            bg_url = "qrc:/app/res/image/ff_burger_pattern.jpg"
        elif bg_path.startswith("qrc:"):
            bg_url = bg_path
        elif os.path.exists(bg_path):
            bg_url = f"/uploads/{os.path.basename(bg_path)}"
        else:
            bg_url = bg_path

        return {
            "currentNumber":          p.get_current_number(),
            "nextUp":                 p.get_next_up(),
            "layoutType":             p.get_layout(),
            "accentColor":            p.load("accentColor", "#FFB84D"),
            "accentGradientEnabled":  p.load("accentGradientEnabled", "false"),
            "accentGradientDirection":p.load("accentGradientDirection", "top-to-bottom"),
            "bannerText":             p.get_banner(),
            "bannerEnabled":          p.load("bannerEnabled", "true"),
            "facilityName":           p.get_facility(),
            "fontSize":               p.get_font_size(),
            "numberFontSize":         p.get_text_size("numberFontSize", p.get_font_size()),
            "categoryFontSize":       p.get_text_size("categoryFontSize", 34),
            "facilityFontSize":       p.get_text_size("facilityFontSize", 24),
            "bannerFontSize":         p.get_text_size("bannerFontSize", 24),
            "nowServingFontSize":     p.get_text_size("nowServingFontSize", 16),
            "logoSize":               p.get_logo_size(),
            "numberFont":             p.load("numberFont", "DM Mono"),
            "categoryFont":           p.load("categoryFont", p.load("numberFont", "DM Mono")),
            "facilityFont":           p.load("facilityFont", p.load("numberFont", "DM Mono")),
            "bannerFont":             p.load("bannerFont", p.load("numberFont", "DM Mono")),
            "nowServingFont":         p.load("nowServingFont", p.load("numberFont", "DM Mono")),
            "logoUrl":                logo_url,
            "logoVisible":            p.load("logoVisible", "true"),
            "logoPosition":           p.load("logoPosition", "top-left"),
            "backgroundImage":        bg_url,
            "backgroundOrientation":  p.load("backgroundOrientation", "portrait"),
            "category":               p.load("category", "A"),
            "categoryDisplayName":    p.load("categoryDisplayName", "Category A"),
            "ttsLanguage":            p.load("ttsLanguage", "en"),
            "ttsEnabled":             p.load("ttsEnabled", "true"),
            "audioMuted":             p.load("audioMuted", "false"),
            "audioVolumeStep":        p.load("audioVolumeStep", "3"),
        }

    # ── low-level helpers ─────────────────────────────────────────────────

    def _serve_qrc(self, qrc_path: str, mime: str):
        qf = QFile(qrc_path)
        if qf.open(QFile.OpenModeFlag.ReadOnly):
            data = qf.readAll().data()
            qf.close()
            self._send(200, mime, data)
        else:
            self._send(404, "text/plain", b"Not found")

    def _serve_file(self, name: str):
        self._serve_static(os.path.join(SERVE_DIR, name))

    def _serve_static(self, fpath: str):
        if not os.path.isfile(fpath):
            self._send(404, "text/plain", b"Not found")
            return
        mime, _ = mimetypes.guess_type(fpath)
        with open(fpath, "rb") as f:
            self._send(200, mime or "application/octet-stream", f.read())

    def _json_response(self, obj: dict):
        self._send(200, "application/json", json.dumps(obj).encode())

    def _send(self, code: int, mime: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length))
        except Exception:
            self._send(400, "text/plain", b"Bad JSON")
            return None


def run(mqtt_client, display_persistence, usage_stats, font_manager):
    """Start the HTTP server. Runs forever — call from a daemon thread."""
    global UPLOAD_DIR, _mqtt_client, _display_persistence, _usage_stats, _font_manager

    _mqtt_client         = mqtt_client
    _display_persistence = display_persistence
    _usage_stats         = usage_stats
    _font_manager        = font_manager

    UPLOAD_DIR = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Seed static assets the admin UI references via /uploads/
    for qrc_path, fname in [(":/app/res/image/noise_texture.png", "noise_texture.png")]:
        dest = os.path.join(UPLOAD_DIR, fname)
        if not os.path.exists(dest):
            qf = QFile(qrc_path)
            if qf.open(QFile.OpenModeFlag.ReadOnly):
                with open(dest, "wb") as f:
                    f.write(qf.readAll().data())
                qf.close()

    local_ip = _get_local_ip()
    print(f"[admin-web] http://0.0.0.0:{PORT}  (LAN: http://{local_ip}:{PORT})")

    http.server.HTTPServer.allow_reuse_address = True
    with http.server.HTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        httpd.serve_forever()
