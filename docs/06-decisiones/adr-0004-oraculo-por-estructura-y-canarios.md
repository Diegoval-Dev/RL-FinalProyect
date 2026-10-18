# ADR-0004: Oráculo por cambio de estructura y canarios

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** F1-T03, F1-T04

## Contexto
Si el oráculo no verifica que un payload mutado sigue funcionando, el atacante aprende a "evadir" enviando basura inofensiva y el resultado principal del proyecto es falso. Detectar el efecto solo con canarios es difícil para `boolean_blind`, cuyo efecto no se ve en una sola respuesta.

## Opciones consideradas
1. Solo canarios (lectura o escritura de valores secretos).
2. Solo comparación de la estructura de la consulta ejecutada contra la plantilla.
3. Ambas: la estructura decide la funcionalidad para cualquier familia y los canarios aportan evidencia más fuerte cuando existen.

## Decisión
Opción 3. `vulnapp` registra cada SQL ejecutado con un rol separado; el oráculo compara la huella de `libpg_query` (vía `pglast`) con la de la plantilla y busca canarios en respuesta, errores y escrituras.

## Consecuencias
- Un criterio único para todas las familias, verificable con pruebas.
- Depende de que `vulnapp` registre fielmente cada consulta: es una propiedad de nuestra app, no de una app arbitraria. Por eso se usa una app propia ([ADR-0007](adr-0007-app-propia-python.md)).
- El informe reporta por separado cuántas evasiones tienen evidencia de canario y cuántas solo de estructura.
