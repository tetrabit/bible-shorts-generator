"""Word-level timestamp alignment using WhisperX"""
import json
from collections import defaultdict, OrderedDict
from pathlib import Path
from typing import List, Dict, Any

import whisperx
import torch
from pyannote.audio.core.model import Introspection
from pyannote.audio.core.task import (
    Specifications,
    Problem,
    Resolution,
    Task,
    TrainDataset,
    ValDataset,
    UnknownSpecificationsError,
)
from omegaconf import dictconfig, listconfig
from omegaconf.base import ContainerMetadata, Metadata
from omegaconf.nodes import AnyNode
from torch.torch_version import TorchVersion


class WordAligner:
    """Extract word-level timestamps using WhisperX forced alignment"""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.align_model = None
        self.metadata = None
        self.device = config.models['whisper']['device']
        self.compute_type = config.models['whisper']['compute_type']
        self._cpu_forced = False
        self._register_safe_globals()

    def load_model(self):
        """Load WhisperX model (lazy loading)"""
        if self.model is not None:
            return

        self._ensure_device_ready()

        print("Loading Whisper model...")
        try:
            self.model = whisperx.load_model(
                self.config.models['whisper']['model_size'],
                device=self.device,
                compute_type=self.compute_type
            )
        except RuntimeError as e:
            if "cudnn" in str(e).lower() and self.device == "cuda":
                print("CUDA/cuDNN unavailable; falling back to CPU for Whisper.")
                self.device = "cpu"
                self.compute_type = "float32"
                self.model = whisperx.load_model(
                    self.config.models['whisper']['model_size'],
                    device=self.device,
                    compute_type=self.compute_type
                )
            else:
                raise
        print("Whisper model loaded")

    def load_align_model(self, language="en"):
        """Load alignment model"""
        if self.align_model is not None:
            return

        self._ensure_device_ready()

        print("Loading alignment model...")
        try:
            self.align_model, self.metadata = whisperx.load_align_model(
                language_code=language,
                device=self.device
            )
        except RuntimeError as e:
            if "cudnn" in str(e).lower() and self.device == "cuda":
                print("CUDA/cuDNN unavailable; falling back to CPU for aligner.")
                self.device = "cpu"
                self.compute_type = "float32"
                self.align_model, self.metadata = whisperx.load_align_model(
                    language_code=language,
                    device=self.device
                )
            else:
                raise
        print("Alignment model loaded")

    def align(self, audio_path: str, text: str, output_path: str, _retry: bool = True) -> str:
        """
        Get word-level timestamps for audio

        Args:
            audio_path: Path to audio file
            text: Expected text (for validation)
            output_path: Path to save timestamps JSON

        Returns:
            output_path: Path to saved timestamps file
        """
        try:
            self.load_model()
            self.load_align_model()

            print("Loading audio...")
            audio = whisperx.load_audio(audio_path)

            print("Transcribing with Whisper...")
            result = self.model.transcribe(audio, batch_size=16)

            print("Performing forced alignment...")
            result_aligned = whisperx.align(
                result["segments"],
                self.align_model,
                self.metadata,
                audio,
                device=self.device,
                return_char_alignments=False
            )
        except RuntimeError as e:
            if "cudnn" in str(e).lower() and self.device == "cuda" and _retry:
                print("cuDNN error during WhisperX run; retrying on CPU.")
                self.unload_models()
                self.device = "cpu"
                self.compute_type = "float32"
                return self.align(audio_path, text, output_path, _retry=False)
            raise

        # Extract word timestamps
        words = []
        for segment in result_aligned["segments"]:
            if "words" in segment:
                for word_info in segment["words"]:
                    words.append({
                        "word": word_info.get("word", "").strip(),
                        "start": word_info.get("start", 0.0),
                        "end": word_info.get("end", 0.0)
                    })

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(words, f, indent=2)

        print(f"Timestamps saved to: {output_path}")
        print(f"Total words: {len(words)}")

        return output_path

    def unload_models(self):
        """Unload models to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.align_model is not None:
            del self.align_model
            self.align_model = None
        self.metadata = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _register_safe_globals(self):
        """
        Torch 2.6+ defaults to weights_only loading. WhisperX checkpoints rely on
        OmegaConf objects, so we allowlist them to avoid unsafe-load errors.
        """
        try:
            torch.serialization.add_safe_globals([
                listconfig.ListConfig,
                dictconfig.DictConfig,
                ContainerMetadata,
                Metadata,
                Any,
                list,
                dict,
                tuple,
                set,
                type(None),
                defaultdict,
                OrderedDict,
                str,
                int,
                float,
                bool,
                AnyNode,
                TorchVersion,
                Introspection,
                Specifications,
                Problem,
                Resolution,
                Task,
                TrainDataset,
                ValDataset,
                UnknownSpecificationsError,
            ])
        except Exception:
            # Best-effort; if this fails we still proceed and let upstream handle errors
            pass

    def _ensure_device_ready(self):
        """Fallback to CPU when CUDA or cuDNN is not available."""
        if self.device != "cuda":
            return

        # Force WhisperX to CPU to avoid environments without full cuDNN runtimes
        if not self._cpu_forced:
            print("Using CPU for WhisperX to avoid CUDA/cuDNN runtime issues.")
        self.device = "cpu"
        self.compute_type = "float32"
        self._cpu_forced = True
