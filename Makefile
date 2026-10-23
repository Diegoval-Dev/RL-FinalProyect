.PHONY: setup lint test test-lab lab-up lab-down smoke run summarize verify-splits build-splits endpoints-doc modsec-baseline

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
	$(COMPOSE) up -d --build --wait db vulnapp honeypot proxy modsec-pl1 modsec-pl2 modsec-pl3 modsec-pl4

lab-down:
	$(COMPOSE) --profile tools down -v

modsec-baseline:
	$(COMPOSE) run --rm runner python scripts/modsec_baseline.py

operator-preservation:
	$(COMPOSE) run --rm runner python scripts/operator_preservation.py

bandit-arm-means:
	$(COMPOSE) run --rm runner python scripts/bandit_arm_means.py

evasion-reachability:
	$(COMPOSE) run --rm runner python scripts/evasion_reachability.py

endpoints-doc:
	PYTHONPATH=lab/vulnapp uv run python -m vulnapp.docs > lab/vulnapp/ENDPOINTS.md

smoke: lab-up
	$(COMPOSE) run --rm runner python scripts/smoke.py

verify-splits:
	uv run python scripts/verify_splits.py

build-splits:
	VERIFIED_COMMIT=$$(git rev-parse --short HEAD) uv run python scripts/build_splits.py

run: lab-up
	@test -n "$(CONFIG)" || { echo "usage: make run CONFIG=configs/exp/<file>.yaml" >&2; exit 1; }
	$(COMPOSE) run --rm runner python -m wafarena.run --config $(CONFIG) $(RUN_ARGS)

summarize:
	@test -n "$(EXP)" || { echo "usage: make summarize EXP=<exp_id>" >&2; exit 1; }
	uv run python -m wafarena.summarize --exp $(EXP)
