#!/bin/bash
# SQLite 백업 스크립트
# 사용법: ./backup.sh
# cron 예시: 0 3 * * * /var/www/drama-shorts-web/infra/backup.sh

set -e

# 설정
PROJECT_DIR="/var/www/drama-shorts-web"
BACKUP_DIR="/var/www/backups"
CONTAINER_NAME="drama-shorts-web-backend-1"
RETENTION_DAYS=7

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

# 타임스탬프
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_$TIMESTAMP.sqlite3"

echo "=== SQLite 백업 시작 ==="
echo "시간: $(date)"

# Docker 컨테이너에서 SQLite 백업 (안전한 방식)
docker exec "$CONTAINER_NAME" sqlite3 /app/data/db.sqlite3 ".backup '/app/data/backup.sqlite3'"

# 백업 파일 복사
docker cp "$CONTAINER_NAME:/app/data/backup.sqlite3" "$BACKUP_FILE"

# 컨테이너 내 임시 백업 파일 삭제
docker exec "$CONTAINER_NAME" rm -f /app/data/backup.sqlite3

# 압축
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

echo "✓ 백업 완료: $BACKUP_FILE"
echo "✓ 크기: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"

# S3 업로드 (선택사항 - AWS CLI 필요)
if command -v aws &> /dev/null && [ -n "$AWS_STORAGE_BUCKET_NAME" ]; then
    aws s3 cp "$BACKUP_FILE" "s3://$AWS_STORAGE_BUCKET_NAME/backups/$(basename "$BACKUP_FILE")"
    echo "✓ S3 업로드 완료"
fi

# 오래된 백업 삭제
echo "=== 오래된 백업 정리 (${RETENTION_DAYS}일 이상) ==="
find "$BACKUP_DIR" -name "db_*.sqlite3.gz" -mtime +$RETENTION_DAYS -delete -print

echo "=== 백업 완료 ==="
