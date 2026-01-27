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
        "product",
        "status_badge",
        "progress_bar",
        "current_step",
        "segment_count",
        "video_preview",
        "created_at",
    ]
    list_filter = ["status", "product", "created_at"]
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
    actions_detail = [
        "generate_video_action",
        "regenerate_first_frame_action",
        "regenerate_scene1_action",
        "regenerate_cta_last_frame_action",
        "regenerate_scene2_action",
        "regenerate_final_video_action",
    ]

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
            action for action in all_actions
            if any(action.action_name.endswith(f"_{name}") for name in allowed_action_names)
        ]

    def _get_allowed_action_names(self, job):
        """상태와 조건에 따라 허용할 액션 이름 반환"""
        # PENDING: 영상 생성 액션만
        if job.status == VideoGenerationJob.Status.PENDING:
            return ["generate_video_action"]

        # COMPLETED: 재작업 액션들
        if job.status == VideoGenerationJob.Status.COMPLETED:
            return self._get_rework_action_names(job)

        # 진행중/실패: 액션 없음
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
        ("입력", {"fields": ("topic", "script", "product", "product_image_url")}),
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
        from django.db import DatabaseError, transaction
        from django.shortcuts import redirect

        from .services import generate_video_sync_simple

        job = self.get_object(request, object_id)

        # Row-level lock으로 중복 실행 방지
        try:
            with transaction.atomic():
                locked_job = (
                    VideoGenerationJob.objects.select_for_update(nowait=True)
                    .filter(pk=job.pk, status=VideoGenerationJob.Status.PENDING)
                    .first()
                )
                if not locked_job:
                    self.message_user(
                        request,
                        f"Job #{job.id}은(는) 이미 처리 중이거나 대기 상태가 아닙니다.",
                        level="warning",
                    )
                    return redirect(request.META.get("HTTP_REFERER", ".."))

                # 즉시 상태 변경하여 다른 요청 차단
                locked_job.status = VideoGenerationJob.Status.GENERATING
                locked_job.current_step = "시작 중..."
                locked_job.save(update_fields=["status", "current_step"])
        except DatabaseError:
            # 이미 다른 요청에서 처리 중 (lock 획득 실패)
            self.message_user(
                request,
                f"Job #{job.id}은(는) 이미 다른 요청에서 처리 중입니다.",
                level="warning",
            )
            return redirect(request.META.get("HTTP_REFERER", ".."))

        # Lock 해제 후 실제 작업 수행
        try:
            generate_video_sync_simple(locked_job)
            self.message_user(request, f"Job #{job.id} 영상 생성 완료")
        except Exception as e:
            locked_job.status = VideoGenerationJob.Status.FAILED
            locked_job.error_message = str(e)
            locked_job.save()
            self.message_user(request, f"Job #{job.id} 실패: {e}", level="error")

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

    @action(description="CTA 마지막 프레임 재생성 (Nano Banana)", url_path="regenerate_cta_last_frame_action")
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

    def status_badge(self, obj):
        colors = {
            VideoGenerationJob.Status.PENDING: "bg-gray-100 text-gray-700",
            VideoGenerationJob.Status.PLANNING: "bg-blue-100 text-blue-700",
            VideoGenerationJob.Status.PREPARING: "bg-blue-100 text-blue-700",
            VideoGenerationJob.Status.GENERATING: "bg-yellow-100 text-yellow-700",
            VideoGenerationJob.Status.CONCATENATING: "bg-yellow-100 text-yellow-700",
            VideoGenerationJob.Status.COMPLETED: "bg-green-100 text-green-700",
            VideoGenerationJob.Status.FAILED: "bg-red-100 text-red-700",
        }
        css_class = colors.get(obj.status, "bg-gray-100 text-gray-700")
        return format_html(
            '<span class="{} px-2 py-1 rounded-md text-xs font-medium">{}</span>',
            css_class,
            obj.get_status_display(),
        )

    status_badge.short_description = "상태"
    status_badge.admin_order_field = "status"

    def progress_bar(self, obj):
        """진행 바 표시"""
        # 상태별 진행률
        progress_map = {
            VideoGenerationJob.Status.PENDING: 0,
            VideoGenerationJob.Status.PLANNING: 20,
            VideoGenerationJob.Status.PREPARING: 40,
            VideoGenerationJob.Status.GENERATING: 60,
            VideoGenerationJob.Status.CONCATENATING: 80,
            VideoGenerationJob.Status.COMPLETED: 100,
            VideoGenerationJob.Status.FAILED: 0,
        }
        progress = progress_map.get(obj.status, 0)

        # 실패 상태는 별도 표시
        if obj.status == VideoGenerationJob.Status.FAILED:
            return mark_safe(
                '<div style="width: 100px; height: 8px; background: #fee2e2; border-radius: 4px;">'
                '<div style="width: 100%; height: 100%; background: #ef4444; border-radius: 4px;"></div>'
                '</div>'
                '<span style="font-size: 10px; color: #ef4444;">실패</span>'
            )

        # 완료 상태
        if obj.status == VideoGenerationJob.Status.COMPLETED:
            return mark_safe(
                '<div style="width: 100px; height: 8px; background: #dcfce7; border-radius: 4px;">'
                '<div style="width: 100%; height: 100%; background: #22c55e; border-radius: 4px;"></div>'
                '</div>'
                '<span style="font-size: 10px; color: #22c55e;">100%</span>'
            )

        # 대기 상태
        if obj.status == VideoGenerationJob.Status.PENDING:
            return mark_safe(
                '<div style="width: 100px; height: 8px; background: #f3f4f6; border-radius: 4px;">'
                '</div>'
                '<span style="font-size: 10px; color: #9ca3af;">대기중</span>'
            )

        # 진행중 상태 (애니메이션 효과)
        return format_html(
            '<div style="width: 100px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); '
            'border-radius: 4px; animation: pulse 2s infinite;"></div>'
            '</div>'
            '<span style="font-size: 10px; color: #3b82f6;">{}%</span>',
            progress,
            progress,
        )

    progress_bar.short_description = "진행도"

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

    def progress_steps_display(self, obj):
        """단계별 진행 상황 표시"""
        # 단계 정의
        steps = [
            ("pending", "대기", "작업이 대기열에 있습니다"),
            ("planning", "기획", "Gemini AI가 스크립트를 기획합니다"),
            ("preparing", "에셋 준비", "첫 프레임 이미지를 생성합니다"),
            ("generating", "영상 생성", "Veo로 Scene 1, 2 영상을 생성합니다"),
            ("concatenating", "병합", "영상을 병합하고 효과음을 추가합니다"),
            ("completed", "완료", "영상 생성이 완료되었습니다"),
        ]

        # 상태별 순서
        status_order = {
            VideoGenerationJob.Status.PENDING: 0,
            VideoGenerationJob.Status.PLANNING: 1,
            VideoGenerationJob.Status.PREPARING: 2,
            VideoGenerationJob.Status.GENERATING: 3,
            VideoGenerationJob.Status.CONCATENATING: 4,
            VideoGenerationJob.Status.COMPLETED: 5,
            VideoGenerationJob.Status.FAILED: -1,
        }

        current_order = status_order.get(obj.status, 0)

        # 실패 상태 특별 처리
        if obj.status == VideoGenerationJob.Status.FAILED:
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
            return mark_safe(error_html)

        # 진행 바
        progress_percent = min(100, (current_order / 5) * 100)

        html = f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #374151;">전체 진행률</span>
                <span style="font-size: 14px; font-weight: 600; color: #3b82f6;">{int(progress_percent)}%</span>
            </div>
            <div style="width: 100%; height: 12px; background: #e5e7eb; border-radius: 6px; overflow: hidden;">
                <div style="width: {progress_percent}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 6px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
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

        html += "</div>"
        return mark_safe(html)

    progress_steps_display.short_description = "진행 상황"
