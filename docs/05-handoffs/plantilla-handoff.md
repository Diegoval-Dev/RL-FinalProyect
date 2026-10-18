# HANDOFF-<N>: <quien entrega> → <quien recibe>

> Un handoff es la única dependencia entre dos personas del equipo. Debe permitir que quien recibe trabaje sin preguntarle nada a quien entregó. Si algo hace falta saber y no está aquí, en los contratos o en el código, el handoff está incompleto.

| | |
|---|---|
| **Tag** | `v0.<N>-fase<N>` |
| **Commit** | `<sha>` |
| **Fecha de entrega** | |
| **Ventana de aceptación** | hasta `<fecha + 1 día hábil>` |
| **Estado** | Borrador / Entregado / Aceptado |

## 1. Qué se entrega

Resumen en 5 líneas de lo que quedó funcionando.

## 2. Versiones de contratos implementadas

| Contrato | Versión | Cambios respecto a la versión anterior |
|---|---|---|

## 3. Cómo correrlo desde cero

Comandos exactos, en orden, en una máquina limpia.

## 4. Checklist de aceptación

Quien recibe lo corre en **su** máquina. Cada punto es un comando con un resultado esperado verificable.

- [ ] …

## 5. Resultados entregados

| Experimento | Resumen | Hallazgo principal (con número citado) |
|---|---|---|

## 6. Checkpoints de referencia publicados

| ID | Ruta | Cómo se eligió | Métrica en `val` |
|---|---|---|---|

## 7. Recortes y desviaciones del plan

Qué no se hizo o se hizo distinto, y por qué. Enlazar ADR si aplica.

## 8. Problemas conocidos

Bugs, limitaciones o cosas frágiles que quien recibe debe saber.

## 9. Datos útiles para la siguiente fase

Rendimiento medido (pasos/s), tiempos de entrenamiento típicos, hiperparámetros que funcionaron, cosas que no funcionaron.

## 10. Capítulos del informe entregados

## 11. Firma de aceptación

- [ ] Quien recibe corrió el checklist completo en su máquina.
- [ ] Problemas encontrados en la ventana: _(lista o "ninguno")_
- [ ] Aceptado por: ______ · Fecha: ______
- [ ] `CLAUDE.md` actualizado con la nueva fase activa.
