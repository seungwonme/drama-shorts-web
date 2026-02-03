"""State definition for game character shorts generation workflow."""

from typing import TypedDict


class GameScriptData(TypedDict):
    """Data for a single game scene script."""

    scene: int
    shot_type: str
    game_location: str
    prompt: str
    action: str
    camera: str
    description_kr: str


class GameGeneratorState(TypedDict):
    """State for the game character shorts generation workflow.

    5개의 4초 씬으로 구성된 20초 숏폼 영상을 생성합니다.
    각 씬은 게임 세계관 내 특정 장소에서 캐릭터가 등장합니다.
    """

    # User input
    character_image_url: str  # 업로드된 캐릭터 이미지 URL
    game_name: str  # 게임 이름 (예: PUBG, 원신)
    user_prompt: str  # 추가 프롬프트 (예: "배틀그라운드 세계관에 빠진 병아리")

    # Planning results (from plan_game_scripts node)
    character_description: str | None  # AI가 분석한 캐릭터 외형 설명
    game_locations_used: list[str]  # 스크립트에 사용된 게임 내 장소 목록
    scripts: list[GameScriptData]  # 5개 씬 스크립트

    # Generated assets (S3 URLs)
    frame_urls: list[str]  # 5개 시작 프레임 이미지 URL
    video_urls: list[str]  # 5개 영상 URL

    # Final output URL (S3 URL)
    final_video_url: str | None

    # Error handling
    error: str | None

    # Status tracking
    status: str
