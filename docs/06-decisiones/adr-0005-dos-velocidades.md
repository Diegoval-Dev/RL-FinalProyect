# ADR-0005: Entorno de dos velocidades con caché de ModSecurity

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** F1-T11

## Contexto
RL necesita cientos de miles de pasos. Un ciclo HTTP completo por paso a través de Docker es demasiado lento. ModSecurity es determinista dado el request y el PL.

## Opciones consideradas
1. Todo por HTTP siempre.
2. Reimplementar las reglas del CRS en Python para el modo rápido.
3. Modo rápido con consultas en proceso a la base y ModSecurity real por HTTP en lote con caché persistente; modo real para validación.
4. Bindings de libmodsecurity en Python.

## Decisión
Opción 3. La opción 4 puede evaluarse como mejora si los bindings funcionan con la versión usada; si se adopta, se registra en un ADR nuevo. La opción 2 se descarta porque dejaría de comparar contra el ModSecurity real.

## Consecuencias
- Se reportan resultados de ambos modos y la brecha (EXP-R1).
- La caché se invalida si cambia la versión del CRS o la configuración de ModSecurity; la clave incluye un hash de la configuración.
- La prueba de concordancia de F1-T11 protege contra divergencias entre modos.
