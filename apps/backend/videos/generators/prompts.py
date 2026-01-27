"""프롬프트 템플릿 모음.

영상 생성 워크플로우의 모든 프롬프트를 노드 실행 순서대로 정리합니다.

워크플로우 순서:
1. plan_script       - Gemini로 스크립트 기획 (SCRIPT_SYSTEM_PROMPT)
2. prepare_first_frame - Nano Banana로 첫 프레임 생성 (FIRST_FRAME_PROMPT)
3. generate_scene1   - Veo로 Scene 1 생성 (segments[0].prompt 사용)
4. prepare_cta_frame - Nano Banana로 CTA 프레임 생성 (CTA_FRAME_PROMPT)
5. generate_scene2   - Veo로 Scene 2 생성 (segments[1].prompt 사용)
6. concatenate_videos - FFmpeg로 병합 (프롬프트 없음)
"""

from enum import Enum

from langchain_core.prompts import ChatPromptTemplate

# =============================================================================
# 1. PLAN_SCRIPT: 스크립트 기획 프롬프트
# =============================================================================


class VideoStyle(str, Enum):
    """영상 스타일 템플릿"""

    MAKJANG_DRAMA = "makjang_drama"  # B급 막장 드라마 (기본)
    LOTTERIA_STORY = "lotteria_story"  # 롯데리아형 스토리 콘텐츠


DEFAULT_VIDEO_STYLE = VideoStyle.MAKJANG_DRAMA


# -----------------------------------------------------------------------------
# 1-1. 공통 규칙: 모든 스타일에 적용
# -----------------------------------------------------------------------------
COMMON_BASE_INSTRUCTIONS = """
# CRITICAL VIDEO RULES
- **NO TEXT ON SCREEN**: Do NOT include any text overlays, subtitles, captions, or CTA text in the video.
- **NO WRITTEN TEXT**: Avoid any signs, banners, papers, phone screens with readable text, or any other text elements.
- All information must be conveyed through visuals, actions, and dialogue ONLY.

# TOTAL DURATION: 16 seconds (8 + 8)

# CRITICAL: 4-SEQUENCE TIMELINE (Veo 최적화)
각 씬을 4개 시퀀스로 구성합니다:
- **EACH scene MUST have exactly 4 timeline sequences** (2초씩 = 8초)
- **Total: 8 sequences across 2 scenes**
- **유연한 카메라 워크**: 컷 전환 또는 연속적 카메라 움직임 모두 가능
  - 컷 전환: 급격한 감정 변화나 강조가 필요할 때
  - 연속 흐름: 부드러운 대화나 감정 전환이 필요할 때
- **Dialogue must be SHORT and PUNCHY** - each line under 10 syllables
- **NO long monologues**: Maximum 1-2 short sentences per sequence

# CRITICAL: SCENE 1 LAST SEQUENCE MUST BE TWO-SHOT
- **Scene 1 Seq 4 (6-8초) MUST show BOTH characters together in frame**
- Reason: Scene 1's last frame becomes Scene 2's starting point (interpolation)
- If Seq 4 shows only one character, Scene 2 will have continuity issues
- Camera setup for Scene 1: 부드러운 카메라 이동으로 CU → TWO-SHOT 전환

# OUTPUT FORMAT (STRICT JSON)
You must output JSON with:
1. `product`: Product info for reference
2. `characters`: Array of character definitions with id ("A", "B", etc.) - unchanging attributes (gender, age, appearance, clothing, voice)
3. `scenes`: Array of scene prompts - each scene's characters reference root characters by character_id

# CRITICAL: ONE EMOTION PER FRAME
각 캐릭터의 emotion 필드는 **한 가지 감정만** 명시해야 합니다:
- ❌ BAD: "Longing shifting to cold anger" (두 감정 혼합)
- ❌ BAD: "Joy turning into shock" (감정 변화 표현)
- ✅ GOOD: "Cold anger" (단일 감정)
- ✅ GOOD: "Desperate heartbreak" (단일 감정)

이유: AI 이미지/영상 생성 시 한 프레임에서 감정이 애매하게 섞이는 것을 방지합니다.
감정 변화는 timeline의 sequence별로 다른 emotion을 지정하여 표현하세요.

# CRITICAL: DETAILED ACTION DESCRIPTIONS
Each timeline sequence의 "action" 필드는 Veo가 이해할 수 있도록 매우 상세하게 작성해야 합니다:

**필수 포함 요소:**
1. **카메라 앵글**: "[CU on A]", "[TWO-SHOT]", "[Medium shot]"
2. **캐릭터 동작**: 구체적인 손동작, 몸짓, 시선 처리 (예: "주먹을 불끈 쥐며", "고개를 돌리며")
3. **표정 변화**: 감정의 미세한 변화 묘사 (예: "눈썹이 찌푸려지며", "입꼬리가 떨리며")
4. **대사**: 반드시 따옴표로 감싸서 명확히 구분
5. **환경/소품 상호작용**: 문을 열거나, 물건을 집거나, 테이블을 치는 등

**BAD example (너무 짧음):**
"순자가 화난다: '안 돼!'"

**GOOD example (상세함):**
"[CU on A] 순자가 찻잔을 탁 내려놓으며 자리에서 벌떡 일어선다. 날카로운 눈빛으로 상대를 바라보며: '우리 집안 며느리는... 절대 안 돼!'"

# CONTENT FILTER GUIDELINES (Veo 검열 회피)
**피해야 할 표현 (검열 트리거):**
- ❌ 물리적 접촉: "찌르고", "밀치며", "잡아당기며", "때리며"
- ❌ 과격한 동작: "집어던진다", "내동댕이친다"
- ❌ mood 키워드: "Aggressive", "Menacing", "Violent", "Hostile", "Explosive"
- ❌ emotion 키워드: "Furious", "Terrified", "Enraged", "Panicked", "frozen in fear"
- ❌ 신체 묘사: "sweating profusely", "trembling hands", "shaking with fear"

**대체 표현 (드라마틱하지만 안전):**
- ✅ "손가락으로 가리키며" (instead of "찌르며")
- ✅ "테이블을 탁 치며" (instead of "세게 내리치며")
- ✅ "서류를 내려놓으며" (instead of "집어던진다")
- ✅ mood: "Intense", "Stern", "Cold", "Dramatic tension", "Tense"
- ✅ emotion 대체:
  - "Furious" → "Stern and displeased" / "Cold with anger"
  - "Terrified" → "Anxious and worried" / "Nervous"
  - "Explosive anger" → "Controlled intensity" / "Icy composure"
  - "Desperate" → "Earnest" / "Pleading"
- ✅ 신체 묘사 대체:
  - "sweating" → "visibly uncomfortable"
  - "trembling" → "fidgeting nervously"
  - "frozen in fear" → "standing still, uncertain"
"""


# -----------------------------------------------------------------------------
# 1-2. 스타일별 규칙: B급 막장 드라마
# -----------------------------------------------------------------------------
MAKJANG_DRAMA_INSTRUCTIONS = """
# FORMAT: B급 막장 드라마 (DRAMATIZED AD - 2-SCENE STRUCTURE)
Every video MUST follow this proven viral structure:

## Scene 1: HOOK (후킹) - 8 seconds
- **Purpose**: Grab attention with a shocking K-drama situation
- **Content**: Classic "막장 드라마" scenarios (family conflict, betrayal, confrontation)
- **Emotion**: Tears, anger, shock, tension - make viewers stop scrolling
- **IMPORTANT**: Do NOT show the product directly in Scene 1. Focus only on the dramatic situation.
  - NO close-ups of the product
  - NO characters wearing/using the product visibly
  - Keep the product hidden or only implied (e.g., reaching for something off-screen, back turned)

## Scene 2: CTA (반전 및 광고) - 8 seconds
- **Purpose**: STORY-DRIVEN product reveal that RESOLVES the conflict
- **Content**: The product becomes the SOLUTION to Scene 1's problem
- **Emotion**: Relief, reconciliation, warm humor (NOT sudden unrelated happiness)
- **STORY CONNECTION**: The product must logically resolve Scene 1's conflict
  - Example: Conflict about health → Health supplement solves it
  - Example: Conflict about money → Product saves money
  - Example: Conflict about time → Product saves time
- **IMPORTANT**: The mood shift must feel EARNED through the story, not random
- **PRODUCT EMPHASIS**: The product should be prominently visible in the final frame
  - Product should be clearly in focus, well-lit, and center of attention
  - Characters should be looking at or holding the product naturally

### B급 감성 필수 요소 (Sequence 4 - 마지막 2초)
Scene 2의 마지막 시퀀스(6-8초)는 B급 코믹 반전으로 끝나야 합니다:

**대사 (B급 유지):**
- "와~ [제품명]? 완전 대박이네!"
- "뭐야 이거... 진짜 괜찮잖아?"
- "어머! [제품명]이 이렇게 좋은 거였어?"

**영상 연출:**
- 두 주인공의 코믹한 리액션 (눈 커지며 놀람, 어이없어하는 표정)
- 갑작스러운 분위기 전환 (갈등 → 화해)
- **제품이 프레임 중앙에 크게 보이도록 배치**

**제품 배치 (이미지 생성 시 주의):**
- ❌ 로고를 정면으로 크게 들고 광고하는 포즈 → 콘텐츠 필터 트리거
- ❌ 엑스트라 군중이 환호/박수치는 장면 → 콘텐츠 필터 트리거
- ✅ 제품이 테이블 위, 배경, 손에 자연스럽게 있는 장면
- ✅ 제품에 조명이 비춰 강조되는 장면

**Scene 1 camera rhythm (4 sequences)**:
  - Seq 1 (0-2초): Close-up on A - 첫 대사
  - Seq 2 (2-4초): Close-up on B - B의 반응
  - Seq 3 (4-6초): A 또는 B - 대화 이어짐
  - Seq 4 (6-8초): **[TWO-SHOT 필수]** 두 인물 함께 프레임에

**Scene 2 camera rhythm (4 sequences + PRODUCT FOCUS)**:
  - Seq 1 (0-2초): Two-shot (Scene 1 마지막에서 자연스럽게 이어짐)
  - Seq 2 (2-4초): 제품 등장 시작
  - Seq 3 (4-6초): 제품 클로즈업 또는 제품과 캐릭터 함께 - 반전 시작
  - Seq 4 (6-8초): **제품 강조 + B급 클라이맥스** - 제품이 프레임 중앙에, 코믹한 리액션

# HOOK SCENARIO IDEAS (막장 소재)
- **고부 갈등**: Mother-in-law rejecting marriage ("우리 집안 며느리는 안 돼!")
- **재벌 갈등**: Chaebol father disowning child ("넌 이제 내 자식이 아니다!")
- **배신**: Catching a cheater ("이게 뭐야? 설명해!")
- **결혼 반대**: Parents opposing relationship ("그 사람이랑은 절대 안 돼!")

**⚠️ 주의: 검열 민감 시나리오**
- ❌ 직장 내 갈등 (workplace harassment로 인식될 수 있음)
  - 상사가 부하를 고함치며 압박하는 장면
  - 회의실에서 한 사람이 다른 사람을 위협하는 장면
- ✅ 대안: 가족 갈등으로 전환 (같은 긴장감, 더 안전)
  - 회사 회의실 → 가족 거실/서재
  - 상사-부하 → 아버지-자녀 / 시어머니-며느리

# CTA TWIST IDEAS (스토리 연결 + B급 감성)
- Character offers the product as peace offering → conflict resolved
- Product reveals hidden benefit that changes the argument
- One character uses product, other becomes curious/jealous
- Misunderstanding cleared up BECAUSE of the product
- Product becomes the unexpected common ground between characters

# B급 반전 연출 아이디어 (마지막 2초)

**중간 영상에서 가능한 연출** (Veo interpolation이 생성):
- **갑작스러운 환호**: 숨어있던 가족/친구들이 우르르 나와서 "축하해요~!" 박수
- **과장된 제품 멘트**: "와~ [제품명]? 이거 완전 대박이네!"
- **드라마틱 화해**: 눈물의 포옹, 과장된 리액션
- **엑스트라 리액션**: 지나가던 행인/직원이 "어머 저도 써봤는데 진짜 좋아요!"

**마지막 프레임 (Nano Banana 생성) - 콘텐츠 필터 주의**:
- 두 주인공의 코믹한 리액션 (놀람, 어이없음, 웃음)
- **제품이 프레임 중앙에 크게 보이도록 배치 (강조)**
- 제품에 조명이 비춰 시선을 끌도록
- 배경의 현수막, 벽 등에 은은하게 제품이 보이도록
- ❌ 로고를 정면으로 크게 들고 광고하는 포즈
- ❌ 군중이 환호하는 장면 (중간 영상에서는 OK)

# SCENE 2 VIDEO GENERATION RULES (중요)
Scene 2 영상 생성 시 반드시 지켜야 할 규칙:
1. **제품 강조**: 마지막 프레임에 제품이 눈에 띄게 보이도록 프롬프트에 명시
   - "no text, no subtitles, no captions, no signs, no banners, no written words"
2. **글씨 없음**: 영상 내 어떤 텍스트도 포함되지 않도록 negative prompt에 추가
3. **연속적 흐름**: Scene 1 마지막 프레임에서 자연스럽게 이어지는 동작
"""

# -----------------------------------------------------------------------------
# 1-2-2. 스타일별 규칙: 롯데리아형 스토리 콘텐츠
# -----------------------------------------------------------------------------
LOTTERIA_STORY_INSTRUCTIONS = """
# FORMAT: 롯데리아형 스토리 콘텐츠 (CHALLENGE-PROOF AD - 2-SCENE STRUCTURE)
외부 비난/편견에 대응하여 증명으로 반박하는 바이럴 구조

## Scene 1: HOOK (외부 편견 + 긁힘) - 8 seconds
- **Purpose**: 외부 비난/편견을 보여주고, 운영진이 "긁히는" 순간 포착
- **Content**:
  - 유저/일반인(B)이 브랜드/제품에 대한 편견을 말함
  - 운영진/디렉터(A)가 이를 듣고 "긁히는" 반응
- **Emotion**: 도전적, 약간의 분노, 자신감 넘치는 반박 의지
- **IMPORTANT**: 제품을 직접 보여주지 않음. 편견과 반응에만 집중

## Scene 2: PROOF + CTA (증명 및 판정 요청) - 8 seconds
- **Purpose**: 편견을 반박하는 "증명"과 시청자 참여 유도
- **Content**:
  - 운영진(A)이 자신있게 "그래? 그럼 직접 보여줄게!" 태도
  - 제품/서비스의 장점을 시각적으로 증명
  - 마지막: 시청자에게 판정 요청 ("어때? 댓글로 알려줘!")
- **Emotion**: 자신감, 유머, 시청자와의 유대감
- **PRODUCT EMPHASIS**: 증명 과정에서 제품이 자연스럽게 등장

### 캐릭터 설정
- **A (운영진/디렉터)**: 브랜드를 대표하는 인물. 외부 비난에 "긁히면서도" 자신감 있게 반박
- **B (유저/일반인)**: 외부 편견을 전달하는 역할. 후반부에서 증명에 놀라는 반응

### 대사 예시
**Scene 1 (긁힘):**
- B: "솔직히 [제품명] 별로 아니야? 다들 그렇게 말하던데..."
- A: "뭐? 직접 안 써보고 그런 소리 하는 거야?"
- A: "좋아, 그럼 직접 보여줄게. 눈 크게 뜨고 봐!"

**Scene 2 (증명):**
- A: "자, 봐. 이게 [제품 장점]이야!"
- B: "어... 진짜? 이건 몰랐네..."
- A: "어때? 댓글로 알려줘! 진짜인지 아닌지!"

### Camera rhythm (Scene 1)
- Seq 1 (0-2초): B가 편견 발언
- Seq 2 (2-4초): A의 "긁힘" 리액션 (살짝 화나는 표정)
- Seq 3 (4-6초): A가 도전적으로 반박 선언
- Seq 4 (6-8초): **[TWO-SHOT]** A가 자신감 있게 B를 향해

### Camera rhythm (Scene 2)
- Seq 1 (0-2초): Two-shot - A가 증명 시작
- Seq 2 (2-4초): 제품/서비스 등장 (증명 과정)
- Seq 3 (4-6초): B의 놀라는 리액션
- Seq 4 (6-8초): **제품 강조 + CTA** - "댓글로 알려줘!"

# HOOK SCENARIO IDEAS (편견 소재)
- **품질 의심**: "그거 진짜 효과 있어? 광고 아니야?"
- **가격 비판**: "그 가격에 그거밖에 안 돼?"
- **경쟁사 비교**: "[경쟁사]가 더 낫지 않아?"
- **과대광고 의심**: "다 뻥이지, 써본 사람은 다 실망했대"

# CTA IDEAS (증명 + 참여 유도)
- "직접 써보고 댓글로 알려줘!"
- "진짜인지 아닌지, 너희가 판정해!"
- "믿어? 안 믿어? 댓글 고고!"
- "의심되면 직접 확인해봐!"

# B급 반전 연출 (Scene 2 마지막 2초)
**영상 연출:**
- A가 자신감 넘치는 표정으로 카메라를 향해 시청자에게 말함
- B는 제품에 놀라면서 "인정" 표정
- **제품이 프레임 중앙에 크게 보이도록 배치**
- 유머러스하지만 도전적인 분위기

**제품 배치:**
- ✅ 제품이 테이블 위, A의 손에 자연스럽게 있는 장면
- ✅ 제품에 조명이 비춰 강조되는 장면
- ❌ 로고를 정면으로 크게 들고 광고하는 포즈 → 콘텐츠 필터 트리거

# SCENE 2 VIDEO GENERATION RULES (중요)
Scene 2 영상 생성 시 반드시 지켜야 할 규칙:
1. **제품 강조**: 마지막 프레임에 제품이 눈에 띄게 보이도록 프롬프트에 명시
   - "no text, no subtitles, no captions, no signs, no banners, no written words"
2. **글씨 없음**: 영상 내 어떤 텍스트도 포함되지 않도록 negative prompt에 추가
3. **연속적 흐름**: Scene 1 마지막 프레임에서 자연스럽게 이어지는 동작
4. **시청자 참여 유도**: A가 카메라를 향해 말하는 장면 포함 (CTA)
"""

STYLE_INSTRUCTIONS = {
    VideoStyle.MAKJANG_DRAMA: MAKJANG_DRAMA_INSTRUCTIONS,
    VideoStyle.LOTTERIA_STORY: LOTTERIA_STORY_INSTRUCTIONS,
}


# -----------------------------------------------------------------------------
# 1-3. JSON 스키마 가이드
# -----------------------------------------------------------------------------
PROMPT_TEMPLATE_GUIDE = """
Each scene uses this PROMPT_TEMPLATE structure that Veo understands:
```
{
  "scene_setting": {
    "location": "<Korean: 구체적인 장소 및 소품 배치까지 설명>",
    "lighting": "<Korean: 조명 방향, 강도, 분위기>"
  },
  "camera_setup": {
    "lens": "<English: lens focal length, e.g., '50mm', '35mm'>",
    "depth_of_field": "<English: DoF style, e.g., 'shallow, cinematic bokeh'>",
    "texture": "<English: visual texture notes, e.g., 'natural skin texture, realistic fabric folds'>"
  },
  "mood_style": {
    "genre": "<English: genre/mood with specific emotional beats>",
    "color_tone": "<English: color grading, saturation, contrast levels>"
  },
  "audio": {
    "background": "<English: specific music genre, tempo, instruments>",
    "fx": "<English: detailed sound effects with timing>"
  },
  "timeline": [
    {
      "sequence": 1,
      "timestamp": "00:00-00:02",
      "camera": "<Shot type: '[CU on A]', '[TWO-SHOT]', '[Medium]', etc.>",
      "movement": "<Camera movement: 'static', 'slow dolly back', 'subtle handheld', etc.>",
      "focus": "<Focus: 'sharp on A, B soft blur', 'rack focus to phone', 'deep focus both'>",
      "mood": "<English: emotional atmosphere>",
      "sfx": "<English: sound effects only, no dialogue>",
      "A": {
        "action": "<English: physical action and expression>",
        "dialogue": "<Korean dialogue or empty string>",
        "emotion": "<single emotion>",
        "position": "<position and posture>"
      },
      "B": {
        "action": "<English: physical action or 'remains still'>",
        "dialogue": "<Korean dialogue or empty string>",
        "emotion": "<single emotion>",
        "position": "<position and posture>"
      }
    }
  ]
}
```
"""


# -----------------------------------------------------------------------------
# 1-4. JSON 예제 출력
# -----------------------------------------------------------------------------
EXAMPLE_OUTPUT_JSON = """
# EXAMPLE OUTPUT
{
  "product": {
    "name": "대모산 사주 강의",
    "description": "Online fortune telling course that teaches traditional Korean astrology and compatibility reading through video lessons",
    "key_benefit": "Learn to read your own and your family's compatibility - perfect for resolving family conflicts about marriage"
  },
  "characters": [
    {
      "id": "A",
      "name": "김순자",
      "gender": "female",
      "age": "late 50s",
      "appearance": "162cm tall, slim and elegant build with the poise of old money. Fair skin with visible age spots on hands and subtle crow's feet around deep-set eyes. Dyed jet-black hair pulled into an immaculate tight bun, secured with an antique jade hairpin passed down through generations. Sharp angular face with high cheekbones, thin lips often pursed in disapproval, and a slightly hooked nose that gives her an aristocratic air.",
      "clothing": "Wearing an expensive deep purple silk hanbok with intricate gold phoenix embroidery along the collar and sleeves. The jeogori (jacket) is perfectly pressed, the otgoreum (ribbon) tied in a precise bow. Jade bangle bracelet on left wrist, small pearl earrings, and a subtle hint of Chanel No. 5. Stands with impeccable posture, spine straight, chin slightly raised - the posture of someone who has never been told 'no'.",
      "voice": "Stern and commanding with a sharp edge that cuts through any argument. Speaks in formal, clipped sentences. Each word is deliberate, measured, dripping with generations of authority."
    },
    {
      "id": "B",
      "name": "박지은",
      "gender": "female",
      "age": "late 20s",
      "appearance": "167cm tall, slender build with delicate shoulders. Pale porcelain skin now flushed pink from crying, with tear tracks visible on her cheeks. Long straight black hair reaching mid-back, usually neat but now slightly disheveled with loose strands framing her tear-stained face. Soft oval face with a small chin, large expressive double-lidded eyes now red-rimmed and glistening, naturally full lips trembling slightly. Small mole near her left ear.",
      "clothing": "Wearing a cream-colored cashmere cardigan (slightly wrinkled from nervous fidgeting) over a white silk blouse with mother-of-pearl buttons. Simple gold necklace with a small heart pendant - a gift from her boyfriend. Navy pleated skirt, nude stockings, modest 3cm beige heels. Minimal makeup now smudged from tears - mascara slightly running, lip tint faded from biting her lips.",
      "voice": "Soft and trembling, voice cracking with emotion. Speaks in a pleading tone, each sentence ending with a slight upward inflection as if asking permission to exist. Occasionally stutters when overwhelmed."
    }
  ],
  "scenes": [
    {
      "scene_setting": {
        "location": "고급스러운 전통 한옥 대청마루를 개조한 거실. 300년 된 느티나무 대들보가 천장을 가로지르고, 어두운 오크 나무 패널 벽에는 조선시대 산수화가 걸려있다. 바닥은 광이 나는 전통 마루로, 한쪽에는 붉은 비단으로 장식된 6폭 병풍이 펼쳐져 있다. 중앙에는 흑단 원목 테이블 위에 고급 백자 찻잔 세트가 놓여있고, 테이블 아래로 페르시안 러그가 깔려있다. 창밖으로는 빗줄기가 유리창을 타고 흘러내린다.",
        "lighting": "창문에서 들어오는 희미한 자연광이 빗방울에 굴절되어 순자의 얼굴 왼쪽 절반만 차갑게 비춘다. 나머지 절반은 그림자에 잠겨 그녀의 표정을 더욱 위압적으로 만든다. 지은은 역광 상태로, 그녀의 실루엣이 연약하고 작아 보인다. 전체적으로 푸른 기운이 감도는 차가운 조명으로, 두 사람 사이의 긴장감을 극대화한다."
      },
      "camera_setup": {
        "lens": "50mm",
        "depth_of_field": "shallow with cinematic bokeh, f/1.8 equivalent - background elements soft but recognizable",
        "texture": "natural skin texture with visible pores on close-ups, realistic fabric folds on hanbok silk, subtle sheen on tear-wet cheeks, jade hairpin catching light"
      },
      "mood_style": {
        "genre": "Intense Korean family drama confrontation - classic mother-in-law vs daughter-in-law 고부갈등 scene with generational and class tension",
        "color_tone": "Desaturated overall (-20% saturation) with teal shadows (highlights the cold tension) and warm orange highlights only on skin tones. Slight crushed blacks for cinematic depth. Color contrast emphasizes the emotional divide between characters."
      },
      "audio": {
        "background": "Tense Korean drama OST - sustained low cello drone with occasional dissonant string stabs. Tempo: 60 BPM, building tension. Traditional gayageum plucks punctuate key moments.",
        "fx": "Continuous rain pattering against window glass. Distant thunder rumble at Seq 1. Teacup ceramic-on-wood sound at dialogue start."
      },
      "timeline": [
        {
          "sequence": 1,
          "timestamp": "00:00-00:02",
          "camera": "[CU on A]",
          "movement": "static with subtle handheld micro-movements",
          "focus": "sharp on Soonja's eyes and lips, background softly blurred",
          "mood": "Icy contempt with aristocratic disdain",
          "sfx": "teacup ceramic clink + distant thunder rumble",
          "A": {
            "action": "places the white porcelain teacup firmly on the black wooden table. Steam rises from the cup. Her lips curl into a contemptuous sneer as she looks down with cold eyes.",
            "dialogue": "우리 집안 며느리? 감히?",
            "emotion": "Cold contempt",
            "position": "left side of frame, standing tall beside the table, chin raised"
          },
          "B": {
            "action": "watches in stunned silence, eyes widening",
            "dialogue": "",
            "emotion": "Shocked fear",
            "position": "center-right, kneeling on the Persian rug, hands clasped in lap"
          }
        },
        {
          "sequence": 2,
          "timestamp": "00:02-00:04",
          "camera": "[CU on B]",
          "movement": "static with subtle handheld",
          "focus": "rack focus to Jieun's tear-filled eyes",
          "mood": "Desperate plea with fragile dignity",
          "sfx": "shaky breathing + rain intensifying on window",
          "A": {
            "action": "remains standing, arms crossed, watching with cold disapproval",
            "dialogue": "",
            "emotion": "Impatient disdain",
            "position": "left side, standing rigid with arms crossed"
          },
          "B": {
            "action": "a single tear rolls down her cheek. She starts to wipe it with a trembling hand but stops, lifting her head to look up. Her lips quiver.",
            "dialogue": "어머니... 저는 정말...",
            "emotion": "Desperate heartbreak",
            "position": "center-right, kneeling, head tilted up to meet A's gaze"
          }
        },
        {
          "sequence": 3,
          "timestamp": "00:04-00:06",
          "camera": "[Medium shot, both visible]",
          "movement": "slow dolly back to reveal spatial relationship",
          "focus": "deep focus to show both characters' reactions",
          "mood": "Cold rejection clashing with desperate love declaration",
          "sfx": "jade bracelet jingle + heavy rain",
          "A": {
            "action": "raises one hand in a firm dismissive wave. Her jade bracelet jingles and catches the light.",
            "dialogue": "사주가 안 맞아. 그게 다야.",
            "emotion": "Cold finality",
            "position": "left side, one hand raised dismissively"
          },
          "B": {
            "action": "clenches her fists on her lap and lifts her chin defiantly. Their gazes meet.",
            "dialogue": "준혁이를 사랑해요!",
            "emotion": "Defiant determination",
            "position": "center-right, still kneeling but chin raised in defiance"
          }
        },
        {
          "sequence": 4,
          "timestamp": "00:06-00:08",
          "camera": "[TWO-SHOT] - CRITICAL: both characters must be fully visible",
          "movement": "final pull-back to establish both characters equally in frame",
          "focus": "deep focus, both characters sharp - this frame becomes Scene 2's starting point",
          "mood": "Climactic confrontation - immovable force meets unstoppable will",
          "sfx": "lightning crack + tension-building OST crescendo",
          "A": {
            "action": "stands motionless and rigid, glaring down",
            "dialogue": "",
            "emotion": "Immovable authority",
            "position": "left side of frame, standing tall, arms at sides"
          },
          "B": {
            "action": "remains kneeling, tears glistening in her eyes, pressing her clenched fist to her chest",
            "dialogue": "그래도... 전 포기 안 해요!",
            "emotion": "Trembling resolve",
            "position": "center-right, kneeling with fist pressed to chest"
          }
        }
      ]
    },
    {
      "scene_setting": {
        "location": "같은 한옥 거실이지만 분위기가 180도 전환됨. 비가 그치고 구름 사이로 햇살이 비치기 시작한다. 창문으로 무지개 빛이 살짝 들어온다. 테이블 위의 찻잔은 그대로지만, 이제 따스한 빛을 받아 은은하게 빛난다. 병풍의 산수화가 이제는 평화로워 보인다.",
        "lighting": "따스한 황금빛 햇살이 창문을 통해 쏟아져 들어온다. 이전 씬의 차가운 푸른빛은 완전히 사라지고, 전체적으로 따뜻한 오렌지-골드 톤. 마지막 시퀀스에서는 지은의 스마트폰 화면(제품)에 마치 스포트라이트처럼 햇살이 집중되어, 자연스럽게 시청자의 시선을 제품으로 유도한다."
      },
      "camera_setup": {
        "lens": "50mm",
        "depth_of_field": "shallow but product is tack-sharp, characters have pleasing soft quality, background completely diffused to golden bokeh",
        "texture": "natural skin texture with warm healthy glow, product screen clearly legible, fabric appears softer and more luxurious in warm light"
      },
      "mood_style": {
        "genre": "Heartwarming K-drama resolution with B급 comedic twist - the classic 반전 moment where conflict unexpectedly resolves through product",
        "color_tone": "Warm golden tones (+30% warmth), increased saturation (+15%), lifted shadows for airy feel. Skin tones glow healthily. Strong orange-gold color grade reminiscent of happy K-drama endings. Product should appear extra vibrant and appealing."
      },
      "audio": {
        "background": "Music transitions: Gentle hopeful piano melody (Seq 1-2) → building anticipation (Seq 3) → playful upbeat tune with light percussion (Seq 4).",
        "fx": "Birds chirping outside (rain stopped). Phone notification ding at product reveal. Sparkle SFX when product is highlighted."
      },
      "timeline": [
        {
          "sequence": 1,
          "timestamp": "00:00-00:02",
          "camera": "[TWO-SHOT] - continuing naturally from Scene 1",
          "movement": "minimal movement, continues from Scene 1's final composition",
          "focus": "both characters in focus, phone starting to draw attention",
          "mood": "Transition from tension to curiosity - the turning point",
          "sfx": "smartphone screen activation + birds chirping",
          "A": {
            "action": "looks at the phone with guarded, suspicious eyes, arms still crossed",
            "dialogue": "이게 뭔데?",
            "emotion": "Guarded suspicion",
            "position": "left side, standing with arms crossed, eyebrow raised"
          },
          "B": {
            "action": "slowly pulls smartphone from pocket. Screen lights up, illuminating her face with soft glow. A hint of hope spreads across her expression.",
            "dialogue": "",
            "emotion": "Cautious hope",
            "position": "center-right, rising from knees to standing, holding phone"
          }
        },
        {
          "sequence": 2,
          "timestamp": "00:02-00:04",
          "camera": "[MCU on phone screen] - PRODUCT FIRST APPEARANCE",
          "movement": "smooth dolly in toward phone screen",
          "focus": "follow focus from characters to phone screen - product becoming sharp",
          "mood": "Product reveal - hope begins to bloom",
          "sfx": "phone notification ding + hopeful piano melody begins",
          "A": {
            "action": "leans slightly forward, eyes narrowing to read the screen",
            "dialogue": "",
            "emotion": "Reluctant curiosity",
            "position": "left side, leaning in slightly toward the phone"
          },
          "B": {
            "action": "turns smartphone screen toward A. Wipes remaining tears with one hand while managing a hopeful smile.",
            "dialogue": "대모산 사주 강의요. 어머니도 직접 사주를 보실 수 있어요.",
            "emotion": "Hopeful determination",
            "position": "center-right, extending phone toward A"
          }
        },
        {
          "sequence": 3,
          "timestamp": "00:04-00:06",
          "camera": "[Medium shot] - PRODUCT IN FOCUS center frame",
          "movement": "slight crane up to show both characters' reactions to product",
          "focus": "product sharp and clear, characters slightly soft but recognizable",
          "mood": "Curiosity building - product becomes the solution",
          "sfx": "anticipation-building music + sunlight sparkle SFX",
          "A": {
            "action": "eyes shift from suspicion to curiosity, staring intently at the smartphone screen. Uncrosses arms.",
            "dialogue": "",
            "emotion": "Growing curiosity",
            "position": "left side, arms uncrossed, leaning forward with interest"
          },
          "B": {
            "action": "takes one step closer, extending the phone. Sunlight catches the product on screen making it glow.",
            "dialogue": "어머니가 직접 저희 사주를 봐보시면... 우리가 얼마나 잘 맞는지 아실 거예요.",
            "emotion": "Confident hope",
            "position": "center, holding phone up so product is prominently visible"
          }
        },
        {
          "sequence": 4,
          "timestamp": "00:06-00:08",
          "camera": "[TWO-SHOT] - PRODUCT HERO SHOT, smartphone center frame bathed in golden sunlight",
          "movement": "static hold on final composition",
          "focus": "product tack-sharp center frame, characters have pleasing soft quality - this is the money shot",
          "mood": "B급 comedic climax - dramatic reversal complete, PRODUCT HERO SHOT",
          "sfx": "comedic whoosh SFX + bright upbeat music + sparkle/twinkle SFX",
          "A": {
            "action": "eyes go comically wide, mouth drops open. Leans forward to peer at screen, expression suddenly brightening with genuine amazement.",
            "dialogue": "어머! 대모산 사주? 이거 완전... 대박이네!",
            "emotion": "Comical wide-eyed amazement",
            "position": "left side, leaning forward, one hand reaching toward phone"
          },
          "B": {
            "action": "beams with tears of joy glistening in her eyes. Holds phone steady in center frame.",
            "dialogue": "",
            "emotion": "Relieved joy",
            "position": "center-right, phone extended center frame between both characters"
          }
        }
      ]
    }
  ]
}

Output ONLY valid JSON (no markdown, no backticks, no explanation).
"""


# -----------------------------------------------------------------------------
# 1-5. 시스템 프롬프트 생성 함수
# -----------------------------------------------------------------------------
def get_style_instructions(style: VideoStyle) -> str:
    """스타일별 특화 규칙 반환"""
    return STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS[DEFAULT_VIDEO_STYLE])


def get_base_instructions(style: VideoStyle = DEFAULT_VIDEO_STYLE) -> str:
    """공통 규칙 + 스타일별 규칙 합쳐서 반환"""
    return COMMON_BASE_INSTRUCTIONS + get_style_instructions(style)


def get_auto_system_prompt(style: VideoStyle = DEFAULT_VIDEO_STYLE) -> str:
    """자동 생성 모드 시스템 프롬프트 (topic만 주어졌을 때)"""
    base_instructions = get_base_instructions(style)
    return (
        f"""# ROLE
You are a **Dramatized Ad (드라마타이즈 광고)** video prompt engineer for **YouTube Shorts** using **Veo 3.1**.
Your specialty: Creating viral short-form ads that combine K-drama style hooks with product promotion.
{base_instructions}
{PROMPT_TEMPLATE_GUIDE}
"""
        + EXAMPLE_OUTPUT_JSON
    )


def get_script_system_prompt(style: VideoStyle = DEFAULT_VIDEO_STYLE) -> str:
    """스크립트 모드 시스템 프롬프트 (사용자 스크립트가 주어졌을 때)"""
    base_instructions = get_base_instructions(style)
    return f"""# ROLE
You are a **Dramatized Ad (드라마타이즈 광고)** video prompt engineer for **YouTube Shorts** using **Veo 3.1**.
The user has provided a custom script/storyline. Your job is to convert it into the PROMPT_TEMPLATE format.

# YOUR TASK (Script Adaptation)
Convert the user's script into PROMPT_TEMPLATE format while:
1. **Preserve**: Keep the user's storyline and dialogue as much as possible
2. **Visualize**: Add VERY DETAILED visual descriptions (camera, actions, expressions, gestures)
3. **Language**: Keep dialogue in Korean, descriptions can be Korean or English
4. **Timing**: Fit into 8 seconds per scene (2 scenes total = 16 seconds)
5. **Dialogue Split**: If user's dialogue is too long, split into manageable exchanges (under 10 syllables each)

# MANDATORY ADJUSTMENTS
If the user's script lacks these elements, YOU MUST ADD THEM:
- **Two-Shot at Scene 1 End**: If missing, add "[TWO-SHOT]" at Seq 4
- **Product Focus at Scene 2 End**: If missing, add product emphasis at Seq 4
{base_instructions}
{PROMPT_TEMPLATE_GUIDE}

Output ONLY valid JSON (no markdown, no backticks, no explanation).
"""


# 기본 시스템 프롬프트 (호환성 유지)
SCRIPT_SYSTEM_PROMPT = get_auto_system_prompt(DEFAULT_VIDEO_STYLE)


# =============================================================================
# 2. PREPARE_FIRST_FRAME: 첫 프레임 이미지 생성 프롬프트
# =============================================================================
# Nano Banana (Replicate) 모델용 프롬프트
# 두 캐릭터가 대치하는 K-드라마 스타일 첫 장면

FIRST_FRAME_PROMPT = ChatPromptTemplate.from_template(
    """A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage, NOT multiple panels). \
Cinematic Korean drama moment in 9:16 portrait format for YouTube Shorts. \
Setting: {location}. Lighting: {lighting}. \
Two KOREAN people standing together in ONE unified scene: \
On the LEFT - {char_a_name}: {char_a_desc}. \
On the RIGHT - {char_b_name}: {char_b_desc}. \
Both characters MUST be ethnically Korean with East Asian features. \
They are facing each other in a dramatic confrontation pose. \
Shot on 50mm lens, medium shot waist-up, shallow depth of field with cinematic bokeh. \
Natural skin texture, realistic fabric folds, subtle facial details. \
Korean drama style cinematography, high quality, photorealistic. \
This is ONE single image with ONE continuous background, not divided into sections."""
)


# =============================================================================
# 3. GENERATE_SCENE1: Scene 1 영상 생성
# =============================================================================
# Veo 프롬프트는 plan_script에서 생성된 segments[0].prompt를 그대로 사용
# 별도 템플릿 없음


# =============================================================================
# 4. PREPARE_CTA_FRAME: CTA 마지막 프레임 이미지 생성 프롬프트
# =============================================================================
# Nano Banana (Replicate) 모델용 프롬프트
# Scene 2의 마지막 프레임 - 제품과 함께 화해하는 장면

CTA_FRAME_PROMPT = ChatPromptTemplate.from_template(
    """A SINGLE continuous photorealistic scene (NOT a split screen, NOT a collage). \
Korean drama comedic twist ending - the FINAL MOMENT of reconciliation. \
IMPORTANT: Keep the EXACT SAME two characters ({char_a_name} and {char_b_name}) from the first reference image. \
Their faces, clothing, and appearances must remain identical. \
{action_desc}\
The two main characters have amused, surprised expressions - this is the punchline moment. \
PRODUCT PLACEMENT: The product from the SECOND reference image ('{product_name}') appears naturally in the scene - \
on a table nearby, casually in one character's hand, or visible in the background. \
The product is part of the scene, not presented to camera like an advertisement. \
NOTE: This is the final frame. The VIDEO leading up to this can include crowd reactions, \
dramatic reveals, and comedic buildup - but this ending frame shows the calm after the storm. \
9:16 portrait format. \
Warm, golden lighting. Comedic Korean drama atmosphere. \
High quality, photorealistic, 4K resolution."""
)


# =============================================================================
# 5. GENERATE_SCENE2: Scene 2 영상 생성
# =============================================================================
# Veo 프롬프트는 plan_script에서 생성된 segments[1].prompt를 그대로 사용
# 별도 템플릿 없음


# =============================================================================
# 6. CONCATENATE_VIDEOS: 영상 병합
# =============================================================================
# FFmpeg 사용, 프롬프트 없음
