"""fal.ai API client for video generation."""

import fal_client
import requests

from ...constants import (
    FAL_VIDEO_DOWNLOAD_TIMEOUT,
    MODERATION_KEYWORDS,
)
from ..config import (
    ASPECT_RATIO,
    FAL_VIDEO_INTERPOLATION_MODEL,
    FAL_VIDEO_MODEL,
    RESOLUTION,
)
from ..exceptions import ModerationError
from ..utils.logging import log, log_separator


def _check_moderation_error(exception: Exception) -> None:
    """Check if exception is a moderation error and re-raise appropriately.

    Args:
        exception: The caught exception to analyze

    Raises:
        ModerationError: If the exception indicates content moderation rejection
        Exception: Re-raises the original exception if not a moderation error
    """
    error_msg = str(exception).lower()
    if any(keyword in error_msg for keyword in MODERATION_KEYWORDS):
        raise ModerationError(str(exception))
    raise exception


def generate_video_from_image(
    prompt: str,
    first_frame_url: str,
    duration: int = 8,
) -> bytes:
    """Generate video from image using fal.ai Veo (image-to-video).

    Args:
        prompt: Text prompt for video generation
        first_frame_url: URL of the first frame image
        duration: Video duration in seconds (default 8)

    Returns:
        Video bytes
    """
    log_separator("Scene 1 Generation (fal.ai)")

    log(f"Model: {FAL_VIDEO_MODEL}")
    log(f"Resolution: {RESOLUTION}")
    log(f"Aspect ratio: {ASPECT_RATIO}")
    log(f"Duration: {duration}s")
    log(f"First frame URL: {first_frame_url[:80]}...")

    log("Prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    input_params = {
        "prompt": prompt,
        "image_url": first_frame_url,
        "duration": f"{duration}s",
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "generate_audio": True,
    }

    log("Sending API request...")

    try:
        result = fal_client.subscribe(
            FAL_VIDEO_MODEL,
            arguments=input_params,
            with_logs=True,
        )

        video_url = result.get("video", {}).get("url")
        if not video_url:
            raise ValueError(f"No video URL in response: {result}")

        log(f"Downloading video from: {video_url[:80]}...")
        response = requests.get(video_url, timeout=FAL_VIDEO_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        video_bytes = response.content

        log(f"Video downloaded: {len(video_bytes)} bytes", "SUCCESS")
        return video_bytes

    except Exception as e:
        log(f"API request failed: {e}", "ERROR")
        _check_moderation_error(e)


def generate_video_interpolation(
    prompt: str,
    first_frame_url: str,
    last_frame_url: str,
    duration: int = 8,
) -> bytes:
    """Generate video interpolation using fal.ai Veo (first-last-frame-to-video).

    Creates a smooth transition between first and last frame.

    Args:
        prompt: Text prompt for video generation
        first_frame_url: URL of the first frame image (scene1 last frame)
        last_frame_url: URL of the last frame image (CTA frame)
        duration: Video duration in seconds (default 8)

    Returns:
        Video bytes
    """
    log_separator("Scene 2 Generation (fal.ai)")

    log(f"Model: {FAL_VIDEO_INTERPOLATION_MODEL}")
    log(f"Resolution: {RESOLUTION}")
    log(f"Aspect ratio: {ASPECT_RATIO}")
    log(f"Duration: {duration}s")
    log(f"First frame URL: {first_frame_url[:80]}...")
    log(f"Last frame URL: {last_frame_url[:80]}...")

    log("Prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    input_params = {
        "prompt": prompt,
        "first_frame_url": first_frame_url,
        "last_frame_url": last_frame_url,
        "duration": f"{duration}s",
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "generate_audio": True,
    }

    log("Sending API request...")

    try:
        result = fal_client.subscribe(
            FAL_VIDEO_INTERPOLATION_MODEL,
            arguments=input_params,
            with_logs=True,
        )

        video_url = result.get("video", {}).get("url")
        if not video_url:
            raise ValueError(f"No video URL in response: {result}")

        log(f"Downloading video from: {video_url[:80]}...")
        response = requests.get(video_url, timeout=FAL_VIDEO_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        video_bytes = response.content

        log(f"Video downloaded: {len(video_bytes)} bytes", "SUCCESS")
        return video_bytes

    except Exception as e:
        log(f"API request failed: {e}", "ERROR")
        _check_moderation_error(e)
