# Fuentes del corpus de payloads

El corpus `corpus.jsonl` se genera con `make build-corpus`
(`wafarena/corpus/templates.py` + `wafarena/corpus/builder.py`) y solo conserva los payloads que el
oráculo confirma como funcionales contra `vulnapp` en el laboratorio aislado.

## Origen

Las plantillas son payloads de inyección SQL clásicos y de dominio público, documentados por la
comunidad de seguridad (OWASP, PayloadsAllTheThings y literatura de evasión de WAF por mutación),
adaptados a la sintaxis de PostgreSQL y a los contextos de inyección de cada endpoint de `vulnapp`:

- cierre de literal de texto (`'`), patrón `LIKE`, contexto numérico, `ORDER BY` e `INSERT`.

No se incorporan payloads obtenidos de sistemas de terceros ni se dirigen a ningún host externo
(ver [ética y alcance](../../docs/00-vision/etica-y-alcance.md)).

## Familias

`tautology`, `union`, `error`, `boolean_blind`, `stacked`. Cada entrada registra `source`,
`source_ref` (el módulo que la generó), `adapted_for_postgres` y el `verified_commit` con el que el
oráculo la validó.

## Reproducibilidad

`make build-corpus` regenera el mismo archivo: el conjunto de plantillas es determinista y el orden
de salida está ordenado por `(family, endpoint, id)`.
