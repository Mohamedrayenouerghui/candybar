"""
sync_sounds.py — copy files from the sound/ folder into the audio data dir.

Naming convention expected in sound/:
  <number> <language>.mp3   e.g. "1 english.mp3", "2 french.mp3", "3 arabic.mp3"

Language mapping:
  english → en
  french  → fr
  arabic  → ar

Run automatically by the go script on every launch.
"""

import os
import re
import shutil
import sys

LANG_MAP = {"english": "en", "french": "fr", "arabic": "ar"}

def main(audio_dir: str):
    sound_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sound")
    if not os.path.isdir(sound_dir):
        return

    pattern = re.compile(r"^(\d+)\s+(\w+)\.mp3$", re.IGNORECASE)
    copied = 0

    for fname in os.listdir(sound_dir):
        m = pattern.match(fname)
        if not m:
            continue
        number = m.group(1)
        lang_word = m.group(2).lower()
        lang = LANG_MAP.get(lang_word)
        if not lang:
            print(f"[sync_sounds] Unknown language '{lang_word}' in {fname}, skipping")
            continue

        dest_dir = os.path.join(audio_dir, lang, "numbers")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f"{number}.mp3")
        src  = os.path.join(sound_dir, fname)

        # Only copy if source is newer or dest missing
        if not os.path.exists(dest) or os.path.getmtime(src) > os.path.getmtime(dest):
            shutil.copy2(src, dest)
            copied += 1
            print(f"[sync_sounds] {fname} → {lang}/numbers/{number}.mp3")

    if copied:
        print(f"[sync_sounds] Synced {copied} file(s)")
    else:
        print("[sync_sounds] All sound files up to date")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sync_sounds.py <audio_dir>")
        sys.exit(1)
    main(sys.argv[1])
