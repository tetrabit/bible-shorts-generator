# Wan T2V Setup Guide

## What is Wan?

**Wan** is Alibaba's actual text-to-video generation model. Unlike Qwen3-VL (which analyzes videos to produce text), Wan generates videos from text prompts.

- **Wan2.1-T2V-1.3B**: Consumer GPU friendly (~3GB, 8GB VRAM, generates 480p in ~4 min)
- **Wan2.1-T2V-14B**: High quality (~28GB, 24GB+ VRAM, generates 720p)

## Quick Setup (Recommended: 1.3B Model)

### Step 1: Install Hugging Face CLI

```bash
source venv/bin/activate
pip install "huggingface_hub[cli]"
```

### Step 2: Download Wan Model Weights

```bash
python3 download_wan_weights.py
```

Select option **1** for the 1.3B model (consumer GPU friendly).

This will download ~3GB to `models/wan2.1-weights/`.

### Step 3: Clone Wan Repository

```bash
git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1
```

### Step 4: Install Wan Dependencies

```bash
cd models/wan2.1
pip install -r requirements.txt
cd ../..
```

**Note:** If `flash_attn` installation fails, that's OK - install the other packages first and continue.

### Step 5: Configure Backend

Your `config.yaml` is already set to use Wan! Verify it says:

```yaml
video:
  backend: "wan"  # Using Wan T2V

models:
  wan:
    size: "1.3B"
    resolution: "480*832"  # vertical for Shorts (use 832*480 for horizontal; falls back to supported if you pick an invalid size)
    offload_model: true  # Memory optimization
```

### Step 6: Test Generation

```bash
./run.sh generate 1
```

## Expected Performance

**Wan2.1-T2V-1.3B (Consumer GPU):**
- VRAM: 8GB minimum
- Generation Time: ~4 minutes per 5-second video (on RTX 4090)
- Resolution: 480p (480x832 vertical for Shorts; 832x480 horizontal). If you pick an unsupported size, the app falls back to a supported one (prefers vertical for Shorts).
- Quality: Good for social media shorts

**Wan2.1-T2V-14B (High-End GPU):**
- VRAM: 24GB+ with optimization, 80GB without
- Generation Time: Faster with more GPUs
- Resolution: 720p (1280x720)
- Quality: Excellent, cinematic

## Troubleshooting

### Out of Memory

If you get CUDA OOM errors:

1. Ensure `offload_model: true` in config.yaml
2. Close other applications using GPU
3. Try the 1.3B model if using 14B

### Wan Repository Not Found

```bash
git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1
cd models/wan2.1
pip install -r requirements.txt
```

### Model Weights Not Found

```bash
python3 download_wan_weights.py
```

Select your preferred model size and let it download.

### Generation Fails

Check the logs:

```bash
tail -f logs/app.log
```

Common issues:
- Missing dependencies: `cd models/wan2.1 && pip install -r requirements.txt`
- Wrong Python version: Wan requires Python 3.8+
- CUDA not available: Check `nvidia-smi`

## SDXL Support
SDXL support was removed; Wan is the only backend.

## Advanced Configuration

### Using 14B Model

```yaml
# config.yaml
models:
  wan:
    size: "14B"
    resolution: "1280*720"
```

Download weights:

```bash
python3 download_wan_weights.py
# Select option 2
```

### Multi-GPU Acceleration

If you have multiple GPUs:

```bash
# Edit models/wan2.1/generate.py to use torchrun
torchrun --nproc_per_node=2 models/wan2.1/generate.py ...
```

See Wan documentation for details.

## Resources

- **Wan2.1 GitHub**: https://github.com/Wan-Video/Wan2.1
- **Hugging Face Models**: https://huggingface.co/Wan-AI
- **Paper**: https://labitobi.github.io/Wan2.1/

## Sources

- [Alibaba Wan Models](https://www.alibabacloud.com/blog/alibaba-cloud-open-sources-its-ai-models-for-video-generation_602025)
- [Wan2.1-T2V-1.3B on Hugging Face](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B)
- [Wan2.1-T2V-14B on Hugging Face](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B)
- [Top Open Source Text-to-Video Models 2025](https://www.siliconflow.com/articles/en/best-open-source-text-to-video-models)
