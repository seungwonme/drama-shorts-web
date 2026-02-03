#!/usr/bin/env python3
"""
씬 분리 스크립트

사용법:
    python scripts/split_scenes.py prompts/ep01.json

입력: ep01.json (전체 에피소드, scenes 배열)
출력: ep01/ 폴더 → 1.json, 2.json, 3.json... (씬별 분리)
"""

import json
import sys
from pathlib import Path


def split_scenes(input_file: str) -> None:
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: {input_file} 파일이 존재하지 않습니다.")
        sys.exit(1)

    # JSON 읽기
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # 필수 필드 검증
    if "scenes" not in data:
        print("Error: scenes 필드가 없습니다.")
        sys.exit(1)

    # 출력 폴더 생성 (파일명에서 확장자 제거)
    output_dir = input_path.parent / input_path.stem
    output_dir.mkdir(exist_ok=True)

    # 공통 데이터 추출
    common_data = {
        key: value for key, value in data.items() if key != "scenes"
    }

    # 씬별 분리
    scenes = data["scenes"]
    for i, scene in enumerate(scenes, start=1):
        scene_data = {
            **common_data,
            "scene": scene,  # scenes → scene (단일 객체)
        }

        output_file = output_dir / f"{i}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scene_data, f, ensure_ascii=False, indent=2)

        print(f"생성: {output_file} (씬 {scene.get('scene_number', i)}, {scene.get('duration', '?')}초)")

    print(f"\n완료: {len(scenes)}개 씬 → {output_dir}/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python scripts/split_scenes.py <input.json>")
        print("예시: python scripts/split_scenes.py prompts/ep01.json")
        sys.exit(1)

    split_scenes(sys.argv[1])
