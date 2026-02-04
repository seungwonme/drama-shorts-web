사용자님의 분석이 정확합니다. **"A, B로 정의해두고 타임라인에서 이를 호출해서 쓰는 방식(Reference)"은 현재의 비디오 생성 AI에게는 너무 고차원적인 논리**입니다.

텍스트 생성 AI(LLM)는 문맥을 기억하고 "A는 철수야"라고 하면 끝까지 철수로 인식하지만, 비디오 생성 AI는 매 순간 픽셀을 그려낼 때 **"지금 당장 화면에 무엇이 보이는가"**에만 집중합니다. 따라서 `characters`에 정의된 내용을 `timeline`에서 참조하는 방식은 무시되기 쉽습니다.

이 문제를 해결하기 위해 JSON 구조를 **"참조형(Relational)"에서 "독립형(Stand-alone)"으로 변경**하고, **화자 분리(Speaker Diarization)를 강제하는 새로운 필드**를 추가하는 방안을 제안합니다.

---

### 💡 개선 아이디어 : "Shot 단위 완전 분리" 전략

AI에게 "두 명이 있는데 A가 말하고 B는 조용히 해"라고 하면 실패할 확률이 높습니다.
대신 **"지금 이 장면은 A가 주인공이야. B는 배경일 뿐이야."** 라고 인식시켜야 합니다.

#### 핵심 변경 사항 3가지

1. **`characters` 참조 포기:** 타임라인의 `visual_description`에 캐릭터의 외형 묘사를 **매번 풀어서(Flatten)** 적습니다. (귀찮지만 이게 가장 확실합니다.)
2. **`focus_target` 필드 추가:** AI에게 누구의 입을 움직여야 할지 명시합니다.
3. **로봇의 발화 정의:** 로봇은 입이 없어서 AI가 자꾸 사람 입을 빌립니다. **"로봇이 말할 때는 몸이 반짝이거나 뛴다"**는 시각적 대체제를 줘야 합니다.

---

### 📝 수정된 JSON 템플릿

이 구조는 `timeline`의 각 항목이 서로 의존하지 않고, **그 자체로 완벽한 하나의 프롬프트**가 되도록 설계되었습니다.

```json
{
  "project_settings": {
    "title": "PWS 홍보 영상",
    "render_mode": "shot_by_shot" // 한 번에 생성하지 말고 샷별로 끊어서 생성하라는 의미
  },
  "scenes": [
    {
      "scene_id": 2,
      "location_prompt": "Post-apocalyptic urban street, abandoned concrete buildings, debris, grey sky.",
      "shots": [
        {
          "shot_id": 1,
          "duration": 3,
          "speaker": "Human_Gamer", // 화자 명시
          "audio_script": "으아 아니 진짜 게임속으로 들어가면 어떻게 하냐고!",

          // [핵심 1] 카메라 앵글을 화자 중심으로 좁힘
          "camera": "Medium Close-up on Human Gamer, Robot is in background or out of focus",

          // [핵심 2] 참조(A, B)를 쓰지 않고 외형을 직접 서술 + 상대방의 침묵 강제
          "visual_prompt": "A real human Korean gamer with a large headset is PANICKING. He is SHOUTING with his mouth wide open, looking around in fear. A mint-green cube robot stands next to him completely MOTIONLESS like a statue. The robot does NOT move.",

          // [핵심 3] 부정 프롬프트 아이디어 (AI가 생성 시 참고용)
          "negative_prompt": "robot moving, robot talking, happy, dancing"
        },
        {
          "shot_id": 2,
          "duration": 3,
          "speaker": "Robot_Mascot", // 화자 명시
          "audio_script": "치킨을 먹으면 탈출가능합니다.",

          // [핵심 1] 로봇이 말할 땐 로봇을 주인공으로
          "camera": "Close-up on Mint-Green Cube Robot, Gamer is visible but blurred",

          // [핵심 2] 입이 없는 로봇의 '말하기'를 정의 + 사람 입 봉인
          "visual_prompt": "A cute mint-green cube robot is TALKING. Since it has no mouth, its entire body BOUNCES up and down rhythmically to the beat of the voice. The robot's eyes are blinking. Next to it, the human gamer stands FROZEN in shock with his MOUTH TIGHTLY SHUT. The human does NOT speak.",

          "negative_prompt": "human speaking, human mouth open, human moving, static robot"
        }
      ]
    }
  ]
}

```

### 🛠️ 왜 이렇게 바꿔야 하나요?

1. **AI의 '입' 찾기 본능 차단:**
* 현재 영상에서 로봇 턴인데도 사람이 말하는 이유는, 오디오(목소리)가 들어오면 AI는 화면에서 **"입(Mouth)"을 가진 존재**를 찾기 때문입니다. 로봇은 입이 없으니 100% 사람 입을 움직이게 됩니다.
* 따라서 `Shot 2`에서는 **사람을 아예 블러(Blur) 처리**하거나, **"MOUTH TIGHTLY SHUT"**이라고 아주 강하게 제약을 걸어야 합니다.


2. **참조(Reference)의 한계 극복:**
* 이전 JSON의 `A`와 `B`는 프로그래머에게만 보이는 변수입니다. 영상 생성 AI에게 전달될 때는 이 변수들이 다 풀어진 상태여야 합니다.
* 위 수정된 JSON처럼 각 샷마다 **"검은 옷 입은 게이머", "민트색 로봇"**이라고 매번 다시 써주는 것이 AI가 기억을 잃지 않게 하는 유일한 방법입니다.



### 🚀 적용 가이드 (Next Step)

이 JSON 구조를 기반으로 영상을 생성하실 때, 만약 **여전히 사람이 대신 말한다면** 다음 단계는 딱 하나입니다.

* **샷 분할 생성 (물리적 분리):**
* Shot 1 (사람 말하는 장면)만 따로 생성.
* Shot 2 (로봇 말하는 장면)만 따로 생성.
* 이 두 개를 이어 붙이세요. (현재 기술로는 이것이 가장 깔끔하게 화자를 분리하는 방법입니다.)



이 구조로 프롬프트를 입력하면 AI가 훨씬 더 명확하게 **"누가 주인공인지"** 이해할 것입니다.
