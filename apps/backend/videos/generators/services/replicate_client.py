"""Replicate API client for video generation."""

import io

import replicate
import requests

from ..config import ASPECT_RATIO, REPLICATE_VIDEO_MODEL, RESOLUTION
from ..exceptions import ModerationError
from ..utils.logging import log, log_separator


def create_and_download_video(
    prompt: str,
    first_frame: bytes | None = None,
    last_frame: bytes | None = None,
    duration: int = 8,
) -> bytes:
    """Create video using Replicate Veo and return result as bytes.

    Args:
        prompt: Text prompt for video generation
        first_frame: Optional first frame image bytes (image parameter)
        last_frame: Optional last frame image bytes for interpolation
                    (creates transition between first_frame and last_frame)
        duration: Video duration in seconds (default 8)

    Returns:
        Video bytes
    """
    log_separator("Replicate Veo API request")

    log(f"Model: {REPLICATE_VIDEO_MODEL}")
    log(f"Resolution: {RESOLUTION}")
    log(f"Aspect ratio: {ASPECT_RATIO}")
    log(f"Duration: {duration}s")
    log(f"First frame (image): {'yes' if first_frame else 'no'}")
    log(f"Last frame (interpolation): {'yes' if last_frame else 'no'}")

    log("Prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    input_params = {
        "prompt": prompt,
        "duration": duration,
        "resolution": RESOLUTION,
        "aspect_ratio": ASPECT_RATIO,
        "generate_audio": True,
    }

    # Add first frame if provided (image-to-video mode)
    if first_frame:
        input_params["image"] = io.BytesIO(first_frame)
        log("Using image (first frame) for image-to-video mode")

    # Add last frame if provided (interpolation mode)
    # When both image and last_frame are provided, Veo creates transition between them
    if last_frame:
        input_params["last_frame"] = io.BytesIO(last_frame)
        log("Using last_frame for interpolation mode")

    log("Sending API request...")

    try:
        # Create prediction and wait for completion using SDK's built-in wait()
        # Reference: https://github.com/replicate/replicate-python
        prediction = replicate.predictions.create(
            model=REPLICATE_VIDEO_MODEL,
            input=input_params,
        )

        log(f"Prediction created: {prediction.id}")
        log("Waiting for completion (video generation takes ~70s)...")

        # SDK's built-in wait() handles polling automatically
        prediction.wait()

        if prediction.status == "failed":
            raise Exception(f"Prediction failed: {prediction.error}")

        output = prediction.output

        # Handle FileOutput or URL response
        if hasattr(output, "read"):
            video_bytes = output.read()
        else:
            # Output is a URL string
            log(f"Downloading video from: {str(output)[:80]}...")
            response = requests.get(str(output), timeout=300)
            response.raise_for_status()
            video_bytes = response.content

        log(f"Video downloaded: {len(video_bytes)} bytes", "SUCCESS")
        return video_bytes

    except Exception as e:
        error_msg = str(e).lower()
        log(f"API request failed: {e}", "ERROR")

        # Detect content moderation errors
        moderation_keywords = [
            "moderation",
            "blocked",
            "safety",
            "sensitive",  # "flagged as sensitive"
            "content filter",
            "e005",  # Replicate error code for moderation
        ]
        if any(keyword in error_msg for keyword in moderation_keywords):
            raise ModerationError(str(e))
        raise
