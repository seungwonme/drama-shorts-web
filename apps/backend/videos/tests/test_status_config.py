"""Tests for status_config module."""

from django.test import TestCase

from videos.models import VideoGenerationJob
from videos.status_config import (
    IN_PROGRESS_STATUSES,
    NODE_ORDER,
    NODE_TO_STATUS,
    PROGRESS_PERCENTAGES,
    PROGRESS_STEPS,
    STATUS_COLORS,
    STATUS_ORDER,
    STATUS_TO_RESUME_NODE,
    TOTAL_STEPS,
    get_progress_percent,
    get_resume_node,
    get_status_color,
    get_status_order,
    is_in_progress,
)


class StatusConfigTest(TestCase):
    """Tests for status configuration mappings."""

    def test_node_order_has_all_nodes(self):
        """Test NODE_ORDER contains all expected nodes."""
        expected_nodes = [
            "plan_script",
            "prepare_first_frame",
            "generate_scene1",
            "prepare_cta_frame",
            "generate_scene2",
            "concatenate_videos",
        ]
        self.assertEqual(NODE_ORDER, expected_nodes)

    def test_node_to_status_mapping(self):
        """Test all nodes map to valid statuses."""
        for node_name in NODE_ORDER:
            self.assertIn(node_name, NODE_TO_STATUS)
            status, display_text = NODE_TO_STATUS[node_name]
            self.assertIsInstance(status, str)
            self.assertIsInstance(display_text, str)

    def test_status_order_values(self):
        """Test STATUS_ORDER has correct ordering."""
        Status = VideoGenerationJob.Status
        self.assertEqual(STATUS_ORDER[Status.PENDING], 0)
        self.assertEqual(STATUS_ORDER[Status.COMPLETED], 7)
        self.assertEqual(STATUS_ORDER[Status.FAILED], -1)

    def test_progress_percentages_range(self):
        """Test all progress percentages are 0-100."""
        for status, percent in PROGRESS_PERCENTAGES.items():
            self.assertGreaterEqual(percent, 0)
            self.assertLessEqual(percent, 100)

    def test_progress_percentages_completed_is_100(self):
        """Test COMPLETED status is 100%."""
        Status = VideoGenerationJob.Status
        self.assertEqual(PROGRESS_PERCENTAGES[Status.COMPLETED], 100)

    def test_status_colors_exist_for_all_statuses(self):
        """Test all statuses have colors defined."""
        for status in VideoGenerationJob.Status.values:
            self.assertIn(status, STATUS_COLORS)

    def test_in_progress_statuses(self):
        """Test IN_PROGRESS_STATUSES list."""
        Status = VideoGenerationJob.Status
        self.assertIn(Status.PLANNING, IN_PROGRESS_STATUSES)
        self.assertIn(Status.GENERATING_S1, IN_PROGRESS_STATUSES)
        self.assertNotIn(Status.PENDING, IN_PROGRESS_STATUSES)
        self.assertNotIn(Status.COMPLETED, IN_PROGRESS_STATUSES)
        self.assertNotIn(Status.FAILED, IN_PROGRESS_STATUSES)

    def test_progress_steps_count(self):
        """Test PROGRESS_STEPS has correct number of steps."""
        self.assertEqual(len(PROGRESS_STEPS), 8)  # 7 steps + completed

    def test_total_steps_constant(self):
        """Test TOTAL_STEPS is 7."""
        self.assertEqual(TOTAL_STEPS, 7)


class StatusHelperFunctionsTest(TestCase):
    """Tests for status helper functions."""

    def test_get_status_color(self):
        """Test get_status_color returns correct colors."""
        Status = VideoGenerationJob.Status
        self.assertIn("green", get_status_color(Status.COMPLETED))
        self.assertIn("red", get_status_color(Status.FAILED))
        self.assertIn("gray", get_status_color(Status.PENDING))

    def test_get_status_color_unknown(self):
        """Test get_status_color returns default for unknown status."""
        color = get_status_color("unknown_status")
        self.assertIn("gray", color)

    def test_get_progress_percent(self):
        """Test get_progress_percent returns correct values."""
        Status = VideoGenerationJob.Status
        self.assertEqual(get_progress_percent(Status.PENDING), 0)
        self.assertEqual(get_progress_percent(Status.COMPLETED), 100)

    def test_get_progress_percent_unknown(self):
        """Test get_progress_percent returns 0 for unknown status."""
        self.assertEqual(get_progress_percent("unknown_status"), 0)

    def test_get_status_order(self):
        """Test get_status_order returns correct order."""
        Status = VideoGenerationJob.Status
        self.assertEqual(get_status_order(Status.PENDING), 0)
        self.assertEqual(get_status_order(Status.COMPLETED), 7)

    def test_get_status_order_unknown(self):
        """Test get_status_order returns 0 for unknown status."""
        self.assertEqual(get_status_order("unknown_status"), 0)

    def test_get_resume_node(self):
        """Test get_resume_node returns correct node names."""
        Status = VideoGenerationJob.Status
        self.assertEqual(get_resume_node(Status.PENDING), "plan_script")
        self.assertEqual(get_resume_node(Status.PLANNING), "plan_script")
        self.assertEqual(get_resume_node(Status.PREPARING), "prepare_first_frame")
        self.assertEqual(get_resume_node(Status.GENERATING_S1), "generate_scene1")
        self.assertEqual(get_resume_node(Status.GENERATING_S2), "generate_scene2")

    def test_get_resume_node_unknown(self):
        """Test get_resume_node returns plan_script for unknown status."""
        self.assertEqual(get_resume_node("unknown_status"), "plan_script")

    def test_is_in_progress(self):
        """Test is_in_progress returns correct boolean."""
        Status = VideoGenerationJob.Status
        self.assertTrue(is_in_progress(Status.PLANNING))
        self.assertTrue(is_in_progress(Status.GENERATING_S1))
        self.assertFalse(is_in_progress(Status.PENDING))
        self.assertFalse(is_in_progress(Status.COMPLETED))
        self.assertFalse(is_in_progress(Status.FAILED))
