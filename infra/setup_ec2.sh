#!/bin/bash
# EC2 Ubuntu 초기 설정 스크립트
# 사용법: curl -sSL <raw-url> | bash
# 참고: https://docs.docker.com/engine/install/ubuntu/
#       https://git-scm.com/download/linux

set -e

echo "=== 시스템 업데이트 ==="
sudo apt-get update
sudo apt-get upgrade -y

echo "=== 기존 Docker 패키지 제거 ==="
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
    sudo apt-get remove -y $pkg 2>/dev/null || true
done

echo "=== Docker 공식 저장소 설정 ==="
# 필수 패키지 설치
sudo apt-get install -y ca-certificates curl

# Docker GPG 키 추가
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

echo "=== Docker 설치 ==="
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker 그룹에 현재 사용자 추가
sudo usermod -aG docker $USER

echo "=== Git 공식 저장소 설정 ==="
# Git PPA 추가 (최신 버전)
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt-get update

echo "=== Git 설치 ==="
sudo apt-get install -y git

echo "=== 프로젝트 디렉토리 생성 ==="
sudo mkdir -p /var/www/drama-shorts-web
sudo chown $USER:$USER /var/www/drama-shorts-web

echo "=== 설치 확인 ==="
echo "Docker 버전: $(docker --version)"
echo "Docker Compose 버전: $(docker compose version)"
echo "Git 버전: $(git --version)"

echo ""
echo "=== 완료 ==="
echo ""
echo "!! 로그아웃 후 다시 접속하세요 (docker 그룹 적용) !!"
echo ""
echo "다음 단계:"
echo "1. exit"
echo "2. ssh -i drama-shorts-key.pem ubuntu@<ip-address>"
echo "3. cd /var/www/drama-shorts-web"
echo "4. git clone https://github.com/seungwonme/drama-shorts-web.git ."
echo "5. cp .env.example .env && nano .env"
echo "6. ./run.sh"