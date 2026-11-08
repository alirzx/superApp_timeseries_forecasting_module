.PHONY: doctor model model-verify build up down ps health test smoke
PYTHON ?= python3
doctor:
	docker compose config --quiet
model:
	PYTHONPATH=backend $(PYTHON) backend/scripts/prepare_model.py --output .models/granite-ttm-r3
model-verify:
	PYTHONPATH=backend $(PYTHON) backend/scripts/prepare_model.py --output .models/granite-ttm-r3 --verify-only
build:
	docker compose build api ui
up:
	docker compose up -d --no-build api ui
ps:
	docker compose ps
down:
	docker compose down
health:
	curl -fsS http://127.0.0.1:8005/health/ready
test:
	PYTHONPATH=backend pytest -q backend/tests
smoke:
	$(PYTHON) scripts/smoke_api.py
