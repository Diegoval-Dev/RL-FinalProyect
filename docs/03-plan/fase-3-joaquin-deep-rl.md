# Fase 3 — Deep RL: defensor DQN y atacante PPO

| | |
|---|---|
| **Dueño** | Joaquín Puente |
| **Semanas** | 7–9 |
| **Recibe** | Tag `v0.2-fase2` + [HANDOFF-2](../05-handoffs/handoff-2-daniel-a-joaquin.md) (única dependencia) |
| **Entrega** | Tag `v0.3-fase3` + [HANDOFF-3](../05-handoffs/handoff-3-joaquin-a-nelson.md) |
| **Contratos que consume** | [env-defensor](../02-contratos/env-defensor.md), [env-atacante](../02-contratos/env-atacante.md), [features](../02-contratos/features.md), [agentes](../02-contratos/agentes-y-checkpoints.md), [métricas](../02-contratos/metricas.md), [experimentos](../02-contratos/experimentos.md) |
| **Experimentos** | EXP-E1, E2, F1–F7, G1–G4, ABL-1, ABL-2 ([catálogo](../07-experimentos/catalogo.md)) |
| **Responde** | RQ2 y la parte de RQ5 sobre el defensor entrenado contra oponentes fijos |

## Objetivo

Entrenar un defensor neuronal que compita con ModSecurity en la frontera detección/falsos positivos y un atacante de policy gradient más fuerte que los tabulares. Publicar `DEF-REF-1` y `ATK-REF-1`, que serán el punto de partida del self-play.

## Oponente de entrenamiento del defensor

Salvo que el experimento diga otra cosa, el defensor entrena contra `{"type": "pool", "paths": [corpus-replay, random-mutation, ATK-REF-0], "weights": [1/3, 1/3, 1/3]}` con `attack_ratio = 0.1`.

## Regla de selección de `DEF-REF-1`

Entre todos los defensores entrenados en F3-T05, el de mayor TPR en `val` sujeto a FPR en `val` ≤ FPR de `modsec-pl2` en `val`. Si ninguno cumple, el de menor FPR, y se documenta. La regla se fija antes de mirar resultados de `test`.

## Tareas

### F3-T01 — Aceptación del relevo
- **Hacer:** checklist de aceptación de HANDOFF-2 en una máquina distinta a la de Daniel.
- **Aceptación:** checklist firmado en la ventana de 1 día.

### F3-T02 — Defensor lineal (EXP-E1, EXP-E2)
- **Hacer:** Q-learning y SARSA semi-gradiente con aproximación lineal sobre las 37 features. EXP-E2 opcional: configuración off-policy con bootstrapping que muestre divergencia (triada mortal).
- **Aceptación:** EXP-E1 registrado con 5 semillas en `defender-eval-v1`; si se hace E2, figura de la norma de los pesos contra pasos.

### F3-T03 — DQN base (EXP-F1)
- **Hacer:** DQN estilo CleanRL (un archivo legible) adaptado a la interfaz `Agent`; red MLP; replay buffer; red objetivo.
- **Aceptación:** pasa una prueba de cordura en `CartPole-v1` (umbral documentado en la tarea); EXP-F1 registrado con 5 semillas.

### F3-T04 — Ablación incremental de DQN (EXP-F2, F3, F4)
- **Requiere:** F3-T03.
- **Hacer:** agregar una mejora a la vez: Double → Double + Dueling → Double + Dueling + PER. Cada variante activable por YAML.
- **Aceptación:** los cuatro runs con 5 semillas y mismos hiperparámetros compartidos; tabla de TPR, FPR, FPR-h y F1 con IC; además, para PER, la proporción de muestras del buffer que corresponden a ataques que pasaron.

### F3-T05 — Frontera de Pareto contra ModSecurity (EXP-F5)
- **Requiere:** F3-T04.
- **Hacer:** con la mejor variante, barrer α ∈ {1, 2, 4, 8, 16} manteniendo β = α/4 y γ = α/8; evaluar en `defender-eval-v1`; graficar (FPR, TPR) de cada α junto a `modsec-pl1` … `pl4`.
- **Aceptación:** figura generada por script desde `results/summary/EXP-F5.csv`; texto del informe dice qué puntos de ModSecurity quedan dominados y cuáles no, con IC.

### F3-T06 — Ablaciones del defensor (ABL-1, ABL-2)
- **Requiere:** F3-T05.
- **Hacer:** con el α elegido para `DEF-REF-1`, entrenar sin scores de ModSecurity (ABL-1) y sin features de sesión ni ventana (ABL-2). Se implementa como máscara de observación configurable por YAML, sin cambiar el contrato del entorno.
- **Aceptación:** runs con 5 semillas; tabla comparativa con la configuración completa.

### F3-T07 — Generalización del defensor estático (EXP-F6, EXP-F7)
- **Requiere:** F3-T05.
- **Hacer:** evaluar `DEF-REF-1` candidato en `defender-eval-family-v1` (familias no vistas) y `defender-eval-hard-v1` (benignos difíciles no vistos), junto a ModSecurity PL1–PL4.
- **Aceptación:** tabla con TPR y FPR por suite. Esta es la línea base contra la que la Fase 4 compara al defensor de self-play.

### F3-T08 — Atacante policy gradient (EXP-G1, G2, G3)
- **Hacer:** REINFORCE con línea base, A2C y PPO con GAE estilo CleanRL, sobre la observación de 288 dimensiones; entrenar contra `modsec-pl1` y contra el candidato a `DEF-REF-1`.
- **Aceptación:** runs con 5 semillas; ER, QFE y DIV en `attacker-eval-v1`; comparación con `ATK-REF-0`.

### F3-T09 — Bono de entropía (EXP-G4)
- **Requiere:** F3-T08.
- **Hacer:** PPO con coeficiente de entropía ∈ {0, 0.01, 0.05}.
- **Aceptación:** figura de DIV contra ER; el informe discute si un atacante más estocástico es más difícil de bloquear, evaluándolo contra `DEF-REF-1`.

### F3-T10 — Latencia del defensor
- **Requiere:** F3-T05.
- **Hacer:** medir LAT de `DEF-REF-1` en modo real con 2 000 requests.
- **Aceptación:** p50 y p95 en `results/summary/latency.csv`.

### F3-T11 — Publicar `DEF-REF-1` y `ATK-REF-1`
- **Requiere:** F3-T05, F3-T08.
- **Hacer:** aplicar la regla de selección; copiar a `checkpoints/refs/`; `ATK-REF-1` es el mejor PPO por ER en `val` contra `DEF-REF-1`.
- **Aceptación:** ambos cargan con `load_checkpoint`; ambos funcionan como oponentes vía `DefenderDriver` y `AttackerDriver` en 100 episodios.

### F3-T12 — Capítulo del informe y handoff
- **Hacer:** `report/capitulos/05-deep-rl.md` (RQ2 y generalización del defensor estático); completar HANDOFF-3; crear el tag.
- **Aceptación:** checklist de [DoD de fase](../04-metodologia-ai-first/definicion-de-terminado.md#fase) completo.

## Riesgos de esta fase

| Riesgo | Mitigación |
|---|---|
| El defensor aprende a bloquear todo | Vigilar FPR desde la primera evaluación; si FPR > 0.5 en `val`, subir α antes de seguir |
| El defensor aprende a permitir todo porque los ataques son raros | PER, y como diagnóstico subir `attack_ratio` a 0.3 solo para depurar, nunca en el resultado final |
| DQN inestable | Normalización de recompensas documentada en el YAML, recorte de gradiente, revisar con el prompt de depuración de [prompts.md](../04-metodologia-ai-first/prompts.md#p9--depurar-un-entrenamiento-que-no-aprende) |
| PPO lento | Entornos vectorizados de Gymnasium en modo rápido |

## Estado

- [ ] F3-T01 Aceptación del relevo
- [ ] F3-T02 Defensor lineal
- [ ] F3-T03 DQN base
- [ ] F3-T04 Ablación DQN
- [ ] F3-T05 Pareto contra ModSecurity
- [ ] F3-T06 Ablaciones del defensor
- [ ] F3-T07 Generalización del defensor estático
- [ ] F3-T08 Atacante policy gradient
- [ ] F3-T09 Bono de entropía
- [ ] F3-T10 Latencia
- [ ] F3-T11 `DEF-REF-1` y `ATK-REF-1`
- [ ] F3-T12 Informe y handoff

## Hallazgos

_(vacío)_
