#!/usr/bin/env bash
set -euo pipefail
TRANSCRIBER_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$TRANSCRIBER_ROOT"
umask 077
mkdir -p logs
exec /usr/bin/python3 service.py >> logs/service.log 2>&1
