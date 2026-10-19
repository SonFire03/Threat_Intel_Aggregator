RUNNER ?= python -m uvicorn
APP_HOST ?= 0.0.0.0
APP_PORT ?= 8000

.PHONY: run test docker-up docker-test lint

run:
	APP_HOST=$(APP_HOST) APP_PORT=$(APP_PORT) ./scripts/run.sh

test:
	./scripts/test.sh -q

docker-up:
	docker compose up --build

docker-test:
	USE_DOCKER=1 ./scripts/test.sh -q

lint:
	python -m ruff check .
