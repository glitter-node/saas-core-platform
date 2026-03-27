#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENV_DIR="${ROOT_DIR}/.venv"

python3 - <<'PY'
import socket

try:
    socket.getaddrinfo("pypi.org", 443)
except OSError as exc:
    raise SystemExit(f"PyPI network access is required for dependency installation: {exc}")
PY

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements.txt"
