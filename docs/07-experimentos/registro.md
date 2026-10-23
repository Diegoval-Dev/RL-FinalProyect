# Registro de experimentos

Una fila por configuración (`run_name`) terminada de un experimento del [catálogo](catalogo.md). Las filas no se borran: si un run resultó inválido (bug, configuración equivocada), se marca como **inválido** con la razón y se agrega una fila nueva.

Los números de la columna *Resultado* se copian de `results/summary/<exp_id>.csv`; nunca se escriben de memoria.

| Fecha | Exp | `run_name` | Commit | Semillas | Resultado principal (media [IC 95 %]) | Estado | Responsable | Notas |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22 | (apoyo EXP-A1/A2) | bandit-arm-means | e10434a | 1 (seed 0) | μ = 0.000 en los 16 brazos contra modsec-pl1 … pl4 (2 000 tiradas por brazo; `results/summary/bandit_arm_means.csv`) | válido | Daniel | Estimación fuera de línea para el regret; todas las medias son 0 |
| 2026-10-22 | (exploratorio) | evasion-reachability-pl1 | e10434a | 1 (seed 0) | 0 / 172 payloads de `train` evaden PL1 con búsqueda voraz de 25 pasos; puntuación mínima alcanzada 5 (umbral de bloqueo 5); `results/summary/evasion_reachability_pl1.csv` | exploratorio | Daniel | Sondeo de alcanzabilidad, no un experimento del catálogo |

Estados posibles: **válido**, **inválido** (con razón), **exploratorio** (no se usa en el informe).
