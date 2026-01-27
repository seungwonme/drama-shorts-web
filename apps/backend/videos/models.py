from django.db import models


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

    class Status(models.TextChoices):
        PENDING = "pending", "대기중"
        PLANNING = "planning", "기획중"
        PREPARING = "preparing", "에셋 준비중"
        GENERATING = "generating", "영상 생성중"
        CONCATENATING = "concatenating", "병합중"
        COMPLETED = "completed", "완료"
        FAILED = "failed", "실패"

    # 입력
    topic = models.CharField("주제", max_length=200, help_text="광고할 제품/서비스")
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

    # 에셋 선택 (Job별로 다른 에셋 사용 가능)
    last_cta_asset = models.ForeignKey(
        VideoAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_as_cta",
        verbose_name="라스트 CTA 이미지",
        limit_choices_to={"asset_type": VideoAsset.AssetType.LAST_CTA_IMAGE},
        help_text="선택하지 않으면 기본 활성화된 에셋 사용",
    )
    sound_effect_asset = models.ForeignKey(
        VideoAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_as_sound",
        verbose_name="효과음",
        limit_choices_to={"asset_type": VideoAsset.AssetType.SOUND_EFFECT},
        help_text="선택하지 않으면 기본 활성화된 에셋 사용",
    )

    # 상태
    status = models.CharField(
        "상태", max_length=20, choices=Status.choices, default=Status.PENDING
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
