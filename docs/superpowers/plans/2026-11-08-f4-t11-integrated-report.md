# Plan de implementación F4-T11: informe integrado

> **Para agentes ejecutores:** usar `superpowers:executing-plans` para llevar este plan por tareas; mantener las casillas como registro.

**Objetivo:** integrar las respuestas de Fase 4, completar las conclusiones y dejar el repositorio reproducible con cifras rastreables.

**Arquitectura:** capítulos de informe con referencias a resúmenes y al registro, más un README raíz que usa el Compose existente del laboratorio.

**Tecnología:** Markdown en español, Docker Compose, YAML.

**Diseño:** `docs/superpowers/specs/2026-11-08-f4-t11-integrated-report-design.md`

## Restricciones globales

- Ninguna cifra nueva sin `exp_id`, `run_name`/`run_id`, commit y resumen versionado.
- No modificar archivos de `results/`.
- Mantener el laboratorio en red interna y no publicar puertos desde el Compose base.
- Documentación e informe en español; commits en inglés según instrucción del usuario.
- No crear el tag `v1.0` antes de satisfacer el DoD completo.

## Tarea 1: Entrada reproducible del repositorio

**Archivos:** `README.md`.

- [ ] Documentar requisitos, setup, `docker compose -f lab/docker-compose.yml up`, `make demo`, apagado, lint, pruebas y smoke.
- [ ] Enlazar configuraciones, figuras y resúmenes versionados de los experimentos principales.
- [ ] Explicar que las salidas crudas están ignoradas y que regenerar resultados cuesta tiempo/recursos.

## Tarea 2: Capítulo de planning y self-play

**Archivos:** `report/capitulos/06-planning-selfplay.md`.

- [ ] Responder RQ3 con EXP-I1 e I2; reportar incertidumbre y alcance de test.
- [ ] Responder RQ4 con EXP-H1/H2 y declarar el recorte de H3.
- [ ] Enlazar tablas/curvas y citar commits, run names y semillas desde el registro.

## Tarea 3: Generalización, referencias y coherencia

**Archivos:** `report/capitulos/07-generalizacion.md`, `report/capitulos/01-introduccion.md`, `docs/08-informe/referencias.md`.

- [ ] Confirmar la atribución de RQ3/RQ4 contra visión y catálogo; corregir la discrepancia en la introducción.
- [ ] Verificar metadatos de fuentes bibliográficas y marcar el estado con las URL consultadas.
- [ ] Mantener los resultados I3–I5 y R1 limitados a sus suites y denominadores reales.

## Tarea 4: Conclusiones y limitaciones consolidadas

**Archivos:** `report/capitulos/09-conclusiones.md`.

- [ ] Dar una respuesta breve a cada RQ con referencias a capítulos, resúmenes y runs.
- [ ] Consolidar límites del oráculo, espacio de ataque, laboratorio, semillas, selección y evaluación.
- [ ] Distinguir resultados negativos, resultados descriptivos y preguntas que siguen sin respuesta.

## Tarea 5: Estado y verificación de entrega

**Archivos:** `docs/03-plan/fase-4-nelson-planning-selfplay.md`.

- [ ] Revisar documentación, enlaces, figuras, fuentes y rastreabilidad de los números nuevos.
- [ ] Dejar instrucciones para que otra persona valide el arranque desde una clonación limpia.
- [ ] Registrar la prueba independiente y revisión humana como pendientes hasta que alguien distinto de Nelson las complete.
- [ ] No marcar F4-T11 completo ni crear `v1.0` mientras queden bloqueos del DoD.

## Riesgos de revisión

- Confundir número de sesiones con solicitudes emitidas en I5/R1.
- Presentar tres semillas o una sola cohorte como evidencia de variabilidad de entrenamiento.
- Interpretar igualdad de métricas fast/real como equivalencia universal o de latencia.
- Decir que el pool supera robustamente al self-play ingenuo pese a IC superpuestos.
- Tratar el tag v1.0 como un paso de rutina antes de la revisión externa requerida.
