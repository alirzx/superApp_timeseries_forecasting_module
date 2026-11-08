"""Deployment wiring regression checks, no Docker daemon or model weights required."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_env_templates_are_trackable_and_safe():
    for name in ('.env.example', '.env.production.example', '.gitignore', '.dockerignore'):
        assert (ROOT / name).exists(), f'Missing deployment prerequisite {name}'
    dev = (ROOT / '.env.example').read_text()
    prod = (ROOT / '.env.production.example').read_text()
    assert 'UI_BIND_IP=127.0.0.1' in dev
    assert 'UI_BIND_IP=0.0.0.0' in prod
    assert 'API_BIND_IP=127.0.0.1' in prod
    for text in (dev, prod):
        assert 'PIP_PRIMARY_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple' in text
        assert 'PIP_FALLBACK_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/' in text
    ignore = (ROOT / '.gitignore').read_text()
    assert '.models/' in ignore and '.env' in ignore


def test_compose_uses_lan_bind_and_one_shot_model_download():
    compose = (ROOT / 'docker-compose.yml').read_text()
    assert 'profiles: ["setup"]' in compose
    assert '${UI_BIND_IP:-127.0.0.1}:${UI_PORT:-8086}:8080' in compose
    assert 'http://api:8000' in (ROOT/'ops/nginx.conf.template').read_text()
    assert '${PIP_PRIMARY_INDEX_URL' in compose
    assert '${PIP_FALLBACK_INDEX_URL' in compose
    assert 'HF_HUB_OFFLINE: "1"' in compose
    assert 'run --rm --no-deps model-setup' in (ROOT / 'Makefile').read_text()


def test_python_build_is_cpu_only_and_mirrored():
    image = (ROOT/'backend/Dockerfile').read_text()
    assert 'torch==2.10.0+cpu' in image
    assert 'torch.version.cuda is None' in image
    assert 'PIP_PRIMARY_INDEX_URL' in image and 'PIP_FALLBACK_INDEX_URL' in image
    assert 'pypi.org/simple' not in image
    assert not (ROOT/'.gitlab-ci.yml').exists()
