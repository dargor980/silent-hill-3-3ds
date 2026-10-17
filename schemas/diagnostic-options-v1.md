# Contrato F01.03: archivos sintéticos y opciones v1

Formato propio del diagnóstico; no es un formato de Silent Hill 3 ni de partidas. Requisitos de origen: RNF03.04, RF11.06, RF14.01. La opción implementada es activar el tono sintético (predeterminado: activado); el perfil de juego español/Normal/Normal no cambia.

## Criterios EARS de esta instancia

- **C01:** WHEN inicia el diagnóstico THEN SHALL leer `probe.txt` y comparar exactamente los 16 bytes ASCII `SH3 SD PROBE v1\n` sin modificar el archivo.
- **C02:** IF falta un archivo o falla una operación THEN SHALL mostrar código, etapa y build, manteniendo la salida mediante START disponible.
- **C03:** WHEN hay registros de opciones válidos THEN SHALL cargar el de mayor generación; un registro inválido no sustituye al válido.
- **C04:** WHEN X solicita cambiar el tono o Y restaurar su valor predeterminado THEN SHALL escribir el slot alterno, cerrar y releer su contenido; solo un resultado íntegro y coincidente confirma la operación en memoria.
- **C05:** IF falla escritura, flush, cierre o verificación THEN SHALL informar fallo y conservar las opciones en memoria y el slot válido anterior sin sobrescribirlo.
- **C06:** IF no puede leer un slot por error de I/O o hay generaciones iguales con valores distintos THEN SHALL impedir escrituras hasta resolver la incertidumbre y reiniciar.
- **C07:** IF llega a la generación máxima THEN SHALL rechazar nuevas escrituras sin wraparound.
- **C08:** WHEN termina cualquier operación THEN SHALL cerrar los handles adquiridos; no se escribe durante el dibujo ni cada frame.

## Datos y selección

Directorio dedicado en consola: `sdmc:/3ds/sh3_diagnostic/`. El adaptador recibe la raíz por constructor; el puerto usa IDs cerrados, no rutas arbitrarias. Archivos: `probe.txt` (solo lectura), `options-a.dat`, `options-b.dat`. La aplicación no crea directorios ni elimina archivos. El lector admite como máximo 32 bytes y detecta un byte adicional; el parser exige exactamente 16. No reserva memoria proporcional a entradas externas.

Registro de opciones, 16 bytes, sin padding nativo:

| Offset | Bytes | Valor |
|---|---:|---|
| 0 | 4 | ASCII `S3OP` |
| 4 | 1 | Versión `1` |
| 5 | 1 | Tono: `0` desactivado / `1` activado |
| 6 | 2 | Reservados, ambos cero |
| 8 | 4 | Generación uint32 little-endian, rango 1…4294967295 |
| 12 | 4 | FNV-1a de bytes 0…11, uint32 little-endian |

FNV-1a usa base 2166136261 y multiplicador 16777619, aritmética módulo 2^32. Detecta alteraciones accidentales; no autentica datos. Campos, versión, tamaño y checksum se validan antes de exponer opciones.

Ambos slots ausentes: valores predeterminados en memoria, `MISSING`, sin escritura automática; la primera solicitud escribe A/generación 1. Un slot válido y otro ausente: usar el válido. Un slot inválido permite recuperar el válido con aviso `INVALID_DATA` (o `TOO_LARGE`) y escribir posteriormente sobre el inválido. Ambos inválidos: predeterminados con aviso; una solicitud explícita puede crear A/1. Dos registros con igual generación y valor son equivalentes; si difieren se informa `AMBIGUOUS` y se bloquea escritura.

El destino de escritura es siempre el slot no seleccionado. `write` comprueba cantidad, `fflush` y `fclose`; la aplicación vuelve a leer y exige coincidencia de todos los bytes. No hay renombrado ni promesa de atomicidad/durabilidad ante pérdida de energía. Un error tardío puede dejar un candidato completo que sea seleccionable al reiniciar: el resultado se informa **no confirmado**, no como rollback físico garantizado. El slot anterior permanece sin escritura; la recuperación real y el comportamiento de SD requieren pruebas físicas.

## Integración y prueba

Dominio: codec de opciones puro. Puertos: lectura acotada y escritura separadas. Aplicación: selección/verificación y confirmación en memoria. Adaptador stdio compartido: archivos y errores tipados. Fachada 3DS: comprobación del fixture, acciones y estado para la vista. START prevalece sobre Y, X y A; Y sobre X; X sobre A. X/Y solo se aceptan mientras la sesión está activa o pausada.

Host prueba codec malformado, selección/recuperación, escrituras parciales, disco lleno simulado, fallos de flush/cierre, relectura distinta y conservación del slot anterior. Se ejecuta además stdio sobre un directorio temporal real y la composición 3DS con dobles del SDK. Compilar ARM no equivale a probar SD, botones o durabilidad en consola.
