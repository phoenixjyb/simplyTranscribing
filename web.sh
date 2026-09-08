#!/usr/bin/env bash
set -euo pipefail
umask 077
TRANSCRIBER_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$TRANSCRIBER_ROOT"
mkdir -p logs
exec .venv/bin/python -m uvicorn web:app --host 127.0.0.1 --port 8020 --workers 1 --no-access-log >> logs/web.log 2>&1
