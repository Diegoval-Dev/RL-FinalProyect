# F4-T10 Dashboard and Demo Implementation Plan

**Goal:** Deliver a reproducible local Streamlit demo with real lab traffic and saved-run visualizations.

**Spec:** `docs/superpowers/specs/2026-11-08-f4-t10-dashboard-demo-design.md`

## Task 1: Data contracts and live probe

**Files:** `dashboard/data.py`, `dashboard/live.py`, `tests/unit/test_dashboard_data.py`, `tests/unit/test_dashboard_live.py`.

- [x] Test required CSV columns, source provenance, matrix shape, and missing file behavior before implementing loaders.
- [x] Test bounded live session results using an injected backend and policy before implementing the probe.
- [x] Implement loaders and live probe. No synthetic or default metrics.

## Task 2: Streamlit interface and Docker entrypoint

**Files:** `dashboard/app.py`, `dashboard/README.md`, `dashboard/docker-compose.yml`, `pyproject.toml`, `uv.lock`, `lab/Dockerfile`, `Makefile`.

- [x] Add Streamlit in a demo dependency group and a dashboard Docker target/service bound to localhost.
- [x] Build live and saved-results tabs with clear source labels and errors for absent data.
- [x] Verify `make demo` starts the lab and serves the app; manually exercise a live sample.

## Task 3: Video and completion evidence

**Files:** `dashboard/make_video.py`, `report/video/EXP-I1_arms_race.mp4`, `docs/03-plan/fase-4-nelson-planning-selfplay.md`.

- [x] Generate a short MP4 from the EXP-I1 TPR CSV and verify its source and duration.
- [x] Run lint, unit suite, relevant lab checks, inspect dashboard, and mark F4-T10 complete.
- [ ] Commit all changes with English messages.

## Review focus

- Never display hard-coded experiment metrics or a fake live event.
- Keep the lab network isolated and expose only the dashboard on host loopback.
- Do not mistake a single live demonstration session for a statistical evaluation.
