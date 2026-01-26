# Drama Shorts Web

Django Admin 기반 웹 애플리케이션

## 프로젝트 구조

```
drama-shorts-web/
├── apps/
│   └── backend/
│       ├── config/
│       ├── scripts/
│       ├── data/              # SQLite DB (gitignore)
│       ├── manage.py
│       ├── pyproject.toml
│       ├── Dockerfile
│       ├── Dockerfile.dev
│       └── entrypoint.sh
├── infra/
│   ├── nginx.conf
│   ├── setup_ec2.sh
│   ├── provision_aws.sh
│   ├── backup.sh
│   └── restore.sh
├── .github/
│   └── workflows/
│       └── deploy.yml
├── .env.example
├── docker-compose.yml
├── docker-compose.dev.yml
├── run.sh
├── dev.sh
└── README.md
```

## 환경 변수 설정

`.env.example`을 `.env`로 복사 후 환경에 맞게 수정합니다.

```sh
cp .env.example .env
```

### Django 설정

| 변수 | 설명 | 로컬 | 프로덕션 |
|------|------|------|----------|
| `DJANGO_SECRET_KEY` | 보안 키 | 아무 값 | `openssl rand -base64 50` |
| `DJANGO_DEBUG` | 디버그 모드 | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | 허용 호스트 | `localhost,127.0.0.1` | `IP,도메인` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSRF 출처 | `http://localhost:8000` | `https://도메인` |

**SECRET_KEY 생성:**
```sh
# 방법 1: Django
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 방법 2: OpenSSL
openssl rand -base64 50
```

### 관리자 계정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DJANGO_SUPERUSER_USERNAME` | 관리자 ID | `admin` |
| `DJANGO_SUPERUSER_EMAIL` | 관리자 이메일 | `admin@example.com` |
| `DJANGO_SUPERUSER_PASSWORD` | 관리자 비밀번호 | 변경 필수 |

### AWS S3 (선택사항)

미디어 파일을 S3에 저장하려면 설정합니다. 비워두면 로컬 파일 시스템 사용.

| 변수 | 설명 | 획득 방법 |
|------|------|-----------|
| `AWS_ACCESS_KEY_ID` | IAM 액세스 키 | `provision_aws.sh` 출력 |
| `AWS_SECRET_ACCESS_KEY` | IAM 시크릿 키 | `provision_aws.sh` 출력 |
| `AWS_STORAGE_BUCKET_NAME` | S3 버킷명 | `provision_aws.sh` 출력 |
| `AWS_S3_REGION_NAME` | 리전 | `ap-northeast-2` (서울) |

### 환경별 예시

**로컬 개발:**
```env
DJANGO_SECRET_KEY=dev-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin1234
# AWS 변수는 비워둠
```

**프로덕션:**
```env
DJANGO_SECRET_KEY=Abc123...긴랜덤문자열...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=13.125.xxx.xxx,example.com
DJANGO_CSRF_TRUSTED_ORIGINS=http://13.125.xxx.xxx,https://example.com
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=강력한비밀번호123!
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=drama-shorts-media-123456789
AWS_S3_REGION_NAME=ap-northeast-2
```

## 로컬 개발

### uv 직접 실행
```sh
cp .env.example .env
# .env 수정 후

cd apps/backend
cp ../../.env .env
uv sync
uv run python scripts/init.py  # migrate + superuser
uv run python manage.py runserver
```

### Docker (hot reload)
```sh
cp .env.example .env
# .env 수정 후

./dev.sh
```

http://localhost:8000/admin/ 접속

## 프로덕션 실행

```sh
cp .env.example .env
# .env 수정 후

./run.sh
```

http://localhost/admin/ 접속

## AWS 배포 (EC2 + S3 + Cloudflare)

### 1. AWS 인프라 자동 프로비저닝
```sh
cd infra
./provision_aws.sh
```

생성되는 리소스:
- EC2 인스턴스 (t3.micro)
- Elastic IP
- S3 버킷 (미디어 저장용)
- IAM 사용자 (S3 접근용)
- 보안 그룹 (SSH, HTTP)
- SSH 키 페어

### 2. Cloudflare 설정
- DNS에 A 레코드 추가 (Elastic IP)
- Proxy 상태: Proxied (주황색 구름)
- SSL/TLS: Full

### 3. EC2 접속 및 Docker 설치
```sh
ssh -i drama-shorts-key.pem ubuntu@<elastic-ip>

curl -sSL https://raw.githubusercontent.com/<your-repo>/main/infra/setup_ec2.sh | bash

# 로그아웃 후 재접속 (docker 그룹 적용)
exit
ssh -i drama-shorts-key.pem ubuntu@<elastic-ip>
```

### 4. 프로젝트 배포
```sh
cd /var/www/drama-shorts-web
git clone https://github.com/<your-repo>.git .

cp .env.example .env
nano .env  # provision_aws.sh 출력값으로 수정

./run.sh
```

### 5. 접속
https://drama.buuup.kr/admin/

## CI/CD (GitHub Actions)

main 브랜치에 push 시 자동 배포됩니다.

### GitHub Secrets 설정
Repository Settings > Secrets and variables > Actions에 추가:

| Secret | 설명 |
|--------|------|
| `EC2_HOST` | EC2 Elastic IP 주소 |
| `EC2_SSH_KEY` | SSH 프라이빗 키 (drama-shorts-key.pem 내용) |

## 백업 & 복원

### 수동 백업
```sh
./infra/backup.sh
```

### 자동 백업 (cron)
```sh
# 매일 새벽 3시 백업
crontab -e
0 3 * * * /var/www/drama-shorts-web/infra/backup.sh >> /var/log/backup.log 2>&1
```

### 복원
```sh
./infra/restore.sh /var/www/backups/db_20240101_030000.sqlite3.gz
```
