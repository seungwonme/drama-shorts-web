#!/bin/bash
# EC2 Ubuntu Docker 설치 스크립트
# 사용법: curl -sSL <raw-url> | bash

set -e

echo "=== 시스템 업데이트 ==="
sudo apt update && sudo apt upgrade -y

echo "=== Docker 설치 ==="
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

echo "=== Git 설치 ==="
sudo apt install -y git

echo "=== 프로젝트 디렉토리 생성 ==="
sudo mkdir -p /var/www/drama-shorts-web
sudo chown $USER:$USER /var/www/drama-shorts-web

echo "=== 완료 ==="
echo ""
echo "!! 로그아웃 후 다시 접속하세요 (docker 그룹 적용) !!"
echo ""
echo "다음 단계:"
echo "1. exit"
echo "2. ssh -i your-key.pem ubuntu@<elastic-ip>"
echo "3. cd /var/www/drama-shorts-web"
echo "4. git clone <your-repo> ."
echo "5. cp .env.example .env && nano .env"
echo "6. ./run.sh"
