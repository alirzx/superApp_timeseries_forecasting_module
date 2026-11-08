"""Manifest-based integrity. The manifest is only a local integrity record, not a signature."""
import hashlib
import json
from pathlib import Path


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_model(directory: Path) -> str:
    root = Path(directory).resolve()
    manifest_file = root / 'manifest.json'
    if not manifest_file.is_file():
        raise FileNotFoundError(f'Missing {manifest_file}; run model setup')
    manifest = json.loads(manifest_file.read_text('utf-8'))
    if manifest.get('model_id') != 'ibm-granite/granite-timeseries-ttm-r3':
        raise ValueError('Unexpected model ID')
    revision = manifest.get('revision', '')
    if len(revision) != 40 or not all(c in '0123456789abcdef' for c in revision):
        raise ValueError('Revision must be a pinned 40-character SHA')
    files = manifest.get('files', {})
    if not files or 'config.json' not in files or not any(k.endswith('.safetensors') for k in files):
        raise ValueError('Missing model configuration or safetensors hash')
    for relative, expected in files.items():
        p = (root / relative).resolve()
        if not p.is_relative_to(root) or not p.is_file() or p.is_symlink():
            raise ValueError('Model file missing or unsafe path')
        if hash_file(p) != expected:
            raise ValueError(f'Checksum mismatch: {relative}')
    return revision
