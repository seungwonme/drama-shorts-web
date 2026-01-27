#!/bin/bash
# 로컬 개발 환경 실행 스크립트 (hot reload)

set -e

# 플래그 파싱
CLEAN=false
RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -r|--restart)
            RESTART=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./dev.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --clean    이미지 삭제 후 새로 빌드"
            echo "  -r, --restart  컨테이너 재시작"
            echo "  -h, --help     도움말"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

# .env 파일 복사
if [ -f .env ]; then
    cp .env apps/backend/.env
    echo "✓ .env -> apps/backend/.env 복사 완료"
else
    echo "✗ .env 파일이 없습니다. .env.example을 복사하세요:"
    echo "  cp .env.example .env"
    exit 1
fi

# 이미지 삭제 후 새로 빌드
if [ "$CLEAN" = true ]; then
    echo "✓ 기존 컨테이너 및 이미지 삭제 중..."
    docker compose -f docker-compose.dev.yml down --rmi local -v 2>/dev/null || true
    echo "✓ 삭제 완료. 새로 빌드합니다."
fi

# 컨테이너 재시작
if [ "$RESTART" = true ]; then
    echo "✓ 컨테이너 재시작 중..."
    docker compose -f docker-compose.dev.yml restart
    docker compose -f docker-compose.dev.yml logs -f
    exit 0
fi

# Docker Compose 개발 모드 실행
docker compose -f docker-compose.dev.yml up --build

