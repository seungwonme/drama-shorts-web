"""Configuration settings for video generator."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
FAL_KEY = os.environ.get("FAL_KEY", "")

# Models
PLANNER_MODEL = os.environ.get("GEMINI_AI_MODEL", "gemini-3-flash-preview")

# fal.ai Models
FAL_IMAGE_MODEL = "fal-ai/nano-banana-pro"
FAL_IMAGE_EDIT_MODEL = "fal-ai/nano-banana-pro/edit"
FAL_VIDEO_MODEL = "fal-ai/veo3.1/fast/image-to-video"
FAL_VIDEO_INTERPOLATION_MODEL = "fal-ai/veo3.1/fast/first-last-frame-to-video"

# Video settings
RESOLUTION = "720p"
ASPECT_RATIO = "9:16"
