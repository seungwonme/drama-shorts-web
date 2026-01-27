"""Services for video generation using integrated generators package."""

from django.core.files.base import ContentFile

# Import from local generators package (no sys.path manipulation needed)
from .generators.graph import graph
from .generators.state import VideoGeneratorState


def generate_video_sync(job):
    """동기식 영상 생성.

    generators의 LangGraph workflow를 실행하고 결과를 Django 모델에 저장합니다.

    Args:
        job: VideoGenerationJob 인스턴스
    """
    from .models import VideoGenerationJob, VideoSegment

    try:
        # === Step 1: Plan Script ===
        job.status = VideoGenerationJob.Status.PLANNING
        job.current_step = "AI 스크립트 기획"
        job.save()

        # 초기 상태 설정
        initial_state: VideoGeneratorState = {
            "topic": job.topic,
            "script": job.script if job.script else None,
            "product_image_url": job.effective_product_image_url,
            # Product 정보 (Django Product 모델에서)
            "product_brand": job.product.brand if job.product else None,
            "product_description": job.product.description if job.product else None,
            # S3 에셋 URL (Job 선택 > 기본 활성 에셋)
            "last_cta_image_url": job.effective_last_cta_image_url,
            "sound_effect_url": job.effective_sound_effect_url,
            # 초기화 필드
            "script_json": None,
            "product_detail": None,
            "character_details": None,
            "segments": [],
            "first_frame_image": None,
            "cta_last_frame_image": None,
            "current_segment_index": 0,
            "segment_videos": [],
            "scene1_last_frame_image": None,
            "skipped_segments": [],
            "final_video_bytes": None,
            "error": None,
            "status": "pending",
        }

        # LangGraph 실행 (동기)
        # 각 노드를 개별적으로 추적하기 위해 stream 사용
        for step in graph.stream(initial_state):
            node_name = list(step.keys())[0]
            node_output = step[node_name]

            # 상태 업데이트
            _update_job_status(job, node_name, node_output)

            # 에러 체크
            if node_output.get("error"):
                raise RuntimeError(node_output["error"])

        # 최종 상태 가져오기
        # stream이 완료되면 node_output이 마지막 상태를 가짐
        final_state = node_output

        # === 결과 저장 ===
        _save_results(job, final_state)

        job.status = VideoGenerationJob.Status.COMPLETED
        job.current_step = "완료"
        job.save()

    except Exception as e:
        import traceback
        traceback.print_exc()

        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise


def _update_job_status(job, node_name: str, node_output: dict):
    """노드 실행에 따라 job 상태를 업데이트합니다."""
    from .models import VideoGenerationJob

    status_map = {
        "plan_script": (VideoGenerationJob.Status.PLANNING, "AI 스크립트 기획"),
        "prepare_assets": (VideoGenerationJob.Status.PREPARING, "첫 프레임 생성"),
        "generate_video_segment": (VideoGenerationJob.Status.GENERATING, "영상 세그먼트 생성"),
        "concatenate_videos": (VideoGenerationJob.Status.CONCATENATING, "영상 병합"),
        "handle_error": (VideoGenerationJob.Status.FAILED, "에러 처리"),
    }

    if node_name in status_map:
        status, step_name = status_map[node_name]
        job.status = status
        job.current_step = step_name

        # plan_script에서 JSON 저장
        if node_name == "plan_script":
            if node_output.get("script_json"):
                job.script_json = node_output["script_json"]
            if node_output.get("product_detail"):
                job.product_detail = node_output["product_detail"]
            if node_output.get("character_details"):
                job.character_details = node_output["character_details"]

        job.save()


def _save_results(job, final_state: dict):
    """최종 결과물을 Django 모델에 저장합니다."""
    from .models import VideoSegment

    # 최종 영상 저장 (bytes 직접 저장 -> S3 자동 업로드)
    final_video_bytes = final_state.get("final_video_bytes")
    if final_video_bytes:
        job.final_video.save(
            f"job_{job.id}_final.mp4",
            ContentFile(final_video_bytes),
        )

    # 스킵된 세그먼트 저장
    skipped = final_state.get("skipped_segments", [])
    if skipped:
        job.skipped_segments = skipped

    job.save()


def generate_video_sync_simple(job):
    """단순 버전: invoke로 한 번에 실행.

    디버깅용. 전체 워크플로우를 한 번에 실행하고 결과만 저장합니다.
    """
    from .models import VideoGenerationJob, VideoSegment

    try:
        job.status = VideoGenerationJob.Status.GENERATING
        job.current_step = "영상 생성 중"
        job.save()

        # 초기 상태
        initial_state = {
            "topic": job.topic,
            "script": job.script if job.script else None,
            "product_image_url": job.effective_product_image_url,
            # Product 정보 (Django Product 모델에서)
            "product_brand": job.product.brand if job.product else None,
            "product_description": job.product.description if job.product else None,
            # S3 에셋 URL (Job 선택 > 기본 활성 에셋)
            "last_cta_image_url": job.effective_last_cta_image_url,
            "sound_effect_url": job.effective_sound_effect_url,
        }

        # LangGraph 실행 (동기)
        final_state = graph.invoke(initial_state)

        # 에러 체크
        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        # 결과 저장
        job.script_json = final_state.get("script_json")
        job.product_detail = final_state.get("product_detail")
        job.character_details = final_state.get("character_details")
        job.skipped_segments = final_state.get("skipped_segments", [])

        # 첫 프레임 이미지 저장 (bytes 직접 저장)
        first_frame = final_state.get("first_frame_image")
        if first_frame:
            job.first_frame.save(
                f"job_{job.id}_first_frame.png",
                ContentFile(first_frame),
            )

        # Scene 1 마지막 프레임 저장
        scene1_last = final_state.get("scene1_last_frame_image")
        if scene1_last:
            job.scene1_last_frame.save(
                f"job_{job.id}_scene1_last.png",
                ContentFile(scene1_last),
            )

        # CTA 마지막 프레임 저장
        cta_last = final_state.get("cta_last_frame_image")
        if cta_last:
            job.cta_last_frame.save(
                f"job_{job.id}_cta_last.png",
                ContentFile(cta_last),
            )

        # 세그먼트 저장
        segments_data = final_state.get("segments", [])
        segment_videos = final_state.get("segment_videos", [])

        # Sort segment_videos by index
        segment_videos_sorted = sorted(segment_videos, key=lambda x: x["index"])

        for i, seg_data in enumerate(segments_data):
            segment = VideoSegment.objects.create(
                job=job,
                segment_index=i,
                title=seg_data.get("title", f"Segment {i+1}"),
                seconds=seg_data.get("seconds", 8),
                prompt=seg_data.get("prompt", ""),
                status=VideoSegment.Status.COMPLETED,
            )

            # 세그먼트 영상 파일 저장 (bytes 직접 저장)
            if i < len(segment_videos_sorted):
                seg_video = segment_videos_sorted[i]
                segment.video_file.save(
                    f"segment_{i+1:02d}.mp4",
                    ContentFile(seg_video["video_bytes"]),
                )

            segment.save()

        # 최종 영상 저장 (bytes 직접 저장)
        final_video_bytes = final_state.get("final_video_bytes")
        if final_video_bytes:
            job.final_video.save(
                f"job_{job.id}_final.mp4",
                ContentFile(final_video_bytes),
            )

        job.status = VideoGenerationJob.Status.COMPLETED
        job.current_step = "완료"
        job.save()

    except Exception as e:
        import traceback
        traceback.print_exc()

        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise
