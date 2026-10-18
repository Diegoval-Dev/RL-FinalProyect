# Contrato: métricas

**Versión:** 1.0 · **Implementa:** Fase 2 (F2-T03) · **Archivos:** `wafarena/eval/metrics.py`, `wafarena/eval/stats.py`

Una métrica que no está definida aquí no aparece en el informe. Si una fase necesita una nueva, la agrega aquí (cambio MENOR) antes de usarla.

## Atacante

| Métrica | Símbolo | Definición |
|---|---|---|
| Tasa de evasión | ER | Episodios con `evaded = True` / episodios de la suite |
| Consultas hasta la primera evasión | QFE | Mediana de `queries_used` en episodios con evasión. Se reporta junto con ER, porque es condicional al éxito |
| Consultas censuradas | QFE-c | Media de `queries_used` tratando los episodios sin evasión como `query_budget` |
| Diversidad de éxitos | DIV | Distancia de Levenshtein normalizada media entre pares de payloads exitosos distintos (muestreo de hasta 500 pares) |
| Unicidad | UNQ | Payloads exitosos únicos / payloads exitosos |
| Tasa de rotura | BRK | Mutaciones con `broken = True` / mutaciones totales |
| Regret acumulado | R(t) | Solo bandits: `Σ (μ* − μ_{a_t})`, con μ de cada brazo estimada fuera de línea con 2 000 tiradas por brazo y semilla fija |

## Defensor

Todas se calculan por request; las marcadas con (s) también por sesión.

| Métrica | Símbolo | Definición |
|---|---|---|
| Tasa de detección | TPR | Requests de ataque con acción ≠ `ALLOW` / requests de ataque |
| Tasa de evasión sufrida | ER-d | Requests de ataque con `ALLOW` y efecto / requests de ataque con efecto |
| Falsos positivos | FPR | Requests benignos con acción ≠ `ALLOW` / requests benignos (s) |
| Falsos positivos duros | FPR-h | Requests benignos con `BLOCK` o `HONEYPOT` / requests benignos (s) |
| F1 | F1 | Sobre la binarización acción ≠ `ALLOW` |
| Latencia agregada | LAT | p50 y p95 en ms del tiempo agregado por el proxy respecto a ModSecurity solo, en modo real |

Para comparar contra ModSecurity, que solo bloquea o permite, se usan TPR y FPR. FPR-h se reporta aparte para no esconder fricción detrás de captchas.

## Brecha entre modos

`GAP(m) = |m_fast − m_real|` para cada métrica principal, medida en EXP-R1 con las mismas semillas.

## Suites de evaluación

Definidas en `wafarena/eval/harness.py`. Son fijas: mismas semillas, mismos payloads, mismas sesiones.

| Suite | Contenido |
|---|---|
| `attacker-eval-v1` | 200 episodios sobre payloads `test`, semillas 1000–1199, `query_budget = 50` |
| `attacker-eval-family-v1` | 200 episodios sobre `test-family` |
| `defender-eval-v1` | 2 000 sesiones de `test`, `attack_ratio = 0.1`; atacantes: `corpus-replay`, `random-mutation` y, desde la Fase 3, `ATK-REF-0` |
| `defender-eval-hard-v1` | Todas las sesiones de `test-hard` mezcladas con ataques de `defender-eval-v1` |
| `defender-eval-family-v1` | Sesiones benignas `test` con ataques sobre `test-family` |

## Estadística

- Mínimo 5 semillas por configuración principal; 10 para bandits y tabulares, que son baratos.
- Se reporta media e intervalo de confianza del 95 % por bootstrap sobre semillas (10 000 remuestreos, `stats.bootstrap_ci`).
- Para afirmar que A supera a B se reporta el IC de la diferencia `A − B`. Si contiene el 0, el informe dice que no hay diferencia detectable.
- Las curvas de entrenamiento muestran media y banda del IC.

## Historial

- 1.0 — versión inicial.
