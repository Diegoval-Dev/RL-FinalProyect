# ADR-0009: PyTorch solo CPU para DQN y policy gradient

- **Estado:** Aceptado
- **Fecha:** 2026-10-25
- **Autor:** Joaquín Puente
- **Tarea relacionada:** F3-T03, F3-T08

## Contexto
ADR-0006 decidió implementar DQN y PPO partiendo de implementaciones de un archivo estilo CleanRL, que usan PyTorch. Hasta la Fase 2 el proyecto no tenía librería de redes neuronales. Las redes de esta fase son MLP pequeñas (37 → 128 → 128 → 5 para el defensor, 288 → 64 → 64 → 17 para el atacante) y todos los entornos corren en CPU, en el contenedor `runner`. Todas las imágenes del laboratorio comparten la misma lista de dependencias (`uv sync` en `lab/Dockerfile`), y el proxy necesitará cargar `DEF-REF-1` para medir latencia (F3-T10).

## Opciones consideradas
1. PyTorch desde PyPI (rueda por defecto, incluye CUDA: del orden de GB por imagen).
2. PyTorch desde el índice oficial solo CPU (`https://download.pytorch.org/whl/cpu`).
3. MLP propias en NumPy con retropropagación a mano.

## Decisión
Opción 2: `torch` como dependencia de runtime, resuelta desde el índice solo CPU con `[tool.uv.sources]` en `pyproject.toml`. Cada agente fija `torch.set_num_threads(threads)` (1 por defecto, desde el YAML) para que los runs sean deterministas y varios puedan correr en paralelo sin competir por hilos.

## Consecuencias
- Las ablaciones (Double, Dueling, PER) y PPO se escriben como en CleanRL, con autograd, sin retropropagación manual que probar.
- No hay aceleración por GPU; con redes de este tamaño el cuello de botella es el entorno, no la red.
- Las imágenes y el CI descargan la rueda CPU de PyTorch (cientos de MB): `make setup` y el primer `make lab-up` tardan más.
- La opción 3 quedó descartada por el costo de mantener y probar gradientes a mano para cuatro variantes de DQN y tres algoritmos de policy gradient.
