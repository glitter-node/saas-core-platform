#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
SRC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

sudo mkdir -p "${APP_ROOT}"
sudo rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '.local' \
  --exclude '__pycache__' \
  --exclude 'deployment/rendered' \
  "${SRC_DIR}/" "${APP_ROOT}/"

sudo python3 -m venv "${APP_ROOT}/.venv"
sudo "${APP_ROOT}/.venv/bin/python" -m pip install --upgrade pip
sudo "${APP_ROOT}/.venv/bin/python" -m pip install -r "${APP_ROOT}/requirements.txt"

sudo install -d -o www-data -g www-data "${APP_ROOT}/.local"
sudo install -d -o www-data -g adm /var/log/multi_tenant_saas_subscription_platform
sudo touch /var/log/multi_tenant_saas_subscription_platform/api.log
sudo touch /var/log/multi_tenant_saas_subscription_platform/worker.log
sudo touch /var/log/multi_tenant_saas_subscription_platform/scheduler.log
sudo chown www-data:adm /var/log/multi_tenant_saas_subscription_platform/api.log
sudo chown www-data:adm /var/log/multi_tenant_saas_subscription_platform/worker.log
sudo chown www-data:adm /var/log/multi_tenant_saas_subscription_platform/scheduler.log
sudo install -m 0644 "${APP_ROOT}/deployment/systemd/saas_api.service" /etc/systemd/system/saas_api.service
sudo install -m 0644 "${APP_ROOT}/deployment/systemd/saas_worker.service" /etc/systemd/system/saas_worker.service
sudo install -m 0644 "${APP_ROOT}/deployment/systemd/saas_scheduler.service" /etc/systemd/system/saas_scheduler.service
sudo install -m 0644 "${APP_ROOT}/deployment/nginx/nginx.conf" /etc/nginx/nginx.conf
sudo chmod +x "${APP_ROOT}/scripts/run_scheduler.sh" "${APP_ROOT}/scripts/test_auto_recovery.sh" "${APP_ROOT}/scripts/ops_status.sh" "${APP_ROOT}/scripts/validate_production.sh"

if [[ ! -f "${APP_ROOT}/.env" ]]; then
  sudo install -m 0640 "${APP_ROOT}/.env.production.example" "${APP_ROOT}/.env"
fi

sudo chown root:www-data "${APP_ROOT}/.env"
sudo systemctl daemon-reload
