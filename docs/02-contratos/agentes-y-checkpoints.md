# Contrato: agentes, políticas y checkpoints

**Versión:** 1.1 · **Implementa:** Fase 1 (`DefenderPolicy`, `AttackerPolicy`), Fase 2 (`Agent`, checkpoints, `AttackerDriver`) y Fase 3 (`DefenderDriver`) · **Archivos:** `wafarena/defenders/base.py`, `wafarena/attackers/base.py`, `wafarena/attackers/driver.py`, `wafarena/defenders/driver.py`, `wafarena/agents/base.py`

Este contrato es lo que permite enchufar un agente entrenado por una fase como oponente en la fase siguiente sin tocar su código.

## Políticas (Fase 1)

```python
class DefenderPolicy(Protocol):
    def reset_session(self, session_id: str) -> None: ...
    def act(self, obs: np.ndarray) -> int: ...            # obs de Defender-v0, devuelve 0..4

class AttackerPolicy(Protocol):
    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None: ...
    def next_request(self, last_response: int) -> Payload | None: ...   # None = abandona la sesión
```

Implementaciones de la Fase 1: `ModSecDefender(paranoia_level)`, `CorpusReplayAttacker`, `RandomMutationAttacker`.

`AttackerDriver(agent)` convierte un `Agent` entrenado en `Attacker-v0` en un `AttackerPolicy`: mantiene internamente el payload, la ventana de respuestas y los contadores, construye la observación de 288 dimensiones y llama al agente hasta que este elige `SEND`. `DefenderDriver(agent)` hace lo mismo del lado defensor: convierte un `Agent` de `Defender-v0` en un `DefenderPolicy` que actúa de forma voraz (`explore=False`) y sin `info`; es lo que usan `Attacker-v0` con `defender={"type": "checkpoint", "path": ...}` y, en modo real, el proxy.

## Agente (Fase 2)

```python
@dataclass
class Transition:
    obs: np.ndarray
    action: int
    reward: float
    next_obs: np.ndarray
    terminated: bool
    truncated: bool
    info: Mapping[str, Any]          # sin claves gt_

class Agent(Protocol):
    agent_id: str
    role: Literal["attacker", "defender"]
    def act(self, obs: np.ndarray, info: Mapping[str, Any], *, explore: bool) -> int: ...
    def observe(self, t: Transition) -> dict[str, float]: ...   # actualiza; devuelve métricas de entrenamiento
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "Agent": ...
```

- `explore=False` en evaluación: política greedy o determinista.
- Agentes que aprenden por lotes o episodios (Monte Carlo, PPO) acumulan transiciones dentro de `observe` y actualizan cuando corresponde.
- `wafarena.agents.base.strip_ground_truth(info)` elimina toda clave `gt_*`. El runner siempre la aplica antes de `act` y `observe`. Una prueba de la Fase 2 verifica que ningún agente del paquete accede a claves `gt_`.

## Formato de checkpoint

Un directorio:

```
checkpoints/<ruta>/
├── meta.yaml
└── weights.pt | q_table.npy | params.npz
```

`meta.yaml`:

```yaml
agent_id: ATK-REF-0
role: attacker
algo: qlearning
obs_dim: 288
n_actions: 17
contract_versions: {env_attacker: "1.0", operators: "1.0", features: "1.0"}
train: {exp_id: EXP-D1, run_id: EXP-D1__qlearning-pl1__s3__abc1234, seed: 3, git_sha: abc1234}
eval_summary: {suite: attacker-eval-v1, defender: modsec-pl1, evasion_rate: <valor del run>}
created_at: 2026-11-02T18:00:00Z
```

`wafarena.agents.load_checkpoint(path)` devuelve el agente correcto según `algo` y verifica `contract_versions`.

## Referencias fijas

Oponentes congelados. Una vez publicados en su handoff, no se reentrenan ni se sobrescriben.

| ID | Rol | Qué es | Lo publica | Lo usan |
|---|---|---|---|---|
| `modsec-pl1` … `modsec-pl4` | defensor | ModSecurity en cada PL | F1 | todas |
| `corpus-replay` | atacante | Corpus `test` sin mutar | F1 | todas |
| `random-mutation` | atacante | Mutación aleatoria con el mismo presupuesto | F1 | todas |
| `ATK-REF-0` | atacante | Mejor atacante tabular contra `modsec-pl1` | F2 | F3, F4 |
| `DEF-REF-1` | defensor | Mejor defensor DQN (en `val`) | F3 | F4 |
| `ATK-REF-1` | atacante | Mejor atacante PPO contra `DEF-REF-1` | F3 | F4 |

Se guardan en `checkpoints/refs/<ID>/` y sí se versionan en git (con Git LFS si superan 50 MB).

## Historial

- 1.0 — versión inicial. `AttackerDriver` estaba documentado desde Fase 1 pero no existía en el código (ver Hallazgos de la Fase 2); se implementó en F2-T10 (`wafarena/attackers/driver.py`), sin cambiar esta interfaz.
- 1.1 — `DefenderDriver` implementado en `wafarena/defenders/driver.py` (F3-T08); se elimina `wafarena/envs/drivers.py`, un borrador de la Fase 1 que nadie importaba y cuyo `AttackerDriver` no coincidía con el real. Compatible hacia atrás.
