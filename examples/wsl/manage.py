#!/usr/bin/env python3
"""Legacy client for the original fixed-layout WSL deployment; see examples/wsl/README.md."""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time
import uuid
import bridge

REMOTE = '/opt/local-transcriber'

def wsl_command(command):
    distro = os.environ.get('TRANSCRIBER_DISTRO', 'Ubuntu-24.04').replace("'", "''")
    # PowerShell 5 native argument forwarding strips nested quote characters.
    # Transfer the actual command as data, keeping stdin available for uploads.
    blob = base64.b64encode(command.encode()).decode()
    path = f'{REMOTE}/commands/{uuid.uuid4().hex}.sh'
    wrapper = f'umask 077; mkdir -p {REMOTE}/commands; echo {blob} | base64 -d > {path}; bash {path}; result=$?; rm -f {path}; exit $result'
    script = "& wsl.exe -d '" + distro + "' -- bash -c '" + wrapper + "'; exit $LASTEXITCODE"
    return bridge.command(script)

def remote(command, capture=False):
    return subprocess.run(wsl_command(command), check=True, stdout=subprocess.PIPE if capture else None)

def check_job(value):
    if not re.fullmatch(r'[a-f0-9]{12}', value):
        raise ValueError('Job IDs are twelve lowercase hexadecimal characters')
    return value

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('health')
    start = sub.add_parser('submit')
    start.add_argument('input', help='Mac local file, or WSL path with --remote')
    start.add_argument('--remote', action='store_true')
    start.add_argument('--language', default='auto')
    start.add_argument('--no-vad', action='store_true')
    start.add_argument('--initial-prompt')
    start.add_argument('--title')
    start.add_argument('--upload-only', action='store_true')
    status = sub.add_parser('status')
    status.add_argument('job')
    fetch = sub.add_parser('fetch')
    fetch.add_argument('job')
    fetch.add_argument('--output-dir', required=True)
    args = p.parse_args()
    if args.action == 'health':
        bridge.powershell("Get-ScheduledTask -TaskName 'Local Transcriber WSL' | Select-Object TaskName,State | ConvertTo-Json; exit 0")
        return remote(f"test -x {REMOTE}/run.sh && test -f {REMOTE}/models/large-v3.receipt.json && {REMOTE}/.venv/bin/python -m pip check && cat {REMOTE}/service-health.json && cat {REMOTE}/models/large-v3.receipt.json && /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.free,utilization.gpu --format=csv")
    if args.action == 'submit':
        job = uuid.uuid4().hex[:12]
        source = args.input
        if not args.remote:
            path = Path(source).expanduser().resolve(strict=True)
            if not path.is_file():
                raise ValueError('Input must be a file')
            # Keep uploaded filenames opaque so user-controlled paths never become commands.
            suffix = path.suffix.lower()
            if not re.fullmatch(r'\.[a-z0-9]{1,8}', suffix):
                suffix = '.media'
            source = f'{REMOTE}/input/{job}{suffix}'
            process = subprocess.Popen(wsl_command(f'umask 077; base64 -d > {source}.part && mv {source}.part {source}'), stdin=subprocess.PIPE)
            try:
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(3 * 1024 * 1024), b''):
                        process.stdin.write(base64.b64encode(chunk))
                process.stdin.close()
                if process.wait() != 0:
                    raise RuntimeError('Upload failed; partial media remains on the home PC')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
        if args.upload_only:
            print(json.dumps(dict(upload=job, input=source)))
            return
        payload = dict(status='queued', input=source, language=args.language, title=args.title or Path(args.input).stem, no_vad=args.no_vad, initial_prompt=args.initial_prompt, submitted_at=time.time())
        blob = base64.b64encode(json.dumps(payload).encode()).decode()
        command = 'umask 077; test -f ' + shlex.quote(source) + ' || exit 2; '
        command += f'mkdir -p {REMOTE}/jobs; printf %s {blob} | base64 -d > {REMOTE}/jobs/{job}.json.tmp && mv {REMOTE}/jobs/{job}.json.tmp {REMOTE}/jobs/{job}.json'
        remote(command)
        if bridge.powershell("$ErrorActionPreference='Stop'; Start-ScheduledTask -TaskName 'Local Transcriber WSL'; exit 0") != 0:
            raise RuntimeError(f'Job {job} was queued but the Windows worker task could not be started')
        print(json.dumps(dict(job=job, input=source, output=f'{REMOTE}/output/{job}', status='submitted')))
        return
    job = check_job(args.job)
    out = f'{REMOTE}/output/{job}'
    if args.action == 'status':
        result = remote(f'cat {REMOTE}/jobs/{job}.json; cat {out}/run.json 2>/dev/null; tail -4 {REMOTE}/logs/{job}.log 2>/dev/null; cat {REMOTE}/service-health.json', capture=True)
        print(result.stdout.decode('utf-8', errors='replace'))
    elif args.action == 'fetch':
        dest = Path(args.output_dir).expanduser().resolve()
        if dest.exists() and any(dest.iterdir()):
            raise ValueError('Download directory must be new or empty')
        code = 'import json; assert json.load(open(' + repr(out + '/run.json') + '))["complete"], "Job is incomplete; inspect status and partial progress"'
        files = ['run.json', 'segments.jsonl', 'transcript.txt', 'transcript.md', 'transcript.json', 'transcript.srt', 'transcript.docx']
        result = remote(f'{REMOTE}/.venv/bin/python -c {shlex.quote(code)} && tar -czf - -C {out} ' + shlex.join(files) + ' | base64 -w0', capture=True)
        data = base64.b64decode(result.stdout.strip(), validate=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            members = archive.getmembers()
            if {m.name for m in members} != set(files) or any(not m.isfile() for m in members):
                raise ValueError('Unexpected artifact archive contents')
            dest.mkdir(parents=True, exist_ok=True)
            for member in members:
                (dest / member.name).write_bytes(archive.extractfile(member).read())
        print(str(dest))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
