#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
SCHEDULE_FILE="${APP_ROOT}/.local/celerybeat-schedule"

rm -f "${SCHEDULE_FILE}" "${SCHEDULE_FILE}".db "${SCHEDULE_FILE}".dat "${SCHEDULE_FILE}".bak "${SCHEDULE_FILE}".dir

exec "${APP_ROOT}/.venv/bin/celery" -A worker.scheduler:celery_app beat --loglevel=INFO --schedule "${SCHEDULE_FILE}"
