"""Tests for videos services module."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from videos.models import VideoGenerationJob, VideoSegment
from videos.services import (
    _build_initial_state,
    _build_resume_state,
    _create_video_segments,
    get_resume_entry_point,
)


class BuildInitialStateTest(TestCase):
    """Tests for _build_initial_state function."""

    def test_build_initial_state_basic(self):
        """Test building initial state from job."""
        job = VideoGenerationJob.objects.create(topic="Test topic")
        state = _build_initial_state(job)

        self.assertEqual(state["topic"], "Test topic")
        self.assertIsNone(state["script"])
        self.assertIsNone(state["product_image_url"])
        self.assertIsNone(state["first_frame_url"])
        self.assertEqual(state["segment_videos"], [])
        self.assertEqual(state["status"], "pending")

    def test_build_initial_state_with_script(self):
        """Test building initial state with script."""
        job = VideoGenerationJob.objects.create(
            topic="Test topic",
            script="Custom script",
        )
        state = _build_initial_state(job)

        self.assertEqual(state["script"], "Custom script")


class CreateVideoSegmentsTest(TestCase):
    """Tests for _create_video_segments function."""

    def test_create_segments(self):
        """Test creating video segments."""
        job = VideoGenerationJob.objects.create(topic="Test")
        segments_data = [
            {"title": "Scene 1", "seconds": 8, "prompt": "Prompt 1"},
            {"title": "Scene 2", "seconds": 8, "prompt": "Prompt 2"},
        ]

        _create_video_segments(job, segments_data)

        segments = list(job.segments.order_by("segment_index"))
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].title, "Scene 1")
        self.assertEqual(segments[0].prompt, "Prompt 1")
        self.assertEqual(segments[1].title, "Scene 2")
        self.assertEqual(segments[1].prompt, "Prompt 2")

    def test_create_segments_replaces_existing(self):
        """Test creating segments replaces existing ones."""
        job = VideoGenerationJob.objects.create(topic="Test")

        # Create initial segments
        _create_video_segments(job, [{"title": "Old Scene"}])
        self.assertEqual(job.segments.count(), 1)

        # Replace with new segments
        _create_video_segments(job, [{"title": "New Scene 1"}, {"title": "New Scene 2"}])

        segments = list(job.segments.order_by("segment_index"))
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].title, "New Scene 1")
        self.assertEqual(segments[1].title, "New Scene 2")

    def test_create_segments_with_defaults(self):
        """Test creating segments uses default values."""
        job = VideoGenerationJob.objects.create(topic="Test")
        _create_video_segments(job, [{}])

        segment = job.segments.first()
        self.assertEqual(segment.title, "Segment 1")
        self.assertEqual(segment.seconds, 8)
        self.assertEqual(segment.prompt, "")
        self.assertEqual(segment.status, VideoSegment.Status.PENDING)


class GetResumeEntryPointTest(TestCase):
    """Tests for get_resume_entry_point function."""

    def test_resume_from_pending(self):
        """Test resuming from PENDING status."""
        job = VideoGenerationJob.objects.create(
            topic="Test",
            status=VideoGenerationJob.Status.PENDING,
        )
        self.assertEqual(get_resume_entry_point(job), "plan_script")

    def test_resume_from_failed_at_generating(self):
        """Test resuming from failed at GENERATING_S1."""
        job = VideoGenerationJob.objects.create(
            topic="Test",
            status=VideoGenerationJob.Status.FAILED,
            failed_at_status=VideoGenerationJob.Status.GENERATING_S1,
        )
        self.assertEqual(get_resume_entry_point(job), "generate_scene1")

    def test_resume_from_failed_at_preparing(self):
        """Test resuming from failed at PREPARING."""
        job = VideoGenerationJob.objects.create(
            topic="Test",
            status=VideoGenerationJob.Status.FAILED,
            failed_at_status=VideoGenerationJob.Status.PREPARING,
        )
        self.assertEqual(get_resume_entry_point(job), "prepare_first_frame")


class BuildResumeStateTest(TestCase):
    """Tests for _build_resume_state function."""

    def test_build_resume_state_basic(self):
        """Test building resume state from job."""
        job = VideoGenerationJob.objects.create(
            topic="Test topic",
            script_json={"scenes": []},
        )
        state = _build_resume_state(job)

        self.assertEqual(state["topic"], "Test topic")
        self.assertEqual(state["script_json"], {"scenes": []})
        self.assertEqual(state["status"], "resuming")

    def test_build_resume_state_with_segments(self):
        """Test building resume state includes segment data."""
        job = VideoGenerationJob.objects.create(topic="Test")
        VideoSegment.objects.create(
            job=job,
            segment_index=0,
            title="Scene 1",
            seconds=8,
            prompt="Prompt 1",
        )

        state = _build_resume_state(job)

        self.assertEqual(len(state["segments"]), 1)
        self.assertEqual(state["segments"][0]["title"], "Scene 1")
        self.assertEqual(state["segments"][0]["prompt"], "Prompt 1")
