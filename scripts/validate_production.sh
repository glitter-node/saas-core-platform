#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/srv/multi_tenant_saas_subscription_platform
cd "${APP_ROOT}"

APP_DOMAIN=$(
  python3 - <<'PY'
from pathlib import Path

for line in Path("/srv/multi_tenant_saas_subscription_platform/.env").read_text(encoding="utf-8").splitlines():
    if line.startswith("APP_DOMAIN="):
        print(line.split("=", 1)[1].strip().strip('"').strip("'"))
        break
PY
)

curl -fsS -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz

ACCESS_TOKEN=$(
  python3 - <<'PY'
import json
import urllib.request
from pathlib import Path

app_domain = None
for line in Path("/srv/multi_tenant_saas_subscription_platform/.env").read_text(encoding="utf-8").splitlines():
    if line.startswith("APP_DOMAIN="):
        app_domain = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

payload = json.dumps({
    "email": "owner@app.local",
    "password": "StrongPass123",
}).encode("utf-8")
request = urllib.request.Request(
    "http://127.0.0.1/api/v1/auth/login",
    data=payload,
    headers={"Host": app_domain, "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=5) as response:
    body = json.loads(response.read().decode("utf-8"))
print(body["access_token"])
PY
)

ACCESS_TOKEN="${ACCESS_TOKEN}" APP_DOMAIN="${APP_DOMAIN}" python3 - <<'PY'
import os
import urllib.request

request = urllib.request.Request(
    "http://127.0.0.1/api/v1/me",
    headers={
        "Host": f"localdemo.{os.environ['APP_DOMAIN']}",
        "Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}",
    },
)
with urllib.request.urlopen(request, timeout=5) as response:
    if response.status != 200:
        raise SystemExit(response.status)
    print(response.read().decode("utf-8"))
PY

sleep 5

"${APP_ROOT}/.venv/bin/python" - <<'PY'
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
