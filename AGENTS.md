# Agents Guide

## What changed recently
- Wan 1.3B pipeline: falls back to PyTorch SDPA if FlashAttention is missing; looks for outputs in `models/wan2.1/outputs` or repo root.
- Wan weights: `download_wan_weights.py` now clears `models/wan2.1-weights` before downloading to avoid mixed-size checkpoints.
- Whisper aligner: default to `base` on CPU (float32) to dodge cuDNN issues; switch back to CUDA once cuDNN is healthy.
- Accelerate: install in the venv for faster/lower-memory model loading (`venv/bin/pip install --upgrade "accelerate>=0.30.1"`).

## How to generate
1) Ensure Wan repo + 1.3B weights exist (`models/wan2.1`, `models/wan2.1-weights`).
2) Config: `models.wan.size: "1.3B"`, `models.wan.resolution: "480*832"` (vertical for Shorts).
3) Run: `./run.sh generate 1` → final video in `generated/final/<verse_id>.mp4`.

## Troubleshooting quick hits
- Size mismatch errors: re-run `python3 download_wan_weights.py` (option 1) to refresh weights.
- FlashAttention missing: expect slower generation; optional to install FA2/FA3 for speed.
- Whisper errors about model name: ensure `whisper.model_size` is a valid Whisper id (e.g., `base`, `small`).
- cuDNN load errors in WhisperX: keep `device: "cpu"` until GPU stack is fixed, then set back to `cuda`/`float16`.
