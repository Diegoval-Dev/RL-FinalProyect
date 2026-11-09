# Diseño F4-T11: informe integrado y entrega

## Intención

Cerrar el informe de Fase 4 y facilitar que otra persona instale el proyecto, levante el laboratorio y encuentre los runs, resúmenes y figuras que respaldan cada conclusión.

## Enfoque

La fase añadirá los capítulos 6 y 9, mantendrá el capítulo 7 existente y alineará el identificador de RQ en la introducción con `docs/00-vision/vision.md` y el catálogo de experimentos. Las cifras se tomarán de `results/summary/` y el registro; las corridas crudas no versionadas no se presentarán como artefactos disponibles.

El README usará el archivo Compose que ya existe en `lab/`, sin duplicar ni reestructurar servicios. Documentará instalación, demo, pruebas, rutas de reproducción y límites de la evidencia.

## Alternativas consideradas

1. **Documentar `docker compose -f lab/docker-compose.yml up`:** reutiliza el único Compose del laboratorio y mantiene T11 como trabajo de documentación; es el enfoque elegido.
2. **Añadir un Compose raíz con `include`:** haría disponible `docker compose up` sin `-f`, pero añade configuración operativa fuera del alcance documental acordado para esta tarea.
3. **Duplicar servicios en la raíz:** crea definiciones que pueden divergir y se descarta.

## Límites

- No se recalculan ni editan CSV de resultados.
- No se modifican contratos ni algoritmos.
- No se crea `v1.0` mientras falte la validación de clonación limpia por otra persona y la revisión humana final exigidas por el DoD.
- El capítulo 2 está ausente del repositorio y pertenece a entregas previas; se documentará como pendiente de integración sin inventar ni atribuir contenido a otras fases.

## Criterio de cierre de esta rama

Los capítulos nuevos y el README enlazarán cada resultado a su resumen versionado, run registrado y figura existente cuando corresponda. El estado de release distinguirá las verificaciones ejecutadas aquí de las tareas que requieren a otra persona.
