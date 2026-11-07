# F4-T06 Self-play Comparison Design

## Intent

Test EXP-I1 and H3: whether a defender trained against a pool retains detection against earlier attacker generations better than one trained only against the latest attacker. Deliver eight-generation runs for both conditions with at least three paired seeds, a reproducible summary, and a TPR figure against `ATK-REF-0` and `ATK-REF-1`.

## Constraints and approach

Use the merged F4-T05 runner, the same initial `ATK-REF-1` and `DEF-REF-1` checkpoints, the frozen `train` and `val` splits, and one YAML per condition. The conditions differ only in `pool.current_probability`: 1.0 for the latest-opponent baseline and 0.5 for the historical pool. Both use seeds 0, 1, and 2; eight generations; three attacker iterations of 512 steps and one defender iteration of 1024 steps per generation. This gives PPO at least one update per generation and carries DQN past its 5000-step learning start. Each generation evaluates 40 attacker episodes per fixed defender and 40 defender sessions per fixed attacker. These budgets balance a real training signal against the cost of six complete runs; uncertainty and low event counts must be reported.

The runner already saves fixed-reference metrics in generation markers. A separate, read-only report command validates all six completed runs and their provenance, extracts per-seed TPR, FPR, and ER curves, and evaluates each defender generation against every *earlier* attacker generation from the same run on the same `val` session plan. It writes raw and seed-aggregated CSVs plus the required fixed-reference TPR figure. Historical comparisons belong to EXP-I1; the full all-pairs heatmap is F4-T07.

## Alternatives considered

Changing checkpoint format or adding a new training loop would duplicate F4-T05 and risk unequal conditions. Evaluating earlier attackers inside every generation would make interrupted runs redo expensive comparisons. The report command can resume historical cells from recorded results and leaves training checkpoints untouched.

## Acceptance

All 48 generation markers and 96 checkpoints exist with clean matching code SHA and exact configuration; all fixed-reference metrics and historical comparisons are present; two conditions differ only by opponent sampling; the figure plots seed means and uncertainty for both fixed attackers; the experiment register states the measured outcome and limitations. No `test` or `test-hard` data is used.
