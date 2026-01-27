"""Assets nodes - generates frames and prepares prompts for video generation."""

import json

from ..services.gemini_planner import generate_cta_last_frame, generate_first_frame
from ..state import SegmentData, VideoGeneratorState
from ..utils.logging import log, log_separator


def scene_to_prompt(scene: dict) -> str:
    """Convert scene JSON to Veo prompt string.

    Simply serializes the PROMPT_TEMPLATE JSON structure directly.
    Veo can parse and understand the structured JSON format.
    """
    return json.dumps(scene, ensure_ascii=False, indent=2)


def prepare_first_frame(state: VideoGeneratorState) -> dict:
    """Prepare first frame for video generation (Step 2a).

    Generates the first frame with both characters using Nano Banana,
    then converts scene JSON to prompt strings.
    """
    log_separator("Step 2a: First Frame Preparation")

    script_json = state.get("script_json")

    if not script_json:
        log("No script_json found - planning may have failed", "ERROR")
        return {
            "error": "No script data available",
            "status": "first_frame_preparation_failed",
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
            "status": "first_frame_prepared",
        }

    except Exception as e:
        log(f"First frame preparation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "first_frame_preparation_failed",
        }


def prepare_cta_frame(state: VideoGeneratorState) -> dict:
    """Prepare CTA last frame for Scene 2 interpolation (Step 2b).

    Generates the CTA last frame using Nano Banana.
    This frame shows the product reveal for Scene 2's ending.
    """
    log_separator("Step 2b: CTA Frame Preparation")

    scene1_last_frame = state.get("scene1_last_frame_image")
    product_image_url = state.get("product_image_url")
    product_detail = state.get("product_detail", {})
    script_json = state.get("script_json", {})
    characters = script_json.get("characters", {})

    if not scene1_last_frame:
        log("No scene1_last_frame available - Scene 1 may have failed", "ERROR")
        return {
            "error": "No scene1_last_frame available for CTA frame generation",
            "status": "cta_frame_preparation_failed",
        }

    if not product_image_url:
        log("No product image URL - CTA frame will be skipped", "WARNING")
        return {
            "cta_last_frame_image": None,
            "status": "cta_frame_skipped",
        }

    try:
        # Extract Scene 2's last timeline action for the CTA frame prompt
        cta_action = None
        scenes = script_json.get("scenes", [])
        if len(scenes) >= 2:
            scene2 = scenes[1]
            timeline = scene2.get("timeline", [])
            if timeline:
                # Get the last sequence's action
                last_seq = timeline[-1]
                cta_action = last_seq.get("action", "")
                log(f"CTA action from script: {cta_action[:100]}...")

        log("Generating CTA last frame with product image...")
        cta_last_frame_image = generate_cta_last_frame(
            scene1_last_frame=scene1_last_frame,
            product_image_url=product_image_url,
            product_detail=product_detail,
            characters=characters,
            cta_action=cta_action,
        )
        log("CTA last frame generated successfully", "SUCCESS")

        return {
            "cta_last_frame_image": cta_last_frame_image,
            "status": "cta_frame_prepared",
        }

    except Exception as e:
        log(f"CTA frame preparation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "cta_frame_preparation_failed",
        }


# Alias for backwards compatibility
prepare_assets = prepare_first_frame
