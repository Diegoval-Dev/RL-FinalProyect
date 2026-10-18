# Glosario

| Término | Significado en este proyecto |
|---|---|
| **WAF** | Web Application Firewall. Inspecciona requests HTTP y decide si pasan. |
| **ModSecurity** | Motor WAF de código abierto. Se usa la versión 3 con conector Nginx. |
| **CRS** | OWASP Core Rule Set, el conjunto de reglas que ModSecurity aplica. |
| **Paranoia level (PL)** | Nivel de agresividad del CRS, de 1 (menos reglas, menos falsos positivos) a 4 (más reglas, más falsos positivos). |
| **Anomaly score** | Puntaje acumulado que el CRS asigna a un request; si supera el umbral, se bloquea. El defensor lo recibe como feature. |
| **Payload** | La cadena de inyección SQL que el atacante coloca en un parámetro. |
| **Payload base** | Payload público sin mutar, tomado del corpus. |
| **Familia** | Tipo de inyección: `tautology`, `union`, `error`, `boolean_blind`, `stacked`. |
| **Operador de mutación** | Transformación del payload que intenta preservar su semántica (ver [operadores](../02-contratos/operadores-mutacion.md)). |
| **Oráculo** | Componente que verifica con certeza si un payload tuvo efecto en la base de datos (ver [contrato](../02-contratos/oraculo.md)). |
| **Canario** | Valor secreto en la base de datos que solo se puede leer si la inyección cambió la estructura de la consulta. |
| **Funcional** | Un payload es funcional si, enviado directo a `vulnapp` sin WAF, el oráculo confirma efecto. |
| **Evasión** | Un payload funcional que el defensor deja pasar (`ALLOW`) y cuyo efecto el oráculo confirma. |
| **Benigno difícil** | Request legítimo que se parece a un ataque: apóstrofes (O'Brien), símbolos (`C++`, `<=`), fragmentos de código, español con tildes y emojis. |
| **Sesión** | Secuencia de requests de un mismo cliente. Es el episodio del defensor. |
| **Presupuesto de consultas** | Máximo de envíos al defensor que tiene el atacante por episodio. |
| **Ban** | Terminación del episodio del atacante por acumular demasiados bloqueos. |
| **Modo rápido** | Backend de entrenamiento: sin ciclo HTTP completo, con caché de decisiones de ModSecurity. |
| **Modo real** | Backend de validación: todo pasa por HTTP contra el laboratorio Docker. |
| **Estado abstracto** | Discretización del estado del atacante (familia × última respuesta × cubeta de mutaciones) usada por los métodos tabulares. |
| **Modelo sustituto** | Clasificador que el atacante entrena para predecir si el defensor bloqueará un payload. Base del atacante Dyna. |
| **Self-play** | Entrenamiento alternado de atacante y defensor, cada uno contra versiones del otro. |
| **Pool de oponentes** | Conjunto de checkpoints históricos del oponente contra los que se entrena para evitar olvido. |
| **Matriz de cruces** | Tabla de evaluación de cada generación de defensor contra cada generación de atacante. |
| **Frontera de Pareto** | Curva de configuraciones no dominadas en el plano (tasa de falsos positivos, tasa de detección). |
| **Relevo** | Modelo de trabajo del equipo: cada fase recibe una sola vez el entregable de la anterior. |
| **Handoff** | Documento y tag de git con que una fase entrega a la siguiente. |
| **Contrato** | Interfaz documentada y versionada entre componentes y entre fases. |
| **ADR** | Architecture Decision Record. Registro breve de una decisión de diseño y su porqué. |
| **Referencias fijas** | Oponentes congelados usados para medir progreso real: ModSecurity PL1–PL4, `ATK-REF-0`, `DEF-REF-1`, corpus sin mutar. |
