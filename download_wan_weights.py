#!/usr/bin/env python3
"""
Download Alibaba Wan T2V (text-to-video) model weights from Hugging Face.
Uses huggingface_hub snapshot_download (no external CLI dependency).
"""
import os
import sys
from pathlib import Path
import subprocess

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None


def _is_venv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _ensure_hf_available():
    """
    Ensure huggingface_hub is importable. Prefer running inside the local venv
    if it exists; otherwise, attempt to install with pip (adding
    --break-system-packages when not in a venv to bypass PEP 668 managed envs).
    """
    global snapshot_download
    if snapshot_download is not None:
        return

    repo_root = Path(__file__).resolve().parent
    venv_python = repo_root / "venv" / "bin" / "python"

    # If a venv exists and we are not using it, re-exec inside it.
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        print(f"Re-running inside virtualenv: {venv_python}")
        os.execv(str(venv_python), [str(venv_python), __file__])

    print("huggingface_hub not found. Installing 'huggingface_hub[cli]'...")
    pip_cmd = [sys.executable, "-m", "pip", "install", "huggingface_hub[cli]"]
    if not _is_venv():
        pip_cmd.append("--break-system-packages")

    try:
        subprocess.check_call(pip_cmd)
        from huggingface_hub import snapshot_download as _snap_dl  # type: ignore
        snapshot_download = _snap_dl
    except Exception as e:
        print(f"✗ Failed to install huggingface_hub: {e}")
        print("If you prefer isolation, create/activate the venv with:")
        print("  python3 -m venv venv && source venv/bin/activate")
        sys.exit(1)


def main():
    _ensure_hf_available()

    print("=" * 60)
    print("Alibaba Wan Text-to-Video Model Downloader")
    print("=" * 60)
    print()
    print("Wan models are ACTUAL text-to-video generators from Alibaba.")
    print("(Note: Qwen3-VL is different - it's vision-to-text, not video generation)")
    print()
    print("Available models:")
    print("  1) Wan2.1-T2V-1.3B (~3GB) - Consumer GPU friendly (8GB VRAM)")
    print("     Generates 480p videos in ~4 minutes on RTX 4090")
    print()
    print("  2) Wan2.1-T2V-14B (~28GB) - High quality (24GB+ VRAM with optimization)")
    print("     Generates 720p videos, needs powerful GPU")
    print()

    global snapshot_download
    if snapshot_download is None:
        print("huggingface_hub not found. Installing 'huggingface_hub[cli]'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub[cli]"])
            from huggingface_hub import snapshot_download as _snap_dl  # type: ignore
            snapshot_download = _snap_dl
        except Exception as e:
            print(f"✗ Failed to install huggingface_hub: {e}")
            sys.exit(1)

    try:
        choice = input("Select model (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nDownload cancelled.")
        return

    models = {
        "1": ("Wan-AI/Wan2.1-T2V-1.3B", "~3GB", "1.3B"),
        "2": ("Wan-AI/Wan2.1-T2V-14B", "~28GB", "14B"),
    }

    if choice not in models:
        print(f"Invalid choice: {choice}")
        sys.exit(1)

    model_id, size, model_size = models[choice]
    local_dir = Path("models/wan2.1-weights").resolve()

    # Remove existing weights to avoid mixing sizes
    if local_dir.exists():
        print(f"\nRemoving existing weights at {local_dir} to avoid size mismatches...")
        import shutil
        shutil.rmtree(local_dir, ignore_errors=True)

    print()
    print(f"Downloading: {model_id}")
    print(f"Size: {size}")
    print(f"Destination: {local_dir}")
    print()
    print("This may take 5-60 minutes depending on your internet connection...")
    print("Download can be resumed if interrupted (Ctrl+C to cancel)")
    print()

    try:
        local_dir.mkdir(parents=True, exist_ok=True)

        token = os.getenv("HF_TOKEN")
        print("Starting download via huggingface_hub (snapshot_download)...\n")
        snapshot_download(
            repo_id=model_id,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
            token=token,
            resume_download=True,
            max_workers=4,
        )

        print()
        print("=" * 60)
        print(f"✓ Successfully downloaded {model_id}")
        print(f"✓ Location: {local_dir}")
        print("=" * 60)
        print()

        # Update config.yaml if it exists
        config_file = Path("config.yaml")
        if config_file.exists():
            try:
                import re
                content = config_file.read_text()

                # Add or update wan section
                content = re.sub(
                    r'(size:\s*)"[^"]*"',
                    f'\\1"{model_size}"',
                    content
                )
                config_file.write_text(content)
                print(f"✓ Updated config.yaml with model size: {model_size}")

                print()
            except Exception as e:
                print(f"⚠ Could not update config.yaml: {e}")
                print(f"Please manually update config.yaml with:")
                print(f"  models.wan.size: \"{model_size}\"")
                print()

        print("Next steps:")
        print("1. Ensure Wan repository is cloned:")
        print("   git clone https://github.com/Wan-Video/Wan2.1.git models/wan2.1")
        print()
        print("2. Install Wan dependencies:")
        print("   cd models/wan2.1 && pip install -r requirements.txt")
        print()
        print("3. Set video.backend: \"wan\" in config.yaml")
        print()
        print("4. Test with: ./run.sh generate 1")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠ Download cancelled by user")
        print("Download progress has been saved and can be resumed by running this script again.")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Unexpected error: {e}")
        print("=" * 60)
        print()
        print("Troubleshooting:")
        print("1) Ensure internet access and enough disk space.")
        print("2) If authentication needed, set HF_TOKEN env var.")
        print("3) Upgrade huggingface_hub: pip install -U 'huggingface_hub[cli]'")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
