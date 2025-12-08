# Bible Shorts Generator (Wan-only)

Generates YouTube Shorts (vertical 1080x1920, <7s) from Bible verses using Alibaba Wan text-to-video, Piper TTS, WhisperX alignment, subtitle overlay, and YouTube upload.

## Quick Start
- Prereqs: Python 3.10+, FFmpeg, CUDA GPU with ~8GB+ VRAM, Piper binary installed, Wan repo + weights in `models/wan2.1` and `models/wan2.1-weights`.
- Setup: `./setup.sh` (handles venv, deps, DB, bible data; prompts for Wan clone/weights).
- Auth YouTube: `./run.sh auth` (place `client_secrets.json` first).
- Generate: `./run.sh generate 1` → `generated/final/<verse_id>.mp4`
- Upload: `./run.sh upload <video_id>`
- Schedule: `./run.sh schedule` (gen every 2h, uploads at configured times, retries failures).

### Wan 1.3B notes
- Use resolution `832*480` (or `480*832`) with `models.wan.size: "1.3B"`; `1280*720` is only for 14B.
- Re-download weights if you see size-mismatch errors: `python3 download_wan_weights.py` (option 1) will clear the folder first.
- Install accelerate in the venv to speed loading: `venv/bin/pip install --upgrade "accelerate>=0.30.1"`.
- If FlashAttention isn’t available, the code falls back to PyTorch SDPA (slower but works).

## Config (`config.yaml`)
- `video.backend: "wan"` (only backend)
- `models.wan`: repo/model paths, size (`1.3B` default), resolution, offload flags.
- `text`/`bible`: word limits, speaking rate, font path, book list.
- `youtube`: title/description templates, schedule.

## Commands
- `./run.sh generate N` – batch generate
- `./run.sh upload ID` – upload ready video
- `./run.sh schedule` – run generator/uploader/retry/cleanup jobs
- `./run.sh stats` | `progress` | `retry` | `logs` | `db ...`

## Pipeline
1) Verse selection (random/sequential, DB-tracked, word count filter)  
2) Wan T2V background generation  
3) Piper TTS audio  
4) WhisperX alignment (freed after use)  
5) Subtitle render (word highlighting)  
6) FFmpeg compose  
7) YouTube upload + optional archive/cleanup

## Troubleshooting
- Wan unavailable: ensure repo/weights exist and `pip install -r models/wan2.1/requirements.txt` inside venv.
- VRAM: needs ~8GB free for 1.3B; clear GPU memory or use larger GPU for 14B.
- Piper missing: install Piper binary; voices auto-download to `models/piper/`.
- WhisperX errors: rerun setup to refresh deps/checkpoints.

## Structure (key)
- `config.yaml`, `run.sh`, `setup.sh`, `download_wan_weights.py`
- `src/main.py` pipeline, `modules/` (database, verse selection, Wan generator, TTS, aligner, subtitles, composer, uploader), `utils/` (logger, ffmpeg, files)
- `models/wan2.1` repo, `models/wan2.1-weights` checkpoints, `generated/`, `data/database.db`, `logs/`
