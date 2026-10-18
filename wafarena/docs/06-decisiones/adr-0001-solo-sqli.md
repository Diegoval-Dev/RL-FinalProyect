# ADR-0001: Solo SQL injection contra PostgreSQL

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** —

## Contexto
El proyecto tiene 12 semanas y una escalera de algoritmos larga. Cada familia de ataque nueva necesita su propio oráculo, sus operadores y su tráfico benigno difícil. Cada motor de base de datos cambia la sintaxis válida de los payloads.

## Opciones consideradas
1. SQLi y XSS desde el inicio.
2. SQLi contra varios motores.
3. SQLi contra un solo motor; XSS como extensión.

## Decisión
Opción 3, con PostgreSQL. XSS (con oráculo de navegador headless) queda como extensión posterior a `v1.0`.

## Consecuencias
- El oráculo se puede apoyar en `libpg_query` para comparar estructuras de consulta.
- Los operadores pueden usar sintaxis propia de PostgreSQL (`$$`, `CHR`, `::`).
- La generalización (RQ5) se mide entre familias de SQLi, no entre tipos de ataque. El informe lo declara.
