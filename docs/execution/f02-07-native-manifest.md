# F02.07 — Hashes desde descriptores y manifiesto (SRC93)

Fecha: 2026-10-18. Completa **IP-NATIVE2c1 / NM-T1–3** bajo
[NM01–NM10](../../schemas/native-artifact-manifest-v1.md), tras
[SRC92](f02-07-native-images.md). IP-NATIVE2c sigue abierto por caché del sistema,
composición con mappings y observación coordinada del inventario completo.

## Implementación

`AnchoredDigest` separa identidad, lectura de bytes y algoritmo. Lee bloques de
64 KiB desde el descriptor retenido, exige tamaño y EOF coherentes y comprueba
identidad antes/después. Hash, objeto o lectura cambiados descartan la instancia.
No se calcula un hash reabriendo una ruta independiente del archivo anclado.

`ManifestGuard` posee su configuración y exige nombres relativos normalizados,
ordenados y únicos, tamaños y SHA-256 esperados. Límites: 256 archivos, 256 MiB
por archivo y 512 MiB en total; rechaza entradas vacías, inválidas y digest cero
antes de consultar la fuente. Verifica todos los archivos en dos pasadas y compara
identidad y bytes con su primera verificación. Mantiene fallo terminal y salida
vacía aun cuando se restauren ruta, contenido o disponibilidad.

`MacOSArtifactFiles` retiene una raíz y descriptores propios; resuelve mediante
openat y rechaza symlinks en todos los componentes, incluida la raíz absoluta.
Contrasta la resolución actual con los objetos retenidos. Usa pread y CommonCrypto
SHA-256, sin cambiar offsets compartidos ni implementar el algoritmo criptográfico.
Las sustituciones de raíz, directorio y archivo también quedan descartadas.

No enumera archivos adicionales que no estén en el manifiesto ni prueba que los
archivos declarados estén cargados. La composición pendiente debe cubrir cada
imagen cargada y rechazar las externas sin evidencia. Las comprobaciones de
metadata y hash no son exclusión de escritores ni una defensa contra código
malicioso dentro del propio proveedor.

## Pruebas y candidato existente

Se ejecutaron **89 escenarios × cuatro modalidades = 356 ejecuciones correctas**
en Debug, Release, ASan/UBSan y cobertura. Se mantienen los 48 escenarios de SRC92
y se añaden 23 portables y 18 macOS. Los tests conservan sus comprobaciones en
Release y CTest limita cada caso a quince segundos. Sanitizadores interrumpen
ante error; no se habilitó detección de fugas.

Las pruebas reales verifican SHA-256 de vacío y `abc`, y un archivo con un millón
de letras `a` mediante valores esperados independientes. Cubren bloques/EOF,
symlinks en archivo/directorio/raíz, ruta ausente, directorio en lugar de archivo,
archivo vacío, reemplazo con bytes iguales/distintos, cambio de raíz y escritura
durante la lectura. Las respuestas cortas, sobredimensionadas y fallidas usan
un doble de pread; los fallos del algoritmo y del puerto usan dobles portables.

El verificador propio contrastó **42 binarios del candidato SRC88**, utilizando
los hashes previamente custodiados en SRC89. Confirmó esos hashes antes de fijar
los tamaños del manifiesto de prueba. Ejecutó dos verificaciones por modalidad
en Release y ASan/UBSan: ocho pasadas completas en total. Volvió a comprobar los
hashes al terminar. **No ejecutó PCSX2** ni cambió ese candidato.

Cuatro regresiones compiladas fueron detectadas: omitir el hash esperado, ignorar
EOF adicional, omitir continuidad con el objeto inicial y seguir symlinks al abrir
componentes. Los tres primeros son controles del núcleo; el cuarto usa filesystem
real con el adaptador modificado solo en una copia privada del control negativo.

LLVM mide 100 % de líneas y 97,46 % de ramas en el núcleo nuevo; 99,17 % de líneas
y 81,58 % de ramas en el adaptador macOS. No se fuerza agotamiento de descriptores,
fallos internos de CommonCrypto ni todos los errores del kernel. El pipeline host
existente incorpora los nuevos targets mediante CMake; no se ejecutó CI remoto
ni Linux en esta unidad. Plataforma local: Apple Clang 21.0.0, SDK MacOSX26.5 y
ejecutables x86_64 sobre macOS 26.5.

## Investigación de caché y límite pendiente

La primera sonda consulta TASK_DYLD_INFO del proceso propio y copia 368 bytes con
mach_vm_read_overwrite. Obtiene versión 17. Rechaza con código 2 el requisito de
versión 18 para sharedCacheFSID/sharedCacheFSObjID; su fuente, binario, log y
recibo fallido se conservan. No se modifica ni repite esa sonda.

La segunda sonda confirma `file_ids_supported=0`, pero su diagnóstico aún imprime
los campos que corresponden a padding en versión 17; esos ceros no son evidencia
de identidades ausentes. Se conserva y se reemplaza por una tercera sonda que
omite esos campos salvo versión >=18. La sonda final observa UUID/base, slide y
metadatos AOT válidos en versión 17. El resultado no acredita archivos de caché,
subcachés ni las imágenes traducidas por Rosetta.

El SDK local documenta los campos de identidad de archivo desde versión 18.
La [descripción de Apple](https://github.com/apple-oss-distributions/dyld/blob/main/doc/CacheLayout.md)
explica que una caché puede distribuirse en varios archivos y mappings. Es una
referencia de diseño; no demuestra que esa revisión de fuente sea la instalada.
No se publica código de Apple ni se adopta una allowlist de rutas/UUID para
sustituir la evidencia ausente.

## Custodia y siguiente tarea

Una etapa nueva conserva fuentes, cuatro builds, perfiles, fixtures y controles
negativos. Tres etapas adicionales conservan las sondas de caché. La supervisión
mantiene reserva/floor de 10 GiB y límite de etapa de 512 MiB. El candidato previo,
la fuente privada pine-transport v2 y las etapas de SRC92 se contrastan por hash.
El CMake anterior se conserva en el snapshot de SRC92; CMake raíz y CI anterior
no cambian. Dos auditorías deben producir evidencia idéntica antes de publicarla.

**Siguiente IP-NATIVE2c2:** investigar una fuente acreditable de identidad de
caché para el entorno x86_64/Rosetta observado, con subcachés y AOT explícitos;
después componer manifiesto, objetos, mappings, nacimiento y revisión del cargador
en una lectura estable. Una imagen sin evidencia descarta el inventario entero.
IP-NATIVE3 integrará ese resultado en una nueva copia del proveedor y comprobará
el peer. No hubo ISO, BIOS, VM, captura ni lectura de RAM del juego; admisión y
capacidades siguen vacías.
