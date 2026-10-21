# 8. Ética y alcance

Este proyecto produce un atacante que aprende a evadir un WAF. Esa capacidad se acota con reglas de
operación que aplican por igual a personas y agentes, detalladas en
[docs/00-vision/etica-y-alcance.md](../../docs/00-vision/etica-y-alcance.md).

## Aislamiento

Toda la experimentación ocurre en una red de Docker Compose declarada `internal: true`, sin salida
a internet y sin puertos publicados. Una prueba automática (`tests/lab/test_isolation.py`) verifica,
con un control positivo contra un host interno, que ningún contenedor resuelve DNS externo ni abre
conexiones a direcciones externas. Los únicos objetivos válidos son `vulnapp` y los servicios del
propio laboratorio.

## Origen del corpus

Los payloads base son cadenas de inyección SQL clásicas y de dominio público, documentadas por la
comunidad de seguridad, adaptadas a PostgreSQL y a los contextos de inyección de `vulnapp`. No se
incorporan payloads obtenidos de sistemas de terceros. El origen se registra en
`data/payloads/SOURCES.md`.

## Propósito y política de publicación

El propósito es defensivo: *red teaming* automatizado para medir y mejorar la robustez de un WAF de
reglas. No se publica un generador de evasiones empaquetado contra configuraciones de producción
concretas; el material público documenta el método y los resultados agregados. Si se encontrara una
debilidad relevante en el OWASP CRS, se seguiría su proceso de divulgación responsable antes de
describirla en detalle, y la decisión la tomaría el equipo con el catedrático.

## Limitación del oráculo en producción

En el laboratorio el oráculo sabe con certeza qué request es un ataque y si tuvo efecto. En
producción no existe esa señal inmediata. El informe discute cómo se aproximaría —recompensas
retrasadas, etiquetado por analistas, señales indirectas como errores de base de datos o
honeypots— y no presenta el defensor como listo para producción.
