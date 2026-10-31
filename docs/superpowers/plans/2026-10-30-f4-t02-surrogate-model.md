# F4-T02 Surrogate Model Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train an incremental surrogate of an attacker-visible `SEND` response and report validation accuracy and calibration against `modsec-pl1` and `DEF-REF-1`.

**Architecture:** Use the first 256 ngram features of `Attacker-v0` observations. A five-logit PyTorch classifier predicts `Response` values 1–5; `NONE` is never a `SEND` result. A linear layer is multinomial logistic regression; an optional 32-unit hidden layer provides the small MLP. A separate evaluator collects labeled `SEND` examples through the public environment on frozen `train` and `val` splits, trains only on `train`, and writes one provenance-bearing result per defender and variant.

**Tech Stack:** Python 3.11, NumPy, CPU PyTorch already in `pyproject.toml`, PyYAML, Gymnasium, pytest.

**Spec:** `docs/03-plan/fase-4-nelson-planning-selfplay.md` §F4-T02; `docs/02-contratos/env-atacante.md` §Observación and §`info`.

## Global Constraints

- Use `np.random.Generator` and explicit seeds for data collection; model initialization must not perturb global PyTorch RNG state.
- Hyperparameters and episode budgets for the validation run live in YAML.
- Read only the public `info["response"]` label; never use `gt_*` in the model or collector.
- Keep validation data out of incremental updates and keep `test` splits unused.
- Record `run_id`, commit, seed, configuration, class counts, accuracy, expected calibration error, and multiclass Brier score for each defender and variant.
- Use English commit messages as requested by Nelson; do not push directly to `main`.

## Review Focus

- Empty or malformed observation: reject before passing data to PyTorch.
- `Response.NONE` or out-of-range label: reject as an invalid `SEND` target.
- Unseen response classes in `train`: probabilities remain finite and sum to one.
- Empty validation set: raise a clear error rather than reporting undefined calibration.
- `DEF-REF-1` may respond differently to the same payload by session length; report its measured metrics without treating the 256-feature classifier as a perfect defender replica.

---

### Task 1: Incremental classifier and metric functions

**Files:**
- Create: `wafarena/agents/dyna/__init__.py`
- Create: `wafarena/agents/dyna/surrogate.py`
- Test: `tests/unit/test_surrogate.py`

**Interfaces:**
- `SurrogateModel(*, hidden_dim: int | None, learning_rate: float, seed: int)`
- `predict_proba(obs: np.ndarray) -> np.ndarray`: five probabilities ordered as `Response` 1–5.
- `predict_response(obs: np.ndarray) -> Response`
- `update(obs: np.ndarray, response: int | Response) -> float`: one cross-entropy SGD step; returns loss.
- `calibration_metrics(probabilities: np.ndarray, responses: np.ndarray, *, bins: int = 10) -> dict[str, float]`: `accuracy`, `ece`, `brier`.

- [x] Add failing tests for synthetic separable classes, optional MLP, probability normalization, deterministic initialization, input validation, and a hand-calculated calibration example.
- [x] Run `uv run pytest tests/unit/test_surrogate.py -q`; confirm failures come from the missing implementation.
- [x] Implement the minimal classifier and metric functions; accept both 256- and 288-dimensional observations but use only the first 256 features.
- [x] Run `uv run pytest tests/unit/test_surrogate.py -q`; require all tests to pass.

### Task 2: Reproducible train/val collection and run report

**Files:**
- Create: `wafarena/agents/dyna/evaluation.py`
- Create: `scripts/eval_surrogate.py`
- Create: `configs/surrogate/f4_t02.yaml`
- Modify: `Makefile`
- Test: `tests/unit/test_surrogate_evaluation.py`

**Interfaces:**
- `collect_send_examples(backend, defender, *, split: str, episodes: int, seed: int) -> tuple[np.ndarray, np.ndarray]`: captures the pre-`SEND` ngram observation and the subsequent public response.
- `evaluate_surrogate(config_path: Path, *, results_root: Path) -> Path`: trains each configured variant and writes `meta.yaml` plus `validation.csv` under `results/F4-T02/`.
- `make surrogate-eval`: starts the lab, then runs `scripts/eval_surrogate.py` in the runner.

- [x] Add failing unit tests for split separation, explicit episode seeds, no `gt_*` access, class counts, and stable CSV columns.
- [x] Run `uv run pytest tests/unit/test_surrogate_evaluation.py -q`; confirm expected failures.
- [x] Implement the collector and evaluator with YAML budgets, two named defenders, and the project's run metadata helpers.
- [x] Run focused tests, then `make lint && make test`.
- [x] Commit code, tests, config, Makefile, and this plan with an English `feat(F4-T02): ...` message before recording lab results.

### Task 3: Validation run and task documentation

**Files:**
- Generate: `results/F4-T02/.../meta.yaml` and `validation.csv` (raw results remain ignored)
- Generate: `results/summary/F4-T02_surrogate.csv`
- Modify: `docs/03-plan/fase-4-nelson-planning-selfplay.md`
- Modify: `docs/07-experimentos/registro.md`

- [x] Run the evaluator with committed code and a clean guarded tree; collect `train` and `val` samples for `modsec-pl1` and `DEF-REF-1` using seed 0.
- [x] Verify both variants have finite accuracy, ECE, and Brier results; verify metadata names the commit and the result rows include the run ID and class counts.
- [x] Record measured `val` metrics and the 256-feature limitation in the Phase 4 findings and experiment register; mark F4-T02 complete only when the acceptance run is valid.
- [x] Run `make lint && make test` and `git diff --check`; commit generated summary and documentation with an English `exp(F4-T02): ...` message.
