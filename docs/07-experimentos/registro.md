# Registro de experimentos

Una fila por configuración (`run_name`) terminada de un experimento del [catálogo](catalogo.md). Las filas no se borran: si un run resultó inválido (bug, configuración equivocada), se marca como **inválido** con la razón y se agrega una fila nueva.

Los números de la columna *Resultado* se copian de `results/summary/<exp_id>.csv`; nunca se escriben de memoria.

| Fecha | Exp | `run_name` | Commit | Semillas | Resultado principal (media [IC 95 %]) | Estado | Responsable | Notas |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22 | (apoyo EXP-A1/A2) | bandit-arm-means | e10434a | 1 (seed 0) | μ = 0.000 en los 16 brazos contra modsec-pl1 … pl4 (2 000 tiradas por brazo; `results/summary/bandit_arm_means.csv`) | válido | Daniel | Estimación fuera de línea para el regret; todas las medias son 0 |
| 2026-10-22 | (exploratorio) | evasion-reachability-pl1 | e10434a | 1 (seed 0) | 0 / 172 payloads de `train` evaden PL1 con búsqueda voraz de 25 pasos; puntuación mínima alcanzada 5 (umbral de bloqueo 5); `results/summary/evasion_reachability_pl1.csv` | exploratorio | Daniel | Sondeo de alcanzabilidad, no un experimento del catálogo |

| 2026-10-23 | EXP-A1 | greedy-pl1 / eps-greedy-001-pl1 / eps-greedy-01-pl1 / optimistic-pl1 / ucb-05-pl1 / ucb-2-pl1 / random-pl1 | 6055362 | 10 | ER = 0.000 [0.000, 0.000] en los 7 métodos; regret acumulado = 0 en las 20 000 tiradas (`results/summary/EXP-A1.csv`) | válido | Daniel | Consistente con mu = 0 en los 16 brazos contra modsec-pl1 (bandit_arm_means.csv); ningún método se distingue de otro porque la señal de recompensa es siempre 0 |
| 2026-10-23 | EXP-A2 | eps-greedy-01-sample-average / eps-greedy-01-constant-{005,01,03} | 6055362 | 10 | ER = 0.000 [0.000, 0.000] en las 4 configuraciones; sin recuperación que medir (regret ya era 0 antes y después del cambio pl1->pl3) (`results/summary/EXP-A2.csv`) | válido | Daniel | El riesgo documentado en el plan ("es un resultado válido si se mide bien") se cumple: resultado degenerado pero correctamente medido |

| 2026-10-23 | EXP-B1 | value-policy-iteration-pl1 | 8a90594 | 10 | ER = 0.000 [0.000, 0.000] en attacker-eval-v1; value iteration converge en 1147 iteraciones, policy iteration en 3, idéntico en las 10 semillas (`results/summary/EXP-B1.csv`) | válido | Daniel | VI y PI difieren en 6/120 estados, pero con el mismo valor Q exacto en esos estados (empates genuinos entre acciones igual de inútiles, verificado a mano); no es un desacuerdo real. Cota bajo un modelo aproximado: estados con bloqueo parcial mezclan transiciones terminales y no terminales porque el estado abstracto no distingue el conteo de bloqueos acumulados |

Estados posibles: **válido**, **inválido** (con razón), **exploratorio** (no se usa en el informe).
