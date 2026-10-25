# ADR-0010: Desempate de la regla de selección de `DEF-REF-1`

- **Estado:** Aceptado
- **Fecha:** 2026-10-25
- **Autor:** Joaquín Puente
- **Tarea relacionada:** F3-T05, F3-T11

## Contexto
El plan de la Fase 3 fija la regla de `DEF-REF-1`: entre los defensores de F3-T05, el de mayor TPR en `val` sujeto a FPR en `val` ≤ FPR de `modsec-pl2` en `val`. La regla no dice qué hacer con empates. En EXP-F5, 7 de los 25 checkpoints empatan exactamente con TPR = 1,0 y FPR = 0,0 en `defender-val-v1`, con `fpr_cap` = 0,0. Hace falta un desempate determinista, y tiene que decidirse **solo con `val`**: los promedios por α en `test` ya estaban calculados para la figura de Pareto (EXP-F5) cuando apareció el empate, así que usarlos sería seleccionar en `test`.

## Opciones consideradas
1. Elegir a mano entre los empatados.
2. Desempatar por métricas de `test`.
3. Desempatar con criterios de `val`, en un orden fijo y aplicado por un script.

## Decisión
Opción 3, implementada en `scripts/select_def_ref.py`. Tras la regla del plan, el orden es: menor FPR en `val`, mayor F1 en `val`, mayor TPR medio en `val` del `run_name` del checkpoint sobre sus semillas (se prefiere la configuración más estable, no la semilla con suerte) y, por último, menor semilla. El ranking completo queda en `results/summary/DEF-REF-1_selection.csv`.

## Consecuencias
- `DEF-REF-1` = EXP-F5 `alpha-4`, semilla 0. α = 4 tiene el mayor TPR medio en `val` del barrido (0,99929), y es por eso «el α elegido para `DEF-REF-1`» que usan ABL-1 y ABL-2 (F3-T06).
- La elección se reproduce con un comando y no depende de nadie mirando `test`.
- Si una fase futura vuelve a seleccionar una referencia con la misma regla, reutiliza este desempate o lo reemplaza con un ADR nuevo.
