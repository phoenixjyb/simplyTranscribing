#!/usr/bin/env python3
"""Copy this isolated worker's source to its existing WSL installation."""
import base64
from pathlib import Path
import shlex
import bridge

ROOT = Path(__file__).resolve().parent
files = ['transcribe.py', 'run.sh', 'requirements.txt', 'download_model.py', 'model-manifest.json', 'service.py', 'service.sh']
script = 'set -eu\ncd /opt/local-transcriber\nmkdir -p input output models logs\n'
for name in files:
    blob = base64.b64encode((ROOT / name).read_bytes()).decode()
    script += f"printf %s {shlex.quote(blob)} | base64 -d > {shlex.quote(name)}\n"
script += 'chmod 700 run.sh service.sh\npython3 -m py_compile transcribe.py download_model.py service.py\n'
raise SystemExit(bridge.wsl(script))
