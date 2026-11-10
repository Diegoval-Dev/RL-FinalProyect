# 9. Conclusiones

## Respuestas a las preguntas de investigación

| Pregunta | Respuesta respaldada por la campaña |
|---|---|
| **RQ1.** ¿Qué tan vulnerable es ModSecurity a métodos clásicos? | En las 32 celdas de EXP-A1–D2 y RQ1, ER fue 0 para los ocho métodos frente a PL1–PL4. Esta respuesta se limita a los 16 operadores actuales y a los ataques SQLi del laboratorio. [Cap. 4](04-atacante-clasico.md), [RQ1_table.csv](../../results/summary/RQ1_table.csv), commit `6eb3ff1`. |
| **RQ2.** ¿Compite un defensor RL con ModSecurity? | En `defender-eval-v1`, DQN Double+Dueling alcanza TPR 0,9984 [0,9967; 0,9994] y FPR 0,0002 [0,0000; 0,0005], por encima de PL1 y PL2 en TPR con FPR cercano a cero. No domina PL3/PL4, que alcanzan TPR 1,0 pero tienen FPR 0,3327/0,3844. En benignos difíciles el FPR del defensor estático sube a 0,3385 [0,2775; 0,3996]. [Cap. 5](05-deep-rl.md), [EXP-F5.csv](../../results/summary/EXP-F5.csv), [EXP-F7.csv](../../results/summary/EXP-F7.csv), entrenamiento `1517d8f` y `d9d7d49`. |
| **RQ3.** ¿El pool de self-play mejora la robustez? | En generación 8 el pool tuvo mayor TPR descriptivo que el entrenamiento ingenuo frente a `ATK-REF-0` y `ATK-REF-1`, pero los IC se superponen y se usaron tres semillas. La matriz de cruces conserva evasiones en algunos pares históricos. No hay evidencia suficiente para afirmar superioridad robusta. [Cap. 6](06-planning-selfplay.md), [EXP-I1_curve.csv](../../results/summary/EXP-I1_curve.csv), [EXP-I2_matrix.csv](../../results/summary/EXP-I2_matrix.csv), entrenamiento `eea6f78`, evaluación `85524f0`. |
| **RQ4.** ¿Dyna mejora la evasión por consulta? | No se observó una ER positiva en Dyna-Q ni Q-learning contra `DEF-REF-1`; Dyna tampoco produjo evasiones frente a PL1. El sustituto tuvo exactitud cercana a 0,939, pero *recall* minoritario de 0,0083–0,0155. H2 no puede comparar recuperación porque todas las ER fueron cero; H3 se recortó. La campaña no respalda una ventaja de Dyna. [Cap. 6](06-planning-selfplay.md), [EXP-H1.csv](../../results/summary/EXP-H1.csv), [EXP-H2_recovery.csv](../../results/summary/EXP-H2_recovery.csv), `7714621`, `9d54cd2` y `dc698cb`. |
| **RQ5.** ¿Generalizan los agentes a condiciones no vistas y cuál es la brecha fast/real? | El self-play detecta ataques de familias no vistas con TPR 0,9470 [0,9446; 0,9520] y FPR 0,0092 [0,0012; 0,0177], pero en benignos difíciles su FPR sube a 0,3112 [0,2611; 0,4084]. Contra el PPO no visto la TPR cae a 0,6108 [0,5596; 0,6812]. La Dyna elegida tuvo TPR 1,0 solo entre solicitudes emitidas; únicamente 73 de 200 sesiones de ataque previstas emitieron solicitudes. En EXP-R1, las 22 combinaciones de métrica/agente definidas tuvieron GAP fast-real de 0 en las tres semillas; esto es específico a las suites y checkpoints estudiados. [Cap. 7](07-generalizacion.md), [RQ5_final.csv](../../results/summary/RQ5_final.csv), [EXP-R1_gap.csv](../../results/summary/EXP-R1_gap.csv), evaluación `bf14912` y `c1d2f4d`. |

## Síntesis

La campaña muestra que un defensor DQN puede separar ataques de tráfico benigno ordinario en el laboratorio y competir con los niveles bajos de ModSecurity en la suite de evaluación estándar. La brecha aparece cuando cambia el tráfico benigno: los FPR de los defensores aprendidos aumentan en `test-hard`. El entrenamiento contra adversarios propios y un pool genera políticas con respuestas diversas, pero los resultados disponibles no prueban que el pool sea consistentemente superior. Para el atacante, Dyna no resolvió el bajo poder predictivo del sustituto sobre respuestas minoritarias; con los operadores evaluados, su ER fue cero. La validación rápida y real coincidió en las métricas definidas, aunque no evaluó latencia ni generalización fuera de esas condiciones.

En conjunto, los resultados contestan las RQ dentro del laboratorio y las suites registradas. No justifican afirmar que el defensor esté listo para producción ni que el agente atacante pueda evadir WAF de otras configuraciones.

## Limitaciones consolidadas

### Alcance y oráculo

- El objeto de estudio es una aplicación vulnerable propia, PostgreSQL, ModSecurity con OWASP CRS y SQLi. No se cubren otras aplicaciones, motores de base de datos, familias como XSS ni WAF de producción (ADR-0001; [capítulos 1](01-introduccion.md) y [3](03-laboratorio.md)).
- El oráculo de laboratorio observa directamente la consulta y los canarios. Además, el atacante puede verificar funcionalidad sin pagar una consulta real. En producción no existe esa etiqueta inmediata ni esa ventaja; el defensor no se presenta como listo para desplegar ([cap. 3](03-laboratorio.md), [cap. 8](08-etica.md)).
- El espacio de ataque está limitado a 16 operadores. Los resultados negativos frente a ModSecurity y Dyna pueden reflejar esa limitación y no una imposibilidad general de evadir un WAF ([cap. 4](04-atacante-clasico.md), [cap. 6](06-planning-selfplay.md)).

### Datos y generalización

- Los splits congelados y las suites representan un corpus y una aplicación concretos. El buen resultado en `defender-eval-v1` no se conserva ante todo el tráfico benigno: el FPR aumenta en `defender-eval-hard-v1` para ambos defensores aprendidos ([EXP-F7.csv](../../results/summary/EXP-F7.csv), [EXP-I4.csv](../../results/summary/EXP-I4.csv)).
- **Excepción a las 5 semillas.** La definición de terminado pide al menos 5 semillas en las configuraciones principales, o una excepción justificada. Las campañas EXP-I1, I2, I3 y I4 usan 3 semillas. La Fase 4 fija ese mínimo para el self-play porque cada semilla entrena ocho generaciones de atacante y defensor ([plan de la Fase 4](../../docs/03-plan/fase-4-nelson-planning-selfplay.md), F4-T06 y tabla de riesgos). No se midió ni se registró el tiempo de cómputo de cada corrida, así que aquí no se cuantifica el costo. La consecuencia está declarada en RQ3: con 3 semillas no se afirma superioridad del pool. Los tabulares de EXP-H1 y EXP-H2 sí usan 10 semillas y PPO usa 5.
- Las campañas finales de self-play y generalización usan tres semillas de defensor. Los IC describen variación entre esas semillas y no una población amplia de entrenamientos. Las referencias fijas de ModSecurity se ejecutaron como suites deterministas, sin IC de entrenamiento.
- I5 evalúa un solo checkpoint PPO nuevo (semilla de entrenamiento 5) contra una cohorte de tres defensores. Para la referencia Dyna, 127 de 200 sesiones planificadas no emitieron solicitud; el TPR condicionado a solicitudes no describe el éxito por sesión planificada ([EXP-I5.csv](../../results/summary/EXP-I5.csv)).
- I2 usa el split `test` para evaluación de cruces. Sus resultados son descriptivos y no pueden emplearse para cambiar checkpoints, umbrales o hiperparámetros ([EXP-I2_matrix.csv](../../results/summary/EXP-I2_matrix.csv)).

### Métodos y comparación

- La exactitud del sustituto de Dyna queda dominada por la clase mayoritaria y no implica capacidad predictiva útil para la clase minoritaria. ER cero vuelve indefinida la comparación de recuperación de H2; Prioritized Sweeping (H3) se recortó según el orden aprobado ([cap. 6](06-planning-selfplay.md)).
- El mayor TPR de cierre del pool en I1 es descriptivo: hay tres semillas, los intervalos se superponen y ambos métodos pierden TPR respecto del inicio. No se debe convertir ese patrón en una afirmación de mejora robusta.
- ER, TPR por solicitud, sesiones planificadas y solicitudes realmente emitidas usan denominadores distintos. Las tablas de los capítulos mantienen la definición y el denominador de cada suite.
- La igualdad de las métricas fast/real en R1 no mide latencia ni acredita equivalencia con otros payloads, estados de laboratorio, checkpoints o reglas. La prueba de R1 cubrió los pares de agentes, semillas y planes declarados en el capítulo 7.

### Reproducibilidad y uso

- Los resúmenes compactos y las figuras están versionados; las corridas crudas se excluyen del repositorio. La regeneración requiere las configuraciones, checkpoints fuente y servicios del laboratorio. El [README](../../README.md) documenta los puntos de entrada, y el inicio rápido se verificó desde una clonación limpia de `main` (ocho servicios del laboratorio saludables, 798 pruebas unitarias). No se reconstruyó la campaña completa desde esa clonación.
- La matriz de cruces y la demo son instrumentos de evaluación y presentación del laboratorio, no una certificación del producto ni una recomendación de despliegue.

## Trabajo futuro

1. Ampliar y evaluar el espacio de mutación dentro de un laboratorio propio, conservando splits independientes y el mismo control de aislamiento.
2. Mejorar la medición de tráfico benigno difícil y estudiar la selección de defensor bajo límites de falsos positivos definidos antes de ver `test-hard`.
3. Aumentar semillas y sesiones para self-play, y evaluar generaciones frente a atacantes retenidos sin usar el conjunto de prueba para selección.
4. Mejorar la calibración y el *recall* minoritario del sustituto antes de atribuir beneficios a más pasos de planificación.
5. Medir latencia y costo operacional en una suite dedicada; la igualdad de decisiones de R1 no sustituye una medición de rendimiento.
6. Ampliar el capítulo 2 con una revisión sistemática de la literatura sobre WAF con aprendizaje automático y RL ofensivo; el actual cubre solo las fuentes verificadas.
