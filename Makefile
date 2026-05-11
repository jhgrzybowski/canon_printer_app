PYTHON ?= .venv/bin/python

.PHONY: test pycompile shellcheck docker-build compose-up healthcheck

test:
	$(PYTHON) -m pytest -q

pycompile:
	$(PYTHON) -m py_compile $$(find app scripts tests -name '*.py')

shellcheck:
	bash -n scripts/*.sh

docker-build:
	docker build -t local-printer-api:latest .

compose-up:
	docker compose up -d --build

healthcheck:
	curl -fsS http://localhost:8000/health
