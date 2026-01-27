# 프롬프트 구조 분석

각 단계별 이미지/영상 생성에 사용되는 프롬프트 구조를 정리합니다.

---

## 영상 스타일 템플릿

영상 스타일을 선택하여 다른 톤의 광고 영상을 생성할 수 있습니다.

### 사용 가능한 스타일

| 스타일 | 설명 | 상태 |
|--------|------|------|
| `makjang_drama` | B급 막장 드라마 | **기본값** |
| `romantic_comedy` | 로맨틱 코미디 | 예정 |
| `emotional` | 감동/힐링 | 예정 |

### 스타일 선택 방법

1. **Admin에서**: 영상 생성 작업 → "영상 스타일" 드롭다운에서 선택
2. **코드에서**:
   ```python
   from videos.generators.constants import VideoStyle, get_auto_system_prompt

   # 스타일별 시스템 프롬프트 가져오기
   prompt = get_auto_system_prompt(VideoStyle.MAKJANG_DRAMA)
   ```

### 새 스타일 추가 방법

1. `videos/generators/constants.py`에서:
   - `VideoStyle` enum에 새 스타일 추가
   - `STYLE_INSTRUCTIONS` dict에 스타일별 규칙 추가

2. `videos/models.py`에서:
   - `VideoStyleChoice`에 새 선택지 추가

3. 마이그레이션 실행:
   ```bash
   cd apps/backend
   uv run python manage.py makemigrations
   uv run python manage.py migrate
   ```

---

## 워크플로우 개요

```
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Gemini     │ →  │ 2. Nano Banana  │ →  │ 3. Veo 3.1      │
│ 스크립트 기획 │    │ 첫 프레임 생성  │    │ Scene 1 생성    │
└───────────────┘    └─────────────────┘    └─────────────────┘
                                                     ↓
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 6. FFmpeg     │ ←  │ 5. Veo 3.1      │ ←  │ 4. Nano Banana  │
│ 영상 병합     │    │ Scene 2 생성    │    │ CTA 마지막 프레임│
└───────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 1. Gemini (스크립트 기획)

### 파일 위치
- `videos/generators/constants.py` - 시스템 프롬프트
- `videos/generators/services/gemini_planner.py` - API 호출

### 시스템 프롬프트 모드

| 모드          | 상수명                       | 사용 시점                |
| ------------- | ---------------------------- | ------------------------ |
| 자동 생성     | `KOREAN_DRAMA_SYSTEM_PROMPT` | script 없이 topic만 제공 |
| 스크립트 기반 | `SCRIPT_MODE_SYSTEM_PROMPT`  | 사용자 script 제공 시    |

### 핵심 규칙 (BASE_INSTRUCTIONS)

1. **NO TEXT ON SCREEN** - 자막, 캡션, CTA 텍스트 금지
2. **2-SCENE 구조** (총 16초)
   - Scene 1 (8초): HOOK - 막장 드라마 상황, 제품 직접 노출 금지
   - Scene 2 (8초): CTA - 반전 + 제품 강조
3. **4-SEQUENCE TIMELINE** - 각 씬마다 2초씩 4개 시퀀스
4. **Scene 1 마지막 필수**: TWO-SHOT (두 캐릭터 함께)
5. **콘텐츠 필터 회피** - 폭력적 표현 대체

### 출력 JSON 구조

```json
{
  "product": {
    "name": "제품명",
    "description": "설명",
    "key_benefit": "핵심 이점"
  },
  "characters": {
    "character_a": {
      "name": "한글 이름",
      "description": "영어 상세 외모 (나이, 체형, 피부색, 머리, 옷)"
    },
    "character_b": { ... }
  },
  "scenes": [
    { ...PROMPT_TEMPLATE Scene 1... },
    { ...PROMPT_TEMPLATE Scene 2... }
  ]
}
```

### PROMPT_TEMPLATE 구조 (각 Scene)

```json
{
  "metadata": {
    "prompt_name": "씬 설명 (한글)",
    "base_style": "영상 스타일",
    "aspect_ratio": "9:16"
  },
  "scene_setting": {
    "location": "장소 + 소품 (한글)",
    "lighting": "조명 설명"
  },
  "camera_setup": {
    "shot": "샷 타입 (영어, 앵글 포함)",
    "movement": "dolly, pan, tilt, cuts",
    "focus": "포커싱, 심도",
    "key_shots": "중요 샷"
  },
  "mood_style": {
    "genre": "장르/분위기 (영어)",
    "color_tone": "컬러 그레이딩"
  },
  "audio": {
    "background": "배경음악 (장르, 템포)",
    "fx": "효과음 (한글)"
  },
  "characters": [
    {
      "name": "이름",
      "appearance": "외모 (영어)",
      "emotion": "감정 (영어)",
      "position": "프레임 위치"
    }
  ],
  "timeline": [
    {
      "sequence": 1,
      "timestamp": "00:00-00:02",
      "action": "한글 상세 (카메라앵글 + 동작 + 표정 + 대사)",
      "mood": "감정 분위기 (영어)",
      "audio": "대사 + 효과음"
    }
  ]
}
```

---

## 2. Nano Banana: 첫 프레임 생성

### 파일 위치
- `videos/generators/services/gemini_planner.py` → `generate_first_frame()`

### 프롬프트 템플릿

```
A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage, NOT multiple panels).
Cinematic Korean drama moment in 9:16 portrait format for YouTube Shorts.
Setting: {location}. Lighting: {lighting}.
Two KOREAN people standing together in ONE unified scene:
On the LEFT - {char_a_name}: {char_a_desc}.
On the RIGHT - {char_b_name}: {char_b_desc}.
Both characters MUST be ethnically Korean with East Asian features.
They are facing each other in a dramatic confrontation pose.
Korean drama style cinematography, high quality, photorealistic, 4K resolution.
This is ONE single image with ONE continuous background, not divided into sections.
```

### 입력 파라미터

| 파라미터      | 출처                                 | 설명          |
| ------------- | ------------------------------------ | ------------- |
| `location`    | `scenes[0].scene_setting.location`   | 장소 설명     |
| `lighting`    | `scenes[0].scene_setting.lighting`   | 조명 설명     |
| `char_a_name` | `characters.character_a.name`        | 캐릭터 A 이름 |
| `char_a_desc` | `characters.character_a.description` | 캐릭터 A 외모 |
| `char_b_name` | `characters.character_b.name`        | 캐릭터 B 이름 |
| `char_b_desc` | `characters.character_b.description` | 캐릭터 B 외모 |

### API 호출

```python
replicate.run(
    "google/nano-banana",
    input={
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "output_format": "png",
    },
)
```

### 출력
- PNG 이미지 (bytes)
- Veo Scene 1의 시작 프레임으로 사용

---

## 3. Veo 3.1: Scene 1 생성

### 파일 위치
- `videos/generators/services/replicate_client.py` → `create_and_download_video()`

### 프롬프트
- Gemini에서 생성한 `scenes[0]` PROMPT_TEMPLATE JSON을 **문자열로 직렬화**

```python
prompt = json.dumps(scene, ensure_ascii=False, indent=2)
```

### API 호출

```python
replicate.run(
    "google/veo-3.1-fast",
    input={
        "prompt": prompt,           # PROMPT_TEMPLATE JSON 문자열
        "duration": 8,              # 8초
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": True,
        "image": first_frame_image, # Nano Banana에서 생성한 첫 프레임
    },
)
```

### 생성 모드
- **Image-to-video**: 첫 프레임에서 시작하여 영상 생성

### 출력
- MP4 영상 (bytes) - 8초
- **마지막 프레임 추출** → Scene 2 시작점으로 사용

---

## 4. Nano Banana: CTA 마지막 프레임 생성

### 파일 위치
- `videos/generators/services/gemini_planner.py` → `generate_cta_last_frame()`

### 프롬프트 템플릿

```
A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage).
Korean drama comedic twist ending - the FINAL MOMENT of reconciliation.
IMPORTANT: Keep the EXACT SAME two characters ({char_a_name} and {char_b_name}) from the first reference image.
Their faces, clothing, and appearances must remain identical.
{action_desc}
The two main characters have amused, surprised expressions - this is the punchline moment.
PRODUCT PLACEMENT: The product from the SECOND reference image ('{product_name}') appears naturally in the scene -
on a table nearby, casually in one character's hand, or visible in the background.
The product is part of the scene, not presented to camera like an advertisement.
NOTE: This is the final frame. The VIDEO leading up to this can include crowd reactions,
dramatic reveals, and comedic buildup - but this ending frame shows the calm after the storm.
9:16 portrait format.
Warm, golden lighting. Comedic Korean drama atmosphere.
High quality, photorealistic, 4K resolution.
```

### 입력 파라미터

| 파라미터            | 출처                            | 설명                |
| ------------------- | ------------------------------- | ------------------- |
| `scene1_last_frame` | Veo Scene 1 마지막 프레임 추출  | 참고 이미지 1       |
| `product_image_url` | S3 제품 이미지                  | 참고 이미지 2       |
| `char_a_name`       | `characters.character_a.name`   | 캐릭터 A 이름       |
| `char_b_name`       | `characters.character_b.name`   | 캐릭터 B 이름       |
| `product_name`      | `product.name`                  | 제품명              |
| `action_desc`       | `scenes[1].timeline[-1].action` | Scene 2 마지막 액션 |

### API 호출

```python
# 참고 이미지 2개 업로드 후
replicate.run(
    "google/nano-banana",
    input={
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "output_format": "png",
        "image_input": [scene1_frame_url, product_replicate_url],  # 참고 이미지 2개
    },
)
```

### 핵심 특징
- **2개 참고 이미지 사용**: Scene 1 마지막 + 제품 이미지
- **캐릭터 일관성 유지**: 동일한 외모, 옷
- **제품 자연스럽게 배치**: 광고처럼 보이지 않게

### 출력
- PNG 이미지 (bytes)
- Veo Scene 2의 마지막 프레임 (interpolation 목표)

---

## 5. Veo 3.1: Scene 2 생성

### 파일 위치
- `videos/generators/services/replicate_client.py` → `create_and_download_video()`

### 프롬프트
- Gemini에서 생성한 `scenes[1]` PROMPT_TEMPLATE JSON을 **문자열로 직렬화**

### API 호출

```python
replicate.run(
    "google/veo-3.1-fast",
    input={
        "prompt": prompt,              # PROMPT_TEMPLATE JSON 문자열
        "duration": 8,                 # 8초
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": True,
        "image": scene1_last_frame,    # Scene 1 마지막 프레임
        "last_frame": cta_last_frame,  # Nano Banana CTA 마지막 프레임
    },
)
```

### 생성 모드
- **Interpolation (보간)**: 시작 프레임 → 끝 프레임 사이를 자연스럽게 연결

### 출력
- MP4 영상 (bytes) - 8초

---

## 6. FFmpeg: 영상 병합

### 파일 위치
- `videos/generators/nodes/concatenate_videos.py`

### 입력
- `segment_videos`: Scene 1 + Scene 2 영상 바이트
- `last_cta_image_url` (선택): 마지막 정적 이미지
- `sound_effect_url` (선택): 효과음

### 출력
- 최종 완성 영상 (16초)

---

## 프롬프트 파라미터 요약

| 단계 | AI          | 입력                                                     | 출력                               |
| ---- | ----------- | -------------------------------------------------------- | ---------------------------------- |
| 1    | Gemini      | topic, script?, product_brand?, product_description?     | JSON (product, characters, scenes) |
| 2    | Nano Banana | characters, scene_setting                                | first_frame_image                  |
| 3    | Veo         | JSON prompt, first_frame                                 | scene1_video + scene1_last_frame   |
| 4    | Nano Banana | scene1_last_frame, product_image, characters, cta_action | cta_last_frame_image               |
| 5    | Veo         | JSON prompt, scene1_last_frame, cta_last_frame           | scene2_video                       |
| 6    | FFmpeg      | segment_videos                                           | final_video                        |

---

## 설정값

**파일**: `videos/generators/config.py`

```python
PLANNER_MODEL = "gemini-3-flash-preview"
REPLICATE_VIDEO_MODEL = "google/veo-3.1-fast"
REPLICATE_IMAGE_MODEL = "google/nano-banana"
RESOLUTION = "720p"
ASPECT_RATIO = "9:16"
```
