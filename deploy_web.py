#!/usr/bin/env python3
"""Deploy only web source; never overwrite credentials or transcription data."""
import base64
from pathlib import Path
import shlex
import bridge

ROOT = Path(__file__).resolve().parent
names = ['configure_web.py', 'web.py', 'web.sh', 'web-requirements.txt', 'test_web.py', 'web/index.html', 'web/style.css', 'web/app.js']
script = 'set -eu\numask 077\ncd /opt/local-transcriber\nmkdir -p web logs\n'
for name in names:
    blob = base64.b64encode((ROOT / name).read_bytes()).decode()
    script += f'printf %s {shlex.quote(blob)} | base64 -d > {shlex.quote(name + ".new")}\nmv {shlex.quote(name + ".new")} {shlex.quote(name)}\n'
script += '''chmod 700 web.sh
.venv/bin/python -m py_compile web.py test_web.py
.venv/bin/python - <<'PY'
import json, secrets
from pathlib import Path
p = Path('web-config.json')
if not p.exists():
    with p.open('x') as f:
        json.dump(dict(allowed_logins=[], admin_token=secrets.token_urlsafe(40)), f)
p.chmod(0o600)
PY
'''
raise SystemExit(bridge.wsl(script))
