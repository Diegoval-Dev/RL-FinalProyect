# F4-T05 Self-play Orchestrator

## Design

Use the existing `Attacker-v0`, `Defender-v0`, trainer, checkpoint format, and fixed validation data. A generation trains the attacker for three configured iterations against a per-episode mix of the current defender (probability 0.5) and uniformly sampled historical defenders, then trains the defender for one configured iteration against the analogous attacker mix. Save both trained agents, then evaluate both against fixed references on `val`. The initial agents are `ATK-REF-1` and `DEF-REF-1`. No PettingZoo layer is needed because the existing Gym environments and policy drivers already define both sides of a match.

The runner records a completed generation only after both checkpoints and its evaluation are durable. On restart, it loads the last completed pair, including replay, rollout, optimizer, and random generator state, and repeats any interrupted generation. A run uses one YAML config, explicit seeds, a git SHA, and per-generation opponent and metric records. In-progress work within an interrupted generation is repeated from its beginning.

## Files and tasks

1. **Config and opponent selection.** Add `wafarena/selfplay/config.py`, `wafarena/selfplay/pool.py`, and `configs/selfplay/f4_t05_smoke.yaml`. Validate all steps, seed lists, paths, ratios, and generation count before writing. Test seeded per-episode 0.5/current versus uniform/history selection, including the first generation with no history.
2. **Generation runner and resume.** Add `wafarena/selfplay/orchestrator.py`, `wafarena/selfplay/state.py`, and `scripts/run_selfplay.py`. Reuse `train`, `load_checkpoint`, `save_checkpoint`, and `runmeta`; write checkpoints and their learning-state sidecars to `checkpoints/selfplay/<run_id>/{atk,def}-gen-XX/`. Test the three attacker iterations to one defender iteration, checkpoint provenance, completed-generation markers, and resume after interruption without replaying earlier generations. Keep the three attacker iterations within one continuous trainer call so a PPO rollout never crosses an artificial environment reset.
3. **Fixed-reference validation.** Add `wafarena/selfplay/evaluation.py`. Evaluate attacker against PL1–PL4 and `DEF-REF-1`; defender against `corpus-replay`, `random-mutation`, `ATK-REF-0`, and `ATK-REF-1`, always on `val` with configured, fixed sample counts and seeds. Reload the attacker's policy for each reference so its stochastic evaluation stream starts identically for every comparison. Test that evaluation happens after every generation and that opponent results are saved separately.
4. **Smoke and acceptance.** Run a two-generation smoke end to end, interrupt and resume a run, run `make lint`, `make test`, and the project smoke gate as relevant. Record measured run identity and outcome in the Phase 4 findings and experiment register; mark F4-T05 complete only after all acceptance checks pass.

## Acceptance checks

- Two generations produce both checkpoints and fixed-reference evaluations.
- Seeded opponent sampling selects the current checkpoint with probability 0.5 and each historical checkpoint with equal share of the other 0.5.
- Resume starts at the first incomplete generation and rejects a changed config or code revision.
- The existing checkpoint and environment contracts remain compatible.
