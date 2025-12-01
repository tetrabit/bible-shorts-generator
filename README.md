# Bible Shorts Generator

Automated system for creating YouTube Shorts (vertical 1080x1920 videos, <7 seconds) from Bible verses using local AI models. Completely headless and terminal-based - no GUI required.

## Features

- **Fully Automated**: Select verses → Generate video → Upload to YouTube
- **100% Local AI**: All models run locally (SDXL, WhisperX, Piper TTS via external install)
- **Terminal-Only**: No UI, perfect for servers and automation
- **Smart Verse Selection**: Filters verses by word count to ensure <7 second duration
- **Professional Output**: Cinematic backgrounds, word-by-word subtitle highlighting
- **Scheduled Uploads**: Auto-generate and upload on configurable schedule
- **Database Tracking**: SQLite tracks all videos, uploads, and statistics
- **Self-Healing Assets**: Auto-download Piper voices and fallback subtitle font when missing
- **Memory Friendly**: Diffusion and WhisperX models are loaded lazily, use GPU during runs, and are unloaded after use to free VRAM

## System Architecture

**Pipeline:**
1. Verse Selection (word count filtering)
2. Background Generation (SDXL + Ken Burns effect)
3. TTS Generation (Piper TTS binary, installed separately)
4. Word Alignment (WhisperX forced alignment)
5. Subtitle Rendering (word-level highlighting)
6. Video Composition (FFmpeg)
7. YouTube Upload (API v3)

## Requirements

### Hardware

**Minimum:**
- NVIDIA GPU with 12GB VRAM (RTX 3060 or better)
- 16GB RAM
- 100GB free disk space

**Recommended:**
- NVIDIA RTX 4070 or better (24GB VRAM)
- 32GB RAM
- 500GB SSD

**CPU-Only Mode:**
- Possible but very slow (10-30 min per video vs 2-5 min)
- Set `models.sdxl.device: "cpu"` in config.yaml

### Software

- Python 3.10+ (tested on 3.13)
- FFmpeg
- CUDA 12.1+ (for GPU)
- Linux (Ubuntu/Debian recommended)
- Piper TTS binary if you want the Piper engine (PyPI wheels are not available on Python 3.13; install from https://github.com/rhasspy/piper or use Python ≤3.12)
- OpenAI Whisper is installed from a pinned Git commit for Python 3.13 compatibility (handled automatically by `setup.sh`)

## Installation

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd bible-shorts-generator
```

### 2. Run Setup

```bash
./setup.sh
```

This will:
- Create virtual environment
- Install all Python dependencies
- Initialize database
- Download Bible data
- Optionally download AI models (~15GB)
- Note: Piper TTS is not installed automatically on Python 3.13. Install the Piper binary manually if you need that engine.
  - Piper voices are downloaded automatically on first use to `models/piper/<voice>/` via Hugging Face.

### 3. Configure YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable "YouTube Data API v3"
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials as `client_secrets.json`
6. Place in project root

### 4. Authenticate

```bash
./run.sh auth
# or: python3 auth.py
```

Follow browser prompts to authorize. Credentials saved to `.env` automatically.

### 5. Download Models (if skipped during setup)

```bash
./run.sh models
# or: python3 download_models.py
```

Downloads:
- Stable Diffusion XL (~14GB)
- Whisper base model (~140MB)
- Piper TTS voice (~30MB) if Piper is installed on your system

## Quick Start

### Generate Single Video

```bash
./run.sh generate 1
```

Output saved to `generated/final/<verse_id>.mp4`

### Upload Video

```bash
./run.sh upload <video_id>
```

Get video ID from database or generation output.

### Start Automated Scheduler

```bash
./run.sh schedule
```

Runs continuously:
- Generates videos every 2 hours (configurable)
- Uploads at scheduled times (9am, 3pm, 9pm by default)
- Automatic cleanup and maintenance

Press Ctrl+C to stop.

## Configuration

All behavior controlled via `config.yaml`:

### Key Settings

```yaml
video:
  width: 1080
  height: 1920
  max_duration: 7  # seconds

text:
  max_words: 18  # Ensures <7s duration
  speaking_rate: 3.0  # words/second
  # The renderer will download DejaVuSans-Bold to this path if the file is missing.
  font_path: "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

bible:
  version: "KJV"
  books: ["Psalms", "Proverbs", "John", "Matthew"]
  min_words: 5
  max_words: 18

models:
  sdxl:
    device: "cuda"  # or "cpu"
    dtype: "float16"
    skip: false  # Set to true to use a placeholder background for fast, non-SDXL testing
    skip: false  # Set to true to skip SDXL and use a placeholder background for fast testing

youtube:
  privacy: "public"
  upload_schedule:
    times: ["09:00", "15:00", "21:00"]

scheduler:
  generation_interval: "2h"
  batch_size: 3

# Debug shortcuts
# models:
#   sdxl:
#     skip: true        # Use placeholder background instead of SDXL
# video:
#   skip_subtitles: true # Compose without subtitle overlay (video + audio only)
```

## Usage

### Command Line

```bash
# Generate videos
./run.sh generate 5         # Generate 5 videos

# Upload videos
./run.sh upload 42          # Upload video ID 42

# Start scheduler (runs indefinitely)
./run.sh schedule

# View statistics
./run.sh stats

# Test components
./run.sh test

# View logs
./run.sh logs               # Tail app.log
./run.sh logs upload.log    # Tail upload.log

# Database operations
./run.sh db videos          # List recent videos
./run.sh db ready           # List videos ready to upload
./run.sh db shell           # Open SQLite shell

# Clean up
./run.sh clean              # Delete generated files
```

### Python API

```python
from src.main import BibleShortsGenerator

# Create generator
gen = BibleShortsGenerator()

# Generate single video
result = gen.generate_video()

# Upload video
if result:
    gen.upload_video(result['video_id'])

# Generate batch
gen.run_batch(count=5)
```

## Monitoring

### Logs

```bash
# Live application logs
tail -f logs/app.log

# Upload logs
tail -f logs/upload.log
```

### Database Queries

```bash
# Statistics
sqlite3 data/database.db "SELECT * FROM statistics ORDER BY date DESC LIMIT 7;"

# Video status counts
sqlite3 data/database.db "SELECT status, COUNT(*) FROM videos GROUP BY status;"

# Ready to upload
sqlite3 data/database.db "SELECT * FROM videos WHERE status='ready';"
```

### Systemd Service (Linux)

For automatic startup on boot:

```bash
sudo cp bible-shorts.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bible-shorts.service
sudo systemctl start bible-shorts.service

# Monitor
sudo systemctl status bible-shorts.service
sudo journalctl -u bible-shorts.service -f
```

## Troubleshooting

### Common Issues

**1. Out of Memory (CUDA)**
```yaml
# In config.yaml, reduce batch size or use CPU:
models:
  sdxl:
    device: "cpu"
    dtype: "float32"
```

**2. FFmpeg Not Found**
```bash
sudo apt-get install ffmpeg
```

**3. Piper TTS Not Installed/Working**
- Install the Piper binary from https://github.com/rhasspy/piper (preferred on Python 3.13), or use Python ≤3.12 and `pip install piper-tts`, then rerun `./run.sh models`.
- Voices are stored in `models/piper/<voice>/`. If a download lands in nested folders (Hugging Face layout), the app will flatten it automatically on next run.

**4. YouTube Quota Exceeded**
- Default quota: 10,000 points/day
- Each upload: 1,600 points
- Limit: ~6 videos/day
- Request quota increase from Google

**5. No Suitable Verses Found**
```yaml
# Increase max_words in config.yaml:
bible:
  max_words: 22  # Allow longer verses
```

**6. Torch 2.6 `weights_only` / OmegaConf errors**
- Update to the latest code; WhisperX loads now allowlist OmegaConf configs.
- If you still see the error, remove old WhisperX checkpoints and rerun so fresh, safe globals are applied.

**7. SDXL not using GPU**
- Ensure `models.sdxl.device: "cuda"` in `config.yaml`.
- The model now stays on GPU while generating and is moved back to CPU after each batch to free VRAM. If you disabled CUDA elsewhere, re-enable it and restart.

**8. Final video is black with subtitles only**
- Subtitles are encoded to WebM (VP9 with alpha) and overlaid with `overlay=...:format=auto`. Update to the latest code if you see black backgrounds.
- If you’re testing without SDXL, set `models.sdxl.skip: true` to use a placeholder background.

### Testing Components

```bash
./run.sh test
```

Tests:
- Configuration loading
- Database connectivity
- FFmpeg availability
- Piper TTS availability (if installed)

## Project Structure

```
bible-shorts-generator/
├── config.yaml           # Main configuration
├── .env                  # API credentials (create from .env.example)
├── setup.sh              # One-time setup script
├── run.sh                # Main execution script
├── auth.py               # YouTube authentication
├── download_models.py    # Download AI models
├── download_bible.py     # Initialize Bible data
│
├── src/
│   ├── main.py          # Main orchestrator
│   ├── config.py        # Configuration loader
│   ├── scheduler.py     # APScheduler automation
│   │
│   ├── modules/
│   │   ├── database.py          # SQLite operations
│   │   ├── verse_selector.py   # Verse selection
│   │   ├── timing_analyzer.py  # Duration estimation
│   │   ├── video_generator.py  # SDXL background gen
│   │   ├── tts_engine.py       # Piper TTS wrapper (expects Piper binary)
│   │   ├── word_aligner.py     # WhisperX alignment
│   │   ├── subtitle_renderer.py # Subtitle overlays
│   │   ├── video_composer.py   # FFmpeg composition
│   │   └── youtube_uploader.py # YouTube API
│   │
│   └── utils/
│       ├── logger.py        # Logging setup
│       ├── ffmpeg_utils.py  # FFmpeg wrappers
│       └── file_manager.py  # File operations
│
├── data/
│   ├── bible/           # Bible data
│   └── database.db      # SQLite database
│
├── models/              # AI models
│   ├── sdxl/
│   ├── piper/
│   └── whisper/
│
├── generated/           # Output files
│   ├── backgrounds/
│   ├── audio/
│   ├── timestamps/
│   ├── subtitles/
│   ├── final/
│   └── uploaded/
│
└── logs/                # Application logs
```

## Development

### Adding New Features

1. Modify modules in `src/modules/`
2. Update `config.yaml` with new settings
3. Test with `./run.sh test`
4. Generate test video with `./run.sh generate 1`

### Custom Prompts

Edit `config.yaml`:

```yaml
prompts:
  themes:
    custom_theme: "your custom SDXL prompt here"
```

Then modify `video_generator.py` to use your theme.

## Performance

**Typical Generation Times (RTX 4070):**
- Background video: 1-2 minutes
- TTS generation: 2-5 seconds
- Word alignment: 5-10 seconds
- Subtitle rendering: 10-20 seconds
- Video composition: 5-10 seconds
- **Total: 2-4 minutes per video**

**Storage:**
- Per video: ~500MB (all intermediate files)
- Per video (final only): ~30-50MB
- Enable cleanup to save space

## Cost

**100% Free (after hardware)**
- All AI models: Open source
- YouTube API: Free (with quota limits)
- Total monthly cost: $0 (+ electricity)

**Hardware Investment:**
- RTX 4070: ~$600
- Or RTX 3060 12GB: ~$300 (used)
- Or cloud GPU: ~$0.50/hour

## License

[Your License Here]

## Credits

- **AI Models:**
  - Stable Diffusion XL by Stability AI
  - Piper TTS (install separately)
  - WhisperX

- **APIs:**
  - pythonbible for Bible data
  - YouTube Data API v3

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Disclaimer

This tool is for creating religious/spiritual content. Ensure you comply with:
- YouTube's Terms of Service
- YouTube Shorts requirements
- Copyright laws for Bible translations
- Fair use guidelines

Default uses KJV (public domain). Check license for other translations.
