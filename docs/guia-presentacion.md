# Guía de pruebas y presentación de WAF Arena

Esta guía reúne los comandos para comprobar el proyecto y mostrar el dashboard durante una presentación. Ejecute los comandos desde la raíz del repositorio.

## Requisitos

- Linux x86_64 o Docker Desktop compatible con `linux/amd64`.
- Docker Engine y Docker Compose v2.20 o posterior.
- `uv`, Python 3.11 y `make` para las comprobaciones locales.
- Espacio de disco para las imágenes del laboratorio (PostgreSQL, ModSecurity/CRS y Python con PyTorch CPU).

La primera ejecución de Docker descarga y construye imágenes, por lo que puede tardar más y requiere conexión a Internet. El dashboard se publica únicamente en `127.0.0.1:8501`.

## Preparar el proyecto

Si aún no se ha clonado:

```bash
git clone https://github.com/Diegoval-Dev/RL-FinalProyect.git
cd RL-FinalProyect
```

Sincronice dependencias y ejecute las comprobaciones rápidas:

```bash
uv sync --frozen --group dev --group report
make lint
make test
```

`make lint` ejecuta Ruff. `make test` ejecuta las pruebas unitarias; no necesita iniciar el laboratorio Docker.

Para comprobar integración y aislamiento con el laboratorio activo:

```bash
make test-lab
```

Esta última comprobación inicia contenedores y tarda más. No es necesaria para abrir el dashboard en la presentación.

## Iniciar el dashboard

Desde la raíz del proyecto:

```bash
make demo
```

El comando construye, inicia y espera a que el laboratorio y el dashboard estén disponibles. Abra en el navegador:

```text
http://127.0.0.1:8501
```

En la primera ejecución, la construcción y descarga de imágenes puede tomar varios minutos. Para comprobar los servicios si la página tarda en abrir, ejecute:

```bash
docker compose -f lab/docker-compose.yml -f dashboard/docker-compose.yml --profile tools ps
```

## Recorrido sugerido para la presentación

1. **Laboratorio en vivo:** seleccione un defensor (`DEF-REF-1` o `selfplay-champion`) y el tipo de tráfico. Use el control de solicitudes máximas para mantener breve la demostración y pulse **Ejecutar sesión en vivo**. La tabla muestra, para las solicitudes observadas, la acción del defensor y la decisión de ModSecurity PL2.
2. **Curvas:** muestre la evolución de TPR de EXP-I1 y la relación entre consultas reales y ER de H1. El video de EXP-I1, si está disponible, aparece en esta pestaña.
3. **Cruces:** explique la matriz de resultados entre generaciones de defensores y atacantes de EXP-I2.
4. **Resultados finales:** muestre las métricas de generalización RQ5 y la brecha entre el entorno rápido y el laboratorio real de EXP-R1.

Las pestañas de curvas, cruces y resultados finales leen CSV versionados. La sesión en vivo consulta el laboratorio en ese momento; es una muestra de presentación, no un nuevo resultado estadístico ni un entrenamiento.

## Detener la demo

Para detener los servicios conservando los volúmenes de Docker:

```bash
docker compose -f lab/docker-compose.yml -f dashboard/docker-compose.yml --profile tools stop
```

Para volver a iniciar la demo después:

```bash
make demo
```

## Solución rápida de problemas

- **No abre `127.0.0.1:8501`:** confirme que Docker esté activo y revise los servicios con el comando `docker compose ... ps` de arriba. Si la imagen se está construyendo por primera vez, espere a que `make demo` termine.
- **El puerto 8501 está ocupado:** cierre el otro servicio que lo utiliza y vuelva a ejecutar `make demo`.
- **No cargan los resultados:** ejecute la demo desde la raíz del repositorio y confirme que existan los archivos en `results/summary/`. El dashboard muestra un error si faltan archivos o no coinciden sus fuentes; no sustituye datos por métricas de ejemplo.
- **Falla la sesión en vivo:** confirme que los servicios del laboratorio estén saludables. Las vistas de resultados guardados no requieren ejecutar una sesión en vivo.

Para más detalle sobre las fuentes de datos y el funcionamiento del dashboard, consulte [dashboard/README.md](../dashboard/README.md). Para las pruebas y comandos de experimentos, consulte el [README del proyecto](../README.md).
