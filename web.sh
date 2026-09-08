#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${TRANSCRIBER_PYTHON:-.venv/bin/python}" -m uvicorn web:app --host 127.0.0.1 --port 8020 --no-proxy-headers --no-access-log
