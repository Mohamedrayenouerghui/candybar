# CandyBarV2 — AI Codebase Reference

This document is written for an AI assistant. It answers three questions for every possible change:
**what the system does**, **where state lives**, and **exactly which files to touch** for any given feature area.

Read this before touching any file. Do not guess at file locations.

---

## 1. What Is This Project

CandyBarV2 is a **self-contained kiosk queue-number display system**.

- A screen (TV/monitor) runs the Qt/QML app fullscreen and shows the currently-called number.
- Staff manage the display from any phone on the local network via a web admin panel at `http://<LAN-IP>:8080/admin`.
- Numbers are announced via pre-generated TTS audio atoms.
- All state survives power loss.

**Tech stack**

| Layer | Technology |
|---|---|
| Display UI | PySide6 + QML (Qt 6) + vendored FluentUI |
| Rendering | OpenGL (QSGRendererInterface) |
| Messaging | paho-mqtt (MQTT broker, optional) |
| HTTP admin | Python stdlib `http.server` — no framework |
| Audio | pygame.mixer (playback) + edge-tts (pre-generation script) |
| Persistence | QSettings INI file |
| Entry point | `./go` → `python -m app.main` |

---

## 2. Project Structure

```
CandyBarv2-main/
│
├── run.py                          # Thin wrapper — calls app.main.main()
├── go                              # One-shot launcher: venv → deps → resources → launch
├── requirements.txt
│
├── app/
│   ├── main.py                     # ★ Qt init, context property registration, startup
│   ├── mqtt_client.py              # ★ paho-mqtt ↔ Qt signal bridge
│   ├── __init__.py                 # Package marker (__version__, __author__)
│   │
│   ├── helper/
│   │   ├── AudioEngine.py          # ★ pygame TTS playback, number announcements
│   │   ├── CategoryAudioHelper.py  # Background edge-tts generation for category names
│   │   ├── DisplayPersistence.py   # ★ QSettings INI read/write, persistence helpers
│   │   ├── FontManager.py          # Runtime custom font registration
│   │   ├── NetworkHelper.py        # LAN IP discovery, URL exposure to QML
│   │   └── UsageStats.py           # Uptime / session / number-change counters
│   │
│   └── imports/
│       ├── resource.qrc            # Qt resource manifest — lists every bundled file
│       ├── resource_rc.py          # Auto-generated from resource.qrc (run scripts/update_resources.py)
│       ├── __init__.py
│       └── app/
│           ├── qml/
│           │   ├── global/
│           │   │   ├── DisplayState.qml  # ★★ THE single source of truth for all display state
│           │   │   └── qmldir            # Registers DisplayState as a QML singleton
│           │   ├── App.qml               # ★ Root Window: fullscreen kiosk, MQTT→DisplayState wiring
│           │   ├── MainDisplay.qml       # Boot splash → DisplayView stack orchestration
│           │   ├── DisplayView.qml       # ★★ All three layouts (Classic/Split/Centered), animations
│           │   ├── WelcomeSplash.qml     # Boot branding screen
│           │   ├── ConnectionBanner.qml  # MQTT reconnecting pill
│           │   └── CustomerSiteQrOverlay.qml  # Bottom-right QR code
│           └── res/
│               ├── font/           # DM Mono Regular + Medium (bundled)
│               └── image/          # Background images, favicon, genical logo, noise texture
│
├── web/
│   ├── server.py                   # ★ HTTP server: routing, API handlers, state builder
│   ├── admin.html                  # ★★ Staff SPA: Remote / Settings / Theme tabs
│   ├── public.html                 # Read-only customer number display page
│   └── mqtt.min.js                 # MQTT.js for in-browser live updates (public.html)
│
├── scripts/
│   ├── generate_audio.py           # Offline TTS pre-generation (needs internet, run once)
│   ├── sync_sounds.py              # Copies sound/ folder → audio data dir
│   └── update_resources.py         # Rebuilds resource_rc.py from resource.qrc
│
├── sound/                          # Source audio samples (copied by sync_sounds.py)
├── background/                     # Raw background image assets (source, not bundled)
└── fluentui/                       # Vendored FluentUI Qt/QML component library — DO NOT TOUCH
```

---

## 3. The Data Flow (most important thing to understand)

Every display change follows this exact path:

```
Staff taps "042" in admin.html
  → POST /api/publish  {topic:"display/currentNumber", payload:"042"}
    → server.py Handler._handle_publish()
      → _display_persistence.save("currentNumber", "042")   ← persisted immediately
      → _mqtt_client.direct_command("currentNumber", "042") ← pushed to queue
        → MQTTClient._cmd_queue.put(("currentNumber","042"))
          → drain timer (50ms, Qt main thread) pops it
            → displayCommandReceived signal fires
              → App.qml Connections → DisplayState.applyMqttCommand("currentNumber","042")
                → DisplayState.currentNumber = "042"           ← QML binding updates UI
                → DisplayPersistence.save("currentNumber","042")
                → AudioEngine.announceNumber("042")            ← TTS fires
```

**The rule:** `DisplayState.applyMqttCommand(key, value)` is the **only** write path into the display UI. Every new property must have a case there.

---

## 4. DisplayState.qml — The Central Registry

**File:** `app/imports/app/qml/global/DisplayState.qml`

This is a `pragma Singleton` — imported everywhere as `DisplayState`. It holds every display property. There is no other state.

**All current properties:**

| Property | Type | Default | Purpose |
|---|---|---|---|
| `currentNumber` | string | "001" | Currently displayed queue number |
| `nextUp` | var (array) | [] | Queue of upcoming numbers (Split layout) |
| `audioMuted` | bool | false | Mute all announcements |
| `audioVolumeStep` | int | 3 | Volume index 0–4 |
| `ttsLanguage` | string | "en" | Voice language for TTS (en/fr/ar) |
| `ttsEnabled` | bool | true | Enable/disable voice announcements |
| `displayLanguage` | string | "en" | On-screen text language (en/fr/ar) |
| `category` | string | "A" | MQTT category slug |
| `categoryDisplayName` | string | "Category A" | Human name shown on display |
| `logoSource` | string | qrc:// | Logo image URL |
| `facilityName` | string | "CandyBar…" | Shown in header |
| `bannerText` | string | "Welcome…" | Scrolling footer message |
| `backgroundImage` | string | qrc:// | Background image URL |
| `backgroundFitMode` | string | "crop" | crop / fit / stretch / auto |
| `backgroundScale` | real | 1.0 | Zoom multiplier |
| `backgroundOffsetX` | int | 0 | Horizontal pan in px |
| `backgroundOffsetY` | int | 0 | Vertical pan in px |
| `backgroundOrientation` | string | "portrait" | Source image orientation hint |
| `logoPosition` | string | "top-left" | top-left / top-center / hidden |
| `bannerEnabled` | bool | true | Show/hide footer banner |
| `logoVisible` | bool | true | Show/hide logo |
| `bgColor` | color | "#0b0d10" | Fallback background color |
| `accentColor` | color | "#FFB84D" | Accent (gold) color |
| `accentGradientEnabled` | bool | false | Gradient on accent underline bar |
| `accentGradientDirection` | string | "top-to-bottom" | Gradient direction |
| `layoutType` | string | "Classic" | Classic / Split / Centered |
| `numberFont` | string | "DM Mono" | Number text font family |
| `categoryFont` | string | "DM Mono" | Category badge font |
| `facilityFont` | string | "DM Mono" | Facility name font |
| `bannerFont` | string | "DM Mono" | Banner ticker font |
| `nowServingFont` | string | "DM Mono" | "NOW SERVING" label font |
| `uiFont` | string | system | System UI font (read-only) |
| `fontSize` | int | 96 | Global number size (48–200px) |
| `numberFontSize` | int | 96 | Number override size |
| `categoryFontSize` | int | 34 | Category override size |
| `facilityFontSize` | int | 24 | Facility name override size |
| `bannerFontSize` | int | 24 | Banner text override size |
| `nowServingFontSize` | int | 16 | "NOW SERVING" override size |
| `logoSize` | int | 48 | Logo container height px (24–120) |
| `publicUrl` | string | localhost | Public page URL (set at startup) |
| `adminUrl` | string | localhost | Admin page URL (set at startup) |
| `siteUrl` | string | candybarv2.app | Official site URL |
| `mqttConnected` | bool | false | MQTT connection status |
| `mqttStatus` | string | "Connecting…" | Human-readable MQTT status |
| `isRtl` | bool (readonly) | false | True when displayLanguage is "ar" |

**Key functions:**

- `loadFromDisk()` — called once at startup from `App.qml`. Reads all values from `DisplayPersistence`.
- `applyMqttCommand(key, value)` — the sole write path. Called from `App.qml` on every incoming command.
- `tr(key)` — returns the translated string for the current `displayLanguage`. Keys: `now_serving`, `next_up`, `visit_website`, `proceed`.
- `_syncAudioEngine()` — pushes audio-related state to `AudioEngine` Python object.

---

## 5. File-by-File: What to Touch for Each Change

### A. Change what appears on screen (text, number, layout)
→ **`DisplayState.qml`** — add/change the property  
→ **`DisplayView.qml`** — bind the property to a QML element  
→ **`web/server.py`** `_build_state()` — add to the state JSON returned to admin  
→ **`web/admin.html`** — add the control that sends `pub('keyName', value)`  
→ **`app/helper/DisplayPersistence.py`** — add a helper if the server needs typed access  

### B. Add a new display property (e.g. a new color or toggle)
1. `DisplayState.qml` → add `property <type> myProp: <default>`
2. `DisplayState.qml` → `loadFromDisk()` → add `myProp = p.load("myProp", "<default>")`
3. `DisplayState.qml` → `applyMqttCommand()` → add `} else if (key === "myProp") { myProp = value; p.save("myProp", value) }`
4. `DisplayView.qml` → use `DisplayState.myProp` in the relevant QML item
5. `web/server.py` → `_build_state()` → add `"myProp": p.load("myProp", "<default>"),`
6. `web/server.py` → `_handle_publish()` → add int coercion if needed
7. `web/admin.html` → add control that calls `pub('myProp', value)`

### C. Change audio / TTS behaviour
→ **`app/helper/AudioEngine.py`** — playback engine (pygame)  
→ **`app/helper/CategoryAudioHelper.py`** — edge-tts generation for category names  
→ **`scripts/generate_audio.py`** — offline batch TTS generation  
→ `DisplayState.qml` `_syncAudioEngine()` — pushes state to `AudioEngine`  
→ Audio files live in `~/.local/share/CandyBarV2/CandyBarV2/audio/`

### D. Change the admin web UI
→ **`web/admin.html`** — single-file SPA (HTML + CSS + JS all in one file)  
→ **`web/server.py`** — add/change API routes if new data needs to flow  
→ Admin translations: `ADMIN_I18N` dict inside `admin.html` `<script>` block  
→ `data-i18n` attributes on HTML elements trigger `setAdminLang()` to translate them  

### E. Change on-screen text language (NOW SERVING / NEXT UP / etc.)
→ **`DisplayState.qml`** — `_tr` object (translations dict), `tr(key)` function  
→ **`DisplayView.qml`** — all on-screen labels already use `DisplayState.tr('key')`  
→ **`CustomerSiteQrOverlay.qml`** — "Visit our website" already uses `DisplayState.tr('visit_website')`  
→ **`web/admin.html`** — "Display language" card in Settings tab sends `pub('displayLanguage', 'xx')`  

### F. Add a new language to the display
1. `DisplayState.qml` → `_tr` object → add `"xx": { now_serving: "...", next_up: "...", visit_website: "...", proceed: "..." }`
2. `DisplayState.qml` → `applyMqttCommand("displayLanguage")` → add `"xx"` to the allowed-values check
3. `DisplayState.qml` → `loadFromDisk()` → `get_display_language()` already handles new values if added to server
4. `web/admin.html` → Display Language card → add a `<button>` for the new language
5. `web/admin.html` → `ADMIN_I18N` dict → add the new language key with all UI strings translated
6. `app/helper/AudioEngine.py` → `language.setter` → add `"xx"` to the allowed tuple
7. `scripts/generate_audio.py` → `VOICES` and `PHRASES` dicts → add the new language

### G. Change the MQTT topic structure
→ **`app/mqtt_client.py`** — `_on_connect` subscription, `_on_message` parsing  
→ **`web/server.py`** `_handle_publish()` — `mqtt_topic` construction  
→ **`app/imports/app/qml/App.qml`** — `onDisplayCommandReceived` connection  

### H. Change the HTTP API (add a new endpoint)
→ **`web/server.py`** — `do_GET()` or `do_POST()` routing + new handler method  
→ **`web/admin.html`** — JS `fetch()` call  

### I. Change persistence / what survives power loss
→ **`app/helper/DisplayPersistence.py`** — `save()` / `load()` wrappers + typed helpers  
→ `DisplayState.qml` `loadFromDisk()` — reads on startup  
→ `DisplayState.qml` `applyMqttCommand()` — saves on every change  
→ INI file location: `~/.local/share/CandyBarV2/CandyBarV2/candybar_display.ini`

### J. Change the boot splash / welcome screen
→ **`app/imports/app/qml/WelcomeSplash.qml`**  
→ Duration controlled by `splashDuration` property (default 2600ms)

### K. Change what QML files / assets are bundled into the app
→ **`app/imports/resource.qrc`** — add/remove `<file>` entries  
→ Then run `python scripts/update_resources.py` to regenerate `resource_rc.py`  
→ Import `resource_rc` in `app/main.py` is already there — no change needed

### L. Add a new Python context property (expose a Python object to QML)
→ **`app/main.py`** — instantiate and `ctx.setContextProperty("Name", obj)`  
→ The name used in `setContextProperty` is how QML references it (e.g. `AudioEngine.announceNumber(...)`)

---

## 6. The Thread Safety Contract

The HTTP server (`web/server.py`) runs on a **daemon thread**. QML/Qt objects are **not thread-safe**. The bridge:

- `_mqtt_client.direct_command(key, value)` — puts `(key, value)` onto a `queue.Queue`
- `MQTTClient._drain_timer` — a `QTimer` on the Qt main thread polls every 50ms and emits `displayCommandReceived`
- **Never** call any Qt/QML object directly from the HTTP handler thread

---

## 7. Audio System

Audio atoms live at: `~/.local/share/CandyBarV2/CandyBarV2/audio/`

```
audio/
  en/
    numbers/   0.mp3 … 19.mp3, 20.mp3, 30.mp3 … 90.mp3, 100.mp3
    phrases/   now_serving.mp3
    category/  <slug>.mp3  (generated on first use of a category name)
  fr/           (same structure)
  ar/
    numbers/   0.mp3 … 99.mp3  (no composition — all individual)
    phrases/   now_serving.mp3
    category/  <slug>.mp3
```

**Generation:** `python scripts/generate_audio.py --output-dir <path>` (needs internet, edge-tts)  
**Playback:** `AudioEngine._build_audio_sequence()` → `AudioEngine._play_announcement()` (background thread, pygame)

---

## 8. Key Constraints — Things To Never Do

| Don't | Why |
|---|---|
| Touch `fluentui/` | Vendored library — changes will be overwritten |
| Change MQTT topic names (`display/<cat>/<key>`) | External clients depend on them |
| Change HTTP API routes | External integrations depend on them |
| Call Qt/QML objects from the HTTP handler thread | Thread safety — use `direct_command()` |
| Add `numberSizePreset` or `NUMBER_SIZE_MAP` back | Removed — replaced by continuous `fontSize` slider |
| Add `SettingsHelper` back | Removed — QML never called it |
| Rename QML types registered via `qmlRegisterType` | Breaks the QML engine type lookup |
| Edit `resource_rc.py` by hand | Auto-generated — run `scripts/update_resources.py` |

---

## 9. Quick Reference: Every MQTT Key

These are all valid keys in `applyMqttCommand()` and `_handle_publish()`. Sending `pub('keyName', 'value')` from admin.html is the standard way to change any of them.

```
currentNumber         nextUp               layoutType
accentColor           accentGradientEnabled  accentGradientDirection
bannerText            facilityName         fontSize
numberFontSize        categoryFontSize     facilityFontSize
bannerFontSize        nowServingFontSize   logoSize
numberFont            categoryFont         facilityFont
bannerFont            nowServingFont       logoSource
backgroundImage       backgroundFitMode    backgroundScale
backgroundOffsetX     backgroundOffsetY    backgroundOrientation
adminPin              category             categoryDisplayName
logoPosition          bannerEnabled        logoVisible
ttsLanguage           displayLanguage      ttsEnabled
audioMuted            audioVolumeStep
```

---

## 10. How to Run

```bash
# First run (creates venv, installs deps, compiles resources, generates audio)
./go

# Subsequent runs
./go

# The display opens fullscreen. Admin panel: http://<LAN-IP>:8080/admin
# Default PIN: 1234

# Generate audio atoms manually (needs internet)
./venv/bin/python scripts/generate_audio.py --output-dir ~/.local/share/CandyBarV2/CandyBarV2/audio

# Rebuild QRC bundle after adding/removing assets
./venv/bin/python scripts/update_resources.py
```

---

## 11. DisplayPersistence API Reference

**File:** `app/helper/DisplayPersistence.py`

All methods are `@Slot` decorated and callable from both Python and QML.

| Method | Returns | Purpose |
|---|---|---|
| `save(key, value)` | None | Write any key to INI, sync immediately |
| `load(key, default)` | QVariant | Read any key from INI |
| `save_logo(src_path)` | str | Copy logo file to data dir, persist path |
| `logo_path()` | str | Return stored logo absolute path |
| `background_path()` | str | Return stored background path |
| `get_pin()` | str | Return admin PIN (default "1234") |
| `set_pin(pin)` | None | Save admin PIN |
| `get_current_number()` | str | Return current queue number |
| `get_next_up()` | list | Return next-up array |
| `get_layout()` | str | Return layout type |
| `get_banner()` | str | Return banner text |
| `get_facility()` | str | Return facility name |
| `get_font_size()` | int | Return fontSize (48–200, default 96) |
| `get_logo_size()` | int | Return logoSize (24–120, default 48) |
| `get_text_size(key, default)` | int | Return any text size key (8–240) |
| `get_display_language()` | str | Return displayLanguage (en/fr/ar) |
