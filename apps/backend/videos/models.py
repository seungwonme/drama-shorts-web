from django.db import models

from .generators.prompts import DEFAULT_VIDEO_STYLE, VideoStyle


# =============================================================================
# Upload path helpers (job id별 폴더 구조)
# =============================================================================


def job_frame_path(instance, filename):
    """Job 프레임 이미지 경로: jobs/{job_id}/frames/{filename}"""
    return f"jobs/{instance.id}/frames/{filename}"


def job_video_path(instance, filename):
    """Job 최종 영상 경로: jobs/{job_id}/{filename}"""
    return f"jobs/{instance.id}/{filename}"


def segment_video_path(instance, filename):
    """세그먼트 영상 경로: jobs/{job_id}/segments/{filename}"""
    return f"jobs/{instance.job_id}/segments/{filename}"


def segment_frame_path(instance, filename):
    """세그먼트 프레임 경로: jobs/{job_id}/segments/frames/{filename}"""
    return f"jobs/{instance.job_id}/segments/frames/{filename}"


# =============================================================================
# Models
# =============================================================================


class VideoAsset(models.Model):
    """영상 생성에 사용되는 에셋 (라스트 CTA 이미지, 효과음 등)"""

    class AssetType(models.TextChoices):
        LAST_CTA_IMAGE = "last_cta_image", "라스트 CTA 이미지"
        SOUND_EFFECT = "sound_effect", "효과음"

    name = models.CharField("이름", max_length=100)
    asset_type = models.CharField(
        "에셋 타입",
        max_length=20,
        choices=AssetType.choices,
    )
    file = models.FileField("파일", upload_to="assets/")
    is_active = models.BooleanField(
        "활성화",
        default=True,
        help_text="활성화된 에셋이 영상 생성에 사용됩니다. 타입별로 하나만 활성화 가능합니다.",
    )
    description = models.TextField("설명", blank=True)

    # 메타
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "영상 에셋"
        verbose_name_plural = "영상 에셋"
        ordering = ["asset_type", "-created_at"]

    def __str__(self):
        status = "✓" if self.is_active else ""
        return f"[{self.get_asset_type_display()}] {self.name} {status}"

    def save(self, *args, **kwargs):
        # 활성화 시 같은 타입의 다른 에셋 비활성화
        if self.is_active:
            VideoAsset.objects.filter(
                asset_type=self.asset_type, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_asset(cls, asset_type: str) -> "VideoAsset | None":
        """타입별 활성화된 에셋 반환"""
        return cls.objects.filter(asset_type=asset_type, is_active=True).first()

    @classmethod
    def get_last_cta_image_url(cls) -> str | None:
        """활성화된 라스트 CTA 이미지 URL 반환"""
        asset = cls.get_active_asset(cls.AssetType.LAST_CTA_IMAGE)
        return asset.file.url if asset else None

    @classmethod
    def get_sound_effect_url(cls) -> str | None:
        """활성화된 효과음 URL 반환"""
        asset = cls.get_active_asset(cls.AssetType.SOUND_EFFECT)
        return asset.file.url if asset else None


class Product(models.Model):
    """제품 정보"""

    name = models.CharField("제품명/상호", max_length=200)
    brand = models.CharField("브랜드", max_length=100, blank=True)
    description = models.TextField("브랜드/제품 설명", blank=True)

    # 메타
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "제품"
        verbose_name_plural = "제품"
        ordering = ["-created_at"]

    def __str__(self):
        if self.brand:
            return f"{self.brand} - {self.name}"
        return self.name

    @property
    def primary_image_url(self):
        """대표 이미지 URL 반환"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url
        first = self.images.first()
        if first:
            return first.image.url
        return None


class ProductImage(models.Model):
    """제품 이미지"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("이미지", upload_to="products/")
    alt_text = models.CharField("대체 텍스트", max_length=200, blank=True)
    is_primary = models.BooleanField("대표 이미지", default=False)
    order = models.PositiveSmallIntegerField("순서", default=0)

    # 메타
    created_at = models.DateTimeField("생성일", auto_now_add=True)

    class Meta:
        verbose_name = "제품 이미지"
        verbose_name_plural = "제품 이미지"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.product.name} 이미지 #{self.pk}"

    def save(self, *args, **kwargs):
        # 대표 이미지로 설정 시 다른 이미지의 is_primary를 False로
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class VideoGenerationJob(models.Model):
    """영상 생성 작업"""

    class JobType(models.TextChoices):
        DRAMA = "drama", "드라마타이즈 광고"
        GAME = "game", "게임 캐릭터 숏폼"

    class Status(models.TextChoices):
        # 공통 상태
        PENDING = "pending", "대기중"
        PLANNING = "planning", "기획중"
        COMPLETED = "completed", "완료"
        FAILED = "failed", "실패"

        # 드라마 전용 상태
        PREPARING = "preparing", "첫 프레임 생성중"
        GENERATING_S1 = "generating_s1", "Scene 1 생성중"
        PREPARING_CTA = "preparing_cta", "CTA 프레임 생성중"
        GENERATING_S2 = "generating_s2", "Scene 2 생성중"
        CONCATENATING = "concatenating", "병합중"

        # 게임 캐릭터 전용 상태
        GENERATING_FRAMES = "generating_frames", "프레임 생성중"
        GENERATING_VIDEOS = "generating_videos", "영상 생성중"
        MERGING = "merging", "영상 병합중"

    class VideoStyleChoice(models.TextChoices):
        """영상 스타일 선택"""

        MAKJANG_DRAMA = VideoStyle.MAKJANG_DRAMA.value, "B급 막장 드라마"
        LOTTERIA_STORY = VideoStyle.LOTTERIA_STORY.value, "롯데리아형 스토리"

    # Job Type
    job_type = models.CharField(
        "작업 유형",
        max_length=20,
        choices=JobType.choices,
        default=JobType.DRAMA,
    )

    # 입력
    topic = models.CharField("주제", max_length=200, help_text="광고할 제품/서비스")
    video_style = models.CharField(
        "영상 스타일",
        max_length=50,
        choices=VideoStyleChoice.choices,
        default=VideoStyleChoice.MAKJANG_DRAMA,
        help_text="영상 스타일 템플릿",
    )
    script = models.TextField(
        "스크립트", blank=True, help_text="선택적 줄거리/대본 (비어있으면 AI가 자동 생성)"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        verbose_name="제품",
        help_text="연결할 제품 (제품 이미지가 CTA에 사용됨)",
    )
    product_image_url = models.URLField(
        "제품 이미지 URL (직접 입력)",
        blank=True,
        help_text="제품을 선택하지 않고 직접 URL 입력 시 사용",
    )

    # ==========================================================================
    # 게임 캐릭터 전용 입력 필드
    # ==========================================================================
    character_image = models.ImageField(
        "캐릭터 이미지",
        upload_to="game_characters/",
        blank=True,
        help_text="게임 캐릭터 이미지 (게임 타입 전용)",
    )
    game_name = models.CharField(
        "게임명",
        max_length=200,
        blank=True,
        help_text="캐릭터가 들어갈 게임 이름 (예: PUBG, 원신)",
    )
    user_prompt = models.TextField(
        "추가 프롬프트",
        blank=True,
        help_text="영상에 대한 추가 요청사항",
    )
    character_description = models.TextField(
        "캐릭터 분석 결과",
        blank=True,
        help_text="AI가 분석한 캐릭터 외형 설명",
    )
    game_locations_used = models.JSONField(
        "사용된 게임 장소",
        default=list,
        blank=True,
        help_text="스크립트에 사용된 게임 내 장소 목록",
    )

    # ==========================================================================
    # 드라마 전용 에셋 선택 필드
    # ==========================================================================
    last_cta_asset = models.ForeignKey(
        VideoAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_as_cta",
        verbose_name="라스트 CTA 이미지",
        limit_choices_to={"asset_type": VideoAsset.AssetType.LAST_CTA_IMAGE},
        help_text="선택하지 않으면 기본 활성화된 에셋 사용 (드라마 타입 전용)",
    )
    sound_effect_asset = models.ForeignKey(
        VideoAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_as_sound",
        verbose_name="효과음",
        limit_choices_to={"asset_type": VideoAsset.AssetType.SOUND_EFFECT},
        help_text="선택하지 않으면 기본 활성화된 에셋 사용 (드라마 타입 전용)",
    )

    # 상태
    status = models.CharField(
        "상태", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    failed_at_status = models.CharField(
        "실패 시점 상태",
        max_length=20,
        blank=True,
        help_text="실패 시 어느 단계에서 실패했는지 기록 (재개 시 사용)",
    )
    current_step = models.CharField("현재 단계", max_length=100, blank=True)
    error_message = models.TextField("에러 메시지", blank=True)

    # 기획 결과
    script_json = models.JSONField("생성된 시나리오", null=True, blank=True)
    product_detail = models.JSONField("제품 정보", null=True, blank=True)
    character_details = models.JSONField("캐릭터 정보", null=True, blank=True)

    # 프레임 이미지 (S3 저장) - jobs/{job_id}/frames/
    first_frame = models.ImageField(
        "Scene 1 첫 프레임", upload_to=job_frame_path, blank=True
    )
    scene1_last_frame = models.ImageField(
        "Scene 1 마지막 프레임", upload_to=job_frame_path, blank=True
    )
    cta_last_frame = models.ImageField(
        "CTA 마지막 프레임", upload_to=job_frame_path, blank=True
    )

    # 최종 결과 - jobs/{job_id}/
    final_video = models.FileField("최종 영상", upload_to=job_video_path, blank=True)

    # 스킵된 세그먼트 (모더레이션 에러)
    skipped_segments = models.JSONField("스킵된 세그먼트", default=list, blank=True)

    # 메타
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "영상 생성 작업"
        verbose_name_plural = "영상 생성 작업"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.topic}"

    @property
    def effective_product_image_url(self):
        """제품 이미지 URL 반환 (제품 선택 > 직접 입력 URL)"""
        if self.product and self.product.primary_image_url:
            return self.product.primary_image_url
        return self.product_image_url or None

    @property
    def effective_last_cta_image_url(self):
        """라스트 CTA 이미지 URL 반환 (Job 선택 > 기본 활성 에셋)"""
        if self.last_cta_asset:
            return self.last_cta_asset.file.url
        return VideoAsset.get_last_cta_image_url()

    @property
    def effective_sound_effect_url(self):
        """효과음 URL 반환 (Job 선택 > 기본 활성 에셋)"""
        if self.sound_effect_asset:
            return self.sound_effect_asset.file.url
        return VideoAsset.get_sound_effect_url()


class VideoSegment(models.Model):
    """영상 세그먼트"""

    class Status(models.TextChoices):
        PENDING = "pending", "대기중"
        GENERATING = "generating", "생성중"
        COMPLETED = "completed", "완료"
        SKIPPED = "skipped", "스킵됨"

    job = models.ForeignKey(
        VideoGenerationJob, on_delete=models.CASCADE, related_name="segments"
    )
    segment_index = models.PositiveSmallIntegerField("세그먼트 번호")
    title = models.CharField("제목", max_length=100, blank=True)
    seconds = models.PositiveSmallIntegerField("길이(초)", default=8)
    prompt = models.TextField("프롬프트", blank=True)

    # 결과 - jobs/{job_id}/segments/
    video_file = models.FileField("세그먼트 영상", upload_to=segment_video_path, blank=True)
    last_frame = models.ImageField(
        "마지막 프레임", upload_to=segment_frame_path, blank=True
    )
    status = models.CharField(
        "상태", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField("에러 메시지", blank=True)

    class Meta:
        verbose_name = "영상 세그먼트"
        verbose_name_plural = "영상 세그먼트"
        ordering = ["segment_index"]
        unique_together = ["job", "segment_index"]

    def __str__(self):
        return f"Segment {self.segment_index}: {self.title}"


# =============================================================================
# Game Character Models (게임 캐릭터 숏폼 전용)
# =============================================================================


def game_frame_image_path(instance, filename):
    """게임 프레임 이미지 경로: jobs/{job_id}/game_frames/{filename}"""
    return f"jobs/{instance.job_id}/game_frames/{filename}"


def game_segment_video_path(instance, filename):
    """게임 세그먼트 영상 경로: jobs/{job_id}/game_segments/{filename}"""
    return f"jobs/{instance.job_id}/game_segments/{filename}"


class GameFrame(models.Model):
    """게임 캐릭터 숏폼의 각 씬 시작 프레임"""

    job = models.ForeignKey(
        VideoGenerationJob,
        on_delete=models.CASCADE,
        related_name="game_frames",
        verbose_name="영상 작업",
    )
    scene_number = models.PositiveSmallIntegerField("씬 번호")

    # 스크립트 정보
    shot_type = models.CharField("샷 타입", max_length=50, blank=True)
    game_location = models.CharField("게임 장소", max_length=200, blank=True)
    prompt = models.TextField("영상 생성 프롬프트")
    action = models.CharField("액션", max_length=200, blank=True)
    camera = models.CharField("카메라 움직임", max_length=200, blank=True)
    description_kr = models.TextField("한글 설명", blank=True)

    # 생성 결과
    image_file = models.ImageField(
        "시작 프레임 이미지",
        upload_to=game_frame_image_path,
        blank=True,
    )
    image_url = models.URLField("이미지 URL", blank=True)
    video_file = models.FileField(
        "생성된 영상",
        upload_to=game_segment_video_path,
        blank=True,
    )
    video_url = models.URLField("영상 URL", blank=True)

    # 메타
    created_at = models.DateTimeField("생성일", auto_now_add=True)

    class Meta:
        verbose_name = "게임 프레임"
        verbose_name_plural = "게임 프레임"
        ordering = ["scene_number"]
        unique_together = [["job", "scene_number"]]

    def __str__(self):
        location = self.game_location or "Unknown"
        return f"Scene {self.scene_number}: {location}"
