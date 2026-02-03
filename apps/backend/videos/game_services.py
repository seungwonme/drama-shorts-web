"""Services for game character shorts generation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile

from .generators.game_state import GameGeneratorState
from .generators.nodes import (
    generate_game_frames,
    generate_game_videos,
    merge_game_videos,
    plan_game_scripts,
)
from .status_config import (
    GAME_NODE_ORDER,
    GAME_NODE_TO_STATUS,
    get_game_resume_node,
)

if TYPE_CHECKING:
    from .models import GameFrame, VideoGenerationJob

logger = logging.getLogger(__name__)

# Map node names to functions
GAME_NODE_FUNCTIONS = {
    "plan_game_scripts": plan_game_scripts,
    "generate_game_frames": generate_game_frames,
    "generate_game_videos": generate_game_videos,
    "merge_game_videos": merge_game_videos,
}


def _generate_game_video(
    job: VideoGenerationJob, start_from: str | None = None
) -> None:
    """Core game video generation logic.

    Executes nodes sequentially, saving results after each step.

    Args:
        job: VideoGenerationJob instance (job_type="game")
        start_from: Node name to start from (None = start from beginning)
    """
    from .models import VideoGenerationJob

    try:
        # Build initial or resume state
        if start_from is None:
            current_state = _build_game_initial_state(job)
            nodes_to_execute = GAME_NODE_ORDER
        else:
            current_state = _build_game_resume_state(job)
            job.error_message = ""
            job.save()
            start_idx = GAME_NODE_ORDER.index(start_from)
            nodes_to_execute = GAME_NODE_ORDER[start_idx:]

        # Execute nodes sequentially
        for node_name in nodes_to_execute:
            _update_game_job_status_for_node(job, node_name)

            node_func = GAME_NODE_FUNCTIONS[node_name]
            result = node_func(current_state)

            current_state = _save_and_inject_game_urls(
                job, node_name, result, current_state
            )

            if result.get("error"):
                _handle_game_node_error(job, result["error"])
                raise RuntimeError(result["error"])

        _mark_game_completed(job)

    except Exception as e:
        _handle_game_exception(job, e)
        raise


def _handle_game_node_error(job: VideoGenerationJob, error_message: str) -> None:
    """Handle error returned from a game node."""
    from .models import VideoGenerationJob

    job.failed_at_status = job.status
    job.status = VideoGenerationJob.Status.FAILED
    job.error_message = error_message
    job.save()


def _handle_game_exception(job: VideoGenerationJob, exception: Exception) -> None:
    """Handle unexpected exception during game generation."""
    from .models import VideoGenerationJob

    logger.exception("Game video generation failed for job %d: %s", job.id, exception)

    if not job.failed_at_status:
        job.failed_at_status = job.status
    job.status = VideoGenerationJob.Status.FAILED
    job.error_message = str(exception)
    job.save()


def _mark_game_completed(job: VideoGenerationJob) -> None:
    """Mark game job as successfully completed."""
    from .models import VideoGenerationJob

    job.status = VideoGenerationJob.Status.COMPLETED
    job.current_step = "완료"
    job.failed_at_status = ""
    job.save()


def generate_game_video_sync(job: VideoGenerationJob) -> None:
    """동기식 게임 영상 생성.

    5개의 4초 씬을 생성하고 페이드 효과로 병합합니다.

    Args:
        job: VideoGenerationJob 인스턴스 (job_type="game")
    """
    _generate_game_video(job, start_from=None)


def _build_game_initial_state(job: VideoGenerationJob) -> GameGeneratorState:
    """Build initial game state from job."""
    return {
        "character_image_url": job.character_image.url if job.character_image else "",
        "game_name": job.game_name or "",
        "user_prompt": job.user_prompt or "",
        # Initialize empty fields
        "character_description": None,
        "game_locations_used": [],
        "scripts": [],
        "frame_urls": [],
        "video_urls": [],
        "final_video_url": None,
        "error": None,
        "status": "pending",
    }


def _update_game_job_status_for_node(job: VideoGenerationJob, node_name: str) -> None:
    """Update job status based on current game node."""
    if node_name in GAME_NODE_TO_STATUS:
        job.status, job.current_step = GAME_NODE_TO_STATUS[node_name]
        job.save()


def _save_and_inject_game_urls(
    job: VideoGenerationJob,
    node_name: str,
    result: dict,
    state: GameGeneratorState,
) -> GameGeneratorState:
    """Save bytes to S3 and inject URLs into state for next node."""
    from .models import GameFrame

    # Merge non-temporary results into state
    for key, value in result.items():
        if not key.startswith("_"):
            state[key] = value

    if node_name == "plan_game_scripts":
        # Save planning results to job
        if result.get("character_description"):
            job.character_description = result["character_description"]
        if result.get("game_locations_used"):
            job.game_locations_used = result["game_locations_used"]
        if result.get("scripts"):
            job.script_json = result["scripts"]

        # Create GameFrame records
        _create_game_frames(job, result.get("scripts", []))
        job.save()

    elif node_name == "generate_game_frames":
        # Save frame images to S3 and inject URLs
        frame_results = result.get("_frame_results", [])
        frame_urls = []

        for fr in frame_results:
            scene_num = fr.get("scene")
            image_bytes = fr.get("_image_bytes")

            if image_bytes:
                game_frame = job.game_frames.filter(scene_number=scene_num).first()
                if game_frame:
                    game_frame.image_file.save(
                        f"frame_{scene_num:02d}.png",
                        ContentFile(image_bytes),
                    )
                    game_frame.image_url = fr.get("image_url", "")
                    game_frame.save()
                    frame_urls.append(game_frame.image_file.url)

        state["frame_urls"] = frame_urls
        job.save()

    elif node_name == "generate_game_videos":
        # Save video files to S3 and inject URLs
        video_results = result.get("_video_results", [])
        video_urls = []

        for vr in video_results:
            scene_num = vr.get("scene")
            video_bytes = vr.get("_video_bytes")

            if video_bytes:
                game_frame = job.game_frames.filter(scene_number=scene_num).first()
                if game_frame:
                    game_frame.video_file.save(
                        f"video_{scene_num:02d}.mp4",
                        ContentFile(video_bytes),
                    )
                    game_frame.video_url = vr.get("video_url", "")
                    game_frame.save()
                    video_urls.append(game_frame.video_file.url)

        state["video_urls"] = video_urls
        job.save()

    elif node_name == "merge_game_videos":
        # Save final video to S3
        final_video_bytes = result.get("_final_video_bytes")
        if final_video_bytes:
            job.final_video.save(
                f"job_{job.id}_final.mp4",
                ContentFile(final_video_bytes),
            )
            state["final_video_url"] = job.final_video.url
        job.save()

    return state


def _create_game_frames(job: VideoGenerationJob, scripts: list[dict]) -> None:
    """Create GameFrame records from scripts."""
    from django.db import transaction

    from .models import GameFrame

    with transaction.atomic():
        # Delete existing frames for this job
        job.game_frames.all().delete()

        # Bulk create new frames
        frames_to_create = [
            GameFrame(
                job=job,
                scene_number=script.get("scene", i + 1),
                shot_type=script.get("shot_type", ""),
                game_location=script.get("game_location", ""),
                prompt=script.get("prompt", ""),
                action=script.get("action", ""),
                camera=script.get("camera", ""),
                description_kr=script.get("description_kr", ""),
            )
            for i, script in enumerate(scripts)
        ]
        GameFrame.objects.bulk_create(frames_to_create)


def get_game_resume_entry_point(job: VideoGenerationJob) -> str:
    """Return the node to resume from based on failure point."""
    resume_status = job.failed_at_status or job.status
    return get_game_resume_node(resume_status)


def _build_game_resume_state(job: VideoGenerationJob) -> GameGeneratorState:
    """Build state from DB for resuming from failure point."""
    state = {
        "character_image_url": job.character_image.url if job.character_image else "",
        "game_name": job.game_name or "",
        "user_prompt": job.user_prompt or "",
        # Load existing results
        "character_description": job.character_description,
        "game_locations_used": job.game_locations_used or [],
        "scripts": job.script_json or [],
        "frame_urls": [],
        "video_urls": [],
        "final_video_url": job.final_video.url if job.final_video else None,
        "error": None,
        "status": "resuming",
    }

    # Load frame and video URLs from GameFrame records
    for frame in job.game_frames.order_by("scene_number"):
        if frame.image_file:
            state["frame_urls"].append(frame.image_file.url)
        if frame.video_file:
            state["video_urls"].append(frame.video_file.url)

    return state


def generate_game_video_with_resume(job: VideoGenerationJob) -> None:
    """Resume game video generation from failure point."""
    entry_point = get_game_resume_entry_point(job)

    # Start from beginning if needed
    if entry_point == "plan_game_scripts":
        return generate_game_video_sync(job)

    _generate_game_video(job, start_from=entry_point)


# =============================================================================
# Async Game Video Generation
# =============================================================================


def generate_game_video_async(job_id: int, resume: bool = False) -> None:
    """Run game video generation in a background thread.

    Args:
        job_id: ID of the VideoGenerationJob to process
        resume: If True, resume from failure point
    """
    import threading

    from django import db

    def _run_in_thread():
        db.connections.close_all()

        from .models import VideoGenerationJob

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)

            if resume:
                entry_point = get_game_resume_entry_point(job)
                if entry_point == "plan_game_scripts":
                    generate_game_video_sync(job)
                else:
                    _generate_game_video(job, start_from=entry_point)
            else:
                generate_game_video_sync(job)
        except VideoGenerationJob.DoesNotExist:
            pass
        except Exception:
            pass
        finally:
            db.connections.close_all()

    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
