# Búsqueda acotada de muestras EE en el catálogo

F02.07/camera-resource-link-eu · RL01–RL08 · experimento de coincidencia exacta.

## Requisitos EARS

- **RL01:** CUANDO se investigue una captura, el coordinador DEBERÁ fijar por hash
  plan, captura, ambos recibos CO, catálogo, recibo de extracción y cada estado;
  DEBERÁ revalidar CO y exigir igualdad de los recibos y de los registros importados.
- **RL02:** CUANDO se lea memoria, el lector DEBERÁ aceptar exclusivamente un estado
  PS01–PS07 con `eeMemory.bin` de 32 MiB, verificar completamente su CRC ZIP y extraer
  una muestra de 64 o 256 bytes desde un GPR explícito del mismo punto/estado.
- **RL03:** SI el PC/GPR no coincide, existe delay slot, el puntero es nulo, está
  fuera de `[0x00100000,0x02000000)` o el rango cruza su límite, el lector DEBERÁ
  rechazar. DEBERÁ rechazar alias, scratchpad y memoria extendida sin normalizarlos.
- **RL04:** CUANDO busque muestras, el buscador DEBERÁ recorrer todos los bytes de
  cada recurso aceptado, incluso coincidencias solapadas o entre bloques; DEBERÁ
  verificar tamaño/SHA-256 del recurso completo y estabilidad antes de aceptar hits.
- **RL05:** CUANDO procese entradas, DEBERÁ limitarse a 10 patrones de 64/256 bytes,
  100.000 recursos, 4 GiB por copia, bloques de 1 MiB y 128 hits por patrón en total.
  Una muestra de un solo valor de byte DEBERÁ quedar `non_discriminating`, sin búsqueda.
  SI excede hits o presupuesto, DEBERÁ fallar sin publicar éxito ni truncar en silencio.
- **RL06:** CUANDO termine, DEBERÁ exigir igualdad de resultados entre dos copias
  verificadas, volver a comprobar su conjunto/identidad y publicar exclusivamente
  después de cerrar establemente todas las lecturas privadas.
- **RL07:** CUANDO informe coincidencias, DEBERÁ publicar solo hashes, IDs, offsets
  dentro del recurso, tamaños, conteos y estados. DEBERÁ omitir bytes, GPR, direcciones
  de RAM y nombres originales; `resource_links`/`capabilities` permanecerán vacíos.
- **RL08:** CUANDO no haya hits, DEBERÁ limitar la conclusión a esas muestras y al
  catálogo aceptado; no descartar datos transformados/generados, otros offsets,
  mapeos TLB o XBG0/AFS. Una coincidencia tampoco DEBERÁ acreditar origen ni semántica.

## Diseño y decisiones

Se amplía el lector ZIP compartido para permitir miembros explícitos acotados. El
lector de CPU anterior sigue leyendo solo dos miembros. `state_memory` comprueba el
estado y selecciona muestras; `state_files` conserva I/O/custodia mediante una función
de decodificación inyectada. `resource_match` busca en streams; un adaptador reutiliza
la custodia de `VerifiedPrivateReader`. `resource_link` compone entradas, resultados
y publicación, sin cambios al runtime, parser MFA ni contrato CO histórico.

El offset físico se toma igual al valor bajo del GPR exclusivamente en el rango
directo bajo. Esta es una **hipótesis explícita**: no se decodifica el TLB del estado
ni se prueba que una página de datos conserve el mapeo inicial. PCSX2 v2.8.2 guarda
`eeMem->Main` en `eeMemory.bin`; su tamaño normal es 32 MiB y su mapeo inicial bajo
es directo. Referencias primarias GPL-3.0+, consultadas como hechos, sin copiar código:
[SaveState.cpp](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/SaveState.cpp),
[MemoryTypes.h](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/MemoryTypes.h),
[Memory.cpp](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/Memory.cpp).

Se conserva en memoria un archivo de estado ≤64 MiB y un miembro RAM ≤32 MiB por vez;
no se extrae RAM al disco. Las muestras son privadas y el procesamiento de recursos
usa bloques de 1 MiB más solapamiento ≤255 bytes. No se busca dentro de la ISO ni en
contenedores fuera del catálogo. Cada copia se verifica entera, no solo sus hits.

La selección v1 es declarativa: entrada A/GPR4 y entrada/retorno de B1/B2/GPR16,
con prefijos de 64 y 256 bytes. No usar GPR4 de retorno de A como el mismo argumento.
Dos patrones con bytes iguales conservan sus puntos/contextos separados. Una búsqueda
exacta negativa no identifica compresión, estructura dinámica ni transformación.

## Tareas y aceptación

1. Implementar miembro RAM acotado y selección de muestra (RL01–RL03).
2. Implementar búsqueda streaming y adaptador privado, conservando lectores previos
   y controles de estabilidad hasta cierre (RL04–RL06).
3. Coordinar evidencia fijada, revalidación CO/catálogo, dos copias y reporte sin
   valores privados (RL01/RL06–RL08).
4. Fixtures propios: identidades alteradas, PC/GPR, alias/límites, CRC, RAM de tamaño
   incorrecto, coincidencias solapadas/entre bloques, duplicados, cap, hash/lectura/
   cierre fallidos y discrepancia entre copias. Regresión/cobertura/Ruff/CI existentes.
5. Ejecutar sobre estados/catálogo reales, repetir en salida nueva, registrar fuente,
   hashes y alcance. Publicar antes de correr custodia, sin operaciones concurrentes.
6. Si aparecen candidatos, definir prueba de carga/escritor; si no, registrar un
   experimento negativo y precisar siguiente observación. F02.07/Q05/G02 siguen abiertos.

## Evidencia del experimento

Los pasos 1–5 están completados: 66 pruebas nuevas, 1.583 pruebas de regresión y dos
informes finales idénticos. Diez muestras, seis hits sobre un único candidato de
1.536 bytes. El paso 6 continúa como investigación de origen; no hay vínculo confirmado.
[Resultado y siguiente observación](../docs/execution/f02-07-camera-resource-link.md).
