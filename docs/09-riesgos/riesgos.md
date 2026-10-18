# Riesgos

Cada riesgo tiene un dueño que lo vigila en su fase. Los riesgos específicos de cada fase están también en su documento.

| # | Riesgo | Probabilidad | Impacto | Mitigación | Dueño |
|---|---|---|---|---|---|
| R1 | El atacante "hace trampa" con payloads rotos que el oráculo no detecta | Media | Invalida todo | Oráculo por estructura y canarios; 5 garantías probadas antes de cualquier entrenamiento | Diego |
| R2 | Una fase se atrasa y arrastra a las siguientes | Alta | Alto | Recortes predefinidos en el [plan maestro](../03-plan/plan-maestro.md#recortes-de-alcance), aplicables sin consultar; trabajo previo independiente | Cada dueño |
| R3 | Handoff incompleto obliga a consultar a quien entregó | Media | Medio | Plantilla con checklist ejecutable; ventana de aceptación de 1 día; prompt P6 que marca `[COMPLETAR]` | Quien entrega |
| R4 | Entrenamiento demasiado lento | Media | Alto | Modo rápido con caché; meta de 300 pasos/s medida en F1; reducir pasos antes que semillas | Diego, luego cada dueño |
| R5 | El defensor aprende a bloquear todo | Media | Medio | α suficientemente alto, benignos difíciles en entrenamiento, FPR vigilado desde la primera evaluación | Joaquín |
| R6 | Self-play inestable o cíclico | Alta | Medio | Pool de oponentes, asimetría de ritmo, evaluación contra referencias fijas | Nelson |
| R7 | Fuga de información entre entrenamiento y evaluación | Baja | Invalida resultados | Splits congelados con hashes, división por agrupación, runner que rechaza splits de prueba | Diego, luego el runner (Daniel) |
| R8 | Selección de modelos mirando `test` | Media | Invalida resultados | Reglas de selección escritas antes de los experimentos; selección solo en `val` | Cada dueño |
| R9 | Resultados reportados que no vienen de runs (incluido texto generado por el agente) | Media | Integridad académica | Regla "ningún número sin run", registro obligatorio, prompt P5 | Todos |
| R10 | Código que nadie del equipo entiende | Media | Alto en la defensa | Plan aprobado por el humano, revisión del diff completo, regla de comprensión | Todos |
| R11 | Solapamiento con la tesis de Diego (detección ML en RASP) | Baja | Medio | El aporte de este proyecto es el RL y el self-play, no el detector; confirmarlo con el catedrático y el asesor de tesis | Diego |
| R12 | Contenedores con salida a internet o payloads hacia terceros | Baja | Alto | `internal: true`, prueba automática de aislamiento, reglas para agentes | Diego |
