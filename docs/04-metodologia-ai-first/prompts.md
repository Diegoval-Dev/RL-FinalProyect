# Biblioteca de prompts

Prompts reutilizables para Claude Code. Reemplazar lo que está entre `<>`. Están escritos para que el agente lea los documentos por sí mismo en vez de recibir el contexto pegado en el chat.

## P0 — Arranque de sesión

```
Lee CLAUDE.md y el documento de la fase activa. Voy a trabajar en la tarea <ID>.
Antes de hacer nada, resúmeme en 5 líneas: qué pide la tarea, qué contratos cita,
qué tareas previas de la fase están marcadas como hechas y si hay hallazgos
abiertos que la afecten. No edites ningún archivo.
```

## P1 — Explorar y planificar una tarea

```
Tarea <ID>. Lee su especificación en docs/03-plan/<archivo de la fase>.md y los
contratos que referencia. Revisa el código existente relacionado.

Propón un plan con:
1. Archivos que vas a crear o modificar (y por qué cada uno).
2. Una prueba por cada criterio de aceptación, con el nombre del test.
3. Dependencias nuevas, si hacen falta.
4. Riesgos o ambigüedades de la especificación.

No escribas código todavía. Espera mi aprobación.
```

## P2 — Implementar con pruebas primero

```
Plan aprobado para <ID>. Primero escribe las pruebas del plan, córrelas y
muéstrame que fallan por la razón esperada. Después implementa lo mínimo para
que pasen. Al final corre `make lint && make test` (y `make test-lab` si la
tarea toca el laboratorio) y pega la salida real. No toques archivos fuera
del plan sin avisarme.
```

## P3 — Revisión adversarial del propio diff

```
Revisa el diff de esta rama como si fueras un revisor que quiere encontrar
problemas. Contrasta contra:
- los criterios de aceptación de <ID>,
- los contratos citados (tamaños, órdenes, valores por defecto, claves de info),
- las reglas de docs/04-metodologia-ai-first/reglas-para-agentes.md.
Busca en particular: accesos a claves gt_, aleatoriedad sin semilla,
hiperparámetros escritos en el código, uso de splits de prueba, rutas o hosts
externos. Lista hallazgos por severidad. No corrijas nada todavía.
```

## P4 — Preparar y lanzar un experimento

```
Experimento <EXP-ID>. Lee su entrada en docs/07-experimentos/catalogo.md y el
contrato docs/02-contratos/experimentos.md. Genera los YAML en
configs/exp/<EXP-ID>/, uno por configuración del catálogo, con las semillas
que indica. Verifica que ningún YAML entrene con split de prueba y que
eval.suites coincida con el catálogo. Muéstrame los YAML y el comando para
correrlos. No los ejecutes.
```

## P5 — Analizar resultados

```
Analiza results/summary/<EXP-ID>.csv. Reglas:
- Usa solo números que estén en ese archivo; cita la fila y la columna.
- Para comparar dos configuraciones usa el IC de la diferencia si existe; si
  los intervalos se solapan, dilo y no declares un ganador.
- Contrasta con la hipótesis del catálogo para <EXP-ID>: ¿se sostiene, se
  refuta o no hay evidencia suficiente?
- Señala resultados sospechosos que podrían ser bugs (por ejemplo ER = 1.0 o
  FPR = 0 exactos).
Dame 1 párrafo de resultado y una lista de verificaciones pendientes.
```

## P6 — Redactar el handoff

```
Voy a entregar la fase <N>. Con base en la sección Estado y Hallazgos de mi
documento de fase, docs/07-experimentos/registro.md, results/summary/ y
`git log v<tag anterior>..HEAD`, llena docs/05-handoffs/handoff-<N>-*.md
siguiendo la plantilla. Donde no tengas el dato, deja [COMPLETAR] en vez de
suponerlo. Ejecuta tú mismo cada comando del checklist de aceptación y reporta
su salida real.
```

## P7 — Aceptar un handoff

```
Recibo la fase <N-1>. Lee docs/05-handoffs/handoff-<N-1>-*.md. En esta máquina,
ejecuta en orden cada punto del checklist de aceptación y dime cuál pasa y
cuál falla, con la salida. Verifica también que los hashes de los splits
coinciden (`make verify-splits`) y que los checkpoints de referencia cargan.
No arregles nada: solo reporta.
```

## P8 — Redactar un capítulo del informe

```
Redacta report/capitulos/<archivo>.md según docs/08-informe/estructura-informe.md.
- Cada número debe venir de results/summary/ y citarse como (EXP-ID, run, N semillas).
- Cada figura debe existir en report/figuras/ y haberse generado por script.
- Solo cita referencias marcadas como verificadas en docs/08-informe/referencias.md.
- Describe lo que el código hace realmente: si el documento de fase dice una
  cosa y el código otra, avísame antes de escribir.
- Registro académico formal en español, sin muletillas de relleno.
```

## P9 — Depurar un entrenamiento que no aprende

```
El run <run_id> no aprende (describe el síntoma). Revisa en este orden y
reporta qué encontraste en cada punto antes de proponer cambios:
1. ¿La recompensa tiene la escala esperada? Distribución de recompensas por episodio.
2. ¿La observación tiene valores fuera de [0, 1] o constantes?
3. ¿El agente con política aleatoria obtiene lo mismo que el agente "entrenado"?
4. ¿La exploración decae demasiado rápido?
5. ¿Hay fuga o error en la terminación (terminated vs truncated)?
6. ¿La tasa de aprendizaje y la red objetivo (si aplica) son razonables?
7. ¿El entorno es determinista con la semilla dada?
No cambies hiperparámetros en el código: proponlos como cambios al YAML.
```

## P10 — Registrar una decisión

```
Tomamos esta decisión: <decisión>. Redacta un ADR nuevo en docs/06-decisiones/
con la plantilla, numerado después del último existente. Incluye contexto,
opciones consideradas, decisión y consecuencias, y qué contratos o documentos
hay que actualizar. Agrega el ADR al índice.
```
