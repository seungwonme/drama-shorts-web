from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from .constants import (
    MSG_JOB_CANCELLED,
    MSG_JOB_FAILED,
    MSG_JOB_NEEDS_RESTART,
    MSG_JOB_NOT_COMPLETED,
    MSG_JOB_NOT_IN_PROGRESS,
    MSG_JOB_NOT_RESUMABLE,
    MSG_JOB_NOT_RETRIABLE,
    MSG_JOB_RESUMED,
    MSG_JOB_STARTED,
    MSG_JOBS_DELETED,
    MSG_JOBS_STARTED,
    MSG_NO_ELIGIBLE_JOBS,
)
from .models import GameFrame, Product, ProductImage, VideoAsset, VideoGenerationJob, VideoSegment
from .status_config import (
    # Drama workflow
    IN_PROGRESS_STATUSES,
    PROGRESS_PERCENTAGES,
    PROGRESS_STEPS,
    STATUS_COLORS,
    STATUS_ORDER,
    TOTAL_STEPS,
    get_progress_percent,
    get_status_color,
    get_status_order,
    is_in_progress,
    # Game workflow
    GAME_PROGRESS_STEPS,
    GAME_TOTAL_STEPS,
    get_game_progress_percent,
    get_game_status_order,
)

# Group 모델 숨기기 (사용하지 않음)
admin.site.unregister(Group)


# =============================================================================
# 모든 Django 모델 자동 등록 (CRUD 가능)
# =============================================================================


class AutoModelAdmin(ModelAdmin):
    """모든 필드를 자동으로 표시하는 ModelAdmin"""

    def __init__(self, model, admin_site):
        # list_display: 모든 필드 표시 (최대 10개)
        fields = [f.name for f in model._meta.fields]
        self.list_display = fields[:10]

        # search_fields: CharField, TextField만
        self.search_fields = [
            f.name for f in model._meta.fields if f.__class__.__name__ in ("CharField", "TextField")
        ][:3]

        # list_filter: 선택 가능한 필드만
        self.list_filter = [
            f.name
            for f in model._meta.fields
            if f.__class__.__name__ in ("BooleanField", "DateTimeField", "DateField", "ForeignKey")
        ][:3]

        super().__init__(model, admin_site)


def auto_register_models():
    """등록되지 않은 모든 모델 자동 등록"""
    # 제외할 앱 (Django 내부 앱 중 이미 등록된 것)
    exclude_apps = {"admin", "contenttypes", "sessions"}

    for model in apps.get_models():
        app_label = model._meta.app_label

        # 제외 앱 스킵
        if app_label in exclude_apps:
            continue

        # 이미 등록된 모델 스킵
        if model in admin.site._registry:
            continue

        try:
            admin.site.register(model, AutoModelAdmin)
        except admin.sites.AlreadyRegistered:
            pass


# 파일 끝에서 자동 등록 실행 (커스텀 ModelAdmin 등록 후)
# _auto_register_models() 는 파일 맨 아래에서 호출


# =============================================================================
# VideoAsset Admin
# =============================================================================


@admin.register(VideoAsset)
class VideoAssetAdmin(ModelAdmin):
    list_display = ["id", "name", "asset_type", "is_active_badge", "file_preview", "created_at"]
    list_filter = ["asset_type", "is_active", "created_at"]
    search_fields = ["name", "description"]
    list_display_links = ["id", "name"]

    fieldsets = (
        (None, {"fields": ("name", "asset_type", "file", "is_active", "description")}),
        ("메타", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="상태")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2 py-1 rounded-md text-xs font-medium">활성</span>'
            )
        return mark_safe(
            '<span class="bg-gray-100 text-gray-500 px-2 py-1 rounded-md text-xs font-medium">비활성</span>'
        )

    @admin.display(description="미리보기")
    def file_preview(self, obj):
        if obj.file:
            if obj.asset_type == VideoAsset.AssetType.LAST_CTA_IMAGE:
                return format_html(
                    '<img src="{}" width="80" height="45" style="object-fit: cover; border-radius: 4px;" />',
                    obj.file.url,
                )
            else:
                return format_html(
                    '<a href="{}" target="_blank" class="text-primary-600 hover:text-primary-700 font-medium">다운로드</a>',
                    obj.file.url,
                )
        return "-"


# =============================================================================
# Product Admin
# =============================================================================


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "image_preview", "alt_text", "is_primary", "order"]
    readonly_fields = ["image_preview"]
    tab = True

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; '
                'border-radius: 8px;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "미리보기"


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ["id", "name", "brand", "image_count", "primary_image_preview", "created_at"]
    list_filter = ["brand", "created_at"]
    search_fields = ["name", "brand", "description"]
    inlines = [ProductImageInline]
    list_display_links = ["id", "name"]

    fieldsets = (
        (None, {"fields": ("name", "brand", "description")}),
        ("메타", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at"]

    def image_count(self, obj):
        count = obj.images.count()
        return f"{count}개"

    image_count.short_description = "이미지"

    def primary_image_preview(self, obj):
        url = obj.primary_image_url
        if url:
            return format_html(
                '<img src="{}" width="48" height="48" style="object-fit: cover; '
                'border-radius: 8px;" />',
                url,
            )
        return "-"

    primary_image_preview.short_description = "대표 이미지"


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = [
        "id",
        "product",
        "image_preview",
        "alt_text",
        "is_primary",
        "order",
        "created_at",
    ]
    list_filter = ["is_primary", "product", "created_at"]
    search_fields = ["product__name", "alt_text"]
    list_display_links = ["id"]
    autocomplete_fields = ["product"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "product",
                    "image",
                    "image_preview_large",
                    "alt_text",
                    "is_primary",
                    "order",
                )
            },
        ),
        ("메타", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "image_preview_large"]

    @admin.display(description="미리보기")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 8px;" />',
                obj.image.url,
            )
        return "-"

    @admin.display(description="이미지 미리보기")
    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="200" height="200" style="object-fit: cover; border-radius: 8px;" />',
                obj.image.url,
            )
        return "-"


# =============================================================================
# Video Admin
# =============================================================================


class VideoSegmentInline(TabularInline):
    model = VideoSegment
    extra = 0
    readonly_fields = [
        "segment_index",
        "title",
        "seconds",
        "prompt",
        "status",
        "video_preview",
        "last_frame_preview",
        "error_message",
    ]
    fields = [
        "segment_index",
        "title",
        "seconds",
        "status",
        "video_preview",
        "last_frame_preview",
    ]
    can_delete = False
    tab = True

    def has_add_permission(self, request, obj=None):
        return False

    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<a href="{}" target="_blank" class="text-primary-600 hover:text-primary-700 font-medium">다운로드</a>',
                obj.video_file.url,
            )
        return "-"

    video_preview.short_description = "영상"

    def last_frame_preview(self, obj):
        if obj.last_frame:
            return format_html(
                '<img src="{}" width="80" height="45" style="object-fit: cover; border-radius: 4px;" />',
                obj.last_frame.url,
            )
        return "-"

    last_frame_preview.short_description = "마지막 프레임"


class GameFrameInline(TabularInline):
    """게임 프레임 인라인"""
    model = GameFrame
    extra = 0
    readonly_fields = [
        "scene_number",
        "shot_type",
        "game_location",
        "description_kr",
        "image_preview",
        "video_preview",
    ]
    fields = [
        "scene_number",
        "shot_type",
        "game_location",
        "description_kr",
        "image_preview",
        "video_preview",
    ]
    can_delete = False
    tab = True

    def has_add_permission(self, request, obj=None):
        return False

    def image_preview(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" width="80" height="142" style="object-fit: cover; border-radius: 4px;" />',
                obj.image_file.url,
            )
        return "-"
    image_preview.short_description = "프레임"

    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<a href="{}" target="_blank" class="text-primary-600 hover:text-primary-700 font-medium">다운로드</a>',
                obj.video_file.url,
            )
        return "-"
    video_preview.short_description = "영상"


@admin.register(VideoGenerationJob)
class VideoGenerationJobAdmin(ModelAdmin):
    list_display = [
        "id",
        "job_type_badge",
        "topic_or_game",
        "video_style_badge",
        "product",
        "status_badge",
        "progress_bar",
        "current_step_display",
        "segment_count",
        "video_preview",
        "created_at",
        "row_actions",
    ]
    list_filter = ["job_type", "status", "video_style", "product", "created_at"]
    search_fields = ["topic", "script", "product__name", "game_name"]
    list_display_links = ["id", "topic_or_game"]
    readonly_fields = [
        "status",
        "current_step",
        "progress_steps_display",
        "error_message",
        "script_json",
        "product_detail",
        "character_details",
        "character_description",
        "game_locations_used",
        "first_frame_preview",
        "scene1_last_frame_preview",
        "cta_last_frame_preview",
        "character_image_preview",
        "final_video",
        "skipped_segments",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["product"]

    def get_inlines(self, request, obj):
        """job_type에 따라 다른 인라인 표시"""
        if obj and obj.job_type == VideoGenerationJob.JobType.GAME:
            return [GameFrameInline]
        return [VideoSegmentInline]

    # 목록 페이지 상단 버튼 (선택된 항목들에 대해)
    actions = ["bulk_generate_video_action", "bulk_delete_selected"]

    # 상세 페이지 버튼
    actions_detail = [
        "generate_video_action",
        "resume_video_action",
        "cancel_video_action",
        "regenerate_first_frame_action",
        "regenerate_scene1_action",
        "regenerate_cta_last_frame_action",
        "regenerate_scene2_action",
        "regenerate_final_video_action",
    ]

    # =========================================================================
    # HTMX URLs and Views
    # =========================================================================

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "htmx/<int:job_id>/status/",
                self.admin_site.admin_view(self.htmx_status_view),
                name="videos_videogenerationjob_htmx_status",
            ),
            path(
                "htmx/<int:job_id>/progress/",
                self.admin_site.admin_view(self.htmx_progress_view),
                name="videos_videogenerationjob_htmx_progress",
            ),
            path(
                "htmx/<int:job_id>/current-step/",
                self.admin_site.admin_view(self.htmx_current_step_view),
                name="videos_videogenerationjob_htmx_current_step",
            ),
            path(
                "htmx/<int:job_id>/row-actions/",
                self.admin_site.admin_view(self.htmx_row_actions_view),
                name="videos_videogenerationjob_htmx_row_actions",
            ),
            path(
                "htmx/<int:job_id>/progress-steps/",
                self.admin_site.admin_view(self.htmx_progress_steps_view),
                name="videos_videogenerationjob_htmx_progress_steps",
            ),
        ]
        return custom_urls + urls

    def _is_polling_active(self, job):
        """Check if HTMX polling should continue."""
        return job.status not in [
            VideoGenerationJob.Status.COMPLETED,
            VideoGenerationJob.Status.FAILED,
            VideoGenerationJob.Status.PENDING,
        ]

    def _get_htmx_attrs(self, job, endpoint, interval="3s"):
        """Generate HTMX attributes for polling."""
        if not self._is_polling_active(job):
            return ""
        return f'hx-get="/admin/videos/videogenerationjob/htmx/{job.pk}/{endpoint}/" hx-trigger="every {interval}" hx-swap="outerHTML"'

    def _htmx_view(self, job_id, render_fn):
        """Common HTMX view handler with job lookup and error handling.

        Args:
            job_id: Job primary key
            render_fn: Function that takes job and returns HTML string

        Returns:
            HttpResponse with rendered HTML or "-" if job not found
        """
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
            return HttpResponse(render_fn(job))
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

    def htmx_status_view(self, request, job_id):
        return self._htmx_view(job_id, self._render_status_badge)

    def htmx_progress_view(self, request, job_id):
        return self._htmx_view(job_id, self._render_progress_bar)

    def htmx_current_step_view(self, request, job_id):
        return self._htmx_view(job_id, self._render_current_step)

    def htmx_row_actions_view(self, request, job_id):
        return self._htmx_view(job_id, self._render_row_actions)

    def htmx_progress_steps_view(self, request, job_id):
        return self._htmx_view(job_id, self._render_progress_steps)

    def get_actions_detail(self, request, object_id=None):
        """상태에 따라 표시할 액션 결정 - UnfoldAction 객체 리스트 반환"""
        # 부모 메서드 호출하여 UnfoldAction 객체 리스트 가져오기
        all_actions = super().get_actions_detail(request, object_id)

        if not object_id:
            return []

        job = VideoGenerationJob.objects.filter(pk=object_id).first()
        if not job:
            return []

        # 상태에 따라 허용할 액션 이름 결정
        allowed_action_names = self._get_allowed_action_names(job)

        # UnfoldAction 객체 중 허용된 것만 필터링
        return [
            action
            for action in all_actions
            if any(action.action_name.endswith(f"_{name}") for name in allowed_action_names)
        ]

    def _get_allowed_action_names(self, job):
        """상태와 조건에 따라 허용할 액션 이름 반환"""
        # PENDING: 영상 생성 액션만
        if job.status == VideoGenerationJob.Status.PENDING:
            return ["generate_video_action"]

        # FAILED: 재시도 액션 + 재개 액션 (failed_at_status가 있는 경우)
        if job.status == VideoGenerationJob.Status.FAILED:
            actions = ["generate_video_action"]
            # 중간 단계에서 실패한 경우 재개 액션 추가
            if job.failed_at_status and job.failed_at_status not in [
                VideoGenerationJob.Status.PENDING,
                VideoGenerationJob.Status.PLANNING,
            ]:
                actions.append("resume_video_action")
            return actions

        # COMPLETED: 재작업 액션들
        if job.status == VideoGenerationJob.Status.COMPLETED:
            return self._get_rework_action_names(job)

        # 진행중 상태: 취소 액션
        if is_in_progress(job.status):
            return ["cancel_video_action"]

        return []

    def _get_rework_action_names(self, job):
        """조건에 따라 가능한 재작업 액션 이름 반환"""
        actions = []

        # 1. 첫 프레임 재생성: script_json 필요
        if job.script_json:
            actions.append("regenerate_first_frame_action")

        # 2. Scene 1 재생성: first_frame 필요
        if job.first_frame:
            actions.append("regenerate_scene1_action")

        # 3. CTA 마지막 프레임 재생성: scene1_last_frame, product_image 필요
        if job.scene1_last_frame and job.effective_product_image_url:
            actions.append("regenerate_cta_last_frame_action")

        # 4. Scene 2 재생성: scene1_last_frame, cta_last_frame 필요
        if job.scene1_last_frame and job.cta_last_frame:
            actions.append("regenerate_scene2_action")

        # 5. 최종 영상 병합: 세그먼트 영상 필요
        # FileField stores empty string when no file, not NULL
        if job.segments.exclude(video_file="").exists():
            actions.append("regenerate_final_video_action")

        return actions

    def get_fieldsets(self, request, obj=None):
        """job_type에 따라 다른 필드셋 반환"""
        # 게임 캐릭터 타입
        if obj and obj.job_type == VideoGenerationJob.JobType.GAME:
            return (
                ("작업 유형", {"fields": ("job_type",)}),
                ("게임 입력", {"fields": ("character_image", "character_image_preview", "game_name", "user_prompt")}),
                (
                    "진행 상황",
                    {"fields": ("progress_steps_display",)},
                ),
                (
                    "상태",
                    {
                        "fields": ("status", "current_step", "error_message"),
                        "classes": ("collapse",),
                    },
                ),
                (
                    "기획 결과",
                    {
                        "fields": ("character_description", "game_locations_used", "script_json"),
                        "classes": ("collapse",),
                    },
                ),
                (
                    "결과",
                    {"fields": ("final_video",)},
                ),
                (
                    "메타",
                    {
                        "fields": ("created_at", "updated_at"),
                        "classes": ("collapse",),
                    },
                ),
            )

        # 드라마타이즈 광고 타입 (기본)
        return (
            ("작업 유형", {"fields": ("job_type",)}),
            ("입력", {"fields": ("topic", "video_style", "script", "product", "product_image_url")}),
            ("에셋", {"fields": ("last_cta_asset", "sound_effect_asset")}),
            (
                "진행 상황",
                {"fields": ("progress_steps_display",)},
            ),
            (
                "상태",
                {
                    "fields": ("status", "current_step", "error_message"),
                    "classes": ("collapse",),
                },
            ),
            (
                "기획 결과",
                {
                    "fields": ("script_json", "product_detail", "character_details"),
                    "classes": ("collapse",),
                },
            ),
            (
                "프레임 이미지",
                {
                    "fields": (
                        "first_frame_preview",
                        "scene1_last_frame_preview",
                        "cta_last_frame_preview",
                    ),
                    "classes": ("collapse",),
                },
            ),
            (
                "결과",
                {"fields": ("final_video", "skipped_segments")},
            ),
            (
                "메타",
                {
                    "fields": ("created_at", "updated_at"),
                    "classes": ("collapse",),
                },
            ),
        )

    @action(description="영상 생성 실행", url_path="generate_video_action")
    def generate_video_action(self, request, object_id):
        from django.shortcuts import redirect

        from .services import generate_video_async, get_resume_entry_point

        job = self.get_object(request, object_id)

        # PENDING 또는 FAILED 상태에서만 실행 가능
        allowed_statuses = [VideoGenerationJob.Status.PENDING, VideoGenerationJob.Status.FAILED]

        if job.status not in allowed_statuses:
            self.message_user(
                request,
                MSG_JOB_NOT_RETRIABLE.format(job_id=job.id, status=job.get_status_display()),
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 에러 메시지만 초기화 (failed_at_status는 유지하여 재개 지점 판단에 사용)
        job.error_message = ""
        job.current_step = "시작 중..."
        job.save(update_fields=["current_step", "error_message"])

        # 실패 지점이 있고 중간 단계라면 자동으로 재개
        entry_point = get_resume_entry_point(job)
        should_resume = (
            job.status == VideoGenerationJob.Status.FAILED
            and job.failed_at_status
            and entry_point != "plan_script"
        )

        # 비동기 실행 - 즉시 응답하고 백그라운드에서 처리
        generate_video_async(job.id, resume=should_resume)

        if should_resume:
            self.message_user(
                request,
                MSG_JOB_RESUMED.format(job_id=job.id, entry_point=entry_point),
                level="success",
            )
        else:
            self.message_user(
                request,
                MSG_JOB_STARTED.format(job_id=job.id),
                level="success",
            )

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="실패 지점부터 재개", url_path="resume_video_action")
    def resume_video_action(self, request, object_id):
        from django.shortcuts import redirect

        from .services import generate_video_async, get_resume_entry_point

        job = self.get_object(request, object_id)

        # FAILED 상태에서만 재개 가능
        if job.status != VideoGenerationJob.Status.FAILED:
            self.message_user(
                request,
                MSG_JOB_NOT_RESUMABLE.format(job_id=job.id, status=job.get_status_display()),
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 재개 지점 확인
        entry_point = get_resume_entry_point(job)
        if entry_point == "plan_script":
            self.message_user(
                request,
                MSG_JOB_NEEDS_RESTART.format(job_id=job.id),
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 에러 메시지 초기화
        job.error_message = ""
        job.current_step = "재개 중..."
        job.save(update_fields=["current_step", "error_message"])

        # 비동기 실행
        generate_video_async(job.id, resume=True)

        self.message_user(
            request,
            MSG_JOB_RESUMED.format(job_id=job.id, entry_point=entry_point),
            level="success",
        )

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="작업 취소", url_path="cancel_video_action")
    def cancel_video_action(self, request, object_id):
        from django.shortcuts import redirect

        job = self.get_object(request, object_id)

        # 진행중 상태에서만 취소 가능
        if not is_in_progress(job.status):
            self.message_user(
                request,
                MSG_JOB_NOT_IN_PROGRESS.format(job_id=job.id, status=job.get_status_display()),
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 실패 시점 기록 후 상태를 FAILED로 변경
        job.failed_at_status = job.status
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = "사용자에 의해 취소됨"
        job.current_step = "취소됨"
        job.save(update_fields=["status", "failed_at_status", "error_message", "current_step"])

        self.message_user(request, MSG_JOB_CANCELLED.format(job_id=job.id), level="success")
        return redirect(request.META.get("HTTP_REFERER", ".."))

    def _execute_rework_action(self, request, object_id, rework_fn, success_msg: str):
        """Execute a rework action with common validation and error handling.

        Args:
            request: HTTP request
            object_id: Job ID
            rework_fn: Rework service function to call
            success_msg: Success message to display

        Returns:
            HTTP redirect response
        """
        from django.shortcuts import redirect

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                MSG_JOB_NOT_COMPLETED.format(job_id=job.id),
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            rework_fn(job)
            self.message_user(request, f"Job #{job.id} {success_msg}", level="success")
        except Exception as e:
            self.message_user(request, MSG_JOB_FAILED.format(job_id=job.id, error=e), level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="첫 프레임 재생성 (Nano Banana)", url_path="regenerate_first_frame_action")
    def regenerate_first_frame_action(self, request, object_id):
        from .rework_services import regenerate_first_frame

        return self._execute_rework_action(
            request, object_id, regenerate_first_frame,
            "첫 프레임 재생성 완료. Scene 1, Scene 2, 최종 영상도 재생성 권장."
        )

    @action(description="Scene 1 재생성 (Veo)", url_path="regenerate_scene1_action")
    def regenerate_scene1_action(self, request, object_id):
        from .rework_services import regenerate_scene1

        return self._execute_rework_action(
            request, object_id, regenerate_scene1,
            "Scene 1 재생성 완료. Scene 2, 최종 영상도 재생성 권장."
        )

    @action(
        description="CTA 마지막 프레임 재생성 (Nano Banana)",
        url_path="regenerate_cta_last_frame_action",
    )
    def regenerate_cta_last_frame_action(self, request, object_id):
        from .rework_services import regenerate_cta_last_frame

        return self._execute_rework_action(
            request, object_id, regenerate_cta_last_frame,
            "CTA 마지막 프레임 재생성 완료. Scene 2, 최종 영상도 재생성 권장."
        )

    @action(description="Scene 2 재생성 (Veo)", url_path="regenerate_scene2_action")
    def regenerate_scene2_action(self, request, object_id):
        from .rework_services import regenerate_scene2

        return self._execute_rework_action(
            request, object_id, regenerate_scene2,
            "Scene 2 재생성 완료. 최종 영상도 재생성 권장."
        )

    @action(description="최종 영상 병합 (FFmpeg)", url_path="regenerate_final_video_action")
    def regenerate_final_video_action(self, request, object_id):
        from .rework_services import regenerate_final_video

        return self._execute_rework_action(
            request, object_id, regenerate_final_video,
            "최종 영상 병합 완료."
        )

    # =========================================================================
    # 목록 페이지 액션 (버튼 형태)
    # =========================================================================

    @admin.action(description="선택된 작업 영상 생성/재시도")
    def bulk_generate_video_action(self, request, queryset):
        """선택된 PENDING 또는 FAILED 작업들의 영상 생성 (실패 시 자동 재개)"""
        from .services import generate_video_async, get_resume_entry_point

        allowed_statuses = [VideoGenerationJob.Status.PENDING, VideoGenerationJob.Status.FAILED]
        eligible_jobs = queryset.filter(status__in=allowed_statuses)
        count = eligible_jobs.count()

        if count == 0:
            self.message_user(request, MSG_NO_ELIGIBLE_JOBS, level="warning")
            return

        started = 0
        for job in eligible_jobs:
            job.current_step = "시작 중..."
            job.error_message = ""
            job.save(update_fields=["current_step", "error_message"])

            # 실패 지점이 있고 중간 단계라면 자동으로 재개
            entry_point = get_resume_entry_point(job)
            should_resume = (
                job.status == VideoGenerationJob.Status.FAILED
                and job.failed_at_status
                and entry_point != "plan_script"
            )

            # 비동기 실행
            generate_video_async(job.id, resume=should_resume)
            started += 1

        self.message_user(request, MSG_JOBS_STARTED.format(count=started), level="success")

    @admin.action(description="선택된 작업 삭제")
    def bulk_delete_selected(self, request, queryset):
        """선택된 작업 삭제"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, MSG_JOBS_DELETED.format(count=count))

    # =========================================================================
    # 행별 액션 버튼
    # =========================================================================

    def _render_row_actions(self, obj):
        """Render row action buttons HTML with HTMX attributes."""
        from django.urls import reverse

        buttons = []
        hx_attrs = self._get_htmx_attrs(obj, "row-actions")

        if obj.status == VideoGenerationJob.Status.PENDING:
            url = reverse("admin:videos_videogenerationjob_change", args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="px-3 py-1 bg-primary-600 text-white rounded-md text-xs font-medium hover:bg-primary-700">생성</a>'
            )
        elif obj.status == VideoGenerationJob.Status.COMPLETED:
            if obj.final_video:
                buttons.append(
                    f'<a href="{obj.final_video.url}" target="_blank" class="px-3 py-1 bg-green-600 text-white rounded-md text-xs font-medium hover:bg-green-700">다운로드</a>'
                )
        elif obj.status == VideoGenerationJob.Status.FAILED:
            url = reverse("admin:videos_videogenerationjob_change", args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="px-3 py-1 bg-orange-600 text-white rounded-md text-xs font-medium hover:bg-orange-700">재시도</a>'
            )
        elif is_in_progress(obj.status):
            url = reverse("admin:videos_videogenerationjob_cancel_video_action", args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="px-3 py-1 bg-gray-600 text-white rounded-md text-xs font-medium hover:bg-gray-700">취소</a>'
            )

        content = " ".join(buttons) if buttons else "-"
        return f"<span {hx_attrs}>{content}</span>"

    @admin.display(description="액션")
    def row_actions(self, obj):
        """각 행에 액션 버튼 표시"""
        return mark_safe(self._render_row_actions(obj))

    @admin.display(description="유형")
    def job_type_badge(self, obj):
        """작업 유형 배지"""
        type_colors = {
            VideoGenerationJob.JobType.DRAMA: "bg-purple-100 text-purple-700",
            VideoGenerationJob.JobType.GAME: "bg-cyan-100 text-cyan-700",
        }
        css_class = type_colors.get(obj.job_type, "bg-gray-100 text-gray-700")
        return format_html(
            '<span class="{} px-2 py-1 rounded-md text-xs font-medium">{}</span>',
            css_class,
            obj.get_job_type_display(),
        )

    @admin.display(description="주제/게임")
    def topic_or_game(self, obj):
        """드라마는 topic, 게임은 game_name 표시"""
        if obj.job_type == VideoGenerationJob.JobType.GAME:
            return obj.game_name or "-"
        return obj.topic or "-"

    @admin.display(description="캐릭터 이미지")
    def character_image_preview(self, obj):
        """캐릭터 이미지 미리보기"""
        if obj.character_image:
            return format_html(
                '<img src="{}" width="180" height="320" style="object-fit: cover; border-radius: 8px;" />',
                obj.character_image.url,
            )
        return "-"

    def video_style_badge(self, obj):
        """영상 스타일 배지 (드라마 타입만)"""
        if obj.job_type == VideoGenerationJob.JobType.GAME:
            return "-"
        style_colors = {
            "makjang_drama": "bg-purple-100 text-purple-700",
        }
        css_class = style_colors.get(obj.video_style, "bg-gray-100 text-gray-700")
        return format_html(
            '<span class="{} px-2 py-1 rounded-md text-xs font-medium">{}</span>',
            css_class,
            obj.get_video_style_display(),
        )

    video_style_badge.short_description = "스타일"
    video_style_badge.admin_order_field = "video_style"

    def _render_status_badge(self, obj):
        """Render status badge HTML with HTMX attributes."""
        css_class = get_status_color(obj.status)
        hx_attrs = self._get_htmx_attrs(obj, "status")
        return f'<span class="{css_class} px-2 py-1 rounded-md text-xs font-medium" {hx_attrs}>{obj.get_status_display()}</span>'

    def status_badge(self, obj):
        return mark_safe(self._render_status_badge(obj))

    status_badge.short_description = "상태"
    status_badge.admin_order_field = "status"

    def _render_progress_bar(self, obj):
        """Render progress bar HTML with HTMX attributes."""
        # 게임 타입은 다른 진행률 함수 사용
        if obj.job_type == VideoGenerationJob.JobType.GAME:
            progress = get_game_progress_percent(obj.status)
        else:
            progress = get_progress_percent(obj.status)
        hx_attrs = self._get_htmx_attrs(obj, "progress")

        # Failed state
        if obj.status == VideoGenerationJob.Status.FAILED:
            if obj.job_type == VideoGenerationJob.JobType.GAME:
                failed_progress = get_game_progress_percent(obj.failed_at_status) if obj.failed_at_status else 0
            else:
                failed_progress = get_progress_percent(obj.failed_at_status) if obj.failed_at_status else 0
            if failed_progress > 0:
                return f"""<div {hx_attrs}>
                    <div style="width: 100px; height: 8px; background: #fee2e2; border-radius: 4px; overflow: hidden;">
                        <div style="width: {failed_progress}%; height: 100%; background: #ef4444; border-radius: 4px;"></div>
                    </div>
                    <span style="font-size: 10px; color: #ef4444;">실패 ({failed_progress}%)</span>
                </div>"""
            return f"""<div {hx_attrs}>
                <div style="width: 100px; height: 8px; background: #fee2e2; border-radius: 4px;"></div>
                <span style="font-size: 10px; color: #ef4444;">실패</span>
            </div>"""

        # Completed state
        if obj.status == VideoGenerationJob.Status.COMPLETED:
            return f"""<div {hx_attrs}>
                <div style="width: 100px; height: 8px; background: #dcfce7; border-radius: 4px;">
                    <div style="width: 100%; height: 100%; background: #22c55e; border-radius: 4px;"></div>
                </div>
                <span style="font-size: 10px; color: #22c55e;">100%</span>
            </div>"""

        # Pending state
        if obj.status == VideoGenerationJob.Status.PENDING:
            return f"""<div {hx_attrs}>
                <div style="width: 100px; height: 8px; background: #f3f4f6; border-radius: 4px;"></div>
                <span style="font-size: 10px; color: #9ca3af;">대기중</span>
            </div>"""

        # In progress state
        return f"""<div {hx_attrs}>
            <div style="width: 100px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                <div style="width: {progress}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa);
                    border-radius: 4px; animation: pulse 2s infinite;"></div>
            </div>
            <span style="font-size: 10px; color: #3b82f6;">{progress}%</span>
        </div>"""

    def progress_bar(self, obj):
        """진행 바 표시 (7단계)"""
        return mark_safe(self._render_progress_bar(obj))

    progress_bar.short_description = "진행도"

    def _render_current_step(self, obj):
        """Render current step HTML with HTMX attributes."""
        hx_attrs = self._get_htmx_attrs(obj, "current-step")
        step = obj.current_step or "-"
        return f"<span {hx_attrs}>{step}</span>"

    def current_step_display(self, obj):
        """현재 단계 표시"""
        return mark_safe(self._render_current_step(obj))

    current_step_display.short_description = "현재 단계"

    def segment_count(self, obj):
        """세그먼트 또는 게임 프레임 수 표시"""
        # 게임 타입
        if obj.job_type == VideoGenerationJob.JobType.GAME:
            total = obj.game_frames.count()
            completed = obj.game_frames.exclude(video_file="").count()
            if total == 0:
                return "-"
            return f"{completed}/{total}"
        # 드라마 타입
        total = obj.segments.count()
        completed = obj.segments.filter(status=VideoSegment.Status.COMPLETED).count()
        if total == 0:
            return "-"
        return f"{completed}/{total}"

    segment_count.short_description = "세그먼트"

    def video_preview(self, obj):
        if obj.final_video:
            return format_html(
                '<a href="{}" target="_blank" class="text-green-600 hover:text-green-700 font-semibold">다운로드</a>',
                obj.final_video.url,
            )
        return "-"

    video_preview.short_description = "최종 영상"

    def first_frame_preview(self, obj):
        if obj.first_frame:
            return format_html(
                '<img src="{}" width="320" height="180" style="object-fit: cover; '
                'border-radius: 8px;" />',
                obj.first_frame.url,
            )
        return "-"

    first_frame_preview.short_description = "Scene 1 첫 프레임"

    def scene1_last_frame_preview(self, obj):
        if obj.scene1_last_frame:
            return format_html(
                '<img src="{}" width="320" height="180" style="object-fit: cover; '
                'border-radius: 8px;" />',
                obj.scene1_last_frame.url,
            )
        return "-"

    scene1_last_frame_preview.short_description = "Scene 1 마지막 프레임"

    def cta_last_frame_preview(self, obj):
        if obj.cta_last_frame:
            return format_html(
                '<img src="{}" width="320" height="180" style="object-fit: cover; '
                'border-radius: 8px;" />',
                obj.cta_last_frame.url,
            )
        return "-"

    cta_last_frame_preview.short_description = "CTA 마지막 프레임"

    def _render_progress_steps(self, obj):
        """Render progress steps HTML with HTMX attributes.

        For Drama type (8-step):
        1. 대기 (Pending)
        2. 기획 (Planning) - Gemini AI script generation
        3. 첫 프레임 (First Frame) - Nano Banana image generation
        4. Scene 1 - Veo video generation
        5. CTA 프레임 (CTA Frame) - Product CTA frame generation
        6. Scene 2 - Veo video interpolation
        7. 병합 (Concatenation) - FFmpeg video merge
        8. 완료 (Completed)

        For Game type (6-step):
        1. 대기 (Pending)
        2. 기획 (Planning) - Gemini AI script generation
        3. 프레임 (Frames) - Nano Banana frame generation (5 parallel)
        4. 영상 (Videos) - Veo video generation (5 parallel)
        5. 병합 (Merge) - FFmpeg with fade transition
        6. 완료 (Completed)

        Uses HTMX polling (3s interval) for real-time updates during generation.

        Args:
            obj: VideoGenerationJob instance

        Returns:
            HTML string with styled progress cards and progress bar
        """
        hx_attrs = self._get_htmx_attrs(obj, "progress-steps")

        # 게임 타입은 다른 함수 사용
        if obj.job_type == VideoGenerationJob.JobType.GAME:
            current_order = get_game_status_order(obj.status)
            if obj.status == VideoGenerationJob.Status.FAILED:
                return self._render_game_failed_progress_steps(obj, hx_attrs)
            return self._render_game_normal_progress_steps(obj, hx_attrs, current_order)

        # 드라마 타입
        current_order = get_status_order(obj.status)

        # 실패 상태: 실패 지점까지 진행 상황 표시
        if obj.status == VideoGenerationJob.Status.FAILED:
            return self._render_failed_progress_steps(obj, hx_attrs)

        # 정상 상태: 현재 진행 상황 표시
        return self._render_normal_progress_steps(obj, hx_attrs, current_order)

    def _render_error_box(self, error_message: str) -> str:
        """Render error message box HTML."""
        return f"""
        <div style="padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px; color: #dc2626; font-weight: 600;">
                <span style="font-size: 20px;">&#10060;</span>
                <span>영상 생성 실패</span>
            </div>
            <div style="margin-top: 8px; color: #7f1d1d; font-size: 14px;">
                {error_message or '알 수 없는 오류가 발생했습니다.'}
            </div>
        </div>
        """

    def _render_detail_progress_bar(self, progress_percent: int, label: str, color: str, bg_color: str) -> str:
        """Render a progress bar HTML for detail page."""
        return f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #374151;">{label}</span>
                <span style="font-size: 14px; font-weight: 600; color: {color};">{int(progress_percent)}%</span>
            </div>
            <div style="width: 100%; height: 12px; background: {bg_color}; border-radius: 6px; overflow: hidden;">
                <div style="width: {progress_percent}%; height: 100%; background: {color}; border-radius: 6px;"></div>
            </div>
        </div>
        """

    def _get_step_style(self, step_index: int, current_order: int, is_failed: bool = False) -> tuple[str, str, str, str, str]:
        """Get step card styling based on status.

        Returns:
            Tuple of (icon, bg_color, border_color, icon_color, text_color)
        """
        if step_index < current_order:
            # 완료된 단계
            return "&#10004;", "#dcfce7", "#22c55e", "#22c55e", "#166534"
        elif step_index == current_order:
            if is_failed:
                # 실패한 단계
                return "&#10060;", "#fef2f2", "#ef4444", "#ef4444", "#991b1b"
            else:
                # 현재 단계
                return "&#9679;", "#dbeafe", "#3b82f6", "#3b82f6", "#1e40af"
        else:
            # 대기 단계
            return "&#9675;", "#f9fafb", "#e5e7eb", "#9ca3af", "#6b7280"

    def _render_step_card(self, label: str, description: str, icon: str, bg_color: str,
                          border_color: str, icon_color: str, text_color: str, step_info: str = "") -> str:
        """Render a single step card HTML."""
        return f"""
        <div style="padding: 12px; background: {bg_color}; border: 2px solid {border_color}; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 18px; color: {icon_color};">{icon}</span>
                <span style="font-weight: 600; color: {text_color};">{label}</span>
            </div>
            <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{description}</div>
            {step_info}
        </div>
        """

    def _render_failed_progress_steps(self, obj, hx_attrs: str) -> str:
        """Render progress steps for failed status."""
        failed_order = get_status_order(obj.failed_at_status) if obj.failed_at_status else 0
        progress_percent = min(100, (failed_order / TOTAL_STEPS) * 100) if failed_order > 0 else 0

        error_html = self._render_error_box(obj.error_message)
        progress_bar = self._render_detail_progress_bar(progress_percent, "진행률 (실패 시점)", "#ef4444", "#fee2e2")

        html = f'<div {hx_attrs}>{error_html}{progress_bar}<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">'

        for i, (status_key, label, description) in enumerate(PROGRESS_STEPS):
            icon, bg_color, border_color, icon_color, text_color = self._get_step_style(i, failed_order, is_failed=True)
            html += self._render_step_card(label, description, icon, bg_color, border_color, icon_color, text_color)

        html += "</div></div>"
        return html

    def _render_normal_progress_steps(self, obj, hx_attrs: str, current_order: int) -> str:
        """Render progress steps for normal status."""
        progress_percent = min(100, (current_order / TOTAL_STEPS) * 100)

        # Use gradient for normal progress
        progress_bar_html = f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #374151;">전체 진행률</span>
                <span style="font-size: 14px; font-weight: 600; color: #3b82f6;">{int(progress_percent)}%</span>
            </div>
            <div style="width: 100%; height: 12px; background: #e5e7eb; border-radius: 6px; overflow: hidden;">
                <div style="width: {progress_percent}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 6px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        """

        html = f'<div {hx_attrs}>{progress_bar_html}<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">'

        for i, (status_key, label, description) in enumerate(PROGRESS_STEPS):
            icon, bg_color, border_color, icon_color, text_color = self._get_step_style(i, current_order)

            # 현재 단계면 current_step 표시
            step_info = ""
            if i == current_order and obj.current_step:
                step_info = f'<div style="font-size: 11px; color: #3b82f6; margin-top: 4px;">{obj.current_step}</div>'

            html += self._render_step_card(label, description, icon, bg_color, border_color, icon_color, text_color, step_info)

        html += "</div></div>"
        return html

    def _render_game_failed_progress_steps(self, obj, hx_attrs: str) -> str:
        """Render progress steps for failed game status."""
        failed_order = get_game_status_order(obj.failed_at_status) if obj.failed_at_status else 0
        progress_percent = min(100, (failed_order / GAME_TOTAL_STEPS) * 100) if failed_order > 0 else 0

        error_html = self._render_error_box(obj.error_message)
        progress_bar = self._render_detail_progress_bar(progress_percent, "진행률 (실패 시점)", "#ef4444", "#fee2e2")

        # 게임은 6단계이므로 3열
        html = f'<div {hx_attrs}>{error_html}{progress_bar}<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">'

        for i, (status_key, label, description) in enumerate(GAME_PROGRESS_STEPS):
            icon, bg_color, border_color, icon_color, text_color = self._get_step_style(i, failed_order, is_failed=True)
            html += self._render_step_card(label, description, icon, bg_color, border_color, icon_color, text_color)

        html += "</div></div>"
        return html

    def _render_game_normal_progress_steps(self, obj, hx_attrs: str, current_order: int) -> str:
        """Render progress steps for normal game status."""
        progress_percent = min(100, (current_order / GAME_TOTAL_STEPS) * 100)

        progress_bar_html = f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #374151;">전체 진행률</span>
                <span style="font-size: 14px; font-weight: 600; color: #3b82f6;">{int(progress_percent)}%</span>
            </div>
            <div style="width: 100%; height: 12px; background: #e5e7eb; border-radius: 6px; overflow: hidden;">
                <div style="width: {progress_percent}%; height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee); border-radius: 6px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        """

        # 게임은 6단계이므로 3열
        html = f'<div {hx_attrs}>{progress_bar_html}<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">'

        for i, (status_key, label, description) in enumerate(GAME_PROGRESS_STEPS):
            icon, bg_color, border_color, icon_color, text_color = self._get_step_style(i, current_order)

            # 현재 단계면 current_step 표시
            step_info = ""
            if i == current_order and obj.current_step:
                step_info = f'<div style="font-size: 11px; color: #06b6d4; margin-top: 4px;">{obj.current_step}</div>'

            html += self._render_step_card(label, description, icon, bg_color, border_color, icon_color, text_color, step_info)

        html += "</div></div>"
        return html

    def progress_steps_display(self, obj):
        """단계별 진행 상황 표시"""
        return mark_safe(self._render_progress_steps(obj))

    progress_steps_display.short_description = "진행 상황"


# =============================================================================
# VideoSegment Admin (독립 CRUD)
# =============================================================================


@admin.register(VideoSegment)
class VideoSegmentAdmin(ModelAdmin):
    list_display = [
        "id",
        "job_link",
        "segment_index",
        "title",
        "seconds",
        "status_badge",
        "video_preview",
        "last_frame_preview",
    ]
    list_filter = ["status", "job__status", "segment_index"]
    search_fields = ["job__topic", "title", "prompt"]
    list_display_links = ["id"]
    autocomplete_fields = ["job"]

    fieldsets = (
        (None, {"fields": ("job", "segment_index", "title", "seconds")}),
        ("프롬프트", {"fields": ("prompt",)}),
        (
            "결과",
            {
                "fields": (
                    "status",
                    "video_file",
                    "video_preview_large",
                    "last_frame",
                    "last_frame_preview_large",
                )
            },
        ),
        ("에러", {"fields": ("error_message",), "classes": ("collapse",)}),
    )
    readonly_fields = ["video_preview_large", "last_frame_preview_large"]

    @admin.display(description="작업")
    def job_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:videos_videogenerationjob_change", args=[obj.job_id])
        return format_html('<a href="{}">{}</a>', url, obj.job.topic[:30])

    @admin.display(description="상태")
    def status_badge(self, obj):
        colors = {
            VideoSegment.Status.PENDING: "bg-gray-100 text-gray-700",
            VideoSegment.Status.GENERATING: "bg-yellow-100 text-yellow-700",
            VideoSegment.Status.COMPLETED: "bg-green-100 text-green-700",
            VideoSegment.Status.SKIPPED: "bg-red-100 text-red-700",
        }
        css_class = colors.get(obj.status, "bg-gray-100 text-gray-700")
        return format_html(
            '<span class="{} px-2 py-1 rounded-md text-xs font-medium">{}</span>',
            css_class,
            obj.get_status_display(),
        )

    @admin.display(description="영상")
    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<a href="{}" target="_blank" class="text-primary-600 hover:text-primary-700 font-medium">다운로드</a>',
                obj.video_file.url,
            )
        return "-"

    @admin.display(description="영상 미리보기")
    def video_preview_large(self, obj):
        if obj.video_file:
            return format_html(
                '<video width="480" height="270" controls style="border-radius: 8px;">'
                '<source src="{}" type="video/mp4">'
                "</video>",
                obj.video_file.url,
            )
        return "-"

    @admin.display(description="마지막 프레임")
    def last_frame_preview(self, obj):
        if obj.last_frame:
            return format_html(
                '<img src="{}" width="80" height="45" style="object-fit: cover; border-radius: 4px;" />',
                obj.last_frame.url,
            )
        return "-"

    @admin.display(description="마지막 프레임 미리보기")
    def last_frame_preview_large(self, obj):
        if obj.last_frame:
            return format_html(
                '<img src="{}" width="320" height="180" style="object-fit: cover; border-radius: 8px;" />',
                obj.last_frame.url,
            )
        return "-"


# =============================================================================
# GameFrame Admin (독립 CRUD)
# =============================================================================


@admin.register(GameFrame)
class GameFrameAdmin(ModelAdmin):
    list_display = [
        "id",
        "job_link",
        "scene_number",
        "shot_type",
        "game_location",
        "image_preview",
        "video_preview",
    ]
    list_filter = ["scene_number", "job__status"]
    search_fields = ["job__game_name", "game_location", "prompt"]
    list_display_links = ["id"]
    autocomplete_fields = ["job"]

    fieldsets = (
        (None, {"fields": ("job", "scene_number", "shot_type", "game_location")}),
        ("프롬프트", {"fields": ("prompt", "action", "camera", "description_kr")}),
        (
            "결과",
            {
                "fields": (
                    "image_file",
                    "image_preview_large",
                    "video_file",
                    "video_preview_large",
                )
            },
        ),
    )
    readonly_fields = ["image_preview_large", "video_preview_large"]

    @admin.display(description="작업")
    def job_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:videos_videogenerationjob_change", args=[obj.job_id])
        game_name = obj.job.game_name[:30] if obj.job.game_name else "-"
        return format_html('<a href="{}">{}</a>', url, game_name)

    @admin.display(description="프레임")
    def image_preview(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" width="45" height="80" style="object-fit: cover; border-radius: 4px;" />',
                obj.image_file.url,
            )
        return "-"

    @admin.display(description="프레임 미리보기")
    def image_preview_large(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" width="180" height="320" style="object-fit: cover; border-radius: 8px;" />',
                obj.image_file.url,
            )
        return "-"

    @admin.display(description="영상")
    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<a href="{}" target="_blank" class="text-primary-600 hover:text-primary-700 font-medium">다운로드</a>',
                obj.video_file.url,
            )
        return "-"

    @admin.display(description="영상 미리보기")
    def video_preview_large(self, obj):
        if obj.video_file:
            return format_html(
                '<video width="270" height="480" controls style="border-radius: 8px;">'
                '<source src="{}" type="video/mp4">'
                "</video>",
                obj.video_file.url,
            )
        return "-"


# =============================================================================
# 자동 등록 실행 (파일 맨 끝에서 실행해야 커스텀 ModelAdmin이 우선 적용됨)
# =============================================================================
auto_register_models()
