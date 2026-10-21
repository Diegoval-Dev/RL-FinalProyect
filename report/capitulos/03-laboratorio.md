# 3. Laboratorio y formulación

## Arquitectura

El laboratorio corre en Docker Compose sobre una red declarada `internal: true`, sin salida a
internet y sin puertos publicados al host. Una prueba automática verifica que ningún contenedor
resuelve ni alcanza un host externo. Los componentes son: la aplicación vulnerable `vulnapp`
(FastAPI), PostgreSQL con canarios, cuatro instancias de ModSecurity + OWASP CRS (una por paranoia
level), un proxy defensor y un honeypot. El diagrama está en
[docs/01-arquitectura/arquitectura.md](../../docs/01-arquitectura/arquitectura.md).

Se usa una aplicación propia en lugar de una de terceros ([ADR-0007](../../docs/06-decisiones/adr-0007-app-propia-python.md))
porque permite saber con exactitud qué consulta ejecuta cada endpoint, lo que hace el oráculo
trivial de especificar. `vulnapp` expone ocho endpoints vulnerables por concatenación de cadenas,
catalogados en `lab/vulnapp/ENDPOINTS.md`, más flujos benignos.

## Oráculo

El oráculo responde dos preguntas sobre un payload: si es **funcional** (el SQL resultante es válido
y cambió la estructura de la consulta) y si tuvo **efecto** verificable
([ADR-0004](../../docs/06-decisiones/adr-0004-oraculo-por-estructura-y-canarios.md)). Compara la
huella de `libpg_query` (vía `pglast`) de la consulta ejecutada con la de la plantilla del endpoint;
una huella distinta indica un cambio estructural. Los canarios aportan evidencia más fuerte: un
token aleatorio de 32 caracteres generado en cada arranque, una tabla de escrituras y una fila
oculta. Cada consulta ejecutada se registra en `oracle_log` con un rol de base de datos separado al
de la aplicación.

Las cinco garantías del contrato se prueban automáticamente: todos los payloads de referencia dan
`effect = True`; los valores benignos dan `effect = False`; un payload sin la comilla de cierre no
es funcional; el mismo payload evaluado cien veces da el mismo resultado; y ninguna consulta
legítima devuelve el token del canario.

## Corpus y tráfico benigno

El corpus (`data/payloads/corpus.jsonl`) contiene **528 payloads funcionales** verificados por el
oráculo, por encima del mínimo de 200 y de 30 por familia: tautology 120, boolean_blind 120,
error 196, union 52, stacked 40. El tráfico benigno (`data/benign/sessions.jsonl`) contiene
**5 200 sesiones** (1 200 difíciles, 240 por cada etiqueta de dificultad), todas con `effect =
False` según el oráculo. Ambos conjuntos se generan de forma reproducible (mismo hash al
regenerar).

Los *splits* (`data/splits/v1.json`) se congelan en esta fase. Las familias `error` y `stacked` se
reservan completas para `test-family`; el resto se divide 60/20/20 por grupo base, de modo que las
variantes de un mismo payload no cruzan particiones. Tamaños: payloads 172/56/64/236
(train/val/test/test-family); benignos 2 832/944/944/480 (train/val/test/test-hard). La regla
`make verify-splits` recalcula los hashes y falla si los archivos cambian.

## Formulación como MDP/POMDP

**Atacante (`Attacker-v0`).** Un episodio es un intento de evadir al defensor partiendo de un
payload base. La observación es un vector de 288 dimensiones (hashing de n-gramas de caracteres,
ventana de las últimas respuestas, contadores de presupuesto y familia). Las acciones son
`Discrete(17)`: aplicar uno de los 16 operadores de mutación o `SEND`. La verificación de
funcionalidad tras cada mutación usa el oráculo sin WAF y no consume consultas; **esta es una
simplificación declarada**: equivale a que el atacante tenga una copia local del objetivo. El
atacante no observa el estado interno del defensor, solo sus respuestas, por lo que el problema es
un POMDP; la observación incluye una ventana de las últimas cuatro respuestas como aproximación.

**Defensor (`Defender-v0`).** Un episodio es una sesión de tráfico; cada paso es un request. La
observación es un vector de 37 dimensiones (features del request, los cuatro scores de anomalía de
ModSecurity, features de sesión y una ventana). Las acciones son `Discrete(5)`: permitir, bloquear,
captcha, limitar o desviar al honeypot. Incluir los cuatro scores de ModSecurity hace del defensor
un sistema híbrido ([ADR-0003](../../docs/06-decisiones/adr-0003-defensor-hibrido.md)).

Para métodos tabulares, el atacante expone un estado abstracto biyectivo en `[0, 120)` combinando
familia, última respuesta y un *bucket* de mutaciones.

## Entorno de dos velocidades

El entrenamiento necesita cientos de miles de pasos, inviables por HTTP
([ADR-0005](../../docs/06-decisiones/adr-0005-dos-velocidades.md)). El modo rápido (`FastBackend`)
ejecuta las consultas del oráculo en proceso y obtiene los scores de ModSecurity por HTTP con una
caché persistente por `(versión de configuración, PL, hash del request)`; el modo real
(`RealBackend`) hace todo por HTTP. Con caché caliente el modo rápido sostiene **3.27 millones de
pasos/s** para la verificación de funcionalidad y **234 000 pasos/s** incluyendo los scores de
ModSecurity, muy por encima de la meta de 300 pasos/s. La concordancia entre ambos modos es ≥ 99 %
sobre los requests muestreados.

El anomaly score por request se obtiene del audit log JSON de ModSecurity, correlacionado por
`X-Request-ID` en un volumen compartido ([ADR-0008](../../docs/06-decisiones/adr-0008-modsec-score-por-audit-log.md)).

## Protocolo experimental y estadística

Lo completa Daniel en la Fase 2 (runner, métricas y agregación por semillas). Esta fase deja la
prueba de humo como línea base de cordura: un atacante aleatorio contra ModSecurity PL1–PL4 obtiene
una tasa de evasión de **0.0** en los cuatro niveles, en modo rápido y real
(`results/summary/smoke.csv`), lo que confirma que la evasión no es trivial y motiva el aprendizaje.
