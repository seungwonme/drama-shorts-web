"""Rework services for regenerating specific steps of video generation.

These functions allow re-running individual steps of the video generation pipeline
for completed VideoGenerationJob instances.
"""

import tempfile
from pathlib import Path

from django.core.files.base import ContentFile

from .generators.nodes.video_generator import extract_last_frame_from_bytes
from .generators.services.gemini_planner import (
    generate_cta_last_frame,
    generate_first_frame,
)
from .generators.services.replicate_client import create_and_download_video
from .generators.utils.video import concatenate_segments
from .models import VideoGenerationJob, VideoSegment


def regenerate_first_frame(job: VideoGenerationJob) -> bytes:
    """Regenerate the first frame image using Nano Banana.

    Requires: job.script_json (characters, scene_setting)
    Updates: job.first_frame

    Args:
        job: VideoGenerationJob instance with completed script_json

    Returns:
        Generated first frame image bytes
    """
    if not job.script_json:
        raise ValueError("script_json is required to regenerate first frame")

    characters = job.script_json.get("characters", {})
    scenes = job.script_json.get("scenes", [])

    if not scenes:
        raise ValueError("No scenes found in script_json")

    scene_setting = scenes[0].get("scene_setting", {})

    # Generate first frame
    first_frame_bytes = generate_first_frame(characters, scene_setting)

    # Save to job
    job.first_frame.save(
        f"job_{job.id}_first_frame.png",
        ContentFile(first_frame_bytes),
    )
    job.save()

    return first_frame_bytes


def regenerate_scene1(job: VideoGenerationJob) -> bytes:
    """Regenerate Scene 1 video using Veo.

    Requires: job.first_frame, job.segments[0].prompt
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

    # Read first frame bytes
    job.first_frame.seek(0)
    first_frame_bytes = job.first_frame.read()

    # Generate Scene 1 video (image-to-video mode)
    video_bytes = create_and_download_video(
        prompt=segment.prompt,
        first_frame=first_frame_bytes,
        last_frame=None,
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
    """Regenerate CTA last frame image using Nano Banana.

    Requires: job.scene1_last_frame, job.effective_product_image_url
    Updates: job.cta_last_frame

    Args:
        job: VideoGenerationJob instance with scene1_last_frame

    Returns:
        Generated CTA last frame image bytes
    """
    if not job.scene1_last_frame:
        raise ValueError("scene1_last_frame is required to regenerate CTA last frame")

    if not job.effective_product_image_url:
        raise ValueError("Product image URL is required to regenerate CTA last frame")

    # Read scene1 last frame bytes
    job.scene1_last_frame.seek(0)
    scene1_last_bytes = job.scene1_last_frame.read()

    # Get CTA action from script
    cta_action = _get_cta_action_from_script(job.script_json)

    # Generate CTA last frame
    cta_last_bytes = generate_cta_last_frame(
        scene1_last_frame=scene1_last_bytes,
        product_image_url=job.effective_product_image_url,
        product_detail=job.product_detail or {},
        characters=job.script_json.get("characters", {}) if job.script_json else {},
        cta_action=cta_action,
    )

    # Save to job
    job.cta_last_frame.save(
        f"job_{job.id}_cta_last.png",
        ContentFile(cta_last_bytes),
    )
    job.save()

    return cta_last_bytes


def regenerate_scene2(job: VideoGenerationJob) -> bytes:
    """Regenerate Scene 2 video using Veo interpolation mode.

    Requires: job.scene1_last_frame, job.cta_last_frame, job.segments[1].prompt
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

    # Read frame bytes
    job.scene1_last_frame.seek(0)
    scene1_last_bytes = job.scene1_last_frame.read()

    job.cta_last_frame.seek(0)
    cta_last_bytes = job.cta_last_frame.read()

    # Generate Scene 2 video (interpolation mode)
    video_bytes = create_and_download_video(
        prompt=segment.prompt,
        first_frame=scene1_last_bytes,  # image parameter
        last_frame=cta_last_bytes,  # interpolation to this frame
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

    Requires: job.segments with video_file
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

    # Write segment videos to temp files
    temp_paths = []
    try:
        for seg in segments:
            temp_path = Path(tempfile.gettempdir()) / f"segment_{seg.segment_index:02d}.mp4"
            seg.video_file.seek(0)
            temp_path.write_bytes(seg.video_file.read())
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


def _get_cta_action_from_script(script_json: dict | None) -> str | None:
    """Extract CTA action description from script_json.

    Args:
        script_json: Script JSON from job

    Returns:
        CTA action string or None
    """
    if not script_json:
        return None

    scenes = script_json.get("scenes", [])
    if len(scenes) < 2:
        return None

    scene2 = scenes[1]
    timeline = scene2.get("timeline", [])
    if not timeline:
        return None

    # Get the last sequence's action
    last_seq = timeline[-1]
    return last_seq.get("action", "")
