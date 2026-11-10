# 2. Trabajo relacionado

Este capítulo ubica el proyecto frente a la literatura que lo motivó. Solo cita fuentes cotejadas en [referencias verificadas](../../docs/08-informe/referencias.md). Los resultados propios no se discuten aquí; están en los capítulos 4 a 7.

## Evasión de WAF por mutación

WAF-A-MoLE (`demetrio2020wafamole`) trata la evasión de un WAF como un problema de búsqueda: parte de un payload malicioso y le aplica operaciones que preservan su semántica hasta que el WAF deja de bloquearlo. La idea de mutar sin romper la función del ataque es la base del espacio de acciones del atacante de este proyecto (16 operadores, capítulo 3), y el oráculo del laboratorio cumple el papel de verificar que la función se conserve.

Este proyecto se diferencia en tres puntos. Primero, el atacante no es una búsqueda por ataque individual sino una política aprendida con métodos de RL de distintas familias (bandits, programación dinámica, Monte Carlo, TD, policy gradient y planificación; capítulos 4 a 6). Segundo, el WAF atacado, ModSecurity con el OWASP Core Rule Set (`owaspcrs`) en cuatro niveles de paranoia, se compara además con un defensor que también aprende. Tercero, la evasión se mide con presupuesto de consultas reales, no solo con tasa de éxito.

## Aprendizaje por refuerzo aplicado a inyección SQL

Erdődi, Sommervoll y Zennaro (`erdodi2021sqlq`) modelan la explotación de una inyección SQL como un reto de captura de bandera formulado como proceso de decisión de Markov y entrenan agentes de Q-learning en un escenario sintético simplificado. Es el antecedente más cercano en cuanto a formular SQLi como un problema de RL. Su escenario es una simulación del reto de explotación; este proyecto, en cambio, usa una aplicación vulnerable real en un laboratorio aislado, un WAF real como adversario y un oráculo basado en la consulta ejecutada y en canarios (ADR-0004).

## Algoritmos de RL usados como herramientas

Los métodos del curso siguen a Sutton y Barto (`sutton2018`): bandits, programación dinámica, Monte Carlo, diferencias temporales y aproximación de funciones. Para el defensor profundo se usó DQN (`mnih2015dqn`) y las variantes evaluadas en la ablación del capítulo 5: Double DQN (`vanhasselt2016double`), arquitectura Dueling (`wang2016dueling`) y *Prioritized Experience Replay* (`schaul2016per`). El atacante de gradiente de política parte de REINFORCE (`williams1992reinforce`) y de PPO (`schulman2017ppo`) con estimación de ventaja generalizada (`schulman2016gae`); el contexto de métodos actor-critic asíncronos es `mnih2016a3c`. Las implementaciones siguen el estilo de archivo único de CleanRL (`huang2022cleanrl`, ADR-0006) y los entornos exponen la API de Gymnasium (`gymnasium`).

La planificación del atacante (capítulo 6) usa la arquitectura Dyna (`sutton1990dyna`), que combina aprendizaje con experiencia real y actualizaciones sobre un modelo aprendido. En este proyecto el modelo es un sustituto supervisado de la respuesta del defensor, y solo las consultas reales consumen presupuesto.

## Self-play y entrenamiento contra adversarios propios

AlphaZero (`silver2017alphazero`) es la referencia habitual de aprendizaje por self-play, donde el agente mejora jugando contra versiones de sí mismo. Bansal et al. (`bansal2018emergent`) estudian la competencia entre agentes como fuente de comportamientos complejos. Ambos trabajos justifican la pregunta de RQ3, pero ninguno de los dos es un entorno de seguridad ni asimétrico como este: aquí atacante y defensor tienen acciones, observaciones y ritmos de entrenamiento distintos, y la comparación relevante es entre alternancia ingenua y entrenamiento contra un pool de generaciones anteriores. Este capítulo no usa esas fuentes para afirmar que el pool deba funcionar; el resultado propio, que no muestra una superioridad robusta, está en el capítulo 6.

## Lo que este capítulo no afirma

No se hace una revisión sistemática de la literatura sobre WAF con aprendizaje automático ni sobre RL ofensivo. Las fuentes de este capítulo son las verificadas hasta la fecha de entrega; la cobertura es deliberadamente acotada y no sustituye una revisión exhaustiva.
