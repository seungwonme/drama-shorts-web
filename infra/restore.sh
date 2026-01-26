#!/bin/bash
# SQLite 복원 스크립트
# 사용법: ./restore.sh <backup_file.sqlite3.gz>

set -e

if [ -z "$1" ]; then
    echo "사용법: $0 <backup_file.sqlite3.gz>"
    echo ""
    echo "사용 가능한 백업 파일:"
    ls -lh /var/www/backups/db_*.sqlite3.gz 2>/dev/null || echo "  (백업 파일 없음)"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="drama-shorts-web-backend-1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ 파일이 존재하지 않습니다: $BACKUP_FILE"
    exit 1
fi

echo "=== SQLite 복원 ==="
echo "백업 파일: $BACKUP_FILE"
echo ""
read -p "⚠ 현재 데이터가 덮어씌워집니다. 계속하시겠습니까? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "취소됨"
    exit 0
fi

# 임시 디렉토리에 압축 해제
TEMP_FILE="/tmp/restore_db.sqlite3"
gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"

# 컨테이너 중지
echo "컨테이너 중지..."
docker stop "$CONTAINER_NAME"

# 백업 파일 복사
docker cp "$TEMP_FILE" "$CONTAINER_NAME:/app/data/db.sqlite3"

# 컨테이너 재시작
echo "컨테이너 재시작..."
docker start "$CONTAINER_NAME"

# 임시 파일 삭제
rm -f "$TEMP_FILE"

echo "✓ 복원 완료"
