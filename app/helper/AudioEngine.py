"""
AudioEngine.py — TTS audio playback engine for CandyBarV2.

Hybrid pre-generation + runtime playback. No live TTS at runtime.
Uses pygame.mixer.Sound for sequential atom playback (<50ms gap).
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
        self._category_display_name = "Category A"
        self._tts_enabled = True
        self._init_mixer()

    def _init_mixer(self):
        if pygame is None:
            print("[AudioEngine] pygame not installed — audio disabled")
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
        except Exception as e:
            print(f"[AudioEngine] Failed to initialize audio: {e}")

    @Property(bool)
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, value):
        self._muted = bool(value)

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

    def set_data_dir(self, data_dir: str):
        self._data_dir = data_dir

    @Slot(str)
    def set_category_display_name(self, name: str):
        if self._category_display_name != name:
            self._category_display_name = name or "Category A"
            if self._data_dir and name:
                slug = re.sub(r"[^\w\-]", "_", name.lower())[:48]
                exists = all(
                    os.path.isfile(os.path.join(self._data_dir, lang, "category", f"{slug}.mp3"))
                    for lang in ("en", "fr", "ar")
                )
                if not exists:
                    try:
                        from app.helper.CategoryAudioHelper import generate_category_audio
                        generate_category_audio(name, self._data_dir)
                    except Exception as e:
                        print(f"[AudioEngine] Failed to trigger category audio generation: {e}")

    @Slot(str)
    def announceNumber(self, number: str):
        if not self._initialized or self._muted or not self._tts_enabled:
            print(f"[AudioEngine] blocked — init={self._initialized} muted={self._muted} tts={self._tts_enabled}")
            return
        print(f"[AudioEngine] Playing: {number}")
        threading.Thread(target=self._play_announcement, args=(number,), daemon=True).start()

    def _category_slug(self) -> str:
        return re.sub(r"[^\w\-]", "_", self._category_display_name.lower())[:48]

    def _play_announcement(self, number: str):
        try:
            self._playing = True
            audio_files = self._build_audio_sequence(number)
            if not audio_files:
                print(f"[AudioEngine] No audio files for number {number}")
                self._playing = False
                return

            vol = 0.0 if self._muted else self.VOLUME_STEPS[self._volume_step]
            gap = 0.04  # <50ms between atoms

            for rel_path in audio_files:
                if not self._playing:
                    break
                full = os.path.join(self._data_dir, rel_path)
                if not os.path.isfile(full):
                    print(f"[AudioEngine] Missing: {full}")
                    continue
                try:
                    snd = pygame.mixer.Sound(full)
                    snd.set_volume(vol)
                    ch = snd.play()
                    while ch and ch.get_busy():
                        if not self._playing:
                            ch.stop()
                            break
                        time.sleep(0.01)
                    time.sleep(gap)
                except Exception as exc:
                    print(f"[AudioEngine] Playback error {full}: {exc}")
        except Exception as e:
            print(f"[AudioEngine] Playback error: {e}")
        finally:
            self._playing = False

    def _build_audio_sequence(self, number: str) -> list:
        if not self._data_dir:
            return []

        lang = self._language
        slug = self._category_slug()
        sequence = []

        category_audio = f"{lang}/category/{slug}.mp3"
        if os.path.isfile(os.path.join(self._data_dir, category_audio)):
            sequence.append(category_audio)

        sequence.append(f"{lang}/phrases/now_serving.mp3")

        try:
            num_val = int(number)
        except ValueError:
            num_val = 0

        # Build digit sequence inline
        if lang == "ar":
            if 0 <= num_val <= 99:
                sequence.append(f"{lang}/numbers/{num_val}.mp3")
            elif num_val >= 100:
                hundreds = num_val // 100
                remainder = num_val % 100
                sequence.append(f"{lang}/numbers/{hundreds}00.mp3")
                if remainder > 0:
                    sequence.append(f"{lang}/numbers/{remainder}.mp3")
        else:
            # English / French composition
            def _en_fr_digits(n):
                parts = []
                if 0 <= n <= 19:
                    parts.append(f"{lang}/numbers/{n}.mp3")
                elif 20 <= n <= 99:
                    tens = (n // 10) * 10
                    ones = n % 10
                    parts.append(f"{lang}/numbers/{tens}.mp3")
                    if ones > 0:
                        parts.append(f"{lang}/numbers/{ones}.mp3")
                elif n >= 100:
                    hundreds = n // 100
                    remainder = n % 100
                    for _ in range(hundreds):
                        parts.append(f"{lang}/numbers/100.mp3")
                    if remainder > 0:
                        parts.extend(_en_fr_digits(remainder))
                return parts
            sequence.extend(_en_fr_digits(num_val))

        return sequence

    @Slot()
    def stop(self):
        self._playing = False
