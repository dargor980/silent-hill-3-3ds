# Vinculación de cabeceras Mach-O thin/universal — MS v1 y PT v2

Historia: como investigador necesito demostrar qué slice de un archivo contiene
la cabecera cargada, sin atribuir membresía de plataforma a una biblioteca externa
ni aceptar un offset únicamente por su nombre. Detalla PO-T3b de SRC102.

## Requisitos EARS

- **MS01:** CUANDO lea un archivo, DEBERÁ aceptar solo Mach-O thin de 64 bits
  little endian o contenedores FAT32/FAT64 canónicos big endian, con 1–32 entradas
  y tamaño máximo 256 MiB. Magias/endianidades no admitidas DEBERÁN rechazarse.
- **MS02:** CUANDO recorra FAT, DEBERÁ validar todas las entradas y cabeceras:
  límites, tamaño mínimo, alineación, reserved de FAT64 cero, ausencia de
  solapamientos con tabla/otras entradas y unicidad exacta de CPU/subtipo.
  La cabecera thin DEBERÁ coincidir con CPU/subtipo de su entrada.
- **MS03:** CUANDO seleccione, DEBERÁ coincidir exactamente CPU, subtipo completo
  y offset esperados. SHALL NOT aplicar preferencias por CPU, máscaras de subtipo
  ni elegir la primera coincidencia ambigua. CPU admitidas: x86_64 y arm64; tipos
  thin admitidos: executable, dylib y bundle. Límites de comandos: 1 MiB y
  cantidades coherentes con el tamaño de la cabecera/slice.
- **MS04:** CUANDO adquiera metadata, DEBERÁ hacer dos lecturas completas de la
  tabla y todas las cabeceras, compararlas y rechazar cambios/lecturas parciales.
  DEBERÁ usar memoria fija y consultas acotadas, sin leer payloads de segmentos.
- **MS05:** CUANDO vincule un mapping, DEBERÁ exigir inicio exacto de cabecera,
  rango válido de al menos 32 bytes y archivo regular coincidente por identidad
  antes/después. El offset del kernel y CPU/subtipo de la cabecera residente
  DEBERÁN seleccionar un único slice; sus 32 bytes DEBERÁN coincidir con el archivo
  y una segunda lectura residente. Error DEBERÁ vaciar la salida.
- **MS06:** CUANDO el adaptador nativo abra una ruta del loader, DEBERÁ tratarla
  solo como localizador, usar descriptor retenido y verificar identidad frente
  al vnode; repetir vnode/PID al terminar. Error, sustitución, unlink, PID ajeno
  o archivo inaccesible DEBERÁN invalidar la instancia sin reintento ni fallback.
- **MS07:** CUANDO el perfil `macos_platform_slices_v2` clasifique aplicación,
  DEBERÁ exigir testigo de slice válido, conservar el offset real y vincular el
  archivo completo con el manifiesto. PT v1 SHALL NOT aceptar testigos de slice
  ni offsets no cero. Ninguna rama de caché DEBERÁ contener un testigo de slice.
- **MS08:** CUANDO PT v2 calcule hashes, DEBERÁ usar dominios v2 e incluir formato,
  offset, tamaño y cabecera completa del slice. Cambios de esos campos DEBERÁN
  detectarse entre pasadas/muestras; mezclar perfiles SHALL NOT conservar hashes.
- **MS09:** CUANDO se valide, DEBERÁ cubrir límites/overflow/solapamiento,
  arquitecturas ambiguas/endianidad, fallos parciales, sustitución, COW y fork,
  versiones cruzadas y vectores independientes. DEBERÁ ejecutar el candidato
  con testconfig y dos pasadas completas en arranque/salida, conservando fallos.

## Diseño y alcance

`select_macho_slice(ByteSource, size, SliceRequest)` analiza metadata y devuelve
`MachSlice`; `bind_macho_slice` compone bytes residentes, descriptor de archivo
y mapping. Un puerto `SliceBindingSource` entrega esa asociación. El adaptador
`MacOSSliceMappings` reutiliza vnode, `MacOSPageAnchor` y `MacOSImageBytes`;
una ruta o un FileObject aislados no sustituyen la comparación de bytes.

CPU/subtipo esperados por el parser son argumentos exactos. En el adaptador se
obtienen de la cabecera residente y se contrastan con el archivo en el offset
del kernel. Esto vincula metadata; no autoriza ese archivo: PT-T4 todavía deberá
fijar el manifiesto y las identidades de evidencia desde el lanzador.

`MacOSPlatformOrigins` mantiene su constructor con `MappingSource` para PO/PT v1
y agrega otro que recibe `SliceBindingSource`. Solo este último produce testigos
de slice. `PlatformInventoryGuard` recibe perfil 1 o 2 explícitamente. No cambia
el protocolo productivo, el inventario exhaustivo NC/CI ni las puertas de captura.

PT v2 mantiene las reglas de PT01–10 salvo la extensión declarada de PT03 y los
dominios de PT07. Codificación: mismos campos canónicos de PT v1, con dominios
`SH3:platform-files:v2` y `SH3:platform-images:v2`, perfil u64=2. Tras cada registro
de aplicación (tamaño, offset e índice u64), añade formato u64 (thin=1,FAT32=2,
FAT64=3), offset u64, tamaño u64 y los 32 bytes de cabecera. No cambia la rama
de caché. No hay conversiones implícitas al resultado de NC.

Se verifica únicamente la cabecera, no comandos/segmentos completos, firma,
payload, páginas transformadas ni fixups. Los límites de comandos comprobados
son estructurales. El manifiesto posterior deberá acreditar el archivo completo.
No se afirma instantaneidad, exclusión ABA ni resistencia a código arbitrario
que corrompa el proceso confiable. El kernel/dyld/Rosetta siguen asumidos.

## Tareas

- [x] **MS-T1 / MS01–05:** parser portable, comparación de catálogos y binder de
  cabecera con puertos de lectura/identidad; pruebas independientes y límites.
- [x] **MS-T2 / MS06–08:** adaptador nativo y perfil explícito PT v2; conservar
  semántica/vectores v1, probar archivos reales, errores y versiones cruzadas.
- [x] **MS-T3 / MS09:** cuatro builds, sanitizadores, cobertura y negativos;
  testconfig en nueva copia privada, clasificar todo el ledger dos veces en
  inicio/salida, registrar slices externos y verificar hashes de la copia.
  Cierre habilita PT-T4 (manifiesto/costes); captura y peer siguen pendientes.
