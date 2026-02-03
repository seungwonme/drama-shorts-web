## 질문

```md
너는 광고 및 AI 영상 제작 파이프라인 설계를 위한 영상 분석 AI다.
첨부된 레퍼런스 영상을 분석하여,
동일한 형식의 영상을 자동 생성할 수 있도록
제작 관점의 구조 데이터를 추출하라.

분석 시, 고정된 시간 단위(예: 2초)에 얽매이지 말고,
영상의 의미 단위(shot, beat, scene 변화 기준)로 분해하라.

다음 항목을 반드시 포함하라:

1. 영상 메타 정보
- 총 길이
- 영상 목적 및 사용 채널
- 전반적인 감정 톤 및 브랜드 무드
- 시청자가 느끼도록 설계된 핵심 메시지

2. 구조적 분해 (Shot / Beat 단위)
각 구간마다 다음 정보를 포함:
- 구간 ID
- 시작–종료 시간
- 해당 구간의 역할 (도입 / 강조 / 전환 / 클로징 등)
- 화면 구성 설명 (피사체, 배경, 카메라, 무브먼트)
- 텍스트/자막/로고 사용 여부
- 이전/다음 구간과의 연결 방식

3. 편집 및 연출 규칙
- 컷 길이의 평균 범위
- 템포 변화 패턴
- 반복되는 연출 문법
- 브랜드 로고/카피가 등장하는 규칙

4. 교체 가능한 요소 vs 고정 요소
- 브랜드/제품만 교체 가능한 영역
- 무드를 유지해야 하는 고정 요소
- AI 재생성 시 반드시 유지해야 할 시각 규칙

5. AI 영상 재현 가능성 평가
- 각 구간을 단독 생성 가능한지 여부
- 여러 구간을 묶어서 생성하는 것이 유리한 부분
- 분할 생성 시 리스크 포인트

출력은 구조화된 JSON으로 제공하라.
```

```json
{
  "project_info": {
    "title": "PUBG Weekly Series (PWS) 2026 참여 유도 프로모션",
    "version": "1.0",
    "analyzer": "Gemini_Video_Architect_AI"
  },
  "1_video_meta_info": {
    "total_duration": "96s (1분 36초)",
    "purpose": "이스포츠 대회 일반인 참가 신청 유도 (Recruitment)",
    "target_channel": "YouTube Shorts, TikTok, Instagram Reels (세로형 9:16 최적화)",
    "tone_and_mood": {
      "primary": "Cute & Cinematic (귀여움과 영화적 웅장함의 조화)",
      "secondary": "Humorous (반전 유머)",
      "emotional_arc": "동경(Desire) -> 상상(Fantasy) -> 좌절/현실(Comedy) -> 희망(Hope) -> 행동(Action)"
    },
    "core_message": "누구나(심지어 귀여운 병아리도) 도전할 수 있는 대회"
  },
  "2_structural_breakdown": [
    {
      "id": "SCENE_01",
      "time_range": "00:00 - 00:05",
      "role": "Intro (Hook)",
      "description": "배틀그라운드 3레벨 헬멧을 쓴 귀여운 노란 병아리의 뒷모습. 스마트폰으로 프로게이머들의 화려한 경기 장면을 시청 중.",
      "camera": "Over-the-shoulder (어깨 너머 시점), Close-up",
      "audio": "웅장한 대회 현장음, 해설 소리",
      "text_overlay": "(배그 대회 보는 중)",
      "transition": "Cut to close-up"
    },
    {
      "id": "SCENE_02",
      "time_range": "00:05 - 00:08",
      "role": "Buildup (Emotion)",
      "description": "병아리의 얼굴 클로즈업. 눈을 반짝이며 동경하는 표정. 우승 트로피를 들어올리는 선수들의 모습과 교차 편집.",
      "camera": "Extreme Close-up (얼굴)",
      "audio": "관중 환호성, '우와' 하는 효과음",
      "text_overlay": "우승 트로피 시각적 강조",
      "transition": "Dream blur or Dissolve to fantasy"
    },
    {
      "id": "SCENE_03",
      "time_range": "00:09 - 00:12",
      "role": "Bridge (Imagination)",
      "description": "다른 병아리 친구들과 함께 스마트폰을 보며 상상에 잠김. '내가 대회에 나간다면?'이라는 가정.",
      "camera": "Eye-level shot",
      "audio": "궁금증을 유발하는 효과음",
      "text_overlay": "내가.. 대회에 나간다면?",
      "transition": "Match Cut (현실 -> 게임 속)"
    },
    {
      "id": "SCENE_04",
      "time_range": "00:13 - 00:26",
      "role": "Highlight (Fantasy - Drop)",
      "description": "게임 속 수송기에서 병아리 분대(4마리)가 낙하함. 웅장한 하늘 배경. 귀엽게 날아가는 모습.",
      "camera": "Wide shot (하늘), Tracking shot (낙하)",
      "audio": "비행기 소음, 바람 소리, 웅장한 BGM 시작",
      "text_overlay": "얘들아 모여봐, 이번만 잘하면 우승이야!",
      "transition": "Fast Cut"
    },
    {
      "id": "SCENE_05",
      "time_range": "00:27 - 00:48",
      "role": "Action/Comedy (Fantasy - Looting)",
      "description": "건물 내부 파밍(아이템 획득). 낡은 창고 문을 열고 들어감. 프라이팬 하나를 발견하고 실망함. 수류탄을 던지려다 실수로 자신들에게 떨어뜨림.",
      "camera": "Interior shot, Handheld feeling",
      "audio": "긴장감 넘치는 정적, 금속 소리(프라이팬), 수류탄 핀 뽑는 소리",
      "text_overlay": "이 창고엔 아무것도 없어.. 프라이팬 하나로 뭘 할 수 있냐고!",
      "transition": "Explosion (Black screen)"
    },
    {
      "id": "SCENE_06",
      "time_range": "00:49 - 00:59",
      "role": "Climax (Comedy Twist)",
      "description": "폭발 후 연기 속. 프라이팬이 우연히 수류탄을 쳐내거나 막아냄. 엉겁결에 적을 제압하고 승리함(치킨 먹음).",
      "camera": "Slow motion (폭발 순간)",
      "audio": "이명 소리(삐-), 이후 승리 팡파레",
      "text_overlay": "아니 이걸 우승하네 ㅋㅋ",
      "transition": "Fade out to Reality"
    },
    {
      "id": "SCENE_07",
      "time_range": "01:00 - 01:14",
      "role": "Resolution (Reality)",
      "description": "다시 현실의 거실. 스마트폰 화면 속에서 우승 팀이 트로피를 드는 장면. 병아리들이 부러워하며 화면을 쪼아봄.",
      "camera": "High angle (내려다봄)",
      "audio": "환호성, 차분해진 BGM",
      "text_overlay": "트로피 진짜 영롱하다",
      "transition": "Slide overlay"
    },
    {
      "id": "SCENE_08",
      "time_range": "01:15 - 01:36",
      "role": "Call to Action (CTA)",
      "description": "스마트폰 화면이 '참가 신청 QR코드'로 바뀜. 병아리들이 서로를 쳐다보고(결의), 카메라(시청자)를 쳐다보며 권유함.",
      "camera": "Top view (QR코드), Low angle (병아리들)",
      "audio": "경쾌한 마무리 효과음, 내레이션(없을 경우 자막 강조)",
      "text_overlay": "2026 PWS: PHASE 1 누구나 도전 가능 / 우리 이거.. 나가볼래?",
      "transition": "Loop or End card"
    }
  ],
  "3_editing_rules": {
    "cut_duration": {
      "action": "0.5초 ~ 1.5초 (빠른 호흡)",
      "emotion": "2.0초 ~ 4.0초 (감정 전달)"
    },
    "pacing": "초반(정적) -> 중반(빠른 액션) -> 후반(유머러스한 슬로우) -> 결말(정보 전달 정적)",
    "visual_grammar": "3D 애니메이션 캐릭터(귀여움)와 실사/게임풍 배경(진지함)의 이질적인 조화(Mismatch)를 통해 유머 유발"
  },
  "4_asset_management": {
    "replaceable_elements": [
      "스마트폰 화면 내 영상 (다른 시즌 경기 영상으로 교체 가능)",
      "QR코드 및 대회 일정 텍스트 (다음 시즌 정보로 교체)",
      "배경 음악 (유행하는 밈 사운드로 교체 가능)"
    ],
    "fixed_elements": [
      "메인 캐릭터 (헬멧 쓴 노란 병아리 3D 모델)",
      "PUBG IP 요소 (3레벨 헬멧, 프라이팬, 수송기)",
      "전체적인 스토리 구조 (상상 -> 현실 복귀)"
    ],
    "ai_generation_constraint": "캐릭터의 털 질감(Fur simulation)과 헬멧의 텍스처 일관성을 전 구간 유지해야 함."
  },
  "5_ai_reproducibility": {
    "feasibility_score": "High (높음)",
    "strategy": "Segmented Generation (분할 생성)",
    "notes": "병아리 캐릭터는 LoRA(스타일 학습 모델)를 통해 고정하고, 배경(거실/수송기/창고)만 프롬프트를 변경하여 생성. 전투 씬의 물리 효과(수류탄, 폭발)는 비디오-투-비디오(Video-to-Video) 기술 활용 권장."
  }
}

```

## 응답

```md
좋아, 이 응답 퀄리티 꽤 높고 지금 단계에서 해야 할 건
❌ “다시 만들기”가 아니라
✅ AI 제작 관점으로 재구조화 + 실행 가능한 설계로 진화야.

그래서 내가 제안하는 디벨롭 방향은 3단 업그레이드야.

⸻

🔧 1단계 디벨롭: “분석 결과 → 실행 설계”로 변환

지금 JSON은 기획자/감독 시점에는 완벽한데,
AI 에이전트가 바로 실행하기엔 추상도가 조금 높아.

👉 그래서 각 SCENE에 ‘AI 생성 전략 메타’만 추가하면 바로 쓸 수 있어.

⸻

🔹 SCENE 단위 확장 스키마 (핵심 추가)

각 SCENE에 아래 필드를 추가하자:

"ai_generation_plan": {
  "generation_mode": "single-shot | multi-shot | video-to-video",
  "recommended_duration": "5s",
  "consistency_priority": "character | environment | action",
  "generation_risk": "low | medium | high",
  "fallback_strategy": "still+camera_motion | split_scene | replace_with_cutaway"
}


⸻

✍️ 예시 – SCENE_04 (Drop 씬)

"ai_generation_plan": {
  "generation_mode": "single-shot",
  "recommended_duration": "4~6s",
  "consistency_priority": "character",
  "generation_risk": "medium",
  "fallback_strategy": "split into sky-only + character close-up"
}

👉 이 한 덩어리 덕분에
Sora / Veo / Runway 중 뭐를 써도 판단이 자동화됨

⸻

🧠 2단계 디벨롭: “제작 전략 에이전트” 명문화

이제 이 프로젝트엔 Production Strategy Agent가 꼭 필요해.

⸻

🎯 Production Strategy Agent Prompt (개선 버전)

너는 AI 영상 제작 파이프라인을 설계하는 수석 디렉터다.

입력으로 주어진 레퍼런스 영상 분석 JSON을 기반으로,
각 SCENE에 대해 다음을 결정하라:

1. 생성 방식
- 단일 샷 생성
- 복수 샷 분할 생성
- Video-to-Video 변환

2. 생성 단위 최적화
- 권장 생성 길이 (초)
- 프롬프트 난이도
- 캐릭터/배경 중 우선 고정 요소

3. 리스크 관리
- 실패 가능성이 높은 구간
- 해당 구간의 대체 연출 제안

출력은 기존 SCENE 구조를 유지한 채
`ai_generation_plan` 필드를 추가하는 JSON으로 제공하라.

👉 이 에이전트의 역할은 “2초냐 5초냐”를 정하는 게 아니라
👉 “어디를 쪼개야 하는가”를 판단하는 것

⸻

🧩 3단계 디벨롭: 실제 ‘자동화’에 필요한 에이전트 분리

지금 구조를 기준으로 하면
에이전트는 최소 5개가 가장 안정적이야.

⸻

🤖 권장 에이전트 아키텍처

1. Video Analysis Agent
   → 지금 받은 JSON 생성

2. Production Strategy Agent
   → SCENE별 생성 방식 결정

3. Scene Prompt Generator Agent
   → Sora / Veo용 씬별 프롬프트 생성

4. Video Assembly Agent
   → 컷 병합, 트랜지션, 텍스트 오버레이

5. QA / Consistency Agent
   → 병아리 캐릭터 외형, 톤, 템포 검수


⸻

🎬 Scene Prompt Generator – 실제 중요한 포인트

SCENE_05 같은 리스크 높은 씬은
👉 하나의 프롬프트로 만들지 말고
👉 의도적으로 “연출을 단순화”

예:
	•	❌ “수류탄 던지고 실수하고 폭발하고”
	•	✅ “수류탄 핀 소리 → 병아리 표정 → 컷 → 폭발 결과”

이걸 전략 에이전트가 자동으로 판단하게 만드는 게 핵심이야.

⸻

⚠️ 지금 JSON에서 아주 좋은 포인트 (칭찬)

이건 꼭 유지해야 해 👇

✅ Emotional Arc 명시

→ AI 영상에서 제일 망하기 쉬운 부분인데 잘 잡힘

✅ replaceable vs fixed 요소 분리

→ 클라이언트가 “시즌마다 재활용”하기 딱 좋음

✅ LoRA 고정 전략

→ 병아리 캐릭터 하나로 프랜차이즈화 가능

⸻

🧠 내가 보기엔 이 프로젝트의 진짜 정체성

이건 그냥

“영상 자동 생성”

이 아니라

**“IP 기반 스토리 포맷 자동화 엔진”**야

병아리 → 다른 캐릭터
PUBG → 다른 게임
PWS → 다른 대회

전부 갈아 끼울 수 있음.

⸻

다음으로 같이 할 수 있는 것 (추천 순서)

1️⃣ SCENE별 ai_generation_plan 전부 채워보기 (같이)
2️⃣ Sora vs Veo 기준 씬 분할 가이드
3️⃣ 실제 프롬프트 예시 1~2개 씬 완성
4️⃣ 클라이언트 제안서용 ‘이 시스템이 왜 강한지’ 한 장 요약

👉 다음으로 뭐부터 같이 파볼까?
개인적으로는 **SCENE_04~06 (가장 위험 + 핵심)**부터 잡는 게 제일 좋다 🔥
```
