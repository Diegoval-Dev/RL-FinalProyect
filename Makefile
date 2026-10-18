.PHONY: setup lint test test-lab lab-up lab-down smoke run verify-splits

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

test-lab:
	uv run pytest tests/lab -m lab

lab-up:
	$(call not_implemented,lab-up,F1-T02)

lab-down:
	$(call not_implemented,lab-down,F1-T02)

smoke:
	$(call not_implemented,smoke,F1-T14)

verify-splits:
	$(call not_implemented,verify-splits,F1-T13)

run:
	$(call not_implemented,run,F2)
