# Quick Start (Wan-only)

1) **Install system deps**  
   `sudo apt-get update && sudo apt-get install -y python3.10 python3-venv ffmpeg git`

2) **Clone & setup**  
   ```bash
   git clone <your-repo-url> bible-shorts-generator
   cd bible-shorts-generator
   ./setup.sh
   ```
   - Creates venv, installs Python deps, DB, bible data.  
   - Prompts to clone Wan repo/download weights (~3GB for 1.3B).  
   - Piper binary must be installed manually (Python 3.13 compatible).

3) **YouTube credentials**  
   Place `client_secrets.json` in repo → run `./run.sh auth`.

4) **Generate a video**  
   `./run.sh generate 1` → output `generated/final/<verse_id>.mp4`

5) **Upload**  
   `./run.sh upload <video_id>` (use `./run.sh db ready` to list).

6) **Automation**  
   `./run.sh schedule` (gen every 2h, uploads at configured times, retries failures, cleanup/vacuum jobs).

Troubleshooting (Wan 1.3B):
- Ensure `models.wan.size: "1.3B"` and `models.wan.resolution: "480*832"` (vertical for Shorts; horizontal option is `832*480`).
- If you hit size-mismatch errors, re-download weights: `python3 download_wan_weights.py` (option 1 clears the folder first).
- Install accelerate inside the venv for faster/leaner loads: `venv/bin/pip install --upgrade "accelerate>=0.30.1"`.
- FlashAttention is optional; if not installed, the generator falls back to PyTorch SDPA (slower).

Config tips (`config.yaml`):
- `video.backend: "wan"` (only option).
- `models.wan.size`: `"1.3B"` (default) or `"14B"` if you have VRAM; adjust `resolution`.
- Increase `bible.max_words` if you need longer verses (<7s recommended).
- Set `youtube.privacy` to `"private"` while testing.
