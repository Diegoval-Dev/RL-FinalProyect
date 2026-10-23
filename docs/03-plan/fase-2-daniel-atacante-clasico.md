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
- [x] F2-T03 Runner
- [x] F2-T04 Métricas y suites
- [x] F2-T05 Bandits
- [x] F2-T06 MDP abstracto y DP
- [x] F2-T07 Monte Carlo
- [x] F2-T08 TD
- [ ] F2-T09 Tabla RQ1
- [ ] F2-T10 `ATK-REF-0`
- [ ] F2-T11 Informe y handoff

## Hallazgos

- **F2-T01 (heredado de F1-T12):** `gym.make("WafArena/Attacker-v0", backend="fast", defender={...})` y `Defender-v0` con `backend="fast"` / `attacker="corpus_replay"` no funcionaban como lo documentan los contratos (los entornos solo aceptaban objetos). Corregido en esta fase con `wafarena/envs/resolve.py`; los tipos `checkpoint` y `pool` lanzan `NotImplementedError` hasta F2-T02/T10. El contrato no cambia (el código se alineó con él).
- **F2-T01 (hallazgo, afecta F2-T10):** `AttackerDriver` y `DefenderDriver` figuran como entregados en HANDOFF-1 §2 y en el contrato de agentes, pero no existen en el código (`grep` sin resultados). Hay que implementarlos antes de usar `ATK-REF-0` dentro de `Defender-v0`; `{"type": "checkpoint"|"pool"}` sigue lanzando `NotImplementedError` hasta entonces.
- **F2-T02:** el contrato nombra las versiones en `meta.yaml` como `env_attacker`, `operators`, `features`, distintos de las claves de `wafarena.CONTRACT_VERSIONS`; `wafarena/agents/base.py` mantiene la correspondencia (`META_CONTRACT_KEYS`). `pyyaml` pasó a dependencia de runtime.
- **F2-T04:** `DefenderEnv` usaba un solo `split` para sesiones benignas y payloads de ataque, lo que impedía las suites `family` y `hard`. Se agregó `attack_split` y `options` (`base_id`, `session_id`) en `reset` (contrato env-defensor 1.1, compatible). Además `RandomMutationAttacker` podía sortear presupuesto 0 y producir una sesión de ataque sin requests, que rompía `DefenderEnv.reset`; ahora envía entre 1 y 5 requests. `ATK-REF-0` se agrega a `defender-eval-v1` en F2-T10.
- **F2-T03 (rendimiento):** un run de humo con el agente aleatorio contra `modsec-pl1` en el laboratorio real (2 000 pasos de entrenamiento + 3 evaluaciones de 200 episodios) tardó 2 192 s con la caché fría, unos 40 pasos/s, porque cada payload nuevo cuesta una conexión al oráculo más cuatro consultas HTTP a ModSecurity (el problema de «una conexión por consulta» ya anotado en HANDOFF-1 §8). Una segunda semilla con la caché de la primera tampoco bajó de 35 min, porque las trayectorias aleatorias casi no repiten payloads. Los atacantes tabulares repiten estados y payloads mucho más; antes de las corridas de 200 000 pasos hay que medir su tasa de aciertos de caché y, si hace falta, agregar un *pool* de conexiones al oráculo (R3 de los riesgos de esta fase).
- **F2-T03 (decisión):** `make run` ejecuta el runner dentro del contenedor `runner` (único con acceso a la red del laboratorio); por eso la imagen incluye `git`.
- **F2-T05 (rendimiento, resuelto):** el cuello de botella del backend `fast` en frío eran la conexión nueva al oráculo por payload (≈ 5,5 ms), cuatro consultas secuenciales a ModSecurity (≈ 6–10 ms cada una) y el reescaneo completo del audit log por request. Se reutiliza una conexión del oráculo, se leen solo los bytes nuevos del log, se mantienen conexiones HTTP vivas y se consultan en paralelo los niveles sin caché: ≈ 24 → ≈ 239 payloads/s en frío (≈ 10×); 128 000 tiradas de bandit en 58 s; `make test-lab` pasó de 195 s a 31 s.
- **F2-T05 (hallazgo que afecta a RQ1):** la media de **todos** los brazos es 0 contra `modsec-pl1` … `pl4` (`results/summary/bandit_arm_means.csv`), y una búsqueda voraz de 25 pasos con 64 candidatos por paso no baja de 5 la puntuación de ningún payload de `train` (umbral de bloqueo = 5; `results/summary/evasion_reachability_pl1.csv`). Con los 16 operadores actuales, la señal de recompensa de EXP-A1 (1 al evadir) es siempre 0: el regret es 0 y todos los métodos empatan. Enviar el payload en su `location` real (form/JSON) no cambia la puntuación de CRS (60/60 bloqueados en las tres ubicaciones, sondeo manual), aunque `location_switch` hoy no modifica lo que reciben los backends. Decisión pendiente con el equipo: ver el informe de esta sesión.
- **F2-T05 (bug, resuelto):** `hex_string` reaplicado sobre su propia salida es siempre funcional para el oráculo (hex de hex es hex válido), así que sin límite el payload crece sin cota. Causó un OOM del contenedor `runner` corriendo EXP-A1 (`ucb-05-pl1`) contra el laboratorio real. Se limitó a una sola capa (`wafarena/mutations/operators.py`); el ejemplo documentado en el contrato no cambia, versión 1.1.
- **F2-T05 (resultado final):** las 10 semillas de los 7 métodos de EXP-A1 y las 4 configuraciones de EXP-A2 corrieron completas contra el laboratorio real (110 corridas, 0 fallos). ER = 0,000 [0,000; 0,000] para todos: ningún método bandit evade ModSecurity PL1 ni se distingue de otro, porque los 16 operadores no producen una sola evasión (ya visto en \`bandit_arm_means.csv\` y \`evasion_reachability_pl1.csv\`). Regret acumulado = 0 en las 20 000 tiradas para los 7 métodos de A1, y en A2 no hay nada que recuperar tras el cambio de defensor porque ya era 0 antes. Registrado en \`registro.md\`; figuras en \`report/figuras/EXP-A1_regret.png\`, \`EXP-A1_mean_reward.png\`, \`EXP-A2_regret.png\`.
- **F2-T06 (resultado final):** 200 000 transiciones con política aleatoria contra modsec-pl1, 10 semillas, laboratorio real. Value iteration (1147 iteraciones) y policy iteration (3 iteraciones) convergen a la misma política en 114/120 estados; en los 6 restantes difieren solo por empates exactos entre acciones de igual valor Q (verificado a mano, no es un desacuerdo real). ER = 0,000 [0,000; 0,000] en \`attacker-eval-v1\`, idéntico a los bandits de F2-T05: la cota óptima bajo el modelo aproximado tampoco evade. Se corrigió de paso un ciclo de policy iteration entre políticas empatadas (detección de ciclos en \`wafarena/agents/dp.py\`). Registrado en \`registro.md\`.
- **F2-T07 (resultado final):** first-visit y every-visit MC control, eps in {0.05, 0.1}, 200 000 pasos, 10 semillas, laboratorio real (40 corridas, 0 fallos reales; una semilla se reintentó por un choque transitorio con un commit en curso). ER = 0,000 [0,000; 0,000] en los 4 métodos, curva plana en val durante todo el entrenamiento. Mismo resultado que bandits (F2-T05) y DP (F2-T06): el techo está en los 16 operadores, no en el método de aprendizaje. Registrado en `registro.md`.
- **F2-T08 (bugs, resueltos):** corriendo EXP-D1 contra el laboratorio real aparecieron dos problemas nuevos. (1) El log de auditoría de ModSecurity nunca se rota y ya pesaba cientos de MB; cada proceso nuevo (`docker compose run`) empezaba a leerlo desde el byte 0, y escanear eso bajo carga sostenida superaba el timeout de 5 s del oráculo de ModSecurity — se corrigió para que el lector arranque en el final del archivo (`wafarena/defenders/modsec.py`), más un reintento de una sola vez si de todas formas se pierde una entrada. (2) El límite de una sola capa que le puse a `hex_string` en F2-T05 comparaba el marcador con mayúsculas exactas; `case_swap` puede revolver las mayúsculas de ese mismo texto, haciéndolo invisible para la comprobación y permitiendo que `hex_string` se reaplicara de todas formas — en un payload real llegó a 40 capas anidadas y 8 KB. Se corrigió comparando en minúsculas.
- **F2-T08 (resultado final):** SARSA y Q-learning, ε=0,1 fijo, pl1 y pl2; SARSA(λ) con λ ∈ {0, 0.5, 0.9} contra pl1. 200 000 pasos, 10 semillas, laboratorio real (70 corridas, 0 fallos reales tras los arreglos). ER = 0,000 [0,000; 0,000] en los 7 métodos, igual que F2-T05/06/07. La hipótesis del catálogo sobre el efecto *cliff* no se confirma: SARSA rompe más el payload durante el entrenamiento que Q-learning (~0,024 contra ~0,021), lo opuesto a lo esperado. Se atribuye a que aquí no hay asimetría de recompensa entre el camino arriesgado y el seguro (toda mutación da −0,1 sin importar el riesgo), a diferencia del cliff walking clásico. Registrado en `registro.md`.
