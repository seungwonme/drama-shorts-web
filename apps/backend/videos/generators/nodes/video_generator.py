"""Video generator nodes - generates video segments using fal.ai Veo."""

import tempfile
from pathlib import Path
from typing import Callable

from moviepy import VideoFileClip
from PIL import Image as PILImage

from ...constants import MAX_MODERATION_RETRIES
from ..exceptions import ModerationError
from ..services.fal_client import generate_video_from_image, generate_video_interpolation
from ..services.prompt_sanitizer import quick_sanitize_names, sanitize_prompt_for_veo
from ..state import VideoGeneratorState
from ..utils.logging import log, log_separator


def extract_last_frame_from_bytes(video_bytes: bytes) -> bytes:
    """Extract the last frame from video bytes.

    Args:
        video_bytes: Video file contents as bytes

    Returns:
        PNG image bytes of the last frame
    """
    log("Extracting last frame from video bytes...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        tmp_file.write(video_bytes)
        tmp_path = Path(tmp_file.name)

    try:
        with VideoFileClip(str(tmp_path)) as clip:
            # Get the last frame (at duration - small epsilon to avoid edge issues)
            last_time = max(0, clip.duration - 0.01)
            frame = clip.get_frame(last_time)

            # Convert numpy array to PIL Image and save to bytes
            pil_image = PILImage.fromarray(frame)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_tmp:
                pil_image.save(img_tmp.name)
                image_bytes = Path(img_tmp.name).read_bytes()
                Path(img_tmp.name).unlink()

            log(f"Last frame extracted: {len(image_bytes)} bytes")

        return image_bytes
    finally:
        # Clean up temp video file
        tmp_path.unlink(missing_ok=True)


def _generate_with_moderation_retry(
    generate_fn: Callable[..., bytes],
    scene_name: str,
    prompt: str,
    **kwargs,
) -> bytes | None:
    """Generate video with retry logic for moderation errors.

    Common retry wrapper for Scene 1 and Scene 2 generation.
    Applies progressive prompt sanitization on moderation failures.

    Args:
        generate_fn: The video generation function to call
        scene_name: Name of the scene for logging (e.g., "Scene 1", "Scene 2")
        prompt: Video generation prompt
        **kwargs: Additional arguments passed to generate_fn

    Returns:
        Video bytes or None if all retries failed
    """
    current_prompt = prompt
    for attempt in range(MAX_MODERATION_RETRIES + 1):
        try:
            video_bytes = generate_fn(prompt=current_prompt, **kwargs)
            log(f"{scene_name} generated: {len(video_bytes)} bytes")
            return video_bytes

        except ModerationError as e:
            if attempt < MAX_MODERATION_RETRIES:
                log(
                    f"{scene_name} MODERATION error (attempt {attempt + 1}/{MAX_MODERATION_RETRIES + 1}): {e}",
                    "WARNING",
                )
                # Progressive sanitization strategies
                if attempt == 0:
                    # First try: quick regex-based sanitization
                    log("Attempting quick sanitization (regex-based)...")
                    current_prompt = quick_sanitize_names(current_prompt)
                elif attempt == 1:
                    # Second try: Gemini-based full sanitization
                    log("Attempting full sanitization (Gemini-based)...")
                    current_prompt = sanitize_prompt_for_veo(prompt)  # From original
                else:
                    # Third+ try: Apply both sanitizations progressively
                    log(f"Attempting combined sanitization (attempt {attempt + 1})...")
                    # Re-sanitize the already sanitized prompt
                    current_prompt = sanitize_prompt_for_veo(current_prompt)
                log("Retrying with sanitized prompt...")
                continue
            else:
                log(
                    f"{scene_name} MODERATION error after {MAX_MODERATION_RETRIES + 1} attempts: {e}",
                    "WARNING",
                )
                return None

        except Exception as e:
            log(f"{scene_name} generation failed: {e}", "ERROR")
            return None

    return None


def generate_scene1(state: VideoGeneratorState) -> dict:
    """Generate Scene 1 video using fal.ai Veo.

    Scene 1 (HOOK): image-to-video from first_frame (Nano Banana generated)
    - Video starts from the pre-generated first frame
    - Extract last frame after generation for Scene 2 continuity
    """
    segments = state["segments"]

    if not segments:
        return {
            "error": "No segments available for Scene 1",
            "status": "scene1_failed",
        }

    seg = segments[0]
    first_frame_url = state.get("first_frame_url")

    log_separator("Scene 1/2 Generation (HOOK)")

    log(f"Title: {seg.get('title', '(no title)')}")
    log(f"Duration: {seg['seconds']}s")
    log("Strategy: Scene 1 - image-to-video (first_frame from Nano Banana)")
    log(f"First frame URL: {'yes' if first_frame_url else 'no'}")

    log("Scene prompt (full):")
    print("-" * 40)
    print(seg["prompt"])
    print("-" * 40)

    if not first_frame_url:
        return {
            "error": "No first_frame_url available for Scene 1",
            "status": "scene1_failed",
        }

    # Generate video using URL directly (fal.ai accepts URLs)
    video_bytes = _generate_with_moderation_retry(
        generate_fn=generate_video_from_image,
        scene_name="Scene 1",
        prompt=seg["prompt"],
        first_frame_url=first_frame_url,
        duration=seg["seconds"],
    )

    if not video_bytes:
        return {
            "skipped_segments": [1],
            "error": "Scene 1 generation failed after all retries",
            "status": "scene1_failed",
        }

    # Extract last frame for Scene 2 continuity
    scene1_last_frame_bytes = extract_last_frame_from_bytes(video_bytes)
    log("Scene 1 processing complete!")

    # Note: video_bytes and scene1_last_frame_bytes returned as bytes
    # services.py will save to S3 and inject URLs for next node
    return {
        "_scene1_video_bytes": video_bytes,  # Temporary: saved by services.py
        "_scene1_last_frame_bytes": scene1_last_frame_bytes,  # Temporary: saved by services.py
        "_scene1_title": seg.get("title", "Scene 1"),  # For segment record
        "current_segment_index": 1,
        "status": "scene1_complete",
    }


def generate_scene2(state: VideoGeneratorState) -> dict:
    """Generate Scene 2 video using fal.ai Veo.

    Scene 2 (CTA): interpolation mode (image → last_frame)
    - Creates transition from scene1 end to product reveal
    - CTA last frame already generated by prepare_cta_frame node
    """
    segments = state["segments"]

    if len(segments) < 2:
        log("No Scene 2 segment available, skipping")
        return {
            "current_segment_index": 2,
            "status": "scene2_skipped",
        }

    seg = segments[1]
    scene1_last_frame_url = state.get("scene1_last_frame_url")
    cta_last_frame_url = state.get("cta_last_frame_url")

    log_separator("Scene 2/2 Generation (CTA)")

    log(f"Title: {seg.get('title', '(no title)')}")
    log(f"Duration: {seg['seconds']}s")
    log("Strategy: Scene 2 - interpolation (scene1_last → cta_last with product)")
    log(f"First frame URL (scene1_last): {'yes' if scene1_last_frame_url else 'no'}")
    log(f"Last frame URL (cta_last): {'yes' if cta_last_frame_url else 'no'}")

    log("Scene prompt (full):")
    print("-" * 40)
    print(seg["prompt"])
    print("-" * 40)

    if not scene1_last_frame_url or not cta_last_frame_url:
        return {
            "error": "Missing frame URLs for Scene 2 interpolation",
            "status": "scene2_failed",
        }

    # Generate video with interpolation using URLs directly (fal.ai accepts URLs)
    video_bytes = _generate_with_moderation_retry(
        generate_fn=generate_video_interpolation,
        scene_name="Scene 2",
        prompt=seg["prompt"],
        first_frame_url=scene1_last_frame_url,
        last_frame_url=cta_last_frame_url,
        duration=seg["seconds"],
    )

    if not video_bytes:
        return {
            "skipped_segments": [2],
            "error": "Scene 2 generation failed after all retries",
            "status": "scene2_failed",
        }

    log("Scene 2 processing complete!")

    # Note: video_bytes returned as bytes
    # services.py will save to S3 and inject URL
    return {
        "_scene2_video_bytes": video_bytes,  # Temporary: saved by services.py
        "_scene2_title": seg.get("title", "Scene 2"),  # For segment record
        "current_segment_index": 2,
        "status": "scene2_complete",
    }


# Legacy function for backwards compatibility (if needed)
def generate_video_segment(state: VideoGeneratorState) -> dict:
    """Generate a single video segment using Replicate Veo.

    DEPRECATED: Use generate_scene1 and generate_scene2 instead.
    Kept for backwards compatibility during transition.
    """
    current_idx = state.get("current_segment_index", 0)

    if current_idx == 0:
        return generate_scene1(state)
    elif current_idx == 1:
        return generate_scene2(state)
    else:
        return {
            "current_segment_index": current_idx + 1,
            "status": "generation_complete",
        }
