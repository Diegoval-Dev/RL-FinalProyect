# HANDOFF-2: Daniel Dubón → Joaquín Puente

> Completar al cerrar la Fase 2 con el prompt [P6](../04-metodologia-ai-first/prompts.md#p6--redactar-el-handoff).

| | |
|---|---|
| **Tag** | `v0.2-fase2` |
| **Commit** | [COMPLETAR] |
| **Fecha de entrega** | [COMPLETAR] |
| **Ventana de aceptación** | [COMPLETAR] |
| **Estado** | Pendiente |

## 1. Qué se entrega

[COMPLETAR]

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| agentes y checkpoints | [COMPLETAR] | |
| métricas | [COMPLETAR] | Se agrega `ATK-REF-0` a `defender-eval-v1` |
| experimentos | [COMPLETAR] | |
| (heredados de la Fase 1) | [COMPLETAR] | |

## 3. Cómo correrlo desde cero

[COMPLETAR]

## 4. Checklist de aceptación

- [ ] Todo el checklist de HANDOFF-1 sigue pasando.
- [ ] `make run CONFIG=configs/exp/EXP-D1/<un yaml>.yaml` con una sola semilla corre de punta a punta y genera el árbol de resultados del contrato.
- [ ] Repetir el mismo run produce un `eval.csv` idéntico.
- [ ] El runner rechaza un YAML con `split: test` en entrenamiento.
- [ ] `make summarize EXP=EXP-A1` regenera `results/summary/EXP-A1.csv` idéntico al versionado.
- [ ] `load_checkpoint("checkpoints/refs/ATK-REF-0")` funciona y el agente corre 100 sesiones dentro de `Defender-v0` vía `AttackerDriver`.
- [ ] La prueba estática de acceso a claves `gt_` pasa.

## 5. Resultados entregados

| Experimento | Resumen | Hallazgo principal |
|---|---|---|
| EXP-A1 | [COMPLETAR] | [COMPLETAR] |
| EXP-A2 | [COMPLETAR] | [COMPLETAR] |
| EXP-B1 | [COMPLETAR] | [COMPLETAR] |
| EXP-C1 | [COMPLETAR] | [COMPLETAR] |
| EXP-D1 | [COMPLETAR] | [COMPLETAR] |
| EXP-D2 | [COMPLETAR] | [COMPLETAR] |
| Tabla RQ1 | `results/summary/RQ1_table.csv` | [COMPLETAR] |

## 6. Checkpoints de referencia publicados

| ID | Ruta | Cómo se eligió | ER en `val` contra `modsec-pl1` |
|---|---|---|---|
| `ATK-REF-0` | `checkpoints/refs/ATK-REF-0/` | Mejor tabular por ER en `val` | [COMPLETAR] |

## 7. Recortes y desviaciones del plan

[COMPLETAR]

## 8. Problemas conocidos

[COMPLETAR]

## 9. Datos útiles para la siguiente fase

- Tiempo típico de un run tabular de 200 000 pasos: [COMPLETAR]
- Hiperparámetros que funcionaron mejor por método: [COMPLETAR]
- Cómo agregar un algoritmo nuevo al runner (archivos a tocar): [COMPLETAR]

## 10. Capítulos del informe entregados

- `report/capitulos/04-atacante-clasico.md`
- Sección de protocolo experimental en `report/capitulos/03-laboratorio.md`

## 11. Firma de aceptación

- [ ] Joaquín corrió el checklist completo en su máquina.
- [ ] Problemas encontrados en la ventana: _(lista o "ninguno")_
- [ ] Aceptado por: ______ · Fecha: ______
- [ ] `CLAUDE.md` actualizado: **Fase activa: 3**.
