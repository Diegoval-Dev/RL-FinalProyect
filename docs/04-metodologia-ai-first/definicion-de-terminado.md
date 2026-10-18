# Definición de terminado

## Tarea

Una tarea `F<N>-T<nn>` está terminada cuando:

- [ ] Cada criterio de aceptación tiene al menos una prueba y todas pasan.
- [ ] `make lint && make test` pasa; `make test-lab` y `make smoke` también si la tarea toca laboratorio o entornos.
- [ ] El diff solo toca archivos del plan aprobado (o las desviaciones están explicadas en el PR).
- [ ] No hay aleatoriedad sin semilla ni hiperparámetros escritos en el código.
- [ ] Si cambió una interfaz, el contrato correspondiente está actualizado con su versión.
- [ ] Si hubo una decisión de diseño, existe su ADR.
- [ ] Si corrió un experimento, está en el registro.
- [ ] La tarea está marcada en *Estado* del documento de la fase.
- [ ] El autor humano revisó el diff completo y puede explicarlo.

## Fase

Una fase está terminada cuando:

- [ ] Todas sus tareas están terminadas o recortadas (los recortes están en *Hallazgos* y siguen el orden del plan maestro).
- [ ] CI está en verde en la rama principal.
- [ ] Todos los experimentos de la fase están en el registro con su resumen en `results/summary/`.
- [ ] Los checkpoints de referencia que la fase publica están en `checkpoints/refs/` y cargan.
- [ ] Los capítulos del informe que le tocan están escritos, con números citados y figuras generadas por script.
- [ ] El handoff está completo, sin `[COMPLETAR]`, y su checklist de aceptación se corrió de punta a punta.
- [ ] Existe el tag de la fase.

## Proyecto

El proyecto está terminado cuando:

- [ ] RQ1 a RQ5 tienen respuesta en el informe respaldada por runs registrados.
- [ ] Las configuraciones principales tienen al menos 5 semillas (10 en bandits y tabulares), o la excepción está justificada en el informe.
- [ ] `git clone` + `make setup` + `docker compose up` funciona en una máquina limpia, probado por alguien que no sea Nelson.
- [ ] La matriz de cruces se regenera desde checkpoints con un comando.
- [ ] El dashboard o su reemplazo funciona en la demo.
- [ ] Cada número del informe se puede rastrear a un `exp_id` y `run_name`.
- [ ] Todas las referencias del informe están verificadas.
- [ ] El capítulo de ética y limitaciones está completo.
- [ ] Cada integrante ensayó la explicación de su fase.
- [ ] Existe el tag `v1.0`.
