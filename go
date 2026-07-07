#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  CandyBarV2 — one-shot launcher
#  Usage:  ./go
# ─────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

PYTHON="./venv/bin/python3"
PIP="./venv/bin/pip"

# ── 1. Create venv if missing ────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo "[go] Creating virtual environment..."
    python3 -m venv venv
fi

# ── 2. Install / sync dependencies ──────────────────────────────
echo "[go] Checking dependencies..."
$PIP install -q -r requirements.txt

# ── 3. Regenerate QRC resource bundle ───────────────────────────
echo "[go] Compiling resources..."
$PYTHON scripts/update_resources.py

# ── 4. Sync sound folder → audio data dir ───────────────────────
AUDIO_DIR="$HOME/.local/share/CandyBarV2/CandyBarV2/audio"
python3 scripts/sync_sounds.py "$AUDIO_DIR" 2>/dev/null || true

# ── 5. Generate audio atoms if missing ──────────────────────────
AUDIO_DIR="$HOME/.local/share/CandyBarV2/CandyBarV2/audio"
if [ ! -f "$AUDIO_DIR/en/phrases/now_serving.mp3" ]; then
    echo "[go] Generating TTS audio atoms (first run — needs internet)..."
    $PYTHON scripts/generate_audio.py --output-dir "$AUDIO_DIR" || \
        echo "[go] Warning: audio generation failed — announcements will be silent"
else
    echo "[go] Audio atoms OK"
fi

# ── 6. Launch ───────────────────────────────────────────────────
echo "[go] Starting CandyBarV2..."
exec $PYTHON -m app.main
