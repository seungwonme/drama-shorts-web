# Drama Shorts Web

Django Admin 기반 웹 애플리케이션

## 설치 절차

### 1. Python 버전 설정
```sh
uv python pin 3.13.11
```

### 2. 프로젝트 초기화
```sh
uv init
```

### 3. 패키지 설치
```sh
# 필수
uv add django

# 선택적 추가 패키지
uv add django-jazzmin      # Modern admin UI
uv add django-import-export # 데이터 import/export
uv add django-debug-toolbar # 디버깅
```

### 4. Django 프로젝트 생성
```sh
uv run django-admin startproject config .
```

### 5. 데이터베이스 마이그레이션
```sh
uv run python manage.py migrate
```

### 6. 환경변수 설정
```sh
cp .env.example .env
# .env 파일에서 DJANGO_SUPERUSER_USERNAME, EMAIL, PASSWORD 수정
```

### 7. 슈퍼유저 생성
```sh
uv run python scripts/create_superuser.py
```

### 8. 개발 서버 실행
```sh
uv run python manage.py runserver
```

http://localhost:8000/admin/ 접속

## 프로젝트 구조

```
drama-shorts-web/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── scripts/
│   └── create_superuser.py
├── .env.example
├── manage.py
├── pyproject.toml
└── README.md
```
