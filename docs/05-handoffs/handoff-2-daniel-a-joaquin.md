# HANDOFF-2: Daniel Dubón → Joaquín Puente

> Completar al cerrar la Fase 2 con el prompt [P6](../04-metodologia-ai-first/prompts.md#p6--redactar-el-handoff).

| | |
|---|---|
| **Tag** | `v0.2-fase2` (se crea en `main` tras mergear los PR de la Fase 2) |
| **Commit** | el de `main` con el tag `v0.2-fase2` |
| **Fecha de entrega** | 2026-10-23 |
| **Ventana de aceptación** | hasta 2026-10-24 (1 día hábil) |
| **Estado** | Aceptado |

## 1. Qué se entrega

El runner de experimentos (`wafarena/run.py`, `dp_run.py`, `bandit_run.py`), la interfaz `Agent` y
el formato de checkpoint, las métricas y suites de evaluación con estadística por bootstrap, seis
familias de atacante tabular entrenadas y evaluadas (bandits, programación dinámica, Monte Carlo,
SARSA, Q-learning, SARSA(λ)), la tabla de vulnerabilidad de ModSecurity que responde RQ1, y
`ATK-REF-0`, el primer atacante de referencia congelado, enchufable en `Defender-v0` vía
`AttackerDriver`. RQ1: con los 16 operadores de mutación actuales, ModSecurity no es vulnerable a
ningún método clásico en ningún nivel de paranoia (capítulo 4 del informe).

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| agentes y checkpoints | 1.0 | Versión inicial de esta fase: `Agent`, `Transition`, checkpoints, `AttackerDriver` implementado (estaba documentado desde la Fase 1 pero no existía en el código) |
| métricas | 1.2 | Métricas y suites del atacante y defensor (1.0); suite `attacker-val-v1` para selección de modelo (1.1); se agrega `ATK-REF-0` a `defender-eval-v1` (1.2) |
| experimentos | 1.1 | Formato de `run.py`, resultados y resúmenes versionados (1.0); detalle de selección de modelo en `val` y opciones de línea de comandos (1.1) |
| (heredados de la Fase 1) | sin cambios | env-atacante 1.0, env-defensor 1.1 (agregó `attack_split`/`options` en F2-T04, compatible), oráculo 1.1, operadores-mutación 1.1 (límite de una capa en `hex_string`, compatible), features 1.0, datos-y-splits 1.0 |

## 3. Cómo correrlo desde cero

```bash
make setup
make lab-up
make lint && make test
make test-lab          # requiere el laboratorio arriba
make run CONFIG=configs/exp/EXP-D1/qlearning-pl1.yaml RUN_ARGS="--seed 0"
make summarize EXP=EXP-D1
```

El runner corre dentro del contenedor `runner` del laboratorio (único con acceso a la red de
`db`/`modsec-pl1..4`/`vulnapp`), así que `make lab-up` tiene que estar arriba antes de `make run` o
`make test-lab`.

## 4. Checklist de aceptación

- [x] Todo el checklist de HANDOFF-1 sigue pasando.
- [x] `make run CONFIG=configs/exp/EXP-D1/<un yaml>.yaml` con una sola semilla corre de punta a punta y genera el árbol de resultados del contrato.
- [x] Repetir el mismo run produce un `eval.csv` idéntico.
- [x] El runner rechaza un YAML con `split: test` en entrenamiento.
- [x] `make summarize EXP=EXP-A1` regenera `results/summary/EXP-A1.csv` idéntico al versionado.
- [x] `load_checkpoint("checkpoints/refs/ATK-REF-0")` funciona y el agente corre 100 sesiones dentro de `Defender-v0` vía `AttackerDriver`.
- [x] La prueba estática de acceso a claves `gt_` pasa.

_Nota sobre el ítem de `make summarize EXP=EXP-A1` (F3-T01):_ tal como está escrito no se puede cumplir fuera de la máquina original. `results/EXP-A1/` no se versiona, así que en una máquina nueva `summarize` falla con `FileNotFoundError: no finished runs for EXP-A1`; y aunque se re-corran los runs, la columna `git_shas` del resumen registra el commit con que se corrieron (`6055362`), distinto del de quien verifica. Se verificó de la forma más fuerte posible: se re-corrieron los 70 runs (7 configuraciones × 10 semillas) con `make run-bandit ... RUN_ARGS="--results results/_f3t01_A1"` sobre `ae99905` (árbol limpio), y `python -m wafarena.summarize --exp EXP-A1 --results results/_f3t01_A1` produce un CSV con las mismas 7 filas y 29 columnas que el versionado, idénticas celda por celda salvo `git_shas` (`6055362` / `6055362+c93e655` → `ae99905`). El CSV versionado no se modificó.

## 5. Resultados entregados

| Experimento | Resumen | Hallazgo principal |
|---|---|---|
| EXP-A1 | `results/summary/EXP-A1.csv` | 7 bandits (greedy, ε-greedy, optimista, UCB, aleatorio), 10 semillas, ER = 0,000 [0,000; 0,000] y regret acumulado = 0 en los 7: la media de los 16 brazos contra `modsec-pl1`…`pl4` ya es 0 (`bandit_arm_means.csv`) |
| EXP-A2 | `results/summary/EXP-A2.csv` | Promedio muestral contra paso constante (α ∈ {0,05; 0,1; 0,3}), 10 semillas, ER = 0,000 [0,000; 0,000] en las 4; nada que recuperar al cambiar de PL porque el regret ya era 0 |
| EXP-B1 | `results/summary/EXP-B1.csv` | Value iteration (1 147 iteraciones) y policy iteration (3) sobre el MDP estimado (120 estados), 10 semillas; coinciden en 114/120 estados (6 son empates exactos de valor Q); la política óptima bajo el modelo tiene ER = 0,000 [0,000; 0,000] en `attacker-eval-v1` |
| EXP-C1 | `results/summary/EXP-C1.csv` | MC *first/every-visit* ε-soft (ε ∈ {0,05; 0,1}), 10 semillas, ER = 0,000 [0,000; 0,000] en los 4, curva plana en `val` durante todo el entrenamiento |
| EXP-D1 | `results/summary/EXP-D1.csv` | SARSA/Q-learning, `pl1`/`pl2`, 10 semillas, ER = 0,000 [0,000; 0,000] en los 4; BRK final SARSA 0,0533 vs Q-learning 0,0396 (hipótesis del catálogo sobre el efecto *cliff* no se confirma — no hay asimetría riesgo/recompensa en este entorno) |
| EXP-D2 | `results/summary/EXP-D2.csv` | SARSA(λ) con λ ∈ {0; 0,5; 0,9}, 10 semillas, ER = 0,000 [0,000; 0,000] en los 3 |
| Tabla RQ1 | `results/summary/RQ1_table.csv` | 8 métodos × 4 PL × 10 semillas = 32 celdas, ER = 0,000 [0,000; 0,000] en todas. **Respuesta a RQ1:** con los 16 operadores actuales, ModSecurity no es vulnerable a ningún método clásico en ningún nivel de paranoia; el techo está en el espacio de ataque, no en el método de aprendizaje (capítulo 4 del informe) |

## 6. Checkpoints de referencia publicados

| ID | Ruta | Cómo se eligió | ER en `attacker-eval-v1` contra `modsec-pl1` |
|---|---|---|---|
| `ATK-REF-0` | `checkpoints/refs/ATK-REF-0/` | `greedy-pl1` (EXP-A1, semilla 0): no por ER (todos los métodos empatan en 0,000) sino por ser el único que ataca de forma confiable al desplegarse de forma voraz — ver §8, sesgo de optimismo de DP/MC/TD | 0,000 [0,000; 0,000], igual que el resto de EXP-A1 |

## 7. Recortes y desviaciones del plan

- **`DefenderDriver` no se implementó.** El contrato de agentes lo documenta junto a `AttackerDriver`, pero esta fase solo necesitaba evaluar atacantes entrenados contra el defensor fijo (ModSecurity); no hace falta un defensor entrenado todavía. Queda para cuando la Fase 3 necesite evaluar un atacante contra `DEF-REF-1`. El código y el contrato ya reservan el lugar (`wafarena/attackers/driver.py` como referencia de patrón).
- **`{"type": "pool"}` en `resolve_attacker_type`/`_resolve_attacker_factory` sigue lanzando `NotImplementedError`.** Es para el *pool* de oponentes de self-play (Fase 4), no hace falta antes.
- No hubo otros recortes: las seis tareas de método (F2-T05 a F2-T08), la tabla RQ1 (F2-T09) y la publicación de `ATK-REF-0` (F2-T10) se completaron según el plan de la fase.

## 8. Problemas conocidos

- **Sesgo de optimismo en despliegue voraz.** Las políticas de DP, Monte Carlo, SARSA y SARSA(λ), desplegadas con `explore=False`, casi nunca llegan a `SEND`: con la tabla Q en cero y toda recompensa real negativa, una acción nunca visitada parece mejor que cualquiera ya explorada, así que la política se queda mutando indefinidamente (verificado contra el laboratorio real: 148–150 de 150 pasos mutando, 0–2 consultas enviadas). No afecta las cifras de ER registradas (un episodio que nunca envía tampoco evade), pero si la Fase 3 necesita desplegar uno de estos checkpoints tabulares como oponente fuera de una evaluación controlada, va a necesitar romper los empates de otra forma (por ejemplo, inicialización optimista en el despliegue, no solo en el entrenamiento).
- **El oráculo cuesta una conexión nueva por consulta** (heredado de HANDOFF-1 §8). Con trayectorias que repiten poco estado — como la exploración temprana de un agente que recién empieza a aprender — la caché del *backend* rápido no ayuda tanto como con políticas tabulares ya convergidas; si DQN/PPO en la Fase 3 generan estados muy diversos, vale la pena medir la tasa de aciertos de caché antes de lanzar una corrida larga, y considerar un *pool* de conexiones al oráculo si el cuello de botella vuelve a aparecer.
- Dos bugs de infraestructura aparecieron bajo carga sostenida y ya están corregidos, pero son buenos candidatos a reaparecer con una carga de entrenamiento más intensa (DQN hace muchos más pasos por segundo que los tabulares): crecimiento sin cota de `hex_string` reaplicado sobre sí mismo (limitado a una capa, comparando en minúsculas) y lectura del log de auditoría de ModSecurity desde el byte 0 en cada proceso nuevo (`AuditTail` ahora arranca al final del archivo existente, con un reintento). Ver *Hallazgos* de F2-T05 y F2-T08 en el documento de esta fase.

## 9. Datos útiles para la siguiente fase

- **Tiempo típico de un run tabular de 200 000 pasos:** mediana ≈ 133 s (mín. 44 s, máx. 256 s sobre 110 corridas registradas de EXP-C1/D1/D2), laboratorio real, caché caliente. Los bandits se miden por tiradas, no por pasos: 128 000 tiradas en 58 s (F2-T05).
- **Hiperparámetros:** la recompensa es degenerada (ER = 0 en todo el espacio de búsqueda), así que ningún hiperparámetro "funcionó mejor" que otro en el sentido de evasión — todas las configuraciones de EXP-A1/A2/C1/D1/D2 empatan en ER = 0,000. Las configuraciones registradas (`configs/exp/EXP-*/*.yaml`) son un punto de partida razonable para RQ2/RQ5 (ε, α, γ, λ) pero no vienen de una búsqueda que haya tenido señal para guiarse.
- **Cómo agregar un algoritmo nuevo al runner:** implementar la clase en `wafarena/agents/<archivo>.py` cumpliendo el protocolo `Agent` (`act`, `observe`, `save`, `load`) y decorarla con `@register_agent("<algo>")` (patrón en `wafarena/agents/td.py`, `dp.py`, `mc.py`, `bandits.py`); `build_agent`/`load_checkpoint` la encuentran por la clave `algo` del YAML o del `meta.yaml` sin tocar el runner. Agregar el experimento al [catálogo](../07-experimentos/catalogo.md) y los YAML en `configs/exp/<exp_id>/`.

## 10. Capítulos del informe entregados

- `report/capitulos/04-atacante-clasico.md`
- Sección de protocolo experimental en `report/capitulos/03-laboratorio.md`

## 11. Firma de aceptación

- [x] Joaquín corrió el checklist completo en su máquina.
- [x] Problemas encontrados en la ventana:
  1. `make summarize EXP=EXP-A1` no es reproducible tal como lo pide el ítem (runs crudos no versionados y columna `git_shas` dependiente del commit). Verificado re-corriendo EXP-A1 completo: idéntico salvo `git_shas` (ver la nota en §4).
  2. `Defender-v0` no acepta un objeto `AttackerPolicy` como `attacker` (`AttributeError: 'AttackerDriver' object has no attribute 'get'`), a diferencia de `Attacker-v0`, que sí acepta un objeto como `defender`. La forma del contrato, `{"type": "checkpoint", "path": ...}`, funciona. No bloquea; anotado en *Hallazgos* de la Fase 3.
  3. El checklist se corrió el 2026-10-24; la re-corrida de EXP-A1 terminó a las 00:00 del 2026-10-25 por una caída del *daemon* de Docker en la máquina de verificación (ajena al proyecto).
- [x] Aceptado por: Joaquín Puente · Fecha: 2026-10-25
- [x] `CLAUDE.md` actualizado: **Fase activa: 3**.
