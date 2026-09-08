#!/usr/bin/env python3
"""Download a revision pinned by an independently retrieved official manifest."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'model-manifest.json').read_text())
target = ROOT / 'models/large-v3'
target.mkdir(parents=True, exist_ok=True)
files = []
for item in manifest['siblings']:
    name = item['rfilename']
    if name not in ['config.json', 'model.bin', 'preprocessor_config.json', 'tokenizer.json', 'vocabulary.json']:
        continue
    output = target / name
    part = target / (name + '.part')
    if not output.exists():
        endpoint = os.environ.get('HF_ENDPOINT', 'https://huggingface.co').rstrip('/')
        url = f"{endpoint}/Systran/faster-whisper-large-v3/resolve/{manifest['sha']}/{name}"
        print(f'Downloading {name}', flush=True)
        subprocess.run(['curl', '--fail', '--location', '--retry', '5', '--connect-timeout', '20', '--speed-time', '90', '--speed-limit', '1024', '-C', '-', '-o', str(part), url], check=True)
        part.replace(output)
    lfs = item.get('lfs')
    digest = hashlib.sha256() if lfs else hashlib.sha1()
    if not lfs:
        digest.update(f'blob {output.stat().st_size}\0'.encode())
    with output.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    expected = lfs['sha256'] if lfs else item['blobId']
    if digest.hexdigest() != expected:
        raise RuntimeError(f'Official model digest mismatch: {name}')
    files.append(dict(name=name, size=output.stat().st_size, digest=expected))
    print(f'Verified {name}', flush=True)
assert {'model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json'} <= {f['name'] for f in files}
(ROOT / 'models/large-v3.receipt.json').write_text(json.dumps(dict(repository='Systran/faster-whisper-large-v3', revision=manifest['sha'], files=files, verified_at=time.time()), indent=2) + '\n')
print('MODEL_FILES_VERIFIED', flush=True)
