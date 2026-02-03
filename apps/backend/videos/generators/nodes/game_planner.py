"""Game character script planning node using Gemini via LangChain."""

import base64
import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ...constants import GAME_SEGMENT_COUNT
from ..config import GEMINI_API_KEY
from ..game_prompts import GAME_SCRIPT_SYSTEM_PROMPT
from ..game_state import GameGeneratorState, GameScriptData
from ..utils.logging import log, log_separator
from ..utils.media import download_image_as_base64

# Gemini model for game script planning
GAME_PLANNER_MODEL = "gemini-2.0-flash"


def _get_game_planner_llm() -> ChatGoogleGenerativeAI:
    """Get LangChain Gemini LLM for game script planning."""
    safety_settings = {
        "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
    }
    return ChatGoogleGenerativeAI(
        model=GAME_PLANNER_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.8,
        safety_settings=safety_settings,
    )


def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Parse JSON from Gemini response, handling various formats."""
    json_str = text

    # Try ```json ... ``` format
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        for part in parts:
            if "{" in part and "}" in part:
                json_str = part
                break

    # Extract { ... } portion
    start_idx = json_str.find("{")
    end_idx = json_str.rfind("}")

    if start_idx != -1 and end_idx != -1:
        json_str = json_str[start_idx : end_idx + 1]

    try:
        return json.loads(json_str.strip())
    except json.JSONDecodeError:
        # Last attempt: regex extraction
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None


def plan_game_scripts(state: GameGeneratorState) -> dict[str, Any]:
    """Generate 5 scene scripts for game character shorts using Gemini.

    Args:
        state: Current workflow state with character_image_url, game_name, user_prompt

    Returns:
        Dictionary with character_description, game_locations_used, scripts
    """
    log_separator("Game Script Planning (Gemini via LangChain)")

    character_image_url = state["character_image_url"]
    game_name = state["game_name"]
    user_prompt = state["user_prompt"]

    log(f"Game: {game_name}")
    log(f"User prompt: {user_prompt}")
    log(f"Character image: {character_image_url[:60]}...")

    # Download and convert image to base64
    log("Downloading character image...")
    image_base64 = download_image_as_base64(character_image_url)
    log("Image converted to base64")

    # Build the user prompt
    user_message = f"""CONTEXT:
- Game: {game_name}
- User request: {user_prompt}

Analyze the character image and create {GAME_SEGMENT_COUNT} video prompts where this character is inside the game world of "{game_name}".

Respond ONLY in this JSON format:
{{
    "character_description": "Detailed character appearance in English (50+ words)",
    "game_locations_used": ["list of {game_name} locations referenced"],
    "scripts": [
        {{
            "scene": 1,
            "shot_type": "close-up / medium / wide / etc",
            "game_location": "specific location name from {game_name}",
            "prompt": "Full detailed prompt in English (80+ words)",
            "action": "The specific action in this scene",
            "camera": "Camera movement description",
            "description_kr": "Korean description of the scene"
        }},
        ... ({GAME_SEGMENT_COUNT} total)
    ]
}}"""

    log(f"Sending request to Gemini ({GAME_PLANNER_MODEL})...")

    llm = _get_game_planner_llm()

    # Build multimodal message with image
    messages = [
        SystemMessage(content=GAME_SCRIPT_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
                {"type": "text", "text": user_message},
            ]
        ),
    ]

    response = llm.invoke(messages)
    response_text = response.content
    log("Response received from Gemini")

    # Parse JSON response
    data = _parse_json_response(response_text)

    if not data:
        log("Failed to parse JSON response", "ERROR")
        log(f"Raw response: {response_text[:500]}...")
        raise ValueError("Failed to parse Gemini response as JSON")

    # Validate and extract data
    character_description = data.get("character_description", "")
    game_locations_used = data.get("game_locations_used", [])
    scripts_raw = data.get("scripts", [])

    if len(scripts_raw) != GAME_SEGMENT_COUNT:
        log(f"Warning: Expected {GAME_SEGMENT_COUNT} scripts, got {len(scripts_raw)}")

    # Convert to typed script data
    scripts: list[GameScriptData] = []
    for s in scripts_raw:
        scripts.append(
            GameScriptData(
                scene=s.get("scene", len(scripts) + 1),
                shot_type=s.get("shot_type", ""),
                game_location=s.get("game_location", ""),
                prompt=s.get("prompt", ""),
                action=s.get("action", ""),
                camera=s.get("camera", ""),
                description_kr=s.get("description_kr", ""),
            )
        )

    log(f"Character description: {character_description[:100]}...")
    log(f"Game locations: {', '.join(game_locations_used)}")
    log(f"Scripts generated: {len(scripts)}")

    for script in scripts:
        log(f"  Scene {script['scene']}: {script['game_location']}")

    return {
        "character_description": character_description,
        "game_locations_used": game_locations_used,
        "scripts": scripts,
        "status": "generating_frames",
    }
