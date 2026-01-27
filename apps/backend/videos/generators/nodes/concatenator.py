"""Concatenator node - merges video segments into final video."""

import tempfile
from pathlib import Path

from ..state import VideoGeneratorState
from ..utils.logging import log, log_separator
from ..utils.video import concatenate_segments


def concatenate_videos(state: VideoGeneratorState) -> dict:
    """Concatenate all generated video segments.

    Uses tempfile to write video bytes to disk for MoviePy processing,
    then reads the result back as bytes.
    """
    log_separator("Step 3: Video Concatenation")

    segment_videos = state.get("segment_videos", [])
    skipped = state.get("skipped_segments", [])

    if skipped:
        log(f"Skipped segments: {skipped}", "WARNING")
        log("Some segments were not generated.", "WARNING")

    if not segment_videos:
        return {
            "error": "All segments failed to generate. Please try a different topic.",
            "status": "concatenation_failed",
        }

    # Sort segments by index to ensure correct order
    segment_videos = sorted(segment_videos, key=lambda x: x["index"])

    if len(segment_videos) == 1:
        log("Only one segment generated, using as final video")
        return {
            "final_video_bytes": segment_videos[0]["video_bytes"],
            "status": "complete",
        }

    # Use temporary directory for video processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Write segment bytes to temporary files
        temp_paths = []
        for i, seg_video in enumerate(segment_videos):
            temp_path = temp_dir_path / f"segment_{i:02d}.mp4"
            temp_path.write_bytes(seg_video["video_bytes"])
            temp_paths.append(temp_path)
            log(f"Temp segment {i+1}: {temp_path}")

        # Concatenate using MoviePy (with S3 asset URLs if available)
        output_path = temp_dir_path / "final_video.mp4"
        concatenate_segments(
            temp_paths,
            output_path,
            last_cta_image_url=state.get("last_cta_image_url"),
            sound_effect_url=state.get("sound_effect_url"),
        )

        # Read final video as bytes
        final_bytes = output_path.read_bytes()
        log(f"Final video size: {len(final_bytes)} bytes")

    return {
        "final_video_bytes": final_bytes,
        "status": "complete",
    }
