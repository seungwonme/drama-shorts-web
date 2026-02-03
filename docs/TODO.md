# TODO

- [x] 선택적으로 광고 제품 뿐만 아니라 줄거리/대본도 받기
- [x] 영상 글씨 제거
- [x] 실행마다 영상 덮어쓰기 X -> 폴더를 만들어서 영상 저장
- [x] 인물 일관성 유지
- [x] 프롬프트 구조 확립
- [x] 라스트 씬 이미지 정해져 있고 효과음과 함께
- [x] Django Admin
- [x] 제품 이미지 업로드 기능
- [x] 제품 링크 안들어가는 문제 해결
- [x] S3에 에셋 ID별로 구분하여 정리
- [x] assets 폴더에 있는 라스트 씬 이미지, 효과음 업로드 기능
- [x] 단계별로 재작업 기능 추가
  - nano banana: 첫번째 씬의 첫 번째 프레임 다시 제작하기
  - Veo3.1: 첫 번째 씬 다시 제작하기
  - nano banana: 첫번째 씬의 마지막 프레임 다시 제작하기
  - Veo3.1: 두 번째 씬 다시 제작하기
  - last_cta: 이미지, 효과음 다시 업로드하기
  - ffmpeg: 첫 번째 씬 + 두 번째 씬 + last_cta 합치기
  - [ ] 에러 수정
- [ ] ffmpeg 자막 기능 추가
  - 스크립트 기반 영상 뽑아서 스크립트 자막 달기
  - STT -> 구조는 우선 순위로 두되, 프롬프트로 적었던 대본을 LLM에게 검증하는 로직을 추가하여 타임 스탬프 제대로 확인
- [ ] 문제
  - [ ] 인물의 대사가 바뀌는 문제
  - [ ] 상품 이미지 주소를 넣었는데 영상에 안 들어가는 문제
    - [ ] https://d2igltf4n6ib86.cloudfront.net/characters/0be0386c-7c7b-4048-96ca-c9902ec4901f/a2040c83-1cd8-4863-b0ae-659174439ee5.jpeg 영양제
  - [ ] 센서티브 에러 우회 로직 생성하개
    ```sh
    Failed to generate video: {'code': 8, 'message': 'The service is currently experiencing high load and cannot process your request. Please try again later. Operation ID: b3aac92b-794e-419d-a636-64669a59160f.'}
    ```
  - [ ] 한 노드에서 너무 많은 작업을 처리하는 문제

---

## 드라마 형식 쇼츠 개선점

- [x] 핵심 규칙을 템플릿화하여 선택할 수 있도록 제공 -> 기본 형식은 B급 막장 드라마 형식으로 변경
- [ ] 전체적인 프롬프트 고도화
  - [ ] 현재 시퀀스 2초씩 4개 고정되어있는데 화자 단위로 시퀀스를 분리 (시퀀스 설명 세분화) (e.g. 00:00~01:30 "저기요" 캐릭터 A -> 01:30~02:00 "어?" 캐릭터 B ...)
  - [ ] 2번째 씬 생성 프롬프트에 이전 씬에 대한 설명 추가
  - [ ] 캐릭터 성별 및 묘사 디테일 추가
- [ ] 대본 제작과 이미지/영상 제작 프롬프트에 이 쇼츠에 대한 전체적인 맥락을 넣기
- [ ] 시퀀스를 4개에서 3개로 줄인다. (시퀀스 길이 여유 두자)

### 롯데리아: 내일 시연하는 거는 '방구석여포 도발 + 롯데리아형 스토리콘텐츠' 3개만 할 것 같아요!! 요것만 작업해주셔도 충분할 것 같아요!!
외부인이 긁으면 -> 내부 관계자가 증명

### 고재영:
지금부터 NN일 안에 ~하겠습니다.

## 캐릭터 스토리 쇼츠

1. 캐릭터를 맘대로 넣을 수 있어야 한다.
2. 대본을 잘 인식시켜야 한다.

### 핵심:

- 등장 인물
- 여러 소스 (에란겔 배경, 후라이펜, 헬기) -> 스토리에 맞게 등장

## 관련 자료

- https://bbs.pubg.game.daum.net/gaia/do/pubg/competition/read?bbsId=PN001&articleId=4099&objCate1=223
- https://docs.google.com/spreadsheets/d/1W4EJudAGRk7_zkemVIOUtSz1BhwS9jRhD7HBma5_ZeA/edit?gid=431509896#gid=431509896
- https://docs.google.com/spreadsheets/d/1W4EJudAGRk7_zkemVIOUtSz1BhwS9jRhD7HBma5_ZeA/edit?gid=1355792315#gid=1355792315
- https://www.youtube.com/watch?v=k3GnHTPEgJI

---

매주 수요일 컨설팅 -> 3개 영상 필요

bfb96854-9b3b-4b7c-8fc8-74b20ce76ea4:a389576eae2d09aa43071fc21495e5d6

## 인풋
- 배경
- 인물(캐릭터)

## 요구사항
- 스크립트와 일치하는 영상 생성
- 중간에 텍스트를 최대한 제거
- 영상을 분할해서

## 치크 병아리 버전, 플레이어 버전
- 삐약삐약을 제외한 모든 것들은 효과음이 들어가야 한다.
- 프레임을 여러개 -> 영상 20초 이내
영상 스타일 커스터마이징 기능
스크립트 예시


---

## 게임 캐릭터 숏폼 (bbiyack) 통합 작업

### 완료된 작업 (Phase 1-5)

#### Phase 1: 모델 확장 ✅
- `VideoGenerationJob`에 `job_type` (DRAMA/GAME) 추가
- 게임 전용 필드 추가: `character_image`, `game_name`, `user_prompt`, `character_description`, `game_locations_used`
- `GameFrame` 모델 생성 (5씬 각각의 프레임/영상 저장)
- Migration 적용: `0007_add_game_character_support`

#### Phase 2: Status 설정 확장 ✅
- `status_config.py`: `GAME_NODE_ORDER`, `GAME_STATUS_ORDER`, `GAME_PROGRESS_STEPS` 등 추가
- `constants.py`: `GAME_SEGMENT_COUNT=5`, `GAME_SEGMENT_DURATION=4`, `GAME_FADE_DURATION=0.5` 등 추가

#### Phase 3: Generators 패키지 확장 ✅
- `generators/game_state.py`: `GameScriptData`, `GameGeneratorState` TypedDict
- `generators/game_prompts.py`: 게임 스크립트 시스템 프롬프트, 프레임 생성 프롬프트 템플릿
- `generators/nodes/game_planner.py`: Gemini (langchain_google_genai)로 5씬 스크립트 생성
- `generators/nodes/game_assets.py`: Nano Banana로 5개 프레임 병렬 생성
- `generators/nodes/game_video_generator.py`: Veo로 5개 영상 병렬 생성
- `generators/nodes/game_concatenator.py`: FFmpeg xfade로 페이드 트랜지션 병합
- `generators/utils/media.py`: `download_image_as_base64()`, `resize_image_for_api()` 추가

#### Phase 4: Services 확장 ✅
- `game_services.py`: 게임 영상 생성 워크플로우 전체 구현
  - `generate_game_video_sync()`, `generate_game_video_async()`
  - `_save_and_inject_game_urls()`: S3 저장 및 URL 주입
- `services.py`: `generate_video_async()`에서 `job_type`에 따라 분기

#### Phase 5: Admin 확장 ✅
- `GameFrameInline`: 5개 씬 인라인 표시
- `GameFrameAdmin`: 개별 프레임 관리
- `VideoGenerationJobAdmin` 조건부 UI:
  - `get_fieldsets()`: job_type에 따라 다른 필드 표시
  - `get_inlines()`: 게임 타입일 때만 GameFrameInline 표시
  - `job_type_badge()`, `topic_or_game()`, `character_image_preview()` 커스텀 컬럼
  - `_render_game_progress_steps()`: 5단계 진행 표시 (대기→기획→프레임→영상→병합→완료)

### 남은 작업

#### Phase 6: 테스트 ⏳
- [ ] `videos/tests/test_game_services.py` 작성
  - `test_build_game_initial_state()`: 초기 state 빌드 테스트
  - `test_game_node_order()`: 노드 순서 테스트
  - `test_save_and_inject_game_urls()`: S3 저장/URL 주입 테스트
- [ ] Django runserver 실행하여 Admin UI 확인
- [ ] 실제 게임 영상 생성 테스트 (캐릭터 이미지 + 게임명 + 프롬프트)

#### 검증 필요 사항
- [ ] langchain_google_genai 패키지 정상 동작 확인 (google.generativeai → langchain 마이그레이션)
- [ ] 병렬 처리 (ThreadPoolExecutor 5 workers) 성능 확인
- [ ] FFmpeg xfade 트랜지션 품질 확인

### 테스트 명령어

```bash
# Django 검증
cd apps/backend
uv run python manage.py check

# 테스트 실행
uv run pytest videos/tests/test_game_services.py -v

# Admin UI 확인
uv run python manage.py runserver
# http://localhost:8000/admin/ 접속 → 영상 생성 작업 → job_type=GAME으로 생성
```

### 주요 파일 목록

| 파일                                            | 상태 | 설명                               |
| ----------------------------------------------- | ---- | ---------------------------------- |
| `videos/models.py`                              | 수정 | JobType, 게임 필드, GameFrame 모델 |
| `videos/status_config.py`                       | 수정 | GAME_* 상수                        |
| `videos/constants.py`                           | 수정 | GAME_SEGMENT_* 상수                |
| `videos/services.py`                            | 수정 | job_type 분기                      |
| `videos/game_services.py`                       | 신규 | 게임 워크플로우                    |
| `videos/admin.py`                               | 수정 | 조건부 UI, GameFrameAdmin          |
| `generators/game_state.py`                      | 신규 | State TypedDict                    |
| `generators/game_prompts.py`                    | 신규 | 프롬프트 템플릿                    |
| `generators/nodes/game_planner.py`              | 신규 | Gemini 스크립트                    |
| `generators/nodes/game_assets.py`               | 신규 | 프레임 생성                        |
| `generators/nodes/game_video_generator.py`      | 신규 | 영상 생성                          |
| `generators/nodes/game_concatenator.py`         | 신규 | 영상 병합                          |
| `generators/utils/media.py`                     | 수정 | base64 다운로드                    |
| `generators/nodes/__init__.py`                  | 수정 | export 추가                        |
| `migrations/0007_add_game_character_support.py` | 신규 | DB 마이그레이션                    |
