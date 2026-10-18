# Ética y alcance de operación

Este proyecto genera un atacante que aprende a evadir un WAF. Esa capacidad se acota con las siguientes reglas, que aplican por igual a personas y agentes.

## Reglas de operación

1. **Red aislada.** La red de Docker Compose del laboratorio se declara con `internal: true`. Ningún contenedor del laboratorio tiene salida a internet. La tarea F1-T02 incluye una prueba automática que lo verifica.
2. **Objetivos propios.** Los únicos objetivos válidos son `vulnapp` y los servicios del propio laboratorio. Ningún script, configuración ni agente contiene hosts externos como destino.
3. **Corpus público.** Los payloads base vienen de fuentes públicas ya conocidas por la comunidad de seguridad. No se incorporan payloads obtenidos de sistemas ajenos.
4. **Sin publicación de evasiones específicas.** No se publica un generador de evasiones empaquetado para usarse contra configuraciones concretas de producción. El repositorio público, si existe, documenta el método y los resultados agregados.
5. **Reporte responsable.** Si se encuentra una debilidad relevante en el OWASP CRS, se reporta siguiendo el proceso de divulgación del proyecto OWASP CRS antes de mencionarla con detalle en material público. La decisión de reportar la toma el equipo completo con el catedrático.
6. **Agentes de código.** Las instrucciones a agentes nunca piden atacar, escanear ni contactar sistemas fuera del laboratorio. Si un agente propone hacerlo, se rechaza y se anota en *Hallazgos* de la fase.

## Para el informe

El capítulo de ética (dueño: Diego, ver [estructura del informe](../08-informe/estructura-informe.md)) cubre: aislamiento, origen del corpus, propósito defensivo (red teaming automatizado), política de publicación y la limitación de que en producción no existe un oráculo que etiquete ataques al instante.

## Limitación que se declara explícitamente

En el laboratorio el oráculo sabe con certeza qué request es ataque. En producción no existe esa señal inmediata. El informe discute cómo se aproximaría: recompensas retrasadas, etiquetado por analistas, señales indirectas (errores de base de datos, honeypots). No se presenta el defensor como listo para producción.
