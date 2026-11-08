# F4-T08 Final Generalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reproducible EXP-I3–I5 evaluations and a final RQ5 table from the saved self-play, reference, Dyna-Q, and new PPO checkpoints.

**Architecture:** Select the final pool defender from EXP-I1 `val` history; train PPO seed 5 with the existing runner; evaluate three self-play final defenders plus fixed baselines on existing I3/I4 suites and a fixed unseen-attacker I5 session plan. Save per-cell records, aggregate over self-play seeds, and publish the summary table.

**Tech Stack:** Python, Gymnasium, PyTorch, Docker lab, pytest, YAML, CSV.

**Spec:** `docs/superpowers/specs/2026-11-08-f4-t08-final-generalization-design.md`

## Global Constraints

- Select on `val`; reserve `test` and `test-hard` for final read-only evaluations.
- Self-play source: EXP-I1 pool seed 0–2, generation 8, SHA `eea6f78`.
- New PPO: seed 5, 200 000 steps against `DEF-REF-1`, copied H1 hyperparameters, no final test evaluation during training.
- Dyna-Q: EXP-H1 Dyna-5/DEF-REF-1 seed 0, tied with the other Dyna candidates at zero validation ER.
- I5 plan: 2 000 test sessions, 10% attacks, fixed suite seed plan; report undefined metrics honestly.
- No `test` result may affect checkpoint selection.

## Review Focus

- Reject missing or mismatched checkpoint roles, run IDs, training SHAs, and seeds before evaluation.
- Reject incomplete or stale cached cells; never silently overwrite them.
- Keep identical session IDs, seeds, and suite settings across defenders for each I5 attacker.
- A baseline with one fixed checkpoint has no independent three-seed CI.
- If a Dyna-Q attack yields no requests, record the empty session and exclude it from request-based defender metrics; use the same emitting sessions for every defender.

### Task 1: Validation-only selection and new PPO configuration

**Files:** `wafarena/eval/final_generalization.py`, `configs/exp/EXP-I5/ppo-unseen-defref1.yaml`, `configs/selfplay/exp_i345.yaml`, `tests/unit/test_final_generalization.py`.

- [x] Write failing tests for three complete final pool candidates, FPR cap/fallback ranking, historical-only inputs, and Dyna tie resolution.
- [x] Implement strict selection and provenance validation; add fixed evaluation and PPO training YAMLs.
- [x] Run focused tests and config validation; commit in English.

### Task 2: I3/I4/I5 evaluator and reproducible summaries

**Files:** `wafarena/eval/final_generalization.py`, `scripts/run_i345.py`, `Makefile`, `tests/unit/test_final_generalization.py`, `tests/unit/test_i345_script.py`.

- [x] Write failing tests for suite routing, fixed I5 plan, same attacker checkpoint across defenders, cache validation, and aggregation over exactly three self-play seeds.
- [x] Implement checkpoint-only evaluation, atomic raw cells, CSV summaries, fixed PL2 baseline import, and `make generalization`.
- [x] Run focused tests, lint, full unit suite; commit in English.

### Task 3: Execute and document EXP-I3–I5

**Files:** `results/summary/EXP-I3.csv`, `EXP-I4.csv`, `EXP-I5.csv`, `RQ5_final.csv`, `docs/03-plan/fase-4-nelson-planning-selfplay.md`, `docs/07-experimentos/registro.md`.

- [x] Train clean PPO seed 5, validate its checkpoint and run metadata, then evaluate all I3–I5 cells.
- [x] Rerun from cache, verify byte-identical summaries and unchanged source checkpoint hashes; inspect all metric denominators and undefined cells.
- [x] Record measured results and limits, mark F4-T08 complete, run final lint/tests, and commit evidence in English.
