# Contrato: oráculo

**Versión:** 1.0 · **Implementa:** Fase 1 (F1-T03, F1-T04) · **Archivo:** `wafarena/oracle/`

El oráculo responde con certeza dos preguntas sobre un payload: ¿es funcional? y ¿tuvo efecto? Si se equivoca, el atacante aprende a "evadir" mandando basura inofensiva y todos los resultados del proyecto quedan invalidados. Por eso es la primera pieza que se prueba y la que más pruebas tiene ([ADR-0004](../06-decisiones/adr-0004-oraculo-por-estructura-y-canarios.md)).

## Interfaz

```python
@dataclass(frozen=True)
class OracleResult:
    functional: bool          # el SQL resultante es válido y cambió la estructura de la consulta
    effect: bool              # la inyección produjo un efecto verificable
    evidence: Literal["structure_change", "canary_leak", "canary_write", "canary_error", "none", "syntax_error"]
    detail: str               # texto corto para depuración

class Oracle(Protocol):
    def check_direct(self, payload: Payload, endpoint: str) -> OracleResult: ...
    def check_request(self, request_id: str) -> OracleResult: ...
```

- `check_direct` ejecuta el endpoint de `vulnapp` en proceso, sin WAF. Lo usan los entornos para saber si una mutación rompió el payload.
- `check_request` evalúa un request que ya pasó por el defensor, buscando en el log del oráculo por `request_id`.

## Cómo decide

`vulnapp` registra cada consulta SQL ejecutada en la tabla `oracle_log` (`request_id`, `endpoint`, `sql`, `error`, `rows_returned`), usando una conexión con un rol de base de datos distinto al de la app. El rol de la app no tiene permisos sobre `oracle_log`.

Cada endpoint vulnerable tiene una **plantilla** de consulta. El oráculo calcula la huella (*fingerprint*) de `libpg_query` de la plantilla con un literal inofensivo y la compara con la huella del SQL realmente ejecutado.

| Condición | `functional` | `effect` | `evidence` |
|---|---|---|---|
| El SQL no parsea | False | False | `syntax_error` |
| Parsea y la huella es igual a la de la plantilla (el payload quedó como literal) | False | False | `none` |
| Huella distinta y la respuesta contiene el token de `canary_secrets` | True | True | `canary_leak` |
| Huella distinta y la ejecución escribió en `canary_writes` | True | True | `canary_write` |
| Huella distinta y el error de ejecución contiene el token del canario | True | True | `canary_error` |
| Huella distinta, ejecución sin error, sin canario | True | True | `structure_change` |
| Huella distinta, error de ejecución sin canario | False | False | `syntax_error` |

La huella detecta cualquier familia, incluida `boolean_blind`, porque toda inyección exitosa cambia la estructura de la consulta. Los canarios son evidencia adicional más fuerte y se reportan por separado en el informe.

## Canarios

- `canary_secrets(id, token)`: un token aleatorio de 32 caracteres generado en cada arranque del laboratorio. Ninguna consulta legítima de la app lo devuelve.
- `canary_writes(id, request_id, written_at)`: tabla vacía; solo un `stacked` exitoso escribe en ella.
- Fila oculta en `products` con `hidden = true` y nombre que contiene el token: solo aparece si una tautología anula el `WHERE`.

## Garantías que se prueban (F1-T04)

1. Todos los payloads de referencia de `lab/vulnapp/ENDPOINTS.md` dan `effect = True`.
2. Todas las sesiones benignas de `data/benign/` (incluidas las difíciles) dan `effect = False`.
3. Un payload con la comilla de cierre eliminada da `functional = False`.
4. El mismo payload evaluado 100 veces da el mismo resultado.
5. No existe consulta legítima de la app que devuelva el token del canario (prueba que recorre todos los endpoints con entradas benignas).

## Historial

- 1.0 — versión inicial.
