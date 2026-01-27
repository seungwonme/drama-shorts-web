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
│   │   ├── services.py           # LangGraph 워크플로우 실행 + Django 모델 저장
│   │   ├── rework_services.py    # 단계별 재작업 서비스 (첫 프레임, Scene 1/2, CTA, 병합)
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
| CTA 마지막 프레임 재생성 | Nano Banana | `scene1_last_frame`, product_image    | `cta_last_frame`                              |
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
