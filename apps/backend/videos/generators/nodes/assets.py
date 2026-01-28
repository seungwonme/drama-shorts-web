"""Assets nodes - generates frames and prepares prompts for video generation."""

import json

from ..services.gemini_planner import generate_cta_last_frame, generate_first_frame
from ..state import SegmentData, VideoGeneratorState
from ..utils.logging import log, log_separator


def scene_to_prompt(
    scene: dict,
    product: dict | None = None,
    characters: list | None = None,
) -> str:
    """Convert scene JSON to Veo prompt string with full context.

    Combines product, characters, and scene information into a single
    prompt that Veo can understand and use for video generation.

    Args:
        scene: Scene data (scene_setting, camera_setup, mood_style, audio, timeline)
        product: Product information (name, description, key_benefit)
        characters: Character definitions list (id, name, appearance, clothing, etc.)

    Returns:
        JSON string containing full context for Veo
    """
    prompt_data = {}

    # Include product info for context (especially for Scene 2 product placement)
    if product:
        prompt_data["product"] = product

    # Include character definitions for consistency
    if characters:
        prompt_data["characters"] = characters

    # Include scene-specific data
    prompt_data["scene"] = scene

    return json.dumps(prompt_data, ensure_ascii=False, indent=2)


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
        characters_data = script_json.get("characters", [])
        product_data = script_json.get("product", {})
        raw_scenes = script_json.get("scenes", [])

        first_frame_image = None
        if characters_data and raw_scenes:
            # Get scene setting and first sequence from first scene
            first_scene = raw_scenes[0]
            scene_setting = first_scene.get("scene_setting", {})
            timeline = first_scene.get("timeline", [])
            first_sequence = timeline[0] if timeline else None

            log("Generating first frame with both characters...")
            log(f"First sequence: {first_sequence.get('camera', 'N/A') if first_sequence else 'N/A'}")
            first_frame_image = generate_first_frame(
                characters=characters_data,
                scene_setting=scene_setting,
                first_sequence=first_sequence,
            )
            log("First frame generated successfully", "SUCCESS")

        # === Step 2: Convert scene JSON to prompts ===
        processed_segments: list[SegmentData] = []

        log_separator("Preparing Scene JSON Prompts")
        log("Strategy: JSON structure with product + characters + scene passed to Veo")

        for idx, scene in enumerate(raw_scenes):
            scene_num = idx + 1
            prompt_name = f"Scene {scene_num}"

            # Convert JSON to prompt string with full context
            prompt = scene_to_prompt(
                scene=scene,
                product=product_data,
                characters=characters_data,
            )

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

        # Note: first_frame_image is returned as bytes here
        # services.py will save to S3 and inject first_frame_url for next node
        return {
            "segments": processed_segments,
            "_first_frame_bytes": first_frame_image,  # Temporary: saved by services.py
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

    Generates the CTA last frame using fal.ai Nano Banana.
    This frame shows the product reveal for Scene 2's ending.
    Uses the first frame (not scene1 last frame) for character consistency.
    """
    log_separator("Step 2b: CTA Frame Preparation")

    first_frame_url = state.get("first_frame_url")
    product_image_url = state.get("product_image_url")
    product_detail = state.get("product_detail", {})
    script_json = state.get("script_json", {})
    characters = script_json.get("characters", {})

    if not first_frame_url:
        log("No first_frame_url available - First frame preparation may have failed", "ERROR")
        return {
            "error": "No first_frame_url available for CTA frame generation",
            "status": "cta_frame_preparation_failed",
        }

    if not product_image_url:
        log("No product image URL - CTA frame will be skipped", "WARNING")
        return {
            "_cta_last_frame_bytes": None,
            "status": "cta_frame_skipped",
        }

    try:
        # Extract Scene 2's last timeline sequence and scene_setting for the CTA frame prompt
        last_sequence = None
        scene2_setting = None
        scenes = script_json.get("scenes", [])
        if len(scenes) >= 2:
            scene2 = scenes[1]
            scene2_setting = scene2.get("scene_setting", {})
            timeline = scene2.get("timeline", [])
            if timeline:
                # Get the last sequence (full data, not just action)
                last_sequence = timeline[-1]
                log(f"CTA last sequence - camera: {last_sequence.get('camera', 'N/A')}, mood: {last_sequence.get('mood', 'N/A')}")

        log("Generating CTA last frame with product image...")
        # fal.ai accepts URLs directly, no need to download and re-upload
        cta_last_frame_bytes = generate_cta_last_frame(
            first_frame_url=first_frame_url,
            product_image_url=product_image_url,
            product_detail=product_detail,
            characters=characters,
            last_sequence=last_sequence,
            scene_setting=scene2_setting,
        )
        log("CTA last frame generated successfully", "SUCCESS")

        # Note: cta_last_frame returned as bytes
        # services.py will save to S3 and inject cta_last_frame_url for next node
        return {
            "_cta_last_frame_bytes": cta_last_frame_bytes,  # Temporary: saved by services.py
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
