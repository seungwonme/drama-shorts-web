"""Video generator nodes - generates video segments using Replicate Veo."""

import tempfile
from pathlib import Path

from moviepy import VideoFileClip
from PIL import Image as PILImage

from ..exceptions import ModerationError
from ..services.prompt_sanitizer import quick_sanitize_names, sanitize_prompt_for_veo
from ..services.replicate_client import create_and_download_video
from ..state import SegmentVideo, VideoGeneratorState
from ..utils.logging import log, log_separator

# Maximum retry attempts for moderation errors
MAX_MODERATION_RETRIES = 2


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


def _generate_video_with_retry(
    prompt: str,
    first_frame: bytes | None,
    last_frame: bytes | None,
    duration: int,
    scene_num: int,
) -> bytes | None:
    """Generate video with retry logic for moderation errors.

    Args:
        prompt: Video generation prompt
        first_frame: Starting frame image bytes
        last_frame: Ending frame image bytes (for interpolation)
        duration: Video duration in seconds
        scene_num: Scene number for logging

    Returns:
        Video bytes or None if all retries failed
    """
    current_prompt = prompt
    for attempt in range(MAX_MODERATION_RETRIES + 1):
        try:
            video_bytes = create_and_download_video(
                prompt=current_prompt,
                first_frame=first_frame,
                last_frame=last_frame,
                duration=duration,
            )
            log(f"Scene {scene_num} generated: {len(video_bytes)} bytes")
            return video_bytes

        except ModerationError as e:
            if attempt < MAX_MODERATION_RETRIES:
                log(
                    f"Scene {scene_num} MODERATION error (attempt {attempt + 1}/{MAX_MODERATION_RETRIES + 1}): {e}",
                    "WARNING",
                )
                # Try different sanitization strategies
                if attempt == 0:
                    log("Attempting quick sanitization (regex-based)...")
                    current_prompt = quick_sanitize_names(current_prompt)
                else:
                    log("Attempting full sanitization (Gemini-based)...")
                    current_prompt = sanitize_prompt_for_veo(current_prompt)
                log("Retrying with sanitized prompt...")
                continue
            else:
                log(
                    f"Scene {scene_num} MODERATION error after {MAX_MODERATION_RETRIES + 1} attempts: {e}",
                    "WARNING",
                )
                return None

        except Exception as e:
            log(f"Scene {scene_num} generation failed: {e}", "ERROR")
            return None

    return None


def generate_scene1(state: VideoGeneratorState) -> dict:
    """Generate Scene 1 video using Replicate Veo.

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
    first_frame_image = state.get("first_frame_image")

    log_separator("Scene 1/2 Generation (HOOK)")

    log(f"Title: {seg.get('title', '(no title)')}")
    log(f"Duration: {seg['seconds']}s")
    log("Strategy: Scene 1 - image-to-video (first_frame from Nano Banana)")
    log(f"First frame (image): {'yes' if first_frame_image else 'no'}")

    log("Scene prompt (full):")
    print("-" * 40)
    print(seg["prompt"])
    print("-" * 40)

    # Generate video
    video_bytes = _generate_video_with_retry(
        prompt=seg["prompt"],
        first_frame=first_frame_image,
        last_frame=None,
        duration=seg["seconds"],
        scene_num=1,
    )

    if not video_bytes:
        return {
            "skipped_segments": [1],
            "error": "Scene 1 generation failed after all retries",
            "status": "scene1_failed",
        }

    # Extract last frame for Scene 2 continuity
    scene1_last_frame = extract_last_frame_from_bytes(video_bytes)
    log("Scene 1 processing complete!")

    # Build segment video data
    segment_video: SegmentVideo = {
        "video_bytes": video_bytes,
        "index": 0,
        "title": seg.get("title", "Scene 1"),
    }

    return {
        "segment_videos": [segment_video],
        "scene1_video_bytes": video_bytes,
        "scene1_last_frame_image": scene1_last_frame,
        "current_segment_index": 1,
        "status": "scene1_complete",
    }


def generate_scene2(state: VideoGeneratorState) -> dict:
    """Generate Scene 2 video using Replicate Veo.

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
    scene1_last_frame = state.get("scene1_last_frame_image")
    cta_last_frame = state.get("cta_last_frame_image")

    log_separator("Scene 2/2 Generation (CTA)")

    log(f"Title: {seg.get('title', '(no title)')}")
    log(f"Duration: {seg['seconds']}s")
    log("Strategy: Scene 2 - interpolation (scene1_last → cta_last with product)")
    log(f"First frame (scene1_last): {'yes' if scene1_last_frame else 'no'}")
    log(f"Last frame (cta_last): {'yes' if cta_last_frame else 'no'}")

    log("Scene prompt (full):")
    print("-" * 40)
    print(seg["prompt"])
    print("-" * 40)

    # Generate video with interpolation
    video_bytes = _generate_video_with_retry(
        prompt=seg["prompt"],
        first_frame=scene1_last_frame,
        last_frame=cta_last_frame,
        duration=seg["seconds"],
        scene_num=2,
    )

    if not video_bytes:
        return {
            "skipped_segments": [2],
            "error": "Scene 2 generation failed after all retries",
            "status": "scene2_failed",
        }

    log("Scene 2 processing complete!")

    # Build segment video data
    segment_video: SegmentVideo = {
        "video_bytes": video_bytes,
        "index": 1,
        "title": seg.get("title", "Scene 2"),
    }

    return {
        "segment_videos": [segment_video],
        "scene2_video_bytes": video_bytes,
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
