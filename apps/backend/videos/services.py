"""Services for video generation using integrated generators package."""

from django.core.files.base import ContentFile

# Import from local generators package (no sys.path manipulation needed)
from .generators.constants import VideoStyle
from .generators.graph import graph
from .generators.state import VideoGeneratorState


def generate_video_sync(job):
    """동기식 영상 생성 with incremental saving.

    generators의 LangGraph workflow를 실행하고 각 단계 완료 시 즉시 DB에 저장합니다.
    중간 단계 오류 시 이전 단계 결과물이 유지됩니다.

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
            # 영상 스타일
            "video_style": VideoStyle(job.video_style),
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
            "scene1_video_bytes": None,
            "scene2_video_bytes": None,
            "scene1_last_frame_image": None,
            "skipped_segments": [],
            "final_video_bytes": None,
            "error": None,
            "status": "pending",
        }

        # LangGraph 실행 (동기) - 각 노드별 즉시 저장
        for step in graph.stream(initial_state):
            node_name = list(step.keys())[0]
            node_output = step[node_name]

            # 노드별 즉시 저장
            _save_node_result(job, node_name, node_output)

            # 에러 체크
            if node_output.get("error"):
                # 실패 시점 기록
                job.failed_at_status = job.status
                job.status = VideoGenerationJob.Status.FAILED
                job.error_message = node_output["error"]
                job.save()
                raise RuntimeError(node_output["error"])

        job.status = VideoGenerationJob.Status.COMPLETED
        job.current_step = "완료"
        job.failed_at_status = ""  # 성공 시 초기화
        job.save()

    except Exception as e:
        import traceback
        traceback.print_exc()

        # 실패 시점 상태 기록 (아직 기록되지 않은 경우)
        if not job.failed_at_status:
            job.failed_at_status = job.status
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise


def _save_node_result(job, node_name: str, node_output: dict):
    """노드 실행 결과를 즉시 DB/S3에 저장합니다."""
    from .models import VideoGenerationJob, VideoSegment

    if node_name == "plan_script":
        # 기획 결과 저장
        job.status = VideoGenerationJob.Status.PLANNING
        job.current_step = "AI 스크립트 기획"

        if node_output.get("script_json"):
            job.script_json = node_output["script_json"]
        if node_output.get("product_detail"):
            job.product_detail = node_output["product_detail"]
        if node_output.get("character_details"):
            job.character_details = node_output["character_details"]

        job.save()

    elif node_name == "prepare_first_frame":
        # 첫 프레임 저장
        job.status = VideoGenerationJob.Status.PREPARING
        job.current_step = "첫 프레임 생성"

        first_frame = node_output.get("first_frame_image")
        if first_frame:
            job.first_frame.save(
                f"job_{job.id}_first_frame.png",
                ContentFile(first_frame),
            )

        # 세그먼트 생성 (프롬프트 정보 저장)
        segments_data = node_output.get("segments", [])
        _create_video_segments(job, segments_data)

        job.save()

    elif node_name == "generate_scene1":
        # Scene 1 영상 저장
        job.status = VideoGenerationJob.Status.GENERATING_S1
        job.current_step = "Scene 1 생성"

        # Scene 1 영상 파일 저장
        scene1_video = node_output.get("scene1_video_bytes")
        if scene1_video:
            segment = job.segments.filter(segment_index=0).first()
            if segment:
                segment.video_file.save(
                    f"segment_01.mp4",
                    ContentFile(scene1_video),
                )
                segment.status = VideoSegment.Status.COMPLETED
                segment.save()

        # Scene 1 마지막 프레임 저장
        scene1_last = node_output.get("scene1_last_frame_image")
        if scene1_last:
            job.scene1_last_frame.save(
                f"job_{job.id}_scene1_last.png",
                ContentFile(scene1_last),
            )

        job.save()

    elif node_name == "prepare_cta_frame":
        # CTA 프레임 저장
        job.status = VideoGenerationJob.Status.PREPARING_CTA
        job.current_step = "CTA 프레임 생성"

        cta_last = node_output.get("cta_last_frame_image")
        if cta_last:
            job.cta_last_frame.save(
                f"job_{job.id}_cta_last.png",
                ContentFile(cta_last),
            )

        job.save()

    elif node_name == "generate_scene2":
        # Scene 2 영상 저장
        job.status = VideoGenerationJob.Status.GENERATING_S2
        job.current_step = "Scene 2 생성"

        # Scene 2 영상 파일 저장
        scene2_video = node_output.get("scene2_video_bytes")
        if scene2_video:
            segment = job.segments.filter(segment_index=1).first()
            if segment:
                segment.video_file.save(
                    f"segment_02.mp4",
                    ContentFile(scene2_video),
                )
                segment.status = VideoSegment.Status.COMPLETED
                segment.save()

        job.save()

    elif node_name == "concatenate_videos":
        # 최종 영상 저장
        job.status = VideoGenerationJob.Status.CONCATENATING
        job.current_step = "영상 병합"

        final_video = node_output.get("final_video_bytes")
        if final_video:
            job.final_video.save(
                f"job_{job.id}_final.mp4",
                ContentFile(final_video),
            )

        # 스킵된 세그먼트 저장
        skipped = node_output.get("skipped_segments", [])
        if skipped:
            job.skipped_segments = skipped

        job.save()

    elif node_name == "handle_error":
        job.status = VideoGenerationJob.Status.FAILED
        job.current_step = "에러 처리"
        job.save()


def _create_video_segments(job, segments_data: list):
    """세그먼트 레코드 생성 (프롬프트 정보 저장).

    update_or_create를 사용하여 중복 키 오류를 방지합니다.
    """
    from .models import VideoSegment

    # 기존 세그먼트 삭제 (새로운 세그먼트 수보다 많은 경우 대비)
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
    """실패 지점에 따라 재개할 노드 반환."""
    from .models import VideoGenerationJob

    # failed_at_status가 있으면 그 시점에서 재개, 없으면 현재 status 기준
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
    """DB에서 기존 결과물을 로드하여 재개용 초기 상태 구성."""
    from .generators.constants import VideoStyle

    state = {
        "topic": job.topic,
        "script": job.script if job.script else None,
        "product_image_url": job.effective_product_image_url,
        "video_style": VideoStyle(job.video_style),
        "product_brand": job.product.brand if job.product else None,
        "product_description": job.product.description if job.product else None,
        "last_cta_image_url": job.effective_last_cta_image_url,
        "sound_effect_url": job.effective_sound_effect_url,
        # 기존 결과물 로드
        "script_json": job.script_json,
        "product_detail": job.product_detail,
        "character_details": job.character_details,
        "segments": [],
        "first_frame_image": None,
        "cta_last_frame_image": None,
        "current_segment_index": 0,
        "segment_videos": [],
        "scene1_video_bytes": None,
        "scene2_video_bytes": None,
        "scene1_last_frame_image": None,
        "skipped_segments": job.skipped_segments or [],
        "final_video_bytes": None,
        "error": None,
        "status": "resuming",
    }

    # 세그먼트 데이터 로드
    for seg in job.segments.order_by("segment_index"):
        state["segments"].append({
            "title": seg.title,
            "seconds": seg.seconds,
            "prompt": seg.prompt,
            "raw_data": {},
        })

    # 프레임 이미지 로드
    if job.first_frame:
        try:
            job.first_frame.seek(0)
            state["first_frame_image"] = job.first_frame.read()
        except Exception:
            pass

    if job.scene1_last_frame:
        try:
            job.scene1_last_frame.seek(0)
            state["scene1_last_frame_image"] = job.scene1_last_frame.read()
        except Exception:
            pass

    if job.cta_last_frame:
        try:
            job.cta_last_frame.seek(0)
            state["cta_last_frame_image"] = job.cta_last_frame.read()
        except Exception:
            pass

    # 세그먼트 영상 로드
    segment_videos = []
    for seg in job.segments.order_by("segment_index"):
        if seg.video_file:
            try:
                seg.video_file.seek(0)
                video_bytes = seg.video_file.read()
                segment_videos.append({
                    "video_bytes": video_bytes,
                    "index": seg.segment_index,
                    "title": seg.title,
                })
                # scene1/scene2 bytes 설정
                if seg.segment_index == 0:
                    state["scene1_video_bytes"] = video_bytes
                elif seg.segment_index == 1:
                    state["scene2_video_bytes"] = video_bytes
            except Exception:
                pass

    state["segment_videos"] = segment_videos
    state["current_segment_index"] = len(segment_videos)

    return state


def generate_video_with_resume(job):
    """실패 지점부터 영상 생성 재개.

    DB에 저장된 기존 결과물을 로드하고 실패한 단계부터 재개합니다.
    """
    from langgraph.graph import END

    from .generators.graph import build_graph
    from .models import VideoGenerationJob

    try:
        # 재개 지점 확인
        entry_point = get_resume_entry_point(job)

        # 처음부터 시작해야 하는 경우
        if entry_point == "plan_script":
            return generate_video_sync(job)

        # 재개용 상태 구성
        resume_state = build_resume_state(job)

        # 에러 메시지 초기화
        job.error_message = ""
        job.save()

        # 그래프 재구성하여 entry point 변경
        # LangGraph에서 entry point를 동적으로 변경하기 어려우므로
        # 직접 노드별로 실행
        workflow = build_graph()

        # entry point부터 시작하는 상태 설정
        current_state = resume_state

        # 노드 실행 순서
        node_order = [
            "plan_script",
            "prepare_first_frame",
            "generate_scene1",
            "prepare_cta_frame",
            "generate_scene2",
            "concatenate_videos",
        ]

        # entry point 인덱스 찾기
        start_idx = node_order.index(entry_point)

        # entry point부터 순차 실행
        for node_name in node_order[start_idx:]:
            # 노드 함수 가져오기
            node_func = workflow.nodes[node_name]

            # 노드 실행
            result = node_func.invoke(current_state)

            # 상태 병합 (리듀서 처리)
            for key, value in result.items():
                if key == "segment_videos" and value:
                    # segment_videos는 append 리듀서
                    current_state["segment_videos"] = current_state.get("segment_videos", []) + value
                else:
                    current_state[key] = value

            # 결과 즉시 저장
            _save_node_result(job, node_name, result)

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


def generate_video_sync_simple(job):
    """단순 버전: invoke로 한 번에 실행.

    디버깅용. 전체 워크플로우를 한 번에 실행하고 결과만 저장합니다.
    재시도 시 기존 세그먼트와 파일을 정리합니다.
    """
    from .models import VideoGenerationJob, VideoSegment

    try:
        # 재시도 시 기존 데이터 정리는 update_or_create 후 처리
        # (delete 후 create 시 race condition으로 UNIQUE constraint 오류 발생 가능)

        job.status = VideoGenerationJob.Status.PLANNING
        job.current_step = "영상 생성 중"
        job.skipped_segments = []  # 초기화
        job.save()

        # 초기 상태
        initial_state = {
            "topic": job.topic,
            "script": job.script if job.script else None,
            "product_image_url": job.effective_product_image_url,
            # 영상 스타일
            "video_style": VideoStyle(job.video_style),
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

        # 세그먼트 저장 (update_or_create로 중복 키 오류 방지)
        segments_data = final_state.get("segments", [])
        segment_videos = final_state.get("segment_videos", [])

        # Sort segment_videos by index
        segment_videos_sorted = sorted(segment_videos, key=lambda x: x["index"])

        for i, seg_data in enumerate(segments_data):
            segment, created = VideoSegment.objects.update_or_create(
                job=job,
                segment_index=i,
                defaults={
                    "title": seg_data.get("title", f"Segment {i+1}"),
                    "seconds": seg_data.get("seconds", 8),
                    "prompt": seg_data.get("prompt", ""),
                    "status": VideoSegment.Status.COMPLETED,
                },
            )

            # 세그먼트 영상 파일 저장 (bytes 직접 저장)
            if i < len(segment_videos_sorted):
                seg_video = segment_videos_sorted[i]
                segment.video_file.save(
                    f"segment_{i+1:02d}.mp4",
                    ContentFile(seg_video["video_bytes"]),
                )

        # 재시도 시 이전 세그먼트 수보다 적어진 경우 초과 세그먼트 정리
        job.segments.filter(segment_index__gte=len(segments_data)).delete()

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
