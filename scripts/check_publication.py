"""Fail CI on committed runtime data, private endpoints or local wheel URLs."""
import re
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
blocked_dirs = {'private', 'input', 'output', 'models', 'jobs', 'logs', 'qa', 'evidence', '.venv'}
blocked_suffixes = {'.wav', '.mp3', '.mp4', '.docx', '.srt', '.pem', '.key', '.secret'}
patterns = [r'file:/{2,3}[^\s]+', r'/' + r'Users/[^/\s]+/', r'\b192\.168\.\d+\.\d+\b',
            r'\b[a-z0-9-]+\.tail[a-z0-9]+\.ts\.net\b', r'gh[pousr]_[A-Za-z0-9]{20,}',
            r'tskey-[A-Za-z0-9-]{15,}', r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
errors = []
for name in filter(None, paths):
    path = Path(name)
    if blocked_dirs.intersection(path.parts) or path.suffix in blocked_suffixes or path.name in ('web-config.json', 'runtime.json', '.env'):
        errors.append(name + ': runtime/private file')
    if not (root / path).is_file():
        continue
    if path.suffix == '.png':
        continue
    content = (root / path).read_text(encoding='utf-8', errors='replace')
    if any(re.search(pattern, content) for pattern in patterns):
        errors.append(name + ': private endpoint, credential pattern or local dependency URL')
if errors:
    sys.exit('\n'.join(errors))
print('Publication hygiene checks passed (heuristic; review Git metadata separately).')
