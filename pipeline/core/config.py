
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = PROJECT_ROOT

    gemini_text_model: str = os.getenv(
        "GEMINI_TEXT_MODEL", "gemini-3.8-flash"
    )

    gemini_tts_model: str = os.getenv(
        "GEMINI_TTS_MODEL", "gemini-3.8-flash-tts"
    )

    gemini_api_version: str = os.getenv(
        "GEMINI_API_VERSION", "v1beta"
    )

    image_model: str = os.getenv(
        "IMAGE_MODEL",
        "@cf/black-forest-labs/flux-2-klein-4b",
    )

    video_model: str = os.getenv(
        "VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B"
    )

    music_model: str = os.getenv(
        "MUSIC_MODEL", "ACE-Step-1.5"
    )

    max_attempts: int = int(os.getenv("MAX_ATTEMPTS", "3"))

    request_timeout: float = float(
        os.getenv("REQUEST_TIMEOUT", "120")
    )

    @property
    def storyboard_path(self) -> Path:
        return self.root / "storyboard.json"

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def cache_dir(self) -> Path:
        return self.root / ".cache"

    @property
    def log_path(self) -> Path:
        return self.root / "runs.jsonl"

    @property
    def references_dir(self) -> Path:
        return self.root / "assets" / "references"


settings = Settings()


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value
