# Contrato: entorno del atacante `WafArena/Attacker-v0`

**Versión:** 1.1 · **Implementa:** Fase 1 (F1-T12), Fase 3 (F3-T08) · **Archivo:** `wafarena/envs/attacker_env.py`

## Episodio

Un episodio es un intento de evadir al defensor partiendo de un payload base. Termina con evasión, ban o presupuesto agotado.

## Construcción

```python
gymnasium.make(
    "WafArena/Attacker-v0",
    backend="fast",                 # "fast" | "real"
    defender={"type": "modsec", "paranoia_level": 1},   # o {"type": "checkpoint", "path": "..."}
    split="train",                  # "train" | "val" | "test" | "test-family"
    query_budget=50,
    ban_threshold=10,
    max_steps=150,
    families=None,                  # None = todas las del split
)
```

`defender={"type": "checkpoint", "path": ...}` acepta la ruta de un checkpoint de defensor o el id de una referencia publicada en `checkpoints/refs/` (`DEF-REF-1`); se usa a través de `DefenderDriver` ([agentes](agentes-y-checkpoints.md)), de forma voraz. En cada `SEND` el defensor recibe las 37 features de `Defender-v0` ([features](features.md)): las del request, los scores de ModSecurity y las de sesión y ventana de los envíos anteriores del mismo episodio (el episodio es una sesión). `ModSecDefender` solo lee los scores, así que su comportamiento no cambia.

`reset(seed=..., options={"base_id": ..., "endpoint": ...})` acepta fijar el payload base y el endpoint; si no se fijan, se muestrean con el RNG del entorno.

## Observación

`Box(low=0, high=1, shape=(288,), dtype=float32)`

| Rango | Tamaño | Contenido |
|---|---|---|
| 0–255 | 256 | Hashing de n-gramas de caracteres (n = 1, 2, 3) del payload actual, conteos normalizados por L2 |
| 256–279 | 24 | Ventana de las últimas 4 respuestas, one-hot de 6 clases cada una; índice 256 es la más reciente |
| 280 | 1 | Mutaciones aplicadas en el episodio / `max_steps` |
| 281 | 1 | Consultas usadas / `query_budget` |
| 282 | 1 | Bloqueos acumulados / `ban_threshold` |
| 283–287 | 5 | One-hot de la familia del payload base |

Clases de respuesta (lo que el atacante puede observar desde fuera del defensor):

| Índice | Clase | Cuándo |
|---|---|---|
| 0 | `NONE` | Todavía no envió nada |
| 1 | `PASS_EFFECT` | Pasó y el efecto es visible (canario filtrado). Termina el episodio |
| 2 | `PASS_NO_EFFECT` | Respuesta 200 sin efecto visible. Incluye el honeypot: el atacante no puede distinguirlo |
| 3 | `BLOCKED` | 403 |
| 4 | `CAPTCHA` | Página de captcha; un bot no la resuelve |
| 5 | `RATE_LIMITED` | 429 |

## Estado abstracto (para métodos tabulares)

`info["abstract_state"]` es un entero en `[0, 120)`:

```
abstract_state = family_idx * 24 + last_response_idx * 4 + mutation_bucket
mutation_bucket: 0 → 0 mutaciones, 1 → 1–2, 2 → 3–5, 3 → 6 o más
```

Implementado en `wafarena/envs/abstract_state.py` con pruebas de que la función es biyectiva sobre sus rangos.

## Acciones

`Discrete(17)`

| Acción | Significado |
|---|---|
| 0–15 | Aplicar el operador de mutación con ese índice ([registro](operadores-mutacion.md)). La posición se elige con el RNG del entorno |
| 16 | `SEND`: enviar el payload actual al defensor |

## Dinámica y recompensas

| Evento | Recompensa | Efecto |
|---|---|---|
| Mutación aplicada y el payload sigue funcional | −0.1 | El payload cambia |
| Mutación no aplicable (el payload no cambia) | −0.1 | `info["noop"] = True` |
| Mutación que rompe el payload (oráculo directo: `functional = False`) | −0.1 − 5 = −5.1 | El payload **vuelve** a su versión anterior; `info["broken"] = True` |
| `SEND` y el defensor permite con efecto confirmado | +10 | `terminated = True`, `info["evaded"] = True` |
| `SEND` y respuesta `BLOCKED`, `CAPTCHA` o `RATE_LIMITED` | −1 | Suma 1 a bloqueos |
| `SEND` y respuesta `PASS_NO_EFFECT` (incluye honeypot) | −1 | Si fue honeypot, todos los envíos restantes del episodio van al honeypot |
| Bloqueos ≥ `ban_threshold` | 0 adicional | `terminated = True`, `info["banned"] = True` |
| Consultas = `query_budget` o pasos = `max_steps` | 0 adicional | `truncated = True` |

La reversión tras romper el payload es deliberada: replica la estructura del *cliff walking* de Sutton y Barto y es la base del experimento EXP-D1 (SARSA contra Q-learning).

**Simplificación declarada:** la verificación de funcionalidad tras cada mutación usa el oráculo contra `vulnapp` sin WAF y no consume consultas. Equivale a que el atacante tenga una copia local del objetivo. Se declara como limitación en el informe.

## `info`

| Clave | Tipo | Notas |
|---|---|---|
| `abstract_state` | int | Permitida para políticas tabulares |
| `payload` | str | Texto actual |
| `base_id`, `family`, `endpoint` | str | |
| `response` | int | Última clase de respuesta |
| `queries_used`, `blocks`, `mutations` | int | |
| `noop`, `broken`, `evaded`, `banned` | bool | |
| `gt_defender_action` | int | **Verdad de terreno.** Acción real del defensor (puede ser `HONEYPOT`). Prohibida para políticas |
| `gt_oracle` | dict | **Verdad de terreno.** Resultado completo del oráculo. Prohibida para políticas |

Toda clave que empieza con `gt_` es solo para evaluación y registro. El runner la elimina antes de pasar `info` al agente ([agentes](agentes-y-checkpoints.md)).

## Determinismo

Con el mismo `seed`, el mismo defensor determinista y el backend `fast` con caché, dos ejecuciones producen trayectorias idénticas. F1-T12 lo prueba.

## Historial

- 1.0 — versión inicial.
- 1.1 — Defensor `{"type": "checkpoint"}` implementado (ruta o id de referencia, vía `DefenderDriver`) y features de sesión y ventana en la observación que recibe el defensor (antes iban en cero). Compatible hacia atrás: `ModSecDefender` no las usa (F3-T08).
