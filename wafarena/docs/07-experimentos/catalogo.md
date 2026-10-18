# Catálogo de experimentos

El runner rechaza cualquier `exp_id` que no esté aquí. Para agregar un experimento: nueva fila en la tabla resumen y una ficha, en un PR del dueño de la fase activa.

## Resumen

| ID | Fase | Dueño | Semana del curso | RQ | Qué compara | Semillas | Recortable |
|---|---|---|---|---|---|---|---|
| EXP-A1 | 2 | Daniel | 2 · Bandits | RQ1 | Greedy, ε-greedy, optimista, UCB contra `modsec-pl1` | 10 | No |
| EXP-A2 | 2 | Daniel | 2 · No estacionario | RQ1 | Promedio muestral vs. paso constante cuando el PL cambia | 10 | No |
| EXP-B1 | 2 | Daniel | 3–4 · MDP y DP | RQ1 | Value iteration vs. policy iteration sobre MDP abstracto estimado | 10 | No |
| EXP-C1 | 2 | Daniel | 5 · Monte Carlo | RQ1 | First-visit vs. every-visit, ε-soft | 10 | No |
| EXP-D1 | 2 | Daniel | 6 · TD | RQ1 | SARSA vs. Q-learning, efecto *cliff* | 10 | No |
| EXP-D2 | 2 | Daniel | 6 · TD(λ) | RQ1 | SARSA(λ), λ ∈ {0, 0.5, 0.9} | 10 | Sí (2) |
| EXP-E1 | 3 | Joaquín | 7 · Aproximación | RQ2 | Defensor lineal semi-gradiente | 5 | No |
| EXP-E2 | 3 | Joaquín | 7 · Triada mortal | — | Divergencia con aproximación + bootstrapping + off-policy | 3 | Sí (2) |
| EXP-F1 | 3 | Joaquín | 12 · DQN | RQ2 | DQN base | 5 | No |
| EXP-F2 | 3 | Joaquín | 12 · DQN | RQ2 | + Double | 5 | No |
| EXP-F3 | 3 | Joaquín | 12 · DQN | RQ2 | + Dueling | 5 | Sí (3) |
| EXP-F4 | 3 | Joaquín | 12 · DQN | RQ2 | + PER | 5 | No |
| EXP-F5 | 3 | Joaquín | 12 · DQN | RQ2 | Barrido de α y frontera de Pareto contra PL1–PL4 | 5 | No |
| EXP-F6 | 3 | Joaquín | — | RQ5 | Defensor estático en familias no vistas | 5 | No |
| EXP-F7 | 3 | Joaquín | — | RQ5 | Defensor estático en benignos difíciles no vistos | 5 | No |
| ABL-1 | 3 | Joaquín | — | RQ2 | Defensor sin scores de ModSecurity | 5 | No |
| ABL-2 | 3 | Joaquín | — | RQ2 | Defensor sin features de sesión ni ventana | 5 | No |
| EXP-G1 | 3 | Joaquín | 8 · Policy gradient | RQ1, RQ2 | REINFORCE con línea base | 5 | No |
| EXP-G2 | 3 | Joaquín | 8 · Policy gradient | RQ1, RQ2 | A2C | 5 | Sí (4) |
| EXP-G3 | 3 | Joaquín | 8 · Policy gradient | RQ1, RQ2 | PPO con GAE | 5 | No |
| EXP-G4 | 3 | Joaquín | 8 · Policy gradient | RQ2 | Coeficiente de entropía y diversidad | 5 | No |
| EXP-H1 | 4 | Nelson | 9 · Planning | RQ4 | Dyna-Q vs. Q-learning vs. PPO por consultas reales | 10 / 5 | No |
| EXP-H2 | 4 | Nelson | 9 · Planning | RQ4 | Dyna-Q vs. Dyna-Q+ con defensor que cambia | 10 | No |
| EXP-H3 | 4 | Nelson | 9 · Planning | RQ4 | Prioritized Sweeping | 10 | Sí (1) |
| EXP-I1 | 4 | Nelson | Integración | RQ3 | Self-play ingenuo vs. con pool | ≥ 3 | No |
| EXP-I2 | 4 | Nelson | Integración | RQ3 | Matriz de cruces | — | No |
| EXP-I3 | 4 | Nelson | Integración | RQ5 | Campeón de self-play en familias no vistas | ≥ 3 | No |
| EXP-I4 | 4 | Nelson | Integración | RQ5 | Campeón de self-play en benignos difíciles | ≥ 3 | No |
| EXP-I5 | 4 | Nelson | Integración | RQ5 | Defensores contra atacantes que no participaron del self-play | ≥ 3 | No |
| EXP-R1 | 4 | Nelson | 9 · Simulado vs. real | todas | Brecha entre modo rápido y modo real | 3 | No |

La columna *Recortable* indica la posición en el orden de recortes del [plan maestro](../03-plan/plan-maestro.md#recortes-de-alcance).

## Fichas

### EXP-A1 — Bandits contra ModSecurity estático
- **Hipótesis:** H1. UCB supera a la mutación aleatoria en ER con el mismo presupuesto.
- **Setup:** envoltorio de bandit sobre `Attacker-v0`. Brazos = los 16 operadores. Cada tirada aplica el operador elegido al payload actual y hace `SEND`; recompensa 1 si hay evasión, 0 si no. Una evasión o un ban reinicia con un payload base nuevo de `train`. Defensor `modsec-pl1`. 20 000 tiradas.
- **Configuraciones:** greedy; ε-greedy ε ∈ {0.01, 0.1}; optimista Q₀ = 1; UCB c ∈ {0.5, 2}; aleatorio.
- **Métricas:** R(t), recompensa media por tirada, % de elección del mejor brazo, ER final en `attacker-eval-v1` usando la política del bandit.
- **Figura:** regret acumulado por método con banda IC.

### EXP-A2 — No estacionariedad
- **Hipótesis:** el paso constante se recupera más rápido que el promedio muestral cuando el defensor cambia.
- **Setup:** como EXP-A1, pero el defensor pasa de `modsec-pl1` a `modsec-pl3` en la tirada 10 000.
- **Configuraciones:** ε-greedy ε = 0.1 con promedio muestral; ε-greedy ε = 0.1 con α ∈ {0.05, 0.1, 0.3}.
- **Métricas:** recompensa media móvil, tiradas hasta recuperar el 90 % de la recompensa previa al cambio.

### EXP-B1 — Política óptima bajo modelo estimado
- **Hipótesis:** value iteration y policy iteration convergen a la misma política; su ER es una referencia para los métodos sin modelo.
- **Setup:** ver F2-T06. γ = 0.99, θ = 1e-6.
- **Métricas:** iteraciones y tiempo hasta convergencia, ER en `attacker-eval-v1`, diferencia de valor entre ambas políticas.

### EXP-C1 — Monte Carlo
- **Setup:** control MC ε-soft sobre estado abstracto, 200 000 pasos, contra `modsec-pl1`.
- **Configuraciones:** first-visit y every-visit, ε ∈ {0.05, 0.1}.
- **Métricas:** ER en `val` cada 10 000 pasos; ER final.

### EXP-D1 — SARSA contra Q-learning
- **Hipótesis:** Q-learning aprende la política más arriesgada (más BRK durante el entrenamiento) y SARSA una más conservadora, como en *cliff walking*.
- **Setup:** 200 000 pasos, ε = 0.1 fijo durante el entrenamiento para que la comparación on/off-policy sea clara; contra `modsec-pl1` y `modsec-pl2`.
- **Métricas:** recompensa por episodio durante el entrenamiento, BRK durante el entrenamiento, ER final greedy.

### EXP-D2 — TD(λ)
- **Setup:** SARSA(λ) con trazas reemplazantes, λ ∈ {0, 0.5, 0.9}, contra `modsec-pl1`.
- **Métricas:** pasos hasta alcanzar ER en `val` ≥ al de SARSA final de EXP-D1.

### EXP-E1 — Defensor lineal
- **Setup:** Q-learning semi-gradiente lineal y SARSA semi-gradiente sobre 37 features, contra el oponente por defecto de la Fase 3.
- **Métricas:** TPR, FPR, FPR-h, F1 en `defender-eval-v1`.

### EXP-E2 — Triada mortal
- **Setup:** configuración diseñada para mostrar divergencia: aproximación lineal, bootstrapping, datos off-policy de una política de comportamiento fija. Comparar con la misma configuración on-policy.
- **Métricas:** norma de los pesos, error TD.

### EXP-F1 a EXP-F4 — Ablación de DQN
- **Hipótesis:** Double reduce la sobreestimación del valor de `ALLOW`; Dueling acelera el aprendizaje en requests obviamente benignos o maliciosos; PER mejora TPR al repetir ataques que pasaron.
- **Setup:** mismos hiperparámetros compartidos; cada experimento agrega una mejora sobre el anterior. α = 4.
- **Métricas:** TPR, FPR, FPR-h, F1; Q media de `ALLOW` en requests de ataque (sobreestimación); para PER, fracción de muestras de ataques que pasaron.

### EXP-F5 — Frontera de Pareto
- **Hipótesis:** H2.
- **Setup:** mejor variante de F1–F4, α ∈ {1, 2, 4, 8, 16}, β = α/4, γ = α/8.
- **Métricas:** (FPR, TPR) por α con IC; mismos puntos para `modsec-pl1` … `pl4`.
- **Figura:** plano FPR–TPR con la curva del defensor y los cuatro PL.

### EXP-F6 y EXP-F7 — Generalización del defensor estático
- **Setup:** candidato a `DEF-REF-1` y ModSecurity PL1–PL4 en `defender-eval-family-v1` (F6) y `defender-eval-hard-v1` (F7).
- **Métricas:** TPR y FPR; caída respecto a `defender-eval-v1`.

### ABL-1 y ABL-2 — Ablaciones de observación
- **Setup:** configuración de `DEF-REF-1` con máscara de observación: índices 12–15 en cero (ABL-1); índices 16–36 en cero (ABL-2).
- **Métricas:** TPR, FPR, F1 contra la configuración completa.

### EXP-G1 a EXP-G3 — Atacante policy gradient
- **Setup:** REINFORCE con línea base, A2C y PPO con GAE sobre la observación de 288 dimensiones; contra `modsec-pl1` y contra el candidato a `DEF-REF-1`.
- **Métricas:** ER, QFE, DIV en `attacker-eval-v1`; comparación con `ATK-REF-0`.

### EXP-G4 — Entropía
- **Hipótesis:** un atacante más estocástico produce payloads más diversos y es más difícil de bloquear.
- **Setup:** PPO con coeficiente de entropía ∈ {0, 0.01, 0.05}.
- **Métricas:** DIV, UNQ, ER contra `DEF-REF-1`.

### EXP-H1 — Dyna contra model-free
- **Hipótesis:** H4.
- **Setup:** ver diseño en la Fase 4. `n` ∈ {0, 5, 20, 50}. Contra `modsec-pl1` y `DEF-REF-1`.
- **Métricas:** ER en `val` contra consultas reales acumuladas; exactitud del sustituto.
- **Figura:** ER contra consultas reales, una curva por método.

### EXP-H2 — Dyna-Q+
- **Setup:** el defensor cambia de `modsec-pl1` a `DEF-REF-1` a mitad del entrenamiento. Dyna-Q vs. Dyna-Q+ con κ ∈ {1e-3, 1e-2}.
- **Métricas:** consultas reales hasta recuperar ER previa al cambio.

### EXP-H3 — Prioritized Sweeping
- **Setup:** como EXP-H1 con priorización por incertidumbre del sustituto.
- **Métricas:** igual que EXP-H1.

### EXP-I1 — Self-play ingenuo contra pool
- **Hipótesis:** H3.
- **Setup:** ver diseño en la Fase 4. 8 generaciones, ritmo 3:1.
- **Métricas:** TPR de cada generación de defensor contra `ATK-REF-0`, `ATK-REF-1` y atacantes de generaciones anteriores; ER de cada generación de atacante contra `modsec-pl1` y `DEF-REF-1`.

### EXP-I2 — Matriz de cruces
- **Setup:** configuración con pool de EXP-I1. Cada `def-gen-i` contra cada `atk-gen-j` con `attacker-eval-v1`.
- **Figura:** heatmap de ER (filas: defensores; columnas: atacantes).

### EXP-I3 a EXP-I5 — Generalización final
- **Setup:** campeón de self-play vs. `DEF-REF-1` vs. ModSecurity en `defender-eval-family-v1` (I3) y `defender-eval-hard-v1` (I4); contra un PPO nuevo con semilla distinta entrenado contra `DEF-REF-1` y contra el mejor Dyna-Q de EXP-H1 (I5).
- **Métricas:** TPR, FPR, ER-d.

### EXP-R1 — Brecha simulado contra real
- **Setup:** evaluaciones finales de `ATK-REF-0`, `ATK-REF-1`, `DEF-REF-1` y el campeón de self-play en modo rápido y real con las mismas semillas, suites reducidas a 50 episodios o 500 sesiones.
- **Métricas:** GAP por métrica.
