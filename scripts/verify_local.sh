#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="${ROOT_DIR}/.local"
API_LOG="${LOG_DIR}/api.log"
WORKER_LOG="${LOG_DIR}/worker.log"
SCHEDULER_LOG="${LOG_DIR}/scheduler.log"
APP_PORT_VALUE=${APP_PORT:-8000}

mkdir -p "${LOG_DIR}"

cleanup() {
  if [[ -n "${SCHEDULER_PID:-}" ]]; then kill "${SCHEDULER_PID}" >/dev/null 2>&1 || true; fi
  if [[ -n "${WORKER_PID:-}" ]]; then kill "${WORKER_PID}" >/dev/null 2>&1 || true; fi
  if [[ -n "${API_PID:-}" ]]; then kill "${API_PID}" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT

"${ROOT_DIR}/.venv/bin/alembic" upgrade head
"${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/scripts/bootstrap_local_data.py"
"${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/scripts/render_deployment.py"

"${ROOT_DIR}/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "${APP_PORT_VALUE}" >"${API_LOG}" 2>&1 &
API_PID=$!

for _ in $(seq 1 20); do
  if APP_PORT_VALUE="${APP_PORT_VALUE}" python3 - <<'PY'
import sys
import os
from urllib.request import urlopen
try:
    with urlopen(f"http://127.0.0.1:{os.environ['APP_PORT_VALUE']}/healthz", timeout=1) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
  then
    break
  fi
  sleep 1
done

"${ROOT_DIR}/.venv/bin/celery" -A worker.main:celery_app worker --loglevel=INFO --concurrency=1 -P solo >"${WORKER_LOG}" 2>&1 &
WORKER_PID=$!
sleep 5

"${ROOT_DIR}/.venv/bin/celery" -A worker.scheduler:celery_app beat --loglevel=INFO --schedule "${ROOT_DIR}/.local/celerybeat-schedule" >"${SCHEDULER_LOG}" 2>&1 &
SCHEDULER_PID=$!
sleep 5

ACCESS_TOKEN=$(
  APP_PORT_VALUE="${APP_PORT_VALUE}" python3 - <<'PY'
import json
import os
import urllib.request

payload = json.dumps({
    "email": "owner@app.local",
    "password": "StrongPass123",
}).encode("utf-8")
request = urllib.request.Request(
    f"http://127.0.0.1:{os.environ['APP_PORT_VALUE']}/api/v1/auth/login",
    data=payload,
    headers={"Host": "app.local", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=5) as response:
    body = json.loads(response.read().decode("utf-8"))
print(body["access_token"])
PY
)

export ACCESS_TOKEN
APP_PORT_VALUE="${APP_PORT_VALUE}" python3 - <<'PY'
import os
import urllib.request

request = urllib.request.Request(
    f"http://127.0.0.1:{os.environ['APP_PORT_VALUE']}/api/v1/me",
    headers={
        "Host": "localdemo.app.local",
        "Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}",
    },
)
with urllib.request.urlopen(request, timeout=5) as response:
    print(response.status)
    print(response.read().decode("utf-8"))
PY

sleep 5

"${ROOT_DIR}/.venv/bin/python" - <<'PY'
from app.db import models
from app.db.session import SessionLocal
from app.domains.notifications.models import Notification
from app.domains.tenants.models import Tenant
from sqlalchemy import select

_ = models
with SessionLocal() as session:
    tenant = session.execute(select(Tenant).where(Tenant.slug == "localdemo")).scalar_one()
    notification = session.execute(
        select(Notification).where(
            Notification.tenant_id == tenant.id,
            Notification.type == "usage_limit_warning",
        )
    ).scalar_one_or_none()
    if notification is None:
        raise SystemExit("Missing notification side effect")
    print(notification.id)
PY

grep -q "Uvicorn running" "${API_LOG}"
grep -q "ready." "${WORKER_LOG}"
grep -q "beat: Starting" "${SCHEDULER_LOG}"
grep -q "worker.check_usage_limit_warning" "${WORKER_LOG}"
