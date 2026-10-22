# Contratos

Un contrato es la interfaz documentada entre dos componentes. En un relevo, los contratos son lo que permite que cada fase dependa una sola vez de la anterior: quien recibe no necesita preguntarle nada a quien entregó, porque todo lo que necesita saber del entregable está aquí.

## Lista de contratos

| Contrato | Versión | Implementa | Consume |
|---|---|---|---|
| [env-atacante.md](env-atacante.md) | 1.0 | F1 | F2, F3, F4 |
| [env-defensor.md](env-defensor.md) | 1.1 | F1 | F3, F4 |
| [oraculo.md](oraculo.md) | 1.1 | F1 | entornos (interno) |
| [operadores-mutacion.md](operadores-mutacion.md) | 1.0 | F1 | F2, F3, F4 |
| [features.md](features.md) | 1.0 | F1 | F3, F4 |
| [datos-y-splits.md](datos-y-splits.md) | 1.0 | F1 | todas |
| [agentes-y-checkpoints.md](agentes-y-checkpoints.md) | 1.0 | F1 (protocolos de políticas), F2 (Agent y checkpoints) | F2, F3, F4 |
| [metricas.md](metricas.md) | 1.1 | F2 | F2, F3, F4 |
| [experimentos.md](experimentos.md) | 1.1 | F2 | F2, F3, F4 |

## Versionado

Versión `MAYOR.MENOR`.

- **MENOR** (1.0 → 1.1): cambio compatible. Agregar una clave a `info`, un campo opcional a un YAML, una métrica nueva. Se documenta en la sección *Historial* del contrato.
- **MAYOR** (1.x → 2.0): cambio incompatible. Cambiar el tamaño de la observación, el orden de las acciones, una recompensa por defecto, el formato de un checkpoint. Requiere un ADR y que todos los checkpoints de referencia se regeneren o se marquen como obsoletos.

El código expone la versión en `wafarena.CONTRACT_VERSIONS` (diccionario `nombre → "1.0"`). Cada checkpoint guarda las versiones con que se entrenó. Cargar un checkpoint con versión MAYOR distinta lanza un error.

## Reglas

1. Si el código y el contrato difieren, se corrige uno de los dos en el mismo PR. Nunca se deja la diferencia.
2. Los valores por defecto de este documento son los oficiales. Un experimento puede sobrescribirlos solo desde su YAML, nunca editando constantes.
3. Antes de entregar una fase, su dueño confirma en el handoff qué versión de cada contrato queda implementada.
