#!/usr/bin/env python3
"""Initialize and run Simply Transcribing on Linux, macOS or Windows."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from settings import data_root, SOURCE, runtime_settings
from runtime import prepare_cuda_libraries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--auth', choices=['local', 'tailscale'], default='local')
    init.add_argument('--allow-login', action='append', default=[])
    start = sub.add_parser('start')
    start.add_argument('--port', type=int, default=8020)
    sub.add_parser('doctor')
    args = parser.parse_args()
    root = data_root()
    if args.command == 'doctor':
        print(json.dumps(dict(python=sys.version.split()[0], platform=sys.platform,
            ffprobe=bool(shutil.which('ffprobe')), runtime=runtime_settings(root),
            configured=(root / 'web-config.json').is_file()), indent=2))
        return
    root.mkdir(parents=True, exist_ok=True)
    if args.command == 'init':
        from configure_web import configure
        if (root / 'web-config.json').exists():
            raise ValueError('Already configured; use configure_web.py for explicit access changes')
        if args.auth == 'tailscale' and not args.allow_login:
            raise ValueError('Tailscale mode requires at least one --allow-login')
        configure(root, args.allow_login, auth_mode=args.auth)
        from transcribe import save_json
        if not (root / 'runtime.json').exists():
            save_json(root / 'runtime.json', runtime_settings(root))
        print('Initialized private configuration at ' + str(root))
        return
    if not (root / 'web-config.json').is_file():
        raise ValueError('Run python app.py init first')
    if not shutil.which('ffprobe'):
        raise ValueError('Install FFmpeg and put ffprobe on PATH before starting')
    if not 1 <= args.port <= 65535:
        raise ValueError('Port must be between 1 and 65535')
    from filelock import FileLock
    with FileLock(root / '.app.lock', timeout=0):
        handles = prepare_cuda_libraries()
        (root / '.stop-worker').unlink(missing_ok=True)
        (root / '.stop-app').unlink(missing_ok=True)
        env = dict(os.environ, TRANSCRIBER_DATA_DIR=str(root), HF_HUB_DISABLE_TELEMETRY='1', PYTHONUTF8='1')
        children = []
        try:
            creation = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            children.append(subprocess.Popen([sys.executable, str(SOURCE / 'service.py')], cwd=SOURCE, env=env, **creation))
            children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'web:app', '--host', '127.0.0.1', '--port', str(args.port), '--no-proxy-headers', '--no-access-log'], cwd=SOURCE, env=env, **creation))
            print(f'Open http://127.0.0.1:{args.port} (or your configured Tailscale Serve URL)', flush=True)
            while all(child.poll() is None for child in children):
                if (root / '.stop-app').exists():
                    return
                time.sleep(.5)
            raise RuntimeError('A service process exited; inspect the messages above')
        except KeyboardInterrupt:
            print('Stopping the service…', flush=True)
        finally:
            (root / '.stop-worker').touch()
            if len(children) > 1 and children[1].poll() is None:
                children[1].terminate()
            for child in children:
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            (root / '.stop-worker').unlink(missing_ok=True)


if __name__ == '__main__':
    def stop_signal(*_):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, stop_signal)
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        sys.exit(str(exc))
