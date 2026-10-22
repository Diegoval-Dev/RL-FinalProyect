# Fase 2 — Infraestructura experimental y atacante clásico

| | |
|---|---|
| **Dueño** | Daniel Dubón |
| **Semanas** | 4–6 |
| **Recibe** | Tag `v0.1-fase1` + [HANDOFF-1](../05-handoffs/handoff-1-diego-a-daniel.md) (única dependencia) |
| **Entrega** | Tag `v0.2-fase2` + [HANDOFF-2](../05-handoffs/handoff-2-daniel-a-joaquin.md) |
| **Contratos que implementa** | [métricas](../02-contratos/metricas.md), [experimentos](../02-contratos/experimentos.md), `Agent` y checkpoints de [agentes](../02-contratos/agentes-y-checkpoints.md) |
| **Contratos que consume** | [env-atacante](../02-contratos/env-atacante.md), [operadores](../02-contratos/operadores-mutacion.md), [datos y splits](../02-contratos/datos-y-splits.md) |
| **Experimentos** | EXP-A1, A2, B1, C1, D1, D2 ([catálogo](../07-experimentos/catalogo.md)) |
| **Responde** | RQ1 |

## Objetivo

Construir la maquinaria con la que el resto del proyecto corre y mide experimentos, y usarla para responder RQ1: qué tan vulnerable es ModSecurity a un atacante que aprende con los métodos de las semanas 2 a 6 del curso. Publicar `ATK-REF-0`, el primer atacante de referencia congelado.

## Tareas

### F2-T01 — Aceptación del relevo
- **Hacer:** correr el checklist de aceptación de HANDOFF-1 en una máquina distinta a la de Diego.
- **Aceptación:** checklist marcado y firmado en el handoff dentro de la ventana de 1 día. Problemas encontrados se reportan a Diego en esa ventana.

### F2-T02 — Interfaz `Agent` y checkpoints
- **Hacer:** `wafarena/agents/base.py` con `Agent`, `Transition`, `strip_ground_truth`, `save`/`load`, `load_checkpoint` y verificación de `contract_versions`, según el [contrato](../02-contratos/agentes-y-checkpoints.md).
- **Aceptación:** prueba de ida y vuelta (guardar y cargar) para un agente de prueba; prueba que falla al cargar un checkpoint con versión MAYOR distinta; prueba estática que busca accesos a claves `gt_` dentro de `wafarena/agents/` y falla si encuentra alguno.

### F2-T03 — Runner de experimentos
- **Requiere:** F2-T02.
- **Hacer:** `wafarena/run.py` según el [contrato de experimentos](../02-contratos/experimentos.md): validación de YAML, rechazo de splits de prueba en entrenamiento, verificación de `exp_id` contra el catálogo, árbol de resultados, `meta.yaml`, TensorBoard, guardado del mejor checkpoint en `val`, negativa a correr con cambios sin commit. `make summarize EXP=...`.
- **Aceptación:** dos ejecuciones con la misma semilla de un agente tabular producen `eval.csv` idénticos; prueba de rechazo de `split: test` en entrenamiento.

### F2-T04 — Métricas, estadística y suites de evaluación
- **Requiere:** F2-T02.
- **Hacer:** `wafarena/eval/metrics.py`, `stats.py` y `harness.py` con todas las métricas y suites del [contrato](../02-contratos/metricas.md).
- **Aceptación:** prueba por métrica con un caso de valor conocido calculado a mano; prueba del bootstrap con una distribución conocida; las suites producen exactamente los mismos episodios en dos corridas.

### F2-T05 — Bandits (EXP-A1, EXP-A2)
- **Requiere:** F2-T03, F2-T04.
- **Hacer:** envoltorio de bandit sobre `Attacker-v0` (definido en el catálogo); greedy, ε-greedy, inicialización optimista, UCB; actualización por promedio muestral y por paso constante; cálculo de μ* fuera de línea para el regret.
- **Aceptación:** runs de EXP-A1 y EXP-A2 con 10 semillas registrados; figuras de regret y de recompensa media generadas por script.

### F2-T06 — MDP abstracto y programación dinámica (EXP-B1)
- **Requiere:** F2-T03.
- **Hacer:** estimar `P(s'|s,a)` y `R(s,a)` sobre los 120 estados abstractos con al menos 200 000 transiciones de una política aleatoria contra `modsec-pl1`; value iteration y policy iteration; evaluar en `Attacker-v0` la política greedy resultante usando `info["abstract_state"]`.
- **Aceptación:** ambas convergen a la misma política (o se documenta por qué no); tabla con iteraciones hasta convergencia y ER de la política en `attacker-eval-v1`. El informe declara que es una cota bajo un modelo aproximado.

### F2-T07 — Monte Carlo (EXP-C1)
- **Requiere:** F2-T03.
- **Hacer:** control Monte Carlo con política ε-soft, variantes first-visit y every-visit, sobre el estado abstracto.
- **Aceptación:** runs registrados con 10 semillas; curva de ER en `val` contra pasos.

### F2-T08 — TD: SARSA, Q-learning y TD(λ) (EXP-D1, EXP-D2)
- **Requiere:** F2-T03.
- **Hacer:** SARSA y Q-learning tabulares; SARSA(λ) con trazas de elegibilidad.
- **Aceptación:** EXP-D1 registra, además de ER, la tasa de rotura BRK durante el entrenamiento para mostrar el efecto *cliff* (romper el payload); EXP-D2 con λ ∈ {0, 0.5, 0.9}.

### F2-T09 — Tabla de vulnerabilidad de ModSecurity (RQ1)
- **Requiere:** F2-T05 a F2-T08.
- **Hacer:** evaluar el mejor checkpoint de cada método contra `modsec-pl1` … `pl4` con `attacker-eval-v1`; comparar contra `random-mutation` y `corpus-replay`.
- **Aceptación:** `results/summary/RQ1_table.csv` con ER, QFE y DIV por método y PL, con IC 95 %.

### F2-T10 — Publicar `ATK-REF-0`
- **Requiere:** F2-T09.
- **Hacer:** elegir el mejor atacante tabular por ER en `val` contra `modsec-pl1`, copiarlo a `checkpoints/refs/ATK-REF-0/`, agregar `ATK-REF-0` a `defender-eval-v1` (cambio MENOR del contrato de métricas).
- **Aceptación:** `load_checkpoint("checkpoints/refs/ATK-REF-0")` funciona; `AttackerDriver` lo usa dentro de `Defender-v0` sin errores en 100 sesiones.

### F2-T11 — Capítulo del informe y handoff
- **Hacer:** `report/capitulos/04-atacante-clasico.md` (RQ1) y la sección de protocolo experimental en `03-laboratorio.md` (runner, semillas, estadística); completar HANDOFF-2; crear el tag.
- **Aceptación:** checklist de [DoD de fase](../04-metodologia-ai-first/definicion-de-terminado.md#fase) completo.

## Riesgos de esta fase

| Riesgo | Mitigación |
|---|---|
| El estado abstracto es demasiado pobre y los tabulares no aprenden nada útil | Es un resultado válido para RQ1 si se mide bien; documentarlo. Se puede agregar una cubeta extra de "operador anterior" como variante con ADR, sin cambiar el contrato del entorno |
| El regret necesita μ* y el entorno no es exactamente estacionario | μ* se estima fuera de línea con semilla fija y se declara la aproximación |
| Runs largos | Los tabulares son baratos; si algo pasa de 30 minutos, revisar el caché del backend antes de bajar pasos |

## Estado

- [x] F2-T01 Aceptación del relevo
- [x] F2-T02 Interfaz `Agent` y checkpoints
- [ ] F2-T03 Runner
- [x] F2-T04 Métricas y suites
- [ ] F2-T05 Bandits
- [ ] F2-T06 MDP abstracto y DP
- [ ] F2-T07 Monte Carlo
- [ ] F2-T08 TD
- [ ] F2-T09 Tabla RQ1
- [ ] F2-T10 `ATK-REF-0`
- [ ] F2-T11 Informe y handoff

## Hallazgos

- **F2-T01 (heredado de F1-T12):** `gym.make("WafArena/Attacker-v0", backend="fast", defender={...})` y `Defender-v0` con `backend="fast"` / `attacker="corpus_replay"` no funcionaban como lo documentan los contratos (los entornos solo aceptaban objetos). Corregido en esta fase con `wafarena/envs/resolve.py`; los tipos `checkpoint` y `pool` lanzan `NotImplementedError` hasta F2-T02/T10. El contrato no cambia (el código se alineó con él).
- **F2-T01 (hallazgo, afecta F2-T10):** `AttackerDriver` y `DefenderDriver` figuran como entregados en HANDOFF-1 §2 y en el contrato de agentes, pero no existen en el código (`grep` sin resultados). Hay que implementarlos antes de usar `ATK-REF-0` dentro de `Defender-v0`; `{"type": "checkpoint"|"pool"}` sigue lanzando `NotImplementedError` hasta entonces.
- **F2-T02:** el contrato nombra las versiones en `meta.yaml` como `env_attacker`, `operators`, `features`, distintos de las claves de `wafarena.CONTRACT_VERSIONS`; `wafarena/agents/base.py` mantiene la correspondencia (`META_CONTRACT_KEYS`). `pyyaml` pasó a dependencia de runtime.
- **F2-T04:** `DefenderEnv` usaba un solo `split` para sesiones benignas y payloads de ataque, lo que impedía las suites `family` y `hard`. Se agregó `attack_split` y `options` (`base_id`, `session_id`) en `reset` (contrato env-defensor 1.1, compatible). Además `RandomMutationAttacker` podía sortear presupuesto 0 y producir una sesión de ataque sin requests, que rompía `DefenderEnv.reset`; ahora envía entre 1 y 5 requests. `ATK-REF-0` se agrega a `defender-eval-v1` en F2-T10.
