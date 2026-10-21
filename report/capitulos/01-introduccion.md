# 1. Introducción

## Problema y motivación

Los *Web Application Firewalls* (WAF) basados en reglas, como ModSecurity con el OWASP Core Rule
Set (CRS), son la primera línea de defensa contra la inyección SQL. Su eficacia depende de reglas
escritas a mano que un atacante puede eludir reescribiendo el mismo payload de formas
semánticamente equivalentes. La pregunta que motiva este proyecto es si un atacante y un defensor
que **aprenden por refuerzo** pueden mejorar, respectivamente, la evasión y la detección, y qué
revela ese enfrentamiento sobre la robustez de un WAF de reglas.

## Pregunta de investigación

La pregunta general y las cinco preguntas de investigación (RQ1–RQ5) están definidas en
[docs/00-vision/vision.md](../../docs/00-vision/vision.md). En resumen:

- **RQ1:** ¿Qué tan vulnerable es ModSecurity (PL1–PL4) a un atacante de mutación clásico (bandits
  y métodos tabulares)?
- **RQ2:** ¿Mejora un defensor con aprendizaje profundo (DQN) la frontera entre bloqueo de ataques
  y falsos positivos frente a ModSecurity fijo?
- **RQ3:** ¿Qué aporta la planificación (Dyna) frente a métodos libres de modelo con el mismo
  presupuesto de consultas?
- **RQ4:** ¿El self-play con un *pool* de oponentes produce políticas más generales que el
  entrenamiento contra un oponente fijo?
- **RQ5:** ¿Cuánto generalizan los agentes a familias de ataque y a tráfico benigno difícil no
  vistos, y cuál es la brecha entre el modo rápido y el modo real?

## Alcance

El alcance está cerrado a **inyección SQL contra PostgreSQL** ([ADR-0001](../../docs/06-decisiones/adr-0001-solo-sqli.md)).
XSS queda como extensión posterior a la entrega final.

## Contribuciones de la Fase 1

Esta fase no responde ninguna RQ; construye la base sobre la que las demás fases experimentan:

1. Un laboratorio Docker aislado (`internal: true`, sin salida a internet) con una aplicación
   vulnerable propia, PostgreSQL instrumentada, cuatro instancias de ModSecurity (PL1–PL4), un
   proxy defensor y un honeypot.
2. Un **oráculo verificado** que decide con certeza si un payload es funcional y si tuvo efecto,
   mediante la huella estructural de la consulta (`pglast`) y canarios.
3. Un corpus de 528 payloads funcionales verificados y 5 200 sesiones de tráfico benigno, con
   *splits* congelados.
4. Dieciséis operadores de mutación, los dos entornos Gymnasium (`Attacker-v0`, `Defender-v0`) y
   los *backends* rápido y real.

Los detalles de diseño y verificación están en el capítulo 3.
