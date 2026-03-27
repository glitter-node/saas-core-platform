#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
APP_ENV_FILE=${APP_ROOT}/.env

APP_DOMAIN=$(awk -F= '$1=="APP_DOMAIN"{print $2}' "${APP_ENV_FILE}" | tr -d '"')

echo "== systemd =="
systemctl --no-pager --plain --type=service --state=running status saas_api saas_worker saas_scheduler mariadb redis-server nginx || true

echo
echo "== healthz =="
curl -sS -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz || true
echo

echo "== redis queue =="
redis-cli LLEN operations || true

echo
echo "== recent errors =="
grep -iE 'error|exception|traceback|failed' /var/log/multi_tenant_saas_subscription_platform/api.log /var/log/multi_tenant_saas_subscription_platform/worker.log /var/log/multi_tenant_saas_subscription_platform/scheduler.log /var/log/nginx/error.log | tail -n 50 || true
