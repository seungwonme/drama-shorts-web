"""Game character video generation node using Veo."""

import concurrent.futures
from typing import Any

import fal_client
import requests

from ...constants import GAME_MAX_WORKERS, GAME_SEGMENT_DURATION, FAL_VIDEO_DOWNLOAD_TIMEOUT
from ..config import ASPECT_RATIO, FAL_VIDEO_MODEL, RESOLUTION
from ..game_state import GameGeneratorState, GameScriptData
from ..utils.logging import log, log_separator


def _generate_single_video(
    frame_url: str,
    script: GameScriptData,
) -> dict[str, Any]:
    """Generate a single 4-second video from frame using Veo.

    Args:
        frame_url: URL of the start frame image
        script: Script data for this scene

    Returns:
        Dict with scene number and generated video bytes
    """
    scene_num = script["scene"]
    log(f"  [Scene {scene_num}] Generating video...")

    result = fal_client.subscribe(
        FAL_VIDEO_MODEL,
        arguments={
            "prompt": script["prompt"],
            "image_url": frame_url,
            "duration": f"{GAME_SEGMENT_DURATION}s",
            "aspect_ratio": ASPECT_RATIO,
            "resolution": RESOLUTION,
            "generate_audio": True,
        },
    )

    video_url = result.get("video", {}).get("url")
    if not video_url:
        raise ValueError(f"No video URL in response for scene {scene_num}")

    # Download video
    response = requests.get(video_url, timeout=FAL_VIDEO_DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    video_bytes = response.content

    log(f"  [Scene {scene_num}] Video generated: {len(video_bytes)} bytes")

    return {
        "scene": scene_num,
        "_video_bytes": video_bytes,
        "video_url": video_url,
    }


def generate_game_videos(state: GameGeneratorState) -> dict[str, Any]:
    """Generate all 5 scene videos in parallel using Veo.

    Args:
        state: Current workflow state with frame_urls and scripts

    Returns:
        Dictionary with video_results list containing video bytes
    """
    log_separator("Game Video Generation (Veo)")

    frame_urls = state["frame_urls"]
    scripts = state["scripts"]

    log(f"Model: {FAL_VIDEO_MODEL}")
    log(f"Duration: {GAME_SEGMENT_DURATION}s per scene")
    log(f"Generating {len(scripts)} videos in parallel...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=GAME_MAX_WORKERS) as executor:
        futures = {}
        for script in scripts:
            scene_idx = script["scene"] - 1  # 0-indexed
            if scene_idx < len(frame_urls):
                frame_url = frame_urls[scene_idx]
                future = executor.submit(
                    _generate_single_video,
                    frame_url,
                    script,
                )
                futures[future] = script["scene"]
            else:
                log(f"  [Scene {script['scene']}] Skipped: no frame URL")

        for future in concurrent.futures.as_completed(futures):
            scene_num = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                log(f"  [Scene {scene_num}] Error: {e}", "ERROR")
                results.append({
                    "scene": scene_num,
                    "error": str(e),
                })

    # Sort by scene number
    results.sort(key=lambda x: x["scene"])

    success_count = sum(1 for r in results if "_video_bytes" in r)
    log(f"Video generation complete: {success_count}/{len(scripts)} successful")

    return {
        "_video_results": results,
        "status": "merging",
    }
