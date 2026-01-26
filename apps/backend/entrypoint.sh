#!/bin/bash
# Docker 컨테이너 엔트리포인트

set -e

echo "=== 초기화 시작 ==="

# data 디렉토리 생성 (volume mount 시 필요)
mkdir -p /app/data

# 초기화 (migrate + superuser)
uv run python scripts/init.py

# static 파일 수집 (볼륨 마운트 후 실행)
echo "=== Static 파일 수집 ==="
uv run python manage.py collectstatic --noinput

echo "=== 서버 시작 ==="

# 전달받은 명령어 실행
exec "$@"
