"""Prompt sanitizer for Veo API content filter bypass."""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from .gemini_planner import get_planner_llm
from ..utils.logging import log, log_separator


SANITIZE_SYSTEM_PROMPT = """# ROLE
You are a prompt sanitizer that helps video generation prompts pass content filters.

# TASK
Sanitize the given JSON prompt to avoid content filter triggers while preserving the story structure.

# RULES
1. **Real Person Names** → Replace with generic descriptions:
   - "빌게이츠" → "IT 대기업 회장" or "중년의 IT 기업 회장"
   - "Bill Gates" → "a wealthy middle-aged tech mogul"
   - "스티브잡스" → "유명한 IT 기업인"
   - Other celebrity names → Generic role descriptions

2. **Character Descriptions** → Keep ethnicity/appearance but remove real person references:
   - "resembling a famous tech billionaire" → "wealthy tech executive appearance"
   - Keep clothing, hair, age descriptions intact

3. **Sensitive Expressions** → Soften but maintain drama:
   - Keep the story structure and dialogue intact
   - Only change names and obvious real-person references

4. **Preserve**:
   - All dialogue (대사) - keep exactly as is, just replace names in them
   - Story structure and timeline
   - Camera movements and technical directions
   - Emotional beats and mood

5. **Output**: Return ONLY valid JSON with the same structure as input.

# EXAMPLE
Input: {"name": "빌게이츠", "action": "빌게이츠가 화나며: '개발 못하겠어!'"}
Output: {"name": "IT 회장", "action": "IT 회장이 화나며: '개발 못하겠어!'"}
"""


def sanitize_prompt_for_veo(prompt_json: str) -> str:
    """Sanitize a video generation prompt to pass Veo content filters.

    Uses Gemini to:
    1. Replace real person names with generic descriptions
    2. Soften potentially sensitive expressions
    3. Preserve story structure and dialogue

    Args:
        prompt_json: JSON string of the scene prompt

    Returns:
        Sanitized JSON string with same structure
    """
    log_separator("Prompt Sanitization (Gemini)")
    log("Original prompt (first 200 chars):")
    print(prompt_json[:200] + "...")

    llm = get_planner_llm()

    messages = [
        SystemMessage(content=SANITIZE_SYSTEM_PROMPT),
        HumanMessage(content=f"""다음 JSON 프롬프트를 sanitize해주세요. 실제 인물 이름을 일반적인 설명으로 바꾸고, 스토리 구조는 유지하세요.

{prompt_json}

Output ONLY valid JSON (no markdown, no backticks, no explanation)."""),
    ]

    try:
        log("Calling Gemini for sanitization...")
        response = llm.invoke(messages)
        raw_content = response.content

        # Handle content blocks if needed
        if not isinstance(raw_content, str):
            text_parts = []
            try:
                for item in raw_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif hasattr(item, "text"):
                        text_parts.append(str(item.text))
                    elif isinstance(item, str):
                        text_parts.append(item)
            except (TypeError, AttributeError):
                pass
            raw_content = "".join(text_parts) if text_parts else str(raw_content)

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if json_match:
            sanitized_json = json_match.group()
            # Validate JSON
            json.loads(sanitized_json)
            log("Sanitized prompt (first 200 chars):")
            print(sanitized_json[:200] + "...")
            log("Prompt sanitization successful", "SUCCESS")
            return sanitized_json
        else:
            log("No valid JSON found in response, returning original", "WARNING")
            return prompt_json

    except Exception as e:
        log(f"Sanitization failed: {e}, returning original prompt", "WARNING")
        return prompt_json


def quick_sanitize_names(prompt_json: str) -> str:
    """Quick regex-based name sanitization without API call.

    Faster fallback that replaces common real person names.

    Args:
        prompt_json: JSON string of the scene prompt

    Returns:
        Sanitized JSON string
    """
    log("Quick sanitization (regex-based)...")

    # Common real person name replacements
    replacements = {
        # Korean names
        "빌게이츠": "IT 대기업 회장",
        "빌 게이츠": "IT 대기업 회장",
        "스티브잡스": "유명 IT 기업인",
        "스티브 잡스": "유명 IT 기업인",
        "일론머스크": "테크 기업가",
        "일론 머스크": "테크 기업가",
        "제프베조스": "전자상거래 회장",
        "제프 베조스": "전자상거래 회장",
        "마크저커버그": "SNS 기업 회장",
        "마크 저커버그": "SNS 기업 회장",
        # English names
        "Bill Gates": "a wealthy tech mogul",
        "Steve Jobs": "a famous tech innovator",
        "Elon Musk": "a tech entrepreneur",
        "Jeff Bezos": "an e-commerce executive",
        "Mark Zuckerberg": "a social media CEO",
        # Character description patterns
        "resembling a famous tech billionaire": "with a wealthy tech executive appearance",
        "resembling Bill Gates": "with a tech mogul appearance",
        "looks like a tech billionaire": "has a wealthy executive appearance",
    }

    result = prompt_json
    for original, replacement in replacements.items():
        if original in result:
            result = result.replace(original, replacement)
            log(f"Replaced '{original}' → '{replacement}'")

    if result != prompt_json:
        log("Quick sanitization applied changes", "SUCCESS")
    else:
        log("No replacements needed")

    return result
