"""
AudioEngine.py — TTS audio playback engine for CandyBarV2.

Hybrid pre-generation + runtime playback. No live TTS at runtime.
Uses pygame.mixer.music for sequential atom playback (MP3 supported).

Announcement format (when category audio is enabled):
  "<category name> ... <number>"
  e.g. "Chicken ... twelve"

When category audio is disabled:
  "<number>" only (no prefix)

The "now serving" phrase is intentionally omitted — the category name
already provides full context. Keeping the announcement short reduces
noise in a busy service environment.
"""

import os
import re
import threading
import time

try:
    import pygame
    import pygame.mixer
except ImportError:
    pygame = None

from PySide6.QtCore import QObject, Slot, Property


class AudioEngine(QObject):

    VOLUME_STEPS = [0.0, 0.35, 0.55, 0.75, 1.0]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initialized = False
        self._muted = False
        self._volume_step = 3  # index into VOLUME_STEPS (default ~0.75)
        self._language = "en"
        self._data_dir = ""
        self._playing = False
        self._stop_flag = False
        self._category_display_name = "Counter A"
        self._tts_enabled = True
        self._category_audio_enabled = True   # announce category name before number
        self._lock = threading.Lock()
        self._init_mixer()

    def _init_mixer(self):
        if pygame is None:
            print("[AudioEngine] pygame not installed — audio disabled")
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
            print("[AudioEngine] mixer initialized OK")
        except Exception as e:
            print(f"[AudioEngine] Failed to initialize audio: {e}")

    # ── Properties ────────────────────────────────────────────────────────

    @Property(bool)
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, value):
        self._muted = bool(value)
        if self._muted and self._initialized:
            pygame.mixer.music.set_volume(0.0)

    @Property(int)
    def volumeStep(self):
        return self._volume_step

    @volumeStep.setter
    def volumeStep(self, value):
        self._volume_step = max(0, min(len(self.VOLUME_STEPS) - 1, int(value)))

    @Property(float)
    def volume(self):
        return self.VOLUME_STEPS[self._volume_step]

    @Property(str)
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        if value in ("en", "fr", "ar"):
            self._language = value

    @Property(bool)
    def ttsEnabled(self):
        return self._tts_enabled

    @ttsEnabled.setter
    def ttsEnabled(self, value):
        self._tts_enabled = bool(value)

    @Property(bool)
    def categoryAudioEnabled(self):
        return self._category_audio_enabled

    @categoryAudioEnabled.setter
    def categoryAudioEnabled(self, value):
        self._category_audio_enabled = bool(value)

    def set_data_dir(self, data_dir: str):
        self._data_dir = data_dir
        print(f"[AudioEngine] data_dir set to: {data_dir}")

    # ── Category name & audio pre-generation ─────────────────────────────

    @Slot(str)
    def set_category_display_name(self, name: str):
        clean = (name or "Counter A").strip()
        if self._category_display_name == clean:
            return
        self._category_display_name = clean
        # Trigger background generation for the new name if any language is missing
        if self._data_dir and clean:
            self._ensure_category_audio(clean)

    def _ensure_category_audio(self, name: str):
        """Generate category MP3s in background if any language is missing."""
        slug = _slug(name)
        missing = [
            lang for lang in ("en", "fr", "ar")
            if not os.path.isfile(os.path.join(self._data_dir, lang, "category", f"{slug}.mp3"))
        ]
        if not missing:
            return
        print(f"[AudioEngine] Generating category audio for '{name}' (missing: {missing})")
        try:
            from app.helper.CategoryAudioHelper import generate_category_audio
            generate_category_audio(name, self._data_dir)
        except Exception as e:
            print(f"[AudioEngine] Category audio generation failed: {e}")

    # ── Public playback API ───────────────────────────────────────────────

    @Slot(str)
    def announceNumber(self, number: str):
        """Announce: [category name] + number.
        Safe to call from any thread — spawns its own daemon thread."""
        if not self._initialized or self._muted or not self._tts_enabled:
            print(f"[AudioEngine] blocked — "
                  f"init={self._initialized} muted={self._muted} tts={self._tts_enabled}")
            return
        # Stop any ongoing announcement before starting a new one
        self._stop_flag = True
        print(f"[AudioEngine] Announcing: {number}")
        threading.Thread(
            target=self._play_announcement,
            args=(number,),
            daemon=True,
        ).start()

    @Slot()
    def stop(self):
        self._stop_flag = True
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    # ── Internal playback ─────────────────────────────────────────────────

    def _play_announcement(self, number: str):
        with self._lock:          # serialise announcements
            self._stop_flag = False
            self._playing = True
            try:
                files = self._build_sequence(number)
                if not files:
                    print(f"[AudioEngine] empty sequence for '{number}'")
                    return
                vol = self.VOLUME_STEPS[self._volume_step]
                gap = 0.04         # <50 ms between atoms
                for rel in files:
                    if self._stop_flag:
                        break
                    full = os.path.join(self._data_dir, rel)
                    if not os.path.isfile(full):
                        print(f"[AudioEngine] missing atom: {full}")
                        continue
                    try:
                        pygame.mixer.music.load(full)
                        pygame.mixer.music.set_volume(vol)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            if self._stop_flag:
                                pygame.mixer.music.stop()
                                return
                            time.sleep(0.01)
                        time.sleep(gap)
                    except Exception as exc:
                        print(f"[AudioEngine] playback error {rel}: {exc}")
            except Exception as e:
                print(f"[AudioEngine] announcement error: {e}")
            finally:
                self._playing = False

    def _build_sequence(self, number: str) -> list:
        """Build the ordered list of MP3 relative paths to play.

        Format: [category.mp3 (optional)] + [digit atoms...]
        The 'now_serving' phrase has been removed — the category name
        already provides context, and shorter is better in service settings.
        """
        if not self._data_dir:
            return []

        lang = self._language
        slug = _slug(self._category_display_name)
        seq = []

        # 1. Category name (optional — only if categoryAudioEnabled and file exists)
        if self._category_audio_enabled:
            cat_path = os.path.join(self._data_dir, lang, "category", f"{slug}.mp3")
            if os.path.isfile(cat_path):
                seq.append(f"{lang}/category/{slug}.mp3")
            else:
                print(f"[AudioEngine] no category audio for '{slug}' in {lang} — skipping")

        # 2. Number digits
        try:
            num_val = int(number)
        except ValueError:
            num_val = 0
        seq.extend(self._digit_atoms(lang, num_val))

        return seq

    @staticmethod
    def _digit_atoms(lang: str, n: int) -> list:
        """Return the minimal list of number MP3 atoms for n."""
        atoms = []
        if lang == "ar":
            # Arabic: all numbers 0-99 are individual files
            if 0 <= n <= 99:
                atoms.append(f"{lang}/numbers/{n}.mp3")
            elif n >= 100:
                hundreds = n // 100
                remainder = n % 100
                atoms.append(f"{lang}/numbers/{hundreds}00.mp3")
                if remainder > 0:
                    atoms.append(f"{lang}/numbers/{remainder}.mp3")
        else:
            # English / French: compositional
            def _compose(x):
                parts = []
                if 0 <= x <= 19:
                    parts.append(f"{lang}/numbers/{x}.mp3")
                elif 20 <= x <= 99:
                    tens = (x // 10) * 10
                    ones = x % 10
                    parts.append(f"{lang}/numbers/{tens}.mp3")
                    if ones > 0:
                        parts.append(f"{lang}/numbers/{ones}.mp3")
                elif x >= 100:
                    hundreds = x // 100
                    remainder = x % 100
                    for _ in range(hundreds):
                        parts.append(f"{lang}/numbers/100.mp3")
                    if remainder > 0:
                        parts.extend(_compose(remainder))
                return parts
            atoms.extend(_compose(n))
        return atoms


def _slug(name: str) -> str:
    """Normalise a display name to a safe filename slug."""
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:48]
