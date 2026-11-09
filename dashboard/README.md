# Demo local de WAF Arena (F4-T10)

Desde la raíz del repositorio:

```bash
make demo
```

Abrir `http://127.0.0.1:8501`. El comando levanta el laboratorio Docker aislado y el dashboard; únicamente el puerto del dashboard se publica en la interfaz local `127.0.0.1`. Para detenerlo sin borrar los volúmenes:

```bash
docker compose -f lab/docker-compose.yml -f dashboard/docker-compose.yml --profile tools stop
```

## Datos mostrados

- **Laboratorio en vivo:** el botón ejecuta una sesión `test` del plan reducido de EXP-R1 con `backend=real`. El usuario elige `DEF-REF-1` o el campeón de self-play y tráfico benigno o `ATK-REF-1`. Cada fila muestra la decisión del defensor y la decisión que habría tomado ModSecurity PL2 sobre la misma solicitud, consultadas al laboratorio en ese momento. La muestra se limita a 1–20 solicitudes y no se agrega a ningún resultado experimental. La interfaz muestra la hora UTC, identificadores de los checkpoints, referencia y semilla del plan.
- **Curvas:** TPR por generación de `results/summary/EXP-I1_curve.csv` (entrenamiento `eea6f78`) y ER frente a consultas reales de `results/summary/EXP-H1.csv` (runs `7714621`/`9d54cd2`).
- **Cruces:** matriz completa de 8 × 8 de `results/summary/EXP-I2_matrix.csv` (evaluación `85524f0`).
- **Resultados finales:** `results/summary/RQ5_final.csv` (evaluación `bf14912`) y `results/summary/EXP-R1_gap.csv` (evaluación `c1d2f4d`). Una celda vacía en GAP indica que la métrica quedó indefinida.
- **Video:** `report/video/EXP-I1_arms_race.mp4`, 8 segundos, generado exclusivamente de los TPR de EXP-I1. Regenerar con `make demo-video` (requiere FFmpeg).

El servicio de UI se agrega mediante `dashboard/docker-compose.yml`. El archivo base `lab/docker-compose.yml` conserva solo la red interna y no publica puertos; el dashboard es el único servicio conectado además a `demo-ui` para publicar `127.0.0.1:8501`.

La interfaz detiene la carga si faltan resúmenes o si sus identificadores de fuente no coinciden con los esperados. No contiene métricas de ejemplo ni resultados calculados sin un run o una consulta en vivo.
