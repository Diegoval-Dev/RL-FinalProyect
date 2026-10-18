# Registro de experimentos

Una fila por configuración (`run_name`) terminada de un experimento del [catálogo](catalogo.md). Las filas no se borran: si un run resultó inválido (bug, configuración equivocada), se marca como **inválido** con la razón y se agrega una fila nueva.

Los números de la columna *Resultado* se copian de `results/summary/<exp_id>.csv`; nunca se escriben de memoria.

| Fecha | Exp | `run_name` | Commit | Semillas | Resultado principal (media [IC 95 %]) | Estado | Responsable | Notas |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

Estados posibles: **válido**, **inválido** (con razón), **exploratorio** (no se usa en el informe).
