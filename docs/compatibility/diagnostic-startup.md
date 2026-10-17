# Prueba física del diagnóstico F01.02

Estado: **no ejecutada**. Destino confirmado: **New Nintendo 2DS XL**, Homebrew Launcher. Este documento describe el resultado esperado; no certifica compatibilidad. La compilación y los casos host figuran en el [informe F01.02](../execution/f01-02-diagnostic.md).

## Artefacto de esta ejecución

Archivos locales bajo `build/f01-02/artifacts/`, ignorados por Git:

| Campo | Valor |
|---|---|
| Ejecutable | `sh3_diagnostic.3dsx` |
| Tamaño | 179.980 bytes |
| SHA-256 | `f297720d4e68931b2d29028835b919077ba51e7c4d80e61be84f1848bf4bc181` |
| Build visible | `eabba802d179` |
| Símbolos | `sh3_diagnostic.elf`, conservado en el ordenador |
| Metadatos | `sh3_diagnostic.smdh`; el build incorpora SMDH al 3DSX |

El diagnóstico contiene figuras y tono sintéticos. No necesita la ISO, datos del juego ni guardados. No escribe configuración todavía. FBI y CIA tienen un recorrido independiente posterior; para esta instancia se utiliza Homebrew Launcher. No se cambia la configuración de CPU como parte de esta prueba.

## Pasos y resultado esperado

1. Verificar el SHA-256 del ejecutable en el ordenador. Copiarlo a `/3ds/sh3_diagnostic/sh3_diagnostic.3dsx` en la SD. Mantener ELF y manifiesto del mismo build en el ordenador.
2. Abrir `SH3 diagnostic` desde Homebrew Launcher. Registrar modelo, firmware y versión del launcher observados, fecha y operador. Si no se conoce un dato, escribir `pendiente`.
3. Comprobar el patrón superior: fondo oscuro, rectángulo verde de 320 × 160 desde (40,40), con un cuadrado oscuro de 80 × 80 desde (80,80). La pantalla inferior debe mostrar `Build: eabba802d179`, controles A/START, `State: running` y código NDSP.
4. Pulsar y soltar A: patrón ámbar y `State: paused`. Mantener A durante dos segundos: no debe alternar repetidamente. Soltar y pulsar A de nuevo: verde y `State: running`.
5. Pulsar START: retorno al launcher sin bloqueo. Abrir de nuevo y pulsar A+START simultáneamente: debe prevalecer la salida. Reabrir una tercera vez y salir con START para comprobar que el arranque se repite.
6. Registrar resultado esperado y observado de cada caso, incluyendo fallos. El tono es opcional en esta tarea: anotar el código NDSP y si se escucha, sin cerrar F01.04 por ese dato aislado.

Si aparece `GRAPHICS_INIT_FAILED`, registrar `Stage`, `Build` y si START permite volver. No se fuerza agotamiento de memoria ni se modifica el SDK de la consola para provocar este caso: los tres fallos recuperables ya se inyectan en host. Si no aparece ninguna imagen, registrar pantalla negra y retorno o bloqueo tal como se observa. `gfxInitDefault` no ofrece un código recuperable; no se promete un mensaje si el SDK falla antes de disponer de consola.

La legibilidad, los botones reales, el retorno al launcher y los píxeles quedan pendientes hasta ejecutar estos pasos. Los ensayos de tapa/HOME, audio, depuración y treinta minutos de estabilidad pertenecen a F01.04/F01.05/F01.07/F01.08 y siguen pendientes.

## Registro de evidencia

Completar el registro al ejecutar; no sustituir `no ejecutado` por un resultado inferido del build.

| Campo/caso | Observado actual |
|---|---|
| Modelo previsto | New Nintendo 2DS XL |
| Firmware / launcher y versión observados | pendiente |
| Operador / fecha / duración | pendiente |
| Hash transferido / build en pantalla | pendiente |
| Arranque y patrón | no ejecutado |
| A / mantener A / reanudar | no ejecutado |
| START / A+START / retorno | no ejecutado |
| Reapertura repetida | no ejecutado |
| Código NDSP / audio observado | no ejecutado |
| Error gráfico, si ocurre | no ejecutado |
| Incidencias y ubicación de evidencia | pendiente |

La aceptación física requiere los casos de arranque/controles/salida/reapertura aprobados con el build identificado. Un error de arranque no cuenta como inicio aprobado. F01.02 se cierra solo tras revisar ese registro; G01 tiene además los otros tickets de la fase.
