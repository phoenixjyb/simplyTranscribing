#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${TRANSCRIBER_PYTHON:-.venv/bin/python}" transcribe.py "$@"
