# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django Admin 기반 웹 애플리케이션 (Drama Shorts Admin). Python 3.13 + Django 6.0.1 스택으로 구성되며, Docker 기반 개발/배포 환경을 제공합니다.

## Development Commands

### 로컬 개발 (Docker - 권장)
```bash
cp .env.example .env  # 최초 1회
./dev.sh              # http://localhost:8000/admin/
```

### 로컬 개발 (uv 직접 실행)
```bash
cd apps/backend
cp ../../.env .env
uv sync
uv run python scripts/init.py  # migrate + superuser 생성
uv run python manage.py runserver
```

### 프로덕션 실행
```bash
./run.sh  # http://localhost/admin/
```

### Django 명령어
```bash
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py collectstatic --noinput
```

### 데이터베이스 백업/복원
```bash
./infra/backup.sh
./infra/restore.sh /path/to/backup.sqlite3.gz
```

## Architecture

```
drama-shorts-web/
├── apps/backend/           # Django 애플리케이션
│   ├── config/             # Django 설정 (settings.py, urls.py, wsgi.py)
│   ├── scripts/            # 초기화 스크립트 (init.py, create_superuser.py)
│   ├── data/               # SQLite DB (gitignore)
│   ├── Dockerfile          # 프로덕션 이미지
│   └── Dockerfile.dev      # 개발 이미지
├── infra/                  # 인프라 스크립트
│   ├── nginx.conf          # Nginx 설정
│   ├── provision_aws.sh    # AWS 인프라 프로비저닝
│   ├── setup_ec2.sh        # EC2 초기 설정
│   ├── backup.sh           # DB 백업
│   └── restore.sh          # DB 복원
├── docker-compose.yml      # 프로덕션 (nginx + backend)
├── docker-compose.dev.yml  # 개발 (hot reload)
├── dev.sh                  # 개발 환경 실행
└── run.sh                  # 프로덕션 환경 실행
```

### 주요 기술 스택
- **Backend**: Django 6.0.1, Gunicorn
- **Admin UI**: Django Jazzmin (enhanced admin)
- **Storage**: Local filesystem (dev) / AWS S3 (prod, optional)
- **Database**: SQLite
- **Web Server**: Nginx (reverse proxy)
- **CI/CD**: GitHub Actions → EC2 배포

### 환경 변수
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`
- AWS S3 (선택): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`

### 배포 플로우
1. main 브랜치 push
2. GitHub Actions: Docker 이미지 빌드 → ghcr.io push
3. SSH로 EC2 접속 → docker compose up -d
