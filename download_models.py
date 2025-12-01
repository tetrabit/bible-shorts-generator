#!/usr/bin/env python3
"""
Download required AI models for Bible Shorts Generator
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("Bible Shorts Generator - Model Download Script")
print("=" * 60)
print()

# Set environment variables for model storage
os.environ['TORCH_HOME'] = './models'
os.environ['HF_HOME'] = './models'

def download_sdxl():
    """Download Stable Diffusion XL model"""
    print("\n[1/3] Downloading Stable Diffusion XL...")
    print("This may take 10-30 minutes depending on your internet speed.")
    print("Model size: ~14 GB")

    try:
        from diffusers import StableDiffusionXLPipeline
        import torch

        model_id = "stabilityai/stable-diffusion-xl-base-1.0"

        print(f"Downloading from: {model_id}")

        # Download model
        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            cache_dir="./models/sdxl"
        )

        print("✓ SDXL model downloaded successfully!")
        return True

    except Exception as e:
        print(f"✗ Failed to download SDXL: {e}")
        return False


def download_whisper():
    """Download Whisper model for word alignment"""
    print("\n[2/3] Downloading Whisper model...")
    print("Model size: ~140 MB")

    try:
        import whisper

        model_size = "base"  # Options: tiny, base, small, medium, large
        print(f"Downloading Whisper {model_size} model...")

        model = whisper.load_model(
            model_size,
            download_root="./models/whisper"
        )

        print("✓ Whisper model downloaded successfully!")
        return True

    except Exception as e:
        print(f"✗ Failed to download Whisper: {e}")
        return False


def download_piper():
    """Download Piper TTS voice model"""
    print("\n[3/3] Downloading Piper TTS voice...")
    print("Model size: ~30 MB")

    try:
        import subprocess

        voice = "en_US-lessac-medium"
        models_dir = "./models/piper"

        Path(models_dir).mkdir(parents=True, exist_ok=True)

        print(f"Downloading voice: {voice}")

        # Download using piper command
        result = subprocess.run(
            [
                "piper",
                "--model", voice,
                "--download-dir", models_dir,
                "--data-dir", models_dir
            ],
            capture_output=True,
            text=True,
            input=""  # Empty input
        )

        print("✓ Piper TTS voice downloaded successfully!")
        return True

    except FileNotFoundError:
        print("✗ Piper not found. Install with: pip install piper-tts")
        return False
    except Exception as e:
        print(f"✗ Failed to download Piper voice: {e}")
        return False


def main():
    """Main download script"""

    # Check if models directory exists
    Path("./models").mkdir(exist_ok=True)

    print("Starting model downloads...")
    print("Total download size: ~14-15 GB")
    print()

    results = {
        'sdxl': download_sdxl(),
        'whisper': download_whisper(),
        'piper': download_piper()
    }

    print("\n" + "=" * 60)
    print("Download Summary:")
    print("=" * 60)

    for model, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"{model.upper():15} {status}")

    if all(results.values()):
        print("\n✓ All models downloaded successfully!")
        print("You can now run the Bible Shorts Generator.")
    else:
        print("\n✗ Some models failed to download.")
        print("Please check the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
