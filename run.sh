#!/bin/bash
# 로컬 Docker 실행 스크립트

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

# Docker Compose 실행
docker compose up -d

echo "✓ 실행 완료: http://localhost/admin/"
