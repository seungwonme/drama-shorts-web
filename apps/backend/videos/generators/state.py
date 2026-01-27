"""State definition for LangGraph video generation workflow."""

import operator
from typing import Annotated, Any, TypedDict


class SegmentData(TypedDict):
    """Data for a single video segment."""

    title: str
    seconds: int
    prompt: str
    raw_data: dict[str, Any]


class CharacterDetail(TypedDict):
    """Detailed character information for consistency."""

    name: str
    description: str  # Full English description for prompt injection


class ProductDetail(TypedDict):
    """Product information for prompt enhancement."""

    name: str
    description: str
    key_benefit: str


class SegmentVideo(TypedDict):
    """Generated video segment data."""

    video_bytes: bytes
    index: int
    title: str


class VideoGeneratorState(TypedDict):
    """State for the video generation workflow."""

    # User input
    topic: str
    script: str | None  # Optional: user-provided storyline/script
    product_image_url: str | None  # Optional: URL to product image for CTA frame

    # Product info (from Django Product model)
    product_brand: str | None  # 제품 브랜드
    product_description: str | None  # 제품 설명

    # Asset URLs (from S3 VideoAsset model, injected by services.py)
    last_cta_image_url: str | None  # Last CTA 이미지 URL
    sound_effect_url: str | None  # 효과음 URL

    # Planning results (from plan_script node)
    script_json: dict[str, Any] | None  # Raw JSON from Gemini planning
    product_detail: ProductDetail | None  # Extracted product info
    character_details: dict[str, CharacterDetail] | None  # character_a, character_b with full descriptions

    # Asset preparation results (from prepare_assets node)
    segments: list[SegmentData]

    # Frame images for new workflow:
    # Step 1: Nano Banana generates first frame with both characters
    # Step 2: Veo generates Scene 1 (image=first_frame) → extract last frame
    # Step 3: Nano Banana generates CTA last frame (scene1_last + product)
    # Step 4: Veo generates Scene 2 (image=scene1_last, last_frame=cta_last)
    first_frame_image: bytes | None  # Scene 1 starting frame (both characters)
    cta_last_frame_image: bytes | None  # Scene 2 ending frame (with product)

    # Current processing state
    current_segment_index: int

    # Generated video segments as bytes (uses reducer for accumulation)
    # Each tuple: (video_bytes, metadata_dict)
    segment_videos: Annotated[list[SegmentVideo], operator.add]

    # Last frame image for scene continuity
    scene1_last_frame_image: bytes | None  # Last frame of Scene 1 for Scene 2 start

    # Skipped segments due to errors (uses reducer for accumulation)
    skipped_segments: Annotated[list[int], operator.add]

    # Final output as bytes
    final_video_bytes: bytes | None

    # Error handling
    error: str | None

    # Status tracking
    status: str
