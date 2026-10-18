# Estructura del repositorio

La crea la tarea F1-T01. Cada carpeta tiene un dueño original (quien la crea). Después de cada relevo, el dueño de la fase activa puede modificar cualquier carpeta, respetando los contratos.

```
wafarena/                          # paquete Python principal
├── envs/
│   ├── attacker_env.py            # WafArena/Attacker-v0                 (F1)
│   ├── defender_env.py            # WafArena/Defender-v0                 (F1)
│   ├── abstract_state.py          # estado abstracto para tabulares      (F1)
│   └── backends/
│       ├── base.py                # interfaz Backend                     (F1)
│       ├── fast.py                # modo rápido con caché                (F1)
│       └── real.py                # modo real HTTP                       (F1)
├── oracle/                        # oráculo con canarios                 (F1)
├── mutations/
│   ├── operators.py               # 16 operadores                        (F1)
│   └── registry.py                # índice estable operador ↔ acción     (F1)
├── features/
│   ├── request.py                 # features de request                  (F1)
│   └── session.py                 # features de sesión                   (F1)
├── defenders/
│   ├── base.py                    # protocolo DefenderPolicy             (F1)
│   └── modsec.py                  # ModSecurity PLn como política        (F1)
├── attackers/
│   ├── base.py                    # protocolo AttackerPolicy             (F1)
│   ├── random_mutation.py         # atacante aleatorio de referencia     (F1)
│   └── corpus_replay.py           # corpus sin mutar                     (F1)
├── agents/
│   ├── base.py                    # protocolo Agent + checkpoints        (F2)
│   ├── bandits/                   # greedy, ε-greedy, optimista, UCB     (F2)
│   ├── tabular/                   # DP, MC, SARSA, Q-learning, TD(λ)     (F2)
│   ├── linear/                    # semi-gradient TD                     (F3)
│   ├── dqn/                       # DQN, Double, Dueling, PER            (F3)
│   ├── pg/                        # REINFORCE, A2C, PPO                  (F3)
│   └── dyna/                      # sustituto, Dyna-Q, Dyna-Q+, PS       (F4)
├── selfplay/                      # orquestador, pool, generaciones      (F4)
├── eval/
│   ├── metrics.py                 # métricas del contrato                (F2)
│   ├── harness.py                 # suites de evaluación fijas           (F2)
│   ├── stats.py                   # IC bootstrap, agregación de semillas (F2)
│   └── crossplay.py               # matriz de cruces                     (F4)
└── run.py                         # CLI: python -m wafarena.run          (F2)

lab/
├── docker-compose.yml             # red interna, todos los servicios     (F1)
├── vulnapp/                       # app vulnerable + ENDPOINTS.md        (F1)
├── db/init.sql                    # esquema, datos, canarios             (F1)
├── modsec/                        # config de PL1–PL4                    (F1)
├── proxy/                         # proxy defensor                       (F1)
└── honeypot/                      #                                      (F1)

data/
├── payloads/corpus.jsonl          # corpus validado                      (F1)
├── benign/sessions.jsonl          # sesiones benignas                    (F1)
└── splits/v1.json                 # splits congelados + hashes           (F1)

traffic/                           # Locust y Playwright                  (F1)
configs/
├── env/                           # configs base de entornos             (F1)
└── exp/                           # un YAML por run de experimento       (F2+)
results/                           # salida de runs; solo results/summary/ se versiona
checkpoints/refs/                  # ATK-REF-0, DEF-REF-1, ATK-REF-1      (F2, F3)
dashboard/                         # Streamlit                            (F4)
report/
├── capitulos/                     # un .md por capítulo                  (todos)
└── figuras/                       # generadas por scripts, no a mano     (todos)
tests/
├── unit/
└── lab/                           # requieren make lab-up
docs/
CLAUDE.md
Makefile
pyproject.toml
```

## CLAUDE.md anidados

Cuando una carpeta crece y tiene reglas propias, su dueño agrega un `CLAUDE.md` local corto (por ejemplo `wafarena/envs/CLAUDE.md` con "no cambiar el orden de las acciones del registro sin ADR"). El agente los carga al trabajar en esa carpeta. Mantenerlos por debajo de 40 líneas.
