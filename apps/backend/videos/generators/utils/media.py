"""Media utilities for downloading content from URLs."""

import httpx

from .logging import log


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
