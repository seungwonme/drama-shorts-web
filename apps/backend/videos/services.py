"""Services for video generation using integrated generators package."""

from django.core.files.base import ContentFile

from .generators.prompts import VideoStyle
from .generators.nodes import (
    concatenate_videos,
    generate_scene1,
    generate_scene2,
    plan_script,
    prepare_cta_frame,
    prepare_first_frame,
)
from .generators.state import SegmentVideo, VideoGeneratorState


# Node execution order
NODE_ORDER = [
    "plan_script",
    "prepare_first_frame",
    "generate_scene1",
    "prepare_cta_frame",
    "generate_scene2",
    "concatenate_videos",
]

# Map node names to functions
NODE_FUNCTIONS = {
    "plan_script": plan_script,
    "prepare_first_frame": prepare_first_frame,
    "generate_scene1": generate_scene1,
    "prepare_cta_frame": prepare_cta_frame,
    "generate_scene2": generate_scene2,
    "concatenate_videos": concatenate_videos,
}


def generate_video_sync(job):
    """동기식 영상 생성 with incremental saving.

    generators의 노드들을 순차 실행하고 각 단계 완료 시 즉시 DB에 저장합니다.
    bytes는 S3에 저장 후 URL을 state에 주입하여 다음 노드에서 사용합니다.

    Args:
        job: VideoGenerationJob 인스턴스
    """
    from .models import VideoGenerationJob

    try:
        # 초기 상태 설정
        current_state = _build_initial_state(job)

        # 노드 순차 실행
        for node_name in NODE_ORDER:
            # 상태 업데이트
            _update_job_status_for_node(job, node_name)

            # 노드 함수 실행
            node_func = NODE_FUNCTIONS[node_name]
            result = node_func(current_state)

            # 결과를 DB/S3에 저장하고 URL을 state에 주입
            current_state = _save_and_inject_urls(job, node_name, result, current_state)

            # 에러 체크
            if result.get("error"):
                job.failed_at_status = job.status
                job.status = VideoGenerationJob.Status.FAILED
                job.error_message = result["error"]
                job.save()
                raise RuntimeError(result["error"])

        job.status = VideoGenerationJob.Status.COMPLETED
        job.current_step = "완료"
        job.failed_at_status = ""
        job.save()

    except Exception as e:
        import traceback
        traceback.print_exc()

        if not job.failed_at_status:
            job.failed_at_status = job.status
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise


def _build_initial_state(job) -> VideoGeneratorState:
    """Build initial state from job."""
    return {
        "topic": job.topic,
        "script": job.script if job.script else None,
        "product_image_url": job.effective_product_image_url,
        "video_style": VideoStyle(job.video_style),
        "product_brand": job.product.brand if job.product else None,
        "product_description": job.product.description if job.product else None,
        "last_cta_image_url": job.effective_last_cta_image_url,
        "sound_effect_url": job.effective_sound_effect_url,
        # Initialize URL fields (will be populated as nodes execute)
        "script_json": None,
        "product_detail": None,
        "character_details": None,
        "segments": [],
        "first_frame_url": None,
        "cta_last_frame_url": None,
        "current_segment_index": 0,
        "segment_videos": [],
        "scene1_video_url": None,
        "scene2_video_url": None,
        "scene1_last_frame_url": None,
        "skipped_segments": [],
        "final_video_url": None,
        "error": None,
        "status": "pending",
    }


def _update_job_status_for_node(job, node_name: str):
    """Update job status based on current node."""
    from .models import VideoGenerationJob

    status_map = {
        "plan_script": (VideoGenerationJob.Status.PLANNING, "AI 스크립트 기획"),
        "prepare_first_frame": (VideoGenerationJob.Status.PREPARING, "첫 프레임 생성"),
        "generate_scene1": (VideoGenerationJob.Status.GENERATING_S1, "Scene 1 생성"),
        "prepare_cta_frame": (VideoGenerationJob.Status.PREPARING_CTA, "CTA 프레임 생성"),
        "generate_scene2": (VideoGenerationJob.Status.GENERATING_S2, "Scene 2 생성"),
        "concatenate_videos": (VideoGenerationJob.Status.CONCATENATING, "영상 병합"),
    }

    if node_name in status_map:
        job.status, job.current_step = status_map[node_name]
        job.save()


def _save_and_inject_urls(job, node_name: str, result: dict, state: dict) -> dict:
    """Save bytes to S3 and inject URLs into state for next node."""
    from .models import VideoSegment

    # Merge non-temporary results into state
    for key, value in result.items():
        if not key.startswith("_"):  # Skip temporary byte fields
            if key == "segment_videos" and value:
                # segment_videos uses append reducer
                state["segment_videos"] = state.get("segment_videos", []) + value
            elif key == "skipped_segments" and value:
                # skipped_segments uses append reducer
                state["skipped_segments"] = state.get("skipped_segments", []) + value
            else:
                state[key] = value

    if node_name == "plan_script":
        # Save planning results
        if result.get("script_json"):
            job.script_json = result["script_json"]
        if result.get("product_detail"):
            job.product_detail = result["product_detail"]
        if result.get("character_details"):
            job.character_details = result["character_details"]
        job.save()

    elif node_name == "prepare_first_frame":
        # Save first frame to S3 and inject URL
        first_frame_bytes = result.get("_first_frame_bytes")
        if first_frame_bytes:
            job.first_frame.save(
                f"job_{job.id}_first_frame.png",
                ContentFile(first_frame_bytes),
            )
            # Inject URL for next node (generate_scene1)
            state["first_frame_url"] = job.first_frame.url

        # Create segment records
        segments_data = result.get("segments", [])
        _create_video_segments(job, segments_data)
        job.save()

    elif node_name == "generate_scene1":
        # Save Scene 1 video to S3 and inject URL
        scene1_video_bytes = result.get("_scene1_video_bytes")
        scene1_last_frame_bytes = result.get("_scene1_last_frame_bytes")
        scene1_title = result.get("_scene1_title", "Scene 1")

        if scene1_video_bytes:
            segment = job.segments.filter(segment_index=0).first()
            if segment:
                segment.video_file.save(
                    f"segment_01.mp4",
                    ContentFile(scene1_video_bytes),
                )
                segment.status = VideoSegment.Status.COMPLETED
                segment.save()

                # Inject URL for concatenate_videos
                segment_video: SegmentVideo = {
                    "video_url": segment.video_file.url,
                    "index": 0,
                    "title": scene1_title,
                }
                state["segment_videos"] = [segment_video]
                state["scene1_video_url"] = segment.video_file.url

        if scene1_last_frame_bytes:
            job.scene1_last_frame.save(
                f"job_{job.id}_scene1_last.png",
                ContentFile(scene1_last_frame_bytes),
            )
            # Inject URL for prepare_cta_frame and generate_scene2
            state["scene1_last_frame_url"] = job.scene1_last_frame.url

        job.save()

    elif node_name == "prepare_cta_frame":
        # Save CTA last frame to S3 and inject URL
        cta_last_frame_bytes = result.get("_cta_last_frame_bytes")
        if cta_last_frame_bytes:
            job.cta_last_frame.save(
                f"job_{job.id}_cta_last.png",
                ContentFile(cta_last_frame_bytes),
            )
            # Inject URL for generate_scene2
            state["cta_last_frame_url"] = job.cta_last_frame.url
        job.save()

    elif node_name == "generate_scene2":
        # Save Scene 2 video to S3 and inject URL
        scene2_video_bytes = result.get("_scene2_video_bytes")
        scene2_title = result.get("_scene2_title", "Scene 2")

        if scene2_video_bytes:
            segment = job.segments.filter(segment_index=1).first()
            if segment:
                segment.video_file.save(
                    f"segment_02.mp4",
                    ContentFile(scene2_video_bytes),
                )
                segment.status = VideoSegment.Status.COMPLETED
                segment.save()

                # Inject URL for concatenate_videos
                segment_video: SegmentVideo = {
                    "video_url": segment.video_file.url,
                    "index": 1,
                    "title": scene2_title,
                }
                state["segment_videos"] = state.get("segment_videos", []) + [segment_video]
                state["scene2_video_url"] = segment.video_file.url

        job.save()

    elif node_name == "concatenate_videos":
        # Save final video to S3
        final_video_bytes = result.get("_final_video_bytes")
        if final_video_bytes:
            job.final_video.save(
                f"job_{job.id}_final.mp4",
                ContentFile(final_video_bytes),
            )
            state["final_video_url"] = job.final_video.url

        # Save skipped segments
        skipped = result.get("skipped_segments", [])
        if skipped:
            job.skipped_segments = skipped
        job.save()

    return state


def _create_video_segments(job, segments_data: list):
    """Create segment records (for storing prompts).

    Uses update_or_create to prevent duplicate key errors.
    """
    from .models import VideoSegment

    # Delete excess segments
    job.segments.filter(segment_index__gte=len(segments_data)).delete()

    for i, seg_data in enumerate(segments_data):
        VideoSegment.objects.update_or_create(
            job=job,
            segment_index=i,
            defaults={
                "title": seg_data.get("title", f"Segment {i+1}"),
                "seconds": seg_data.get("seconds", 8),
                "prompt": seg_data.get("prompt", ""),
                "status": VideoSegment.Status.PENDING,
            },
        )


def get_resume_entry_point(job) -> str:
    """Return the node to resume from based on failure point."""
    from .models import VideoGenerationJob

    resume_status = job.failed_at_status or job.status

    resume_map = {
        VideoGenerationJob.Status.PENDING: "plan_script",
        VideoGenerationJob.Status.PLANNING: "plan_script",
        VideoGenerationJob.Status.PREPARING: "prepare_first_frame",
        VideoGenerationJob.Status.GENERATING_S1: "generate_scene1",
        VideoGenerationJob.Status.PREPARING_CTA: "prepare_cta_frame",
        VideoGenerationJob.Status.GENERATING_S2: "generate_scene2",
        VideoGenerationJob.Status.CONCATENATING: "concatenate_videos",
    }
    return resume_map.get(resume_status, "plan_script")


def build_resume_state(job) -> dict:
    """Build state from DB for resuming from failure point.

    Uses FileField.url directly - no bytes download needed.
    """
    state = {
        "topic": job.topic,
        "script": job.script if job.script else None,
        "product_image_url": job.effective_product_image_url,
        "video_style": VideoStyle(job.video_style),
        "product_brand": job.product.brand if job.product else None,
        "product_description": job.product.description if job.product else None,
        "last_cta_image_url": job.effective_last_cta_image_url,
        "sound_effect_url": job.effective_sound_effect_url,
        # Load existing results
        "script_json": job.script_json,
        "product_detail": job.product_detail,
        "character_details": job.character_details,
        "segments": [],
        # URL fields - directly from FileField.url
        "first_frame_url": job.first_frame.url if job.first_frame else None,
        "cta_last_frame_url": job.cta_last_frame.url if job.cta_last_frame else None,
        "scene1_last_frame_url": job.scene1_last_frame.url if job.scene1_last_frame else None,
        "current_segment_index": 0,
        "segment_videos": [],
        "scene1_video_url": None,
        "scene2_video_url": None,
        "skipped_segments": job.skipped_segments or [],
        "final_video_url": job.final_video.url if job.final_video else None,
        "error": None,
        "status": "resuming",
    }

    # Load segment data
    for seg in job.segments.order_by("segment_index"):
        state["segments"].append({
            "title": seg.title,
            "seconds": seg.seconds,
            "prompt": seg.prompt,
            "raw_data": {},
        })

    # Load segment video URLs
    segment_videos = []
    for seg in job.segments.order_by("segment_index"):
        if seg.video_file:
            segment_video: SegmentVideo = {
                "video_url": seg.video_file.url,
                "index": seg.segment_index,
                "title": seg.title,
            }
            segment_videos.append(segment_video)
            # Set scene URLs
            if seg.segment_index == 0:
                state["scene1_video_url"] = seg.video_file.url
            elif seg.segment_index == 1:
                state["scene2_video_url"] = seg.video_file.url

    state["segment_videos"] = segment_videos
    state["current_segment_index"] = len(segment_videos)

    return state


def generate_video_with_resume(job):
    """Resume video generation from failure point.

    Loads existing results from DB and resumes from the failed node.
    """
    from .models import VideoGenerationJob

    try:
        # Get resume point
        entry_point = get_resume_entry_point(job)

        # Start from beginning if needed
        if entry_point == "plan_script":
            return generate_video_sync(job)

        # Build resume state with URLs
        current_state = build_resume_state(job)

        # Clear error message
        job.error_message = ""
        job.save()

        # Find entry point index
        start_idx = NODE_ORDER.index(entry_point)

        # Execute from entry point
        for node_name in NODE_ORDER[start_idx:]:
            # Update status
            _update_job_status_for_node(job, node_name)

            # Execute node
            node_func = NODE_FUNCTIONS[node_name]
            result = node_func(current_state)

            # Save and inject URLs
            current_state = _save_and_inject_urls(job, node_name, result, current_state)

            # Check for errors
            if result.get("error"):
                job.failed_at_status = job.status
                job.status = VideoGenerationJob.Status.FAILED
                job.error_message = result["error"]
                job.save()
                raise RuntimeError(result["error"])

        job.status = VideoGenerationJob.Status.COMPLETED
        job.current_step = "완료"
        job.failed_at_status = ""
        job.save()

    except Exception as e:
        import traceback
        traceback.print_exc()

        if not job.failed_at_status:
            job.failed_at_status = job.status
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise


def generate_video_sync_simple(job):
    """Simple version: invoke all at once (for debugging).

    Note: This version doesn't support URL-based state.
    Use generate_video_sync for production.
    """
    # Redirect to the main function
    return generate_video_sync(job)
