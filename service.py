#!/usr/bin/env python3
"""Serial job queue, held alive by the dedicated Windows WSL task."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from transcribe import save_json

ROOT = Path(__file__).resolve().parent
os.umask(0o077)
for directory in ['jobs', 'logs', 'output', 'input']:
    (ROOT / directory).mkdir(exist_ok=True)
lock = (ROOT / '.service.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
for path in (ROOT / 'jobs').glob('*.json'):
    job = json.loads(path.read_text())
    if job['status'] == 'running':
        job.update(status='interrupted', error='Worker service restarted; inspect partial output and resubmit if needed')
        save_json(path, job)
while True:
    save_json(ROOT / 'service-health.json', dict(status='ready', pid=os.getpid(), checked_at=time.time()))
    for path in sorted((ROOT / 'jobs').glob('*.json'), key=lambda p: p.stat().st_mtime):
        job = json.loads(path.read_text())
        if job['status'] != 'queued':
            continue
        job.update(status='running', started_at=time.time())
        save_json(path, job)
        save_json(ROOT / 'service-health.json', dict(status='busy', pid=os.getpid(), job=path.stem, checked_at=time.time()))
        arguments = [str(ROOT / 'run.sh'), job['input'], '--output-dir', str(ROOT / 'output' / path.stem), '--offline', '--language', job['language'], '--title', job['title']]
        if job.get('no_vad'):
            arguments.append('--no-vad')
        if job.get('initial_prompt'):
            arguments += ['--initial-prompt', job['initial_prompt']]
        try:
            with (ROOT / 'logs' / (path.stem + '.log')).open('ab') as log:
                result = subprocess.run(arguments, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            job.update(status='completed' if result.returncode == 0 else 'failed', exit_code=result.returncode, finished_at=time.time())
        except Exception as exc:
            job.update(status='failed', error=str(exc), finished_at=time.time())
        save_json(path, job)
    time.sleep(2)
