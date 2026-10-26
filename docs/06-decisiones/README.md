# Decisiones de arquitectura (ADR)

Un ADR registra una decisión, su contexto y sus consecuencias. Sirve para que nadie (persona o agente) deshaga una decisión sin saber por qué se tomó. Se crean con el prompt [P10](../04-metodologia-ai-first/prompts.md#p10--registrar-una-decisión).

Un ADR aceptado no se edita: si la decisión cambia, se crea uno nuevo que lo reemplaza y se marca el anterior como *Reemplazado por ADR-XXXX*.

| ADR | Título | Estado |
|---|---|---|
| [0001](adr-0001-solo-sqli.md) | Solo SQL injection contra PostgreSQL | Aceptado |
| [0002](adr-0002-relevo-secuencial.md) | Relevo secuencial con una sola dependencia por persona | Aceptado |
| [0003](adr-0003-defensor-hibrido.md) | Defensor híbrido: scores de ModSecurity como features | Aceptado |
| [0004](adr-0004-oraculo-por-estructura-y-canarios.md) | Oráculo por cambio de estructura y canarios | Aceptado |
| [0005](adr-0005-dos-velocidades.md) | Entorno de dos velocidades con caché de ModSecurity | Aceptado |
| [0006](adr-0006-cleanrl-y-tabulares-propios.md) | Tabulares propios y deep RL estilo CleanRL | Aceptado |
| [0007](adr-0007-app-propia-python.md) | App objetivo propia y stack único en Python | Aceptado |
| [0008](adr-0008-modsec-score-por-audit-log.md) | ModSecurity: anomaly score por audit log JSON | Aceptado |
| [0009](adr-0009-pytorch-cpu.md) | PyTorch solo CPU para DQN y policy gradient | Aceptado |
| [0010](adr-0010-desempate-def-ref-1.md) | Desempate de la regla de selección de `DEF-REF-1` | Aceptado |

Próximo número libre: **0011**.

## Plantilla

```markdown
# ADR-XXXX: <título>

- **Estado:** Propuesto | Aceptado | Reemplazado por ADR-YYYY
- **Fecha:**
- **Autor:**
- **Tarea relacionada:**

## Contexto
Qué problema hay y qué restricciones aplican.

## Opciones consideradas
1. …
2. …

## Decisión
Qué se eligió.

## Consecuencias
Qué se gana, qué se pierde, qué documentos o contratos cambian.
```
