#!/bin/bash
# 로컬 개발 환경 실행 스크립트 (hot reload)

set -e

# .env 파일 복사
if [ -f .env ]; then
    cp .env apps/backend/.env
    echo "✓ .env -> apps/backend/.env 복사 완료"
else
    echo "✗ .env 파일이 없습니다. .env.example을 복사하세요:"
    echo "  cp .env.example .env"
    exit 1
fi

# Docker Compose 개발 모드 실행
docker compose -f docker-compose.dev.yml up --build

