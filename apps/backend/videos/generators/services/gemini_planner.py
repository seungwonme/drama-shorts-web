"""Gemini API client for prompt planning and character image generation."""

import json
from typing import Any

import fal_client
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from ..config import FAL_IMAGE_EDIT_MODEL, FAL_IMAGE_MODEL, GEMINI_API_KEY, PLANNER_MODEL
from ..prompts import (
    CTA_FRAME_PROMPT,
    DEFAULT_VIDEO_STYLE,
    FIRST_FRAME_PROMPT,
    VideoStyle,
    get_auto_system_prompt,
    get_script_system_prompt,
)
from ..utils.logging import log, log_separator


# Pydantic models for structured output

# === Product & Character Definitions (for image generation) ===
class Product(BaseModel):
    """Product information for the ad."""

    name: str = Field(description="Product/service name")
    description: str = Field(description="What it does")
    key_benefit: str = Field(description="Main selling point")


class CharacterDefinition(BaseModel):
    """Character definition for image generation."""

    name: str = Field(description="Korean name")
    description: str = Field(
        description="Detailed physical description in English - age, hair, clothing, distinctive features"
    )


class Characters(BaseModel):
    """All characters in the video."""

    character_a: CharacterDefinition = Field(description="First character (usually antagonist)")
    character_b: CharacterDefinition = Field(description="Second character (usually protagonist)")


# === PROMPT_TEMPLATE format for Veo (per scene) ===
class SceneMetadata(BaseModel):
    """Metadata for a scene prompt."""

    prompt_name: str = Field(description="Short description of scene in Korean")
    base_style: str = Field(description="Visual style (e.g., '영화적, 자연광, 4K')")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio for YouTube Shorts")


class SceneSetting(BaseModel):
    """Scene setting/location."""

    location: str = Field(description="Location description in Korean")
    lighting: str = Field(description="Lighting description in Korean")


class CameraSetup(BaseModel):
    """Camera configuration."""

    shot: str = Field(description="Shot type and framing")
    movement: str = Field(description="Camera movement")
    focus: str = Field(description="Focus and emphasis")
    key_shots: str = Field(default="", description="Important cuts or focus changes")


class MoodStyle(BaseModel):
    """Mood and style."""

    genre: str = Field(description="Genre/mood of the scene")
    color_tone: str = Field(description="Color tone")


class AudioConfig(BaseModel):
    """Audio configuration."""

    background: str = Field(description="Background music/ambiance")
    fx: str = Field(description="Sound effects")


class CharacterInScene(BaseModel):
    """Character in a scene."""

    name: str = Field(description="Character name")
    appearance: str = Field(description="Appearance description")
    emotion: str = Field(description="Emotional state")
    position: str = Field(default="", description="Position in frame (e.g., left, center, standing)")


class TimelineEvent(BaseModel):
    """Timeline event within a scene."""

    sequence: int = Field(description="Event sequence number")
    timestamp: str = Field(description="Timestamp range (e.g., '00:00-00:04')")
    action: str = Field(description="Action description with dialogue")
    mood: str = Field(description="Mood of this moment")
    audio: str = Field(description="Audio note (e.g., 'Dialogue must be in Korean')")


class ScenePrompt(BaseModel):
    """A single scene in PROMPT_TEMPLATE format for Veo."""

    metadata: SceneMetadata = Field(description="Scene metadata")
    scene_setting: SceneSetting = Field(description="Scene setting")
    camera_setup: CameraSetup = Field(description="Camera configuration")
    mood_style: MoodStyle = Field(description="Mood and style")
    audio: AudioConfig = Field(description="Audio configuration")
    characters: list[CharacterInScene] = Field(description="Characters in this scene")
    timeline: list[TimelineEvent] = Field(description="Timeline of events")


class ScriptOutput(BaseModel):
    """Complete script output for dramatized ad."""

    product: Product = Field(description="Product information")
    characters: Characters = Field(description="Character definitions for image generation")
    scenes: list[ScenePrompt] = Field(description="Scene prompts in PROMPT_TEMPLATE format")

_llm: ChatGoogleGenerativeAI | None = None


def get_planner_llm() -> ChatGoogleGenerativeAI:
    """Get or create LangChain Gemini LLM for planning (LangSmith tracing enabled)."""
    global _llm
    if _llm is None:
        # Safety settings for creative dramatic content generation
        # Block only high-severity content, allow medium for dramatic scenarios
        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
        }
        _llm = ChatGoogleGenerativeAI(
            model=PLANNER_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.7,
            safety_settings=safety_settings,
        )
    return _llm


def plan_script_with_ai(
    base_prompt: str,
    script: str | None = None,
    product_brand: str | None = None,
    product_description: str | None = None,
    video_style: VideoStyle = DEFAULT_VIDEO_STYLE,
) -> dict[str, Any]:
    """Generate dramatized ad script JSON using Gemini with structured output.

    This function only generates the raw script JSON.
    Prompt assembly is handled separately in the assets module.

    Args:
        base_prompt: The product/service to advertise
        script: Optional user-provided storyline/script
        product_brand: Optional brand name
        product_description: Optional product description
        video_style: Video style template (default: B급 막장 드라마)

    Returns:
        Raw script JSON containing product, characters, and segments data
    """
    log_separator("AI Script Generation Started")
    log(f"Video Style: {video_style.value}")

    # Build product info section
    product_info_parts = [f"광고할 제품/서비스: {base_prompt}"]
    if product_brand:
        product_info_parts.append(f"브랜드: {product_brand}")
    if product_description:
        product_info_parts.append(f"제품 설명: {product_description}")
    product_info = "\n".join(product_info_parts)

    # Choose system prompt based on whether script is provided and video style
    if script:
        system_prompt = get_script_system_prompt(video_style)
        user_input = f"""{product_info}

사용자 제공 스크립트/줄거리:
{script}

위 스크립트를 기반으로 드라마타이즈 광고 영상 프롬프트를 생성해주세요.
- 사용자의 줄거리와 대사를 최대한 보존하세요.
- 총 16초 (8초 + 8초) 2씬 구성입니다.
- 모든 묘사는 영어로, 대사만 한국어로 작성하세요.""".strip()
        log("Mode: Script-based generation")
    else:
        system_prompt = get_auto_system_prompt(video_style)
        user_input = f"""{product_info}

위 제품/서비스를 홍보하는 드라마타이즈 광고 영상을 생성해주세요.
- Hook(막장 드라마 상황) → Bridge(제품 연결) → CTA(반전 및 광고) 구조를 따르세요.
- 총 16초 (8초 + 8초) 2씬 구성입니다.
- 모든 묘사는 영어로, 대사만 한국어로 작성하세요.""".strip()
        log("Mode: Auto-generated storyline")

    log("System prompt:")
    print("-" * 40)
    print(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
    print("-" * 40)

    log("User input:")
    print("-" * 40)
    print(user_input)
    print("-" * 40)

    log(f"API call started - model: {PLANNER_MODEL}")

    llm = get_planner_llm()

    # Use LangChain messages for LangSmith tracing
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input),
    ]

    log("Using structured output with Pydantic schema...")
    structured_llm = llm.with_structured_output(ScriptOutput)
    result: ScriptOutput = structured_llm.invoke(messages)
    data = result.model_dump()

    log("Structured output received:")
    print("-" * 40)
    print(json.dumps(data, ensure_ascii=False, indent=2)[:1500] + "...")
    print("-" * 40)

    characters = data.get("characters", {})
    product = data.get("product", {})
    scenes = data.get("scenes", [])

    log(f"AI decision - scenes: {len(scenes)}")
    log(f"Product: {product.get('name', 'N/A') if isinstance(product, dict) else product}")
    log(f"Character A: {characters.get('character_a', {}).get('name', 'N/A')}")
    log(f"Character B: {characters.get('character_b', {}).get('name', 'N/A')}")

    return data


def generate_first_frame(
    characters: dict[str, Any],
    scene_setting: dict[str, Any],
) -> bytes:
    """Generate first frame with both characters together using fal.ai Nano Banana.

    Args:
        characters: Character data from planning (character_a, character_b)
        scene_setting: Scene setting from first scene (location, lighting)

    Returns:
        Image bytes
    """
    log_separator("First Frame Generation (fal.ai)")

    log(f"Model: {FAL_IMAGE_MODEL}")

    # Build character descriptions
    char_a = characters.get("character_a", {})
    char_b = characters.get("character_b", {})

    char_a_name = char_a.get("name", "Character A")
    char_a_desc = char_a.get("description", "Korean woman in her 50s")
    char_b_name = char_b.get("name", "Character B")
    char_b_desc = char_b.get("description", "Korean woman in her 20s")

    location = scene_setting.get("location", "luxurious living room")
    lighting = scene_setting.get("lighting", "dramatic lighting")

    prompt = FIRST_FRAME_PROMPT.format(
        char_a_name=char_a_name,
        char_a_desc=char_a_desc,
        char_b_name=char_b_name,
        char_b_desc=char_b_desc,
        location=location,
        lighting=lighting,
    )

    log(f"Prompt: {prompt[:200]}...")

    try:
        result = fal_client.subscribe(
            FAL_IMAGE_MODEL,
            arguments={
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
            with_logs=True,
        )

        images = result.get("images", [])
        if not images:
            raise ValueError(f"No images in response: {result}")

        image_url = images[0].get("url")
        log(f"Downloading image from: {image_url[:60]}...")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        image_bytes = response.content

        log(f"First frame generated: {len(image_bytes)} bytes", "SUCCESS")

        return image_bytes

    except Exception as e:
        log(f"Failed to generate first frame: {e}", "ERROR")
        raise


def generate_cta_last_frame(
    scene1_last_frame_url: str,
    product_image_url: str,
    product_detail: dict[str, Any],
    characters: dict[str, Any],
    cta_action: str | None = None,
) -> bytes:
    """Generate CTA last frame by compositing scene1 last frame with product.

    Uses fal.ai Nano Banana edit mode with multiple reference images to create a natural
    product placement scene that maintains character continuity.

    Args:
        scene1_last_frame_url: URL of the last frame from Scene 1
        product_image_url: URL of the product image
        product_detail: Product information (name, description, key_benefit)
        characters: Character data for context
        cta_action: Action/dialogue description from Scene 2's last timeline sequence

    Returns:
        Image bytes
    """
    log_separator("CTA Frame Generation (fal.ai)")

    log(f"Model: {FAL_IMAGE_EDIT_MODEL}")
    log(f"Scene1 last frame URL: {scene1_last_frame_url[:60]}...")
    log(f"Product image URL: {product_image_url[:60]}...")

    # Build product description
    product_name = product_detail.get("name", "product")

    # Get character info for context
    char_a = characters.get("character_a", {})
    char_b = characters.get("character_b", {})
    char_a_name = char_a.get("name", "Character A")
    char_b_name = char_b.get("name", "Character B")

    action_desc = (
        f"Scene context: {cta_action} "
        if cta_action
        else "The characters react with surprised, amused expressions. "
    )
    prompt = CTA_FRAME_PROMPT.format(
        char_a_name=char_a_name,
        char_b_name=char_b_name,
        product_name=product_name,
        action_desc=action_desc,
    )

    log(f"Prompt: {prompt[:200]}...")

    try:
        # Use fal.ai edit model with image_urls for reference images
        result = fal_client.subscribe(
            FAL_IMAGE_EDIT_MODEL,
            arguments={
                "prompt": prompt,
                "image_urls": [scene1_last_frame_url, product_image_url],
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
            with_logs=True,
        )

        images = result.get("images", [])
        if not images:
            raise ValueError(f"No images in response: {result}")

        image_url = images[0].get("url")
        log(f"Downloading image from: {image_url[:60]}...")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        image_bytes = response.content

        log(f"CTA last frame generated: {len(image_bytes)} bytes", "SUCCESS")

        return image_bytes

    except Exception as e:
        log(f"Failed to generate CTA last frame: {e}", "ERROR")
        raise
