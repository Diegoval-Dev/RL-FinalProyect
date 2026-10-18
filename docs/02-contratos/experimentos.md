# Contrato: experimentos y resultados

**Versión:** 1.0 · **Implementa:** Fase 2 (F2-T02) · **Archivo:** `wafarena/run.py`

## Ejecución

```bash
make run CONFIG=configs/exp/EXP-D1/qlearning-pl1.yaml
# equivale a
uv run python -m wafarena.run --config configs/exp/EXP-D1/qlearning-pl1.yaml
```

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

Reglas: el runner valida el YAML contra un esquema, rechaza `split` de prueba en entrenamiento y falla si `exp_id` no existe en el [catálogo](../07-experimentos/catalogo.md).

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

Lo genera `make summarize EXP=<exp_id>`. Las figuras del informe se generan desde estos CSV con scripts en `report/figuras/make_<exp_id>.py`.

## Registro

Cada experimento terminado agrega una fila a [registro.md](../07-experimentos/registro.md). Un número del informe se cita como `(EXP-D1, qlearning-pl1, 10 semillas)`.

## Historial

- 1.0 — versión inicial.
