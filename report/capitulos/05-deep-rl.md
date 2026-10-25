# 5. Deep RL: defensor DQN, atacante de policy gradient y RQ2

## Pregunta

**RQ2:** ¿puede un defensor entrenado con RL competir con ModSecurity en la frontera entre detección y falsos positivos, y qué tan fuerte es un atacante de policy gradient contra él? Este capítulo responde además la parte de **RQ5** que toca al defensor *estático* (entrenado contra oponentes fijos): cuánto generaliza a familias de ataque y a tráfico benigno que no vio. Esa es la línea base contra la que la Fase 4 compara al defensor de *self-play*.

El protocolo general (runner, semillas, IC por *bootstrap*) es el del capítulo 3. Lo que agrega esta fase se resume en la sección siguiente.

## Protocolo propio de la fase

- **Defensor en el runner.** `Defender-v0` corre con `make run` desde esta fase. Salvo que el experimento diga otra cosa, el defensor entrena contra un *pool* uniforme de los tres atacantes fijos (`corpus-replay`, `random-mutation`, `ATK-REF-0`) con `attack_ratio = 0,1`; cada sesión de ataque sortea su atacante con el RNG del entorno.
- **Selección de modelo en `val`.** Se agregó la suite `defender-val-v1` (2 000 sesiones del split `val`). El checkpoint de cada run es el punto de evaluación de mayor TPR en `val` sujeto a FPR en `val` ≤ FPR de `modsec-pl2` en `val`; ese tope (`fpr_cap`) lo mide el runner al empezar. **`fpr_cap` = 0,0**: `modsec-pl2` no tiene ni un falso positivo en las sesiones benignas de `val` (`results/summary/modsec_defender_suites.csv`). La regla exige entonces FPR = 0 exacto en `val`.
- **Agregación de una suite.** Una suite del defensor se juega una vez por atacante; las métricas se calculan sobre todos los requests juntos (contrato de métricas 1.3) y además por atacante (`tpr@<atacante>`).
- **Experimentos solo de evaluación.** EXP-F6 y EXP-F7 no entrenan: vuelven a evaluar checkpoints de EXP-F5 en otras suites (`wafarena.evaluate`, contrato de experimentos 1.3). Cada resultado conserva el `run_id` del run que entrenó el checkpoint.
- **ModSecurity como referencia.** ModSecurity no aprende y las suites son fijas, así que PL1–PL4 se evalúan una vez y no tienen IC.

## Defensor lineal (EXP-E1) y triada mortal (EXP-E2)

**EXP-E1.** Q-learning y SARSA semi-gradiente con Q(s, a) = w_a · [features, 1], 100 000 pasos, 5 semillas, contra el *pool* por defecto. En `defender-eval-v1`: Q-learning TPR = 0,955 [0,895; 0,991], FPR = 0,016 [0,011; 0,019], F1 = 0,935 [0,915; 0,947]; SARSA TPR = 0,950 [0,879; 0,991], FPR = 0,022 [0,016; 0,028], F1 = 0,919 [0,892; 0,940] (`results/summary/EXP-E1.csv`). Ninguno de los 50 puntos de evaluación (2 métodos × 5 semillas × 10 evaluaciones) llega a FPR = 0 en `val`, así que ninguno cumple la regla de selección. Un modelo lineal no basta para separar sin falsos positivos.

**EXP-E2.** Aproximación lineal + *bootstrapping* + datos *off-policy* de una política uniforme fija (Q-learning, α = 0,05, γ = 0,99), contra SARSA *on-policy* con los mismos α y γ, 3 semillas. La norma de los pesos de la configuración *off-policy* crece sin estabilizarse, de ≈ 19–22 a los 5 000 pasos a 232–309 a los 100 000, y el error TD medio sube a 8,5–11,8. La *on-policy* se estabiliza en ‖w‖ ≈ 50 con |δ| ≈ 1,1 (`results/summary/EXP-E2_weight_norm.csv`, `report/figuras/EXP-E2_weight_norm.png`). Es el comportamiento que predice la triada mortal (Sutton y Barto, sección 11.3). En 100 000 pasos se ve como crecimiento sostenido, no como un desborde a infinito.

## DQN: prueba de cordura y ablación (EXP-F1 a EXP-F4)

**Prueba de cordura.** Antes de usar DQN en el laboratorio se verificó en CartPole-v1 (60 000 pasos, 3 semillas por variante). Cada 5 000 pasos se guarda el mejor *snapshot* en episodios de selección, y ese *snapshot* se confirma en 20 episodios distintos; aprueba con retorno medio ≥ 195. Aprobaron **12 de 12** (`results/summary/dqn_cartpole_sanity.csv`). El primer criterio probado, la política *final* tras 60 000 pasos, aprobó solo 6 de 12 con el mismo código: DQN en CartPole aprende y luego oscila. Por ejemplo, Dueling semilla 0 llega a 314 a los 15 000 pasos y termina en 19,5. Ese criterio medía la estabilidad del final del entrenamiento, no si la implementación aprende, y se reemplazó sin tocar ningún hiperparámetro.

**Ablación.** Cuatro variantes con los mismos hiperparámetros (α = 4, 150 000 pasos), cada una con una mejora más que la anterior, 5 semillas (`results/summary/EXP-F_ablation.csv`, `report/figuras/EXP-F_ablation.png`):

| Variante | TPR | FPR | F1 | Q-ALLOW | ataques que pasaron en el *batch* |
|---|---|---|---|---|---|
| base (EXP-F1) | 0,9970 [0,9943; 0,9998] | 0,0000 [0,0000; 0,0000] | 0,9985 | 0,162 [−0,005; 0,340] | 0,0058 [0,0056; 0,0061] |
| + Double (EXP-F2) | 0,9955 [0,9925; 0,9986] | 0,0000 [0,0000; 0,0000] | 0,9978 | 0,122 [−0,046; 0,277] | 0,0059 [0,0057; 0,0063] |
| + Dueling (EXP-F3) | 0,9984 [0,9967; 0,9994] | 0,0002 [0,0000; 0,0005] | 0,9987 | 0,199 [0,130; 0,304] | 0,0055 [0,0053; 0,0058] |
| + PER (EXP-F4) | 0,9828 [0,9740; 0,9917] | 0,0000 [0,0000; 0,0000] | 0,9913 | 0,208 [0,003; 0,365] | 0,0281 [0,0257; 0,0303] |

Q-ALLOW está en unidades de recompensa escalada (`reward_scale = 0,1`). Ninguna de las tres hipótesis del catálogo se confirma con el IC de la diferencia (`results/summary/EXP-F_ablation_diffs.csv`):

- **Double** no reduce de forma detectable la Q de `ALLOW` en ataques: −0,041 [−0,288; 0,195].
- **Dueling** no cambia el TPR de forma detectable: +0,003 [−0,0004; 0,006].
- **PER** sí cumple su mecanismo: repite unas 5 veces más ataques que pasaron. Pero **baja** el TPR, −0,016 [−0,025; −0,007], y el F1, −0,007 [−0,012; −0,003].

Con TPR ≈ 0,99 sin PER casi no quedan ataques que se escapen, y sobremuestrear esos pocos no ayuda.

Ya el DQN base supera de lejos al lineal: la red no lineal separa sin falsos positivos donde el lineal no puede. La mejor variante en `val` bajo la regla de selección es Double + Dueling (TPR medio en `val` 0,99929, 5/5 semillas con FPR = 0), y es la que usa EXP-F5. Se eligió en `val`; `test` no participó.

## Frontera de Pareto contra ModSecurity (EXP-F5)

Double + Dueling con α ∈ {1, 2, 4, 8, 16}, β = α/4 y γ = α/8, 5 semillas por α, en `defender-eval-v1` (`results/summary/EXP-F5.csv`, `report/figuras/EXP-F5_pareto.png`):

| Defensor | TPR | FPR |
|---|---|---|
| DQN α = 1 | 0,9809 [0,9741; 0,9896] | 0,0005 [0,0000; 0,0015] |
| DQN α = 2 | 0,9958 [0,9918; 0,9986] | 0,0002 [0,0000; 0,0004] |
| DQN α = 4 | 0,9984 [0,9967; 0,9994] | 0,0002 [0,0000; 0,0005] |
| DQN α = 8 | 0,9968 [0,9922; 0,9995] | 0,0000 [0,0000; 0,0000] |
| DQN α = 16 | 0,9987 [0,9979; 0,9994] | 0,0000 [0,0000; 0,0000] |
| `modsec-pl1` | 0,7150 | 0,0000 |
| `modsec-pl2` | 0,9725 | 0,0000 |
| `modsec-pl3` | 1,0000 | 0,3327 |
| `modsec-pl4` | 1,0000 | 0,3844 |

La dominancia se decide de forma conservadora, con todo el IC: un α domina a un PL solo si todo su IC de TPR queda en o sobre el TPR del PL y todo su IC de FPR en o bajo el FPR del PL, con al menos una desigualdad estricta (`results/summary/EXP-F5_dominance.csv`).

- **PL1 y PL2 quedan dominados por α = 8 y α = 16:** mismo FPR = 0 y más detección en todo el IC.
- **PL3 y PL4 no quedan dominados:** detectan el 100 % de los ataques y ningún α llega a TPR = 1 en todo su IC. Pagan por eso un FPR de 0,33–0,38, dos órdenes de magnitud sobre el del DQN.

El barrido no produce el compromiso que se esperaba: el FPR ya es ≈ 0 desde α = 1 y el TPR no es monótono en α. La frontera del DQN es casi un punto en FPR ≈ 0, no una curva.

**Selección de `DEF-REF-1`.** 24 de los 25 checkpoints cumplen la regla y 7 empatan exactamente con TPR = 1,0 y FPR = 0,0 en `val`. El empate se rompe solo con `val` (ADR-0010): menor FPR, mayor F1, mayor TPR medio en `val` de su α y menor semilla. **`DEF-REF-1` = EXP-F5 `alpha-4`, semilla 0** (`results/summary/DEF-REF-1_selection.csv`, `checkpoints/refs/DEF-REF-1/`).

## Generalización del defensor estático (EXP-F6, EXP-F7)

Las 5 semillas de la configuración de `DEF-REF-1` (EXP-F5 `alpha-4`) se evaluaron en las dos suites con datos no vistos (`results/summary/EXP-F6F7_generalization.csv`):

| Suite | Defensor | TPR | FPR | FPR-h |
|---|---|---|---|---|
| `defender-eval-family-v1` (familias no vistas) | DQN | 1,0000 [1,0000; 1,0000] | 0,0002 [0,0000; 0,0005] | 0,0000 |
| | `modsec-pl1` / `pl2` | 0,8547 / 0,9926 | 0,0000 / 0,0000 | 0,0000 / 0,0000 |
| | `modsec-pl3` / `pl4` | 1,0000 / 1,0000 | 0,3327 / 0,3844 | 0,3327 / 0,3844 |
| `defender-eval-hard-v1` (benignos difíciles) | DQN | 0,9997 [0,9992; 1,0000] | **0,3385 [0,2775; 0,3996]** | 0,0583 [0,0000; 0,1333] |
| | `modsec-pl1` / `pl2` | 0,9113 / 0,9846 | 0,0000 / 0,0000 | 0,0000 / 0,0000 |
| | `modsec-pl3` / `pl4` | 1,0000 / 1,0000 | 0,5105 / 1,0000 | 0,5105 / 1,0000 |

- **Familias no vistas: el DQN generaliza.** Atacante por atacante su TPR sigue en 1,0, igual que en `defender-eval-v1`.
- **Benignos difíciles: el DQN no generaliza.** Su FPR sube de ≈ 0 a 0,34; el cambio respecto a `defender-eval-v1` es +0,338 [+0,277; +0,399]. Queda peor que PL1 y PL2, que no tienen falsos positivos, y mejor que PL3 (0,51) y PL4 (1,00). La mayoría de esos falsos positivos son acciones blandas (captcha, *rate limit*): el FPR-h es 0,058.

Esta es la debilidad que la Fase 4 debería atacar. Una nota de lectura: las dos suites usan solo los atacantes con guion (sin `ATK-REF-0`), así que un TPR agregado no es comparable directamente con el de `defender-eval-v1`; la comparación justa es atacante por atacante.

## Qué aprende el defensor: ablaciones de observación (ABL-1, ABL-2)

La configuración de `DEF-REF-1` (EXP-F5 `alpha-4`) se reentrenó con una máscara de observación configurable por YAML, sin tocar el contrato del entorno: la máscara vive en el agente y viaja con el checkpoint. Son 5 semillas por configuración, en `defender-eval-v1` (`results/summary/ABL_comparison.csv`):

| Configuración | TPR | Diferencia de TPR con la completa | F1 |
|---|---|---|---|
| Completa (37 features) | 0,9984 [0,9967; 0,9994] | — | 0,9987 [0,9976; 0,9997] |
| ABL-1: sin scores de ModSecurity (12–15) | 0,9982 [0,9974; 0,9991] | −0,0002 [−0,0017; +0,0017] | 0,9991 [0,9987; 0,9996] |
| ABL-2: sin sesión ni ventana (16–36) | 1,0000 [1,0000; 1,0000] | +0,0016 [+0,0006; +0,0033] | 1,0000 [1,0000; 1,0000] |

**El DQN no depende de ModSecurity.** Sin sus scores detecta igual: las 12 features del request bastan para separar los ataques de este corpus del tráfico benigno. Por eso dominar a `modsec-pl2` en EXP-F5 no consiste en copiar un nivel de paranoia. Quitar la sesión y la ventana incluso mejora un poco, de forma detectable: en estas suites cada request se decide por sí mismo y la historia no aporta. Esto matiza la motivación del defensor híbrido (ADR-0003) solo en lo que estas suites pueden medir.

## Atacante de policy gradient (EXP-G1 a EXP-G3) y entropía (EXP-G4)

**EXP-G1 a EXP-G3.** REINFORCE con línea base, A2C y PPO con GAE sobre la observación de 288 dimensiones, 200 000 pasos y 5 semillas, entrenados y evaluados contra `modsec-pl1` y contra `DEF-REF-1`, en `attacker-eval-v1` (`results/summary/EXP-G1.csv` a `EXP-G3.csv`):

| Atacante | ER contra `modsec-pl1` | ER contra `DEF-REF-1` |
|---|---|---|
| REINFORCE | 0,0000 [0,0000; 0,0000] | 0,0040 [0,0020; 0,0050] |
| A2C | 0,0000 [0,0000; 0,0000] | 0,0000 [0,0000; 0,0000] |
| PPO | 0,0000 [0,0000; 0,0000] | 0,0010 [0,0000; 0,0030] |
| `ATK-REF-0` (referencia) | 0,000 | 0,000 |

`ATK-REF-0` viene de `results/summary/ATK-REF-0_eval.csv`; es una sola evaluación porque el checkpoint y la suite son fijos. Contra ModSecurity PL1 ningún método evade, lo mismo que con los atacantes clásicos del capítulo 4: con los 16 operadores el techo sigue estando en el espacio de ataque. Contra `DEF-REF-1` hay evasiones raras. Las de REINFORCE tienen un IC que excluye el 0, así que supera a `ATK-REF-0`, pero se trata de menos de un episodio de 200 por semilla. QFE vale 10 en todas las semillas con evasión, y DIV queda indefinida porque ninguna semilla tiene dos payloads exitosos distintos.

**El punto ciego de la consulta 10.** Todas las evasiones contra `DEF-REF-1` caen exactamente en la décima consulta de la sesión. Un diagnóstico exploratorio (`scripts/diag_defref1_session.py`, `results/summary/DEF-REF-1_session_diag.csv`) muestra que la política del DQN cambia con la longitud de la sesión justo ahí: frente al mismo payload sin mutar bloquea las consultas 1 a 9 y desde la 10 pasa a `HONEYPOT`. Una explicación posible, **no verificada**, es que en `Defender-v0` los atacantes del *pool* abandonan tras 10 bloqueos, así que el DQN casi no vio sesiones de ataque más largas y en el punto de transición algunos payloads mutados reciben `ALLOW`. Es el tipo de debilidad que un oponente que se adapta (Fase 4) debería encontrar.

**EXP-G4.** PPO contra `DEF-REF-1` con coeficiente de entropía 0, 0,01 y 0,05, 5 semillas (`results/summary/EXP-G4_entropy.csv`, `report/figuras/EXP-G4_div_er.png`). El bono sí vuelve más estocástico al atacante: la entropía de la política al final del entrenamiento pasa de 0,33 [0,18; 0,49] a 0,68 [0,48; 0,89] y a 2,19 [2,13; 2,26], de un máximo de ln 17 ≈ 2,83. El ER no cambia de forma detectable: 0,0010 [0,0000; 0,0030], 0,0010 [0,0000; 0,0030] y 0,0000. **Con estos datos no se puede afirmar que un atacante más estocástico sea más difícil de bloquear.** Con una evasión cada 1 000 episodios la pregunta no se puede responder en este espacio de ataque, y DIV no existe en ninguna configuración.

## Latencia (F3-T10)

`DEF-REF-1` servido por el proxy en modo real, con 2 000 requests del tráfico de `defender-eval-v1`, cada uno enviado a `modsec-pl2` solo y a través del proxy, en orden alternado y con la máquina sin otra carga (`results/summary/latency.csv`):

| Medida | p50 | p95 |
|---|---|---|
| LAT (agregado sobre ModSecurity solo) | 65,6 ms | 74,3 ms |
| `modsec-pl2` solo | 15,9 ms | 17,9 ms |
| Proxy con `DEF-REF-1` | 81,7 ms | 90,3 ms |
| Decisión del DQN sola | 0,034 ms | 0,042 ms |

Casi toda la latencia agregada es del proxy y no de la red neuronal. El proxy consulta ModSecurity PL1–PL4 en secuencia para armar las features 12–15 antes de decidir, del orden de cuatro veces una consulta sola. Como ABL-1 muestra que el DQN no necesita esos scores, un defensor sin ellos, o un proxy que consulte los cuatro niveles en paralelo, bajaría la latencia casi a la de ModSecurity solo.

## Referencias publicadas

- **`DEF-REF-1`:** EXP-F5 `alpha-4`, semilla 0 (DQN Double + Dueling, α = 4), elegido con la regla del plan más el desempate de ADR-0010, todo en `val`.
- **`ATK-REF-1`:** EXP-G3 `ppo-defref1`, semilla 1, el mejor PPO por ER en `val` contra `DEF-REF-1`; tiene ER = 0,005 en `val`.

Las dos cargan con `load_checkpoint` y funcionan como oponentes en 100 episodios (`results/summary/refs_check.csv`). Son el punto de partida del *self-play* de la Fase 4.

## Respuesta a RQ2

**Sí: un defensor entrenado con RL compite con ModSecurity en la frontera entre detección y falsos positivos, y la mejora en una parte de ella.**

- En `defender-eval-v1`, el DQN (Double + Dueling) **domina a ModSecurity PL1 y PL2**: con el mismo FPR = 0 detecta más ataques, con TPR ≈ 0,997–0,999 contra 0,715 y 0,973, comparando con el IC completo.
- **PL3 y PL4 no quedan dominados**, porque detectan el 100 %. Sin embargo, pagan un FPR de 0,33–0,38, mientras que el DQN tiene un FPR del orden de 10⁻⁴.
- El DQN no imita a ModSecurity: sin sus scores detecta igual (ABL-1).
- La ventaja tiene dos límites: el defensor estático no generaliza a tráfico benigno difícil no visto (FPR 0,34 en `defender-eval-hard-v1`), y cuesta ~66 ms de latencia agregada por cómo está construido el proxy.
- **Del lado del atacante**, los métodos de *policy gradient* no son más fuertes que los tabulares contra ModSecurity (ER = 0 los tres). Contra el DQN sí encuentran una grieta, aunque estrecha: evasiones raras y siempre en la consulta 10.

## Limitaciones de esta fase

- **Las suites son fáciles para el DQN.** TPR y F1 ≈ 0,99 dejan poco espacio para distinguir variantes. Por eso la ablación de DQN no separa Double de la base ni Dueling de Double, y el barrido de α no dibuja una curva.
- **`fpr_cap` = 0.** La regla de selección exige FPR = 0 exacto en `val`, porque `modsec-pl2` no tiene falsos positivos ahí. Eso deja muchos empates, que se resolvieron con ADR-0010.
- **El espacio de ataque limita a los atacantes.** Con los 16 operadores, ningún atacante evade ModSecurity, así que las preguntas sobre el atacante (EXP-G4, la DIV) apenas tienen señal. Es el mismo techo del capítulo 4.
- **Entorno sin vectorizar.** El riesgo «PPO lento» del plan no se materializó: un run de PPO de 200 000 pasos tarda 303 s solo en la máquina, y uno de DQN de 150 000 pasos 202 s (corridas de verificación del handoff, idénticas en `final_eval.json` a las de la campaña con la misma semilla). Se entrenó con un solo entorno, sin entornos vectorizados.
- **Incidentes de infraestructura durante los runs**, corregidos o mitigados y documentados en los *Hallazgos* de la Fase 3:
  - una colisión de nombres de temporales en la caché, porque todo contenedor tiene PID 1;
  - el disco lleno por los *audit logs* de ModSecurity, que nunca se rotan.
