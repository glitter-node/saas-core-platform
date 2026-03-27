#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
cd "${APP_ROOT}"
"${APP_ROOT}/.venv/bin/python" "${APP_ROOT}/scripts/bootstrap_local_data.py"
