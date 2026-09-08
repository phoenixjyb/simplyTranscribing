#!/usr/bin/env python3
"""One cross-platform worker and one inference subprocess per job."""
import json
import os
import subprocess
import sys
import time
from filelock import FileLock
from settings import data_root, SOURCE
from transcribe import save_json


def main():
    root = data_root()
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=True)
    for directory in ['jobs', 'logs', 'output', 'input']:
        (root / directory).mkdir(exist_ok=True)
    with FileLock(root / '.service.lock', timeout=0):
        for path in (root / 'jobs').glob('*.json'):
            job = json.loads(path.read_text(encoding='utf-8'))
            if job['status'] == 'running':
                job.update(status='interrupted', error='Worker restarted; resubmit to retry')
                save_json(path, job)
        try:
            while not (root / '.stop-worker').exists():
                save_json(root / 'service-health.json', dict(status='ready', pid=os.getpid(), checked_at=time.time()))
                for path in sorted((root / 'jobs').glob('*.json'), key=lambda p: p.stat().st_mtime):
                    if (root / '.stop-worker').exists():
                        break
                    job = json.loads(path.read_text(encoding='utf-8'))
                    if job['status'] != 'queued':
                        continue
                    job.update(status='running', started_at=time.time())
                    save_json(path, job)
                    arguments = [sys.executable, str(SOURCE / 'transcribe.py'), job['input'], '--output-dir', str(root / 'output' / path.stem), '--language', job['language'], '--title', job['title']]
                    if job.get('no_vad'):
                        arguments.append('--no-vad')
                    if job.get('initial_prompt'):
                        arguments += ['--initial-prompt', job['initial_prompt']]
                    result = None
                    try:
                        with (root / 'logs' / (path.stem + '.log')).open('ab') as log:
                            result = subprocess.Popen(arguments, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                            while result.poll() is None:
                                save_json(root / 'service-health.json', dict(status='busy', pid=os.getpid(), job=path.stem, checked_at=time.time()))
                                if (root / '.stop-worker').exists():
                                    result.terminate()
                                    try:
                                        result.wait(timeout=5)
                                    except subprocess.TimeoutExpired:
                                        result.kill()
                                    break
                                time.sleep(1)
                            result.wait()
                        job.update(status='completed' if result.returncode == 0 else 'failed', exit_code=result.returncode, finished_at=time.time())
                    except Exception as exc:
                        job.update(status='failed', error=str(exc), finished_at=time.time())
                    finally:
                        if result and result.poll() is None:
                            result.kill()
                            result.wait()
                    save_json(path, job)
                time.sleep(1)
        finally:
            save_json(root / 'service-health.json', dict(status='offline', checked_at=time.time()))


if __name__ == '__main__':
    main()
