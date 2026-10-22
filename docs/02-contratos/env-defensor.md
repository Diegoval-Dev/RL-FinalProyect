# Contrato: entorno del defensor `WafArena/Defender-v0`

**Versión:** 1.1 · **Implementa:** Fase 1 (F1-T12) · **Archivo:** `wafarena/envs/defender_env.py`

## Episodio

Un episodio es una sesión de tráfico. El defensor no sabe si es benigna o maliciosa. Cada paso es un request de la sesión.

## Construcción

```python
gymnasium.make(
    "WafArena/Defender-v0",
    backend="fast",
    attacker={"type": "corpus_replay"},     # "corpus_replay" | "random_mutation" | {"type": "checkpoint", "path": ...} | {"type": "pool", "paths": [...], "weights": [...]}
    split="train",                          # sesiones benignas (y payloads base si no se da attack_split)
    attack_split=None,                      # opcional: split de los payloads base de ataque; None = igual a split
    attack_ratio=0.1,                       # fracción de sesiones maliciosas
    reward={"alpha": 4.0, "beta": 1.0, "gamma": 0.5},
    benign_abandon_prob=0.0,                # prob. de que un usuario benigno bloqueado abandone la sesión
)
```

`reset(seed=..., options={"base_id": ...})` fija la sesión de ataque sobre ese payload base; `options={"session_id": ...}` fija una sesión benigna. Son excluyentes; sin opciones, el tipo y la sesión se muestrean con el RNG del entorno. Un id fuera del split lanza `ValueError`.

## Observación

`Box(low=0, high=1, shape=(37,), dtype=float32)`. Definición exacta de cada feature en [features.md](features.md).

| Rango | Tamaño | Bloque |
|---|---|---|
| 0–11 | 12 | Features del request |
| 12–15 | 4 | Anomaly score de ModSecurity en PL1, PL2, PL3, PL4 |
| 16–20 | 5 | Features de sesión |
| 21–36 | 16 | Ventana de los 4 requests anteriores de la sesión, 4 features cada uno |

## Acciones

`Discrete(5)`

| Acción | Nombre | Efecto sobre un usuario benigno | Efecto sobre el atacante (bot) |
|---|---|---|---|
| 0 | `ALLOW` | Pasa | Pasa |
| 1 | `BLOCK` | Denegado (403) | Denegado (403) |
| 2 | `CAPTCHA` | Lo resuelve y pasa, con fricción | No lo resuelve: denegado |
| 3 | `RATE_LIMIT` | Pasa con demora | Denegado (429) |
| 4 | `HONEYPOT` | Desviado a contenido falso | Desviado; recibe 200 sin efecto |

`HONEYPOT` termina el episodio del defensor: el resto de la sesión queda en el honeypot.

## Recompensa

Por request. Los valores por defecto son `α = 4`, `β = 1`, `γ = 0.5`.

| Acción | Benigno | Ataque con efecto (oráculo) | Ataque sin efecto |
|---|---|---|---|
| `ALLOW` | 0 | −10 | 0 |
| `BLOCK` | −α | +5 | +5 |
| `CAPTCHA` | −β | +3 | +3 |
| `RATE_LIMIT` | −γ | +2 | +2 |
| `HONEYPOT` | −α | +6 | +6 |

Un request es *ataque* si pertenece a una sesión generada por el atacante. "Con efecto" lo decide el oráculo en el momento del request (si el defensor lo dejara pasar).

El barrido de α (EXP-F5) es la base de la frontera de Pareto. Restricción: `β < α` y `γ < β` siempre.

## Terminación

- `terminated = True` al acabarse la sesión, al elegir `HONEYPOT`, o si el usuario benigno abandona (`benign_abandon_prob`).
- `truncated = True` si la sesión supera 200 requests.

## `info`

| Clave | Tipo | Notas |
|---|---|---|
| `session_id`, `request_index` | str, int | |
| `modsec_would_block` | list[bool] | Decisión de ModSecurity en PL1–PL4. Permitida (es una señal observable en producción) |
| `gt_label` | str | **Verdad de terreno**: `benign` o `attack`. Prohibida para políticas |
| `gt_effect` | bool | **Verdad de terreno**: el oráculo confirma efecto. Prohibida para políticas |
| `gt_hard_tags` | list[str] | **Verdad de terreno**: etiquetas de benigno difícil. Prohibida para políticas |

## Cómo se generan las sesiones maliciosas

El entorno usa un `AttackerPolicy` ([agentes](agentes-y-checkpoints.md)). En cada paso de una sesión maliciosa, el atacante recibe la respuesta observable del paso anterior, aplica sus mutaciones internamente y emite el siguiente request. Un agente entrenado en `Attacker-v0` se convierte en `AttackerPolicy` con `AttackerDriver` (F1), que reconstruye la observación de 288 dimensiones del atacante.

## Determinismo

Igual que en el entorno del atacante: misma semilla, mismo atacante determinista y backend `fast` producen la misma secuencia de sesiones y observaciones.

## Historial

- 1.0 — versión inicial.
- 1.1 — `attack_split` opcional en la construcción y `options` (`base_id`, `session_id`) en `reset`, para las suites de evaluación del defensor (F2-T04). Compatible hacia atrás.
