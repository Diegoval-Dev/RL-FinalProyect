# Índice de documentación — WAF Arena

La documentación es la fuente de verdad del proyecto. Si el código y un documento se contradicen, se trata como bug: se decide cuál está bien, se corrige el otro y, si fue una decisión de diseño, se registra un ADR.

## Orden de lectura recomendado

1. [CLAUDE.md](../CLAUDE.md) — mapa general y reglas.
2. [00-vision/vision.md](00-vision/vision.md) — qué se investiga y por qué.
3. [03-plan/plan-maestro.md](03-plan/plan-maestro.md) — el relevo y el cronograma.
4. El documento de **tu** fase en `03-plan/`.
5. Los contratos que tu fase consume y produce en `02-contratos/`.
6. [04-metodologia-ai-first/flujo-de-trabajo.md](04-metodologia-ai-first/flujo-de-trabajo.md) — cómo trabajar con el agente.

## Contenido

### 00 — Visión
- [vision.md](00-vision/vision.md) — pregunta de investigación, RQ1–RQ5, alcance y no-alcance.
- [glosario.md](00-vision/glosario.md) — términos usados en todo el proyecto.
- [etica-y-alcance.md](00-vision/etica-y-alcance.md) — límites éticos y de operación.

### 01 — Arquitectura
- [arquitectura.md](01-arquitectura/arquitectura.md) — componentes, flujo de un request, entorno de dos velocidades.
- [repo-estructura.md](01-arquitectura/repo-estructura.md) — estructura de carpetas y dueño original de cada una.
- [stack.md](01-arquitectura/stack.md) — tecnologías y versiones.

### 02 — Contratos (interfaces entre fases)
- [README.md](02-contratos/README.md) — versionado y reglas de cambio.
- [env-atacante.md](02-contratos/env-atacante.md) — `WafArena/Attacker-v0`.
- [env-defensor.md](02-contratos/env-defensor.md) — `WafArena/Defender-v0`.
- [oraculo.md](02-contratos/oraculo.md) — verificación de efecto real de un payload.
- [operadores-mutacion.md](02-contratos/operadores-mutacion.md) — los 16 operadores del atacante.
- [features.md](02-contratos/features.md) — features de request y sesión del defensor.
- [datos-y-splits.md](02-contratos/datos-y-splits.md) — formatos de corpus, sesiones y splits.
- [agentes-y-checkpoints.md](02-contratos/agentes-y-checkpoints.md) — interfaz común de agentes y formato de checkpoint.
- [metricas.md](02-contratos/metricas.md) — definición exacta de cada métrica.
- [experimentos.md](02-contratos/experimentos.md) — formato de configuración YAML y de resultados.

### 03 — Plan
- [plan-maestro.md](03-plan/plan-maestro.md) — relevo, dependencias, cronograma, recortes de alcance.
- [fase-1-diego-laboratorio.md](03-plan/fase-1-diego-laboratorio.md)
- [fase-2-daniel-atacante-clasico.md](03-plan/fase-2-daniel-atacante-clasico.md)
- [fase-3-joaquin-deep-rl.md](03-plan/fase-3-joaquin-deep-rl.md)
- [fase-4-nelson-planning-selfplay.md](03-plan/fase-4-nelson-planning-selfplay.md)

### 04 — Metodología AI-first
- [flujo-de-trabajo.md](04-metodologia-ai-first/flujo-de-trabajo.md) — el ciclo de una tarea con agente.
- [reglas-para-agentes.md](04-metodologia-ai-first/reglas-para-agentes.md) — qué puede y qué no puede hacer el agente.
- [prompts.md](04-metodologia-ai-first/prompts.md) — biblioteca de prompts reutilizables.
- [definicion-de-terminado.md](04-metodologia-ai-first/definicion-de-terminado.md) — DoD de tarea, de fase y de proyecto.
- [convenciones.md](04-metodologia-ai-first/convenciones.md) — código, git, pruebas, nombres.

### 05 — Handoffs
- [plantilla-handoff.md](05-handoffs/plantilla-handoff.md)
- [handoff-1-diego-a-daniel.md](05-handoffs/handoff-1-diego-a-daniel.md)
- [handoff-2-daniel-a-joaquin.md](05-handoffs/handoff-2-daniel-a-joaquin.md)
- [handoff-3-joaquin-a-nelson.md](05-handoffs/handoff-3-joaquin-a-nelson.md)

### 06 — Decisiones (ADR)
- [README.md](06-decisiones/README.md) — índice y plantilla.

### 07 — Experimentos
- [catalogo.md](07-experimentos/catalogo.md) — todos los experimentos con ID, dueño y RQ.
- [registro.md](07-experimentos/registro.md) — bitácora de runs ejecutados.

### 08 — Informe
- [estructura-informe.md](08-informe/estructura-informe.md) — capítulos, dueño de cada uno, figuras obligatorias.
- [referencias.md](08-informe/referencias.md) — bibliografía con estado de verificación.

### 09 — Riesgos
- [riesgos.md](09-riesgos/riesgos.md) — riesgos, mitigaciones y plan de recortes.
