"""Tests for videos constants module."""

from django.test import TestCase

from videos.constants import (
    ADMIN_LIST_DISPLAY_MAX,
    ADMIN_LIST_FILTER_MAX,
    ADMIN_SEARCH_FIELDS_MAX,
    DEFAULT_SEGMENT_DURATION,
    FAL_IMAGE_DOWNLOAD_TIMEOUT,
    FAL_VIDEO_DOWNLOAD_TIMEOUT,
    FRAME_EXTRACTION_EPSILON,
    LAST_CTA_DURATION,
    MAX_MODERATION_RETRIES,
    MODERATION_KEYWORDS,
    MSG_JOB_CANCELLED,
    MSG_JOB_FAILED,
    MSG_JOB_NOT_COMPLETED,
    MSG_JOB_NOT_RETRIABLE,
    MSG_JOB_RESUMED,
    MSG_JOB_STARTED,
    MSG_JOBS_DELETED,
    MSG_JOBS_STARTED,
    MSG_NO_ELIGIBLE_JOBS,
    PREVIEW_IMAGE_HEIGHT,
    PREVIEW_IMAGE_WIDTH,
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
)


class VideoDurationConstantsTest(TestCase):
    """Tests for video duration constants."""

    def test_default_segment_duration(self):
        """Test DEFAULT_SEGMENT_DURATION is 8 seconds."""
        self.assertEqual(DEFAULT_SEGMENT_DURATION, 8)

    def test_last_cta_duration(self):
        """Test LAST_CTA_DURATION is 2 seconds."""
        self.assertEqual(LAST_CTA_DURATION, 2)


class RetryConfigurationTest(TestCase):
    """Tests for retry configuration constants."""

    def test_max_moderation_retries(self):
        """Test MAX_MODERATION_RETRIES is reasonable."""
        self.assertGreaterEqual(MAX_MODERATION_RETRIES, 1)
        self.assertLessEqual(MAX_MODERATION_RETRIES, 10)


class TimeoutConfigurationTest(TestCase):
    """Tests for timeout configuration constants."""

    def test_video_download_timeout(self):
        """Test FAL_VIDEO_DOWNLOAD_TIMEOUT is reasonable."""
        self.assertGreaterEqual(FAL_VIDEO_DOWNLOAD_TIMEOUT, 60)  # At least 1 minute

    def test_image_download_timeout(self):
        """Test FAL_IMAGE_DOWNLOAD_TIMEOUT is reasonable."""
        self.assertGreaterEqual(FAL_IMAGE_DOWNLOAD_TIMEOUT, 30)  # At least 30 seconds


class ModerationKeywordsTest(TestCase):
    """Tests for moderation keywords."""

    def test_moderation_keywords_not_empty(self):
        """Test MODERATION_KEYWORDS is not empty."""
        self.assertGreater(len(MODERATION_KEYWORDS), 0)

    def test_moderation_keywords_are_lowercase(self):
        """Test all moderation keywords are lowercase."""
        for keyword in MODERATION_KEYWORDS:
            self.assertEqual(keyword, keyword.lower())


class VideoProcessingConstantsTest(TestCase):
    """Tests for video processing constants."""

    def test_frame_extraction_epsilon(self):
        """Test FRAME_EXTRACTION_EPSILON is small positive value."""
        self.assertGreater(FRAME_EXTRACTION_EPSILON, 0)
        self.assertLess(FRAME_EXTRACTION_EPSILON, 1)


class AdminUIConstantsTest(TestCase):
    """Tests for Admin UI constants."""

    def test_list_display_max(self):
        """Test ADMIN_LIST_DISPLAY_MAX is reasonable."""
        self.assertGreater(ADMIN_LIST_DISPLAY_MAX, 0)

    def test_preview_dimensions(self):
        """Test preview image dimensions are reasonable."""
        self.assertGreater(PREVIEW_IMAGE_WIDTH, 0)
        self.assertGreater(PREVIEW_IMAGE_HEIGHT, 0)
        self.assertGreater(THUMBNAIL_WIDTH, 0)
        self.assertGreater(THUMBNAIL_HEIGHT, 0)


class ErrorMessageTemplatesTest(TestCase):
    """Tests for error message templates."""

    def test_message_templates_have_placeholders(self):
        """Test message templates contain expected placeholders."""
        self.assertIn("{job_id}", MSG_JOB_NOT_RETRIABLE)
        self.assertIn("{status}", MSG_JOB_NOT_RETRIABLE)
        self.assertIn("{job_id}", MSG_JOB_CANCELLED)
        self.assertIn("{job_id}", MSG_JOB_FAILED)
        self.assertIn("{error}", MSG_JOB_FAILED)

    def test_message_formatting(self):
        """Test messages can be formatted correctly."""
        formatted = MSG_JOB_NOT_RETRIABLE.format(job_id=123, status="pending")
        self.assertIn("123", formatted)
        self.assertIn("pending", formatted)

        formatted = MSG_JOB_FAILED.format(job_id=456, error="Connection timeout")
        self.assertIn("456", formatted)
        self.assertIn("Connection timeout", formatted)

    def test_bulk_message_templates(self):
        """Test bulk action message templates."""
        self.assertIn("{count}", MSG_JOBS_STARTED)
        self.assertIn("{count}", MSG_JOBS_DELETED)

        formatted = MSG_JOBS_STARTED.format(count=5)
        self.assertIn("5", formatted)
