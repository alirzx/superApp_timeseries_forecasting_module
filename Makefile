.PHONY: doctor model model-verify build up down ps health test smoke
PYTHON ?= python3
doctor:
	docker compose --env-file .env config --quiet
model:
	docker compose build model-setup
	docker compose run --rm --no-deps model-setup
model-verify:
	docker compose run --rm --no-deps model-setup python -m scripts.prepare_model --output /models/granite-ttm-r3 --verify-only
build:
	docker compose build model-setup api ui
up:
	docker compose up -d --no-build api ui
ps:
	docker compose ps
down:
	docker compose down
health:
	docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5); print('API model ready')"
	docker compose exec -T ui wget -qO- http://127.0.0.1:8080/ >/dev/null
	@echo 'UI reachable inside container'
test:
	PYTHONPATH=backend $(PYTHON) -m pytest -q backend/tests
smoke:
	$(PYTHON) scripts/smoke_api.py
