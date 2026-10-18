# Estructura del informe

El informe se escribe en Markdown en `report/capitulos/` y se exporta al formato que pida el catedrático. Cada fase entrega sus capítulos en su handoff; la Fase 4 solo agrega los suyos y consolida, sin reescribir capítulos ajenos más allá de unificar formato.

## Capítulos

| # | Archivo | Contenido | Dueño | Se entrega en |
|---|---|---|---|---|
| 1 | `01-introduccion.md` | Problema, motivación, pregunta de investigación, RQ1–RQ5, contribuciones | Diego | HANDOFF-1 |
| 2 | `02-trabajo-relacionado.md` | Evasión de WAF por mutación, RL en seguridad, self-play. Solo referencias verificadas | Diego (base) y cada fase agrega lo suyo | HANDOFF-1 a HANDOFF-3 |
| 3 | `03-laboratorio.md` | Laboratorio, oráculo, corpus, tráfico benigno, entornos y su formulación como MDP/POMDP, dos velocidades; protocolo experimental y estadística | Diego; protocolo experimental: Daniel | HANDOFF-1 y HANDOFF-2 |
| 4 | `04-atacante-clasico.md` | Bandits, DP, MC, TD. Respuesta a RQ1 | Daniel | HANDOFF-2 |
| 5 | `05-deep-rl.md` | Defensor lineal y DQN, Pareto, ablaciones, atacante PG. Respuesta a RQ2 y generalización del defensor estático | Joaquín | HANDOFF-3 |
| 6 | `06-planning-selfplay.md` | Dyna, self-play, matriz de cruces. Respuestas a RQ3 y RQ4 | Nelson | v1.0 |
| 7 | `07-generalizacion.md` | Respuesta a RQ5 combinando F6, F7, I3–I5; brecha simulado/real | Nelson | v1.0 |
| 8 | `08-etica.md` | Ética, alcance, política de publicación, limitación del oráculo en producción | Diego | HANDOFF-1 |
| 9 | `09-conclusiones.md` | Respuesta corta a cada RQ, limitaciones consolidadas, trabajo futuro | Nelson | v1.0 |

## Figuras obligatorias

| Figura | Experimento | Capítulo |
|---|---|---|
| Arquitectura del laboratorio | — | 3 |
| Regret acumulado de bandits | EXP-A1 | 4 |
| Recuperación ante cambio de PL | EXP-A2 | 4 |
| SARSA vs. Q-learning: recompensa y rotura en entrenamiento | EXP-D1 | 4 |
| Tabla de vulnerabilidad de ModSecurity por método y PL | F2-T09 | 4 |
| Ablación de DQN | EXP-F1–F4 | 5 |
| Frontera de Pareto contra PL1–PL4 | EXP-F5 | 5 |
| Diversidad contra evasión por entropía | EXP-G4 | 5 |
| Evasión contra consultas reales | EXP-H1 | 6 |
| TPR por generación: ingenuo vs. pool | EXP-I1 | 6 |
| Matriz de cruces | EXP-I2 | 6 |
| Tabla de generalización | EXP-F6, F7, I3–I5 | 7 |

Toda figura se genera con un script en `report/figuras/make_<exp_id>.py` desde `results/summary/`. Ninguna figura se edita a mano.

## Reglas de redacción

- Cada número se cita con su origen: `(EXP-F5, alpha-4, 5 semillas)`.
- Las comparaciones usan el IC de la diferencia. Si incluye el 0, se escribe que no hay diferencia detectable.
- Los resultados negativos se reportan igual que los positivos.
- Las simplificaciones del laboratorio se declaran en el capítulo donde aparecen y se consolidan en el 9: verificación de funcionalidad gratuita para el atacante, oráculo perfecto, app propia, una sola familia de ataque.
- Registro académico formal en español. Para revisar estilo y verificación de afirmaciones se puede usar el prompt [P8](../04-metodologia-ai-first/prompts.md#p8--redactar-un-capítulo-del-informe).
