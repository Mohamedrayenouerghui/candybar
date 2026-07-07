#!/usr/bin/env python3
"""
generate_audio.py — Pre-generate TTS audio atoms for CandyBarV2.

This script generates all MP3 audio atoms needed for number announcements.
Run once at setup time (requires internet for Edge-TTS).

Usage:
    python3 scripts/generate_audio.py [--output-dir /path/to/audio]

Audio structure:
    audio/
        en/
            numbers/    ← 0-19 individual, 20,30,40,50,60,70,80,90 by tens
            category/   ← generated when category name is saved
            phrases/    ← "now serving", etc.
        fr/
            numbers/    ← same structure, French pronunciation
            category/
            phrases/
        ar/
            numbers/    ← 0-99 individual (no composition for Arabic)
            category/
            phrases/
        custom/       ← operator-uploaded MP3s

Dependencies:
    edge-tts: pip install edge-tts
    num2words: pip install num2words
    pydub: pip install pydub (for volume normalization)

Voice models:
    English: en-US-AriaNeural (natural, clear)
    French: fr-FR-DeniseNeural (clear, standard French)
    Arabic: ar-SA-HamedNeural (male) or ar-SA-ZariyahNeural (female)
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("Error: edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

try:
    from num2words import num2words
except ImportError:
    print("Error: num2words not installed. Run: pip install num2words")
    sys.exit(1)

try:
    from pydub import AudioSegment
except ImportError:
    print("Warning: pydub not installed. Volume normalization disabled. Run: pip install pydub")


# Voice configuration
VOICES = {
    "en": "en-US-AriaNeural",
    "fr": "fr-FR-DeniseNeural",
    "ar": "ar-SA-HamedNeural",  # Can also use "ar-SA-ZariyahNeural" for female
}

# Phrase templates by language
PHRASES = {
    "en": {
        "now_serving": "now serving number",
    },
    "fr": {
        "now_serving": "nous appelons le numéro",
    },
    "ar": {
        "now_serving": "يرجى التوجه للرقم",
    },
}


def normalize_audio(input_path: str, output_path: str, target_dBFS: float = -20.0):
    """Normalize audio to consistent loudness using pydub."""
    try:
        audio = AudioSegment.from_mp3(input_path)
        change_in_dBFS = target_dBFS - audio.dBFS
        normalized = audio.apply_gain(change_in_dBFS)
        normalized.export(output_path, format="mp3")
    except Exception as e:
        print(f"Warning: Could not normalize {input_path}: {e}")
        # Copy original if normalization fails
        import shutil
        shutil.copy(input_path, output_path)


async def generate_tts(text: str, voice: str, output_path: str):
    """Generate TTS audio using edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_number_atoms(language: str, output_dir: Path):
    """Generate number audio atoms for a language."""
    print(f"Generating number atoms for {language}...")
    
    numbers_dir = output_dir / language / "numbers"
    numbers_dir.mkdir(parents=True, exist_ok=True)
    
    voice = VOICES[language]
    
    if language == "ar":
        # Arabic: 0-99 individual files (no composition)
        for num in range(100):
            text = num2words(num, lang='ar')
            output_path = numbers_dir / f"{num}.mp3"
            if not output_path.exists():
                print(f"  Generating {num}.mp3: {text}")
                import asyncio
                asyncio.run(generate_tts(text, voice, str(output_path)))
                
                # Normalize if pydub available
                temp_path = str(output_path) + ".temp"
                os.rename(str(output_path), temp_path)
                normalize_audio(temp_path, str(output_path))
                os.remove(temp_path)
    else:
        # English/French: 0-19 individual + tens (20,30,...,90)
        for num in range(20):
            text = num2words(num, lang=language)
            output_path = numbers_dir / f"{num}.mp3"
            if not output_path.exists():
                print(f"  Generating {num}.mp3: {text}")
                import asyncio
                asyncio.run(generate_tts(text, voice, str(output_path)))
                
                # Normalize
                temp_path = str(output_path) + ".temp"
                os.rename(str(output_path), temp_path)
                normalize_audio(temp_path, str(output_path))
                os.remove(temp_path)
        
        for tens in [20, 30, 40, 50, 60, 70, 80, 90]:
            text = num2words(tens, lang=language)
            output_path = numbers_dir / f"{tens}.mp3"
            if not output_path.exists():
                print(f"  Generating {tens}.mp3: {text}")
                import asyncio
                asyncio.run(generate_tts(text, voice, str(output_path)))
                
                # Normalize
                temp_path = str(output_path) + ".temp"
                os.rename(str(output_path), temp_path)
                normalize_audio(temp_path, str(output_path))
                os.remove(temp_path)
        
        # Also generate "100" for composition
        text = num2words(100, lang=language)
        output_path = numbers_dir / "100.mp3"
        if not output_path.exists():
            print(f"  Generating 100.mp3: {text}")
            import asyncio
            asyncio.run(generate_tts(text, voice, str(output_path)))
            
            # Normalize
            temp_path = str(output_path) + ".temp"
            os.rename(str(output_path), temp_path)
            normalize_audio(temp_path, str(output_path))
            os.remove(temp_path)


def generate_phrases(language: str, output_dir: Path):
    """Generate phrase audio atoms for a language."""
    print(f"Generating phrases for {language}...")
    
    phrases_dir = output_dir / language / "phrases"
    phrases_dir.mkdir(parents=True, exist_ok=True)
    
    voice = VOICES[language]
    
    for phrase_key, phrase_text in PHRASES[language].items():
        output_path = phrases_dir / f"{phrase_key}.mp3"
        if not output_path.exists():
            print(f"  Generating {phrase_key}.mp3: {phrase_text}")
            import asyncio
            asyncio.run(generate_tts(phrase_text, voice, str(output_path)))
            
            # Normalize
            temp_path = str(output_path) + ".temp"
            os.rename(str(output_path), temp_path)
            normalize_audio(temp_path, str(output_path))
            os.remove(temp_path)


def generate_category_name(category_name: str, language: str, output_dir: Path):
    """Generate audio for a category name."""
    print(f"Generating category name audio for '{category_name}' in {language}...")
    
    category_dir = output_dir / language / "category"
    category_dir.mkdir(parents=True, exist_ok=True)
    
    voice = VOICES[language]
    output_path = category_dir / f"{category_name}.mp3"
    
    print(f"  Generating {category_name}.mp3")
    import asyncio
    asyncio.run(generate_tts(category_name, voice, str(output_path)))
    
    # Normalize
    temp_path = str(output_path) + ".temp"
    os.rename(str(output_path), temp_path)
    normalize_audio(temp_path, str(output_path))
    os.remove(temp_path)


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio atoms for CandyBarV2")
    parser.add_argument(
        "--output-dir",
        default="audio",
        help="Output directory for audio files (default: audio)"
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["en", "fr", "ar"],
        choices=["en", "fr", "ar"],
        help="Languages to generate (default: en fr ar)"
    )
    parser.add_argument(
        "--category-name",
        help="Generate audio for a specific category name"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    print(f"Languages: {', '.join(args.languages)}")
    
    # Generate number atoms and phrases for each language
    for language in args.languages:
        generate_number_atoms(language, output_dir)
        generate_phrases(language, output_dir)
    
    # Generate category name if specified
    if args.category_name:
        for language in args.languages:
            generate_category_name(args.category_name, language, output_dir)
    
    print("\nAudio generation complete!")
    print(f"Audio files saved to: {output_dir}")


if __name__ == "__main__":
    main()
