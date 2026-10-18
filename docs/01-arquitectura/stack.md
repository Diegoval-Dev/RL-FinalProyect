# Stack técnico

Las versiones exactas se fijan en `pyproject.toml`, `uv.lock` y `lab/docker-compose.yml` durante F1-T01 y F1-T02. Esta tabla dice qué se usa y para qué.

| Área | Herramienta | Uso |
|---|---|---|
| Lenguaje | Python 3.11 | Todo el proyecto, incluido el laboratorio |
| Dependencias | `uv` | Entorno y lockfile reproducible |
| Entornos RL | Gymnasium | Entornos de atacante y defensor |
| Multiagente | PettingZoo (opcional) | Solo si el orquestador de F4 lo necesita; si no, loop alterno sobre Gymnasium |
| Cómputo numérico | NumPy | Bandits y tabulares (implementados por el equipo, sin librerías de RL) |
| Deep RL | PyTorch + código estilo CleanRL | DQN y PPO en archivos únicos legibles y modificables ([ADR-0006](../06-decisiones/adr-0006-cleanrl-y-tabulares-propios.md)) |
| Baselines rápidos | Stable-Baselines3 | Solo para comparar contra la implementación propia, nunca como resultado principal |
| App objetivo | FastAPI + psycopg | `vulnapp`, proxy y honeypot |
| Base de datos | PostgreSQL 16 | Datos, canarios, log de queries |
| WAF de referencia | ModSecurity v3 + OWASP CRS (imagen `owasp/modsecurity-crs:nginx`) | Cuatro instancias, PL1–PL4 |
| Tráfico benigno | Locust, Playwright | Sesiones realistas grabadas a JSONL |
| Pruebas | pytest, hypothesis | Unitarias, property-based para operadores, integración contra laboratorio |
| Calidad | ruff | Lint y formato |
| CI | GitHub Actions | `make lint` y `make test` en cada PR |
| Seguimiento | TensorBoard + CSV (por defecto), Weights & Biases (opcional) | Curvas de entrenamiento y evaluación |
| Figuras | matplotlib | Generadas por scripts en `report/figuras/` |
| Demo | Streamlit | Dashboard de la Fase 4 |
| Agente de código | Claude Code | Con `CLAUDE.md` y la metodología de [04-metodologia-ai-first](../04-metodologia-ai-first/flujo-de-trabajo.md) |

## Hardware

El entrenamiento debe correr en una laptop con CPU. La GPU es opcional y solo acelera DQN y PPO. Si una configuración no termina en menos de 2 horas en CPU, se reduce antes de pedir más recursos.
