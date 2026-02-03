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

# =============================================================================
# Error Message Templates
# =============================================================================

# Admin action error messages (format with job_id and status)
MSG_JOB_NOT_RETRIABLE = "Job #{job_id}은(는) 재시도 불가능한 상태입니다. (현재: {status})"
MSG_JOB_NOT_RESUMABLE = "Job #{job_id}은(는) 재개할 수 없는 상태입니다. (현재: {status})"
MSG_JOB_NOT_COMPLETED = "Job #{job_id}은(는) 완료 상태가 아닙니다."
MSG_JOB_NOT_IN_PROGRESS = "Job #{job_id}은(는) 진행중 상태가 아닙니다. (현재: {status})"
MSG_JOB_NEEDS_RESTART = "Job #{job_id}은(는) 처음부터 재시도가 필요합니다. '영상 생성 실행' 버튼을 사용하세요."

# Admin action success messages
MSG_JOB_STARTED = "Job #{job_id} 영상 생성 시작됨. 진행 상황은 자동으로 업데이트됩니다."
MSG_JOB_RESUMED = "Job #{job_id} 재개됨 (재개 지점: {entry_point}). 진행 상황은 자동으로 업데이트됩니다."
MSG_JOB_CANCELLED = "Job #{job_id} 작업이 취소되었습니다."
MSG_JOB_FAILED = "Job #{job_id} 실패: {error}"

# Bulk action messages
MSG_NO_ELIGIBLE_JOBS = "대기중 또는 실패한 작업이 없습니다."
MSG_JOBS_STARTED = "{count}개 작업 시작됨. 진행 상황은 목록에서 자동으로 업데이트됩니다."
MSG_JOBS_DELETED = "{count}개 작업 삭제됨"

# =============================================================================
# Video Processing Constants
# =============================================================================

# Epsilon for extracting last frame (avoid edge issues at exact duration)
FRAME_EXTRACTION_EPSILON = 0.01  # seconds

# =============================================================================
# Admin UI Constants
# =============================================================================

# List display limits
ADMIN_LIST_DISPLAY_MAX = 10
ADMIN_SEARCH_FIELDS_MAX = 3
ADMIN_LIST_FILTER_MAX = 3

# Image preview dimensions
PREVIEW_IMAGE_WIDTH = 320
PREVIEW_IMAGE_HEIGHT = 180
THUMBNAIL_WIDTH = 80
THUMBNAIL_HEIGHT = 45

# =============================================================================
# Game Character Shorts Constants
# =============================================================================

GAME_SEGMENT_COUNT = 5  # Number of scenes in game character shorts
GAME_SEGMENT_DURATION = 4  # seconds per scene
GAME_FADE_DURATION = 0.5  # seconds for fade transition
GAME_TOTAL_DURATION = GAME_SEGMENT_COUNT * GAME_SEGMENT_DURATION  # 20 seconds

# Image processing
GAME_MAX_IMAGE_DIMENSION = 1024  # Max width/height for character image
GAME_MAX_FILE_SIZE_MB = 4  # Max file size for character image upload

# Parallel processing
GAME_MAX_WORKERS = 5  # Max concurrent workers for frame/video generation
