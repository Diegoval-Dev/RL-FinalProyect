# Convenciones

## Idiomas

- Código, identificadores, nombres de archivos de código, docstrings y comentarios en el código: inglés.
- Documentación en `docs/`, informe en `report/`, mensajes de PR y handoffs: español.

## Python

- Python 3.11, `ruff` para lint y formato (configuración en `pyproject.toml`).
- Type hints en todas las funciones públicas.
- Dataclasses `frozen=True` para estructuras de datos que cruzan módulos.
- Aleatoriedad solo con `np.random.Generator` recibido por parámetro o creado desde una semilla de configuración. Prohibido `random` global y `np.random.seed`.
- Nada de `print` en código de la librería: `logging`.
- Hiperparámetros solo desde YAML. Los valores por defecto viven en un único lugar por módulo y coinciden con el contrato.

## Pruebas

- `tests/unit/`: sin Docker, rápidas, corren en CI.
- `tests/lab/`: requieren `make lab-up`; marcadas con `@pytest.mark.lab`.
- Nombre: `test_<qué>_<condición>_<resultado esperado>`.
- Pruebas *property-based* con `hypothesis` para operadores y features.
- Toda prueba de un criterio de aceptación lleva el ID de la tarea en el docstring.

## Git

- Rama principal: `main`, protegida; merge solo por PR con CI en verde.
- Ramas: `f<N>/<ID>-<slug>`, por ejemplo `f2/F2-T05-bandits`.
- Commits: `tipo(ID): descripción en español`. Tipos: `feat`, `fix`, `test`, `docs`, `exp`, `refactor`, `chore`. Ejemplo: `exp(F2-T08): runs de EXP-D1 con 10 semillas`.
- Tags: `v0.1-fase1`, `v0.2-fase2`, `v0.3-fase3`, `v1.0`.
- Archivos grandes (checkpoints > 50 MB, sesiones grabadas) con Git LFS.
- `results/` en `.gitignore` salvo `results/summary/`.

## Plantilla de PR

```
## Tarea
<ID> — <título>

## Qué cambia
-

## Criterios de aceptación
- [ ] <criterio> → `tests/...::test_...`

## Verificación
<salida de make lint && make test>

## Contratos / ADR / registro
- [ ] Sin cambios de contrato | contrato <x> actualizado a <versión>
- [ ] ADR: <número o "no aplica">
- [ ] Registro de experimentos: <fila o "no aplica">

## Notas para el revisor
```

## Nombres

| Cosa | Formato | Ejemplo |
|---|---|---|
| Tarea | `F<N>-T<nn>` | `F3-T05` |
| Experimento | `EXP-<letra><n>` | `EXP-F5` |
| Ablación | `ABL-<n>` | `ABL-1` |
| ADR | `adr-<nnnn>-<slug>.md` | `adr-0004-oraculo-por-estructura-y-canarios.md` |
| Run | `<exp>__<run_name>__s<seed>__<sha>` | `EXP-D1__qlearning-pl1__s3__abc1234` |
| Checkpoint de referencia | `<ROL>-REF-<n>` | `DEF-REF-1` |
| Checkpoint de self-play | `<rol>-gen-<nn>` | `def-gen-04` |
