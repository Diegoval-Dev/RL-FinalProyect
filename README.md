# WAF Arena

Proyecto académico de aprendizaje por refuerzo para estudiar un defensor WAF y un atacante de inyección SQL dentro de un laboratorio propio y aislado. El alcance es SQL injection contra PostgreSQL en `vulnapp`; no se dirige tráfico a sistemas externos.

## Requisitos

- Linux x86_64 o una máquina con Docker Desktop y compatibilidad con `linux/amd64`.
- Docker Engine y Docker Compose v2.20 o posterior (el Compose raíz usa `include`).
- `uv` para instalar dependencias y correr las herramientas Python; Python 3.11 si se trabaja fuera de Docker.
- `make` para los comandos de desarrollo.

Docker descarga las imágenes y dependencias al primer uso. El espacio de disco debe admitir imágenes de Python, PostgreSQL, ModSecurity/CRS y las dependencias de PyTorch CPU.

## Inicio rápido

```bash
git clone https://github.com/Diegoval-Dev/RL-FinalProyect.git
cd RL-FinalProyect
uv sync --frozen --group dev --group report
make lint
make test
docker compose -f lab/docker-compose.yml up --build --wait
```

El comando de Compose levanta el laboratorio con una red Docker interna y sin puertos publicados. Al terminar, puede detenerse sin borrar el volumen de la base de datos:

```bash
docker compose -f lab/docker-compose.yml down
```

## Demo

Con Docker y el laboratorio disponible:

```bash
make demo
```

Abra <http://127.0.0.1:8501>. El dashboard muestra una sesión real acotada y datos provenientes de los resúmenes versionados. Instrucciones, fuentes de datos y parada de la demo: [dashboard/README.md](dashboard/README.md).

## Desarrollo y comprobaciones

```bash
make lint          # Ruff: lint y formato
make test          # Pruebas unitarias
make smoke         # Smoke test con laboratorio
make test-lab      # Pruebas de integración y aislamiento
```

`make test-lab` y `make smoke` levantan servicios Docker. El entorno del laboratorio no tiene salida de red externa; no quite `internal: true`.

## Reproducción de resultados

Las filas de abajo indican el punto de entrada de cada experimento. Los YAML fijan método, configuración y semillas; los resultados de la campaña ya cerrada están en `results/summary/`, el protocolo y commits en [el registro](docs/07-experimentos/registro.md), y la interpretación en los capítulos enlazados. Repetir una campaña completa puede tomar horas y requiere checkpoints y recursos Docker; `make` no modifica los CSV versionados al leerlos.

| Resultado | Configuración / comando | Evidencia |
|---|---|---|
| RQ1, métodos clásicos | `make run CONFIG=configs/exp/EXP-A1/greedy-pl1.yaml` (ejemplo de una configuración) | [RQ1_table.csv](results/summary/RQ1_table.csv), [cap. 4](report/capitulos/04-atacante-clasico.md) |
| H1, Dyna-Q | `make run CONFIG=configs/exp/EXP-H1/dyna-5-defref1.yaml` | [EXP-H1.csv](results/summary/EXP-H1.csv), [cap. 6](report/capitulos/06-planning-selfplay.md) |
| H2, cambio de defensor | `make run CONFIG=configs/exp/EXP-H2/dyna-20-switch.yaml` | [EXP-H2.csv](results/summary/EXP-H2.csv), [EXP-H2_recovery.csv](results/summary/EXP-H2_recovery.csv) |
| I1, self-play | `make selfplay-run CONFIG=configs/selfplay/exp_i1_pool.yaml` | [EXP-I1_curve.csv](results/summary/EXP-I1_curve.csv), [figura](report/figuras/EXP-I1_tpr.png) |
| I2, cruces | `make crossplay RUN=checkpoints/selfplay/<run>` | [EXP-I2_matrix.csv](results/summary/EXP-I2_matrix.csv), [figura](report/figuras/EXP-I2_crossplay.png) |
| I3–I5, generalización | `make generalization` | [RQ5_final.csv](results/summary/RQ5_final.csv), [EXP-I3.csv](results/summary/EXP-I3.csv), [EXP-I4.csv](results/summary/EXP-I4.csv), [EXP-I5.csv](results/summary/EXP-I5.csv), [cap. 7](report/capitulos/07-generalizacion.md) |
| R1, fast vs. real | `make real-gap` | [EXP-R1_gap.csv](results/summary/EXP-R1_gap.csv), [cap. 7](report/capitulos/07-generalizacion.md) |

Los comandos de entrenamiento vuelven a ejecutar configuraciones; no reconstruyen automáticamente la campaña histórica ni descargan checkpoints excluidos de Git. Los resúmenes CSV son la evidencia compacta versionada. Los runs crudos de `results/` están ignorados por Git. Para reconstruir la matriz I2 hacen falta los checkpoints de self-play producidos por I1; la ruta concreta aparece en `checkpoints/selfplay/` después de ejecutar I1.

## Informe

- [Capítulo 1: introducción](report/capitulos/01-introduccion.md)
- [Capítulo 3: laboratorio](report/capitulos/03-laboratorio.md)
- [Capítulo 4: atacante clásico](report/capitulos/04-atacante-clasico.md)
- [Capítulo 5: deep RL](report/capitulos/05-deep-rl.md)
- [Capítulo 6: planning y self-play](report/capitulos/06-planning-selfplay.md)
- [Capítulo 7: generalización](report/capitulos/07-generalizacion.md)
- [Capítulo 8: ética](report/capitulos/08-etica.md)
- [Capítulo 9: conclusiones](report/capitulos/09-conclusiones.md)

El capítulo 2 (trabajo relacionado) todavía no está en el repositorio. La lista de fuentes existente se mantiene en [referencias verificadas](docs/08-informe/referencias.md); su formato final debe ajustarse a lo que pida el curso.

## Estado de entrega

El laboratorio, los resultados versionados y el dashboard están en el repositorio. La publicación final `v1.0` requiere además que otra persona distinta de Nelson siga el inicio rápido desde una clonación limpia y que el equipo revise el informe completo y sus referencias. Esta revisión independiente no se debe inferir de una ejecución local.
