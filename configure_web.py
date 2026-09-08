#!/usr/bin/env python3
"""Create/update the local web allowlist without printing or rotating its token."""
import argparse
import json
import os
from pathlib import Path
import secrets
from transcribe import save_json
from settings import data_root


def configure(root, logins, auth_mode="tailscale"):
    logins = sorted({value.strip().lower() for value in logins})
    if auth_mode not in ('local', 'tailscale'):
        raise ValueError('Unknown authentication mode')
    if (auth_mode == 'tailscale' and not logins) or any(not value or any(ord(c) < 33 for c in value) for value in logins):
        raise ValueError('Specify at least one non-empty Tailscale login without whitespace')
    path = Path(root) / 'web-config.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    config['auth_mode'] = auth_mode
    config['allowed_logins'] = logins
    if not config.get('admin_token'):
        config['admin_token'] = secrets.token_urlsafe(40)
    previous = os.umask(0o077)
    try:
        save_json(path, config)
        path.chmod(0o600)
    finally:
        os.umask(previous)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--allow-login', action='append', required=True, help='Repeat for each login; replaces the entire allowlist')
    args = p.parse_args()
    configure(data_root(), args.allow_login)
    print('Web access configured. The private maintenance token was preserved or generated; it is not printed.')
