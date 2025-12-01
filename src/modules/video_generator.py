"""Video background generator using Stable Diffusion XL"""
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
import torch
from PIL import Image
import cv2
import numpy as np
from pathlib import Path
from typing import List
import random


class VideoGenerator:
    """Generates background videos using SDXL and Ken Burns effect"""

    def __init__(self, config):
        self.config = config
        self.pipe = None
        self.device = config.models['sdxl']['device']
        self.dtype = torch.float16 if config.models['sdxl']['dtype'] == 'float16' else torch.float32
        self.skip_sdxl = config.models['sdxl'].get('skip', False)

    def load_model(self):
        """Load SDXL model (lazy loading)"""
        if self.pipe is not None:
            return

        print("Loading SDXL model...")
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            self.config.models['sdxl']['model_id'],
            torch_dtype=self.dtype,
            use_safetensors=True,
            variant="fp16" if self.dtype == torch.float16 else None
        )

        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )

        self.pipe.to(self.device)

        # Use GPU fully during generation, but avoid keeping VRAM pinned after runs
        if self.device == "cuda":
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                pass  # xformers not available

        print("SDXL model loaded successfully")

    def generate_prompt(self, verse_text: str) -> str:
        """
        Generate SDXL prompt from verse content

        Args:
            verse_text: Verse text to analyze for themes

        Returns:
            prompt: Generated prompt for SDXL
        """
        # Simple theme detection based on keywords
        text_lower = verse_text.lower()
        theme = 'default'

        if any(word in text_lower for word in ['hope', 'light', 'dawn', 'morning']):
            theme = 'hope'
        elif any(word in text_lower for word in ['strength', 'power', 'mighty']):
            theme = 'strength'
        elif any(word in text_lower for word in ['peace', 'calm', 'rest', 'still']):
            theme = 'peace'
        elif any(word in text_lower for word in ['love', 'heart', 'beloved']):
            theme = 'love'
        elif any(word in text_lower for word in ['faith', 'believe', 'trust']):
            theme = 'faith'
        elif any(word in text_lower for word in ['wisdom', 'knowledge', 'understanding']):
            theme = 'wisdom'

        theme_prompt = self.config.prompts['themes'][theme]
        style = self.config.prompts['style']

        return f"{theme_prompt}, {style}"

    def generate_images(self, prompt: str, num_images: int = 4) -> List[Image.Image]:
        """
        Generate multiple images for video

        Args:
            prompt: SDXL prompt
            num_images: Number of images to generate

        Returns:
            List of PIL Images
        """
        self.load_model()

        images = []
        negative_prompt = self.config.prompts['negative']

        for i in range(num_images):
            print(f"Generating image {i+1}/{num_images}...")

            # Use different seeds for variety
            generator = torch.Generator(device=self.device).manual_seed(random.randint(0, 2**32 - 1))

            with torch.inference_mode():
                image = self.pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=self.config.models['sdxl']['num_inference_steps'],
                    guidance_scale=self.config.models['sdxl']['guidance_scale'],
                    width=self.config.video['width'],
                    height=self.config.video['height'],
                    generator=generator
                ).images[0]

            images.append(image)

            # Nudge CUDA allocator to release cached blocks between generations
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return images

    def create_ken_burns_video(
        self,
        images: List[Image.Image],
        duration: float,
        output_path: str
    ) -> str:
        """
        Create video with Ken Burns effect from images

        Args:
            images: List of PIL Images
            duration: Total video duration in seconds
            output_path: Path to save video

        Returns:
            output_path: Path to saved video
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fps = self.config.video['fps']
        total_frames = int(duration * fps)
        frames_per_image = total_frames // len(images)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (self.config.video['width'], self.config.video['height'])
        )

        for img_idx, img in enumerate(images):
            print(f"Processing image {img_idx+1}/{len(images)} for Ken Burns effect...")

            # Convert PIL to numpy array
            img_array = np.array(img)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            # Randomly choose zoom direction (in or out)
            zoom_in = random.choice([True, False])

            for frame_idx in range(frames_per_image):
                progress = frame_idx / frames_per_image

                # Ken Burns effect: slow zoom
                if zoom_in:
                    scale = 1.0 + (progress * 0.15)  # Zoom in 15%
                else:
                    scale = 1.15 - (progress * 0.15)  # Zoom out from 115% to 100%

                # Apply zoom
                h, w = img_array.shape[:2]
                new_h, new_w = int(h * scale), int(w * scale)
                scaled = cv2.resize(img_array, (new_w, new_h))

                # Pan effect: slight horizontal/vertical movement
                pan_x = int(progress * 20 * random.choice([-1, 1]))  # Pan up to 20px
                pan_y = int(progress * 20 * random.choice([-1, 1]))

                # Center crop to original size with pan
                target_h, target_w = self.config.video['height'], self.config.video['width']
                y = max(0, min((new_h - target_h) // 2 + pan_y, new_h - target_h))
                x = max(0, min((new_w - target_w) // 2 + pan_x, new_w - target_w))

                cropped = scaled[y:y+target_h, x:x+target_w]

                # Handle edge cases where crop might be smaller
                if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
                    cropped = cv2.resize(cropped, (target_w, target_h))

                writer.write(cropped)

        writer.release()
        print(f"Video saved to: {output_path}")
        return output_path

    def generate(self, verse_text: str, duration: float, output_path: str) -> str:
        """
        Main generation method: create complete background video

        Args:
            verse_text: Verse text for prompt generation
            duration: Video duration in seconds
            output_path: Path to save video

        Returns:
            output_path: Path to saved video
        """
        if self.skip_sdxl:
            print("SDXL skipped (testing mode). Creating placeholder background...")
            return self._generate_placeholder_video(duration, output_path)

        print("Generating background video...")

        # Generate prompt
        prompt = self.generate_prompt(verse_text)
        print(f"Prompt: {prompt}")

        try:
            # Generate images
            images = self.generate_images(prompt, num_images=4)

            # Create video with Ken Burns effect
            video_path = self.create_ken_burns_video(images, duration, output_path)
        finally:
            # Always unload to free GPU memory for subsequent steps
            self.unload_model()

        return video_path

    def unload_model(self):
        """Unload model to free memory"""
        if self.pipe is not None:
            # Move back to CPU to release VRAM before dropping
            try:
                self.pipe.to(torch_device="cpu", torch_dtype=torch.float32)
            except Exception:
                pass
            del self.pipe
            self.pipe = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _generate_placeholder_video(self, duration: float, output_path: str) -> str:
        """Create a simple solid-color placeholder video for testing without SDXL."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fps = self.config.video['fps']
        total_frames = int(duration * fps)
        width = self.config.video['width']
        height = self.config.video['height']

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"Failed to open placeholder video writer at {output_path}")

        # Soft teal placeholder with slight gradient noise to avoid total flatness
        base_color = np.array([180, 220, 210], dtype=np.uint8)  # BGR
        noise = np.random.randint(-6, 6, size=(height, width, 3), dtype=np.int16)
        frame_base = np.clip(base_color + noise, 0, 255).astype(np.uint8)

        for _ in range(total_frames):
            writer.write(frame_base)

        writer.release()
        print(f"Placeholder background saved to: {output_path}")
        return output_path
