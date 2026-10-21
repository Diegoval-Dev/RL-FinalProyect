# ADR-0008: Anomaly score de ModSecurity por audit log JSON en volumen compartido

- **Estado:** Aceptado
- **Fecha:** 2026-10-21
- **Autor:** Diego Valenzuela
- **Tarea relacionada:** F1-T05

## Contexto

El defensor necesita el anomaly score de OWASP CRS por request, no solo si bloqueó. La imagen
`owasp/modsecurity-crs:nginx` corre en modo de puntuación de anomalía y expone el audit log, pero
el score total solo aparece de forma explícita (regla 949110 "Total Score: N") cuando supera el
umbral del PL. Hacía falta un mecanismo que dé el score en **todos** los requests, incluidos los
que pasan, y que se correlacione con nuestro `X-Request-ID`.

## Opciones consideradas (spike de 1 día)

1. **Header de respuesta** inyectado por una regla `phase:5` con la variable `TX.INBOUND_ANOMALY_SCORE`.
   Descartada: la propagación `setenv` → `Header` de nginx no funcionó con el conector ModSecurity-nginx (header vacío).
2. **Regla de log `phase:5`** que escribe el score en el mensaje del audit log.
   Descartada: los `SecAction phase:5` van al error log, no al arreglo `messages` del audit log JSON.
3. **Audit log JSON en volumen compartido, `AuditEngine=On`, correlación por `X-Request-ID`.**
   El score se reconstruye sumando la contribución por severidad de cada regla en `messages`
   (CRITICAL=5, ERROR=4, WARNING=3, NOTICE=2), ignorando las reglas de evaluación (9xx).
   `would_block = is_interrupted`. Validado contra el total de la regla 949110 cuando bloquea.

## Decisión

Opción 3. Cuatro servicios `modsec-pl1`…`pl4` proxy a `vulnapp`, cada uno con `AuditEngine=On` y
`SecAuditLog` a `/var/log/modsec-audit/plN.json` en un volumen compartido. Un servicio de un solo
uso `audit-init` deja el volumen escribible por el usuario `nginx` antes de arrancar las instancias
(el entrypoint de la imagen corre sin privilegios y no puede hacerlo). `modsec_score(method, path,
pl)` envía el request con un `X-Request-ID` único y lee la entrada correspondiente del archivo.

## Consecuencias

- El score está disponible en cada request, bloqueado o no, sin reglas personalizadas.
- El score sub-umbral se reconstruye por severidad; para un benigno sin reglas que casen, es 0.
- `AuditEngine=On` registra todos los requests: el archivo crece durante el entrenamiento. El modo
  rápido (F1-T11) cachea `(PL, hash del request)`, así que no relee el archivo en cada paso.
- El mecanismo depende de un volumen de Docker compartido entre las instancias y el runner; no
  sirve fuera del laboratorio, lo cual es aceptable porque solo se usa en modo real y para el baseline.
