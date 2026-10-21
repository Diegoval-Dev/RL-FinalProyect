# Fase 1 — Laboratorio, oráculo y entornos

| | |
|---|---|
| **Dueño** | Diego Valenzuela |
| **Semanas** | 1–3 |
| **Recibe** | Nada. Es la primera fase |
| **Entrega** | Tag `v0.1-fase1` + [HANDOFF-1](../05-handoffs/handoff-1-diego-a-daniel.md) |
| **Contratos que implementa** | [env-atacante](../02-contratos/env-atacante.md), [env-defensor](../02-contratos/env-defensor.md), [oráculo](../02-contratos/oraculo.md), [operadores](../02-contratos/operadores-mutacion.md), [features](../02-contratos/features.md), [datos y splits](../02-contratos/datos-y-splits.md), políticas de [agentes](../02-contratos/agentes-y-checkpoints.md) |
| **Experimentos** | Ninguno del catálogo; solo la prueba de humo F1-T14 |

## Objetivo

Dejar un laboratorio en el que cualquier agente pueda entrenar sin tocar Docker ni HTTP, con un oráculo en el que todo el equipo confíe. Al terminar esta fase, la Fase 2 solo necesita escribir agentes y experimentos.

## Tareas

Cada tarea es una unidad de trabajo con agente: una rama, un PR, sus pruebas. El orden sugerido sigue la numeración. *Requiere* lista tareas de esta misma fase.

### F1-T01 — Esqueleto del repositorio
- **Hacer:** `pyproject.toml` con `uv`, estructura de [repo-estructura](../01-arquitectura/repo-estructura.md), `Makefile` con los comandos de `CLAUDE.md`, configuración de `ruff` y `pytest`, workflow de GitHub Actions que corre `make lint` y `make test`, `wafarena.CONTRACT_VERSIONS`.
- **Archivos:** raíz, `wafarena/__init__.py`, `.github/workflows/ci.yml`, `Makefile`.
- **Aceptación:** `make setup && make lint && make test` pasa en una máquina limpia; CI en verde con una prueba trivial.

### F1-T02 — Laboratorio Docker y `vulnapp`
- **Requiere:** F1-T01.
- **Hacer:** `lab/docker-compose.yml` con red `internal: true`; `vulnapp` en FastAPI con 8 endpoints vulnerables por concatenación de strings y flujos benignos (home, catálogo, login, carrito, búsqueda, comentarios); `lab/vulnapp/ENDPOINTS.md` con, por endpoint: método, parámetros, ubicaciones aceptadas (query/form/json), plantilla SQL, familias aplicables y un payload de referencia por familia.
- **Archivos:** `lab/`, `lab/vulnapp/`.
- **Aceptación:** `make lab-up` levanta todo; prueba `tests/lab/test_isolation.py` confirma que ningún contenedor resuelve ni alcanza un host externo; cada payload de referencia funciona contra `vulnapp` sin WAF.

### F1-T03 — Base de datos instrumentada
- **Requiere:** F1-T02.
- **Hacer:** `lab/db/init.sql` con esquema, datos de ejemplo en español, `canary_secrets` con token generado al arrancar, `canary_writes`, fila oculta en `products`, tabla `oracle_log` y dos roles (app sin acceso a `oracle_log`, logger con acceso). Hook en `vulnapp` que registra cada consulta con su `X-Request-ID`.
- **Aceptación:** prueba de que ninguna entrada benigna de ningún endpoint devuelve el token; prueba de que el rol de la app no puede leer `oracle_log`.

### F1-T04 — Oráculo
- **Requiere:** F1-T03.
- **Hacer:** `wafarena/oracle/` según el [contrato](../02-contratos/oraculo.md): huellas de plantillas con `pglast`, `check_direct`, `check_request`, evidencias.
- **Aceptación:** las 5 garantías del contrato como pruebas en `tests/lab/test_oracle.py`, todas en verde. Esta tarea no se cierra con ninguna prueba en rojo ni marcada como `skip`.

### F1-T05 — ModSecurity PL1–PL4
- **Requiere:** F1-T02.
- **Hacer:** cuatro servicios con la imagen de ModSecurity + CRS, uno por paranoia level, en modo de puntuación de anomalía. Mecanismo para obtener el anomaly score por request (resolverlo como *spike*: audit log JSON correlacionado por `X-Request-ID` o una alternativa que el spike justifique). Documentar la decisión en un ADR.
- **Aceptación:** función `modsec_score(request, pl) -> (score, would_block)`; tabla `results/summary/modsec_baseline_corpus.csv` con la tasa de bloqueo del corpus sin mutar en cada PL.

### F1-T06 — Proxy defensor y honeypot
- **Requiere:** F1-T05.
- **Hacer:** proxy FastAPI que asigna `X-Request-ID`, consulta las cuatro instancias de ModSecurity, calcula features, pide acción a una `DefenderPolicy` y la aplica (403, captcha simulado, 429, honeypot). Honeypot que imita respuestas de `vulnapp` sin tocar la base real.
- **Aceptación:** con `ModSecDefender(pl)` el proxy reproduce exactamente las decisiones de ModSecurity en ese PL sobre 500 requests de prueba.

### F1-T07 — Corpus de payloads
- **Requiere:** F1-T04.
- **Hacer:** script reproducible que toma payloads de fuentes públicas (registrar cuáles en `data/payloads/SOURCES.md`), los adapta a PostgreSQL y a los endpoints, los etiqueta por familia y conserva solo los que el oráculo confirma.
- **Aceptación:** `corpus.jsonl` cumple el [contrato](../02-contratos/datos-y-splits.md): ≥ 200 funcionales y ≥ 30 por familia; el script regenera el mismo archivo con la misma semilla.

### F1-T08 — Operadores de mutación
- **Requiere:** F1-T07.
- **Hacer:** los 16 operadores del [registro](../02-contratos/operadores-mutacion.md) con pruebas *property-based*; script que mide aplicabilidad y preservación por operador y familia.
- **Aceptación:** pruebas obligatorias del contrato en verde; `results/summary/operator_preservation.csv` generado.

### F1-T09 — Tráfico benigno
- **Requiere:** F1-T02.
- **Hacer:** generadores en `traffic/` (Locust para volumen, Playwright para flujos de usuario) con plantillas `normal` y `hard`. Grabar a `data/benign/sessions.jsonl`.
- **Aceptación:** ≥ 5 000 sesiones, ≥ 1 000 `hard`, todas las etiquetas `hard_tags` representadas; el oráculo da `effect = False` en todas.

### F1-T10 — Features de request y sesión
- **Requiere:** F1-T01.
- **Hacer:** `wafarena/features/` según el [contrato](../02-contratos/features.md).
- **Aceptación:** prueba por feature con valor esperado; prueba de rendimiento ≤ 1 ms por request.

### F1-T11 — Backends rápido y real
- **Requiere:** F1-T04, F1-T05, F1-T06, F1-T10.
- **Hacer:** interfaz `Backend`; `FastBackend` (consultas en proceso, ModSecurity por HTTP en lote con caché persistente en disco por `(PL, hash del request)`); `RealBackend` (todo por el proxy).
- **Aceptación:** concordancia ≥ 99 % entre backends en 1 000 requests muestreados; `FastBackend` sostiene ≥ 300 pasos/s del entorno atacante con caché caliente (medido y anotado en el handoff).

### F1-T12 — Entornos Gymnasium y políticas base
- **Requiere:** F1-T08, F1-T09, F1-T11.
- **Hacer:** `Attacker-v0`, `Defender-v0`, `abstract_state.py`, `ModSecDefender`, `CorpusReplayAttacker`, `RandomMutationAttacker`, `AttackerDriver`, `DefenderDriver`, exactamente como dicen los contratos.
- **Aceptación:** `gymnasium.utils.env_checker.check_env` pasa en ambos; pruebas de determinismo; pruebas de cada fila de las tablas de recompensa con casos construidos; prueba de que el estado abstracto es biyectivo.

### F1-T13 — Splits congelados
- **Requiere:** F1-T07, F1-T09.
- **Hacer:** `data/splits/v1.json` según el contrato; `make verify-splits`; prueba de no fuga (ningún `base_id` ni `template_id` reservado aparece en dos splits).
- **Aceptación:** prueba en verde; hashes anotados en el handoff.

### F1-T14 — Prueba de humo
- **Requiere:** F1-T12, F1-T13.
- **Hacer:** `make smoke`: atacante aleatorio contra `modsec-pl1` … `pl4` y defensor aleatorio, 100 episodios cada uno, en modo rápido y real.
- **Aceptación:** corre sin errores; tasas de evasión aleatoria por PL guardadas en `results/summary/smoke.csv` y copiadas al handoff como línea base de cordura.

### F1-T15 — Capítulos del informe y handoff
- **Requiere:** todas las anteriores.
- **Hacer:** `report/capitulos/01-introduccion.md`, `03-laboratorio.md` y `08-etica.md` (ver [estructura](../08-informe/estructura-informe.md)); completar [HANDOFF-1](../05-handoffs/handoff-1-diego-a-daniel.md); actualizar versiones de contratos si cambió algo; crear el tag.
- **Aceptación:** checklist de [DoD de fase](../04-metodologia-ai-first/definicion-de-terminado.md#fase) completo.

## Riesgos de esta fase

| Riesgo | Mitigación |
|---|---|
| Obtener el anomaly score de ModSecurity por request es más difícil de lo previsto | F1-T05 empieza como spike de máximo 1 día con dos alternativas; el ADR deja la decisión escrita |
| El oráculo da falsos positivos con benignos difíciles | Las sesiones `hard` se pasan por el oráculo en F1-T09; cualquier `effect = True` bloquea el cierre de la tarea |
| El modo rápido es demasiado lento | Caché persistente y lotes; si no se alcanzan 300 pasos/s, documentar el valor real en el handoff y reducir `total_steps` sugeridos |
| La fase es la más pesada | El trabajo previo de las otras fases no depende de esta; recortar la cantidad de endpoints a 6 antes que las pruebas del oráculo |

## Estado

- [x] F1-T01 Esqueleto del repositorio
- [x] F1-T02 Laboratorio Docker y `vulnapp`
- [x] F1-T03 Base de datos instrumentada
- [x] F1-T04 Oráculo
- [ ] F1-T05 ModSecurity PL1–PL4
- [ ] F1-T06 Proxy defensor y honeypot
- [x] F1-T07 Corpus de payloads
- [x] F1-T08 Operadores de mutación
- [ ] F1-T09 Tráfico benigno
- [ ] F1-T10 Features
- [ ] F1-T11 Backends
- [ ] F1-T12 Entornos Gymnasium
- [ ] F1-T13 Splits congelados
- [ ] F1-T14 Prueba de humo
- [ ] F1-T15 Informe y handoff

## Hallazgos

Problemas encontrados fuera del alcance de la tarea en curso, decisiones pendientes o recortes. Formato: `fecha · tarea · hallazgo · acción`.

- 2026-10-18 · F1-T01 · `docs/` y un `CLAUDE.md` duplicado vivían dentro de `wafarena/`, que es el nombre del paquete · se movió `docs/` a la raíz y se borraron los duplicados.
- 2026-10-18 · F1-T01 · CI en GitHub Actions sin verificar: el repo aún no tiene remote · confirmar en verde al subir la rama.
- 2026-10-18 · F1-T01 · `ruff` excluye `docs/` para no formatear los bloques de código de los `.md`.
- 2026-10-18 · F1-T02 · `internal: true` impide publicar puertos al host · `make test-lab` corre las pruebas dentro de un contenedor `runner` en la red interna; solo `test_isolation.py` corre en el host (usa la CLI de docker). El modo rápido de F1-T11 y el smoke de F1-T14 deberán correr también en `runner`.
- 2026-10-18 · F1-T02 · `lab/db/init.sql` incluye ya el esquema mínimo (products con `hidden`, users, orders, comments, cart_items) · F1-T03 lo extiende con canarios, `oracle_log` y roles.
- 2026-10-18 · F1-T02 · Los payloads de referencia viven en `lab/vulnapp/vulnapp/reference.py` (no en JSON) y `ENDPOINTS.md` se genera con `make endpoints-doc` · F1-T04 los importa directamente.
- 2026-10-18 · F1-T02 · El carrito usa el usuario fijo 2 (sin sesiones reales en `vulnapp`) · el `X-Session-ID` solo lo usa el proxy.
- 2026-10-18 · F1-T02 · Las dependencias de `runner` y `vulnapp` se instalan al construir la imagen (la red interna no tiene internet) · tras cambiar `pyproject.toml`, `make lab-up` reconstruye.
- 2026-10-21 · F1-T03 · `init.sql` y los scripts de `lab/db/` solo corren en un volumen vacío; `make lab-up` sobre un contenedor existente no los vuelve a ejecutar · tras cambiarlos, `make lab-down` (con `-v`) antes de `make lab-up`.
- 2026-10-21 · F1-T03 · El token del canario se genera en `02-roles-and-canaries.sh` en el primer arranque del volumen; cada `make lab-down` + `lab-up` produce uno nuevo (verificado).
- 2026-10-21 · F1-T03 · `OracleLog` abre una conexión por consulta, lo que es caro en el lote de entrenamiento · F1-T11 debe usar un pool o el modo rápido en proceso.
- 2026-10-21 · F1-T03 · `oracle_log` crece sin límite durante los entrenamientos · F1-T11 decide purga o rotación por run.
- 2026-10-21 · F1-T03 · El rol `logger` solo tiene acceso a `oracle_log`; F1-T04 leerá `canary_secrets` y `canary_writes` con un rol propio o con el administrador · decidir al implementar el oráculo.
- 2026-10-21 · F1-T03 · La fila oculta de `products` contiene el token en el nombre; una tautología sobre `catalog` la devuelve (prueba `test_tautology_on_catalog_exposes_the_hidden_canary_row`), lo que confirma el canario de evidencia.
- 2026-10-21 · F1-T04 · Los payloads de la familia `error` solo mostraban un error de tipo, sin token; con la tabla del contrato daban `effect = False`, lo que contradecía la garantía 1 · se cambiaron para que el error contenga el token (`CAST((SELECT token FROM canary_secrets) AS int)`), que es el caso `canary_error`.
- 2026-10-21 · F1-T04 · El rol `app` no podía contar `canary_writes` para la transacción de `check_direct` · se añadió `count_canary_writes(text)`, `SECURITY DEFINER`, que solo devuelve un conteo. Requiere volumen nuevo (`make lab-down` antes de `make lab-up`).
- 2026-10-21 · F1-T04 · Garantía 2 cerrada sobre los endpoints del registro (sus valores benignos), no sobre `data/benign/sessions.jsonl`, que llega con F1-T09 · en T09 añadir la prueba sobre las sesiones.
- 2026-10-21 · F1-T04 · `Payload` vive en `wafarena/mutations/payload.py` (contrato de operadores) para que el oráculo lo use sin esperar a F1-T08 · T08 debe importarlo de ahí.
- 2026-10-21 · F1-T04 · `wafarena` importa `vulnapp.queries` y `vulnapp.db` (modo rápido, ADR-0005); `pyproject.toml` incluye `lab/vulnapp/vulnapp` como paquete.
- 2026-10-21 · F1-T04 · `check_request` cuenta `canary_writes` por `request_id`; `check_direct` lo hace dentro de la transacción revertida, así que el conteo no contamina la base.
- 2026-10-21 · F1-T07 · El corpus se genera de plantillas curadas por contexto de inyección (no de un archivo externo descargado), verificadas por el oráculo; 528 payloads funcionales (tautology 120, boolean_blind 120, error 196, union 52, stacked 40). Reproducible (mismo hash al reconstruir).
- 2026-10-21 · F1-T07 · El commit de verificación se pasa al runner por `VERIFIED_COMMIT` porque `git` no está dentro del contenedor.
- 2026-10-21 · F1-T07 · Las plantillas de `stacked`/`error` apuntan a `canary_secrets`/`canary_writes`, así que dependen del esquema de F1-T03; si cambia, regenerar el corpus.
- 2026-10-21 · F1-T08 · `location_switch` se construye con las ubicaciones permitidas (no las conoce `apply`); el registro usa las tres por defecto y el entorno (F1-T12) lo reconstruye con las del endpoint activo.
- 2026-10-21 · F1-T08 · `url_encode`/`double_url_encode` usan el campo `url_encoding_layers` del Payload y no se aplican si ya hay 2 capas; es intencional que rompan en endpoints que decodifican una sola vez.
- 2026-10-21 · F1-T08 · `operator_preservation.csv` se generó sobre todo el corpus (no solo `train`, que llega en F1-T13); regenerar con `train` tras congelar los splits.

