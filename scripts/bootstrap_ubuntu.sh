#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential \
  curl \
  libmariadb-dev \
  mariadb-server \
  nginx \
  pkg-config \
  python3 \
  python3-pip \
  python3-venv \
  redis-server \
  rsync

sudo systemctl enable --now mariadb
sudo systemctl enable --now redis-server
