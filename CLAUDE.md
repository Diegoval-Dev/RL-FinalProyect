# CLAUDE.md — WAF Arena

Punto de entrada para cualquier agente (Claude Code u otro) y para cualquier integrante del equipo. Leer completo al iniciar cada sesión. Este archivo es corto a propósito: aquí está el mapa, el detalle vive en `docs/`.

## Qué es este proyecto

Proyecto final del curso de Reinforcement Learning (UVG). Un **defensor** (WAF) y un **atacante** de inyección SQL aprenden uno contra el otro en un laboratorio Docker aislado. La pregunta de investigación y las cinco RQ están en [docs/00-vision/vision.md](docs/00-vision/vision.md).

Alcance cerrado: **solo SQL injection contra PostgreSQL**. XSS es extensión y no se toca hasta cerrar la Fase 4 (ver [ADR-0001](docs/06-decisiones/adr-0001-solo-sqli.md)).

## El plan: relevo de 4 fases

El trabajo se divide en un **relevo secuencial**. Cada integrante depende exactamente una vez de otro: cuando recibe el entregable (tag + handoff) de la fase anterior. Después de eso, nadie espera a nadie. Detalle completo en [docs/03-plan/plan-maestro.md](docs/03-plan/plan-maestro.md).

| Fase | Dueño | Semanas | Recibe | Entrega | RQ |
|---|---|---|---|---|---|
| 1. Laboratorio, oráculo y entornos | Diego Valenzuela | 1–3 | nada | `v0.1-fase1` | base para todas |
| 2. Infraestructura experimental y atacante clásico | Daniel Dubón | 4–6 | `v0.1-fase1` | `v0.2-fase2` | RQ1 |
| 3. Deep RL: defensor DQN y atacante PPO | Joaquín Puente | 7–9 | `v0.2-fase2` | `v0.3-fase3` | RQ2, RQ5 (parcial) |
| 4. Planning, self-play, evaluación final y demo | Nelson García | 10–12 | `v0.3-fase3` | `v1.0` | RQ3, RQ4, RQ5 |

Documentos de cada fase:
- [Fase 1 — Diego](docs/03-plan/fase-1-diego-laboratorio.md)
- [Fase 2 — Daniel](docs/03-plan/fase-2-daniel-atacante-clasico.md)
- [Fase 3 — Joaquín](docs/03-plan/fase-3-joaquin-deep-rl.md)
- [Fase 4 — Nelson](docs/03-plan/fase-4-nelson-planning-selfplay.md)

**Fase activa:** 4 (actualizar esta línea en cada relevo).

## Cómo trabajar en una sesión (resumen)

Flujo completo en [docs/04-metodologia-ai-first/flujo-de-trabajo.md](docs/04-metodologia-ai-first/flujo-de-trabajo.md).

1. **Ubicar la tarea.** Toda sesión trabaja sobre un ID de tarea (`F<fase>-T<nn>`) definido en el documento de la fase activa. Sin ID, no hay código.
2. **Explorar sin editar.** Leer la tarea, los contratos que referencia y el código existente relacionado.
3. **Planificar.** Escribir el plan de la tarea (archivos a tocar, pruebas a escribir) y esperar aprobación humana.
4. **Pruebas primero.** Convertir los criterios de aceptación de la tarea en pruebas.
5. **Implementar** lo mínimo para pasar las pruebas, sin salir del alcance de la tarea.
6. **Verificar:** `make lint && make test` (y `make smoke` si la tarea toca entornos o laboratorio).
7. **Documentar:** marcar la tarea en la sección *Estado* de la fase, registrar experimentos en [docs/07-experimentos/registro.md](docs/07-experimentos/registro.md) y crear un ADR si se tomó una decisión de diseño.

## Reglas no negociables

Lista completa en [docs/04-metodologia-ai-first/reglas-para-agentes.md](docs/04-metodologia-ai-first/reglas-para-agentes.md).

1. **Los contratos mandan.** Las interfaces en [docs/02-contratos/](docs/02-contratos/README.md) son la frontera entre fases. Un cambio incompatible requiere ADR y subir la versión mayor del contrato.
2. **Ningún número sin run.** Toda cifra en el informe, en un handoff o en una respuesta del agente debe venir de un run registrado (`exp_id` + `run_id` + commit). Nunca inventar, estimar ni "redondear a ojo" resultados.
3. **Laboratorio aislado.** Nada apunta fuera de la red interna de Docker. Ningún payload, script ni agente se dirige a sistemas de terceros. Ver [ética y alcance](docs/00-vision/etica-y-alcance.md).
4. **Separación de datos.** Los splits de `data/splits/` se congelan en la Fase 1. Nunca se entrena con `test` ni con `test-hard`.
5. **Semillas y configuración.** Todo experimento corre desde un YAML en `configs/` con semillas explícitas. Nada de hiperparámetros escritos a mano en el código de entrenamiento.
6. **Comprensión humana.** No se hace merge de código que su autor humano no pueda explicar en la defensa del proyecto.
7. **Alcance de la tarea.** El agente no modifica archivos fuera de lo que la tarea declara. Si encuentra un problema ajeno, lo anota en la sección *Hallazgos* de la fase y sigue.

## Mapa del repositorio

Estructura completa y propósito de cada carpeta en [docs/01-arquitectura/repo-estructura.md](docs/01-arquitectura/repo-estructura.md).

```
wafarena/      paquete Python: envs, oráculo, mutaciones, features, agentes, self-play, evaluación
lab/           Docker Compose: vulnapp, PostgreSQL con canarios, ModSecurity PL1–PL4, proxy
data/          corpus de payloads, sesiones benignas, splits congelados
traffic/       generadores de tráfico benigno (Locust, Playwright)
configs/       YAML de experimentos
results/       salidas de runs (no versionado salvo resúmenes)
dashboard/     demo en Streamlit
report/        capítulos del informe final
docs/          documentación viva (fuente de verdad)
```

## Comandos

Los crea la tarea F1-T01. Hasta entonces no existen.

| Comando | Qué hace |
|---|---|
| `make setup` | Instala dependencias con `uv` |
| `make lab-up` / `make lab-down` | Levanta / apaga el laboratorio Docker |
| `make lint` | `ruff check` + `ruff format --check` |
| `make test` | Pruebas unitarias (no requieren laboratorio) |
| `make test-lab` | Pruebas de integración contra el laboratorio |
| `make smoke` | Prueba de humo de entornos: agentes aleatorios, 100 episodios |
| `make run CONFIG=configs/exp/<archivo>.yaml` | Ejecuta un experimento |

## Índice de documentación

[docs/README.md](docs/README.md)

## Convenciones rápidas

- Código, nombres de archivos de código y commits técnicos en inglés; documentación e informe en español.
- Commits: `tipo(ID): descripción` — por ejemplo `feat(F1-T04): oráculo con canarios`.
- Ramas: `f<fase>/<ID>-<slug>` — por ejemplo `f1/F1-T04-oraculo`.
- Detalle en [docs/04-metodologia-ai-first/convenciones.md](docs/04-metodologia-ai-first/convenciones.md).
