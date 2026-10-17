# Prueba física F01.03: archivos y opciones diagnósticas

Estado: **no ejecutada**. Consola prevista: New Nintendo 2DS XL con Homebrew Launcher. Este procedimiento valida únicamente archivos propios del diagnóstico; no valida guardados, paquetes ni opciones del juego. F01.02/hardware y G01 siguen pendientes.

## Preparación

Usar el 3DSX y `probe.txt` identificados en el [informe F01.03](../execution/f01-03-files.md), disponibles localmente bajo `build/f01-03/artifacts/`. Build visible: **`69dad0b82f77`**. Copiarlos a `/3ds/sh3_diagnostic/` en la SD. El directorio debe existir; el programa no lo crea. El fixture contiene exactamente `SH3 SD PROBE v1` seguido de un salto LF, 16 bytes, sin BOM ni CRLF.

No copiar ISO, partidas ni archivos originales. Los únicos archivos escritos son `options-a.dat` y `options-b.dat` en esa carpeta dedicada. Para ensayar primer inicio, conservar aparte cualquier opción diagnóstica previa y empezar sin esos dos archivos, con la aplicación cerrada. No modificar los slots mientras el programa está abierto.

Registrar modelo, firmware, launcher/versión, build mostrado, hash del 3DSX transferido, fecha y operador. Un dato desconocido permanece `pendiente`. Mantener el ELF del mismo build en el ordenador.

## Casos y resultado esperado

| Caso | Acción | Resultado esperado |
|---|---|---|
| Primer inicio | Abrir con fixture y sin slots | Patrón/control de F01.02; `Probe: OK`, `Load: MISSING`, `Save: NOT_RUN`, `Tone: on`; no se crean slots automáticamente |
| Cambiar y guardar | Pulsar X y esperar la siguiente actualización | `Tone: off`, `Save: OK`; existe `options-a.dat`, 16 bytes |
| Persistencia | Salir con START y reabrir | `Load: OK`, `Tone: off`, `Save: NOT_RUN`; la opción inicial se aplica antes de encolar el tono |
| Restaurar | Pulsar Y y esperar actualización | `Tone: on`, `Save: OK`; se escribe el slot alterno |
| Reabrir restaurado | Salir con START y abrir de nuevo | `Load: OK`, `Tone: on` |
| Prioridad de salida | Pulsar START junto con X/Y | Salir sin una escritura adicional |
| Fixture ausente | Con aplicación cerrada, renombrar únicamente `probe.txt`; abrir | `Probe: MISSING`; opciones independientes y START disponibles; no se recrea el fixture |
| Fixture parcial | Con aplicación cerrada, usar una copia del fixture truncada; abrir | `Probe: INVALID_DATA`; no informa éxito. Restaurar después el fixture exacto |

Los estados Probe/Load corresponden al inicio; Save al último intento y se actualiza en el siguiente frame. Un cambio X/Y confirmado no borra el aviso histórico de recuperación de Load. A mantiene su comportamiento de pausa; X/Y no reanudan una sesión pausada. START prevalece sobre Y, X y A; Y prevalece sobre X, y X sobre A.

El tono y el resultado NDSP se anotan por separado: `Save: OK` acredita el ciclo de escritura/cierre/relectura de las opciones, no la salida audible. Un error de audio no impide comprobar archivos.

No se requiere llenar la SD ni retirarla durante escritura. Disco lleno, I/O parcial y fallos de flush/cierre/relectura se inyectan en host. La prueba física no promete tolerancia a cortes de energía. El [contrato v1](../../schemas/diagnostic-options-v1.md) explica la selección de generaciones y el candidato no confirmado tras un error tardío.

## Registro pendiente

| Dato/caso | Resultado observado |
|---|---|
| Modelo/firmware/launcher/versión | pendiente |
| Build/hash/operador/fecha/duración | pendiente |
| Arranque y lectura correcta | no ejecutado |
| X / escritura / estado mostrado | no ejecutado |
| Persistencia tras salir/reabrir | no ejecutado |
| Y / restauración / reapertura | no ejecutado |
| START combinado | no ejecutado |
| Fixture ausente/parcial | no ejecutado |
| NDSP/audio, registrado aparte | no ejecutado |
| Incidencias y evidencia | pendiente |

Conservar los resultados fallidos como fallidos. La casilla F01.03 solo se cierra tras aprobar lectura, persistencia, restauración y errores físicos previstos con identidad del build. Las suites host y la compilación ARM no completan esa instancia.
