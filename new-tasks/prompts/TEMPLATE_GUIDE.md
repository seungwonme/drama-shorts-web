# JSON 프롬프트 템플릿 가이드

## 기존 대비 개선점

| 문제점 | 해결 |
|--------|------|
| 불필요한 필드가 많음 | Veo 영상 생성에 필요한 필드만 유지 |
| 캐릭터 구분 어려움 | `characters` 섹션에 visual 설명 분리, 각 씬에서 ID로 참조 |
| dialogue가 영상에 영향 | `audio_reference`로 분리 (후편집 참고용) |
| 위치 설명 중복 | `locations` 섹션으로 재사용 가능하게 분리 |

---

## 템플릿 구조

```
{
  episode         // 에피소드 메타정보
  characters      // 캐릭터 정의 (재사용)
  locations       // 배경 정의 (재사용)
  scenes[]        // 씬별 상세 정보
}
```

---

## 1. episode

```json
{
  "episode": {
    "number": 1,
    "title": "에피소드 제목",
    "total_duration": 18
  }
}
```

---

## 2. characters

캐릭터를 **ID로 정의**하고, 각 씬에서 참조합니다.

```json
{
  "characters": {
    "GAMER": {
      "role": "주인공",
      "visual": "Young Asian male, early 20s, black long-sleeve shirt...",
      "reference": "assets/게이머.png"
    },
    "GPT": {
      "role": "로봇 조력자",
      "visual": "PUBG character with level 3 military helmet...",
      "reference": "assets/헬멧남.png"
    }
  }
}
```

**visual 작성 규칙**:
- 영어로 작성 (Veo 입력용)
- 식별 가능한 외형 특징 포함
- 의상, 액세서리 명시
- 짧고 구체적으로

---

## 3. locations

배경을 **ID로 정의**하고 재사용합니다.

```json
{
  "locations": {
    "GAMER_ROOM": "Dark gaming room with glowing monitor...",
    "PUBG_CITY": "Post-apocalyptic urban environment...",
    "PUBG_FIELD": "Open grassy field with scattered trees..."
  }
}
```

---

## 4. scenes[]

각 씬의 상세 정보입니다.

```json
{
  "number": 1,
  "name": "훅",
  "duration": 5,
  "timestamp": "00:00-00:05",

  "setting": {
    "location_id": "GAMER_ROOM",
    "location_desc": "추가 설명 (이 씬 특화)",
    "lighting": "조명 설명",
    "time_of_day": "night"
  },

  "camera": {
    "shot_type": "medium shot",
    "angle": "behind character",
    "movement": "slow push",
    "focus": "character silhouette"
  },

  "cast": ["GAMER", "GPT"],

  "action": {
    "description": "씬 전체 액션 요약 (영어)",
    "GAMER": {
      "start_position": "seated in chair",
      "action": "gets pulled into monitor",
      "emotion": "shocked"
    },
    "GPT": {
      "start_position": "standing nearby",
      "action": "watches calmly",
      "emotion": "neutral"
    }
  },

  "mood": "surreal, dramatic",

  "audio_reference": {
    "sfx": "digital whoosh (후편집용)",
    "dialogue_ko": "한글 대사 (후편집용)"
  }
}
```

---

## 필드별 설명

### setting

| 필드 | 용도 | 예시 |
|------|------|------|
| location_id | locations 참조 | "PUBG_CITY" |
| location_desc | 이 씬 특화 배경 설명 | "폐허가 된 거리" |
| lighting | 조명 분위기 | "Harsh daylight", "Dramatic shadows" |
| time_of_day | 시간대 | "day", "night", "dusk" |

### camera

| 필드 | 용도 | 예시 |
|------|------|------|
| shot_type | 샷 종류 | "wide shot", "medium shot", "close-up", "extreme close-up" |
| angle | 카메라 각도 | "front", "behind", "low angle", "high angle", "over shoulder" |
| movement | 카메라 움직임 | "static", "slow pan", "tracking", "dolly in" |
| focus | 초점 대상 | "character face", "both characters" |

### action

| 필드 | 용도 |
|------|------|
| description | 씬 전체 액션 요약 (Veo 프롬프트 생성 시 사용) |
| {CHARACTER_ID} | 캐릭터별 세부 액션 |

### 캐릭터별 action

| 필드 | 용도 |
|------|------|
| start_position | 시작 위치/자세 |
| action | 수행하는 동작 |
| emotion | 감정 상태 |

### audio_reference (후편집용)

| 필드 | 용도 |
|------|------|
| sfx | 효과음 참고 |
| dialogue_ko | 한글 대사 참고 (영상에 포함 안됨) |

---

## Veo 프롬프트 변환 예시

JSON의 씬 1을 Veo 프롬프트로 변환:

**입력 (JSON)**:
```json
{
  "setting": { "location_desc": "Dark gaming room illuminated only by bright monitor light" },
  "camera": { "shot_type": "medium shot", "angle": "behind and slightly to the right" },
  "cast": ["GAMER"],
  "action": { "description": "GAMER sits in front of glowing monitor. Suddenly a swirling vortex..." }
}
```

**출력 (Veo 프롬프트)**:
```
Young Asian male wearing black long-sleeve shirt, dark blue jeans, and gaming headset sits in a dark gaming room illuminated only by bright monitor light. Medium shot from behind and slightly to the right. A swirling vortex of light bursts from the screen, pulling him toward the monitor. His body stretches as he gets sucked into the digital world. Surreal, dramatic, sci-fi atmosphere.
```

**변환 규칙**:
1. `characters[cast[0]].visual` + `setting.location_desc` + `camera` + `action.description`
2. `mood` 추가
3. "no text on screen" 항상 추가

---

## 체크리스트

JSON 작성 시 확인:

- [ ] 모든 캐릭터가 `characters`에 정의되어 있는가?
- [ ] `cast`에 있는 캐릭터가 `action`에도 있는가?
- [ ] `location_id`가 `locations`에 정의되어 있는가?
- [ ] `visual` 설명이 영어로 작성되어 있는가?
- [ ] `dialogue_ko`가 `audio_reference` 안에 있는가? (영상에 포함 안됨 확인)
