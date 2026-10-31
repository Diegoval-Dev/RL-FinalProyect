# HANDOFF-3: Joaquín Puente → Nelson García

> Completado al cerrar la Fase 3 con el prompt [P6](../04-metodologia-ai-first/prompts.md#p6--redactar-el-handoff).

| | |
|---|---|
| **Tag** | `v0.3-fase3` (se crea en `main` tras mergear la pila de PR de la Fase 3, #18 a #29) |
| **Commit** | el de `main` con el tag `v0.3-fase3` |
| **Fecha de entrega** | 2026-10-25 |
| **Ventana de aceptación** | 1 día hábil desde que el tag exista en `main` |
| **Estado** | Aceptado con salvedades |

## 1. Qué se entrega

Lo que se entrega en esta fase:

- **Defensores.** Corren en el runner, con un *pool* de oponentes y una suite de validación propia (`defender-val-v1`), y se seleccionan con la regla de `DEF-REF-1`. Hay un defensor lineal semi-gradiente y un DQN estilo CleanRL en un archivo, con Double, Dueling y PER activables por YAML y una máscara de observación para ablaciones.
- **Atacantes.** REINFORCE, A2C y PPO en un archivo.
- **Herramientas.** `DefenderDriver`; defensores aprendidos dentro de `Attacker-v0`; experimentos solo de evaluación (`wafarena.evaluate`); el proxy sirviendo un checkpoint (`proxy-learned`).
- **Referencias.** `DEF-REF-1` y `ATK-REF-1`.
- **Respuesta a RQ2.** El DQN domina a ModSecurity PL1 y PL2 en la frontera detección/falsos positivos; PL3 y PL4 no quedan dominados. Está en el capítulo 5 del informe.
- **Línea base de RQ5 (generalización del defensor estático).** Generaliza a familias no vistas, pero no a benignos difíciles no vistos (FPR 0,34).

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| env-defensor | 1.2 | `{"type": "pool"}` implementado (entradas por nombre, id de referencia o ruta; sorteo por sesión con el RNG del entorno); `attacker` acepta un objeto `AttackerPolicy` (F3-T02) |
| env-atacante | 1.1 | `defender={"type": "checkpoint"}` implementado (ruta o id de referencia, vía `DefenderDriver`); el defensor recibe las features de sesión y ventana del episodio (F3-T08) |
| agentes y checkpoints | 1.1 | `DefenderDriver` en `wafarena/defenders/driver.py`; se borra el borrador sin uso `wafarena/envs/drivers.py` (F3-T08) |
| métricas | 1.4 | Suite `defender-val-v1` y agregación por atacante de las suites del defensor (1.3, F3-T02); métrica Q-ALLOW (1.4, F3-T03) |
| experimentos | 1.3 | Runs de `Defender-v0` con la regla de selección de `DEF-REF-1` y `train.agent_params` en el checkpoint (1.2, F3-T02); experimentos solo de evaluación (1.3, F3-T07) |
| (heredados) | sin cambios | oráculo 1.1, operadores-mutación 1.1, features 1.0, datos-y-splits 1.0 |

Todos los cambios son compatibles hacia atrás.

## 3. Cómo correrlo desde cero

```bash
make setup                     # ahora instala PyTorch CPU (ADR-0009); la imagen runner pesa ~2,9 GB
make lab-up
make lint && make test
make test-lab
make dqn-sanity                # DQN en CartPole-v1, 4 variantes × 3 semillas
make run CONFIG=configs/exp/EXP-F3/dqn-double-dueling.yaml RUN_ARGS="--seed 0"   # defensor DQN
make run CONFIG=configs/exp/EXP-G3/ppo-defref1.yaml RUN_ARGS="--seed 0"          # atacante PPO
make evaluate CONFIG=configs/exp/EXP-F6/def-ref-1-candidate.yaml                 # solo evaluación
make modsec-defender-suites    # ModSecurity PL1-PL4 en las suites del defensor
make check-refs                # DEF-REF-1 y ATK-REF-1 como oponentes, 100 episodios
make latency                   # levanta proxy-learned y mide LAT de DEF-REF-1
make summarize EXP=EXP-F5 && uv run --group report python report/figuras/make_EXP-F5.py
```

`make run`, `make evaluate`, `make check-refs` y `make latency` corren dentro del contenedor `runner`. Para correr varias semillas en paralelo, lo probado sin fallas fue **8 procesos a la vez** (ver §8).

## 4. Checklist de aceptación

- [ ] Todo el checklist de HANDOFF-2 sigue pasando (y con él el de HANDOFF-1).
- [x] Un run de DQN de una semilla con la mejor variante (`configs/exp/EXP-F3/dqn-double-dueling.yaml --seed 0`) corre de punta a punta en menos de 10 minutos en CPU.
- [x] Un run de PPO de una semilla (`configs/exp/EXP-G3/ppo-defref1.yaml --seed 0`) corre de punta a punta.
- [x] `DEF-REF-1` y `ATK-REF-1` cargan con `load_checkpoint` y funcionan como oponentes en 100 episodios vía los drivers (`make check-refs`).
- [ ] `make summarize EXP=EXP-F5` regenera el CSV y el script de la figura de Pareto la regenera.
- [x] La máscara de observación de ABL-1 y ABL-2 se activa solo desde YAML (`agent.params.obs_mask`).

_Verificación del autor (P6), 2026-10-25, en la punta de la rama `f3/F3-T12-informe-handoff`:_

- **Checklist de HANDOFF-2.** `make lint` → `All checks passed!` / `191 files already formatted`; `make test` → 672 passed; `make verify-splits` → `splits verified`; `make test-lab` → 12 + 134 passed; `make smoke` → sin diff en `smoke.csv`; YAML con `split: test` → rechazado y sin escribir nada; prueba estática de claves `gt_` → passed. El resto del checklist de HANDOFF-2 (repetir un run de EXP-D1, re-correr EXP-A1, `ATK-REF-0` en `Defender-v0`) se corrió completo en F3-T01 (*Hallazgos* de la Fase 3) y no cambió.
- **DQN, una semilla:** 202 s.
- **PPO, una semilla:** 303 s. Las dos corridas reprodujeron exactamente el `final_eval.json` de la campaña.
- **`make check-refs`:** `DEF-REF-1` (`DQNAgent`) bloqueó los 839 requests juzgados en 100 episodios; `ATK-REF-1` (`PolicyGradientAgent`) generó 289 requests de ataque en 100 sesiones, sin errores (`results/summary/refs_check.csv`).
- **`make summarize EXP=EXP-F5`:** regenera un CSV idéntico al versionado, y `make_EXP-F5.py` regenera la figura idéntica byte a byte.
- **`obs_mask`:** se lee solo de `agent.params.obs_mask` en los YAML de `configs/exp/ABL-1` y `ABL-2`; la prueba `test_obs_mask_hides_the_masked_features_from_the_network` pasa.

_Verificación del receptor (F4-T01), 2026-10-30, en `main` commit `12f17d5` (mismo árbol que `v0.3-fase3`):_

- **Checklist heredado:** `make setup`, `make lint`, `make test` (672 passed), `make verify-splits` y `make test-lab` (12 + 134 passed). Dos corridas de `scripts/smoke.py` produjeron el mismo `smoke.csv`, idéntico al versionado. Un script que usa solo la API pública de Gymnasium completó 10 episodios de `Attacker-v0` contra `modsec-pl2`. Dos corridas de `EXP-D1/qlearning-pl1` s0 (`results/_f4t01_d1a` y `_f4t01_d1b`, `run_id: EXP-D1__qlearning-pl1__s0__12f17d5`) produjeron `eval.csv` idénticos. Las pruebas unitarias cubren el rechazo de `split: test`, el filtro de claves `gt_`, `check_env` y las 100 sesiones de `ATK-REF-0`. `make summarize EXP=EXP-A1` sigue fallando porque faltan los runs crudos no versionados, como documenta HANDOFF-2 §4; por eso el primer ítem de este checklist queda abierto.
- **DQN:** un primer intento falló por `httpx.ReadTimeout` consultando ModSecurity. El siguiente terminó en 1 166,106 s; tras poblar la caché, una corrida aislada terminó en 308,051 s (< 600 s). Ambas corridas completas produjeron el mismo `final_eval.json` (`run_id: EXP-F3__dqn-double-dueling__s0__12f17d5`; raíces `results/_f4t01_retry` y `results/_f4t01_warm`). El tiempo con caché fría y el timeout quedan como hallazgos operativos.
- **PPO:** `EXP-G3/ppo-defref1` s0 terminó de punta a punta en 743,344 s, con `train.csv`, `eval.csv` y `final_eval.json` (`run_id: EXP-G3__ppo-defref1__s0__12f17d5`, `results/_f4t01_retry`).
- **Referencias y máscara:** `scripts/check_refs.py` cargó `DEF-REF-1` como `DQNAgent` y `ATK-REF-1` como `PolicyGradientAgent`; ambos corrieron 100 episodios vía sus drivers. ABL-1 y ABL-2 declaran `agent.params.obs_mask` en YAML y pasó `test_obs_mask_hides_the_masked_features_from_the_network`.
- **EXP-F5:** `make summarize EXP=EXP-F5` falla con `FileNotFoundError: no finished runs for EXP-F5`, porque faltan los runs crudos. El script `make_EXP-F5.py` sí regeneró `EXP-F5_pareto.png` idéntico byte a byte al versionado. El ítem de regeneración completa queda abierto.
- **Ventana:** esta verificación se hizo después del día hábil de aceptación contado desde la entrega del 2026-10-25. Nelson aceptó explícitamente el relevo el 2026-10-30 con las excepciones de regeneración y plazo documentadas aquí; los dos ítems no cumplidos permanecen sin marcar.

## 5. Resultados entregados

| Experimento | Resumen | Hallazgo principal |
|---|---|---|
| EXP-E1 / E2 | `results/summary/EXP-E1.csv`, `EXP-E2.csv`, `EXP-E2_weight_norm.csv` | Lineal: TPR ≈ 0,95 y FPR 0,016–0,022, sin ningún punto con FPR = 0 en `val`. Triada mortal: con datos *off-policy*, la norma de los pesos crece sin estabilizarse (232–309) y *on-policy* se estabiliza (≈ 50) |
| EXP-F1 a F4 | `EXP-F1.csv` … `EXP-F4.csv`, `EXP-F_ablation.csv`, `EXP-F_ablation_diffs.csv` | DQN base TPR = 0,9970 con FPR = 0. Ninguna hipótesis del catálogo se confirma: Double no baja Q-ALLOW de forma detectable, Dueling no cambia el TPR y PER lo **baja** (−0,016 [−0,025; −0,007]) aunque repite unas 5 veces más los ataques que pasaron |
| EXP-F5 (Pareto) | `EXP-F5.csv`, `EXP-F5_dominance.csv`, `modsec_defender_suites.csv` | α = 8 y α = 16 dominan a PL1 y PL2 con todo el IC (FPR = 0 y TPR 0,997–0,999 contra 0,715 / 0,973). PL3 y PL4 no quedan dominados: TPR = 1, con FPR 0,33–0,38 |
| EXP-F6, F7 | `EXP-F6.csv`, `EXP-F7.csv`, `EXP-F6F7_generalization.csv` | Familias no vistas: TPR = 1,0000, generaliza. Benignos difíciles no vistos: **FPR = 0,3385 [0,2775; 0,3996]**, peor que PL1/PL2 (0) y mejor que PL3/PL4 |
| EXP-G1 a G4 | `EXP-G1.csv` … `EXP-G4.csv`, `EXP-G4_entropy.csv`, `ATK-REF-0_eval.csv` | Contra `modsec-pl1` ningún método evade. Contra `DEF-REF-1`: REINFORCE ER = 0,0040 [0,0020; 0,0050], PPO 0,0010, A2C 0. Todas las evasiones caen en la consulta 10. El bono de entropía sube la entropía de la política (0,33 → 2,19) sin cambiar el ER de forma detectable; DIV queda indefinida |
| ABL-1, ABL-2 | `ABL-1.csv`, `ABL-2.csv`, `ABL_comparison.csv` | Sin scores de ModSecurity no hay diferencia detectable: el DQN no depende de ModSecurity. Sin sesión ni ventana mejora un poco (+0,0016 [+0,0006; +0,0033]) |
| Latencia | `results/summary/latency.csv` | LAT de `DEF-REF-1` p50 = 65,6 ms, p95 = 74,3 ms sobre `modsec-pl2` solo. La decisión del DQN cuesta 0,034 ms; el resto es el proxy consultando PL1–PL4 en secuencia |

## 6. Checkpoints de referencia publicados

| ID | Ruta | Cómo se eligió | Métrica en `val` |
|---|---|---|---|
| `DEF-REF-1` | `checkpoints/refs/DEF-REF-1/` | Regla de la Fase 3 (mayor TPR en `val` con FPR ≤ FPR de `modsec-pl2` en `val`, que es 0,0) sobre los 25 checkpoints de EXP-F5; 7 empataron y se desempató solo con `val` (ADR-0010, `scripts/select_def_ref.py`). Es EXP-F5 `alpha-4` s0 | TPR = 1,0, FPR = 0,0, F1 = 1,0 en `defender-val-v1` |
| `ATK-REF-1` | `checkpoints/refs/ATK-REF-1/` | Mejor PPO por ER en `val` contra `DEF-REF-1` (EXP-G3 `ppo-defref1`); empate con s2 y s3, que se rompe por menor QFE-c y luego menor semilla (`scripts/select_atk_ref.py`). Es la s1 | ER = 0,005 en `attacker-val-v1` contra `DEF-REF-1` |

## 7. Recortes y desviaciones del plan

- **Sin entornos vectorizados para PPO.** La mitigación del riesgo «PPO lento» no hizo falta en la práctica (§9), y el entrenamiento usa un solo entorno.
- **Criterio de la prueba de cordura de CartPole.** El primero, la política final, aprobó 6/12 con el mismo código; se reemplazó por el del runner (mejor *snapshot* en selección, confirmado en episodios aparte), que aprueba 12/12. Detalle en *Hallazgos* de F3-T03.
- **Figura de EXP-G4.** La aceptación pide «DIV contra ER», pero DIV es indefinida en las tres configuraciones. La figura lo dice y agrega la entropía de la política como medida directa de estocasticidad.
- **`DEF-REF-1` se publicó en F3-T05**, no en F3-T11, porque F3-T07 y F3-T08 lo necesitaban como checkpoint versionado. F3-T11 lo verificó.
- **Una regla agregada.** La regla de `DEF-REF-1` no definía desempates; se agregó ADR-0010.
- **Pendiente para la Fase 4: *pool* de defensores.** El *pool* de oponentes existe para el atacante dentro de `Defender-v0`. Para el defensor dentro de `Attacker-v0` solo existe un checkpoint fijo (`{"type": "checkpoint"}`). El *self-play* con *pool* de defensores históricos necesita un `{"type": "pool"}` también del lado del atacante.

## 8. Problemas conocidos

- **Los *audit logs* de ModSecurity nunca se rotan y llenaron el disco.** Ocupaban 24 GB (PL4 sola, 8,9 GB). A mitad de la campaña de F3-T08 el disco de la máquina llegó al 100 %, ModSecurity dejó de escribir y todas las consultas fallaron por *timeout* del *audit log*. Se truncaron con nada corriendo (el lector siempre empieza al final del archivo, el historial no se usa). **Antes de una campaña larga de *self-play*, vigilar el espacio en disco o agregar rotación al laboratorio**, que es código de la Fase 1.
- **No conviene paralelizar de más.** Con 12 runs a la vez y caché fría, como al inicio de una campaña de PPO, ModSecurity se satura. Con 8 a la vez los 39 runs pendientes terminaron sin fallas.
- **`DEF-REF-1` depende de la longitud de la sesión.** Cambia de `BLOCK` a `HONEYPOT` en la consulta 10, y todas las evasiones de los atacantes caen ahí. Es un punto ciego que el *self-play* debería encontrar.
- **`DEF-REF-1` falla en benignos difíciles no vistos** (FPR 0,34 en `defender-eval-hard-v1`). Es la debilidad principal del defensor estático y la línea base de RQ5.
- **`ATK-REF-1` es débil en términos absolutos** (ER 0,005 en `val`). El *self-play* arranca de un atacante que casi no evade. Con los 16 operadores actuales ningún atacante evade ModSecurity (capítulo 4).
- **Bug propio ya corregido: la caché de ModSecurity.** Su *flush* atómico nombraba el temporal con el PID, que es 1 en todos los contenedores, y varios runs en paralelo chocaban. Corregido con `tempfile.mkstemp` en F3-T08 (`98aa1a3`, *cherry-pick* `bb32559`).
- **La latencia del proxy es por diseño, no por el modelo.** Consulta ModSecurity PL1–PL4 en secuencia (~66 ms de los ~82 ms totales). Si la demo de la Fase 4 necesita latencia baja, consultar en paralelo o prescindir de los scores, cosa que ABL-1 respalda.
- El proxy construye la observación del defensor con las features de sesión en cero; no lleva el estado de la sesión. Para un defensor que dependa de la sesión, el comportamiento en modo real difiere del de `Defender-v0`.

## 9. Datos útiles para la siguiente fase

- **Hiperparámetros finales.** DQN: `configs/exp/EXP-F5/alpha-4.yaml` (Double + Dueling, MLP 128×128, lr 5·10⁻⁴, γ = 0,9, *buffer* 100 000, *batch* 128, *target* cada 2 000, ε de 1 a 0,05 en 50 000 pasos, huber, `reward_scale` 0,1, 150 000 pasos). PPO: `configs/exp/EXP-G3/ppo-defref1.yaml` (MLP 64×64, lr 3·10⁻⁴, `n_steps` 1 024, 4 épocas, *minibatch* 256, *clip* 0,2, λ = 0,95, entropía 0,01, 200 000 pasos).
- **Tiempo por run, una semilla sola en la máquina:** DQN de 150 000 pasos (EXP-F3) 202 s; PPO de 200 000 pasos (EXP-G3) 303 s (16 núcleos, sin otra carga, 2026-10-25). Las dos corridas reprodujeron exactamente el `final_eval.json` de la campaña con la misma semilla. Con 8–12 runs en paralelo, cada run de DQN tardó 486–604 s y cada PPO 156–528 s (logs de la campaña).
- **Costo estimado de una generación de *self-play*** con el diseño de la Fase 4 (3 iteraciones de atacante por 1 de defensor). Es una estimación derivada de los tiempos anteriores, no una medición: si cada iteración es un run completo como los de esta fase, una generación cuesta 3 × 303 + 202 ≈ 1 100 s ≈ 18,5 min en secuencia, más la evaluación contra las referencias fijas (≈ 14 s por suite del defensor), y G = 8 generaciones ≈ 2,5 h por configuración. Correr las semillas en paralelo (hasta 8) divide el tiempo de pared, no el de cada generación.
- **Comportamientos raros observados:**
  - DQN en CartPole aprende y luego oscila; hay que seleccionar el mejor *snapshot*, no el último.
  - Con `fpr_cap` = 0 muchos checkpoints empatan en `val` (ADR-0010).
  - Q-ALLOW está en unidades de recompensa escalada.
  - Las evaluaciones de `defender-eval-v1` tardan unos 14 s; `defender-val-v1` cuesta lo mismo en cada punto de evaluación.

## 10. Capítulos del informe entregados

- `report/capitulos/05-deep-rl.md`

## 11. Firma de aceptación

- [x] Nelson aceptó la verificación del checklist en su máquina con las salvedades documentadas en §4.
- [x] Problemas encontrados: timeout inicial de ModSecurity, DQN con caché fría fuera del objetivo de 10 minutos, runs crudos de EXP-A1/EXP-F5 ausentes y ventana de aceptación vencida (detalle en §4).
- [x] Aceptado por: Nelson García · Fecha: 2026-10-30 (autorizado en esta conversación, con salvedades de §4).
- [x] `CLAUDE.md` actualizado: **Fase activa: 4**.
