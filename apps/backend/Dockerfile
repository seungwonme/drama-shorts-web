FROM python:3.13-slim

WORKDIR /app

# 시스템 의존성 설치 (curl, ffmpeg, OpenCV 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치
RUN uv sync --frozen --no-dev

# 소스 복사
COPY . .

# 엔트리포인트 실행 권한
RUN chmod +x entrypoint.sh

# static 파일 수집
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
