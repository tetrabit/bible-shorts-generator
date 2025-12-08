# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Bible Shorts Generator: Automated YouTube Shorts creator that generates vertical videos (1080x1920) from Bible verses using Alibaba Wan text-to-video, Piper TTS, WhisperX alignment, and subtitle overlay.

## Architecture

**Video Backend**: Wan T2V (Alibaba text-to-video) only. Qwen3-VL is NOT used for video generation (it's vision-to-text). The old SDXL code has been removed.

**Pipeline Flow** (`src/main.py` BibleShortsGenerator class):
1. **Verse Selection** (`verse_selector.py`) - Random or sequential mode, word count filtered
2. **Video Generation** (`wan_video_generator.py`) - Subprocess call to Wan repo's generate.py
3. **TTS Audio** (`tts_engine.py`) - Piper speech synthesis
4. **Alignment** (`word_aligner.py`) - WhisperX for word-level timestamps (models freed after use)
5. **Subtitles** (`subtitle_renderer.py`) - Word highlighting overlay (skippable via config)
6. **Composition** (`video_composer.py`) - FFmpeg merges background + audio + subtitles
7. **Upload** (`youtube_uploader.py`) - YouTube API v3, optional archival/cleanup

**Database** (`database.py`): SQLite at `data/database.db` tracks videos (status, paths, retry count), verses (usage), statistics (daily), progress (sequential mode).

**Scheduler** (`scheduler.py`): APScheduler blocking scheduler with jobs:
- Generation: interval-based (default 2h)
- Upload: cron-based at configured times
- Retry: every 4h for failed videos
- Cleanup: daily at 3 AM
- DB vacuum: weekly on Sunday at 4 AM

## Setup & Dependencies

- **System**: Python 3.10+, FFmpeg, CUDA GPU (8GB+ VRAM for Wan 1.3B), Piper binary
- **Setup**: `./setup.sh` creates venv, installs requirements, clones Wan repo, optionally downloads weights (~3GB for 1.3B or ~28GB for 14B), initializes DB, downloads Bible data
- **PyTorch**: Uses CUDA 12.1 build from PyTorch index (specified in requirements.txt via --extra-index-url)
- **WhisperX**: Installed from git repositories (OpenAI Whisper + m-bain/whisperX)
- **Wan Dependencies**: Separate requirements in `models/wan2.1/requirements.txt` (flash_attn is optional and may fail)
- **YouTube Auth**: Place `client_secrets.json` in repo root, run `./run.sh auth` to generate OAuth token

## Common Commands

```bash
# Development
./run.sh test              # Test all components (config, DB, FFmpeg, Piper, Wan)
./run.sh generate <N>      # Generate N videos (default: 1)
./run.sh upload <ID>       # Upload video by database ID
./run.sh schedule          # Start scheduler (generation + upload + retry + maintenance)

# Status & debugging
./run.sh stats             # Show statistics (last 7 days, status counts, mode)
./run.sh progress          # Show sequential mode progress
./run.sh retry             # Manually retry failed videos (max 3 attempts)
./run.sh logs [file]       # Tail logs (default: app.log)

# Database
./run.sh db shell          # Open SQLite shell
./run.sh db videos         # List recent videos
./run.sh db ready          # List videos ready to upload

# Configuration
./run.sh mode <random|sequential>  # Set verse selection mode
./run.sh clean             # Delete generated intermediate files
```

## Module Organization

**Core Orchestrator** (`src/main.py`):
- `BibleShortsGenerator` class coordinates entire pipeline
- CLI argument parsing for all operations
- Manages component initialization and lifecycle
- Progress tracking via Rich library

**Pipeline Modules** (`src/modules/`):
- `database.py`: SQLite interface, all DB operations, schema initialization
- `verse_selector.py`: Random/sequential verse selection with word count filtering
- `wan_video_generator.py`: Subprocess wrapper for Wan T2V
- `tts_engine.py`: Piper TTS integration
- `word_aligner.py`: WhisperX wrapper with model lifecycle management
- `subtitle_renderer.py`: OpenCV-based subtitle video generation with word highlighting
- `video_composer.py`: FFmpeg composition (overlay subtitles on background + audio)
- `youtube_uploader.py`: YouTube Data API v3, OAuth flow, metadata templating
- `timing_analyzer.py`: Duration calculations based on word count and speaking rate

**Utilities** (`src/utils/`):
- `logger.py`: Loguru-based logging setup
- `ffmpeg_utils.py`: FFmpeg availability checks and helper functions
- `file_manager.py`: Archive, cleanup, storage management

**Configuration** (`src/config.py`):
- Loads `config.yaml` using OmegaConf
- Provides dot-notation access to config values

## Configuration (`config.yaml`)

- `video.backend`: Must be `"wan"` (only backend)
- `video.skip_subtitles`: Set `true` to skip subtitle rendering (debug video+audio only)
- `models.wan.size`: `"1.3B"` (8GB VRAM) or `"14B"` (24GB+ VRAM)
- `models.wan.resolution`: `"832*480"` (1.3B) or `"1280*720"` (14B)
- `models.wan.offload_model`: Memory optimization (recommended `true`)
- `bible.books`: List of books to use for verse selection
- `bible.max_words`: Max words per verse (affects duration, <7s recommended)
- `youtube.upload_schedule.times`: Cron times for automated uploads
- `scheduler.generation_interval`: Interval between batch generation runs
- `storage.cleanup_after_upload`: Auto-delete intermediate files post-upload

## File Structure

```
models/
  wan2.1/              # Wan T2V repository (cloned from GitHub)
  wan2.1-weights/      # Model weights (downloaded via huggingface-cli)
  piper/               # Piper TTS voices (auto-downloaded)
  whisper/             # WhisperX model checkpoints (auto-downloaded)
generated/
  backgrounds/         # Wan-generated videos (.mp4)
  audio/               # Piper TTS audio (.wav)
  timestamps/          # WhisperX alignments (.json)
  subtitles/           # Subtitle overlays (.mov, ProRes 4444)
  final/               # Final composed videos (.mp4)
  uploaded/            # Archived after upload (if enabled)
data/
  database.db          # SQLite database
  bible/               # Bible data (KJV JSON)
logs/
  app.log              # Main application log
  upload.log           # YouTube upload log
src/
  main.py              # Main orchestrator (BibleShortsGenerator)
  config.py            # Config loader
  scheduler.py         # APScheduler jobs
  modules/             # Pipeline components
  utils/               # Logger, FFmpeg, file management
```

## Key Implementation Details

**Wan Integration**: Subprocess call to `models/wan2.1/generate.py` with task=t2v-{size}, resolution, checkpoint dir, and memory flags (offload_model, t5_cpu). Process runs in Wan repo directory with current venv's Python. Output parsed from `models/wan2.1/outputs/` (most recent .mp4).

**WhisperX Memory Management**: Models explicitly unloaded after alignment (`aligner.unload_models()`) in a finally block to free GPU/CPU memory between videos.

**VRAM Check**: Before Wan generation, uses `torch.cuda.mem_get_info()` to check free VRAM (requires ~8GB for 1.3B). Raises RuntimeError if insufficient.

**Retry Logic**: Videos track `retry_count` (max 3). Status flow: pending → processing → ready/failed. Failed videos can be retried via `--retry` or scheduler job (resets status to pending, increments retry_count).

**Sequential Mode**: DB stores current position (book/chapter/verse) in progress table. Progress saved after each successful verse, enabling resume after shutdown.

**Video Status Transitions**: pending (initial) → processing (during generation) → ready (success) → uploaded (after YouTube upload). Failed videos remain in failed status until retry.

**Composition Modes**: Standard mode uses FFmpeg to overlay subtitle video (ProRes 4444 .mov) on background with audio. Debug mode (`skip_subtitles: true`) uses simple composition (background + audio only) via `compose_simple()`.

## Troubleshooting

- **Wan unavailable**: Ensure repo cloned at `models/wan2.1` and weights at `models/wan2.1-weights`. Check with `ls models/wan2.1/generate.py` and `ls models/wan2.1-weights/`. Run `python3 download_wan_weights.py` if needed.
- **Wan dependencies**: Install with `pip install -r models/wan2.1/requirements.txt`. Note: flash_attn is optional and may fail to install.
- **OOM errors**: Set `offload_model: true` and ensure `t5_cpu` flag is enabled in Wan command. Close GPU apps, or use 1.3B model instead of 14B.
- **Piper missing**: Install Piper binary separately (auto-download no longer works with Python 3.13). Test with `./run.sh test`.
- **WhisperX errors**: Check logs, rerun `./setup.sh` to refresh dependencies. WhisperX installs from git repositories.
- **Generation fails silently**: Check `logs/app.log` for detailed stderr/stdout from Wan subprocess. Wan outputs go to its own outputs directory first.
- **Database locked**: Scheduler uses BlockingScheduler - only one instance should run at a time.
- **YouTube auth fails**: Ensure `client_secrets.json` exists in repo root, then run `./run.sh auth` to generate token.
