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

- [x] F3-T01 Aceptación del relevo
- [x] F3-T02 Defensor lineal
- [x] F3-T03 DQN base
- [x] F3-T04 Ablación DQN
- [x] F3-T05 Pareto contra ModSecurity
- [x] F3-T06 Ablaciones del defensor
- [x] F3-T07 Generalización del defensor estático
- [x] F3-T08 Atacante policy gradient
- [x] F3-T09 Bono de entropía
- [x] F3-T10 Latencia
- [x] F3-T11 `DEF-REF-1` y `ATK-REF-1`
- [ ] F3-T12 Informe y handoff

## Hallazgos

- **F3-T01 (verificación):** checklist de HANDOFF-2 §4 y el heredado de HANDOFF-1 corridos en una máquina distinta a la de Daniel sobre `ae99905` (= `v0.2-fase2`): todos pasan. `make test` 583 pruebas, `make test-lab` 12 + 134; hashes de `verify-splits` iguales a HANDOFF-1 §9; dos `make smoke` idénticos al versionado; `EXP-D1/qlearning-pl1` semilla 0 corrido dos veces con `eval.csv`, `train.csv` y `final_eval.json` idénticos byte a byte; `ATK-REF-0` cargado y 100 sesiones de ataque en `Defender-v0` sin errores.
- **F3-T01 (hallazgo):** el ítem «`make summarize EXP=EXP-A1` regenera `EXP-A1.csv` idéntico» no se puede cumplir en otra máquina: `results/EXP-A1/` no se versiona y la columna `git_shas` del resumen depende del commit con que se corrió. Se verificó re-corriendo los 70 runs de EXP-A1: idéntico celda por celda salvo `git_shas`. Sugerencia para la plantilla de handoff (no se toca en esta tarea): redactar este tipo de ítem como «re-correr y resumir da las mismas métricas, ignorando `git_shas`».
- **F3-T01 (hallazgo, para F3-T02 en adelante):** `DefenderEnv` resuelve `attacker` solo como nombre o dict (`wafarena/envs/defender_env.py`, `_resolve_attacker_factory`); un objeto `AttackerPolicy` falla con `AttributeError`. `AttackerEnv` sí acepta objetos como `defender`. El contrato env-defensor 1.1 tampoco documenta objetos, así que no es una violación del contrato, pero conviene tenerlo presente al implementar `DefenderDriver` y al armar oponentes en memoria.
- **F3-T02 (infraestructura):** el runner no corría `Defender-v0` y `{"type": "pool"}` lanzaba `NotImplementedError`; ambos se implementaron aquí porque todas las tareas del defensor los necesitan. Se agregó la suite `defender-val-v1` (split `val`), sin la cual la regla de selección de `DEF-REF-1` («TPR en `val` sujeto a FPR en `val` ≤ FPR de `modsec-pl2` en `val`») no se podía aplicar. El runner usa esa misma regla para elegir el checkpoint de cada run y mide el tope (`fpr_cap`) con `ModSecDefender(2)` al empezar. Contratos: env-defensor 1.2, métricas 1.3, experimentos 1.2.
- **F3-T02 (hallazgo que condiciona la fase):** `fpr_cap` = 0,0: `modsec-pl2` no tiene ningún falso positivo en las sesiones benignas de `val`. La regla de `DEF-REF-1` exige entonces FPR = 0 exacto en `val`. Ninguno de los 50 puntos de evaluación de EXP-E1 (2 métodos × 5 semillas × 10 evaluaciones) la cumple; en EXP-E2, 2 de las 3 semillas de `sarsa-onpolicy` sí llegan a puntos factibles (FPR = 0 con TPR 0,99–1,0 en `val`).
- **F3-T02 (bug corregido, heredado):** `ModSecCache.flush` reescribía el JSON de la caché en su lugar; un proceso que arrancara mientras otro escribía podía leer un archivo truncado. Ahora escribe a un temporal y hace `os.replace` atómico. Varios runs en paralelo siguen pudiendo perder entradas nuevas (gana el último en escribir), lo que solo cuesta recalcular, nunca un score equivocado.
- **F3-T02 (decisión de método):** `runmeta.build_meta` revisa el árbol de git en cada semilla, así que editar `wafarena/` o `configs/` mientras corre un experimento marcaría las semillas siguientes como `dirty`. El desarrollo de las tareas siguientes se hizo en un *worktree* aparte mientras corrían los experimentos.
- **F3-T02 (resultado):** EXP-E1, 5 semillas, `defender-eval-v1`: Q-learning lineal TPR = 0,955 [0,895; 0,991], FPR = 0,016 [0,011; 0,019]; SARSA lineal TPR = 0,950 [0,879; 0,991], FPR = 0,022 [0,016; 0,028]. EXP-E2, 3 semillas: con datos off-policy de una política uniforme, la norma de los pesos de Q-learning lineal crece sin estabilizarse (232–309 a los 100 000 pasos) y el error TD medio sube a 8,5–11,8, mientras que SARSA on-policy con el mismo α y γ se estabiliza (‖w‖ ≈ 50, |δ| ≈ 1,1). Es crecimiento sostenido dentro del presupuesto, no un desborde a infinito. Registrado en `registro.md`; figura `report/figuras/EXP-E2_weight_norm.png`.
- **F3-T03 (umbral de la prueba de cordura):** CartPole-v1, 60 000 pasos, 3 semillas por variante (base, + Double, + Dueling, + PER), mismos hiperparámetros para todas (`scripts/dqn_cartpole_sanity.py`, `make dqn-sanity`). Cada 5 000 pasos la política voraz juega 10 episodios de selección y se guarda el mejor *snapshot*; ese *snapshot* se confirma en 20 episodios con otras semillas, que no participan en la selección. Aprueba si la confirmación da un retorno medio ≥ 195 (el umbral clásico de «resuelto»). Es el mismo protocolo del runner: seleccionar en `val` y reportar en otro conjunto. Resultado: 12/12 aprueban.
- **F3-T03 (criterio descartado, con su resultado):** el primer criterio, la política final tras 60 000 pasos con umbral 195, aprobó 6 de 12 con el mismo código e hiperparámetros (base 302,7 / 92,7 / 100,0; Double 41,1 / 491,5 / 500,0; Dueling 18,95 / 54,7 / 61,2; PER 197,95 / 222,3 / 262,1). La curva de Dueling semilla 0 muestra la causa: llega a 314 a los 15 000 pasos y colapsa a 19,5 al final. DQN en CartPole aprende y luego oscila, así que ese criterio mide la estabilidad del final del entrenamiento, no si la implementación aprende. No se cambió ningún hiperparámetro para pasar la prueba.
- **F3-T03 (EXP-F1):** EXP-F1 se corrió junto con EXP-F2..F4 (mismos hiperparámetros compartidos, commit `1517d8f`) y está registrado con ellos en el PR de F3-T04.
- **F3-T03 (decisión):** PyTorch se resuelve desde el índice oficial solo CPU (ADR-0009). La imagen `runner` pasa a ~2,9 GB.
- **F3-T04 (resultado):** EXP-F1..F4, 5 semillas cada uno, mismos hiperparámetros compartidos (α = 4, 150 000 pasos), commit `1517d8f`. En `defender-eval-v1`: base TPR = 0.9970 [0.9943; 0.9998]; + Double 0.9955 [0.9925; 0.9986]; + Dueling 0.9984 [0.9967; 0.9994]; + PER 0.9828 [0.9740; 0.9917]; FPR = 0 en las cuatro salvo F3 (0.0002 [0.0000; 0.0005]). Tabla completa y diferencias con IC en `results/summary/EXP-F_ablation.csv` y `EXP-F_ablation_diffs.csv`; figura `report/figuras/EXP-F_ablation.png`.
- **F3-T04 (hipótesis del catálogo):** ninguna se confirma. Double no reduce de forma detectable la Q de `ALLOW` en ataques (diferencia −0,041 [−0,288; 0,195]); Dueling no cambia TPR de forma detectable (+0,003 [−0,0004; 0,006]); PER sí cumple su mecanismo, porque la fracción del batch con ataques que pasaron sube de 0.0055 [0.0053; 0.0058] a 0.0281 [0.0257; 0.0303], pero **baja** el TPR (−0,016 [−0,025; −0,007]) y el F1 (−0,007 [−0,012; −0,003]). Con TPR ≈ 0,99 sin PER, casi no quedan ataques que se escapen; repetir de más esos pocos casos no ayuda.
- **F3-T04 (decisión):** EXP-F5 usa Double + Dueling (EXP-F3): es la variante con mayor TPR en `val` bajo la regla de `DEF-REF-1` (TPR medio en `val` = 0,99929; las 5 semillas con FPR = 0). Se eligió en `val`; `test` no participó.
- **F3-T05 (resultado):** EXP-F5, Double + Dueling, α ∈ {1, 2, 4, 8, 16} con β = α/4 y γ = α/8, 5 semillas cada uno, commit `d9d7d49`. En `defender-eval-v1` el TPR va de 0.9809 [0.9741; 0.9896] (α = 1) a 0.9987 [0.9979; 0.9994] (α = 16), con FPR ≤ 0.0015 en todos. ModSecurity (determinista): PL1 TPR = 0.7150, PL2 0.9725, ambos con FPR = 0; PL3 y PL4 TPR = 1,0000 con FPR = 0.3327 y 0.3844.
- **F3-T05 (dominancia, con IC):** criterio conservador de `report/figuras/make_EXP-F5.py`: un α domina a un PL solo si todo su IC de TPR queda en o sobre el TPR del PL y todo su IC de FPR en o bajo el FPR del PL, con al menos una desigualdad estricta. **PL1 y PL2 quedan dominados** por alpha-8 alpha-16 (mismo FPR = 0 y TPR mayor en todo el IC). **PL3 y PL4 no quedan dominados**: detectan el 100 % de los ataques y ningún α llega a TPR = 1 en todo su IC, aunque pagan FPR de 0,33–0,38 (`results/summary/EXP-F5_dominance.csv`). El barrido no produce el compromiso que se buscaba: el FPR ya es ≈ 0 desde α = 1 y el TPR no es monótono en α (α = 4 queda sobre α = 8, con IC que se solapan). La frontera del DQN es casi un punto en FPR ≈ 0, no una curva.
- **F3-T05 (decisión, ADR-0010):** la regla de `DEF-REF-1` deja 7 checkpoints empatados con TPR = 1,0 y FPR = 0,0 en `val`. Se desempata solo con `val` (menor FPR, mayor F1, mayor TPR medio en `val` de su α, menor semilla): `DEF-REF-1` = EXP-F5 `alpha-4` s0, publicado en `checkpoints/refs/DEF-REF-1/` por `scripts/select_def_ref.py`. Esta parte de F3-T11 se adelantó porque F3-T07 y F3-T08 necesitan el candidato como checkpoint versionado; F3-T11 verifica su uso como oponente.
- **F3-T05 (hallazgo, para leer los resultados del defensor):** el defensor ve los scores de ModSecurity PL1–PL4 como features (índices 12–15, ADR-0003). Que domine a PL2 no significa que haya aprendido algo que ModSecurity no ve. ABL-1 (F3-T06) mide cuánto depende de esos scores.
- **F3-T06 (resultado):** la configuración de `DEF-REF-1` (EXP-F5 `alpha-4`) con máscara de observación, 5 semillas, commit `3170401`, `defender-eval-v1` (`results/summary/ABL_comparison.csv`). Completa: TPR = 0.9984 [0.9967; 0.9994], F1 = 0.9987 [0.9976; 0.9997]. **ABL-1, sin scores de ModSecurity:** TPR = 0.9982 [0.9974; 0.9991], diferencia -0.0002 [-0.0017; +0.0017], sin diferencia detectable. **ABL-2, sin sesión ni ventana:** TPR = 1.0000 [1.0000; 1.0000], diferencia +0.0016 [+0.0006; +0.0033], **mejor de forma detectable**, aunque la mejora es pequeña.
- **F3-T06 (lectura):** el DQN no depende de los scores de ModSecurity. Las 12 features del request bastan para separar los ataques de este corpus del tráfico benigno, así que dominar a `modsec-pl2` (F3-T05) no es copiar un nivel de paranoia. Que quitar la sesión y la ventana no empeore, e incluso mejore un poco, indica que en estas suites cada request se decide por sí mismo: la historia de la sesión no aporta. Esto contradice la motivación del defensor híbrido (ADR-0003) solo en lo que miden estas suites; no se cambia el ADR.
- **F3-T07 (infraestructura):** EXP-F6 y EXP-F7 no entrenan: vuelven a evaluar checkpoints ya entrenados. Para eso se agregó `wafarena.evaluate` (`make evaluate`), con YAML propio en `configs/exp/` y la misma salida que el runner (`meta.yaml` con `source_run_id`, `final_eval.json`), así que `make summarize` funciona igual (contrato de experimentos 1.3).
- **F3-T07 (resultado, línea base para la Fase 4):** las 5 semillas de la configuración de `DEF-REF-1` (EXP-F5 `alpha-4`; s0 es `DEF-REF-1`), commit `3170401` (`results/summary/EXP-F6F7_generalization.csv`). **Familias no vistas (EXP-F6):** TPR = 1.0000 [1.0000; 1.0000], FPR = 0.0002 [0.0000; 0.0005]; el defensor generaliza. **Benignos difíciles no vistos (EXP-F7):** TPR = 0.9997 [0.9992; 1.0000], **FPR = 0.3385 [0.2775; 0.3996]**, cambio de FPR respecto a `defender-eval-v1` +0.338 [+0.277; +0.399]; el defensor no generaliza. Queda peor que PL1 y PL2 (FPR = 0) y mejor que PL3 (0,51) y PL4 (1,00). La mayoría de esos falsos positivos son acciones blandas: FPR-h = 0.0583 [0.0000; 0.1333].
- **F3-T07 (cuidado al leer el TPR agregado):** `defender-eval-family-v1` y `defender-eval-hard-v1` usan solo los atacantes con guion, sin `ATK-REF-0`, así que su TPR agregado no se compara directamente con el de `defender-eval-v1`; ModSecurity PL1, por ejemplo, «sube» solo por esa mezcla. Atacante por atacante, el TPR del DQN es 1,0 en las tres suites.
- **F3-T08 (infraestructura):** `wafarena/agents/pg.py` (REINFORCE con línea base, A2C y PPO con GAE en un archivo, compartiendo buffer y GAE); `DefenderDriver` en `wafarena/defenders/driver.py`; `Attacker-v0` acepta `defender={"type": "checkpoint"}` (ruta o id de referencia) y le pasa al defensor las features de sesión y ventana del episodio, que antes iban en cero. Se borró `wafarena/envs/drivers.py`, un borrador de la Fase 1 que nadie importaba y cuyo `AttackerDriver` no coincidía con el real. Contratos: env-atacante 1.1, agentes-y-checkpoints 1.1.
- **F3-T08 (bug propio, corregido):** el *flush* atómico de la caché de F3-T02 nombraba el temporal con `os.getpid()`, pero dentro de cada contenedor del laboratorio el PID es siempre 1. Con varios runs en paralelo todos escribían en el mismo temporal: un run se caía al renombrar y la caché quedaba un momento con contenido entrelazado, así que los runs que arrancaban justo entonces no podían cargarla. Corregido con `tempfile.mkstemp` (`98aa1a3`); la prueba nueva reproduce la falla con el código viejo. Los runs que habían terminado siguen siendo válidos (una lectura mala hace caer el proceso, no produce un score equivocado). Los runs G a medias se borraron y se repitieron completos.
- **F3-T08 (problema de entorno, mitigado, para la Fase 4):** a mitad de la campaña el disco de la máquina se llenó (251 GB, 100 %). Los *audit logs* de ModSecurity del laboratorio nunca se rotan y ya ocupaban 24 GB (`pl1.json` … `pl4.json`: 2,3 / 5,7 / 7,6 / 8,9 GB). Sin espacio, ModSecurity dejó de escribir y todas las consultas fallaban por *timeout* del *audit log*: 25 de 31 runs G cayeron así. Se truncaron los cuatro logs sin ningún run corriendo (el lector siempre empieza al final del archivo y el historial no se usa) y los 39 runs G pendientes se repitieron con 8 en paralelo en vez de 12, sin fallas. **Pendiente fuera de esta fase:** rotar esos logs en el laboratorio (es código de la Fase 1). El *self-play* de la Fase 4 genera todavía más consultas.
- **F3-T08 (resultado):** 5 semillas por método y defensor, 200 000 pasos, commit `98aa1a3`, `attacker-eval-v1`. **Contra `modsec-pl1` ningún método evade** (ER = 0,000 en REINFORCE, A2C y PPO), igual que los atacantes tabulares de la Fase 2. **Contra `DEF-REF-1`:** REINFORCE ER = 0.0040 [0.0020; 0.0050], PPO 0.0010 [0.0000; 0.0030], A2C 0.0000 [0.0000; 0.0000]. `ATK-REF-0` tiene ER = 0,000 contra los dos defensores (`results/summary/ATK-REF-0_eval.csv`), así que REINFORCE contra `DEF-REF-1` supera a `ATK-REF-0`, porque su IC excluye el 0, aunque por muy poco: menos de 1 episodio de 200 por semilla. DIV queda indefinida en todas las configuraciones: ninguna semilla tiene dos payloads exitosos distintos.
- **F3-T08 (hallazgo, para la Fase 4):** todas las evasiones contra `DEF-REF-1` caen en la consulta 10 (QFE = 10 en todas las semillas con evasión). El diagnóstico exploratorio `scripts/diag_defref1_session.py` muestra que la política del DQN cambia con la longitud de la sesión justo ahí: frente al mismo payload sin mutar bloquea las consultas 1–9 y desde la 10 pasa a `HONEYPOT` (`results/summary/DEF-REF-1_session_diag.csv`). Una explicación posible, **no verificada:** en `Defender-v0` los atacantes del *pool* abandonan tras 10 bloqueos, así que el DQN casi no vio sesiones de ataque más largas y en ese punto de transición algunos payloads mutados reciben `ALLOW`. Es el tipo de punto ciego que el *self-play* debería encontrar y cerrar.
- **F3-T09 (resultado):** PPO contra `DEF-REF-1` con coeficiente de entropía ∈ {0; 0,01; 0,05}, 5 semillas, commit `98aa1a3`. El bono sí hace más estocástico al atacante: la entropía de la política al final del entrenamiento es 0.33 [0.18; 0.49] con 0, 0.68 [0.48; 0.89] con 0,01 y 2.19 [2.13; 2.26] con 0,05 (el máximo es ln 17 ≈ 2,83). El ER contra `DEF-REF-1` es 0.0010 [0.0000; 0.0030], 0.0010 [0.0000; 0.0030] y 0.0000 [0.0000; 0.0000]: los IC se solapan, así que no hay diferencia detectable. **DIV queda indefinida en las tres configuraciones:** ninguna semilla tiene dos payloads exitosos distintos, así que la figura «DIV contra ER» (`report/figuras/EXP-G4_div_er.png`) lo dice en vez de dibujar un valor, y muestra la entropía de la política como medida directa de qué tan estocástico es el atacante (`results/summary/EXP-G4_entropy.csv`).
- **F3-T09 (respuesta a la pregunta de la tarea):** con estos datos no se puede afirmar que un atacante más estocástico sea más difícil de bloquear. El más estocástico (0,05) no evadió nunca, y los otros dos evadieron en 1 de 1 000 episodios. Con tan pocas evasiones la pregunta no se puede responder en este espacio de ataque. La hipótesis del catálogo no se confirma ni se refuta.
- **F3-T09 (control de determinismo):** `ppo-ent-001` (EXP-G4) es la misma configuración que `ppo-defref1` (EXP-G3) y dio exactamente los mismos números en las 5 semillas.
- **F3-T10 (infraestructura):** el *entrypoint* del proxy sirve un checkpoint de defensor si `PROXY_DEFENDER_CHECKPOINT` está definido (ruta o id de referencia, vía `DefenderDriver`); si no, sigue con `ModSecDefender`. El servicio `proxy-learned` (perfil `tools`) usa la imagen `runner`, porque cargar un checkpoint importa todo el paquete `wafarena`, y sirve `DEF-REF-1`. `make latency` lo levanta y corre `scripts/defender_latency.py`.
- **F3-T10 (resultado):** 2 000 requests del tráfico de `defender-eval-v1`, cada uno enviado a `modsec-pl2` solo y a `proxy-learned` en orden alternado, con la máquina sin otra carga, commit `8e5e595`. **LAT de `DEF-REF-1`: p50 = 65.6 ms, p95 = 74.3 ms** sobre ModSecurity solo, que tarda p50 = 15.9 ms, p95 = 17.9 ms; el proxy con `DEF-REF-1` tarda p50 = 81.7 ms, p95 = 90.3 ms. La decisión del DQN por sí sola cuesta p50 = 0.034 ms (`results/summary/latency.csv`).
- **F3-T10 (lectura):** casi toda la latencia agregada es del proxy y no del DQN. El proxy consulta ModSecurity PL1–PL4 **en secuencia** para armar las features 12–15 (≈ 4 veces lo que tarda una consulta sola) antes de decidir. ABL-1 (F3-T06) muestra que el DQN no necesita esos scores, así que un defensor sin ellos, o un proxy que consulte los cuatro niveles en paralelo, bajaría la latencia casi a la de ModSecurity solo. No se cambió el proxy en esta fase.
- **F3-T10 (nota):** algunos benignos con apóstrofo (`O'Brien`, `l'Hôpital`) reciben 500 a través del proxy. Es la respuesta de vulnapp, que es vulnerable a propósito y rompe su consulta con la comilla: el mismo 500 sale directo a vulnapp y a través de `modsec-pl2`, y el proxy no registró ningún *traceback*.
- **F3-T11 (resultado):** `DEF-REF-1` = EXP-F5 `alpha-4` s0, publicado en F3-T05 (ADR-0010). `ATK-REF-1` = EXP-G3 `ppo-defref1` s1: el mejor PPO por ER en `val` contra `DEF-REF-1` (0,005), empatado con s2 y s3 y desempatado por menor QFE-c y luego menor semilla (`scripts/select_atk_ref.py`, `results/summary/ATK-REF-1_selection.csv`). Las dos referencias cargan con `load_checkpoint` y funcionan como oponentes en 100 episodios (`make check-refs`, `results/summary/refs_check.csv`). `DEF-REF-1` vía `DefenderDriver` en `Attacker-v0` juzgó 839 requests de un atacante aleatorio y bloqueó todos. `ATK-REF-1` vía `AttackerDriver` en `Defender-v0` generó 289 requests de ataque en 100 sesiones.
- **F3-T11 (advertencia para la Fase 4):** `ATK-REF-1` es un atacante débil en términos absolutos (ER 0,005 en `val`, 0,0 en `test` para esa semilla). Es «el mejor PPO contra `DEF-REF-1`», como pide el plan, pero el *self-play* arranca de un atacante que casi no evade.
