# ADR-0003: Defensor híbrido con scores de ModSecurity como features

- **Estado:** Aceptado
- **Fecha:** inicio del proyecto
- **Autor:** equipo
- **Tarea relacionada:** F1-T10

## Contexto
Un defensor RL que reemplaza por completo las reglas parte de cero y descarta años de conocimiento encapsulado en el CRS. Un despliegue realista combinaría ambos.

## Opciones consideradas
1. Defensor solo con features propias.
2. Defensor que recibe el anomaly score de un único PL.
3. Defensor que recibe los scores de los cuatro PL.

## Decisión
Opción 3. El defensor aprende cuándo confiar en cada nivel de reglas.

## Consecuencias
- Cada request en modo rápido consulta cuatro instancias de ModSecurity (con caché).
- La ablación ABL-1 (sin scores) mide cuánto aporta el CRS al defensor.
- Comparar el defensor contra ModSecurity solo sigue siendo válido: la pregunta es si el sistema híbrido mejora la frontera.
