"""Gemini API client for prompt planning and character image generation."""

import io
import json
from typing import Any

import replicate
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from ..config import GEMINI_API_KEY, PLANNER_MODEL, REPLICATE_IMAGE_MODEL
from ..constants import KOREAN_DRAMA_SYSTEM_PROMPT, SCRIPT_MODE_SYSTEM_PROMPT
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


def _normalize_script_data(data: dict, base_prompt: str) -> dict:
    """Normalize fallback JSON data to match expected schema.

    Handles cases where Gemini returns slightly different structures:
    - product as string instead of object
    - characters as array instead of object with character_a/character_b keys
    """
    # Normalize product
    product = data.get("product")
    if isinstance(product, str):
        data["product"] = {
            "name": product,
            "description": base_prompt,
            "key_benefit": "See product details",
        }

    # Normalize characters (array -> object)
    characters = data.get("characters")
    if isinstance(characters, list) and len(characters) >= 2:
        data["characters"] = {
            "character_a": {
                "name": characters[0].get("name", "Character A"),
                "description": characters[0].get("appearance", characters[0].get("description", "")),
            },
            "character_b": {
                "name": characters[1].get("name", "Character B"),
                "description": characters[1].get("appearance", characters[1].get("description", "")),
            },
        }
    elif isinstance(characters, list) and len(characters) == 1:
        data["characters"] = {
            "character_a": {
                "name": characters[0].get("name", "Character A"),
                "description": characters[0].get("appearance", characters[0].get("description", "")),
            },
            "character_b": {
                "name": "Character B",
                "description": "Secondary character",
            },
        }

    return data


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
) -> dict[str, Any]:
    """Generate dramatized ad script JSON using Gemini with structured output.

    This function only generates the raw script JSON.
    Prompt assembly is handled separately in the assets module.

    Args:
        base_prompt: The product/service to advertise
        script: Optional user-provided storyline/script
        product_brand: Optional brand name
        product_description: Optional product description

    Returns:
        Raw script JSON containing product, characters, and segments data
    """
    log_separator("AI Script Generation Started")

    # Build product info section
    product_info_parts = [f"광고할 제품/서비스: {base_prompt}"]
    if product_brand:
        product_info_parts.append(f"브랜드: {product_brand}")
    if product_description:
        product_info_parts.append(f"제품 설명: {product_description}")
    product_info = "\n".join(product_info_parts)

    # Choose system prompt based on whether script is provided
    if script:
        system_prompt = SCRIPT_MODE_SYSTEM_PROMPT
        user_input = f"""{product_info}

사용자 제공 스크립트/줄거리:
{script}

위 스크립트를 기반으로 드라마타이즈 광고 영상 프롬프트를 생성해주세요.
- 사용자의 줄거리와 대사를 최대한 보존하세요.
- 총 16초 (8초 + 8초) 2씬 구성입니다.
- 모든 묘사는 영어로, 대사만 한국어로 작성하세요.""".strip()
        log("Mode: Script-based generation")
    else:
        system_prompt = KOREAN_DRAMA_SYSTEM_PROMPT
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

    # Try structured output first, fallback to raw parsing
    try:
        log("Using structured output with Pydantic schema...")
        structured_llm = llm.with_structured_output(ScriptOutput)
        result: ScriptOutput = structured_llm.invoke(messages)
        data = result.model_dump()
    except Exception as struct_error:
        log(f"Structured output failed: {struct_error}", "WARNING")
        log("Falling back to raw JSON parsing...")

        # Fallback: get raw response and parse manually
        raw_response = llm.invoke(messages)
        raw_content = raw_response.content

        # Handle case where content is a list (e.g., [{'type': 'text', 'text': '...'}] or content blocks)
        # Note: langchain_google_genai may return content block objects, not plain dicts
        if not isinstance(raw_content, str):
            text_parts = []
            try:
                for item in raw_content:
                    # Try dict access first
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    # Try object attribute access (for content block objects)
                    elif hasattr(item, "text"):
                        text_parts.append(str(item.text))
                    # Try direct string conversion
                    elif isinstance(item, str):
                        text_parts.append(item)
            except (TypeError, AttributeError):
                pass  # Not iterable or other issue
            raw_content = "".join(text_parts) if text_parts else str(raw_content)

        log(f"Raw response (first 500 chars): {raw_content[:500]}")

        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if json_match:
            try:
                data = json.loads(json_match.group())
                log("Successfully parsed JSON from raw response")
            except json.JSONDecodeError as e:
                log(f"JSON parse error: {e}", "ERROR")
                raise
        else:
            log("No JSON found in response", "ERROR")
            raise ValueError("No valid JSON in response")

        # Normalize data to match expected schema
        data = _normalize_script_data(data, base_prompt)

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
    """Generate first frame with both characters together using Nano Banana.

    Args:
        characters: Character data from planning (character_a, character_b)
        scene_setting: Scene setting from first scene (location, lighting)

    Returns:
        Image bytes
    """
    log_separator("First Frame Generation (Nano Banana)")

    log(f"Model: {REPLICATE_IMAGE_MODEL}")

    # Build character descriptions
    char_a = characters.get("character_a", {})
    char_b = characters.get("character_b", {})

    char_a_name = char_a.get("name", "Character A")
    char_a_desc = char_a.get("description", "Korean woman in her 50s")
    char_b_name = char_b.get("name", "Character B")
    char_b_desc = char_b.get("description", "Korean woman in her 20s")

    location = scene_setting.get("location", "luxurious living room")
    lighting = scene_setting.get("lighting", "dramatic lighting")

    # Create scene prompt with both characters
    # IMPORTANT: Explicitly state this is a SINGLE scene, not split screen
    prompt = (
        f"A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage, NOT multiple panels). "
        f"Cinematic Korean drama moment in 9:16 portrait format for YouTube Shorts. "
        f"Setting: {location}. Lighting: {lighting}. "
        f"Two KOREAN people standing together in ONE unified scene: "
        f"On the LEFT - {char_a_name}: {char_a_desc}. "
        f"On the RIGHT - {char_b_name}: {char_b_desc}. "
        f"Both characters MUST be ethnically Korean with East Asian features. "
        f"They are facing each other in a dramatic confrontation pose. "
        f"Korean drama style cinematography, high quality, photorealistic, 4K resolution. "
        f"This is ONE single image with ONE continuous background, not divided into sections."
    )

    log(f"Prompt: {prompt[:200]}...")

    try:
        output = replicate.run(
            REPLICATE_IMAGE_MODEL,
            input={
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
        )

        # Handle FileOutput or URL response
        if hasattr(output, "read"):
            image_bytes = output.read()
        else:
            log(f"Downloading image from: {str(output)[:60]}...")
            response = requests.get(str(output), timeout=60)
            response.raise_for_status()
            image_bytes = response.content

        log(f"First frame generated: {len(image_bytes)} bytes", "SUCCESS")

        return image_bytes

    except Exception as e:
        log(f"Failed to generate first frame: {e}", "ERROR")
        raise


def generate_cta_last_frame(
    scene1_last_frame: bytes,
    product_image_url: str,
    product_detail: dict[str, Any],
    characters: dict[str, Any],
    cta_action: str | None = None,
) -> bytes:
    """Generate CTA last frame by compositing scene1 last frame with product.

    Uses Nano Banana with multiple reference images to create a natural
    product placement scene that maintains character continuity.

    Args:
        scene1_last_frame: Last frame from Scene 1 as bytes
        product_image_url: URL of the product image
        product_detail: Product information (name, description, key_benefit)
        characters: Character data for context
        cta_action: Action/dialogue description from Scene 2's last timeline sequence

    Returns:
        Image bytes
    """
    log_separator("CTA Last Frame Generation (Nano Banana)")

    log(f"Model: {REPLICATE_IMAGE_MODEL}")
    log(f"Product image URL: {product_image_url}")

    # Upload scene1 last frame to Replicate to get URL
    log("Uploading scene1 last frame to Replicate...")
    scene1_file = replicate.files.create(io.BytesIO(scene1_last_frame))
    scene1_frame_url = scene1_file.urls.get("get")
    log(f"Scene1 last frame URL: {scene1_frame_url[:60]}...")

    # Download and upload product image to Replicate (external URLs can cause E6716 error)
    log("Downloading and uploading product image to Replicate...")
    product_response = requests.get(product_image_url, timeout=60)
    product_response.raise_for_status()
    product_file = replicate.files.create(io.BytesIO(product_response.content))
    product_replicate_url = product_file.urls.get("get")
    log(f"Product image URL (Replicate): {product_replicate_url[:60]}...")

    # Build product description
    product_name = product_detail.get("name", "product")
    product_desc = product_detail.get("description", "")
    key_benefit = product_detail.get("key_benefit", "")

    # Get character info for context
    char_a = characters.get("character_a", {})
    char_b = characters.get("character_b", {})
    char_a_name = char_a.get("name", "Character A")
    char_b_name = char_b.get("name", "Character B")

    # Build action description from script
    if cta_action:
        action_desc = f"Scene context: {cta_action} "
    else:
        action_desc = "The characters react with surprised, amused expressions. "

    # Create prompt for LAST FRAME only
    # Note: This is the END FRAME for Veo interpolation.
    # The video BETWEEN frames can have crowds cheering, dramatic reactions, etc.
    # But this FINAL FRAME should have subtle product placement to avoid content filter.
    prompt = (
        f"A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage). "
        f"Korean drama comedic twist ending - the FINAL MOMENT of reconciliation. "
        f"IMPORTANT: Keep the EXACT SAME two characters ({char_a_name} and {char_b_name}) from the first reference image. "
        f"Their faces, clothing, and appearances must remain identical. "
        f"{action_desc}"
        f"The two main characters have amused, surprised expressions - this is the punchline moment. "
        f"PRODUCT PLACEMENT: The product from the SECOND reference image ('{product_name}') appears naturally in the scene - "
        f"on a table nearby, casually in one character's hand, or visible in the background. "
        f"The product is part of the scene, not presented to camera like an advertisement. "
        f"NOTE: This is the final frame. The VIDEO leading up to this can include crowd reactions, "
        f"dramatic reveals, and comedic buildup - but this ending frame shows the calm after the storm. "
        f"9:16 portrait format. "
        f"Warm, golden lighting. Comedic Korean drama atmosphere. "
        f"High quality, photorealistic, 4K resolution."
    )

    log(f"Prompt: {prompt[:200]}...")

    try:
        # Use BOTH scene1 last frame AND product image as references
        # Both must be Replicate URLs to avoid E6716 error
        input_params = {
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "output_format": "png",
            "image_input": [scene1_frame_url, product_replicate_url],
        }

        log(f"Using {len(input_params['image_input'])} reference images (both Replicate URLs)")

        output = replicate.run(REPLICATE_IMAGE_MODEL, input=input_params)

        # Handle FileOutput or URL response
        if hasattr(output, "read"):
            image_bytes = output.read()
        else:
            log(f"Downloading image from: {str(output)[:60]}...")
            response = requests.get(str(output), timeout=60)
            response.raise_for_status()
            image_bytes = response.content

        log(f"CTA last frame generated: {len(image_bytes)} bytes", "SUCCESS")

        return image_bytes

    except Exception as e:
        log(f"Failed to generate CTA last frame: {e}", "ERROR")
        raise
