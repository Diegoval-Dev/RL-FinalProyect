# Contrato: experimentos y resultados

**Versión:** 1.2 · **Implementa:** Fase 2 (F2-T03), Fase 3 (F3-T02) · **Archivo:** `wafarena/run.py`

## Ejecución

```bash
make run CONFIG=configs/exp/EXP-D1/qlearning-pl1.yaml
# equivale a (dentro del contenedor `runner`, que alcanza la base de datos y ModSecurity)
docker compose -f lab/docker-compose.yml run --rm runner python -m wafarena.run --config configs/exp/EXP-D1/qlearning-pl1.yaml
```

Opciones de `python -m wafarena.run` (pasables con `make run ... RUN_ARGS="..."`): `--allow-dirty`, `--overwrite`, `--results <dir>`. Un run existente no se sobrescribe sin `--overwrite`.

## Configuración YAML

```yaml
exp_id: EXP-D1                    # del catálogo
run_name: qlearning-pl1
owner: daniel
rq: [RQ1]
seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

env:
  id: WafArena/Attacker-v0
  backend: fast
  split: train
  defender: {type: modsec, paranoia_level: 1}
  query_budget: 50

agent:
  algo: qlearning
  params:
    alpha: 0.1
    gamma: 0.99
    epsilon: {start: 1.0, end: 0.05, decay_steps: 50000}

train:
  total_steps: 200000

eval:
  suites: [attacker-eval-v1]
  every_steps: 10000
  final: true

logging:
  tensorboard: true
  wandb: false

checkpoint:
  save_best_on: val            # el mejor checkpoint se elige en val, nunca en test
```

Reglas: el runner valida el YAML contra un esquema (claves desconocidas son error), rechaza cualquier `env.split` distinto de `train` (ni `val` ni los splits de prueba se usan para entrenar) y falla si `exp_id` no existe en el [catálogo](../07-experimentos/catalogo.md). Los defaults se expanden en `config.resolved.yaml`. `eval.suites` debe corresponder al entorno (suites del atacante para `Attacker-v0`, del defensor para `Defender-v0`). `logging.wandb: true` aún no está soportado.

## Selección de modelo y evaluación

- Cada `eval.every_steps` pasos (y al final) el agente se evalúa de forma voraz (`explore=False`) en la suite de validación `attacker-val-v1` (split `val`, [métricas](metricas.md)). Cada punto es una fila de `eval.csv` (`step`, `suite`, y todas las métricas del atacante).
- Se guarda como `checkpoint/` el punto con mayor `evasion_rate` en `val`; el empate se rompe con menor `qfe_c`. Los splits de prueba nunca participan en la selección.
- **Defensor (`Defender-v0`).** Se evalúa en `defender-val-v1`. La selección sigue la regla de `DEF-REF-1` del plan de la Fase 3: el tope de FPR (`fpr_cap`) es el FPR de `modsec-pl2` en `defender-val-v1`, medido por el runner al empezar (no se escribe a mano). Todo punto con `fpr <= fpr_cap` le gana a cualquiera que lo supere; entre ellos gana el de mayor `tpr` y luego el de menor `fpr`; si ninguno cumple, gana el de menor `fpr` y luego el de mayor `tpr`. En empate exacto se queda el punto más temprano. `eval.csv` lleva las métricas del defensor ([métricas](metricas.md)) y `final_eval.json` agrega `fpr_cap`. `train.csv` tiene una fila por sesión: `step`, `episode`, `return`, `length`, `attack`, `blocked` (requests con acción ≠ `ALLOW`), `allowed_effect` (ataques con efecto que dejó pasar), `complete`, más las `m_<nombre>`; `attack` y `allowed_effect` salen de claves `gt_*` y son solo registro: el agente nunca las ve.
- El `meta.yaml` del checkpoint guarda en `train.agent_params` los parámetros del agente del YAML, para que `load_checkpoint` reconstruya el agente con los mismos hiperparámetros.
- Terminado el entrenamiento, el runner recarga el checkpoint desde disco y lo evalúa en cada suite de `eval.suites` (si `eval.final`). El resultado es `final_eval.json`: `{best_step, val, suites: {<suite>: {episodes, evasions, evasion_rate, qfe, qfe_c, diversity, uniqueness, break_rate}}}`.
- `train.csv` tiene una fila por episodio (`step`, `episode`, `return`, `length`, `evaded`, `banned`, `queries_used`, `mutation_attempts`, `broken`, `complete`) más `m_<nombre>` con el promedio por episodio de las métricas que devuelve `Agent.observe`. El último episodio, si el presupuesto de pasos lo corta, lleva `complete = 0`.
- `Transition.info` corresponde a `next_obs` (el `info` posterior al paso).

## Salida

```
results/<exp_id>/<run_name>/s<seed>/
├── config.resolved.yaml     # config con todos los valores por defecto expandidos
├── meta.yaml                # git sha, rama, fecha, máquina, versiones de contratos, duración
├── train.csv                # métricas de entrenamiento por paso
├── eval.csv                 # métricas de evaluación por punto de evaluación
├── final_eval.json          # métricas finales por suite
├── tb/                      # TensorBoard
└── checkpoint/              # mejor checkpoint en val
```

`run_id = <exp_id>__<run_name>__s<seed>__<git_sha_corto>`.

El runner se niega a correr con cambios sin commit en `wafarena/` o `configs/` (salvo `--allow-dirty`, que queda marcado en `meta.yaml` y no vale para el informe).

## Resúmenes versionados

`results/` no se versiona salvo `results/summary/`:

```
results/summary/<exp_id>.csv     # una fila por run_name con media e IC de cada métrica final
```

Lo genera `make summarize EXP=<exp_id>`: una fila por `run_name` y suite, con `n_seeds`, los `git_shas` de los runs, cuántos se corrieron con `--allow-dirty` (`dirty_runs`) y, por métrica, `<métrica>_mean`, `_low` y `_high` (IC 95 % por bootstrap sobre semillas; las semillas con valor `nan` se omiten en esa métrica y, si todas lo son, las celdas quedan vacías). Las figuras del informe se generan desde estos CSV con scripts en `report/figuras/make_<exp_id>.py`.

## Registro

Cada experimento terminado agrega una fila a [registro.md](../07-experimentos/registro.md). Un número del informe se cita como `(EXP-D1, qlearning-pl1, 10 semillas)`.

## Historial

- 1.0 — versión inicial.
- 1.1 — Detalle de la selección de modelo en `val`, formatos de `eval.csv`, `train.csv` y `final_eval.json`, y opciones de la línea de comandos. Compatible hacia atrás.
- 1.2 — Runs de `Defender-v0`: selección en `defender-val-v1` con la regla de `DEF-REF-1`, columnas de `train.csv` del defensor y `train.agent_params` en el checkpoint (F3-T02). Compatible hacia atrás.
