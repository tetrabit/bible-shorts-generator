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
mkdir -p models/{sdxl,piper,whisper}
mkdir -p models/qwen3-vl
mkdir -p data/bible
mkdir -p generated/{backgrounds,audio,timestamps,subtitles,final,uploaded}
mkdir -p logs
echo "✓ Directories created"
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

# Download AI models (optional - can be slow)
read -p "Download AI models now? This will download ~15GB (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 download_models.py
else
    echo "Skipping model download. You can run 'python3 download_models.py' later."
fi
echo ""

# Optional: clone Qwen3-VL repository for text-to-video
read -p "Clone Qwen3-VL repository (optional, required for qwen3 backend)? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "models/qwen3-vl/.git" ]; then
        echo "Qwen3-VL already cloned at models/qwen3-vl"
    else
        echo "Cloning Qwen3-VL..."
        git clone https://github.com/QwenLM/Qwen3-VL.git models/qwen3-vl || echo "⚠ Failed to clone Qwen3-VL. Please clone manually."
    fi
    echo "Remember to follow Qwen3-VL instructions to download weights inside models/qwen3-vl."
else
    echo "Skipping Qwen3-VL clone. Set video.backend to 'sdxl' or clone later into models/qwen3-vl."
fi
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
echo "4. If you skipped models, run: python3 download_models.py"
echo "5. Test generation: ./run.sh generate 1"
echo ""
echo "For help: ./run.sh --help"
echo ""
