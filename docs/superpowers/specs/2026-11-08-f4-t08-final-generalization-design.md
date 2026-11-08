# F4-T08 / EXP-I3–I5: generalización final

## Propósito

Comparar el defensor final de self-play con `DEF-REF-1` y ModSecurity frente a familias SQLi no vistas, tráfico benigno difícil y dos atacantes que nunca participaron en self-play. La tabla final responde RQ5 con procedencia de cada run e IC calculados sobre semillas, sin usar `test` para seleccionar políticas.

## Selección anterior a la evaluación final

- Los candidatos son los tres defensores `def-gen-08` de EXP-I1 `pool` (semillas 0–2, entrenamiento `eea6f78`). Son finales comparables: cada uno enfrentó en `val` a los siete atacantes anteriores de su mismo run, registrados en `results/summary/EXP-I1_history.csv`.
- El límite de FPR es el de `DEF-REF-1` en `val`, 0. Se ordena primero a quienes cumplen el límite, luego por la media de TPR en los siete cruces. Si nadie cumple, se elige menor FPR, luego mayor media de TPR y por último menor semilla. Este caso ocurre en EXP-I1: las tres semillas finales superan el límite. El campeón individual es la semilla 0; las tres semillas se conservan como cohorte para los IC. La selección no consulta EXP-I2.
- Los 30 checkpoints Dyna-Q de EXP-H1 contra `DEF-REF-1` empatan en ER máxima de `attacker-val-v1` (= 0). Se usa Dyna-5 semilla 0, con menos pasos de planificación que Dyna-20/50 y desempate por semilla. No se presenta como mejor por eficacia.
- El PPO nuevo usa los parámetros de `EXP-H1/ppo-defref1`, 200 000 pasos y semilla 5 (fuera de self-play 0–2 y del PPO previo 0–4). El entrenamiento y la elección de su checkpoint usan solo `train` y `attacker-val-v1`; `eval.final: false`.

## Evaluación

- **I3:** los tres defensores finales del pool y `DEF-REF-1` en `defender-eval-family-v1`; **I4:** los mismos en `defender-eval-hard-v1`. El comparador ModSecurity principal es PL2, que fija FPR 0 en `val`. I3 usa 2 000 sesiones por cada uno de dos atacantes guionizados (4 000 agregadas). I4 usa las 480 sesiones benignas difíciles una vez y 200 ataques por atacante (680 por atacante, 1 360 agregadas). Los resultados de ModSecurity PL2 en ambas suites ya están versionados en `results/summary/modsec_defender_suites.csv`; se reutilizan con referencia explícita a su run. Se vuelve a evaluar `DEF-REF-1` como checkpoint publicado.
- **I5:** los tres defensores finales, `DEF-REF-1` y ModSecurity PL2 frente al PPO nuevo y Dyna-5 s0. Para cada par, se usa un plan fijo de 2 000 sesiones de `test` (1 800 benignas, 200 ataques) con los mismos IDs y semillas de `defender-eval-v1`. Antes de evaluar defensores, se identifica cuáles sesiones de ataque producen al menos una solicitud con el checkpoint y la semilla fijados. Se evalúan solo esas sesiones junto con las 1 800 benignas; las sesiones sin solicitud se registran como vacías y nunca como defensas exitosas. Se registran TPR por solicitud, FPR por solicitud y ER-d por solicitud de ataque con efecto. El plan elegible es idéntico para todos los defensores frente a un mismo atacante.
- Cada celda conserva checkpoint y SHA de entrenamiento, SHA de evaluación, suite, split, plan de sesiones y métricas. Las celdas completas se guardan atómicamente y se validan antes de reusar. Los resúmenes y la tabla RQ5 se versionan; los crudos quedan en `results/`.
- El IC del 95 % para self-play se obtiene por *bootstrap* de sus tres valores de semilla. `DEF-REF-1` y PL2 son checkpoints/políticas fijos: se muestran como valores de referencia, sin presentar tres repeticiones idénticas como IC independiente.

## Límites

La elección del campeón se apoya en solo siete cruces de 40 sesiones por candidato y ninguna semilla cumplió el límite de FPR. I5 usa un checkpoint por tipo de atacante, así que el IC de self-play describe variación entre defensores, no entre entrenamientos de atacantes. Las sesiones de ataque vacías reducen el número de ataques observables para ese atacante. ER-d, TPR y FPR tienen denominadores distintos y se presentan por separado. EXP-I3–I5 son evaluaciones de solo lectura en `test`.

## Aceptación

La selección se reproduce desde los CSV de `val`; PPO s5 se entrena con un YAML versionado; I3–I5 se regeneran desde checkpoints y suites fijas, con validación de procedencia y resultados completos. La tabla RQ5 contiene TPR, FPR y ER-d con IC de tres semillas self-play y referencias fijas identificadas. Pasan lint y pruebas unitarias.
