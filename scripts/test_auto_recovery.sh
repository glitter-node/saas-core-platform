#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
APP_ENV_FILE=${APP_ROOT}/.env
APP_DOMAIN=$(awk -F= '$1=="APP_DOMAIN"{print $2}' "${APP_ENV_FILE}" | tr -d '"')

wait_for_active() {
  local service=$1
  for _ in $(seq 1 30); do
    if systemctl is-active --quiet "${service}"; then
      return 0
    fi
    sleep 1
  done
  echo "service did not recover: ${service}" >&2
  return 1
}

wait_for_health() {
  local expected_code=$1
  for _ in $(seq 1 30); do
    code=$(curl -s -o /tmp/saas-health.out -w '%{http_code}' -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz || true)
    if [[ "${code}" == "${expected_code}" ]]; then
      return 0
    fi
    sleep 1
  done
  echo "health did not reach expected status ${expected_code}" >&2
  cat /tmp/saas-health.out >&2 || true
  return 1
}

systemctl kill -s SIGKILL saas_api
wait_for_active saas_api

systemctl kill -s SIGKILL saas_worker
wait_for_active saas_worker

systemctl kill -s SIGKILL saas_scheduler
wait_for_active saas_scheduler

systemctl stop redis-server
wait_for_health 503
systemctl start redis-server
wait_for_health 200

systemctl stop mariadb
wait_for_health 503
systemctl start mariadb
wait_for_health 200

sleep 5
redis-cli LLEN operations
journalctl -u saas_worker -u saas_scheduler -n 50 --no-pager
