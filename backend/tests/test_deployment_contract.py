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
    nginx = (ROOT/'ops/nginx.conf.template').read_text()
    assert 'resolver 127.0.0.11' in nginx
    assert 'set $api_backend "api:8000";' in nginx
    assert 'rewrite ^/api/(.*)$ /$1 break;' in nginx
    assert 'proxy_pass http://$api_backend;' in nginx
    # No DNS lookup at Nginx boot if the API is down or restarting.
    assert 'proxy_pass http://api:8000/;' not in nginx
    entrypoint = (ROOT/'ops/nginx-entrypoint.sh').read_text()
    for name in ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
        assert f'{name}_temp_path /tmp/nginx_' in entrypoint
    assert '/var/cache/nginx/' not in entrypoint.replace('# All Nginx temp modules default to /var/cache/nginx otherwise.', '')
    ui_compose = compose.split('  ui:', 1)[1]
    assert 'depends_on:' not in ui_compose
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
    assert 'requirements-torch-cpu.txt' in image
    assert (ROOT / 'backend/requirements-torch-cpu.txt').is_file()
    assert '--no-deps' in image and "'torch==2.10.0+cpu'" in image
    # Pure Python torch requirements MUST be installed before CPU wheel, and
    # Granite/API requirements afterwards. Never rely on PyPI for wheel deps.
    pure_deps = image.index('-r /tmp/requirements-torch-cpu.txt')
    cpu_wheel = image.index("'torch==2.10.0+cpu'")
    app_deps = image.index('-r /tmp/requirements.txt')
    assert pure_deps < cpu_wheel < app_deps
    assert 'python -m pip check' in image
    assert "torch.__version__.startswith('2.10.0+cpu')" in image

