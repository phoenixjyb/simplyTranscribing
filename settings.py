"""Runtime paths and administrator-controlled inference defaults."""
import json
import os
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
MODELS = ['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 'large-v3']
DEFAULTS = dict(model='base', device='cpu', device_index=0, compute_type='auto', cpu_threads=4,
                min_free_mib=1024, max_gpu_utilization=50, offline=False)


def data_root():
    override = os.environ.get('TRANSCRIBER_DATA_DIR') or os.environ.get('TRANSCRIBER_ROOT')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library/Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    return base / 'simply-transcribing'


def runtime_settings(root=None):
    path = (root or data_root()) / 'runtime.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    unknown = set(config) - set(DEFAULTS)
    if unknown:
        raise ValueError('Unknown runtime settings: ' + ', '.join(sorted(unknown)))
    result = {**DEFAULTS, **config}
    if result['model'] not in MODELS or result['device'] not in ('cpu', 'cuda', 'auto'):
        raise ValueError('Invalid model or device in runtime.json')
    if result['compute_type'] not in ('auto', 'int8', 'float32', 'float16', 'int8_float16'):
        raise ValueError('Invalid compute_type in runtime.json')
    for key in ('device_index', 'cpu_threads', 'min_free_mib', 'max_gpu_utilization'):
        if type(result[key]) is not int or result[key] < 0:
            raise ValueError(f'{key} must be a nonnegative integer')
    if result['cpu_threads'] == 0 or result['max_gpu_utilization'] > 100 or type(result['offline']) is not bool:
        raise ValueError('Invalid thread count, utilization threshold or offline setting')
    return result
