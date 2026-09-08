#!/usr/bin/env python3
"""Cache a supported model explicitly before an offline deployment."""
import argparse
from settings import MODELS, data_root, runtime_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, default=runtime_settings()['model'])
    parser.add_argument('--revision', help='Optional Hugging Face revision to pin')
    args = parser.parse_args()
    from faster_whisper.utils import download_model
    target = data_root() / 'models' / args.model
    target.parent.mkdir(parents=True, exist_ok=True)
    download_model(args.model, output_dir=str(target), revision=args.revision)
    print('Model cached. Set offline=true in runtime.json for offline inference.')


if __name__ == '__main__':
    main()
