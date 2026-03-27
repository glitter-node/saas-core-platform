#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE=${1:-"${ROOT_DIR}/.env"}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

eval "$(
  python3 - "${ENV_FILE}" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlparse

env_path = Path(sys.argv[1])
values = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key] = value.strip().strip('"').strip("'")

database_url = values.get("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL is required in the env file")

parsed = urlparse(database_url)
if parsed.scheme != "mysql+pymysql":
    raise SystemExit(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")

db_name = parsed.path.lstrip("/")
db_user = parsed.username or ""
db_password = parsed.password or ""
db_host = parsed.hostname or "127.0.0.1"

if not db_name or not db_user or not db_password:
    raise SystemExit("DATABASE_URL must include database name, username, and password")

print(f"DB_NAME={db_name!r}")
print(f"DB_USER={db_user!r}")
print(f"DB_PASSWORD={db_password!r}")
print(f"DB_HOST={db_host!r}")
PY
)"

sudo mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;
CREATE USER IF NOT EXISTS '${DB_USER}'@'${DB_HOST}' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'${DB_HOST}';
FLUSH PRIVILEGES;
SQL
