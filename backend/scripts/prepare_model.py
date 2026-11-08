"""One-shot, idempotent Granite checkpoint bootstrap; never download in API process.

A verified cached manifest is authoritative on subsequent starts. New downloads are
pinned to a resolved immutable Hugging Face commit, then SHA256-manifested.
"""
import argparse
import json
import os
from pathlib import Path

from app.core.model_integrity import hash_file, verify_model

REPO = 'ibm-granite/granite-timeseries-ttm-r3'


def ensure_model(dest: Path, requested_revision: str = '', verify_only: bool = False) -> dict:
    dest = Path(dest).resolve()
    manifest = dest / 'manifest.json'
    if manifest.is_file() or verify_only:
        # Never silently replace corrupted cache or a previously pinned revision.
        revision = verify_model(dest)
        if requested_revision and revision != requested_revision:
            raise ValueError('Cached model revision differs from MODEL_REVISION; manual upgrade required')
        return {'status': 'verified_existing' if not verify_only else 'verified', 'revision': revision}

    # Network and Hugging Face dependencies are used only by the setup container.
    from huggingface_hub import HfApi, snapshot_download
    revision = requested_revision or HfApi().model_info(REPO).sha
    if len(revision) != 40 or any(ch not in '0123456789abcdef' for ch in revision):
        raise ValueError('Use immutable 40-character model revision SHA')
    dest.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=REPO, revision=revision, local_dir=str(dest),
                      allow_patterns=['config.json', '*.safetensors', 'model.safetensors.index.json'],
                      ignore_patterns=['*.bin', '*.pt', '*.pth'])
    files = {str(f.relative_to(dest)): hash_file(f) for f in dest.rglob('*')
             if f.is_file() and not f.is_symlink()
             and (f.name == 'config.json' or f.suffix == '.safetensors'
                  or f.name == 'model.safetensors.index.json')}
    if 'config.json' not in files or not any(name.endswith('.safetensors') for name in files):
        raise RuntimeError('Checkpoint download incomplete: config.json or safetensors missing')
    tmp = dest / 'manifest.json.tmp'
    tmp.write_text(json.dumps({'model_id': REPO, 'revision': revision, 'files': files}, indent=2) + '\n', 'utf-8')
    tmp.replace(manifest)
    return {'status': 'downloaded_and_verified', 'revision': verify_model(dest), 'files': list(files)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='./.models/granite-ttm-r3')
    p.add_argument('--revision', default=os.environ.get('MODEL_REVISION', '').strip())
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    print(json.dumps(ensure_model(Path(a.output), a.revision, a.verify_only)))


if __name__ == '__main__':
    main()
