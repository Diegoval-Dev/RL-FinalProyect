# Visión del proyecto

## Pregunta de investigación

> ¿Puede un defensor entrenado con aprendizaje por refuerzo contra un atacante adaptativo superar a un WAF basado en reglas (ModSecurity + OWASP CRS) en la relación detección/falsos positivos, y qué tan bien generaliza a atacantes que no vio durante el entrenamiento?

## Subpreguntas

| ID | Pregunta | Fase que la responde | Experimentos |
|---|---|---|---|
| RQ1 | ¿Qué tan vulnerable es ModSecurity a un atacante que aprende con métodos simples (bandits, RL tabular)? | 2 (Daniel) | EXP-A1, A2, B1, C1, D1, D2 |
| RQ2 | ¿Un defensor RL reduce la tasa de evasión sin aumentar los falsos positivos respecto a ModSecurity PL1–PL4? | 3 (Joaquín) | EXP-E1, F1–F5, ABL-1, ABL-2 |
| RQ3 | ¿El self-play con pool de oponentes produce defensores más robustos que entrenar contra un atacante fijo? | 4 (Nelson) | EXP-I1, I2 |
| RQ4 | ¿Un atacante con presupuesto limitado de consultas mejora si aprende un modelo sustituto del defensor y planifica con él (Dyna)? | 4 (Nelson) | EXP-H1, H2, H3 |
| RQ5 | ¿Qué tan bien generalizan ambos agentes a familias de ataque y tráfico benigno no vistos? | 3 (parcial) y 4 | EXP-F6, F7, I3, I4, I5 |

El catálogo completo de experimentos está en [../07-experimentos/catalogo.md](../07-experimentos/catalogo.md).

## Hipótesis de trabajo

- **H1.** Un bandit UCB sobre operadores de mutación logra una tasa de evasión contra ModSecurity PL1 claramente mayor que la mutación aleatoria con el mismo presupuesto de consultas.
- **H2.** Existe un valor de α (costo del falso positivo) para el cual el defensor DQN domina en el sentido de Pareto a al menos un paranoia level de ModSecurity.
- **H3.** Los defensores entrenados con pool de oponentes conservan su tasa de detección contra atacantes de generaciones viejas; los entrenados con self-play ingenuo la pierden.
- **H4.** Dyna-Q alcanza la tasa de evasión de Q-learning con menos consultas reales al defensor.

Las hipótesis se pueden refutar. Un resultado negativo bien medido se reporta igual que uno positivo.

## Alcance

**Incluido**
- Inyección SQL contra PostgreSQL en una aplicación vulnerable propia (`vulnapp`).
- ModSecurity v3 con OWASP CRS en sus cuatro paranoia levels como línea base.
- Un atacante y un defensor como agentes RL, primero por separado y luego en self-play.
- Tráfico benigno realista, incluyendo casos difíciles que se parecen a ataques.
- Laboratorio reproducible con un solo comando.

**Excluido (o extensión posterior a la Fase 4)**
- XSS, SSRF, path traversal y cualquier otra familia que no sea SQLi.
- Otros motores de base de datos (MySQL, SQLite).
- Ataques basados en tiempo (`pg_sleep`) en el entrenamiento: son lentos de verificar. Pueden usarse solo en evaluación si sobra tiempo.
- Despliegue en producción o contra cualquier sistema externo.

## Qué cuenta como éxito del proyecto

1. Las cinco RQ tienen respuesta respaldada por runs registrados, con al menos 5 semillas por configuración principal.
2. `docker compose up` levanta el laboratorio completo en una máquina limpia.
3. La matriz de cruces entre generaciones de atacante y defensor existe y se puede regenerar desde los checkpoints.
4. Cada integrante puede explicar y defender el código de su fase.
