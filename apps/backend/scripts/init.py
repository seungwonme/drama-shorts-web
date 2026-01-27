#!/usr/bin/env python
"""Django 초기화 스크립트 (migrate + superuser)"""

import os
import sys
from pathlib import Path

# Django 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model


def main():
    print("=== Django 초기화 ===")

    # 1. Migrate
    print("\n[1/3] 마이그레이션 실행...")
    call_command("migrate", verbosity=1)
    print("✓ 마이그레이션 완료")

    # 2. Collectstatic
    print("\n[2/3] 정적 파일 수집...")
    call_command("collectstatic", "--noinput", verbosity=0)
    print("✓ 정적 파일 수집 완료")

    # 3. Superuser 생성
    print("\n[3/3] 슈퍼유저 확인...")
    User = get_user_model()

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234")

    if User.objects.filter(username=username).exists():
        print(f"✓ 슈퍼유저 이미 존재: {username}")
    else:
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"✓ 슈퍼유저 생성: {username}")

    print("\n=== 초기화 완료 ===")


if __name__ == "__main__":
    main()
