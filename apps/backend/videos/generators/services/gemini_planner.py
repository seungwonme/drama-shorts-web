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

    name: str = Field(description="Product/service name in Korean (e.g., '대모산 사주 강의', '비타민C 세럼')")
    description: str = Field(
        description="What the product/service does in English (e.g., 'Online fortune telling course teaching compatibility reading')"
    )
    key_benefit: str = Field(
        description="Main selling point that resolves the drama conflict (e.g., 'Learn to read compatibility yourself')"
    )


class CharacterDefinition(BaseModel):
    """Character definition - unchanging attributes for consistency across scenes."""

    id: str = Field(description="Unique identifier: 'A' for antagonist/authority figure, 'B' for protagonist/younger character")
    name: str = Field(description="Korean full name with surname (e.g., '김순자', '박지은')")
    gender: str = Field(description="Gender: 'female' or 'male'")
    age: str = Field(
        description="Specific age range (e.g., 'late 50s', 'early 30s', 'mid 20s') - be precise for AI image generation"
    )
    appearance: str = Field(
        description="""VERY DETAILED physical description in English. Must include ALL of:
- Height (e.g., '162cm', '175cm')
- Build (e.g., 'slim', 'athletic', 'stocky')
- Skin tone and texture (e.g., 'fair skin with visible age spots', 'tan complexion')
- Hair style, color, length (e.g., 'dyed jet-black hair pulled into tight bun with jade hairpin')
- Facial features (e.g., 'sharp angular face, thin lips, deep-set eyes with crow's feet')
- Distinguishing marks if any"""
    )
    clothing: str = Field(
        description="""VERY DETAILED clothing description in English. Must include ALL of:
- Main outfit with specific colors and materials (e.g., 'expensive deep purple silk hanbok')
- Patterns/embroidery details (e.g., 'intricate gold embroidery on collar')
- Accessories (e.g., 'jade bangle bracelet, small pearl earrings')
- Posture hints (e.g., 'stands with impeccable posture, chin slightly raised')"""
    )
    voice: str = Field(
        default="",
        description="Voice characteristics for TTS/audio (e.g., 'stern and commanding with sharp edge', 'soft and trembling, pleading tone')",
    )




# === PROMPT_TEMPLATE format for Veo (per scene) ===
class SceneSetting(BaseModel):
    """Scene setting/location."""

    location: str = Field(
        description="""DETAILED location description in Korean. Must include:
- Specific room/place type (e.g., '고급스러운 한옥 거실', '현대적인 펜트하우스 거실')
- Wall/floor materials (e.g., '어두운 오크 나무 패널 벽', '대리석 바닥')
- Key furniture and props (e.g., '전통 병풍이 배경에 펼쳐져 있음', '가죽 소파와 유리 테이블')
- Atmosphere details (e.g., '창밖으로 비가 내리는 모습이 보임')"""
    )
    lighting: str = Field(
        description="""DETAILED lighting description in Korean. Must include:
- Light source and direction (e.g., '창문에서 들어오는 희미한 자연광')
- Which parts are lit/shadowed (e.g., '순자의 얼굴 절반만 비춤', '지은의 뒤에서 역광')
- Mood created by lighting (e.g., '차가운 푸른빛이 긴장감을 조성')
- Any special lighting effects (e.g., '마지막에 제품에 스포트라이트처럼 조명 집중')"""
    )


class CameraSetup(BaseModel):
    """Camera configuration for cinematic video generation - scene-level settings only."""

    lens: str = Field(
        default="50mm",
        description="Lens focal length: '35mm' (wider, more context), '50mm' (natural), '85mm' (portrait, compressed)"
    )
    depth_of_field: str = Field(
        default="shallow, cinematic bokeh",
        description="DoF style: 'shallow, cinematic bokeh' (dramatic), 'deep focus' (documentary), 'product sharp with soft background'"
    )
    texture: str = Field(
        default="natural skin texture, realistic fabric folds",
        description="Visual texture for photorealism: 'natural skin texture, realistic fabric folds, subtle facial details', 'product details crisp and clear'"
    )


class MoodStyle(BaseModel):
    """Mood and visual style."""

    genre: str = Field(
        description="""Genre/mood description in English. Be specific:
- Scene 1: 'Intense Korean family drama confrontation', 'Tense chaebol inheritance dispute'
- Scene 2: 'Heartwarming resolution with B급 comedic twist', 'Surprised reconciliation moment'"""
    )
    color_tone: str = Field(
        description="""Color grading description. Include:
- Overall tone (e.g., 'desaturated', 'warm golden tones')
- Shadow color (e.g., 'teal shadows', 'cool blue shadows')
- Highlight color (e.g., 'warm orange highlights')
- Saturation level (e.g., 'increased saturation' for happy scenes)"""
    )


class AudioConfig(BaseModel):
    """Audio configuration for video."""

    background: str = Field(
        description="""Background music description. Include:
- Genre/style (e.g., 'Tense Korean drama OST', 'Gentle hopeful piano melody')
- Tempo (e.g., 'slow building tension', 'upbeat')
- Instruments if relevant (e.g., 'strings and piano', 'traditional Korean instruments')
- Transitions (e.g., 'transitioning to playful upbeat tune at mood shift')"""
    )
    fx: str = Field(
        description="""Sound effects with timing. Include:
- Ambient sounds (e.g., 'rain pattering on window', 'clock ticking')
- Action sounds (e.g., 'teacup placed on table', 'fabric rustling')
- Dramatic effects (e.g., 'thunder rumble', 'dramatic whoosh at mood shift')
- UI sounds if relevant (e.g., 'phone notification chime')"""
    )


class CharacterMoment(BaseModel):
    """Character's complete state at a specific moment in the timeline."""

    action: str = Field(
        description="""Physical action in ENGLISH. What this character does during this sequence.
Examples: 'places teacup firmly on table, lips curl into contemptuous sneer', 'wipes tears, lifts head to meet A\\'s gaze', 'stands motionless with arms crossed'
If character is not acting, use: 'remains still' or 'watches silently'"""
    )
    dialogue: str = Field(
        default="",
        description="""Korean dialogue spoken by this character. Leave empty if no dialogue.
Example: '우리 집안 며느리? 감히?'
⚠️ Only this character's lines - do NOT include other character's dialogue here."""
    )
    emotion: str = Field(
        description="""SINGLE emotional state. ONE emotion only, no transitions.
- ❌ BAD: 'Longing shifting to cold anger'
- ✅ GOOD: 'Cold contempt', 'Desperate heartbreak', 'Comical amazement', 'Relieved joy'"""
    )
    position: str = Field(
        description="""Exact position and posture at this moment.
- Frame position: 'left side of frame', 'center-right'
- Body posture: 'standing tall', 'kneeling', 'leaning forward'
- Relation to props/other: 'beside table', 'facing B', 'holding phone toward A'"""
    )


class TimelineEvent(BaseModel):
    """Timeline event within a scene - 2 seconds each, 4 events per scene."""

    sequence: int = Field(description="Event sequence number: 1, 2, 3, or 4")
    timestamp: str = Field(description="Timestamp range: '00:00-00:02', '00:02-00:04', '00:04-00:06', '00:06-00:08'")
    camera: str = Field(
        description="""Camera angle/shot type for this sequence.
Examples: '[CU on A]', '[CU on B]', '[TWO-SHOT]', '[Medium]', '[MCU on phone]', '[Wide shot]'
Scene 1 Seq 4 MUST be '[TWO-SHOT]'. Scene 2 Seq 4 should emphasize product."""
    )
    movement: str = Field(
        default="static",
        description="""Camera movement for this sequence.
Examples: 'static', 'subtle handheld', 'slow dolly back', 'smooth dolly in', 'slight crane up', 'static hold'
Be specific about the movement that happens during these 2 seconds."""
    )
    focus: str = Field(
        default="",
        description="""Focus description for this sequence.
Examples: 'sharp on A's eyes, B soft blur', 'rack focus to phone screen', 'deep focus both characters', 'product tack-sharp, characters soft'
Describe what should be sharp and what should be blurred."""
    )
    mood: str = Field(
        description="Emotional atmosphere in English (e.g., 'Icy contempt', 'Desperate plea', 'B급 comedic climax')"
    )
    sfx: str = Field(
        description="""Sound effects for this sequence (NOT dialogue). English description.
Examples: 'teacup ceramic clink + distant thunder', 'rain intensifying', 'phone notification ding + upbeat music starts'"""
    )
    A: CharacterMoment = Field(description="Character A's action, dialogue, emotion, and position at this moment")
    B: CharacterMoment = Field(description="Character B's action, dialogue, emotion, and position at this moment")


class ScenePrompt(BaseModel):
    """A single scene in PROMPT_TEMPLATE format for Veo."""

    scene_setting: SceneSetting = Field(description="Scene setting")
    camera_setup: CameraSetup = Field(description="Camera configuration")
    mood_style: MoodStyle = Field(description="Mood and style")
    audio: AudioConfig = Field(description="Audio configuration")
    timeline: list[TimelineEvent] = Field(description="Timeline of events with per-sequence character states")


class ScriptOutput(BaseModel):
    """Complete script output for dramatized ad."""

    product: Product = Field(description="Product information")
    characters: list[CharacterDefinition] = Field(description="Character definitions (list with id 'A', 'B', etc.)")
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
    for char in characters:
        log(f"Character {char.get('id', '?')}: {char.get('name', 'N/A')}")

    return data


def _build_character_description(char: dict[str, Any]) -> str:
    """Build full character description from structured fields."""
    parts = []
    if char.get("gender"):
        parts.append(f"Korean {char['gender']}")
    if char.get("age"):
        parts.append(char["age"])
    if char.get("appearance"):
        parts.append(char["appearance"])
    if char.get("clothing"):
        parts.append(char["clothing"])
    return ", ".join(parts) if parts else "Korean person"


def _get_character_by_id(characters: list[dict[str, Any]], char_id: str) -> dict[str, Any]:
    """Find character by id from characters list."""
    for char in characters:
        if char.get("id") == char_id:
            return char
    return {}


def generate_first_frame(
    characters: list[dict[str, Any]],
    scene_setting: dict[str, Any],
    first_sequence: dict[str, Any] | None = None,
) -> bytes:
    """Generate first frame with both characters together using fal.ai Nano Banana.

    Args:
        characters: Character list from planning (list with id 'A', 'B', etc.)
        scene_setting: Scene setting from first scene (location, lighting)
        first_sequence: First timeline sequence with character states (emotion, position, action)

    Returns:
        Image bytes
    """
    log_separator("First Frame Generation (fal.ai)")

    log(f"Model: {FAL_IMAGE_MODEL}")

    # Build character descriptions from list structure
    char_a = _get_character_by_id(characters, "A")
    char_b = _get_character_by_id(characters, "B")

    char_a_name = char_a.get("name", "Character A")
    char_a_desc = _build_character_description(char_a)
    char_b_name = char_b.get("name", "Character B")
    char_b_desc = _build_character_description(char_b)

    # Extract first sequence data
    seq_a = first_sequence.get("A", {}) if first_sequence else {}
    seq_b = first_sequence.get("B", {}) if first_sequence else {}

    char_a_emotion = seq_a.get("emotion", "intense")
    char_a_action = seq_a.get("action", "standing in confrontation pose")
    char_a_position = seq_a.get("position", "left side of frame")

    char_b_emotion = seq_b.get("emotion", "tense")
    char_b_action = seq_b.get("action", "standing in confrontation pose")
    char_b_position = seq_b.get("position", "right side of frame")

    camera = first_sequence.get("camera", "[TWO-SHOT]") if first_sequence else "[TWO-SHOT]"
    mood = first_sequence.get("mood", "dramatic tension") if first_sequence else "dramatic tension"

    log(f"First sequence - A: {char_a_emotion}, B: {char_b_emotion}")
    log(f"Camera: {camera}, Mood: {mood}")

    location = scene_setting.get("location", "luxurious living room")
    lighting = scene_setting.get("lighting", "dramatic lighting")

    prompt = FIRST_FRAME_PROMPT.format(
        char_a_name=char_a_name,
        char_a_desc=char_a_desc,
        char_b_name=char_b_name,
        char_b_desc=char_b_desc,
        char_a_emotion=char_a_emotion,
        char_a_action=char_a_action,
        char_a_position=char_a_position,
        char_b_emotion=char_b_emotion,
        char_b_action=char_b_action,
        char_b_position=char_b_position,
        location=location,
        lighting=lighting,
        camera=camera,
        mood=mood,
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
    first_frame_url: str,
    product_image_url: str,
    product_detail: dict[str, Any],
    characters: list[dict[str, Any]],
    last_sequence: dict[str, Any] | None = None,
    scene_setting: dict[str, Any] | None = None,
) -> bytes:
    """Generate CTA last frame by compositing first frame with product.

    Uses fal.ai Nano Banana edit mode with multiple reference images to create a natural
    product placement scene that maintains character continuity.

    Args:
        first_frame_url: URL of the first frame (for character consistency)
        product_image_url: URL of the product image
        product_detail: Product information (name, description, key_benefit)
        characters: Character list for context (list with id 'A', 'B', etc.)
        last_sequence: Last timeline sequence from Scene 2 with full character states
        scene_setting: Scene 2's scene setting (location, lighting)

    Returns:
        Image bytes
    """
    log_separator("CTA Frame Generation (fal.ai)")

    log(f"Model: {FAL_IMAGE_EDIT_MODEL}")
    log(f"First frame URL: {first_frame_url[:60]}...")
    log(f"Product image URL: {product_image_url[:60]}...")

    # Build product description
    product_name = product_detail.get("name", "product")

    # Get character info for context
    char_a = _get_character_by_id(characters, "A")
    char_b = _get_character_by_id(characters, "B")
    char_a_name = char_a.get("name", "Character A")
    char_b_name = char_b.get("name", "Character B")

    # Extract last sequence data for detailed prompt
    seq_a = last_sequence.get("A", {}) if last_sequence else {}
    seq_b = last_sequence.get("B", {}) if last_sequence else {}

    char_a_emotion = seq_a.get("emotion", "amused surprise")
    char_a_action = seq_a.get("action", "looking at product with surprised expression")
    char_a_position = seq_a.get("position", "left side of frame")

    char_b_emotion = seq_b.get("emotion", "relieved joy")
    char_b_action = seq_b.get("action", "holding product naturally")
    char_b_position = seq_b.get("position", "right side of frame")

    camera = last_sequence.get("camera", "[TWO-SHOT]") if last_sequence else "[TWO-SHOT]"
    mood = last_sequence.get("mood", "comedic twist ending") if last_sequence else "comedic twist ending"

    # Scene setting
    location = scene_setting.get("location", "same setting with warmer atmosphere") if scene_setting else "warm, bright setting"
    lighting = scene_setting.get("lighting", "warm golden lighting") if scene_setting else "warm golden lighting"

    log(f"Last sequence - A: {char_a_emotion}, B: {char_b_emotion}")
    log(f"Camera: {camera}, Mood: {mood}")

    prompt = CTA_FRAME_PROMPT.format(
        char_a_name=char_a_name,
        char_b_name=char_b_name,
        product_name=product_name,
        char_a_emotion=char_a_emotion,
        char_a_action=char_a_action,
        char_a_position=char_a_position,
        char_b_emotion=char_b_emotion,
        char_b_action=char_b_action,
        char_b_position=char_b_position,
        location=location,
        lighting=lighting,
        camera=camera,
        mood=mood,
    )

    log(f"Prompt: {prompt[:200]}...")

    try:
        # Use fal.ai edit model with image_urls for reference images
        result = fal_client.subscribe(
            FAL_IMAGE_EDIT_MODEL,
            arguments={
                "prompt": prompt,
                "image_urls": [first_frame_url, product_image_url],
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
