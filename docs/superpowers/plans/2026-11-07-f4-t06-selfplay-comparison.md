# F4-T06 Self-play Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete EXP-I1 with eight-generation naive and pool self-play runs over three paired seeds, and produce auditable TPR comparisons.

**Architecture:** Reuse F4-T05 for training and fixed validation. Add a report module and CLI that check run completeness, evaluate earlier attacker checkpoints on `val`, summarize seed curves, and plot the required TPR comparison.

**Tech Stack:** Python, PyTorch, Gymnasium, Docker lab, pandas/matplotlib, pytest.

**Spec:** `docs/superpowers/specs/2026-11-07-f4-t06-selfplay-comparison-design.md`

## Global constraints

- Both conditions use `ATK-REF-1` and `DEF-REF-1`, seeds 0–2, eight generations, and identical budgets and validation references; only current-opponent probability differs.
- Use `train` for training and `val` for all EXP-I1 comparisons. Preserve run IDs and git SHA in every output row.
- Do not infer a robustness benefit from a short smoke or a flat/undefined TPR curve.

## Tasks

### 1. Configurations and runner usability

- [ ] Add `configs/selfplay/exp_i1_naive.yaml` and `exp_i1_pool.yaml`; add tests asserting only run name and pool probability differ, and that each budget crosses the reference learning thresholds.
- [ ] Add a CLI target/documented commands for running one condition and seed at a time, so interrupted seeds resume independently.
- [ ] Run config tests and commit.

### 2. Read-only EXP-I1 report

- [ ] Add `wafarena/selfplay/report.py` and `scripts/summarize_i1.py`; tests first for missing generations, mixed SHA, malformed metrics, fixed-reference extraction, historical opponent evaluation, and deterministic seed aggregation.
- [ ] Write `results/summary/EXP-I1_runs.csv`, `EXP-I1_curve.csv`, `EXP-I1_history.csv`, and `report/figuras/EXP-I1_tpr.png` from completed runs; historical cell cache is keyed by run, defender generation, and earlier attacker generation.
- [ ] Run focused tests and commit.

### 3. Experiment and acceptance

- [ ] Run one seed for each condition, inspect checkpoints and metrics, then complete all three paired seeds and eight generations using clean code.
- [ ] Run report command; verify row counts, provenance, and figure; run `make lint` and `make test`.
- [ ] Record measured results and limitations in the Phase 4 findings and experiment register, mark F4-T06 complete, and commit in English.

## Review focus

- Historical evaluation must load an attacker checkpoint from the *same* run and an earlier generation only.
- A report must fail on incomplete runs or divergent code SHA rather than silently omit them.
- Per-seed curves must stay visible; the 95% CI is over three seed values, not individual requests.
- Undefined TPR due to zero attack requests must remain undefined and be reported.
- Re-running the report must not mutate generation markers or checkpoints.
