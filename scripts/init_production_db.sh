#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
"${APP_ROOT}/scripts/init_local_db.sh" "${APP_ROOT}/.env"
