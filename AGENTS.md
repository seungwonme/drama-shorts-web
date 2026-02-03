# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django Admin 기반 웹 애플리케이션으로 YouTube Shorts용 드라마타이즈 광고 영상을 자동 생성합니다. Python 3.13 + Django 6.0.1 스택이며, `videos/generators/` 패키지의 LangGraph 워크플로우를 Django Admin에서 실행합니다. 모든 생성 파일은 S3에 직접 저장됩니다.

## Development Commands

```bash
# 로컬 개발 (Docker - 권장)
cp .env.example .env  # 최초 1회, API 키 설정
./dev.sh              # http://localhost:8000/admin/

# 로컬 개발 (uv 직접 실행)
cd apps/backend
cp ../../.env .env
uv sync
uv run python scripts/init.py  # migrate + collectstatic + superuser
uv run python manage.py runserver

# 프로덕션 실행
./run.sh  # http://localhost/admin/

# Django 명령어 (apps/backend 디렉토리에서)
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py collectstatic --noinput

# 데이터베이스 백업/복원
./infra/backup.sh
./infra/restore.sh /path/to/backup.sqlite3.gz
```

## Architecture

```
drama-shorts-web/
├── apps/backend/                 # Django 애플리케이션
│   ├── config/                   # Django 설정 (settings.py, urls.py, wsgi.py)
│   ├── videos/                   # 영상 생성 앱
│   │   ├── models.py             # Product, ProductImage, VideoGenerationJob, VideoSegment
│   │   ├── admin.py              # Admin UI + 영상 생성/재작업 액션
│   │   ├── services.py           # 노드 순차 실행 + Django 모델 저장
│   │   ├── rework_services.py    # 단계별 재작업 서비스 (첫 프레임, Scene 1/2, CTA, 병합)
│   │   ├── status_config.py      # Status 설정 중앙화 (NODE_ORDER, STATUS_COLORS 등)
│   │   ├── constants.py          # 상수 정의 (타임아웃, 재시도 횟수 등)
│   │   └── generators/           # 영상 생성 패키지 (구 drama-shorts)
│   │       ├── graph.py          # LangGraph 워크플로우 정의
│   │       ├── state.py          # VideoGeneratorState (URL 기반)
│   │       ├── config.py         # API 키, 모델 설정
│   │       ├── constants.py      # 시스템 프롬프트
│   │       ├── exceptions.py     # ModerationError
│   │       ├── nodes/            # plan_script, prepare_first_frame, prepare_cta_frame, generate_scene1, generate_scene2, concatenate_videos
│   │       ├── services/         # gemini_planner.py, fal_client.py
│   │       ├── utils/            # logging.py, video.py, media.py
│   │       └── assets/           # last-cta.png, sound-effect.wav
│   ├── scripts/                  # init.py, create_superuser.py
│   ├── Dockerfile.dev            # 개발 이미지 (시스템 deps: ffmpeg, libgl 등)
│   └── Dockerfile                # 프로덕션 이미지
├── docker-compose.yml            # 프로덕션 (nginx + backend)
├── docker-compose.dev.yml        # 개발
└── infra/                        # AWS 프로비저닝, 백업/복원 스크립트
```

## 핵심 통합 구조

### Django → generators 연동

`videos/services.py`에서 노드 함수를 직접 임포트하여 순차 실행:

```python
# services.py의 핵심 로직
from .generators.nodes import plan_script, prepare_first_frame, generate_scene1, ...

# 노드 순차 실행 (URL 기반)
for node_name in NODE_ORDER:
    result = NODE_FUNCTIONS[node_name](current_state)
    # bytes를 S3에 저장하고 URL을 state에 주입
    current_state = _save_and_inject_urls(job, node_name, result, current_state)
```

**URL 기반 state**: 노드 간 데이터 전달 시 bytes 대신 S3 URL 사용. 노드는 필요시 URL에서 다운로드하여 사용.

### 영상 생성 워크플로우 (7단계)

```
plan_script (Gemini) → prepare_first_frame (fal.ai Nano Banana 첫 프레임)
    → generate_scene1 (fal.ai Veo Scene 1) → prepare_cta_frame (fal.ai Nano Banana CTA 프레임)
    → generate_scene2 (fal.ai Veo Scene 2 interpolation) → concatenate_videos (병합 + 효과음)
    → final_video_bytes
```

각 단계 완료 시 즉시 DB/S3에 저장되어 중간 단계 오류 시에도 이전 결과물이 유지됩니다.

- **Scene 1 (8초)**: 막장 드라마 상황 (image-to-video)
- **Scene 2 (8초)**: 반전 + 제품 등장 (interpolation 모드)
- **Last CTA (2초)**: 정적 이미지 + 효과음

### State 구조 (URL 기반)

```python
class VideoGeneratorState(TypedDict):
    # 입력
    topic: str
    script: str | None
    product_image_url: str | None

    # 프레임 이미지 (S3 URL)
    first_frame_url: str | None        # Scene 1 시작 프레임
    scene1_last_frame_url: str | None  # Scene 1 마지막 프레임
    cta_last_frame_url: str | None     # CTA 마지막 프레임

    # 생성된 세그먼트 (S3 URL)
    segment_videos: list[SegmentVideo]  # [{video_url, index, title}]
    scene1_video_url: str | None
    scene2_video_url: str | None

    # 최종 출력 (S3 URL)
    final_video_url: str | None
```

**노드 내부 동작**: 노드는 URL에서 bytes를 다운로드(`utils/media.py`)하여 처리 후, 임시 bytes 필드(`_first_frame_bytes` 등)로 반환. `services.py`에서 S3 저장 후 URL을 state에 주입.

## Videos 앱 모델

- **Product**: 제품 정보 (`name`, `brand`, `description`)
- **ProductImage**: S3 업로드 이미지 (`is_primary`로 대표 이미지 지정)
- **VideoGenerationJob**: 영상 생성 작업
  - `product` FK 선택 → 대표 이미지 URL 자동 사용 (`effective_product_image_url`)
  - `status`: pending → planning → preparing → generating_s1 → preparing_cta → generating_s2 → concatenating → completed
  - `failed_at_status`: 실패 시점 상태 기록 (재개 시 사용)
- **VideoSegment**: 생성된 세그먼트 영상

## 환경 변수

```bash
# Django
DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS
DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD

# AWS S3 (선택 - 미디어 저장용)
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME

# 영상 생성 API (필수)
GEMINI_API_KEY      # Gemini AI (스크립트 기획)
FAL_KEY             # fal.ai (Nano Banana 이미지 생성, Veo 영상 생성)
```

## Admin 사용법

1. **제품 등록**: Admin → 제품 → 이미지 업로드 (대표 이미지 체크)
2. **영상 생성**: Admin → 영상 생성 작업 → topic 입력, product 선택 → 저장
3. **실행**: 목록에서 선택 → "영상 생성 실행" 액션 클릭
4. **결과**: `final_video` 링크로 S3 영상 다운로드

### 진행도 확인

- **목록 페이지**: 진행 바 컬럼에서 0~100% 진행률 표시 (7단계)
- **상세 페이지**: "진행 상황" 섹션에서 8단계 체크리스트 확인
  - 대기 → 기획 → 첫 프레임 → Scene 1 → CTA 프레임 → Scene 2 → 병합 → 완료
  - 현재 단계는 파란색 강조, 완료된 단계는 녹색 체크
  - 실패 시 에러 메시지 및 실패 지점 표시

### 실패 지점부터 재개 (FAILED 상태에서)

중간 단계에서 실패한 경우, 이전 결과물을 재사용하여 실패 지점부터 재개할 수 있습니다:
- Admin 상세 페이지에서 "실패 지점부터 재개" 버튼 클릭
- `failed_at_status` 필드에 기록된 실패 지점부터 자동 재개
- 이전 단계의 첫 프레임, Scene 1 영상 등이 재사용됨

### 단계별 재작업 (COMPLETED 상태에서)

완료된 Job에서 특정 단계만 다시 실행할 수 있습니다:

| 액션                     | 서비스      | 필요 조건                             | 업데이트 대상                                 |
| ------------------------ | ----------- | ------------------------------------- | --------------------------------------------- |
| 첫 프레임 재생성         | Nano Banana | `script_json`                         | `first_frame`                                 |
| Scene 1 재생성           | Veo         | `first_frame`, segment[0].prompt      | `segments[0].video_file`, `scene1_last_frame` |
| CTA 마지막 프레임 재생성 | Nano Banana | `first_frame`, product_image          | `cta_last_frame`                              |
| Scene 2 재생성           | Veo         | `scene1_last_frame`, `cta_last_frame` | `segments[1].video_file`                      |
| 최종 영상 병합           | FFmpeg      | segment videos                        | `final_video`                                 |

**의존성 주의**: 앞 단계 재작업 시 후속 단계도 재생성 권장 (예: 첫 프레임 변경 → Scene 1, 2, 최종 영상 재생성)

## 배포

main 브랜치 push → GitHub Actions → ghcr.io 이미지 빌드 → EC2 SSH 배포

```bash
# GitHub Secrets 필요
EC2_HOST, EC2_SSH_KEY
```

# 프로젝트 변경 이력

## 2026-01-28: 첫 프레임 및 CTA 프레임 대본 기반 생성

### 변경 파일
- `apps/backend/videos/generators/prompts.py`
- `apps/backend/videos/generators/services/gemini_planner.py`
- `apps/backend/videos/generators/nodes/assets.py`
- `apps/backend/videos/rework_services.py`

### 변경 내용

#### 1. CTA 프레임 기준 변경
- **변경 전**: `scene1_last_frame_url` 사용 (Scene 1 영상의 마지막 프레임)
- **변경 후**: `first_frame_url` 사용 (Scene 1 시작 프레임)
- 이유: 캐릭터 일관성 유지

#### 2. 첫 프레임 생성 시 대본 정보 반영
**변경 전**: 캐릭터 외모와 위치/조명만 사용

**변경 후**: Scene 1의 첫 번째 시퀀스 전체 정보 활용
- `camera`: 카메라 앵글 (예: "[CU on A]", "[TWO-SHOT]")
- `mood`: 씬 분위기 (예: "Icy contempt")
- `A.emotion`, `A.action`, `A.position`: 캐릭터 A의 상태
- `B.emotion`, `B.action`, `B.position`: 캐릭터 B의 상태

#### 3. CTA 프레임 생성 시 대본 정보 반영
**변경 전**: `cta_action` (Scene 2 마지막 시퀀스의 action 필드만)

**변경 후**: Scene 2의 마지막 시퀀스 전체 정보 + scene_setting 활용
- `scene_setting.location`, `scene_setting.lighting`
- `camera`, `mood`
- `A.emotion`, `A.action`, `A.position`
- `B.emotion`, `B.action`, `B.position`

#### 4. 프롬프트 템플릿 개선
`FIRST_FRAME_PROMPT`와 `CTA_FRAME_PROMPT`에 새 필드 추가:
- `{mood}`, `{camera}`
- `{char_a_emotion}`, `{char_a_action}`, `{char_a_position}`
- `{char_b_emotion}`, `{char_b_action}`, `{char_b_position}`

---

## 2026-01-28: 영상 생성 프롬프트 개선

### 변경 파일
- `apps/backend/videos/generators/services/gemini_planner.py`
- `apps/backend/videos/generators/prompts.py`

### 변경 내용

#### 1. CameraSetup Pydantic 스키마 확장
새로운 필드 추가로 AI 이미지/영상 생성 품질 향상:
- `lens`: 렌즈 초점 거리 (기본값: "50mm")
- `depth_of_field`: 피사계 심도 스타일 (기본값: "shallow, cinematic bokeh")
- `texture`: 시각적 질감 노트 (기본값: "natural skin texture, realistic fabric folds")

#### 2. 시스템 프롬프트에 "한 프레임 = 한 감정" 제약 추가
AI가 감정을 애매하게 섞지 않도록 제약:
- BAD: "Longing shifting to cold anger"
- GOOD: "Cold anger"

#### 3. FIRST_FRAME_PROMPT 개선
첫 프레임 이미지 생성 품질 향상:
- 렌즈 정보 추가: "Shot on 50mm lens, medium shot waist-up"
- 피사계 심도 추가: "shallow depth of field with cinematic bokeh"
- 질감 정보 추가: "Natural skin texture, realistic fabric folds, subtle facial details"
- "4K resolution" 제거 (photorealistic으로 충분)

#### 4. PROMPT_TEMPLATE_GUIDE 및 예제 JSON 업데이트
- 새 필드들의 설명 및 예시 추가

#### 5. scenes에서 metadata 제거
- `ScenePrompt`에서 `metadata` 필드 삭제
- `assets.py`에서 `metadata.prompt_name` 참조 제거 → `"Scene {scene_num}"`으로 고정

#### 6. characters 구조 개선 (중복 제거)
**루트 characters** (리스트 형태로 변경):
```json
"characters": [
  { "id": "A", "name": "김순자", "gender": "female", "age": "late 50s", "appearance": "...", "clothing": "...", "voice": "..." },
  { "id": "B", "name": "박지은", ... }
]
```
- 변하지 않는 속성만 포함: id, name, gender, age, appearance, clothing, voice

**scenes 내 characters** (ID 참조 방식):
```json
"characters": [
  { "character_id": "A", "emotion": "Cold contempt", "position": "Left side..." },
  { "character_id": "B", "emotion": "Desperate heartbreak", "position": "Center-right..." }
]
```
- 씬별 동적 속성만 포함: character_id, emotion, position
- `appearance` 중복 제거 → 루트 characters에서 가져옴

#### 7. Timeline action 필드 영어화 + 화자 명시 (Veo 3.1 최적화)
**문제**: Veo 3.1에서 화자 구분이 불명확하면 의도와 다른 인물이 대사를 함

**해결**: action 필드를 영어로 작성하고, 화자를 명확히 표시
- 모든 액션/동작 설명: 영어
- 대사만: 한국어
- 화자 명시 필수: `SOONJA (A) speaks:`, `JIEUN responds:`

**변경 전**:
```json
"action": "[CU on A] 순자가 찻잔을 내려놓으며: '우리 집안 며느리?'"
```

**변경 후**:
```json
"action": "[CU on A] SOONJA (A) places the teacup firmly on the table. Her lips curl into a contemptuous sneer. SOONJA speaks: '우리 집안 며느리? 감히?'"
```

**audio 필드도 화자 명시**:
```json
"audio": "SOONJA: '우리 집안 며느리? 감히?' + teacup ceramic clink + distant thunder"
```

#### 8. Timeline 구조 대폭 개선 - 캐릭터별 상태 분리

**변경 이유**: scenes 내 characters 배열이 씬 전체에 대한 정보만 담아서, 각 시퀀스(2초)마다 캐릭터 상태가 어떻게 변하는지 표현 불가

**변경 사항**:
1. `scenes.characters` 배열 **삭제**
2. `timeline[].action`, `timeline[].audio` 필드 **삭제**
3. `timeline[].camera`, `timeline[].sfx` 필드 **추가**
4. `timeline[].A`, `timeline[].B` 객체 추가 (각 캐릭터의 상태)

**새 TimelineEvent 구조**:
```json
{
  "sequence": 1,
  "timestamp": "00:00-00:02",
  "camera": "[CU on A]",
  "mood": "Icy contempt",
  "sfx": "teacup ceramic clink + thunder",
  "A": {
    "action": "places teacup on table, lips curl into sneer",
    "dialogue": "우리 집안 며느리? 감히?",
    "emotion": "Cold contempt",
    "position": "left side, standing tall"
  },
  "B": {
    "action": "watches in stunned silence",
    "dialogue": "",
    "emotion": "Shocked fear",
    "position": "center-right, kneeling"
  }
}
```

**장점**:
- 각 2초 시퀀스마다 캐릭터별 행동/대사/감정/위치를 독립적으로 관리
- Veo 3.1 화자 혼동 문제 해결 (대사가 캐릭터별로 명확히 분리)
- 감정 변화를 시퀀스별로 세밀하게 표현 가능

---

## 2026-02-03: 코드 리팩토링 - 중복 제거 및 구조 개선

### 신규 파일
- `apps/backend/videos/status_config.py` - Status 설정 중앙화
- `apps/backend/videos/constants.py` - 상수 중앙화

### 변경 파일
- `apps/backend/videos/services.py`
- `apps/backend/videos/admin.py`
- `apps/backend/videos/generators/nodes/video_generator.py`
- `apps/backend/videos/generators/services/fal_client.py`

### 변경 내용

#### 1. Status 설정 중앙화 (`status_config.py`)
status 관련 맵핑을 한 곳에서 관리:
```python
from .status_config import (
    NODE_ORDER,           # 노드 실행 순서
    NODE_TO_STATUS,       # 노드 → (status, display_text) 맵핑
    STATUS_ORDER,         # status → 순서 번호
    PROGRESS_PERCENTAGES, # status → 진행률 %
    STATUS_COLORS,        # status → Tailwind CSS 클래스
    IN_PROGRESS_STATUSES, # 진행중 상태 목록
    PROGRESS_STEPS,       # 상세 페이지용 단계 정의
    get_status_color,     # 헬퍼 함수
    get_progress_percent,
    get_status_order,
    get_resume_node,
    is_in_progress,
)
```

#### 2. 상수 중앙화 (`constants.py`)
매직 넘버 제거:
```python
DEFAULT_SEGMENT_DURATION = 8  # seconds
LAST_CTA_DURATION = 2
MAX_MODERATION_RETRIES = 2
FAL_VIDEO_DOWNLOAD_TIMEOUT = 300
FAL_IMAGE_DOWNLOAD_TIMEOUT = 60
MODERATION_KEYWORDS = [...]  # moderation error 감지 키워드
```

#### 3. services.py 중복 제거
`generate_video_sync()`와 `generate_video_with_resume()`의 80% 중복 코드 통합:
```python
def _generate_video(job, start_from: str | None = None):
    """Core video generation logic."""
    ...

def generate_video_sync(job):
    _generate_video(job, start_from=None)

def generate_video_with_resume(job):
    entry_point = get_resume_entry_point(job)
    if entry_point == "plan_script":
        return generate_video_sync(job)
    _generate_video(job, start_from=entry_point)
```

에러 처리 헬퍼 함수 추출:
- `_handle_node_error(job, error_message)`
- `_handle_exception(job, exception)`
- `_mark_completed(job)`

#### 4. video_generator.py retry 로직 통합
`_generate_scene1_with_retry()`와 `_generate_scene2_with_retry()` 통합:
```python
def _generate_with_moderation_retry(
    generate_fn: Callable,
    scene_name: str,
    prompt: str,
    **kwargs,
) -> bytes | None:
    """Scene 1/2 공통 retry 로직"""
```

#### 5. fal_client.py moderation 감지 추출
중복된 moderation error 감지 로직 통합:
```python
def _check_moderation_error(exception: Exception) -> None:
    """moderation 에러면 ModerationError로 변환"""
    error_msg = str(exception).lower()
    if any(keyword in error_msg for keyword in MODERATION_KEYWORDS):
        raise ModerationError(str(exception))
    raise exception
```

#### 6. admin.py 긴 함수 분리
`_render_progress_steps()` (157줄) 분리:
- `_render_error_box()` - 에러 메시지 박스 HTML
- `_render_progress_bar()` - 진행 바 HTML
- `_get_step_style()` - 단계별 스타일 결정
- `_render_step_card()` - 단일 단계 카드 HTML
- `_render_failed_progress_steps()` - 실패 상태 렌더링
- `_render_normal_progress_steps()` - 정상 상태 렌더링

### Architecture 업데이트

```
videos/
├── status_config.py      # [신규] Status 설정 중앙화
├── constants.py          # [신규] 상수 중앙화
├── services.py           # 중복 제거, 헬퍼 함수 추출
├── admin.py              # status 맵핑 import, 함수 분리
└── generators/
    ├── nodes/
    │   └── video_generator.py  # retry 로직 통합
    └── services/
        └── fal_client.py       # moderation 감지 추출
```

---

## 2026-02-03: 비동기 영상 생성 및 재시도 횟수 증가

### 변경 파일
- `apps/backend/videos/services.py`
- `apps/backend/videos/admin.py`
- `apps/backend/videos/constants.py`
- `apps/backend/videos/generators/nodes/video_generator.py`

### 변경 내용

#### 1. 비동기 영상 생성 (`generate_video_async`)
영상 생성 실행 시 즉시 응답하고 백그라운드에서 처리:
```python
def generate_video_async(job_id: int, resume: bool = False):
    """Run video generation in a background thread."""
    import threading
    from django import db

    def _run_in_thread():
        db.connections.close_all()
        # ... 영상 생성 로직 ...
        db.connections.close_all()

    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
```

**효과**:
- 영상 생성 버튼 클릭 시 즉시 페이지 응답
- HTMX polling (3초 간격)으로 상태 변화 실시간 확인
- 새로고침 없이 진행 바, 상태 배지, 현재 단계가 자동 업데이트

#### 2. Moderation 재시도 횟수 5회로 증가
```python
# constants.py
MAX_MODERATION_RETRIES = 5  # 기존 2 → 5
```

**재시도 전략 (progressive sanitization)**:
- attempt 0: 원본 프롬프트
- attempt 1: quick_sanitize_names (regex 기반)
- attempt 2: sanitize_prompt_for_veo (Gemini 기반, 원본에서)
- attempt 3+: sanitize_prompt_for_veo (이전 결과에서 재적용)

#### 3. Admin 액션 비동기화
- `generate_video_action`: 즉시 응답 + 백그라운드 실행
- `resume_video_action`: 즉시 응답 + 백그라운드 실행
- `bulk_generate_video_action`: 여러 작업 동시 시작

---

## 2026-02-03: 코드 품질 개선

### 변경 파일
- `apps/backend/config/settings.py`
- `apps/backend/videos/services.py`
- `apps/backend/videos/admin.py`
- `apps/backend/videos/constants.py`
- `apps/backend/videos/generators/utils/logging.py`
- `apps/backend/videos/generators/nodes/video_generator.py`
- `apps/backend/videos/tests/` (신규)
- `apps/backend/pyproject.toml`

### 변경 내용

#### 1. 환경 변수 로딩 안전화
- 직접 .env 파싱 → `python-dotenv` 라이브러리 사용
- CSRF origin URL 유효성 검증 추가

#### 2. 로깅 구조화
- `config/settings.py`에 Django LOGGING 설정 추가
- `traceback.print_exc()` → `logger.exception()` 교체
- `generators/utils/logging.py`를 Python 표준 logging과 통합

#### 3. 타입 힌트 완성
- `services.py`의 모든 함수에 타입 힌트 추가
- `TYPE_CHECKING`을 사용한 순환 import 방지

#### 4. Admin 액션 중복 제거
- `_execute_rework_action()` 헬퍼 함수 추가
- 5개 재작업 액션의 중복 검증/예외 처리 로직 통합

#### 5. HTMX 뷰 중복 제거
- `_htmx_view()` 헬퍼 함수 추가
- 5개 HTMX 뷰의 동일한 try-except 패턴 통합

#### 6. 하드코딩된 값 상수화
- `TOTAL_STEPS` 상수를 `status_config.py`에서 import하여 사용
- `FRAME_EXTRACTION_EPSILON` 상수 추가
- Admin UI 관련 상수 추가 (PREVIEW_IMAGE_WIDTH 등)

#### 7. 쿼리 최적화
- `_create_video_segments()`를 `bulk_create()` + `transaction.atomic()`으로 개선

#### 8. 에러 메시지 표준화
- `constants.py`에 메시지 템플릿 상수 추가 (MSG_JOB_NOT_RETRIABLE 등)
- Admin 액션에서 메시지 상수 사용

#### 9. 테스트 코드 추가
- `videos/tests/` 디렉토리 생성
- `test_models.py` - 모델 단위 테스트
- `test_status_config.py` - status_config 모듈 테스트
- `test_services.py` - services 모듈 테스트
- `test_constants.py` - constants 모듈 테스트
- `pyproject.toml`에 pytest-django 의존성 추가

#### 10. 문서화 개선
- `_render_progress_steps()` docstring 상세화
- 8단계 진행 시각화 설명 추가

### 테스트 실행 방법
```bash
cd apps/backend
uv sync --extra dev
uv run pytest
```

---

## 2026-02-03: 게임 캐릭터 숏폼 (bbiyack) 통합

### 개요
bbiyack(게임 캐릭터 숏폼 영상 생성기)를 기존 drama-shorts-web에 통합.

**주요 차이점**:
| 항목 | Drama Shorts | Game Character Shorts |
|------|-------------|----------------------|
| 입력 | topic, product | character_image, game_name, user_prompt |
| 씬 구성 | 2씬 (8초×2) + CTA (2초) | 5씬 (4초×5) |
| 총 길이 | ~18초 | ~20초 |
| 전환 효과 | 직접 연결 | 페이드 트랜지션 |
| 병렬 처리 | 순차 실행 | 5씬 병렬 가능 |

### 신규 파일
- `apps/backend/videos/game_services.py` - 게임 영상 생성 워크플로우
- `apps/backend/videos/generators/game_state.py` - GameGeneratorState TypedDict
- `apps/backend/videos/generators/game_prompts.py` - 게임 스크립트 프롬프트 템플릿
- `apps/backend/videos/generators/nodes/game_planner.py` - Gemini 스크립트 생성 (langchain_google_genai)
- `apps/backend/videos/generators/nodes/game_assets.py` - Nano Banana 프레임 생성
- `apps/backend/videos/generators/nodes/game_video_generator.py` - Veo 영상 생성
- `apps/backend/videos/generators/nodes/game_concatenator.py` - FFmpeg 페이드 병합
- `apps/backend/videos/migrations/0007_add_game_character_support.py`

### 변경 파일
- `apps/backend/videos/models.py` - JobType, 게임 필드, GameFrame 모델
- `apps/backend/videos/status_config.py` - GAME_* 상수 (NODE_ORDER, STATUS_ORDER 등)
- `apps/backend/videos/constants.py` - GAME_SEGMENT_* 상수
- `apps/backend/videos/services.py` - job_type 분기 로직
- `apps/backend/videos/admin.py` - 조건부 UI, GameFrameAdmin/Inline
- `apps/backend/videos/generators/utils/media.py` - download_image_as_base64()
- `apps/backend/videos/generators/nodes/__init__.py` - 게임 노드 export

### 변경 내용

#### 1. 모델 확장 (`models.py`)
```python
class VideoGenerationJob(models.Model):
    class JobType(models.TextChoices):
        DRAMA = "drama", "드라마타이즈 광고"
        GAME = "game", "게임 캐릭터 숏폼"

    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.DRAMA)
    character_image = models.ImageField(upload_to="game_characters/", null=True, blank=True)
    game_name = models.CharField(max_length=200, blank=True)
    user_prompt = models.TextField(blank=True)
    character_description = models.TextField(blank=True)
    game_locations_used = models.JSONField(default=list, blank=True)

class GameFrame(models.Model):
    """게임 캐릭터 숏폼의 각 씬 프레임/영상"""
    job = models.ForeignKey(VideoGenerationJob, on_delete=models.CASCADE, related_name="game_frames")
    scene_number = models.PositiveSmallIntegerField()
    shot_type = models.CharField(max_length=50, blank=True)
    game_location = models.CharField(max_length=200, blank=True)
    prompt = models.TextField()
    description_kr = models.TextField(blank=True)
    image_file = models.ImageField(upload_to="game_frames/", null=True, blank=True)
    video_file = models.FileField(upload_to="game_videos/", null=True, blank=True)
```

#### 2. 게임 워크플로우 (`game_services.py`)
```python
GAME_NODE_FUNCTIONS = {
    "plan_game_scripts": plan_game_scripts,      # Gemini 5씬 스크립트
    "generate_game_frames": generate_game_frames, # Nano Banana 5프레임 (병렬)
    "generate_game_videos": generate_game_videos, # Veo 5영상 (병렬)
    "merge_game_videos": merge_game_videos,       # FFmpeg xfade 병합
}

def generate_game_video_async(job_id: int, resume: bool = False):
    """게임 영상 비동기 생성 (스레드)"""
    ...
```

#### 3. Admin UI 조건부 표시
- `get_fieldsets()`: job_type에 따라 드라마/게임 필드 분기
- `get_inlines()`: 게임 타입일 때만 GameFrameInline 표시
- `_render_game_progress_steps()`: 5단계 진행 표시 (대기→기획→프레임→영상→병합→완료)

#### 4. 게임 스크립트 생성 (`game_planner.py`)
langchain_google_genai 사용 (google.generativeai 대신):
```python
from langchain_google_genai import ChatGoogleGenerativeAI

def plan_game_scripts(state: GameGeneratorState) -> dict[str, Any]:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", ...)
    messages = [
        SystemMessage(content=GAME_SCRIPT_SYSTEM_PROMPT),
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            {"type": "text", "text": user_message},
        ]),
    ]
    response = llm.invoke(messages)
    ...
```

#### 5. 병렬 처리 (`game_assets.py`, `game_video_generator.py`)
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=GAME_MAX_WORKERS) as executor:
    futures = {executor.submit(generate_single_frame, ...): i for i, script in enumerate(scripts)}
    for future in concurrent.futures.as_completed(futures):
        ...
```

#### 6. FFmpeg 페이드 병합 (`game_concatenator.py`)
```python
def _merge_videos_with_fade(video_paths: list[str], fade_duration: float = 0.5) -> bytes:
    """xfade로 페이드 트랜지션 병합"""
    filter_parts = []
    for i in range(len(video_paths) - 1):
        filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition=fade:duration={fade_duration}:offset={offset}...")
    ...
```

### Architecture 업데이트

```
videos/
├── models.py             # JobType, GameFrame 추가
├── status_config.py      # GAME_* 상수 추가
├── constants.py          # GAME_SEGMENT_* 상수 추가
├── services.py           # job_type 분기
├── game_services.py      # [신규] 게임 워크플로우
├── admin.py              # 조건부 UI, GameFrameAdmin
└── generators/
    ├── game_state.py     # [신규] GameGeneratorState
    ├── game_prompts.py   # [신규] 게임 프롬프트
    ├── utils/media.py    # download_image_as_base64 추가
    └── nodes/
        ├── game_planner.py         # [신규] Gemini 스크립트
        ├── game_assets.py          # [신규] 프레임 생성
        ├── game_video_generator.py # [신규] 영상 생성
        └── game_concatenator.py    # [신규] 병합
```

### 남은 작업
- [ ] `videos/tests/test_game_services.py` 테스트 코드 작성
- [ ] 실제 게임 영상 생성 테스트
- [ ] 병렬 처리 성능 확인
