"""Tests for videos app models."""

from django.test import TestCase

from videos.models import Product, ProductImage, VideoAsset, VideoGenerationJob, VideoSegment


class ProductModelTest(TestCase):
    """Tests for Product model."""

    def test_create_product(self):
        """Test creating a product."""
        product = Product.objects.create(
            name="Test Product",
            brand="Test Brand",
            description="Test description",
        )
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.brand, "Test Brand")
        self.assertEqual(str(product), "Test Product")

    def test_primary_image_url_with_no_images(self):
        """Test primary_image_url returns None when no images."""
        product = Product.objects.create(name="Test Product")
        self.assertIsNone(product.primary_image_url)


class VideoGenerationJobModelTest(TestCase):
    """Tests for VideoGenerationJob model."""

    def test_create_job(self):
        """Test creating a video generation job."""
        job = VideoGenerationJob.objects.create(
            topic="Test topic",
            status=VideoGenerationJob.Status.PENDING,
        )
        self.assertEqual(job.topic, "Test topic")
        self.assertEqual(job.status, VideoGenerationJob.Status.PENDING)

    def test_job_str_representation(self):
        """Test job string representation."""
        job = VideoGenerationJob.objects.create(topic="Test topic")
        self.assertIn("Test topic", str(job))

    def test_job_with_product(self):
        """Test job with associated product."""
        product = Product.objects.create(name="Product A")
        job = VideoGenerationJob.objects.create(
            topic="Test topic",
            product=product,
        )
        self.assertEqual(job.product, product)

    def test_effective_product_image_url_with_product(self):
        """Test effective_product_image_url uses product's primary image."""
        product = Product.objects.create(name="Test Product")
        job = VideoGenerationJob.objects.create(topic="Test", product=product)
        # No images, should return None
        self.assertIsNone(job.effective_product_image_url)

    def test_effective_product_image_url_with_override(self):
        """Test product_image_url overrides product's image."""
        product = Product.objects.create(name="Test Product")
        job = VideoGenerationJob.objects.create(
            topic="Test",
            product=product,
            product_image_url="https://example.com/override.jpg",
        )
        self.assertEqual(job.effective_product_image_url, "https://example.com/override.jpg")


class VideoSegmentModelTest(TestCase):
    """Tests for VideoSegment model."""

    def test_create_segment(self):
        """Test creating a video segment."""
        job = VideoGenerationJob.objects.create(topic="Test")
        segment = VideoSegment.objects.create(
            job=job,
            segment_index=0,
            title="Scene 1",
            seconds=8,
            prompt="Test prompt",
        )
        self.assertEqual(segment.job, job)
        self.assertEqual(segment.segment_index, 0)
        self.assertEqual(segment.title, "Scene 1")
        self.assertEqual(segment.seconds, 8)

    def test_segment_ordering(self):
        """Test segments are ordered by segment_index."""
        job = VideoGenerationJob.objects.create(topic="Test")
        VideoSegment.objects.create(job=job, segment_index=1, title="Scene 2")
        VideoSegment.objects.create(job=job, segment_index=0, title="Scene 1")

        segments = list(job.segments.all())
        self.assertEqual(segments[0].segment_index, 0)
        self.assertEqual(segments[1].segment_index, 1)


class VideoAssetModelTest(TestCase):
    """Tests for VideoAsset model."""

    def test_create_asset(self):
        """Test creating a video asset."""
        asset = VideoAsset.objects.create(
            name="CTA Image",
            asset_type=VideoAsset.AssetType.LAST_CTA_IMAGE,
            is_active=True,
        )
        self.assertEqual(asset.name, "CTA Image")
        self.assertEqual(asset.asset_type, VideoAsset.AssetType.LAST_CTA_IMAGE)
        self.assertTrue(asset.is_active)
