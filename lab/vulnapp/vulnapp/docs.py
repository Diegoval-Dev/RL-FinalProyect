"""Renders lab/vulnapp/ENDPOINTS.md from the endpoint registry.

Usage: python -m vulnapp.docs > lab/vulnapp/ENDPOINTS.md
"""

from vulnapp.queries import ENDPOINTS, EndpointSpec
from vulnapp.reference import REFERENCE_PAYLOADS, ReferencePayload

EXPECTATION_TEXT = {
    "extra_rows": "Devuelve más filas que la entrada benigna `{value}`",
    "rows_contain": "La respuesta contiene `{value}`",
    "error_text": "Error de PostgreSQL que contiene `{value}`",
    "blind_pair": "Con `{value}` (condición falsa) la respuesta difiere de la verdadera",
    "side_effect_author": "Aparece un comentario del autor `{value}`",
}

HEADER = """# Endpoints vulnerables de vulnapp

Generado con `python -m vulnapp.docs`; no editar a mano. Una prueba unitaria falla si este archivo
difiere del registro en `vulnapp/queries.py` y `vulnapp/reference.py`.

Las consultas concatenan los valores sin escapar a propósito. Los payloads de referencia son
clásicos y públicos, y solo se dirigen a `vulnapp` dentro de la red interna del laboratorio.

Los errores de PostgreSQL se devuelven al cliente tal cual (HTTP 500), lo que hace posibles los
payloads de la familia `error`.
"""

BENIGN_FLOWS = """## Flujos benignos

| Ruta | Descripción |
|---|---|
| `GET /` | Productos destacados |
| `GET /health` | Estado del servicio |
| `GET /comments?product_id=` | Últimos comentarios de un producto (consulta parametrizada) |
| `GET /cart` | Carrito del usuario 2 (consulta parametrizada) |

Búsqueda, catálogo, login, carrito y comentarios benignos usan los endpoints de arriba con
entradas legítimas.
"""


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def render_payload_row(ref: ReferencePayload) -> str:
    effect = EXPECTATION_TEXT[ref.expect.kind].format(value=ref.expect.value)
    cells = [ref.family, f"`{ref.param}`", f"`{ref.text}`", effect]
    return "| " + " | ".join(escape_cell(cell) for cell in cells) + " |"


def render_endpoint(spec: EndpointSpec) -> str:
    routes = ", ".join(f"`{method} {spec.path}`" for method in spec.methods)
    benign = ", ".join(f"`{key}={value}`" for key, value in spec.benign_values.items())
    payload_rows = [
        render_payload_row(ref) for ref in REFERENCE_PAYLOADS if ref.endpoint == spec.name
    ]
    return "\n".join(
        [
            f"## {spec.name}",
            "",
            f"- **Rutas:** {routes}",
            f"- **Parámetros:** {', '.join(f'`{param}`' for param in spec.params)}",
            f"- **Ubicaciones aceptadas:** {', '.join(spec.locations)}",
            f"- **Familias aplicables:** {', '.join(spec.families)}",
            f"- **Entrada benigna:** {benign}",
            "",
            "Plantilla SQL:",
            "",
            "```sql",
            spec.template,
            "```",
            "",
            "| Familia | Parámetro | Payload de referencia | Efecto esperado |",
            "|---|---|---|---|",
            *payload_rows,
            "",
        ]
    )


def render_endpoints_md() -> str:
    sections = [render_endpoint(spec) for spec in ENDPOINTS]
    return "\n".join([HEADER, *sections, BENIGN_FLOWS])


if __name__ == "__main__":
    print(render_endpoints_md(), end="")
