#!/bin/bash
# Docker 컨테이너 엔트리포인트

set -e

echo "=== 초기화 시작 ==="

# data 디렉토리 생성 (volume mount 시 필요)
mkdir -p /app/data

# 초기화 (migrate + superuser)
uv run python scripts/init.py

echo "=== 서버 시작 ==="

# 전달받은 명령어 실행
exec "$@"
