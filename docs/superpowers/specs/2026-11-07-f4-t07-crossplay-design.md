# F4-T07 / EXP-I2: matriz de cruces

## Propósito

Medir cómo responde cada defensor de las ocho generaciones de self-play con pool ante cada atacante de esas mismas ocho generaciones. La matriz completa permite ver ciclos y puntos débiles que las referencias fijas de EXP-I1 no muestran.

## Diseño elegido

- `make crossplay RUN=checkpoints/selfplay/EXP-I1__pool__s0__eea6f78` acepta un directorio de checkpoints de una semilla del pool. La configuración EXP-I2 exige las tres semillas 0–2 y el comando localiza sus directorios hermanos con el mismo SHA de entrenamiento. Solo necesita checkpoints, no resultados crudos de EXP-I1.
- Cada celda `(semilla, defensor i, atacante j)` usa `attacker-eval-v1`: 200 episodios de `test`, semillas 1000–1199 y presupuesto de 50 consultas, con el mismo backend rápido del laboratorio. Hay 64 celdas por semilla y 192 en total.
- El atacante se carga desde `atk-gen-j` y el defensor desde `def-gen-i` del mismo run. Se comprueban rol, generación, semilla, run ID, SHA, contrato y presencia de pesos antes de evaluar. Las celdas se guardan atómicamente y se rechaza una caché obsoleta si cambian los pesos o la configuración.
- `results/summary/EXP-I2_cells.csv` conserva las 192 tasas y conteos con procedencia; `EXP-I2_matrix.csv` agrega las tres tasas de semilla por celda con IC *bootstrap* del 95 %. `report/figuras/EXP-I2_crossplay.png` muestra un heatmap 8×8 de la media de ER, con filas de defensores y columnas de atacantes. Una tasa indefinida queda sin color y se señala en la figura.
- Se registra un run de EXP-I2 por semilla con código de evaluación limpio y configuración resuelta. La figura y los CSV se versionan; las celdas y los metadatos crudos quedan en `results/`.

## Alternativas consideradas

- Una sola semilla: cumple la forma 8×8, pero no permite distinguir patrón de azar; se descarta porque ya existen tres runs del pool.
- Reusar la evaluación histórica de EXP-I1: solo cubre `j < i`, usa `val` y 40 sesiones de defensor; no es la matriz completa ni la suite requerida.
- Elegida: 3 matrices 8×8 en `attacker-eval-v1`, con resumen por semilla y heatmap agregado. Cuesta más cómputo, pero preserva la comparación completa y la procedencia.

## Límites de interpretación

Esta evaluación en `test` es de solo lectura. No se ajustan políticas, hiperparámetros ni se selecciona un campeón con EXP-I2. La elección para F4-T08 debe basarse en `val`. ER es una tasa por episodio del atacante; no debe confundirse con el TPR por solicitud de EXP-I1. Tres semillas son pocas para una conclusión fuerte sobre diferencias pequeñas.

## Aceptación

El comando de Make regenera los 192 cruces desde los checkpoints y produce CSVs y figura con los 64 pares únicos por semilla. Falla si falta o no coincide un checkpoint, si una celda cacheada está obsoleta o si el número de episodios difiere de la suite. La reejecución usa la caché y deja los checkpoints intactos. Pasan lint y pruebas unitarias.
