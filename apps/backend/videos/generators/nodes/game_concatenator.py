"""Game character video concatenation node using FFmpeg."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ...constants import GAME_FADE_DURATION, GAME_SEGMENT_DURATION
from ..game_state import GameGeneratorState
from ..utils.logging import log, log_separator
from ..utils.media import download_video_from_url


def _merge_videos_with_fade(
    video_paths: list[str],
    fade_duration: float = GAME_FADE_DURATION,
) -> bytes:
    """Merge multiple videos with fade transition using FFmpeg.

    Args:
        video_paths: List of video file paths
        fade_duration: Duration of fade transition in seconds

    Returns:
        Merged video as bytes
    """
    if len(video_paths) < 2:
        # If only one video, just return it
        with open(video_paths[0], "rb") as f:
            return f.read()

    clip_duration = GAME_SEGMENT_DURATION

    # Build ffmpeg inputs
    inputs = []
    for path in video_paths:
        inputs.extend(["-i", path])

    # Build filter chain
    filter_parts = []

    # Scale and pad each input for consistent dimensions
    for i in range(len(video_paths)):
        filter_parts.append(
            f"[{i}:v]scale=720:1280:force_original_aspect_ratio=decrease,"
            f"pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
        )
        filter_parts.append(
            f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];"
        )

    # Chain videos with xfade
    current_video = "v0"
    current_audio = "a0"

    for i in range(1, len(video_paths)):
        # Calculate offset for transition
        offset = (clip_duration * i) - (fade_duration * i)

        next_video = f"v{i}"
        next_audio = f"a{i}"

        if i < len(video_paths) - 1:
            out_video = f"vout{i}"
            out_audio = f"aout{i}"
        else:
            out_video = "vfinal"
            out_audio = "afinal"

        # Video crossfade
        filter_parts.append(
            f"[{current_video}][{next_video}]xfade=transition=fade:"
            f"duration={fade_duration}:offset={offset}[{out_video}];"
        )

        # Audio crossfade
        filter_parts.append(
            f"[{current_audio}][{next_audio}]acrossfade=d={fade_duration}:"
            f"c1=tri:c2=tri[{out_audio}];"
        )

        current_video = out_video
        current_audio = out_audio

    # Remove trailing semicolon
    filter_complex = "".join(filter_parts).rstrip(";")

    # Create output file
    output_path = tempfile.mktemp(suffix=".mp4")

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vfinal]",
        "-map",
        "[afinal]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_path,
    ]

    log(f"Running FFmpeg with {len(video_paths)} inputs...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log(f"FFmpeg error: {result.stderr}", "ERROR")
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")

    # Read output file
    with open(output_path, "rb") as f:
        output_bytes = f.read()

    # Clean up
    Path(output_path).unlink(missing_ok=True)

    return output_bytes


def merge_game_videos(state: GameGeneratorState) -> dict[str, Any]:
    """Merge all scene videos with fade transitions.

    Args:
        state: Current workflow state with video_urls

    Returns:
        Dictionary with final_video_bytes
    """
    log_separator("Game Video Merge (FFmpeg)")

    video_urls = state["video_urls"]
    log(f"Merging {len(video_urls)} videos with {GAME_FADE_DURATION}s fade...")

    # Download all videos to temp files
    temp_dir = tempfile.mkdtemp()
    video_paths = []

    for i, url in enumerate(video_urls):
        log(f"  Downloading video {i + 1}/{len(video_urls)}...")
        video_bytes = download_video_from_url(url)
        video_path = Path(temp_dir) / f"video_{i:02d}.mp4"
        video_path.write_bytes(video_bytes)
        video_paths.append(str(video_path))

    # Merge videos
    final_bytes = _merge_videos_with_fade(video_paths, GAME_FADE_DURATION)

    # Clean up temp files
    for path in video_paths:
        Path(path).unlink(missing_ok=True)
    Path(temp_dir).rmdir()

    log(f"Final video merged: {len(final_bytes)} bytes", "SUCCESS")

    return {
        "_final_video_bytes": final_bytes,
        "status": "completed",
    }
