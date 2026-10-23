# 4. Atacante clásico y RQ1

## Pregunta

**RQ1:** ¿qué tan vulnerable es ModSecurity (PL1–PL4) a un atacante de mutación que aprende con los
métodos clásicos (bandits, programación dinámica, Monte Carlo, SARSA, Q-learning, SARSA(λ))? El
protocolo de evaluación (runner, semillas, estadística) está en el capítulo 3,
[«Protocolo experimental y estadística»](03-laboratorio.md#protocolo-experimental-y-estadística).

## Métodos evaluados

Todos operan sobre el estado abstracto `[0, 120)` de `Attacker-v0` (familia × última respuesta ×
*bucket* de mutaciones) salvo los bandits, que ven solo el payload base como un brazo entre 16.

| Experimento | Método | Variantes |
|---|---|---|
| EXP-A1 | *k*-armed bandits | greedy, ε-greedy (0,01 / 0,1), optimista, UCB (c = 0,5 / 2), aleatorio |
| EXP-A2 | *k*-armed bandits | ε-greedy 0,1 con paso constante (α = 0,05 / 0,1 / 0,3) contra promedio muestral |
| EXP-B1 | Programación dinámica | *value iteration* y *policy iteration* sobre un MDP estimado con 200 000 transiciones |
| EXP-C1 | Monte Carlo | control ε-soft, *first-visit* y *every-visit* (ε = 0,05 / 0,1) |
| EXP-D1 | TD de un paso | SARSA y Q-learning, ε = 0,1 fijo |
| EXP-D2 | TD(λ) | SARSA(λ) con trazas de elegibilidad reemplazantes, λ ∈ {0, 0,5, 0,9} |

## Resultados por experimento

**EXP-A1/A2 — Bandits.** Los 7 métodos de EXP-A1 y las 4 configuraciones de EXP-A2 corrieron 10
semillas cada uno contra el laboratorio real (110 corridas, 0 fallos). ER = 0,000 [0,000; 0,000] en
todos; el regret acumulado en las 20 000 tiradas es 0 para los 7 métodos de EXP-A1, y EXP-A2 no
tiene nada que recuperar tras el cambio de defensor porque ya era 0 antes y después
(`results/summary/EXP-A1.csv`, `EXP-A2.csv`). La causa está aguas arriba del método de selección:
la media estimada *fuera de línea* de **los 16 brazos** contra `modsec-pl1`…`pl4` es 0
(`results/summary/bandit_arm_means.csv`, 2 000 tiradas por brazo), y una búsqueda voraz de 25 pasos
con 64 candidatos por paso no logra bajar la puntuación de ningún payload de `train` del umbral de
bloqueo (`results/summary/evasion_reachability_pl1.csv`). Ningún algoritmo de selección de brazos
puede explotar una señal que no existe.

**EXP-B1 — Programación dinámica.** Con el modelo estimado (200 000 transiciones, política
aleatoria, `modsec-pl1`), *value iteration* converge en 1 147 iteraciones y *policy iteration* en 3;
ambas coinciden en 114 de los 120 estados abstractos, y los 6 restantes son empates exactos de valor
Q entre acciones igual de inútiles (verificado a mano), no un desacuerdo real
(`results/summary/EXP-B1.csv`). La política óptima bajo este modelo aproximado tiene
ER = 0,000 [0,000; 0,000] en `attacker-eval-v1`: ni la solución exacta del MDP estimado evade. Esto
es una **cota bajo un modelo aproximado** — el estado abstracto no distingue el conteo de bloqueos
acumulados, así que el modelo mezcla transiciones terminales y no terminales en los estados con
bloqueo parcial — pero coincide con el resultado directo de EXP-A1.

**EXP-C1 — Monte Carlo.** *First-visit* y *every-visit*, ε ∈ {0,05; 0,1}, 200 000 pasos, 10
semillas, laboratorio real (40 corridas). ER = 0,000 [0,000; 0,000] en los 4 métodos, curva plana
en `val` durante todo el entrenamiento (`results/summary/EXP-C1.csv`,
`report/figuras/EXP-C1_er_vs_steps.png`).

**EXP-D1 — SARSA y Q-learning.** ε = 0,1 fijo, `pl1` y `pl2`, 200 000 pasos, 10 semillas (70
corridas con EXP-D2). ER = 0,000 [0,000; 0,000] en los 4 métodos
(`results/summary/EXP-D1.csv`). Se midió además la tasa de rotura del payload (BRK) durante el
entrenamiento, buscando el efecto *cliff* clásico (Q-learning más conservador que SARSA cerca del
«precipicio»): aquí ocurre lo contrario — SARSA rompe más (BRK final 0,0533) que Q-learning (0,0396),
y la brecha es consistente durante las 20 ventanas de entrenamiento (`report/figuras/EXP-D1_sarsa_vs_qlearning.png`).
La hipótesis del catálogo **no se confirma**: en *cliff walking* el camino arriesgado es también el
de mayor recompensa, y aquí no — toda mutación cuesta −0,1 sin importar qué tan cerca esté de romper
el payload, así que no hay asimetría de riesgo/recompensa que premie al método más conservador.

**EXP-D2 — SARSA(λ).** λ ∈ {0; 0,5; 0,9} contra `pl1`. ER = 0,000 [0,000; 0,000] en los 3 valores,
plana desde el primer punto de `val` (`results/summary/EXP-D2.csv`,
`report/figuras/EXP-D2_er_vs_steps.png`). La métrica propuesta en el catálogo (pasos hasta igualar
la ER final de SARSA de EXP-D1) es degenerada aquí: ambos lados de la comparación son 0.

## Tabla de vulnerabilidad de ModSecurity (RQ1)

Para responder RQ1 directamente se evaluó el mejor checkpoint de cada familia contra las cuatro
instancias de ModSecurity, comparado con las dos referencias guionizadas de la Fase 1
(`results/summary/RQ1_table.csv`, 10 semillas × 8 métodos × 4 PL = 32 celdas):

| Método | PL1 | PL2 | PL3 | PL4 |
|---|---|---|---|---|
| bandit-greedy | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| dp | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| monte-carlo | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| sarsa | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| qlearning | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| sarsa-lambda | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| corpus-replay | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |
| random-mutation | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] |

(Media [IC 95 % por bootstrap]; valores exactos en `results/summary/RQ1_table.csv`.) QFE, QFE-c y
DIV quedan sin definir (`nan`) en las 32 celdas por falta de evasiones de las que calcularlas. El
método representante de cada familia no se eligió por comparación entre ellos — las 8 filas están
empatadas en 0 — sino por ser la configuración más estándar de cada uno: `bandit-greedy` (única
configuración sin ventaja frente a las demás de EXP-A1/A2), `dp` (única configuración de EXP-B1),
`monte-carlo` = *first-visit* ε = 0,1, `sarsa` y `qlearning` = `pl1`, `sarsa-lambda` = λ = 0,9.

### Respuesta a RQ1

**Bajo el laboratorio actual, con los 16 operadores de mutación del registro congelado
([operadores-mutacion.md](../../docs/02-contratos/operadores-mutacion.md)), ModSecurity no es
vulnerable a ningún atacante clásico de las semanas 2–6 del curso — bandits, programación dinámica,
Monte Carlo, SARSA, Q-learning ni SARSA(λ) — en ningún nivel de paranoia (PL1–PL4).** El techo está
en el **espacio de ataque** (los operadores disponibles), no en el método de aprendizaje: la
evidencia de EXP-A1 es directa y no depende de ningún algoritmo de RL — la media de recompensa de
los 16 brazos contra las 4 instancias de ModSecurity es exactamente 0, y una búsqueda voraz
(no aprendida) de 25 pasos tampoco encuentra una sola mutación que baje la puntuación de un payload
del umbral de bloqueo. Ningún método posterior (DP, MC, TD) puede aprender una política mejor que lo
que el espacio de mutación permite, y en efecto ninguno lo hace: las 32 celdas de la tabla son
idénticas a 0. Esto es una respuesta negativa pero completa a RQ1 dentro del alcance declarado de
esta fase, no un resultado inconcluso.

## Limitaciones y hallazgos relevantes

- **El resultado depende de los 16 operadores actuales**, no de un límite teórico de ModSecurity.
  Es consistente con el riesgo documentado en el plan de esta fase («es un resultado válido si se
  mide bien») y queda abierto como trabajo futuro ampliar el espacio de mutación (por ejemplo, con
  un operador de cambio de ubicación del payload que sí modifique lo que reciben los *backends*, a
  diferencia de `location_switch` hoy).
- **Despliegue voraz y sesgo de optimismo.** Al preparar `ATK-REF-0` (F2-T10) se encontró que, al
  desplegarse de forma puramente voraz (`explore=False`), las políticas de DP, Monte Carlo, SARSA y
  SARSA(λ) casi nunca llegan a `SEND`: con la tabla Q inicializada en cero y toda recompensa real
  negativa, una acción nunca visitada siempre parece mejor que cualquiera ya explorada, así que la
  política se queda mutando indefinidamente (verificado contra el laboratorio real: 148–150 de 150
  pasos mutando, 0–2 consultas enviadas). Esto **no invalida** ER = 0,000 en ninguna evaluación de
  este capítulo — un episodio que nunca envía tampoco evade — pero sí significa que, desplegados tal
  cual fuera de la evaluación controlada, estos atacantes casi no atacan. Por eso `ATK-REF-0` es un
  bandit (`greedy-pl1`, EXP-A1, semilla 0): ataca por protocolo fijo (alterna mutar y enviar), no por
  valor de Q aprendido, y es el único que se comporta como oponente real dentro de `Defender-v0`.
- Dos bugs de infraestructura encontrados bajo carga sostenida en el laboratorio real (crecimiento
  sin cota del operador `hex_string` reaplicado sobre sí mismo; lectura del log de auditoría de
  ModSecurity desde el byte 0 en cada proceso nuevo) se corrigieron antes de registrar los runs
  afectados; no cambian ninguna cifra de este capítulo. Detalle en la sección *Hallazgos* de
  [fase-2-daniel-atacante-clasico.md](../../docs/03-plan/fase-2-daniel-atacante-clasico.md).

## `ATK-REF-0`

Se publica `checkpoints/refs/ATK-REF-0/` (contrato
[agentes-y-checkpoints.md](../../docs/02-contratos/agentes-y-checkpoints.md)): el checkpoint de
`greedy-pl1` (EXP-A1, semilla 0), elegido por ser el único método que ataca de forma confiable al
desplegarse (ver arriba), no por ER en `val` — todos empatan en 0. Se agregó a la suite
`defender-eval-v1` (contrato de métricas, versión 1.2) a través de `AttackerDriver`
(`wafarena/attackers/driver.py`), que reconstruye la observación de 288 dimensiones y el estado
abstracto dentro de `Defender-v0` sin oráculo ni *backend*. Verificado contra el laboratorio real y
como prueba unitaria: `load_checkpoint("checkpoints/refs/ATK-REF-0")` funciona y `AttackerDriver` lo
conduce sin errores en 100 sesiones de `Defender-v0`.
