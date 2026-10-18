# ADR-0007: App objetivo propia y stack único en Python

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** F1-T02

## Contexto
Juice Shop y DVWA son apps vulnerables conocidas, pero no controlamos exactamente qué consultas ejecutan ni podemos instrumentarlas para el oráculo sin modificarlas. Usar lenguajes distintos en la app y en los agentes complica el modo rápido.

## Opciones consideradas
1. Juice Shop o DVWA.
2. App propia en Django o Express.
3. App propia mínima en FastAPI, en el mismo lenguaje que los agentes.

## Decisión
Opción 3: `vulnapp` con 8 endpoints vulnerables catalogados. El modo rápido importa sus funciones de consulta directamente.

## Consecuencias
- Sabemos con exactitud qué es vulnerable, lo que hace el oráculo trivial de especificar.
- Menos realismo que una app de terceros. La extensión "transferir el defensor a una segunda app no vista" queda propuesta para después de `v1.0`.
