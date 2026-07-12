"""
CategoryAudioHelper — generate category name MP3s via Edge-TTS when operator
saves a category display name. Runs in a background thread; never blocks Qt.

Always overwrites existing files — this prevents corrupt/empty files from
a failed previous generation from persisting silently.
"""

import os
import re
import threading
from pathlib import Path

# Minimum valid MP3 size in bytes. Edge-TTS outputs at least ~4 KB for any
# real word. Files smaller than this were likely truncated or corrupt.
_MIN_VALID_BYTES = 1024


def _slug(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:48]


def generate_category_audio(display_name: str, output_dir: str):
    """Generate (or regenerate) category MP3 for en/fr/ar in a daemon thread."""
    threading.Thread(
        target=_generate_sync,
        args=(display_name, output_dir),
        daemon=True,
    ).start()


def is_valid_mp3(path: str) -> bool:
    """Return True if the file exists and is large enough to be a real MP3."""
    try:
        return os.path.isfile(path) and os.path.getsize(path) >= _MIN_VALID_BYTES
    except OSError:
        return False


def _generate_sync(display_name: str, output_dir: str):
    name = display_name.strip()
    if not name:
        return
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("[CategoryAudio] edge-tts not installed — skipping category audio generation")
        return

    voices = {
        "en": "en-US-AriaNeural",
        "fr": "fr-FR-DeniseNeural",
        "ar": "ar-SA-HamedNeural",
    }
    slug = _slug(name)
    out = Path(output_dir)

    async def _gen(lang: str, voice: str):
        cat_dir = out / lang / "category"
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / f"{slug}.mp3"
        tmp = cat_dir / f"{slug}.mp3.tmp"

        # Write to a temp file first, then rename — avoids leaving a partial
        # file on disk if generation fails halfway.
        communicate = edge_tts.Communicate(name, voice)
        await communicate.save(str(tmp))

        size = tmp.stat().st_size if tmp.exists() else 0
        if size < _MIN_VALID_BYTES:
            print(f"[CategoryAudio] Generated file too small ({size}B), discarding: {tmp}")
            tmp.unlink(missing_ok=True)
            return

        # Atomic replace
        tmp.replace(path)
        print(f"[CategoryAudio] Generated {path} ({size} bytes)")

    async def _run_all():
        for lang, voice in voices.items():
            try:
                await _gen(lang, voice)
            except Exception as exc:
                print(f"[CategoryAudio] {lang} generation error for '{name}': {exc}")

    try:
        asyncio.run(_run_all())
    except Exception as exc:
        print(f"[CategoryAudio] Fatal error: {exc}")
