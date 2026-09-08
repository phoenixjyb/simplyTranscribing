#!/usr/bin/env bash
set -euo pipefail
TRANSCRIBER_ROOT="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$("$TRANSCRIBER_ROOT/.venv/bin/python" - <<'PY'
import site
from pathlib import Path
print(':'.join(str(p) for root in site.getsitepackages() for p in Path(root).glob('nvidia/*/lib') if p.is_dir()))
PY
):/usr/lib/wsl/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
exec "$TRANSCRIBER_ROOT/.venv/bin/python" "$TRANSCRIBER_ROOT/transcribe.py" "$@"
