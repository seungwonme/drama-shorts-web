"""Game character frame generation node using Nano Banana."""

import concurrent.futures
from typing import Any

import fal_client
import requests

from ...constants import GAME_MAX_WORKERS
from ..config import FAL_IMAGE_EDIT_MODEL
from ..game_prompts import GAME_FRAME_PROMPT_TEMPLATE
from ..game_state import GameGeneratorState, GameScriptData
from ..utils.logging import log, log_separator


def _generate_single_frame(
    character_image_url: str,
    script: GameScriptData,
) -> dict[str, Any]:
    """Generate a single scene start frame using Nano Banana.

    Args:
        character_image_url: URL of the character image
        script: Script data for this scene

    Returns:
        Dict with scene number and generated image bytes
    """
    scene_num = script["scene"]
    log(f"  [Scene {scene_num}] Generating frame...")

    # Build prompt for frame generation
    prompt = GAME_FRAME_PROMPT_TEMPLATE.format(prompt=script["prompt"])

    result = fal_client.subscribe(
        FAL_IMAGE_EDIT_MODEL,
        arguments={
            "prompt": prompt,
            "image_urls": [character_image_url],
            "aspect_ratio": "9:16",
            "output_format": "png",
            "resolution": "1K",
        },
    )

    images = result.get("images", [])
    if not images:
        raise ValueError(f"No images in response for scene {scene_num}")

    image_url = images[0].get("url")

    # Download image
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    image_bytes = response.content

    log(f"  [Scene {scene_num}] Frame generated: {len(image_bytes)} bytes")

    return {
        "scene": scene_num,
        "_image_bytes": image_bytes,
        "image_url": image_url,
    }


def generate_game_frames(state: GameGeneratorState) -> dict[str, Any]:
    """Generate all 5 scene start frames in parallel using Nano Banana.

    Args:
        state: Current workflow state with character_image_url and scripts

    Returns:
        Dictionary with frame_results list containing image bytes
    """
    log_separator("Game Frame Generation (Nano Banana)")

    character_image_url = state["character_image_url"]
    scripts = state["scripts"]

    log(f"Model: {FAL_IMAGE_EDIT_MODEL}")
    log(f"Generating {len(scripts)} frames in parallel...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=GAME_MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _generate_single_frame,
                character_image_url,
                script,
            ): script["scene"]
            for script in scripts
        }

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

    success_count = sum(1 for r in results if "_image_bytes" in r)
    log(f"Frame generation complete: {success_count}/{len(scripts)} successful")

    return {
        "_frame_results": results,
        "status": "generating_videos",
    }
