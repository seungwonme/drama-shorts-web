"""Planner node - generates scene script JSON using Gemini AI."""

from ..prompts import DEFAULT_VIDEO_STYLE
from ..services.gemini_planner import plan_script_with_ai
from ..state import CharacterDetail, ProductDetail, VideoGeneratorState
from ..utils.logging import log, log_separator


def plan_script(state: VideoGeneratorState) -> dict:
    """Generate dramatized ad script JSON using Gemini (Step 1 of 2).

    This node focuses only on AI planning:
    - Calls Gemini to generate the script JSON
    - Extracts and stores character details for consistency
    - Extracts product information

    Asset preparation (image generation, loading) is handled by prepare_assets node.
    """
    log_separator("Step 1: AI Script Planning")

    topic = state["topic"]
    script = state.get("script")
    product_image_url = state.get("product_image_url")
    product_brand = state.get("product_brand")
    product_description = state.get("product_description")
    video_style = state.get("video_style", DEFAULT_VIDEO_STYLE)

    log(f"Product/Service: {topic}")
    log(f"Video Style: {video_style.value}")
    if product_brand:
        log(f"Brand: {product_brand}")
    if product_description:
        log(f"Description: {product_description[:100]}...")
    if script:
        log(f"Script provided: {len(script)} characters")
    if product_image_url:
        log(f"Product image URL: {product_image_url}")

    try:
        # Generate script JSON from Gemini
        script_json = plan_script_with_ai(
            topic,
            script=script,
            product_brand=product_brand,
            product_description=product_description,
            video_style=video_style,
        )

        # Extract product detail
        product_data = script_json.get("product", {})
        product_detail: ProductDetail = {
            "name": product_data.get("name", topic),
            "description": product_data.get("description", ""),
            "key_benefit": product_data.get("key_benefit", ""),
        }

        # Extract character details with full descriptions for consistency
        characters_data = script_json.get("characters", {})
        character_details: dict[str, CharacterDetail] = {}

        for char_key in ["character_a", "character_b"]:
            char_data = characters_data.get(char_key, {})
            if char_data:
                character_details[char_key] = {
                    "name": char_data.get("name", char_key.upper()),
                    "description": char_data.get("description", ""),
                }
                log(f"{char_key}: {character_details[char_key]['name']} - {character_details[char_key]['description'][:50]}...")

        log(f"Product: {product_detail['name']}")
        log(f"Characters extracted: {len(character_details)}")

        return {
            "script_json": script_json,
            "product_detail": product_detail,
            "character_details": character_details,
            "status": "script_planned",
        }

    except Exception as e:
        log(f"Script planning failed: {e}", "ERROR")
        return {
            "error": str(e),
            "status": "planning_failed",
        }
