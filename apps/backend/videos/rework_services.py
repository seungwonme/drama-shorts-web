"""Rework services for regenerating specific steps of video generation.

These functions allow re-running individual steps of the video generation pipeline
for completed VideoGenerationJob instances.
"""

import tempfile
from pathlib import Path

from django.core.files.base import ContentFile

from .generators.nodes.video_generator import extract_last_frame_from_bytes
from .generators.services.fal_client import (
    generate_video_from_image,
    generate_video_interpolation,
)
from .generators.services.gemini_planner import (
    generate_cta_last_frame,
    generate_first_frame,
)
from .generators.utils.media import download_video_from_url
from .generators.utils.video import concatenate_segments
from .models import VideoGenerationJob, VideoSegment


def regenerate_first_frame(job: VideoGenerationJob) -> bytes:
    """Regenerate the first frame image using Nano Banana.

    Requires: job.script_json (characters, scene_setting, first timeline sequence)
    Updates: job.first_frame

    Args:
        job: VideoGenerationJob instance with completed script_json

    Returns:
        Generated first frame image bytes
    """
    if not job.script_json:
        raise ValueError("script_json is required to regenerate first frame")

    characters = job.script_json.get("characters", [])
    scenes = job.script_json.get("scenes", [])

    if not scenes:
        raise ValueError("No scenes found in script_json")

    first_scene = scenes[0]
    scene_setting = first_scene.get("scene_setting", {})
    timeline = first_scene.get("timeline", [])
    first_sequence = timeline[0] if timeline else None

    # Generate first frame with full script context
    first_frame_bytes = generate_first_frame(characters, scene_setting, first_sequence)

    # Save to job
    job.first_frame.save(
        f"job_{job.id}_first_frame.png",
        ContentFile(first_frame_bytes),
    )
    job.save()

    return first_frame_bytes


def regenerate_scene1(job: VideoGenerationJob) -> bytes:
    """Regenerate Scene 1 video using fal.ai Veo.

    Requires: job.first_frame (URL), job.segments[0].prompt
    Updates: job.segments[0].video_file, job.scene1_last_frame

    Args:
        job: VideoGenerationJob instance with first_frame

    Returns:
        Generated video bytes
    """
    if not job.first_frame:
        raise ValueError("first_frame is required to regenerate Scene 1")

    # Get segment 0
    try:
        segment = job.segments.get(segment_index=0)
    except VideoSegment.DoesNotExist:
        raise ValueError("Scene 1 segment (index 0) not found")

    if not segment.prompt:
        raise ValueError("Scene 1 segment prompt is required")

    # fal.ai accepts URLs directly
    first_frame_url = job.first_frame.url

    # Generate Scene 1 video (image-to-video mode)
    video_bytes = generate_video_from_image(
        prompt=segment.prompt,
        first_frame_url=first_frame_url,
        duration=segment.seconds or 8,
    )

    # Extract last frame for Scene 2
    scene1_last_frame_bytes = extract_last_frame_from_bytes(video_bytes)

    # Save segment video
    segment.video_file.save(
        f"segment_01.mp4",
        ContentFile(video_bytes),
    )
    segment.status = VideoSegment.Status.COMPLETED
    segment.save()

    # Save scene1 last frame to job
    job.scene1_last_frame.save(
        f"job_{job.id}_scene1_last.png",
        ContentFile(scene1_last_frame_bytes),
    )
    job.save()

    return video_bytes


def regenerate_cta_last_frame(job: VideoGenerationJob) -> bytes:
    """Regenerate CTA last frame image using fal.ai Nano Banana.

    Requires: job.first_frame (URL), job.effective_product_image_url, job.script_json
    Updates: job.cta_last_frame

    Args:
        job: VideoGenerationJob instance with first_frame and script_json

    Returns:
        Generated CTA last frame image bytes
    """
    if not job.first_frame:
        raise ValueError("first_frame is required to regenerate CTA last frame")

    if not job.effective_product_image_url:
        raise ValueError("Product image URL is required to regenerate CTA last frame")

    # fal.ai accepts URLs directly
    first_frame_url = job.first_frame.url

    # Get Scene 2's last sequence and scene_setting from script
    last_sequence, scene2_setting = _get_scene2_last_sequence(job.script_json)

    # Generate CTA last frame (fal.ai accepts URLs directly)
    cta_last_bytes = generate_cta_last_frame(
        first_frame_url=first_frame_url,
        product_image_url=job.effective_product_image_url,
        product_detail=job.product_detail or {},
        characters=job.script_json.get("characters", []) if job.script_json else [],
        last_sequence=last_sequence,
        scene_setting=scene2_setting,
    )

    # Save to job
    job.cta_last_frame.save(
        f"job_{job.id}_cta_last.png",
        ContentFile(cta_last_bytes),
    )
    job.save()

    return cta_last_bytes


def regenerate_scene2(job: VideoGenerationJob) -> bytes:
    """Regenerate Scene 2 video using fal.ai Veo interpolation mode.

    Requires: job.scene1_last_frame (URL), job.cta_last_frame (URL), job.segments[1].prompt
    Updates: job.segments[1].video_file

    Args:
        job: VideoGenerationJob instance with scene1_last_frame and cta_last_frame

    Returns:
        Generated video bytes
    """
    if not job.scene1_last_frame:
        raise ValueError("scene1_last_frame is required to regenerate Scene 2")

    if not job.cta_last_frame:
        raise ValueError("cta_last_frame is required to regenerate Scene 2")

    # Get segment 1
    try:
        segment = job.segments.get(segment_index=1)
    except VideoSegment.DoesNotExist:
        raise ValueError("Scene 2 segment (index 1) not found")

    if not segment.prompt:
        raise ValueError("Scene 2 segment prompt is required")

    # fal.ai accepts URLs directly
    scene1_last_frame_url = job.scene1_last_frame.url
    cta_last_frame_url = job.cta_last_frame.url

    # Generate Scene 2 video (interpolation mode)
    video_bytes = generate_video_interpolation(
        prompt=segment.prompt,
        first_frame_url=scene1_last_frame_url,
        last_frame_url=cta_last_frame_url,
        duration=segment.seconds or 8,
    )

    # Save segment video
    segment.video_file.save(
        f"segment_02.mp4",
        ContentFile(video_bytes),
    )
    segment.status = VideoSegment.Status.COMPLETED
    segment.save()

    return video_bytes


def regenerate_final_video(job: VideoGenerationJob) -> bytes:
    """Regenerate final video by concatenating all segments.

    Requires: job.segments with video_file (URLs)
    Updates: job.final_video

    Args:
        job: VideoGenerationJob instance with segment videos

    Returns:
        Final video bytes
    """
    # FileField stores empty string when no file, not NULL
    segments = job.segments.exclude(video_file="").order_by("segment_index")

    if not segments.exists():
        raise ValueError("No segment videos found to concatenate")

    # Download and write segment videos to temp files
    temp_paths = []
    try:
        for seg in segments:
            temp_path = Path(tempfile.gettempdir()) / f"segment_{seg.segment_index:02d}.mp4"
            # Download from URL
            video_bytes = download_video_from_url(seg.video_file.url)
            temp_path.write_bytes(video_bytes)
            temp_paths.append(temp_path)

        # Output path
        output_path = Path(tempfile.gettempdir()) / f"job_{job.id}_final.mp4"

        # Concatenate segments with CTA image and sound effect
        concatenate_segments(
            segment_paths=temp_paths,
            out_path=output_path,
            last_cta_image_url=job.effective_last_cta_image_url,
            sound_effect_url=job.effective_sound_effect_url,
        )

        # Read final video bytes
        final_video_bytes = output_path.read_bytes()

        # Save to job
        job.final_video.save(
            f"job_{job.id}_final.mp4",
            ContentFile(final_video_bytes),
        )
        job.save()

        return final_video_bytes

    finally:
        # Clean up temp files
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)
        output_path = Path(tempfile.gettempdir()) / f"job_{job.id}_final.mp4"
        output_path.unlink(missing_ok=True)


def _get_scene2_last_sequence(script_json: dict | None) -> tuple[dict | None, dict | None]:
    """Extract Scene 2's last sequence and scene_setting from script_json.

    Args:
        script_json: Script JSON from job

    Returns:
        Tuple of (last_sequence, scene2_setting) or (None, None)
    """
    if not script_json:
        return None, None

    scenes = script_json.get("scenes", [])
    if len(scenes) < 2:
        return None, None

    scene2 = scenes[1]
    scene2_setting = scene2.get("scene_setting", {})
    timeline = scene2.get("timeline", [])
    if not timeline:
        return None, scene2_setting

    # Get the last sequence (full data)
    last_seq = timeline[-1]
    return last_seq, scene2_setting
