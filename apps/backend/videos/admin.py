from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from .models import Product, ProductImage, VideoAsset, VideoGenerationJob, VideoSegment

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


@admin.register(VideoGenerationJob)
class VideoGenerationJobAdmin(ModelAdmin):
    list_display = [
        "id",
        "topic",
        "video_style_badge",
        "product",
        "status_badge",
        "progress_bar",
        "current_step_display",
        "segment_count",
        "video_preview",
        "created_at",
        "row_actions",  # 행별 액션 버튼
    ]
    list_filter = ["status", "video_style", "product", "created_at"]
    search_fields = ["topic", "script", "product__name"]
    list_display_links = ["id", "topic"]
    readonly_fields = [
        "status",
        "current_step",
        "progress_steps_display",
        "error_message",
        "script_json",
        "product_detail",
        "character_details",
        "first_frame_preview",
        "scene1_last_frame_preview",
        "cta_last_frame_preview",
        "final_video",
        "skipped_segments",
        "created_at",
        "updated_at",
    ]
    inlines = [VideoSegmentInline]
    autocomplete_fields = ["product"]

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

    def htmx_status_view(self, request, job_id):
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

        return HttpResponse(self._render_status_badge(job))

    def htmx_progress_view(self, request, job_id):
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

        return HttpResponse(self._render_progress_bar(job))

    def htmx_current_step_view(self, request, job_id):
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

        return HttpResponse(self._render_current_step(job))

    def htmx_row_actions_view(self, request, job_id):
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

        return HttpResponse(self._render_row_actions(job))

    def htmx_progress_steps_view(self, request, job_id):
        from django.http import HttpResponse

        try:
            job = VideoGenerationJob.objects.get(pk=job_id)
        except VideoGenerationJob.DoesNotExist:
            return HttpResponse("-")

        return HttpResponse(self._render_progress_steps(job))

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
        in_progress_statuses = [
            VideoGenerationJob.Status.PLANNING,
            VideoGenerationJob.Status.PREPARING,
            VideoGenerationJob.Status.GENERATING_S1,
            VideoGenerationJob.Status.PREPARING_CTA,
            VideoGenerationJob.Status.GENERATING_S2,
            VideoGenerationJob.Status.CONCATENATING,
        ]
        if job.status in in_progress_statuses:
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

    fieldsets = (
        ("입력", {"fields": ("topic", "video_style", "script", "product", "product_image_url")}),
        ("에셋", {"fields": ("last_cta_asset", "sound_effect_asset")}),
        (
            "진행 상황",
            {
                "fields": ("progress_steps_display",),
            },
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
            {
                "fields": ("final_video", "skipped_segments"),
            },
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

        from .services import (
            generate_video_sync,
            generate_video_with_resume,
            get_resume_entry_point,
        )

        job = self.get_object(request, object_id)

        # PENDING 또는 FAILED 상태에서만 실행 가능
        allowed_statuses = [VideoGenerationJob.Status.PENDING, VideoGenerationJob.Status.FAILED]

        if job.status not in allowed_statuses:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 재시도 불가능한 상태입니다. (현재: {job.get_status_display()})",
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

        try:
            if should_resume:
                generate_video_with_resume(job)
                self.message_user(
                    request,
                    f"Job #{job.id} 영상 생성 완료 (재개 지점: {entry_point})",
                )
            else:
                generate_video_sync(job)
                self.message_user(request, f"Job #{job.id} 영상 생성 완료")
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="실패 지점부터 재개", url_path="resume_video_action")
    def resume_video_action(self, request, object_id):
        from django.shortcuts import redirect

        from .services import generate_video_with_resume, get_resume_entry_point

        job = self.get_object(request, object_id)

        # FAILED 상태에서만 재개 가능
        if job.status != VideoGenerationJob.Status.FAILED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 재개할 수 없는 상태입니다. (현재: {job.get_status_display()})",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 재개 지점 확인
        entry_point = get_resume_entry_point(job)
        if entry_point == "plan_script":
            self.message_user(
                request,
                f"Job #{job.id}은(는) 처음부터 재시도가 필요합니다. '영상 생성 실행' 버튼을 사용하세요.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 실제 작업 수행
        try:
            generate_video_with_resume(job)
            self.message_user(
                request,
                f"Job #{job.id} 영상 생성 완료 (재개 지점: {entry_point})",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="작업 취소", url_path="cancel_video_action")
    def cancel_video_action(self, request, object_id):
        from django.shortcuts import redirect

        job = self.get_object(request, object_id)

        # 진행중 상태에서만 취소 가능
        in_progress_statuses = [
            VideoGenerationJob.Status.PLANNING,
            VideoGenerationJob.Status.PREPARING,
            VideoGenerationJob.Status.GENERATING_S1,
            VideoGenerationJob.Status.PREPARING_CTA,
            VideoGenerationJob.Status.GENERATING_S2,
            VideoGenerationJob.Status.CONCATENATING,
        ]

        if job.status not in in_progress_statuses:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 진행중 상태가 아닙니다. (현재: {job.get_status_display()})",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # 실패 시점 기록 후 상태를 FAILED로 변경
        job.failed_at_status = job.status
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = "사용자에 의해 취소됨"
        job.current_step = "취소됨"
        job.save(update_fields=["status", "failed_at_status", "error_message", "current_step"])

        self.message_user(request, f"Job #{job.id} 작업이 취소되었습니다.", level="success")
        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="첫 프레임 재생성 (Nano Banana)", url_path="regenerate_first_frame_action")
    def regenerate_first_frame_action(self, request, object_id):
        from django.shortcuts import redirect

        from .rework_services import regenerate_first_frame

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 완료 상태가 아닙니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            regenerate_first_frame(job)
            self.message_user(
                request,
                f"Job #{job.id} 첫 프레임 재생성 완료. Scene 1, Scene 2, 최종 영상도 재생성 권장.",
                level="success",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="Scene 1 재생성 (Veo)", url_path="regenerate_scene1_action")
    def regenerate_scene1_action(self, request, object_id):
        from django.shortcuts import redirect

        from .rework_services import regenerate_scene1

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 완료 상태가 아닙니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            regenerate_scene1(job)
            self.message_user(
                request,
                f"Job #{job.id} Scene 1 재생성 완료. Scene 2, 최종 영상도 재생성 권장.",
                level="success",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(
        description="CTA 마지막 프레임 재생성 (Nano Banana)",
        url_path="regenerate_cta_last_frame_action",
    )
    def regenerate_cta_last_frame_action(self, request, object_id):
        from django.shortcuts import redirect

        from .rework_services import regenerate_cta_last_frame

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 완료 상태가 아닙니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            regenerate_cta_last_frame(job)
            self.message_user(
                request,
                f"Job #{job.id} CTA 마지막 프레임 재생성 완료. Scene 2, 최종 영상도 재생성 권장.",
                level="success",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="Scene 2 재생성 (Veo)", url_path="regenerate_scene2_action")
    def regenerate_scene2_action(self, request, object_id):
        from django.shortcuts import redirect

        from .rework_services import regenerate_scene2

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 완료 상태가 아닙니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            regenerate_scene2(job)
            self.message_user(
                request,
                f"Job #{job.id} Scene 2 재생성 완료. 최종 영상도 재생성 권장.",
                level="success",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    @action(description="최종 영상 병합 (FFmpeg)", url_path="regenerate_final_video_action")
    def regenerate_final_video_action(self, request, object_id):
        from django.shortcuts import redirect

        from .rework_services import regenerate_final_video

        job = self.get_object(request, object_id)

        if job.status != VideoGenerationJob.Status.COMPLETED:
            self.message_user(
                request,
                f"Job #{job.id}은(는) 완료 상태가 아닙니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        try:
            regenerate_final_video(job)
            self.message_user(
                request,
                f"Job #{job.id} 최종 영상 병합 완료.",
                level="success",
            )
        except Exception as e:
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

        return redirect(request.META.get("HTTP_REFERER", ".."))

    # =========================================================================
    # 목록 페이지 액션 (버튼 형태)
    # =========================================================================

    @admin.action(description="선택된 작업 영상 생성/재시도")
    def bulk_generate_video_action(self, request, queryset):
        """선택된 PENDING 또는 FAILED 작업들의 영상 생성 (실패 시 자동 재개)"""
        from .services import (
            generate_video_sync,
            generate_video_with_resume,
            get_resume_entry_point,
        )

        allowed_statuses = [VideoGenerationJob.Status.PENDING, VideoGenerationJob.Status.FAILED]
        eligible_jobs = queryset.filter(status__in=allowed_statuses)
        count = eligible_jobs.count()

        if count == 0:
            self.message_user(request, "대기중 또는 실패한 작업이 없습니다.", level="warning")
            return

        success = 0
        for job in eligible_jobs:
            try:
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

                if should_resume:
                    generate_video_with_resume(job)
                else:
                    generate_video_sync(job)
                success += 1
            except Exception:
                pass  # 에러는 서비스에서 저장됨

        self.message_user(request, f"{success}/{count}개 영상 생성 완료")

    @admin.action(description="선택된 작업 삭제")
    def bulk_delete_selected(self, request, queryset):
        """선택된 작업 삭제"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count}개 작업 삭제됨")

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
        elif obj.status in [
            VideoGenerationJob.Status.PLANNING,
            VideoGenerationJob.Status.PREPARING,
            VideoGenerationJob.Status.GENERATING_S1,
            VideoGenerationJob.Status.PREPARING_CTA,
            VideoGenerationJob.Status.GENERATING_S2,
            VideoGenerationJob.Status.CONCATENATING,
        ]:
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

    def video_style_badge(self, obj):
        """영상 스타일 배지"""
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
        colors = {
            VideoGenerationJob.Status.PENDING: "bg-gray-100 text-gray-700",
            VideoGenerationJob.Status.PLANNING: "bg-blue-100 text-blue-700",
            VideoGenerationJob.Status.PREPARING: "bg-blue-100 text-blue-700",
            VideoGenerationJob.Status.GENERATING_S1: "bg-yellow-100 text-yellow-700",
            VideoGenerationJob.Status.PREPARING_CTA: "bg-blue-100 text-blue-700",
            VideoGenerationJob.Status.GENERATING_S2: "bg-yellow-100 text-yellow-700",
            VideoGenerationJob.Status.CONCATENATING: "bg-yellow-100 text-yellow-700",
            VideoGenerationJob.Status.COMPLETED: "bg-green-100 text-green-700",
            VideoGenerationJob.Status.FAILED: "bg-red-100 text-red-700",
        }
        css_class = colors.get(obj.status, "bg-gray-100 text-gray-700")
        hx_attrs = self._get_htmx_attrs(obj, "status")
        return f'<span class="{css_class} px-2 py-1 rounded-md text-xs font-medium" {hx_attrs}>{obj.get_status_display()}</span>'

    def status_badge(self, obj):
        return mark_safe(self._render_status_badge(obj))

    status_badge.short_description = "상태"
    status_badge.admin_order_field = "status"

    def _render_progress_bar(self, obj):
        """Render progress bar HTML with HTMX attributes."""
        progress_map = {
            VideoGenerationJob.Status.PENDING: 0,
            VideoGenerationJob.Status.PLANNING: 14,
            VideoGenerationJob.Status.PREPARING: 28,
            VideoGenerationJob.Status.GENERATING_S1: 42,
            VideoGenerationJob.Status.PREPARING_CTA: 57,
            VideoGenerationJob.Status.GENERATING_S2: 71,
            VideoGenerationJob.Status.CONCATENATING: 86,
            VideoGenerationJob.Status.COMPLETED: 100,
            VideoGenerationJob.Status.FAILED: 0,
        }
        progress = progress_map.get(obj.status, 0)
        hx_attrs = self._get_htmx_attrs(obj, "progress")

        # Failed state
        if obj.status == VideoGenerationJob.Status.FAILED:
            failed_progress = progress_map.get(obj.failed_at_status, 0)
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
        """Render progress steps HTML with HTMX attributes."""
        hx_attrs = self._get_htmx_attrs(obj, "progress-steps")

        # 단계 정의 (7단계)
        steps = [
            ("pending", "대기", "작업이 대기열에 있습니다"),
            ("planning", "기획", "Gemini AI가 스크립트를 기획합니다"),
            ("preparing", "첫 프레임", "첫 프레임 이미지를 생성합니다"),
            ("generating_s1", "Scene 1", "Veo로 Scene 1 영상을 생성합니다"),
            ("preparing_cta", "CTA 프레임", "제품 CTA 프레임을 생성합니다"),
            ("generating_s2", "Scene 2", "Veo로 Scene 2 영상을 생성합니다"),
            ("concatenating", "병합", "영상을 병합하고 효과음을 추가합니다"),
            ("completed", "완료", "영상 생성이 완료되었습니다"),
        ]

        # 상태별 순서
        status_order = {
            VideoGenerationJob.Status.PENDING: 0,
            VideoGenerationJob.Status.PLANNING: 1,
            VideoGenerationJob.Status.PREPARING: 2,
            VideoGenerationJob.Status.GENERATING_S1: 3,
            VideoGenerationJob.Status.PREPARING_CTA: 4,
            VideoGenerationJob.Status.GENERATING_S2: 5,
            VideoGenerationJob.Status.CONCATENATING: 6,
            VideoGenerationJob.Status.COMPLETED: 7,
            VideoGenerationJob.Status.FAILED: -1,
        }

        current_order = status_order.get(obj.status, 0)

        # 실패 상태: 실패 지점까지 진행 상황 표시
        if obj.status == VideoGenerationJob.Status.FAILED:
            failed_order = status_order.get(obj.failed_at_status, 0)
            # 실패 지점까지의 진행률
            progress_percent = min(100, (failed_order / 7) * 100) if failed_order > 0 else 0

            # 에러 메시지 박스
            error_html = f"""
            <div style="padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px; color: #dc2626; font-weight: 600;">
                    <span style="font-size: 20px;">&#10060;</span>
                    <span>영상 생성 실패</span>
                </div>
                <div style="margin-top: 8px; color: #7f1d1d; font-size: 14px;">
                    {obj.error_message or '알 수 없는 오류가 발생했습니다.'}
                </div>
            </div>
            """

            # 진행 바 (with HTMX wrapper)
            html = f"""<div {hx_attrs}>{error_html}
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 14px; font-weight: 600; color: #374151;">진행률 (실패 시점)</span>
                    <span style="font-size: 14px; font-weight: 600; color: #ef4444;">{int(progress_percent)}%</span>
                </div>
                <div style="width: 100%; height: 12px; background: #fee2e2; border-radius: 6px; overflow: hidden;">
                    <div style="width: {progress_percent}%; height: 100%; background: #ef4444; border-radius: 6px;"></div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
            """

            # 단계별 표시 (실패 지점까지)
            for i, (status_key, label, description) in enumerate(steps):
                if i < failed_order:
                    # 완료된 단계
                    icon = "&#10004;"
                    bg_color = "#dcfce7"
                    border_color = "#22c55e"
                    icon_color = "#22c55e"
                    text_color = "#166534"
                elif i == failed_order:
                    # 실패한 단계
                    icon = "&#10060;"
                    bg_color = "#fef2f2"
                    border_color = "#ef4444"
                    icon_color = "#ef4444"
                    text_color = "#991b1b"
                else:
                    # 대기 단계
                    icon = "&#9675;"
                    bg_color = "#f9fafb"
                    border_color = "#e5e7eb"
                    icon_color = "#9ca3af"
                    text_color = "#6b7280"

                html += f"""
                <div style="padding: 12px; background: {bg_color}; border: 2px solid {border_color}; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px; color: {icon_color};">{icon}</span>
                        <span style="font-weight: 600; color: {text_color};">{label}</span>
                    </div>
                    <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{description}</div>
                </div>
                """

            html += "</div></div>"
            return html

        # 진행 바 (7단계) - with HTMX wrapper
        progress_percent = min(100, (current_order / 7) * 100)

        html = f"""<div {hx_attrs}>
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #374151;">전체 진행률</span>
                <span style="font-size: 14px; font-weight: 600; color: #3b82f6;">{int(progress_percent)}%</span>
            </div>
            <div style="width: 100%; height: 12px; background: #e5e7eb; border-radius: 6px; overflow: hidden;">
                <div style="width: {progress_percent}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 6px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
        """

        for i, (status_key, label, description) in enumerate(steps):
            if i < current_order:
                # 완료된 단계
                icon = "&#10004;"
                bg_color = "#dcfce7"
                border_color = "#22c55e"
                icon_color = "#22c55e"
                text_color = "#166534"
            elif i == current_order:
                # 현재 단계
                icon = "&#9679;"
                bg_color = "#dbeafe"
                border_color = "#3b82f6"
                icon_color = "#3b82f6"
                text_color = "#1e40af"
            else:
                # 대기 단계
                icon = "&#9675;"
                bg_color = "#f9fafb"
                border_color = "#e5e7eb"
                icon_color = "#9ca3af"
                text_color = "#6b7280"

            # 현재 단계면 current_step 표시
            step_info = ""
            if i == current_order and obj.current_step:
                step_info = f'<div style="font-size: 11px; color: #3b82f6; margin-top: 4px;">{obj.current_step}</div>'

            html += f"""
            <div style="padding: 12px; background: {bg_color}; border: 2px solid {border_color}; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px; color: {icon_color};">{icon}</span>
                    <span style="font-weight: 600; color: {text_color};">{label}</span>
                </div>
                <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{description}</div>
                {step_info}
            </div>
            """

        html += "</div></div>"
        return html

    def progress_steps_display(self, obj):
        """단계별 진행 상황 표시 (7단계)"""
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
# 자동 등록 실행 (파일 맨 끝에서 실행해야 커스텀 ModelAdmin이 우선 적용됨)
# =============================================================================
auto_register_models()
