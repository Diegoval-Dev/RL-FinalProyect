# HANDOFF-1: Diego Valenzuela → Daniel Dubón

| | |
|---|---|
| **Tag** | `v0.1-fase1` (se crea en `main` tras mergear los PR de la Fase 1) |
| **Commit** | el de `main` con el tag `v0.1-fase1` |
| **Fecha de entrega** | 2026-10-21 |
| **Ventana de aceptación** | hasta 2026-10-22 (1 día hábil) |
| **Estado** | Entregado |

## 1. Qué se entrega

El laboratorio completo y aislado (vulnapp, PostgreSQL instrumentada, ModSecurity PL1–PL4, proxy y
honeypot), el oráculo verificado por estructura y canarios, un corpus de 528 payloads funcionales,
5 200 sesiones benignas, los *splits* congelados `v1`, los 16 operadores de mutación, las features
de request y sesión, los *backends* rápido y real con caché, y los dos entornos Gymnasium
(`Attacker-v0`, `Defender-v0`) con sus políticas base. La Fase 2 solo necesita escribir agentes y
experimentos sobre esta base.

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios |
|---|---|---|
| env-atacante | 1.0 | Sin cambios |
| env-defensor | 1.0 | Sin cambios |
| oráculo | 1.1 | `check_direct` recibe `param`; `oracle_log` guarda `rows_json`; `canary_writes` toma el `request_id` de la sesión; conteo de escrituras con `count_canary_writes` (SECURITY DEFINER) |
| operadores | 1.0 | Sin cambios (orden del registro congelado) |
| features | 1.0 | Sin cambios |
| datos y splits | 1.0 | Sin cambios |
| agentes (políticas y drivers) | 1.0 | `DefenderPolicy`, `AttackerPolicy`, `ModSecDefender`, `CorpusReplayAttacker`, `RandomMutationAttacker`, `AttackerDriver`, `DefenderDriver` |

## 3. Cómo correrlo desde cero

```bash
docker pull owasp/modsecurity-crs:nginx   # la red interna no tiene internet; descargar en el host
make setup
make lint && make test
make lab-up
make test-lab
make verify-splits
make smoke            # opcional: regenera results/summary/smoke.csv
make lab-down
```

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
| `results/summary/modsec_baseline_corpus.csv` | Bloqueo del corpus de referencia por PL | Ataques: 100 % en PL1–PL4. Benignos: 0 % en PL1–PL2, 12.5 % en PL3, 25 % en PL4 |
| `results/summary/operator_preservation.csv` | Aplicabilidad y preservación por operador y familia | Generado sobre todo el corpus; regenerar con `train` tras congelar splits |
| `results/summary/smoke.csv` | Evasión aleatoria por PL, modo rápido y real | 0.0 en los 4 PL, en fast y real (un atacante aleatorio no vence al WAF) |

## 6. Checkpoints de referencia publicados

Ninguno en esta fase. Referencias no entrenadas disponibles: `modsec-pl1` … `pl4`, `corpus-replay`, `random-mutation`.

## 7. Recortes y desviaciones del plan

- **Tráfico benigno (F1-T09):** se usó un generador determinista en lugar de Locust/Playwright, para reproducibilidad y CI. Las mismas sesiones pueden reproducirse por HTTP en modo real.
- **Baseline de ModSecurity (F1-T05) y preservación (F1-T08):** se generaron con los payloads de referencia / todo el corpus, no con `corpus.jsonl train`, que se congeló después. Regenerar con `train` si se requiere.
- **Smoke en modo real (F1-T14):** 15 episodios × 25 pasos como sanity (el modo real es HTTP por paso; 100 × 4 PL excedía 10 minutos). Modo rápido: 100 episodios por PL.

## 8. Problemas conocidos

- `OracleLog` y el oráculo abren una conexión por consulta; aceptable en modo real, pero para lotes grandes conviene un *pool* (ya mitigado en modo rápido por la memoización y la caché).
- `oracle_log` crece sin límite durante el entrenamiento; decidir purga o rotación por run si estorba.
- `init.sql` y los scripts de `lab/db/` solo corren en un volumen vacío: tras cambiarlos, `make lab-down` antes de `make lab-up`.
- La imagen `owasp/modsecurity-crs:nginx` debe descargarse en el host antes de levantar el laboratorio.
- `req_rate` (feature 16) se aproxima con el total de requests de la sesión hasta que el entorno pase tiempo simulado.

## 9. Datos útiles para la siguiente fase

- Pasos/s de `Attacker-v0` en modo rápido con caché caliente: **3.27 M/s** (verificación de funcionalidad), **234 K/s** (incluyendo los 4 scores de ModSecurity). Muy por encima de la meta de 300 pasos/s.
- Pasos/s de `Defender-v0` en modo rápido: dominado por el mismo `probe` cacheado (~234 K/s por request evaluado).
- Tamaño del corpus por familia: tautology 120, boolean_blind 120, error 196, union 52, stacked 40 (total 528). Splits de payloads: train 172, val 56, test 64, test-family 236. Benignos: train 2 832, val 944, test 944, test-hard 480.
- Hashes de `data/splits/v1.json`:
  - `corpus.jsonl`: `616e4f578136757ff1bb2f7365471ef4aff8d87e0b378636e56151a0c1f2887e`
  - `sessions.jsonl`: `2bdfe0b580381fef758845f08b91440e7b13e249701acef2645934f42d7f087b`
- Decisión sobre el anomaly score de ModSecurity: [ADR-0008](../06-decisiones/adr-0008-modsec-score-por-audit-log.md) — audit log JSON en volumen compartido, correlación por `X-Request-ID`, score reconstruido por severidad y validado contra la regla 949110.

## 10. Capítulos del informe entregados

- `report/capitulos/01-introduccion.md`
- `report/capitulos/03-laboratorio.md`
- `report/capitulos/08-etica.md`

## 11. Firma de aceptación

- [ ] Daniel corrió el checklist completo en su máquina.
- [ ] Problemas encontrados en la ventana: _(lista o "ninguno")_
- [ ] Aceptado por: ______ · Fecha: ______
- [ ] `CLAUDE.md` actualizado: **Fase activa: 2**.
