"""Media utilities for downloading content from URLs."""

import base64
import io

import httpx
from PIL import Image

from .logging import log


# Image processing constants
MAX_IMAGE_DIMENSION = 1024
MAX_FILE_SIZE_MB = 4


def download_from_url(url: str, timeout: float = 60.0) -> bytes:
    """Download content from URL and return as bytes.

    Args:
        url: URL to download from (S3 URL or any HTTP URL)
        timeout: Request timeout in seconds

    Returns:
        Downloaded content as bytes

    Raises:
        httpx.HTTPError: If download fails
    """
    log(f"Downloading from URL: {url[:100]}...")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
        log(f"Downloaded {len(content)} bytes")
        return content


def download_image_from_url(url: str, timeout: float = 30.0) -> bytes:
    """Download image from URL and return as bytes.

    Convenience wrapper for download_from_url with shorter timeout for images.

    Args:
        url: Image URL to download from
        timeout: Request timeout in seconds (default 30s for images)

    Returns:
        Image content as bytes
    """
    return download_from_url(url, timeout=timeout)


def download_video_from_url(url: str, timeout: float = 120.0) -> bytes:
    """Download video from URL and return as bytes.

    Convenience wrapper for download_from_url with longer timeout for videos.

    Args:
        url: Video URL to download from
        timeout: Request timeout in seconds (default 120s for videos)

    Returns:
        Video content as bytes
    """
    return download_from_url(url, timeout=timeout)


def resize_image_for_api(image_bytes: bytes) -> bytes:
    """Resize image to fit API constraints.

    Args:
        image_bytes: Original image bytes

    Returns:
        Resized image bytes (JPEG format)
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert RGBA to RGB
        if img.mode == "RGBA":
            img = img.convert("RGB")

        width, height = img.size
        file_size_mb = len(image_bytes) / (1024 * 1024)

        # Check if resize is needed
        if (
            file_size_mb > MAX_FILE_SIZE_MB
            or width > MAX_IMAGE_DIMENSION
            or height > MAX_IMAGE_DIMENSION
        ):
            ratio = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            log(f"Image resized: {width}x{height} -> {new_size[0]}x{new_size[1]}")

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


def download_image_as_base64(url: str, timeout: float = 30.0) -> str:
    """Download image from URL and return as base64 string.

    Automatically resizes large images to fit API constraints.

    Args:
        url: Image URL to download from
        timeout: Request timeout in seconds

    Returns:
        Base64 encoded image string (without data URI prefix)
    """
    image_bytes = download_image_from_url(url, timeout=timeout)
    resized_bytes = resize_image_for_api(image_bytes)
    return base64.b64encode(resized_bytes).decode("utf-8")
