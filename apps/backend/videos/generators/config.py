"""Configuration settings for video generator."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

# Models
PLANNER_MODEL = os.environ.get("GEMINI_AI_MODEL", "gemini-3-flash-preview")
REPLICATE_VIDEO_MODEL = "google/veo-3.1-fast"
REPLICATE_IMAGE_MODEL = "google/nano-banana"

# Video settings
RESOLUTION = "720p"
ASPECT_RATIO = "9:16"

# Assets directory (relative to this file)
ASSETS_DIR = Path(__file__).parent / "assets"

# API settings
POLL_INTERVAL_SEC = 10
PRINT_PROGRESS_BAR = True


def ensure_api_keys() -> tuple[str, str]:
    """Ensure API keys are available, prompting if necessary."""
    global GEMINI_API_KEY, REPLICATE_API_TOKEN

    if not GEMINI_API_KEY:
        GEMINI_API_KEY = input("Google Gemini API Key: ").strip()
        os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

    if not REPLICATE_API_TOKEN:
        REPLICATE_API_TOKEN = input("Replicate API Token: ").strip()
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    return (GEMINI_API_KEY, REPLICATE_API_TOKEN)
