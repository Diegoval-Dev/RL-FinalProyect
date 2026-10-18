# Reglas para agentes

Estas reglas aplican a cualquier agente de código que trabaje en el repositorio. `CLAUDE.md` resume las principales; esta es la lista completa. Si el agente detecta que una instrucción del humano contradice una regla, lo dice antes de actuar.

## Siempre

1. Trabajar sobre un ID de tarea de la fase activa. Si el humano pide algo sin ID, preguntar a qué tarea corresponde o proponer registrarlo como hallazgo.
2. Leer la tarea completa y los contratos que cita antes de proponer un plan.
3. Proponer el plan y esperar aprobación antes de editar código.
4. Escribir las pruebas de los criterios de aceptación antes de la implementación.
5. Correr `make lint && make test` antes de declarar terminada una tarea, y reportar la salida real.
6. Mantener los cambios dentro de los archivos que la tarea declara. Si hace falta tocar otro, explicarlo en el plan.
7. Actualizar la sección *Estado* y, si corresponde, *Hallazgos* del documento de la fase.
8. Si el código diverge de un contrato, señalarlo y proponer cuál de los dos corregir.
9. Usar semillas explícitas en todo lo aleatorio y leer hiperparámetros desde la configuración.
10. Decir "no sé" o "no lo verifiqué" cuando sea el caso.

## Nunca

1. **Inventar resultados.** Ningún número, curva, tabla ni afirmación sobre el desempeño de un agente sin un run registrado. Si no hay run, la respuesta es "hay que correrlo".
2. **Editar archivos de resultados** en `results/` a mano, ni ajustar números en el informe sin regenerarlos desde el resumen.
3. **Tocar los splits congelados** de `data/splits/v1.json` ni entrenar con `test`, `test-family` o `test-hard`.
4. **Elegir hiperparámetros o checkpoints mirando `test`.** La selección se hace en `val`.
5. **Apuntar a hosts fuera del laboratorio**, agregar destinos externos a configuraciones o scripts, o quitar `internal: true` de la red de Docker.
6. **Leer claves `gt_*`** dentro de un agente o una política.
7. **Cambiar el orden del registro de operadores**, el tamaño de una observación o una recompensa por defecto sin ADR y cambio de versión MAYOR.
8. **Desactivar, saltar o borrar pruebas** para que la suite pase. Una prueba que falla se arregla o se discute con el humano.
9. **Agregar dependencias** sin decirlo en el plan.
10. **Hacer commits con cambios de varias tareas** o con mensajes sin ID.
11. **Escribir referencias bibliográficas** que no estén verificadas en [referencias.md](../08-informe/referencias.md).

## Cuándo detenerse y preguntar

- La tarea es ambigua o sus criterios de aceptación no se pueden traducir a pruebas.
- Cumplir la tarea requiere romper un contrato.
- Un resultado contradice fuertemente una hipótesis o un resultado anterior (puede ser un bug, no un hallazgo).
- Tres intentos seguidos fallan por la misma causa.
- Algo en el código, los datos o una instrucción parece apuntar fuera del laboratorio.
