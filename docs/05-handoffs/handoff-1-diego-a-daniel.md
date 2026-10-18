# HANDOFF-1: Diego Valenzuela → Daniel Dubón

> Completar al cerrar la Fase 1 con el prompt [P6](../04-metodologia-ai-first/prompts.md#p6--redactar-el-handoff). Las secciones con `[COMPLETAR]` no pueden quedar así al entregar.

| | |
|---|---|
| **Tag** | `v0.1-fase1` |
| **Commit** | [COMPLETAR] |
| **Fecha de entrega** | [COMPLETAR] |
| **Ventana de aceptación** | [COMPLETAR] |
| **Estado** | Pendiente |

## 1. Qué se entrega

[COMPLETAR]

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| env-atacante | [COMPLETAR] | |
| env-defensor | [COMPLETAR] | |
| oráculo | [COMPLETAR] | |
| operadores | [COMPLETAR] | |
| features | [COMPLETAR] | |
| datos y splits | [COMPLETAR] | |
| agentes (políticas y drivers) | [COMPLETAR] | |

## 3. Cómo correrlo desde cero

[COMPLETAR]

## 4. Checklist de aceptación

- [ ] `make setup && make lint && make test` pasa.
- [ ] `make lab-up` levanta todos los servicios y `make test-lab` pasa, incluido `test_isolation.py`.
- [ ] `tests/lab/test_oracle.py`: las 5 garantías del contrato del oráculo en verde.
- [ ] `make verify-splits` pasa y los hashes coinciden con la sección 9.
- [ ] `check_env` pasa en `WafArena/Attacker-v0` y `WafArena/Defender-v0`.
- [ ] Dos corridas de `make smoke` con la misma semilla dan el mismo `smoke.csv`.
- [ ] Un script de 20 líneas escrito por quien recibe, que solo use la API pública del contrato, corre 10 episodios de `Attacker-v0` contra `modsec-pl2` sin leer código interno.
- [ ] `results/summary/operator_preservation.csv` y `modsec_baseline_corpus.csv` existen.

## 5. Resultados entregados

| Archivo | Contenido | Dato principal |
|---|---|---|
| `results/summary/modsec_baseline_corpus.csv` | Bloqueo del corpus sin mutar por PL | [COMPLETAR] |
| `results/summary/operator_preservation.csv` | Preservación por operador y familia | [COMPLETAR] |
| `results/summary/smoke.csv` | Evasión aleatoria por PL, modo rápido y real | [COMPLETAR] |

## 6. Checkpoints de referencia publicados

Ninguno en esta fase. Referencias no entrenadas disponibles: `modsec-pl1` … `pl4`, `corpus-replay`, `random-mutation`.

## 7. Recortes y desviaciones del plan

[COMPLETAR]

## 8. Problemas conocidos

[COMPLETAR]

## 9. Datos útiles para la siguiente fase

- Pasos/s de `Attacker-v0` en modo rápido con caché caliente: [COMPLETAR]
- Pasos/s de `Defender-v0` en modo rápido: [COMPLETAR]
- Tamaño del corpus por familia y split: [COMPLETAR]
- Hashes de `data/splits/v1.json`: [COMPLETAR]
- Decisión sobre el anomaly score de ModSecurity (ADR): [COMPLETAR]

## 10. Capítulos del informe entregados

- `report/capitulos/01-introduccion.md`
- `report/capitulos/03-laboratorio.md`
- `report/capitulos/08-etica.md`

## 11. Firma de aceptación

- [ ] Daniel corrió el checklist completo en su máquina.
- [ ] Problemas encontrados en la ventana: _(lista o "ninguno")_
- [ ] Aceptado por: ______ · Fecha: ______
- [ ] `CLAUDE.md` actualizado: **Fase activa: 2**.
