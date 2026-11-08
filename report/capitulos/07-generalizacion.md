# 7. Generalización

## Validación del modo rápido frente al laboratorio real

EXP-R1 evaluó los checkpoints fijos de `ATK-REF-0`, `ATK-REF-1`, `DEF-REF-1` y el campeón individual de self-play (`def-gen-08`, semilla de entrenamiento 0, seleccionado únicamente con `val` en EXP-I1/F4-T08). Para cada una de tres semillas de evaluación se usaron exactamente los mismos planes `test` en `fast` y `real`: 50 episodios por atacante contra `DEF-REF-1` con un presupuesto de 50 consultas, y 500 sesiones planificadas por defensor (250 frente a cada atacante de referencia, con 450 benignas y 50 de ataque). Las identidades y hashes de pesos de los agentes, oponentes y planes se verificaron en cada par. El GAP se define como `|m_fast − m_real|` por semilla y se promedia sobre las tres semillas (EXP-R1, evaluación `c1d2f4d`; [tabla completa](../../results/summary/EXP-R1_gap.csv)).

| Agente | Métricas definidas | GAP medio en cada métrica |
|---|---|---:|
| `ATK-REF-0` | ER, QFE-c, BRK | 0,0000 |
| `ATK-REF-1` | ER, QFE-c, BRK | 0,0000 |
| `DEF-REF-1` | TPR, ER-d, FPR, FPR-h, FPR(s), FPR-h(s), F1, Q-ALLOW | 0,0000 |
| Campeón self-play | TPR, ER-d, FPR, FPR-h, FPR(s), FPR-h(s), F1, Q-ALLOW | 0,0000 |

Los 22 GAP definidos fueron cero en las tres semillas; por ello sus intervalos *bootstrap* del 95 % también son `[0; 0]`. Los dos atacantes tuvieron ER = 0 en sus 150 episodios respectivos. QFE, DIV y UNQ dependen de evasiones observadas y permanecen indefinidas para ambos, en vez de recibir un cero artificial. En las semillas 0 y 2, `ATK-REF-1` no emitió ninguna solicitud en uno de los 50 intentos de ataque de cada política defensora. Estos intentos se conservaron en el conteo planificado, pero se excluyeron de métricas por solicitud; cada defensor tuvo 499 sesiones efectivas en esas semillas y 500 en la semilla 1 ([celdas y denominadores](../../results/summary/EXP-R1_cells.csv)). La ER del atacante y la ER-d del defensor proceden de planes distintos y no deben compararse como si fueran la misma tasa.

La coincidencia muestra que, para estos payloads y checkpoints, la aproximación rápida conservó las decisiones y métricas observadas en el laboratorio vivo. Es coherente con la implementación: `fast` reutiliza puntuaciones de ModSecurity obtenidas del mismo laboratorio y ejecuta el oráculo funcional directamente; `real` consulta ModSecurity y el oráculo por HTTP en cada evaluación. El resultado no cuantifica latencia y no extiende la equivalencia a otros payloads, configuraciones del WAF o condiciones del laboratorio. Los intervalos solo reflejan tres semillas de evaluación de checkpoints fijos, no variabilidad entre entrenamientos. La evaluación en modo real no corrige las limitaciones de generalización frente a atacantes no vistos y tráfico benigno difícil identificadas en EXP-I3–I5.
