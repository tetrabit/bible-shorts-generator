# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bible Shorts Generator is an automated system that creates YouTube Shorts (vertical 1080x1920 videos, <7 seconds) from Bible verses using local AI models. The system is completely headless and terminal-based - no GUI required.

## System Architecture

### Pipeline Flow

The system follows a sequential pipeline architecture:

1. **Verse Selection** → Filters Bible verses by word count (5-18 words) to ensure <7 second duration
2. **Background Generation** → SDXL generates themed images, composed into video with Ken Burns effect
3. **TTS Generation** → Piper TTS creates natural speech audio from verse text
4. **Word Alignment** → WhisperX performs forced alignment for word-level timestamps
5. **Subtitle Rendering** → Creates overlay video with synchronized text highlighting
6. **Video Composition** → FFmpeg merges background, audio, and subtitles into final video
7. **YouTube Upload** → Automated upload via YouTube Data API v3
8. **Scheduling** → APScheduler manages batch generation and timed uploads

### Key Components

**AI Models (all local, no cloud APIs):**
- SDXL: Image generation for backgrounds
- Piper TTS: Text-to-speech synthesis (CPU-friendly)
- WhisperX: Word-level timestamp extraction via forced alignment

**Data Flow:**
- Config: `config.yaml` drives all behavior (video specs, prompts, scheduling)
- Database: SQLite tracks generated videos, upload queue, and statistics
- Storage: Generated assets in `generated/{backgrounds,audio,timestamps,subtitles,final,uploaded}`

**Module Responsibilities:**
- `verse_selector.py`: Random verse selection with word count filtering
- `timing_analyzer.py`: Duration estimation (words ÷ speaking_rate)
- `video_generator.py`: SDXL image generation + Ken Burns video creation
- `tts_engine.py`: Piper TTS wrapper
- `word_aligner.py`: WhisperX forced alignment wrapper
- `subtitle_renderer.py`: Frame-by-frame subtitle overlay creation with word highlighting
- `video_composer.py`: FFmpeg orchestration for final composite
- `youtube_uploader.py`: YouTube Data API v3 client with OAuth2
- `database.py`: SQLite operations with context managers

## Development Setup

```bash
# Initial setup
./setup.sh  # Creates venv, installs deps, downloads models, initializes DB

# Authentication (one-time)
python auth.py  # Generates YouTube OAuth tokens → .env

# Configuration
cp .env.example .env  # Add YouTube API credentials
vi config.yaml        # Customize video settings, prompts, schedule
```

## Running the System

```bash
# Generate videos
./run.sh generate 1    # Generate single video (testing)
./run.sh generate 5    # Generate batch of 5 videos

# Upload videos
./run.sh upload 123    # Upload video ID 123 to YouTube

# Start scheduler (runs indefinitely)
./run.sh schedule      # Auto-generates and uploads on schedule
```

## Configuration

All behavior is controlled via `config.yaml`:

- **Video specs**: Resolution (1080x1920), FPS (30), duration limit (7s), codec settings
- **Text rendering**: Font, size, colors, outline, positioning, word highlighting
- **Bible filtering**: Allowed books, word count range (5-18 words)
- **AI models**: Device (cuda/cpu), precision (float16/32), model parameters
- **Prompts**: SDXL prompt templates with thematic variations (hope, peace, strength, etc.)
- **YouTube**: Upload schedule times, metadata templates, privacy settings
- **Scheduler**: Generation interval (2h), batch size (3), queue size (10)

## Critical Constraints

1. **7-second limit**: Enforced by `max_words: 18` and `speaking_rate: 3.0` (words/sec)
2. **Vertical format**: 1080x1920 (9:16 aspect ratio) for YouTube Shorts
3. **Local-only**: All AI runs locally, no cloud APIs (except YouTube upload)
4. **Word-level timing**: Requires TTS → WhisperX alignment hybrid (TTS engines don't provide timestamps)
5. **YouTube quota**: 10,000 points/day default, 1,600 per upload = ~6 videos/day

## Database Schema

SQLite database tracks:
- `videos`: Full pipeline state (verse_id, paths to all assets, youtube_id, status)
- `upload_queue`: Scheduled uploads with retry logic
- `statistics`: Daily metrics (videos generated, uploaded, errors)

Status flow: `pending` → `processing` → `ready` → `uploaded` (or `failed`)

## FFmpeg Usage

Heavy reliance on FFmpeg for:
- Ken Burns effect (zoom + pan on static images)
- Subtitle overlay compositing
- Audio mixing
- Final encode with specific YouTube Shorts requirements

All FFmpeg operations wrapped in `ffmpeg_utils.py` and `video_composer.py`.

## Hardware Requirements

**Minimum**:
- NVIDIA GPU with 12GB VRAM (RTX 3060) for SDXL
- Piper TTS runs on CPU

**CPU-only mode**:
- Set `models.sdxl.device: "cpu"` and `models.sdxl.dtype: "float32"` in config.yaml
- Significantly slower video generation (10-30 min vs 2-5 min)

## Monitoring

```bash
# Live logs
tail -f logs/app.log

# Database queries
sqlite3 data/database.db "SELECT * FROM videos WHERE status='ready';"
sqlite3 data/database.db "SELECT * FROM statistics ORDER BY date DESC LIMIT 7;"

# Systemd service (if installed)
sudo systemctl status bible-shorts.service
sudo journalctl -u bible-shorts.service -f
```

## Dependencies Note

- PyTorch with CUDA 12.1 support
- WhisperX installed from git (not PyPI)
- Requires system FFmpeg binary (not Python wrapper)
- Piper TTS downloads voice models on first run to `models/piper/`
