"""Status configuration for video generation workflow.

Centralizes all status-related mappings to avoid duplication across modules.
"""

from .models import VideoGenerationJob

# Type alias for convenience
Status = VideoGenerationJob.Status

# =============================================================================
# Node Execution Order
# =============================================================================

NODE_ORDER = [
    "plan_script",
    "prepare_first_frame",
    "generate_scene1",
    "prepare_cta_frame",
    "generate_scene2",
    "concatenate_videos",
]

# =============================================================================
# Node to Status Mapping
# =============================================================================

# Maps node names to (status, display_text) tuples
NODE_TO_STATUS: dict[str, tuple[str, str]] = {
    "plan_script": (Status.PLANNING, "AI 스크립트 기획"),
    "prepare_first_frame": (Status.PREPARING, "첫 프레임 생성"),
    "generate_scene1": (Status.GENERATING_S1, "Scene 1 생성"),
    "prepare_cta_frame": (Status.PREPARING_CTA, "CTA 프레임 생성"),
    "generate_scene2": (Status.GENERATING_S2, "Scene 2 생성"),
    "concatenate_videos": (Status.CONCATENATING, "영상 병합"),
}

# =============================================================================
# Status Order (for progress calculation)
# =============================================================================

# Total steps for progress calculation (7 steps including completed)
TOTAL_STEPS = 7

STATUS_ORDER: dict[str, int] = {
    Status.PENDING: 0,
    Status.PLANNING: 1,
    Status.PREPARING: 2,
    Status.GENERATING_S1: 3,
    Status.PREPARING_CTA: 4,
    Status.GENERATING_S2: 5,
    Status.CONCATENATING: 6,
    Status.COMPLETED: 7,
    Status.FAILED: -1,  # Special case
}

# =============================================================================
# Progress Percentages
# =============================================================================

PROGRESS_PERCENTAGES: dict[str, int] = {
    status: int((order / TOTAL_STEPS) * 100)
    for status, order in STATUS_ORDER.items()
    if order >= 0  # Exclude FAILED
}
PROGRESS_PERCENTAGES[Status.FAILED] = 0  # Failed shows 0%

# =============================================================================
# Status Colors (Tailwind CSS classes)
# =============================================================================

STATUS_COLORS: dict[str, str] = {
    Status.PENDING: "bg-gray-100 text-gray-700",
    Status.PLANNING: "bg-blue-100 text-blue-700",
    Status.PREPARING: "bg-blue-100 text-blue-700",
    Status.GENERATING_S1: "bg-yellow-100 text-yellow-700",
    Status.PREPARING_CTA: "bg-blue-100 text-blue-700",
    Status.GENERATING_S2: "bg-yellow-100 text-yellow-700",
    Status.CONCATENATING: "bg-yellow-100 text-yellow-700",
    Status.COMPLETED: "bg-green-100 text-green-700",
    Status.FAILED: "bg-red-100 text-red-700",
}

# =============================================================================
# In-Progress Statuses (for UI logic)
# =============================================================================

IN_PROGRESS_STATUSES = [
    Status.PLANNING,
    Status.PREPARING,
    Status.GENERATING_S1,
    Status.PREPARING_CTA,
    Status.GENERATING_S2,
    Status.CONCATENATING,
]

# =============================================================================
# Progress Steps for Detail View
# =============================================================================

# (status_key, label, description)
PROGRESS_STEPS = [
    ("pending", "대기", "작업이 대기열에 있습니다"),
    ("planning", "기획", "Gemini AI가 스크립트를 기획합니다"),
    ("preparing", "첫 프레임", "첫 프레임 이미지를 생성합니다"),
    ("generating_s1", "Scene 1", "Veo로 Scene 1 영상을 생성합니다"),
    ("preparing_cta", "CTA 프레임", "제품 CTA 프레임을 생성합니다"),
    ("generating_s2", "Scene 2", "Veo로 Scene 2 영상을 생성합니다"),
    ("concatenating", "병합", "영상을 병합하고 효과음을 추가합니다"),
    ("completed", "완료", "영상 생성이 완료되었습니다"),
]

# =============================================================================
# Resume Mapping
# =============================================================================

# Maps status to the node that should be resumed
STATUS_TO_RESUME_NODE: dict[str, str] = {
    Status.PENDING: "plan_script",
    Status.PLANNING: "plan_script",
    Status.PREPARING: "prepare_first_frame",
    Status.GENERATING_S1: "generate_scene1",
    Status.PREPARING_CTA: "prepare_cta_frame",
    Status.GENERATING_S2: "generate_scene2",
    Status.CONCATENATING: "concatenate_videos",
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_status_color(status: str) -> str:
    """Get Tailwind CSS color class for a status."""
    return STATUS_COLORS.get(status, "bg-gray-100 text-gray-700")


def get_progress_percent(status: str) -> int:
    """Get progress percentage for a status."""
    return PROGRESS_PERCENTAGES.get(status, 0)


def get_status_order(status: str) -> int:
    """Get the order number for a status."""
    return STATUS_ORDER.get(status, 0)


def get_resume_node(status: str) -> str:
    """Get the node name to resume from for a given status."""
    return STATUS_TO_RESUME_NODE.get(status, "plan_script")


def is_in_progress(status: str) -> bool:
    """Check if a status indicates the job is in progress."""
    return status in IN_PROGRESS_STATUSES or status in GAME_IN_PROGRESS_STATUSES


# =============================================================================
# Game Character Workflow Configuration
# =============================================================================

# Node Execution Order for Game Character Shorts
GAME_NODE_ORDER = [
    "plan_game_scripts",
    "generate_game_frames",
    "generate_game_videos",
    "merge_game_videos",
]

# Maps node names to (status, display_text) tuples for Game Character
GAME_NODE_TO_STATUS: dict[str, tuple[str, str]] = {
    "plan_game_scripts": (Status.PLANNING, "AI 스크립트 기획"),
    "generate_game_frames": (Status.GENERATING_FRAMES, "프레임 생성"),
    "generate_game_videos": (Status.GENERATING_VIDEOS, "영상 생성"),
    "merge_game_videos": (Status.MERGING, "영상 병합"),
}

# Total steps for game progress calculation (5 steps including completed)
GAME_TOTAL_STEPS = 5

GAME_STATUS_ORDER: dict[str, int] = {
    Status.PENDING: 0,
    Status.PLANNING: 1,
    Status.GENERATING_FRAMES: 2,
    Status.GENERATING_VIDEOS: 3,
    Status.MERGING: 4,
    Status.COMPLETED: 5,
    Status.FAILED: -1,
}

GAME_PROGRESS_PERCENTAGES: dict[str, int] = {
    status: int((order / GAME_TOTAL_STEPS) * 100)
    for status, order in GAME_STATUS_ORDER.items()
    if order >= 0
}
GAME_PROGRESS_PERCENTAGES[Status.FAILED] = 0

GAME_STATUS_COLORS: dict[str, str] = {
    Status.PENDING: "bg-gray-100 text-gray-700",
    Status.PLANNING: "bg-blue-100 text-blue-700",
    Status.GENERATING_FRAMES: "bg-yellow-100 text-yellow-700",
    Status.GENERATING_VIDEOS: "bg-yellow-100 text-yellow-700",
    Status.MERGING: "bg-yellow-100 text-yellow-700",
    Status.COMPLETED: "bg-green-100 text-green-700",
    Status.FAILED: "bg-red-100 text-red-700",
}

GAME_IN_PROGRESS_STATUSES = [
    Status.PLANNING,
    Status.GENERATING_FRAMES,
    Status.GENERATING_VIDEOS,
    Status.MERGING,
]

# (status_key, label, description)
GAME_PROGRESS_STEPS = [
    ("pending", "대기", "작업이 대기열에 있습니다"),
    ("planning", "기획", "Gemini AI가 5개의 씬 스크립트를 기획합니다"),
    ("generating_frames", "프레임", "Nano Banana로 5개 시작 프레임을 생성합니다"),
    ("generating_videos", "영상", "Veo로 4초짜리 영상 5개를 생성합니다"),
    ("merging", "병합", "페이드 효과로 영상을 병합합니다"),
    ("completed", "완료", "영상 생성이 완료되었습니다"),
]

GAME_STATUS_TO_RESUME_NODE: dict[str, str] = {
    Status.PENDING: "plan_game_scripts",
    Status.PLANNING: "plan_game_scripts",
    Status.GENERATING_FRAMES: "generate_game_frames",
    Status.GENERATING_VIDEOS: "generate_game_videos",
    Status.MERGING: "merge_game_videos",
}


# =============================================================================
# Game Helper Functions
# =============================================================================


def get_game_status_color(status: str) -> str:
    """Get Tailwind CSS color class for a game status."""
    return GAME_STATUS_COLORS.get(status, "bg-gray-100 text-gray-700")


def get_game_progress_percent(status: str) -> int:
    """Get progress percentage for a game status."""
    return GAME_PROGRESS_PERCENTAGES.get(status, 0)


def get_game_status_order(status: str) -> int:
    """Get the order number for a game status."""
    return GAME_STATUS_ORDER.get(status, 0)


def get_game_resume_node(status: str) -> str:
    """Get the node name to resume from for a given game status."""
    return GAME_STATUS_TO_RESUME_NODE.get(status, "plan_game_scripts")
