#!/bin/bash
set -e

echo "=========================================="
echo "Bible Shorts Generator - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "ERROR: Python $required_version or higher required (found: $python_version)"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Check for FFmpeg
echo "Checking for FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: FFmpeg not found"
    echo "Install with: sudo apt-get install ffmpeg"
    exit 1
fi
echo "✓ FFmpeg found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
echo "This may take 10-20 minutes..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p models/{piper,whisper}
mkdir -p models/qwen3-vl
mkdir -p data/bible
mkdir -p generated/{backgrounds,audio,timestamps,subtitles,final,uploaded}
mkdir -p logs
echo "✓ Directories created"
echo ""

# Clone Wan T2V repository for text-to-video backend
echo "=========================================="
echo "Wan Text-to-Video Setup"
echo "=========================================="
echo ""
echo "Wan is Alibaba's text-to-video model (actual video generation from text)."
echo "Note: This is different from Qwen3-VL (which is vision-to-text)."
echo ""
read -p "Set up Wan text-to-video backend? (y/n): " -n 1 -r
echo ""
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Clone Wan repository
    if [ -d "models/wan2.1/.git" ]; then
        echo "✓ Wan repository already present at models/wan2.1"
    else
        echo "Cloning Wan2.1 repository..."
        set +e
        git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1
        clone_status=$?
        set -e
        if [ $clone_status -ne 0 ]; then
            echo "⚠ Failed to clone Wan repository."
            echo "You can clone manually: git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1"
        else
            echo "✓ Wan repository cloned to models/wan2.1"
        fi
    fi
    echo ""

    # Install Wan dependencies
    if [ -d "models/wan2.1" ] && [ -f "models/wan2.1/requirements.txt" ]; then
        echo "Installing Wan dependencies..."
        set +e
        pip install -r models/wan2.1/requirements.txt
        wan_deps_status=$?
        set -e
        if [ $wan_deps_status -ne 0 ]; then
            echo "⚠ Some Wan dependencies failed to install."
            echo "Note: If flash_attn fails, you can continue - it's optional."
            echo "You can retry: cd models/wan2.1 && pip install -r requirements.txt"
        else
            echo "✓ Wan dependencies installed"
        fi
    fi
    echo ""

    # Download Wan model weights
    echo "=========================================="
    echo "Wan Model Weights Download"
    echo "=========================================="
    echo ""
    echo "Available models:"
    echo "  1) Wan2.1-T2V-1.3B (~3GB) - Consumer GPU (8GB VRAM)"
    echo "     Generates 480p videos in ~4 minutes"
    echo ""
    echo "  2) Wan2.1-T2V-14B (~28GB) - High-end GPU (24GB+ VRAM)"
    echo "     Generates 720p videos, better quality"
    echo ""
    echo "  3) Skip - Download manually later"
    echo ""
    read -p "Select model (1-3): " -n 1 -r model_choice
    echo ""
    echo ""

    if [[ $model_choice =~ ^[1-2]$ ]]; then
        # Ensure huggingface-cli is installed
        echo "Installing huggingface-cli (if not present)..."
        pip install "huggingface_hub[cli]" --quiet

        # Determine model ID based on choice
        case $model_choice in
            1)
                MODEL_ID="Wan-AI/Wan2.1-T2V-1.3B"
                MODEL_SIZE="1.3B"
                RESOLUTION="832*480"
                ;;
            2)
                MODEL_ID="Wan-AI/Wan2.1-T2V-14B"
                MODEL_SIZE="14B"
                RESOLUTION="1280*720"
                ;;
        esac

        echo "Downloading $MODEL_ID..."
        echo "This may take 5-60 minutes depending on your connection..."
        echo ""

        # Download model weights using huggingface-cli
        set +e
        huggingface-cli download $MODEL_ID --local-dir models/wan2.1-weights
        download_status=$?
        set -e

        if [ $download_status -eq 0 ]; then
            echo ""
            echo "✓ Wan model weights successfully downloaded!"
            echo ""

            # Update config.yaml with the downloaded model
            python3 - <<PY
from pathlib import Path
import re

config_file = Path("config.yaml")
if config_file.exists():
    try:
        content = config_file.read_text()

        # Update Wan model size
        content = re.sub(
            r'(size:\s*)"[^"]*"(\s*#.*1\.3B.*14B)',
            f'\\1"${MODEL_SIZE}"\\2',
            content
        )

        # Update resolution
        content = re.sub(
            r'(resolution:\s*)"[^"]*"(\s*#.*for)',
            f'\\1"${RESOLUTION}"\\2',
            content
        )

        config_file.write_text(content)
        print(f"✓ Updated config.yaml with Wan model: ${MODEL_SIZE}")
    except Exception as e:
        print(f"⚠ Could not auto-update config.yaml: {e}")
        print(f"Please manually set: models.wan.size: \"${MODEL_SIZE}\"")
PY
        else
            echo ""
            echo "⚠ Wan model download encountered issues."
            echo "You can retry with: python3 download_wan_weights.py"
        fi
    else
        echo "Skipping Wan weights download."
        echo "You can download later with: python3 download_wan_weights.py"
    fi
    echo ""
else
    echo "Skipping Wan setup."
    echo "To set up later, see: WAN_SETUP.md"
fi
echo ""

# Initialize database
echo "Initializing database..."
python3 -c "from src.modules.database import Database; Database()"
echo "✓ Database initialized"
echo ""

# Download Bible data
echo "Downloading Bible data..."
python3 download_bible.py
echo ""

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
fi

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Add your YouTube API credentials to .env"
echo "2. Get credentials from: https://console.cloud.google.com/"
echo "3. Run: python3 auth.py (to authenticate YouTube)"
echo "4. Test generation: ./run.sh generate 1"
echo ""
echo "For help: ./run.sh --help"
echo ""
