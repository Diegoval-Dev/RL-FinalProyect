# HANDOFF-3: Joaquín Puente → Nelson García

> Completar al cerrar la Fase 3 con el prompt [P6](../04-metodologia-ai-first/prompts.md#p6--redactar-el-handoff).

| | |
|---|---|
| **Tag** | `v0.3-fase3` |
| **Commit** | [COMPLETAR] |
| **Fecha de entrega** | [COMPLETAR] |
| **Ventana de aceptación** | [COMPLETAR] |
| **Estado** | Pendiente |

## 1. Qué se entrega

[COMPLETAR]

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| [COMPLETAR] | | |

## 3. Cómo correrlo desde cero

[COMPLETAR]

## 4. Checklist de aceptación

- [ ] Todo el checklist de HANDOFF-2 sigue pasando.
- [ ] Un run de DQN de una semilla con la mejor variante corre de punta a punta en menos de [COMPLETAR] minutos en CPU.
- [ ] Un run de PPO de una semilla corre de punta a punta.
- [ ] `DEF-REF-1` y `ATK-REF-1` cargan con `load_checkpoint` y funcionan como oponentes en 100 episodios vía los drivers.
- [ ] `make summarize EXP=EXP-F5` regenera el CSV y el script de la figura de Pareto la regenera.
- [ ] La máscara de observación de ABL-1 y ABL-2 se activa solo desde YAML.

## 5. Resultados entregados

| Experimento | Resumen | Hallazgo principal |
|---|---|---|
| EXP-E1 / E2 | [COMPLETAR] | [COMPLETAR] |
| EXP-F1 a F4 | [COMPLETAR] | [COMPLETAR] |
| EXP-F5 (Pareto) | [COMPLETAR] | [COMPLETAR] |
| EXP-F6, F7 | [COMPLETAR] | [COMPLETAR] |
| EXP-G1 a G4 | [COMPLETAR] | [COMPLETAR] |
| ABL-1, ABL-2 | [COMPLETAR] | [COMPLETAR] |
| Latencia | `results/summary/latency.csv` | [COMPLETAR] |

## 6. Checkpoints de referencia publicados

| ID | Ruta | Cómo se eligió | Métrica en `val` |
|---|---|---|---|
| `DEF-REF-1` | `checkpoints/refs/DEF-REF-1/` | Regla de selección de la Fase 3 | [COMPLETAR] |
| `ATK-REF-1` | `checkpoints/refs/ATK-REF-1/` | Mejor PPO por ER contra `DEF-REF-1` | [COMPLETAR] |

## 7. Recortes y desviaciones del plan

[COMPLETAR]

## 8. Problemas conocidos

[COMPLETAR]

## 9. Datos útiles para la siguiente fase

- Hiperparámetros finales de DQN y PPO (ruta al YAML): [COMPLETAR]
- Tiempo por run de DQN y PPO: [COMPLETAR]
- Estimación del costo de una generación de self-play con esos tiempos: [COMPLETAR]
- Comportamientos raros observados en entrenamiento: [COMPLETAR]

## 10. Capítulos del informe entregados

- `report/capitulos/05-deep-rl.md`

## 11. Firma de aceptación

- [ ] Nelson corrió el checklist completo en su máquina.
- [ ] Problemas encontrados en la ventana: _(lista o "ninguno")_
- [ ] Aceptado por: ______ · Fecha: ______
- [ ] `CLAUDE.md` actualizado: **Fase activa: 4**.
