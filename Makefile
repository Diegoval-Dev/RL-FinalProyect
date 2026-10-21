.PHONY: setup lint test test-lab lab-up lab-down smoke run verify-splits endpoints-doc modsec-baseline

COMPOSE = docker compose -f lab/docker-compose.yml

define not_implemented
	@echo "$(1) is created by task $(2)" >&2; exit 1
endef

setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest tests/unit

test-lab: lab-up
	uv run pytest tests/lab/test_isolation.py -m lab
	$(COMPOSE) run --rm runner pytest tests/lab --ignore=tests/lab/test_isolation.py -m lab

lab-up:
	$(COMPOSE) build runner
	$(COMPOSE) up -d --build --wait db vulnapp modsec-pl1 modsec-pl2 modsec-pl3 modsec-pl4

lab-down:
	$(COMPOSE) --profile tools down -v

modsec-baseline:
	$(COMPOSE) run --rm runner python scripts/modsec_baseline.py

operator-preservation:
	$(COMPOSE) run --rm runner python scripts/operator_preservation.py

endpoints-doc:
	PYTHONPATH=lab/vulnapp uv run python -m vulnapp.docs > lab/vulnapp/ENDPOINTS.md

smoke:
	$(call not_implemented,smoke,F1-T14)

verify-splits:
	$(call not_implemented,verify-splits,F1-T13)

run:
	$(call not_implemented,run,F2)
