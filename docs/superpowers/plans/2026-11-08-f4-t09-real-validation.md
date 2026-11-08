# F4-T09 Real Backend Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce paired fast-versus-real EXP-R1 evaluations and an auditable per-metric GAP table.

**Architecture:** Build frozen reduced attacker and defender plans from explicit evaluation seeds, load the four fixed checkpoints, run the same plans in both backends, save validated cells, then aggregate absolute paired gaps. The Docker lab supplies the real backend.

**Tech Stack:** Python, Gymnasium, Docker Compose, pytest, YAML, CSV.

**Spec:** `docs/superpowers/specs/2026-11-08-f4-t09-real-validation-design.md`

## Global Constraints

- Use only `test` for EXP-R1; no checkpoint selection or training.
- Three evaluation seeds; 50 attacker episodes and 500 defender sessions per seed and policy.
- Preserve checkpoint hashes, source runs, plan hashes, and a clean evaluation SHA.
- GAP is absolute, paired by seed, with undefined metrics left blank.

## Review Focus

- Reject checkpoint or champion identity mismatches before evaluation.
- Reject stale cached cells with different plans, hashes, modes, or incomplete counts.
- Preserve the same initial payload/session IDs and seeds in both modes.
- Count empty attack sessions explicitly and exclude them consistently.
- Never present evaluation-seed intervals as training-seed uncertainty.

### Task 1: Frozen plans and GAP aggregation

**Files:** `wafarena/eval/real_gap.py`, `configs/eval/EXP-R1/real-validation.yaml`, `tests/unit/test_real_gap.py`.

- [x] Write failing tests for 50-episode blocks, 500-session plans, pairing, empty/undefined metrics, and absolute GAP aggregation.
- [x] Implement plan generation and aggregation with exact config validation.
- [x] Run focused tests, lint, and commit in English.

### Task 2: Runner and cache

**Files:** `scripts/run_r1.py`, `Makefile`, `tests/unit/test_r1_script.py`.

- [x] Write failing tests for source provenance, plan fingerprints, cache validation, and mode routing.
- [x] Implement checkpoint-only runner, atomic per-cell records, summary CSVs, and `make real-gap`.
- [x] Run focused tests, lint, full unit suite, and commit in English.

### Task 3: Execute and document EXP-R1

**Files:** `results/summary/EXP-R1_cells.csv`, `EXP-R1_gap.csv`, `docs/03-plan/fase-4-nelson-planning-selfplay.md`, `docs/07-experimentos/registro.md`, `report/capitulos/07-generalizacion.md`.

- [x] Run all 24 clean cells against fast and real backends; inspect denominators and undefined metrics.
- [x] Rerun from cache and verify byte-identical summaries, cells, and source checkpoint hashes.
- [x] Record measured gaps and limitations, mark F4-T09 complete, run final checks, and commit evidence in English.
