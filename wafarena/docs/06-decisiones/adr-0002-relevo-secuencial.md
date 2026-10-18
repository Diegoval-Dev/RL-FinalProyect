# ADR-0002: Relevo secuencial con una sola dependencia por persona

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** —

## Contexto
El equipo quiere que nadie dependa del trabajo de otro más de una vez. Una división por roles paralelos (infraestructura, atacante, defensor, evaluación) genera dependencias cruzadas continuas: el defensor necesita al atacante, el atacante necesita el entorno, todos necesitan la evaluación.

## Opciones consideradas
1. Roles paralelos con integración continua.
2. Relevo secuencial: cada fase recibe una vez el entregable de la anterior y es dueña del repositorio completo durante su turno.

## Decisión
Opción 2. Orden: Diego (laboratorio) → Daniel (runner y atacante clásico) → Joaquín (deep RL) → Nelson (planning, self-play, cierre). La frontera entre fases son los contratos de `docs/02-contratos/` y el handoff.

## Consecuencias
- Cada persona tiene una sola dependencia y, después de aceptar el handoff, trabaja sin esperar a nadie.
- Un atraso en una fase se propaga a las siguientes. Mitigación: recortes de alcance definidos de antemano en el plan maestro, aplicables sin consultar.
- Mientras no es su turno, cada persona puede adelantar trabajo que solo depende de los contratos (algoritmos contra entornos de juguete), sin romper la regla.
- El conocimiento de una fase debe quedar escrito; el handoff y los contratos se vuelven entregables tan importantes como el código.
