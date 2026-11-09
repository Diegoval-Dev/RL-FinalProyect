# 6. Planning y self-play

## Preguntas

Este capítulo responde **RQ3** —si el self-play con un pool ayuda a conservar la robustez frente a oponentes anteriores— con EXP-I1 e I2, y **RQ4** —si Dyna-Q aprovecha consultas reales mejor que el aprendizaje libre de modelo— con EXP-H1 y H2. Los resultados proceden de las filas válidas del [registro experimental](../../docs/07-experimentos/registro.md); las figuras y tablas se generaron a partir de los resúmenes versionados.

## Diseño experimental

### Atacante con modelo sustituto

En EXP-H1 el atacante aprende una aproximación supervisada de la respuesta del defensor a `SEND`. Solo las consultas reales consumen presupuesto; los pasos de planificación usan la predicción del sustituto. Se compararon Q-learning (`n = 0`), Dyna-Q (`n ∈ {5, 20, 50}`) y PPO, contra `modsec-pl1` y `DEF-REF-1`. Se ejecutaron 10 semillas para métodos tabulares y 5 para PPO. El eje de muestra son las consultas reales acumuladas, no los pasos de planificación. La evaluación usa `attacker-val-v1` (EXP-H1; commits de código `7714621` y `9d54cd2`; [curvas y celdas](../../results/summary/EXP-H1.csv)).

EXP-H2 cambió el defensor de `modsec-pl1` a `DEF-REF-1` en el paso 100 000 y comparó Dyna-Q (`n = 20`) con Dyna-Q+ (`κ ∈ {0,01; 0,001}`), 10 semillas por configuración. La recuperación se mide desde la ER previa al cambio ([EXP-H2](../../results/summary/EXP-H2.csv), [estados de recuperación](../../results/summary/EXP-H2_recovery.csv); commit `dc698cb`).

### Self-play

EXP-I1 entrenó ocho generaciones con tres semillas emparejadas (0–2) para cada condición. En `naive`, el agente siempre enfrenta al oponente actual; en `pool`, lo enfrenta con probabilidad 0,5 y el resto del tiempo muestrea oponentes históricos. Se usaron 40 episodios o sesiones por referencia y generación en `val`. La comparación principal reporta TPR por solicitud frente a `ATK-REF-0` y `ATK-REF-1`; los intentos sin solicitud emitida se reintentan y cuentan en diagnósticos, no en el denominador por solicitud (EXP-I1, entrenamiento `eea6f78`; [runs](../../results/summary/EXP-I1_runs.csv), [curva](../../results/summary/EXP-I1_curve.csv), [figura](../figuras/EXP-I1_tpr.png)).

EXP-I2 cruzó cada una de las ocho generaciones de defensor con cada generación de atacante del pool. Cada celda usa 200 episodios de `attacker-eval-v1` en `test`, y se repitió con tres semillas: 192 celdas, 38 400 episodios en total. La selección del campeón no usó este resultado. La ER es por episodio y no es directamente comparable con el TPR por solicitud de I1 (commit de evaluación `85524f0`; [celdas](../../results/summary/EXP-I2_cells.csv), [matriz](../../results/summary/EXP-I2_matrix.csv), [figura](../figuras/EXP-I2_crossplay.png)).

## Resultados de self-play (RQ3)

En la generación 8, el pool obtuvo mayor TPR descriptivo que el self-play ingenuo frente a las dos referencias. Los intervalos *bootstrap* se calcularon sobre tres semillas, no sobre solicitudes:

| Condición | TPR vs. `ATK-REF-0` | TPR vs. `ATK-REF-1` |
|---|---:|---:|
| Ingenua | 0,5458 [0,3029; 0,9420] | 0,7334 [0,6506; 0,8196] |
| Pool | 0,7556 [0,6589; 0,8687] | 0,8234 [0,7393; 0,8947] |

Las bandas se superponen y la comparación tiene solo tres semillas. Además, ambas condiciones perdieron TPR desde el inicio; las 84 evaluaciones históricas por condición no revelan una ventaja clara (medias descriptivas 0,9810 ingenua y 0,9841 pool). Por tanto, la diferencia final favorece descriptivamente al pool, pero **no demuestra una mejora robusta** (EXP-I1, `naive` y `pool`; entrenamiento `eea6f78`; [resumen](../../results/summary/EXP-I1_curve.csv), [registro](../../docs/07-experimentos/registro.md#registro-de-experimentos)).

La matriz I2 encontró 59 evasiones en 38 400 episodios. Doce de las 64 posiciones agregadas tuvieron ER positiva. El mayor promedio fue 0,0367 [0,0250; 0,0600] para el defensor de generación 8 contra el atacante de generación 1 (22 de 600 episodios entre semillas). El cruce muestra que algunas parejas históricas conservan vulnerabilidades; no implica una tasa general de evasión alta, ni permite escoger un agente mirando el conjunto `test` (EXP-I2; [matriz](../../results/summary/EXP-I2_matrix.csv)).

**Respuesta a RQ3.** Con estos entrenamientos, el pool termina con mayor TPR frente a las dos referencias, pero la cantidad de semillas, los intervalos superpuestos y la pérdida de TPR en ambas condiciones impiden concluir que el pool sea superior de forma robusta. La hipótesis H3 recibe apoyo descriptivo, no evidencia concluyente.

## Resultados de Dyna (RQ4)

Contra `modsec-pl1`, todos los métodos tabulares y PPO terminan con ER = 0. Contra `DEF-REF-1`, los métodos tabulares también terminan con ER = 0 en el último punto de consultas compartido. PPO alcanza ER = 0,0105 [0,0014; 0,0225] con 1 073 consultas reales. La referencia fija `ATK-REF-1` alcanza ER = 0,0050 en 200 episodios contra `DEF-REF-1`, y 0 contra PL1; las consultas de su entrenamiento no se cuentan en EXP-H1.

| Método, `run_name` | Semillas | Consultas reales medias al cierre | ER vs. PL1 | ER vs. `DEF-REF-1` |
|---|---:|---:|---:|---:|
| Q-learning, `qlearning-defref1` | 10 | 2 426 | 0,0000 [0,0000; 0,0000] | 0,0000 [0,0000; 0,0000] |
| Dyna-Q, `dyna-5-defref1` | 10 | 2 351 | 0,0000 [0,0000; 0,0000] | 0,0000 [0,0000; 0,0000] |
| Dyna-Q, `dyna-20-defref1` | 10 | 2 469 | 0,0000 [0,0000; 0,0000] | 0,0000 [0,0000; 0,0000] |
| Dyna-Q, `dyna-50-defref1` | 10 | 2 586 | 0,0000 [0,0000; 0,0000] | 0,0000 [0,0000; 0,0000] |
| PPO, `ppo-defref1` | 5 | 1 073 | 0,0000 [0,0000; 0,0000] | 0,0105 [0,0014; 0,0225] |

Las consultas son el promedio al último punto de evaluación compartido de cada grupo; las ER e IC son los resúmenes de la suite `attacker-val-v1` (EXP-H1, `results/summary/EXP-H1.csv`). Dyna-Q no mejora la ER frente a Q-learning: ambos empatan en cero. El menor conteo de consultas de Dyna-Q con `n = 5` no constituye una mejora útil, porque no aparece ninguna evasión que comparar.

El sustituto contra `DEF-REF-1` tuvo exactitud media aproximada de 0,9386–0,9389, pero su *recall* de la clase minoritaria al cierre quedó entre 0,0083 y 0,0155. La exactitud agregada oculta que el modelo casi no identifica respuestas minoritarias relevantes para la planificación. Estos valores corresponden a `qlearning-defref1` y `dyna-{5,20,50}-defref1` (10 semillas cada uno; [EXP-H1](../../results/summary/EXP-H1.csv), commits `7714621` y `9d54cd2`).

En EXP-H2, las 30 semillas (10 por método) tuvieron ER previa y posterior al cambio igual a 0. El estado fue `baseline_zero` en 30 de 30; por eso no hay tiempo de recuperación definido y no se puede comparar la adaptación de Dyna-Q+ con Dyna-Q ([resumen](../../results/summary/EXP-H2.csv), [recuperación](../../results/summary/EXP-H2_recovery.csv)).

EXP-H3, Prioritized Sweeping, se recortó según el orden del plan maestro. Dado que H1 y H2 no produjeron señal de evasión para los métodos tabulares, esa comparación adicional no habría resuelto la limitación del espacio de ataque (Hallazgo de F4-T04 en el [plan de fase](../../docs/03-plan/fase-4-nelson-planning-selfplay.md#hallazgos)).

**Respuesta a RQ4.** En este espacio de acciones, los experimentos no muestran que Dyna alcance una ER positiva con menos consultas que Q-learning. El sustituto tuvo bajo *recall* minoritario, y la ER cero hizo indefinida la comparación de recuperación de H2. La hipótesis H4 no queda respaldada por esta campaña. PPO sí halló evasiones raras contra `DEF-REF-1`, pero es una referencia adicional, no evidencia de una ventaja de planificación.

## Limitaciones de la fase

- La campaña de self-play usó el mínimo de tres semillas y 40 sesiones o episodios por punto de referencia; los intervalos son amplios y no permiten inferir estabilidad entre entrenamientos.
- El defensor y el atacante comparten un espacio reducido de operadores. La ausencia de evasiones de Dyna no es una cota sobre otros operadores, WAF o aplicaciones.
- La clasificación del sustituto es dominada por la clase mayoritaria; su exactitud no resume su utilidad para planificar.
- EXP-H2 no permite medir recuperación porque la ER basal es cero.
- EXP-I2 evalúa en `test`; se informa como evaluación final descriptiva y no se usa para selección. ER se mide por episodio, mientras I1 mide TPR por solicitud.
- Los archivos de corridas crudas no se versionan; los CSV resumidos y figuras citados sí forman parte del repositorio.
