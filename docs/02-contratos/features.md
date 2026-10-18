# Contrato: features del defensor

**Versión:** 1.0 · **Implementa:** Fase 1 (F1-T10) · **Archivos:** `wafarena/features/request.py`, `wafarena/features/session.py`

Todas las features quedan en `[0, 1]`. La normalización está definida aquí y no se cambia sin subir versión.

El "texto del request" es la concatenación, separada por `&`, de los valores de todos los parámetros (query, form y JSON aplanado), decodificados una vez.

## Request (índices 0–11)

| Índice | Nombre | Definición |
|---|---|---|
| 0 | `len_log` | `min(1, log1p(len(texto)) / log1p(2048))` |
| 1 | `entropy` | Entropía de Shannon por carácter / 8 |
| 2 | `special_ratio` | Fracción de caracteres del conjunto `' " ; ( ) = < > \| - / * # %` |
| 3 | `sql_kw` | `min(1, conteo de palabras clave SQL / 10)` sobre una lista fija en `request.py` (sin distinguir mayúsculas) |
| 4 | `quote_count` | `min(1, conteo de ' y " / 10)` |
| 5 | `comment_markers` | `min(1, conteo de --, /*, */ / 5)` |
| 6 | `encoding_depth` | Capas de codificación URL detectadas (0–3) / 3 |
| 7 | `digit_ratio` | Fracción de dígitos |
| 8 | `upper_ratio` | Fracción de mayúsculas sobre letras |
| 9 | `param_count` | `min(1, número de parámetros / 20)` |
| 10 | `is_json` | 1 si el cuerpo es JSON |
| 11 | `max_token_len` | `min(1, longitud del token más largo / 256)` |

## ModSecurity (índices 12–15)

| Índice | Nombre | Definición |
|---|---|---|
| 12–15 | `modsec_score_pl1` … `pl4` | `min(1, anomaly score inbound / 50)` en cada paranoia level |

Usar los cuatro scores convierte al defensor en un sistema híbrido que aprende cuándo confiar en cada nivel de reglas ([ADR-0003](../06-decisiones/adr-0003-defensor-hibrido.md)). La ablación ABL-1 los reemplaza por ceros.

## Sesión (índices 16–20)

| Índice | Nombre | Definición |
|---|---|---|
| 16 | `req_rate` | `min(1, requests en los últimos 10 s / 50)` (tiempo simulado en modo rápido) |
| 17 | `prior_denials` | `min(1, requests previos no permitidos en la sesión / 10)` |
| 18 | `prior_captcha_fail` | `min(1, captchas fallados en la sesión / 5)` |
| 19 | `session_len` | `min(1, log1p(requests previos) / log1p(200))` |
| 20 | `sql_kw_frac` | Fracción de requests previos con `sql_kw > 0` |

La ablación ABL-2 reemplaza este bloque y la ventana por ceros.

## Ventana (índices 21–36)

Para cada uno de los 4 requests anteriores de la sesión, del más reciente al más antiguo, 4 features: `entropy`, `special_ratio`, `modsec_score_pl2`, `was_denied` (1 si la acción no fue `ALLOW`). Si hay menos de 4 requests previos, se rellena con ceros.

## Requisitos

- Latencia de cálculo por request ≤ 1 ms en CPU (prueba de rendimiento en F1-T10).
- Pruebas unitarias con requests de ejemplo y valor esperado de cada feature.

## Historial

- 1.0 — versión inicial.
