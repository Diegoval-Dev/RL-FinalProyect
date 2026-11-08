# F4-T09 / EXP-R1: brecha entre modo rápido y modo real

## Propósito

Medir cuánto cambian las métricas finales al reemplazar `FastBackend` por `RealBackend` sin cambiar políticas, payloads, sesiones ni semillas. Los resultados son una validación del laboratorio; no seleccionan nuevos checkpoints ni entrenan agentes.

## Diseño de la evaluación

- Se usan tres semillas de evaluación (0–2), distintas de las semillas de entrenamiento. Cada una fija 50 episodios de `test` para `ATK-REF-0` y `ATK-REF-1` frente a `DEF-REF-1`, con presupuesto de 50 consultas. Los bloques de episodios son 1000–1049, 1050–1099 y 1100–1149, dentro de `attacker-eval-v1`.
- Para cada semilla se evalúan `DEF-REF-1` y el campeón final de self-play sobre 500 sesiones de `test`: 225 benignas y 25 de ataque contra cada uno de `ATK-REF-0` y `ATK-REF-1`. Los IDs y semillas de sesión se generan de forma determinista y son idénticos para ambos defensores y ambos backends. El campeón se lee de `results/summary/EXP-I3_selection.json` (semilla 0, selección previa basada solo en `val`) y se valida contra el checkpoint `def-gen-08` de EXP-I1 `pool`.
- Si un atacante no emite ninguna solicitud en una sesión planificada, esta se registra como vacía y se excluye de las métricas por solicitud en ambos modos. La misma lista de sesiones emisoras se usa en fast y real.
- Se ejecuta cada celda primero en fast y luego en real con el mismo plan. Se conservan los hashes de pesos, el SHA del plan, el run ID y el SHA de evaluación. Las celdas crudas se guardan atómicamente y se reanudan desde caché si son completas.

## Resultados

- Para atacantes se calculan ER, QFE, QFE-c, DIV, UNQ y BRK; para defensores TPR, ER-d, FPR, FPR-h, FPR(s), FPR-h(s), F1 y Q-ALLOW. Una métrica sin denominador queda indefinida y su GAP queda vacío.
- `GAP(m) = |m_fast − m_real|` se calcula por semilla de evaluación y luego se promedia. El IC del 95 % se obtiene por *bootstrap* de las tres brechas emparejadas definidas. El IC describe variación del muestreo de evaluación con checkpoints fijos, no variación de entrenamiento.
- `results/summary/EXP-R1_cells.csv` guarda las 24 celdas; `EXP-R1_gap.csv` es la tabla final por agente y métrica. Los crudos quedan bajo `results/_r1_final_<eval_sha>/` y no se versionan.

## Límites

La prueba usa una fracción de las suites finales y solo un checkpoint por agente. Los tres bloques de evaluación no equivalen a tres entrenamientos independientes. Los modos pueden generar trayectorias distintas después de una respuesta distinta, aunque empiezan con el mismo plan. `RealBackend` consulta el laboratorio interno; las políticas no contactan servicios externos.

## Aceptación

Las 24 celdas terminan limpias, tienen planes emparejados y tamaños documentados, y la tabla registra el GAP de cada métrica definida. La segunda ejecución reproduce resúmenes y celdas byte a byte. Pasan lint y pruebas unitarias; los hallazgos y el registro EXP-R1 enlazan los run IDs.
