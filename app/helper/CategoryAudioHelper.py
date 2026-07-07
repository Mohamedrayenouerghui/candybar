"""
CategoryAudioHelper — generate category name MP3s via Edge-TTS when operator
saves a category display name. Runs in a background thread; never blocks Qt.
"""

import os
import re
import threading
from pathlib import Path


def _slug(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower())[:48]


def generate_category_audio(display_name: str, output_dir: str):
    """Generate category MP3 for en/fr/ar in a daemon thread."""
    threading.Thread(
        target=_generate_sync,
        args=(display_name, output_dir),
        daemon=True,
    ).start()


def _generate_sync(display_name: str, output_dir: str):
    if not display_name.strip():
        return
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("[CategoryAudio] edge-tts not installed — skip category audio")
        return

    voices = {
        "en": "en-US-AriaNeural",
        "fr": "fr-FR-DeniseNeural",
        "ar": "ar-SA-HamedNeural",
    }
    slug = _slug(display_name)
    out = Path(output_dir)

    async def _gen(lang: str, voice: str):
        cat_dir = out / lang / "category"
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / f"{slug}.mp3"
        communicate = edge_tts.Communicate(display_name, voice)
        await communicate.save(str(path))
        print(f"[CategoryAudio] Generated {path}")

    async def _run_all():
        for lang, voice in voices.items():
            await _gen(lang, voice)

    try:
        asyncio.run(_run_all())
    except Exception as exc:
        print(f"[CategoryAudio] Error: {exc}")
