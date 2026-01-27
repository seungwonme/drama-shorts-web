"""Assets node - generates first frame and prepares JSON prompts for Veo."""

import json

from ..services.gemini_planner import generate_first_frame
from ..state import SegmentData, VideoGeneratorState
from ..utils.logging import log, log_separator


def scene_to_prompt(scene: dict) -> str:
    """Convert scene JSON to Veo prompt string.

    Simply serializes the PROMPT_TEMPLATE JSON structure directly.
    Veo can parse and understand the structured JSON format.
    """
    return json.dumps(scene, ensure_ascii=False, indent=2)


def prepare_assets(state: VideoGeneratorState) -> dict:
    """Prepare assets for video generation (Step 2).

    New workflow:
    1. Generate first frame with both characters using Nano Banana
    2. Convert scene JSON to prompt strings (json.dumps)

    CTA last frame is generated later in video_generator after Scene 1 completes.
    """
    log_separator("Step 2: Asset Preparation")

    script_json = state.get("script_json")

    if not script_json:
        log("No script_json found - planning may have failed", "ERROR")
        return {
            "error": "No script data available",
            "status": "asset_preparation_failed",
        }

    try:
        # === Step 1: Generate first frame with both characters ===
        characters_data = script_json.get("characters", {})
        raw_scenes = script_json.get("scenes", [])

        first_frame_image = None
        if characters_data and raw_scenes:
            # Get scene setting from first scene for context
            first_scene = raw_scenes[0]
            scene_setting = first_scene.get("scene_setting", {})

            log("Generating first frame with both characters...")
            first_frame_image = generate_first_frame(characters_data, scene_setting)
            log("First frame generated successfully", "SUCCESS")

        # === Step 2: Convert scene JSON to prompts ===
        processed_segments: list[SegmentData] = []

        log_separator("Preparing Scene JSON Prompts")
        log("Strategy: JSON structure passed directly to Veo")

        for idx, scene in enumerate(raw_scenes):
            scene_num = idx + 1
            metadata = scene.get("metadata", {})
            prompt_name = metadata.get("prompt_name", f"Scene {scene_num}")

            # Convert JSON to prompt string
            prompt = scene_to_prompt(scene)

            # Fixed 8 seconds per scene (Veo API supports 4, 6, 8 only)
            seconds = 8

            processed_segments.append({
                "title": prompt_name,
                "seconds": seconds,
                "prompt": prompt,
                "raw_data": scene,
            })

            print(f"\n{'='*60}")
            print(f"[Scene {scene_num:02d}] {prompt_name} - {seconds}s")
            print(f"{'='*60}")
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            print()

        log(f"Processed {len(processed_segments)} scenes")

        return {
            "segments": processed_segments,
            "first_frame_image": first_frame_image,
            "current_segment_index": 0,
            "status": "assets_prepared",
        }

    except Exception as e:
        log(f"Asset preparation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "asset_preparation_failed",
        }
