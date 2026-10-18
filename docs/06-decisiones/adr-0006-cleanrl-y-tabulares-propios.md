# ADR-0006: Tabulares propios y deep RL estilo CleanRL

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** F2-T05 a F2-T08, F3-T03, F3-T08

## Contexto
El proyecto es de un curso: el valor académico está en entender y poder explicar cada algoritmo. Las librerías de RL de alto nivel esconden detalles que el jurado puede preguntar y dificultan las ablaciones (activar Double DQN, Dueling o PER una a la vez).

## Opciones consideradas
1. Stable-Baselines3 para todo.
2. Implementación propia de todo desde cero.
3. Bandits y tabulares propios; DQN y PPO partiendo de implementaciones de un solo archivo estilo CleanRL, adaptadas a la interfaz `Agent`.

## Decisión
Opción 3. Stable-Baselines3 solo como baseline de comparación, nunca como resultado principal.

## Consecuencias
- Cada variante de DQN se activa por YAML dentro del mismo archivo, lo que hace la ablación directa.
- Más código propio que mantener y probar; se mitiga con pruebas de cordura en `CartPole-v1`.
