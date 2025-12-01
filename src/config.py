"""Configuration loader for Bible Shorts Generator"""

import yaml
from pathlib import Path
from dotenv import load_dotenv
import os
from typing import Any, Dict

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager that loads settings from config.yaml and .env"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.data = self._load_config()

        # Load environment variables
        self.youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.youtube_refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.hf_token = os.getenv("HF_TOKEN")
        self.cuda_visible_devices = os.getenv("CUDA_VISIBLE_DEVICES", "0")

        # Set torch home
        torch_home = os.getenv("TORCH_HOME", "./models")
        os.environ["TORCH_HOME"] = torch_home

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def __getattr__(self, name: str) -> Any:
        """Allow dot notation access to config values"""
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"Config has no attribute: {name}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default"""
        return self.data.get(key, default)

    def reload(self):
        """Reload configuration from file"""
        self.data = self._load_config()


# Global config instance
config = Config()
