# Fase 4 — Planning, self-play, evaluación final y demo

| | |
|---|---|
| **Dueño** | Nelson García |
| **Semanas** | 10–12 |
| **Recibe** | Tag `v0.3-fase3` + [HANDOFF-3](../05-handoffs/handoff-3-joaquin-a-nelson.md) (única dependencia) |
| **Entrega** | Tag `v1.0`: proyecto completo |
| **Contratos que consume** | todos |
| **Experimentos** | EXP-H1, H2, H3, I1–I5, R1 ([catálogo](../07-experimentos/catalogo.md)) |
| **Responde** | RQ3, RQ4, RQ5 |

## Objetivo

Cerrar la carrera armamentista: un atacante que planifica con un modelo del defensor, un self-play que no colapse, la evaluación de generalización final, la validación en modo real, la demo y el informe integrado. Al terminar esta fase no queda trabajo pendiente.

## Diseño del atacante Dyna

En este problema las mutaciones son baratas (el atacante las hace localmente) y lo caro es `SEND`, porque consume presupuesto y acerca el ban. El modelo que aprende el atacante es, por lo tanto, un **modelo sustituto del defensor**: un clasificador que predice la clase de respuesta de un `SEND` a partir de la representación del payload.

- **Experiencia real:** cada `SEND` real actualiza Q y agrega `(features del payload, respuesta)` al conjunto del sustituto.
- **Planificación:** `n` pasos simulados por paso real, donde los `SEND` se resuelven con la predicción del sustituto y no gastan consultas.
- **Dyna-Q+:** bono `κ·√τ` por tiempo desde la última visita real de `(s, a)`, para re-verificar estrategias cuando el defensor cambia.
- **Prioritized Sweeping:** prioriza simular cerca de payloads donde el sustituto tiene menor confianza.

El riesgo de *model error* (planificar sobre un sustituto malo) se mide reportando la exactitud del sustituto en `val` junto con cada curva.

## Diseño del self-play

- **Inicialización:** defensor desde `DEF-REF-1`, atacante desde `ATK-REF-1`.
- **Generaciones:** G = 8 (ajustable por YAML). En cada generación el atacante entrena 3 iteraciones por cada 1 del defensor.
- **Pool de oponentes:** al terminar cada generación se guarda un checkpoint de cada agente. Cada entrenamiento usa el oponente actual con probabilidad 0.5 y uno histórico uniforme el resto.
- **Progreso real:** cada generación se evalúa contra referencias fijas (`modsec-pl1` … `pl4`, `corpus-replay`, `ATK-REF-0`, `DEF-REF-1`, `ATK-REF-1`). La recompensa de entrenamiento no se usa como indicador de progreso.
- **Campeón:** el defensor de self-play final es el de mejor TPR en `val` contra todo el pool histórico, sujeto a FPR ≤ FPR de `DEF-REF-1`.

## Tareas

### F4-T01 — Aceptación del relevo
- **Hacer:** checklist de aceptación de HANDOFF-3 en una máquina distinta a la de Joaquín.
- **Aceptación:** checklist firmado en la ventana de 1 día.

### F4-T02 — Modelo sustituto del defensor
- **Hacer:** `wafarena/agents/dyna/surrogate.py`: regresión logística multiclase sobre las 256 features de n-gramas, con opción de MLP pequeña; entrenamiento incremental.
- **Aceptación:** prueba con datos sintéticos separables; exactitud y calibración reportadas en `val` contra `modsec-pl1` y `DEF-REF-1`.

### F4-T03 — Dyna-Q (EXP-H1)
- **Requiere:** F4-T02.
- **Hacer:** Dyna-Q sobre el estado abstracto con el sustituto como modelo de `SEND`; `n` ∈ {0, 5, 20, 50} (n = 0 equivale a Q-learning).
- **Aceptación:** figura de ER en `val` contra **consultas reales acumuladas** para Dyna-Q, Q-learning (configuración de EXP-D1) y PPO (`ATK-REF-1`), contra `modsec-pl1` y contra `DEF-REF-1`, con 10 semillas para tabulares y 5 para PPO.

### F4-T04 — Dyna-Q+ y Prioritized Sweeping (EXP-H2, EXP-H3)
- **Requiere:** F4-T03.
- **Hacer:** EXP-H2: el defensor cambia de `modsec-pl1` a `DEF-REF-1` a mitad del entrenamiento; comparar Dyna-Q contra Dyna-Q+. EXP-H3 (recortable): Prioritized Sweeping.
- **Aceptación:** curva de ER con la línea vertical del cambio de defensor; tiempo de recuperación medido.

### F4-T05 — Orquestador de self-play
- **Hacer:** `wafarena/selfplay/` con generaciones, pool, asimetría de ritmo, checkpoints por generación en `checkpoints/selfplay/<run>/{atk,def}-gen-XX/` y evaluación automática contra referencias fijas al cerrar cada generación. Loop alterno sobre los entornos Gymnasium existentes; PettingZoo solo si simplifica.
- **Aceptación:** una corrida corta de 2 generaciones completa de punta a punta en la prueba de humo; reanudable desde la última generación si se interrumpe.

### F4-T06 — Self-play ingenuo contra pool (EXP-I1)
- **Requiere:** F4-T05.
- **Hacer:** dos configuraciones de 8 generaciones: alternancia ingenua (sin pool) y con pool.
- **Aceptación:** figura de TPR de cada generación de defensor contra `ATK-REF-0` y `ATK-REF-1` en ambas configuraciones, con 3 semillas como mínimo (el self-play es caro; justificar en el informe si no se llega a 5).

### F4-T07 — Matriz de cruces (EXP-I2)
- **Requiere:** F4-T06.
- **Hacer:** `wafarena/eval/crossplay.py`: evaluar cada generación de defensor contra cada generación de atacante (ER) en la configuración con pool; heatmap.
- **Aceptación:** matriz regenerable con `make crossplay RUN=...` desde los checkpoints; figura en `report/figuras/`.

### F4-T08 — Generalización final (EXP-I3, I4, I5)
- **Requiere:** F4-T06.
- **Hacer:** comparar el campeón de self-play con `DEF-REF-1` y ModSecurity en: `defender-eval-family-v1` (I3), `defender-eval-hard-v1` (I4) y contra atacantes que nunca participaron del self-play (I5): un PPO nuevo con semilla distinta entrenado contra `DEF-REF-1` y el mejor Dyna-Q de EXP-H1.
- **Aceptación:** tabla final de RQ5 con IC.

### F4-T09 — Validación en modo real (EXP-R1)
- **Hacer:** repetir en `backend: real` las evaluaciones finales de los agentes principales con suites reducidas (documentar el tamaño).
- **Aceptación:** tabla de GAP por métrica; el informe interpreta la brecha.

### F4-T10 — Dashboard y demo
- **Hacer:** `dashboard/` en Streamlit: tráfico en vivo en modo real con decisiones del defensor, comparación lado a lado con ModSecurity, matriz de cruces, curvas principales. Video corto de la carrera armamentista.
- **Aceptación:** `make demo` levanta laboratorio y dashboard; el dashboard no muestra ningún dato que no venga de un run o del laboratorio en vivo.

### F4-T11 — Informe integrado y entrega
- **Requiere:** todas.
- **Hacer:** `report/capitulos/06-planning-selfplay.md`, `07-generalizacion.md`, `09-conclusiones.md`; consolidar limitaciones de todas las fases; revisar que cada número del informe tenga su referencia de run; README de reproducción; prueba de `docker compose up` en una máquina limpia; tag `v1.0`.
- **Aceptación:** [DoD de proyecto](../04-metodologia-ai-first/definicion-de-terminado.md#proyecto) completo.

## Riesgos de esta fase

| Riesgo | Mitigación |
|---|---|
| Es la fase con más carga | El trabajo previo independiente (Dyna en juguete, esqueleto del dashboard) se adelanta antes de la semana 10; recortes en el orden del plan maestro |
| Self-play cíclico o colapsado | Pool, asimetría de ritmo y evaluación contra referencias fijas desde la primera generación |
| Self-play demasiado caro | Reducir G a 5 y pasos por generación; mantener la comparación ingenuo contra pool, que es lo que responde RQ3 |
| El sustituto es malo y Dyna planifica sobre una ilusión | Es un resultado de RQ4 si se mide; reportar exactitud del sustituto junto a cada curva |

## Estado

- [x] F4-T01 Aceptación del relevo (con salvedades documentadas en HANDOFF-3 §4)
- [x] F4-T02 Modelo sustituto
- [ ] F4-T03 Dyna-Q
- [ ] F4-T04 Dyna-Q+ y Prioritized Sweeping
- [ ] F4-T05 Orquestador de self-play
- [ ] F4-T06 Ingenuo contra pool
- [ ] F4-T07 Matriz de cruces
- [ ] F4-T08 Generalización final
- [ ] F4-T09 Validación en modo real
- [ ] F4-T10 Dashboard y demo
- [ ] F4-T11 Informe integrado y entrega

## Hallazgos

- **F4-T01 (2026-10-30, `12f17d5`):** se verificó el relevo de HANDOFF-3 en la máquina de Nelson. Pasaron setup, lint, 672 pruebas unitarias, 146 pruebas de laboratorio, splits, dos corridas de smoke idénticas al CSV versionado, la API pública de `Attacker-v0` en 10 episodios, dos corridas de `EXP-D1/qlearning-pl1` s0 con `eval.csv` idénticos, las dos referencias en 100 episodios, PPO s0, y la máscara de ABL-1/2. DQN s0 terminó en 308,051 s con caché caliente y reprodujo exactamente `final_eval.json`; el primer intento tuvo un timeout de ModSecurity y el siguiente tardó 1 166,106 s con caché fría. La figura de Pareto de EXP-F5 se regeneró idéntica.
- **F4-T01 (aceptado con salvedades el 2026-10-30):** `make summarize EXP=EXP-F5` y el heredado `make summarize EXP=EXP-A1` no pueden regenerar los CSV desde este checkout porque los runs crudos no están versionados. La ventana de 1 día hábil desde el tag ya pasó. Nelson autorizó aceptar estas excepciones; HANDOFF-3 §4 conserva los ítems sin marcar y la evidencia de los demás checks. Se firmó la aceptación y se cambió la fase activa en `CLAUDE.md`.
- **F4-T02 (2026-10-31, `F4-T02__surrogate-validation__s0__0b2a96c`, seed 0):** la regresión logística multiclase y la MLP de 32 unidades superaron la prueba sintética separable. En `val`, contra `modsec-pl1` ambas alcanzaron exactitud 1,0000 (797/797 respuestas `BLOCKED`); ECE = 0,00239 y 0,00074, Brier = 0,00000828 y 0,00000074, respectivamente. Contra `DEF-REF-1`, ambas alcanzaron exactitud 0,9382 (759/809), igual a la línea base de predecir siempre la clase mayoritaria; ECE = 0,02609 y 0,03429, Brier = 0,11520 y 0,11695. En los cuatro casos todas las predicciones fueron `BLOCKED`: la exactitud alta no demuestra que el sustituto distinga las respuestas minoritarias. El clasificador solo observa los 256 n-gramas del payload y no el estado de sesión; en `DEF-REF-1`, `PASS_EFFECT` apareció 4 veces en `val` y ninguna en `train`. Antes de usarlo para planificar en F4-T03, medir el error por clase y considerar una recolección que cubra respuestas minoritarias. Datos y conteos: `results/summary/F4-T02_surrogate.csv` (run crudo en `results/_f4t02_final_0b2a96c/F4-T02/surrogate-validation/s0`); configuración: `configs/surrogate/f4_t02.yaml`. Una sola semilla diagnóstica, sin IC.
