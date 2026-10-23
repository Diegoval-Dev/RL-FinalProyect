# Contrato: operadores de mutación

**Versión:** 1.1 · **Implementa:** Fase 1 (F1-T08) · **Archivo:** `wafarena/mutations/`

Los operadores son el espacio de acciones del atacante. Siguen las categorías de la literatura de evasión de WAF por mutación (WAF-A-MoLE y trabajos relacionados, ver [referencias](../08-informe/referencias.md)), adaptadas a la sintaxis de PostgreSQL.

## Interfaz

```python
@dataclass(frozen=True)
class Payload:
    text: str
    location: Literal["query", "form", "json"]   # dónde viaja el parámetro
    url_encoding_layers: int                     # 0, 1 o 2

class Operator(Protocol):
    name: str
    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None: ...
```

`apply` devuelve `None` si el operador no es aplicable (por ejemplo, `dollar_quote` sobre un payload sin literales de texto). No hace I/O, no consulta el oráculo y es determinista dado el `rng`.

## Registro

El índice es la acción del entorno. **El orden está congelado**: cambiarlo es un cambio MAYOR del contrato.

| Índice | Nombre | Transformación | Ejemplo |
|---|---|---|---|
| 0 | `case_swap` | Mayúsculas/minúsculas aleatorias en palabras clave SQL | `OR` → `oR` |
| 1 | `whitespace_sub` | Reemplaza un espacio por `\t`, `\n`, `\r` o `\f` | `OR 1` → `OR\t1` |
| 2 | `inline_comment` | Inserta `/**/` entre dos tokens | `UNION SELECT` → `UNION/**/SELECT` |
| 3 | `comment_tail_variant` | Cambia el comentario final entre variantes válidas | `--` → `-- x` |
| 4 | `url_encode` | Codifica en URL caracteres aleatorios | `'` → `%27` |
| 5 | `double_url_encode` | Agrega una segunda capa de codificación | `%27` → `%2527` |
| 6 | `tautology_rewrite` | Reescribe una tautología por otra equivalente | `1=1` → `2>1` |
| 7 | `number_rewrite` | Reescribe un entero como expresión equivalente | `1` → `(2-1)` |
| 8 | `string_concat_split` | Parte un literal con `\|\|` | `'admin'` → `'ad'\|\|'min'` |
| 9 | `chr_encode` | Reemplaza un literal por concatenación de `CHR()` | `'a'` → `CHR(97)` |
| 10 | `dollar_quote` | Cambia comillas simples por *dollar quoting* | `'abc'` → `$$abc$$` |
| 11 | `hex_string` | Literal como hexadecimal decodificado | `'ab'` → `convert_from(decode('6162','hex'),'UTF8')` |
| 12 | `cast_noise` | Agrega casts redundantes y seguros por tipo | `1` → `1::int` |
| 13 | `paren_wrap` | Envuelve una expresión booleana en paréntesis redundantes | `1=1` → `((1=1))` |
| 14 | `operator_equivalent` | Sustituye un operador por uno equivalente | `<>` → `!=`, `UNION` → `UNION ALL` |
| 15 | `location_switch` | Mueve el parámetro entre query, form y JSON, en endpoints que aceptan varias | query → json |

## Preservación de semántica

Ningún operador garantiza preservar la funcionalidad: el oráculo es quien decide. Algunos operadores (`double_url_encode` en endpoints que decodifican una sola vez) rompen el payload casi siempre, y eso es intencional: el atacante debe aprender a evitarlos.

F1-T08 genera `results/summary/operator_preservation.csv` con, por operador y por familia: tasa de aplicabilidad y tasa de preservación verificada por el oráculo sobre todo el corpus `train`. El handoff de la Fase 1 incluye esa tabla.

## Pruebas obligatorias

- Determinismo: misma semilla, mismo resultado (hypothesis).
- `apply` nunca lanza excepción sobre ningún payload del corpus.
- Si devuelve un `Payload`, es distinto del de entrada.
- `location_switch` solo produce ubicaciones aceptadas por el endpoint.

## Historial

- 1.0 — versión inicial.
- 1.1 — `hex_string` se niega a reaplicarse sobre su propia salida (hex de hex siempre es hex válido para el oráculo, así que sin este límite el payload crece sin cota). El ejemplo documentado no cambia. Encontrado corriendo EXP-A1 contra el laboratorio real (F2-T05).
