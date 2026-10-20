# F02.07 — Vínculo de páginas de caché con archivos (SRC95)

Fecha: 2026-10-19. Completa **NP-T1–3** bajo
[NP01–NP10](../../schemas/native-page-binding-v1.md), tras
[SRC94](f02-07-native-inventory.md). Resuelve el vínculo puntual que faltaba:
la consulta de páginas permite relacionar páginas de caché con archivos retenidos,
aun cuando la consulta de regiones devuelve objetos intermedios distintos.
IP-NATIVE2c2 sigue abierto por integridad y cobertura completa de la caché.

## Implementación y alcance

`PageBinding` depende de dos puertos: referencia de archivo y consulta de página.
Compara dos lecturas de cada uno, terminando con la referencia de archivo.
Exige objeto VM no nulo, página residente/externa y ausencia de indicadores de
modificación. La referencia debe estar en offset cero y el offset objetivo dentro
del archivo. Cambios de inode, metadata, objeto VM u offset descartan la instancia;
los fallos conservan su primera causa y borran la salida.

`MacOSPageAnchor` resuelve componentes con openat/O_NOFOLLOW, retiene descriptor
y mapping compartido de solo lectura y verifica la resolución actual y metadata
antes/después. `MacOSPageSource` lee un byte del proceso propio para resolver la
residencia y consulta mach_vm_page_info; descarta el byte. Exige respuesta completa
y el mismo PID propietario. Las interfaces internas para simular errores siguen
el patrón del adaptador de nacimiento; el cliente no puede seleccionarlas.

El diseño separa política, propiedad de recursos y APIs del sistema. No se cambia
InventoryGuard ni se incorpora automáticamente esta evidencia al proveedor.
La clave VM es opaca y temporal; no es un inode ni un hash criptográfico. Una
página vinculada no acredita otras páginas del mismo segmento ni los bytes del
archivo completo. Tampoco autoriza lectura de memoria del juego.

La [implementación publicada de XNU](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/vm_map.c#L19755)
recorre shadows al consultar páginas y devuelve identidad/offset del objeto
encontrado. Se usa como referencia de diseño, sin afirmar que esa revisión sea
el kernel instalado. Los resultados de este host se verifican por separado.

## Pruebas y pipeline

La versión final pasó **144 escenarios × cuatro modalidades = 576 ejecuciones**:
Debug, Release, ASan/UBSan y cobertura. Conserva los 119 escenarios anteriores y
añade quince portables y diez macOS. Los casos nativos prueban archivo original,
offset no alineado, copia de iguales bytes, reemplazo de ruta, unlink/restauración,
COW/restauración de bytes, página inaccesible, symlinks/componentes inválidos y
rechazo de ancla/consulta heredadas mediante fork.

Los dobles comprueban estados de página inválidos, cambios entre lecturas y contra
la primera muestra, errores de copia/consulta, respuesta corta/larga, PID cambiado
y funciones ausentes. No se fuerza agotamiento de descriptores ni todas las
condiciones internas del kernel. La primera etapa conserva 143 escenarios por
modalidad; una segunda añade los controles de API sin modificar ese snapshot.

Cuatro regresiones compiladas fueron detectadas: omitir igualdad de objeto VM,
aceptar páginas modificadas, omitir continuidad e ignorar tamaño de respuesta Mach.
Las tres primeras usan la fuente del núcleo conservada en ambas etapas; la cuarta
prueba el adaptador final. LLVM registra 100 % de líneas y ramas en el núcleo;
98,63 % de líneas y 84,31 % de ramas en el adaptador macOS final.

El pipeline host incorpora los nuevos targets mediante CMake. Plataforma local:
Apple Clang 21, SDK MacOSX26.5 y ejecutables x86_64 sobre macOS 26.5. ASan/UBSan
interrumpen ante errores; detección de fugas desactivada. No se ejecutó CI remoto,
Linux ni arm64 en esta unidad.

## Caché real observada

Una sonda preliminar consulta el proceso propio con dyld versión 17 y 45 imágenes.
El identificador de la página de cabecera de caché coincide con el del archivo
abierto, con offset cero; sus profundidades son distintas y no se comparan como
identidad. Esto aporta el vínculo que la consulta de regiones de SRC94 no obtenía.

La sonda con el adaptador abre catorce archivos observados: caché x86_64 principal,
seis subcachés y siete archivos aot_shared_cache. Conserva cada descriptor y una
referencia mapeada; no copia esos archivos ni calcula sus hashes completos.

La versión final, tanto Release como ASan/UBSan, verifica **74 puntos por ejecución**:
dos bases de caché/AOT, 44 cabeceras de bibliotecas y 28 inicios de regiones del
submapa del sistema. Cada punto se verifica con dos muestras completas del vínculo.
Las catorce partes tienen puntos observados. LibRosetta se vincula a la subcaché
x86_64 .06. Los mappings de referencia creados por la sonda están fuera del rango
explorado y en profundidad cero; no se cuentan como mappings de caché cargada.

Release observa 45 imágenes: excluye su ejecutable y relaciona las otras 44.
ASan observa 46: relaciona esas mismas 44 y conserva una imagen adicional sin
clasificar dentro de las cachés. No se presenta ninguna ejecución como inventario
completo acreditado. Los 28 inicios de región no cubren todas sus páginas o rangos.

El primer intento explora desde dirección cero. Release termina; ASan agota el
límite de 4096 regiones y sale con código 12. Se conserva como rechazo por límite,
sin promoverlo a éxito. Un segundo intento comienza en la menor base de caché/AOT
obtenida por TASK_DYLD_INFO, mantiene el mismo límite y termina en ambas modalidades.
La versión final del adaptador repite ese diagnóstico en otra carpeta preservada.

## Custodia y continuación

Los 50 comandos supervisados incluyen builds, tests, sondas, cobertura y negativos.
Mantienen reserva/floor de 10 GiB, máximo de etapa de 512 MiB y límites temporales.
Dos etapas conservan snapshots de 31 fuentes propias y sus resultados. Se verifican
por hash las etapas y sondas de SRC94, sus scripts, las 2966 fuentes privadas de
PCSX2 y los 42 binarios del candidato. CMake raíz y CI anterior conservan sus hashes;
el CMake host añade los targets. Dos auditorías idénticas preceden a la publicación.

**Siguiente IP-NATIVE2c2:** definir la política de integridad de los archivos de
caché y la cobertura requerida de rangos/imágenes, usando este vínculo de página.
La política debe tratar subcachés y AOT explícitamente, validar cambios/ausencia y
encajar en el inventario completo antes de IP-NATIVE3. Los archivos superan los
límites NM del bundle; esos límites no se aumentan en esta unidad.

No se modifica PCSX2, su candidato ni el perfil productivo. No se ejecutan ISO,
BIOS o VM ni se produce una captura. Admisión y capacidades permanecen vacías.
