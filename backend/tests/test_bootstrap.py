"""Model bootstrap and production validation using a fake small cache, never network."""
import hashlib
import json
from pathlib import Path
import pytest

from app.core.config import Settings


def cached_model(root: Path, revision: str = 'b' * 40):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'config.json').write_text('{"context_length":512,"prediction_length":30}')
    (root / 'model.safetensors').write_bytes(b'fake-weight-for-manifest-test')
    files = {}
    for name in ('config.json', 'model.safetensors'):
        files[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    (root / 'manifest.json').write_text(json.dumps({
        'model_id': 'ibm-granite/granite-timeseries-ttm-r3',
        'revision': revision, 'files': files,
    }))
    return revision


def test_production_uses_verified_cache_revision(tmp_path, monkeypatch):
    rev = cached_model(tmp_path)
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('API_AUTH_ENABLED', 'true')
    monkeypatch.setenv('API_TOKEN', 't' * 40)
    monkeypatch.setenv('MODEL_PATH', str(tmp_path))
    monkeypatch.delenv('MODEL_REVISION', raising=False)
    assert Settings.load().model_revision == rev


def test_production_rejects_missing_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('API_AUTH_ENABLED', 'true')
    monkeypatch.setenv('API_TOKEN', 't' * 40)
    monkeypatch.setenv('MODEL_PATH', str(tmp_path))
    monkeypatch.setenv('MODEL_REVISION', '')
    with pytest.raises(ValueError, match='verified model cache'):
        Settings.load()


def test_cached_setup_is_offline_and_revision_checked(tmp_path):
    rev = cached_model(tmp_path)
    from scripts.prepare_model import ensure_model
    assert ensure_model(tmp_path, '')['status'] == 'verified_existing'
    assert ensure_model(tmp_path, rev, verify_only=True)['revision'] == rev
    with pytest.raises(ValueError, match='revision differs'):
        ensure_model(tmp_path, 'c' * 40)


def test_cache_corruption_is_not_silently_replaced(tmp_path):
    cached_model(tmp_path)
    (tmp_path / 'model.safetensors').write_bytes(b'corrupted')
    from scripts.prepare_model import ensure_model
    with pytest.raises(ValueError, match='Checksum mismatch'):
        ensure_model(tmp_path)
