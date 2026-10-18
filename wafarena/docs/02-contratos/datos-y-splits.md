# Contrato: datos y splits

**Versión:** 1.0 · **Implementa:** Fase 1 (F1-T07, F1-T09, F1-T13)

## Corpus de payloads: `data/payloads/corpus.jsonl`

Una línea por payload base. Solo entran payloads que el oráculo confirmó como funcionales.

```json
{"id": "p-000123", "family": "union", "endpoint": "search", "text": "...", "location": "query",
 "source": "PayloadsAllTheThings", "source_ref": "ruta o URL del archivo de origen",
 "adapted_for_postgres": true, "verified_commit": "abc1234"}
```

Familias válidas: `tautology`, `union`, `error`, `boolean_blind`, `stacked`.

Mínimos: 200 payloads funcionales en total y 30 por familia.

## Sesiones benignas: `data/benign/sessions.jsonl`

```json
{"session_id": "b-004211", "kind": "hard", "template_id": "t-comment-code-07", "generator": "playwright",
 "requests": [{"t": 0.0, "method": "GET", "path": "/search", "params": {"q": "O'Brien"},
               "body": null, "content_type": null, "hard_tags": ["apostrophe"]}]}
```

- `kind`: `normal` o `hard`.
- `hard_tags`: `apostrophe`, `symbols`, `code`, `spanish`, `emoji`.
- `template_id`: plantilla que generó la sesión. Se usa para que `test-hard` contenga plantillas nunca vistas.

Mínimos: 5 000 sesiones, de las cuales al menos 1 000 son `hard`. Todas dan `effect = False` en el oráculo.

## Splits: `data/splits/v1.json`

```json
{"version": "v1", "created_commit": "abc1234",
 "files_sha256": {"corpus.jsonl": "...", "sessions.jsonl": "..."},
 "payloads": {"train": ["p-..."], "val": [...], "test": [...], "test-family": [...]},
 "benign": {"train": ["b-..."], "val": [...], "test": [...], "test-hard": [...]},
 "holdout_families": ["error", "stacked"]}
```

| Split | Payloads | Sesiones benignas | Uso |
|---|---|---|---|
| `train` | 60 % de `tautology`, `union`, `boolean_blind` | 60 % de las normales y de las difíciles de plantillas no reservadas | Entrenamiento |
| `val` | 20 % de las mismas familias | 20 % | Selección de hiperparámetros y checkpoints |
| `test` | 20 % de las mismas familias | 20 % | Evaluación final |
| `test-family` | Todas las de `error` y `stacked` | — | Solo EXP-F6 e I3 (generalización a familias) |
| `test-hard` | — | Difíciles de un 30 % de plantillas reservadas | Solo EXP-F7 e I4 (benignos difíciles no vistos) |

La división se hace por agrupación: variantes de un mismo payload de origen quedan en el mismo split.

## Reglas

1. `v1.json` se congela en F1-T13. Nadie lo regenera después. Si se necesita otro split, se crea `v2.json` con ADR.
2. `make verify-splits` recalcula los hashes y falla si un archivo cambió.
3. El runner rechaza cualquier configuración de entrenamiento con `split: test`, `test-family` o `test-hard`.

## Historial

- 1.0 — versión inicial.
