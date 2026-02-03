"""Constants for video generation.

Centralizes magic numbers and configuration values.
"""

# =============================================================================
# Video Duration Constants
# =============================================================================

DEFAULT_SEGMENT_DURATION = 8  # seconds per scene
LAST_CTA_DURATION = 2  # seconds for last CTA segment

# =============================================================================
# Retry Configuration
# =============================================================================

MAX_MODERATION_RETRIES = 5  # Maximum retry attempts for moderation errors

# =============================================================================
# Timeout Configuration (milliseconds)
# =============================================================================

FAL_VIDEO_DOWNLOAD_TIMEOUT = 300  # 5 minutes for video download
FAL_IMAGE_DOWNLOAD_TIMEOUT = 60  # 1 minute for image download

# =============================================================================
# Moderation Error Detection
# =============================================================================

# Keywords that indicate content moderation rejection
MODERATION_KEYWORDS = [
    "moderation",
    "blocked",
    "safety",
    "sensitive",
    "content filter",
    "nsfw",
    "policy",
]
