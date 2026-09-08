#!/usr/bin/env python3
"""Invoke Windows PowerShell/WSL over an explicitly configured SSH route."""
import argparse
import base64
import os
from pathlib import Path
import shlex
import subprocess
import sys


def command(script):
    # Keep param blocks valid even when prepending transport preferences.
    script = "$ProgressPreference='SilentlyContinue'; & {\n" + script + '\n}'
    encoded = base64.b64encode(script.encode('utf-16le')).decode()
    host = os.environ.get('TRANSCRIBER_WINDOWS_ALIAS')
    if not host or host.startswith('-') or any(c.isspace() for c in host):
        raise ValueError('Set TRANSCRIBER_WINDOWS_ALIAS to a Windows SSH host or configured alias')
    powershell_command = 'powershell.exe -NoProfile -NonInteractive -EncodedCommand ' + encoded
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', host, powershell_command]
    helper = os.environ.get('TRANSCRIBER_RELAY_HELPER')
    if helper:
        profile = os.environ.get('TRANSCRIBER_RELAY_PROFILE')
        if not profile:
            raise ValueError('TRANSCRIBER_RELAY_PROFILE is required when using a relay helper')
        # Helper signature: helper PROFILE REMOTE_COMMAND. Private configuration
        # and credentials belong outside this repository.
        return [helper, profile, shlex.join(ssh)]
    return ssh


def powershell(script):
    return subprocess.run(command(script)).returncode


def wsl(script):
    distro = os.environ.get('TRANSCRIBER_DISTRO', 'Ubuntu-24.04').replace("'", "''")
    return subprocess.run(command("& wsl.exe -d '" + distro + "' -- bash -s; exit $LASTEXITCODE"), input=script.encode()).returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['ps', 'wsl'])
    parser.add_argument('file', nargs='?', help='Read script from this file, otherwise stdin')
    args = parser.parse_args()
    try:
        script = Path(args.file).read_text() if args.file else sys.stdin.read()
        sys.exit((powershell if args.mode == 'ps' else wsl)(script))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
