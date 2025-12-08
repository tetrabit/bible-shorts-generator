# Dependencies

Complete list of all dependencies required by the Bible Shorts Generator.

## System Requirements

### Operating System
- **Linux** (Ubuntu 20.04+ recommended)
- **WSL2** on Windows (as evidenced by kernel version)

### Hardware
- **GPU**: NVIDIA GPU with CUDA support
  - Minimum: 8GB VRAM (for Wan 1.3B model)
  - Recommended: 24GB+ VRAM (for Wan 14B model)
- **RAM**: 16GB minimum, 32GB+ recommended
- **Storage**: 50GB+ free space (for models and generated videos)

### System Packages

Install via package manager:
```bash
sudo apt-get update
sudo apt-get install -y \
  python3.10 \
  python3-venv \
  python3-dev \
  ffmpeg \
  git \
  build-essential \
  libsndfile1
```

### CUDA & GPU Drivers
- **CUDA**: 12.1+ (for PyTorch CUDA support)
- **NVIDIA Drivers**: Latest compatible with your GPU
- **cuDNN**: Installed automatically with PyTorch

Verify CUDA:
```bash
nvidia-smi
nvcc --version
```

## Python Dependencies

All Python packages are specified in `requirements.txt`. Install with:
```bash
pip install -r requirements.txt
```

### Core Dependencies
- **python-dotenv** (1.0.0) - Environment variable management
- **pyyaml** (6.0.1) - Configuration file parsing
- **loguru** (0.7.2) - Logging
- **rich** (13.7.0) - CLI formatting
- **tqdm** (4.66.1) - Progress bars

### AI/ML - PyTorch Stack
- **torch** (2.8.0) - Deep learning framework
- **torchvision** (0.23.0) - Vision utilities
- **torchaudio** (2.8.0) - Audio utilities
- **omegaconf** (2.3.0) - Configuration management

Note: Uses CUDA 12.1 compatible builds from PyTorch index.

### Speech & Audio Processing
- **whisper** (from OpenAI GitHub) - Speech recognition
- **whisperx** (from GitHub) - Word-level alignment
- **pyannote.audio** (dependency of WhisperX) - Audio processing

### Video/Image Processing
- **opencv-python** (4.10.0.84) - Video processing
- **opencv-python-headless** (4.10.0.84) - Headless OpenCV
- **Pillow** (11.3.0) - Image manipulation
- **numpy** (2.2.6) - Numerical operations
- **imageio** (2.33.1) - Image I/O
- **imageio-ffmpeg** (0.4.9) - FFmpeg wrapper

### Bible Data
- **pythonbible** (0.14.0) - Bible verse management
- **requests** (2.31.0) - HTTP requests

### YouTube API
- **google-api-python-client** (2.115.0) - YouTube API client
- **google-auth-oauthlib** (1.2.0) - OAuth authentication
- **google-auth-httplib2** (0.2.0) - HTTP client for Google Auth

### Model Management
- **huggingface_hub** (0.20.3) - Download models from Hugging Face

### Scheduling
- **APScheduler** (3.10.4) - Job scheduling
- **pytz** (2023.3) - Timezone support
- **python-dateutil** (2.8.2) - Date utilities

## External Binaries

### FFmpeg
**Required for**: Video composition, audio processing, encoding

Install:
```bash
sudo apt-get install ffmpeg
```

Verify:
```bash
ffmpeg -version
```

Features needed:
- libx264 (video encoding)
- aac (audio encoding)
- qtrle (subtitle overlay codec)
- PNG/MOV input/output

### Piper TTS
**Required for**: Text-to-speech audio generation

**Note**: Piper binary must be installed separately. Python package `piper-tts` is NOT compatible with Python 3.13.

Install manually:
```bash
# Download from: https://github.com/rhasspy/piper/releases
# Extract and add to PATH
```

Verify:
```bash
piper --version
```

Voice models are auto-downloaded via Hugging Face Hub to `models/piper/`.

## AI Model Dependencies

### Wan Text-to-Video
**Repository**: `models/wan2.1/` (cloned from GitHub)
**Weights**: `models/wan2.1-weights/` (downloaded from Hugging Face)

Setup:
```bash
# Clone repository
git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1

# Download weights
python3 download_wan_weights.py

# Install Wan-specific dependencies
pip install -r models/wan2.1/requirements.txt
```

Wan dependencies (in `models/wan2.1/requirements.txt`):
- diffusers
- transformers
- accelerate
- safetensors
- flash_attn (optional, may fail on some systems)

### WhisperX Models
**Auto-downloaded** on first use to `models/whisper/`

Models:
- Whisper base model (specified in config.yaml)
- Language-specific alignment models (e.g., English)

### Piper Voice Models
**Auto-downloaded** from Hugging Face on first use to `models/piper/`

Default voice: `en_US-lessac-medium` (configurable in config.yaml)

## Optional Dependencies

### Hugging Face Token
For private models or increased download limits:

```bash
# In .env file
HF_TOKEN=your_token_here
```

Get token from: https://huggingface.co/settings/tokens

## Verification

### Test All Dependencies
```bash
./run.sh test
```

This checks:
- Configuration loading
- Database connectivity
- FFmpeg availability
- Piper TTS installation
- Wan repository and weights

### Manual Verification
```python
# Test PyTorch CUDA
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")

# Test WhisperX
import whisperx
print("WhisperX: OK")

# Test other imports
import cv2, PIL, numpy, pythonbible, googleapiclient
print("All imports: OK")
```

## Common Issues

### Missing huggingface_hub
```bash
pip install huggingface_hub
```

### CUDA/cuDNN Errors with WhisperX
WhisperX automatically falls back to CPU if CUDA/cuDNN fails. Check logs for warnings.

### Piper Not Found
Install Piper binary manually. The Python package does not work with Python 3.13.

### FFmpeg Missing Codecs
```bash
# Reinstall FFmpeg with full codec support
sudo apt-get install --reinstall ffmpeg
```

### Wan Dependencies Fail
```bash
cd models/wan2.1
pip install -r requirements.txt

# If flash_attn fails, that's OK - it's optional
```

## Dependency Management

### Update All Dependencies
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Check for Conflicts
```bash
pip check
```

### Freeze Installed Versions
```bash
pip freeze > requirements-frozen.txt
```

## Version Compatibility

### Python
- **Required**: 3.10+
- **Tested**: 3.10, 3.13
- **Note**: Piper binary issues with 3.13 (use manual installation)

### CUDA
- **Required**: 12.1+
- **PyTorch Index**: Uses cu121 builds
- **Compatible**: NVIDIA drivers 525+

### Operating System
- **Primary**: Ubuntu 20.04+, Debian 11+
- **Secondary**: WSL2 on Windows
- **Not Tested**: macOS (would need CPU-only PyTorch)
