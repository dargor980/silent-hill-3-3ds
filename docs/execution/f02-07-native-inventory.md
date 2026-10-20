# F02.07 — Composición del inventario y caché (SRC94)

Fecha: 2026-10-18. Completa **NC-T1–3** bajo
[NC01–NC10](../../schemas/native-inventory-v1.md), continuando
[SRC93](f02-07-native-manifest.md). IP-NATIVE2c2 sigue abierto: la composición
está implementada para imágenes respaldadas por archivos declarados, pero falta
acreditar caché, subcachés y AOT del host para cubrir el proceso completo.

## Composición implementada

`InventoryGuard` combina ProcessBirth, ManifestGuard, las revisiones del cargador,
MappingSource y DigestEngine. Cada servicio mantiene su responsabilidad y los
puertos se inyectan; el núcleo no depende de APIs de macOS o del transporte.
Obtiene nacimiento/inventario iniciales, verifica el manifiesto, lee dos veces
todos los mappings y vuelve a verificar manifiesto, inventario y nacimiento.
El cierre del cargador ocurre después del cálculo de hashes.

Cada cabecera debe corresponder inequívocamente a un objeto verificado del
manifiesto. Rechaza imágenes desconocidas, duplicados, capacidad excedida,
revisiones inválidas y aliases de dispositivo/inodo. No exige que todos los
archivos del manifiesto estén cargados; sí exige cobertura de todas las imágenes
enumeradas. Una carga/descarga invalida aunque restaure el conjunto anterior.

Los digests de objetos e imágenes usan dominios diferentes, campos little endian
y orden explícito. No dependen de padding de structs, rutas absolutas ni del orden
de enumeración. El resultado conserva PID/nacimiento/nonce, revisión y cantidad.
Ante fallo conserva la primera causa, borra toda salida y deja de consultar los
puertos, incluso si se restablece la condición original.

La evidencia del mapping sigue limitada a la región de cabecera de NI. Esta
composición no verifica todos los segmentos ni igualdad de memoria con disco,
no suspende escritores y todavía no genera la Observation completa de IP con
épocas/generaciones ni comprueba el peer del transporte.

## Validación

La versión final ejecutó **119 escenarios × cuatro modalidades = 476 ejecuciones
correctas** en Debug, Release, ASan/UBSan y cobertura. Conserva los 89 escenarios
anteriores y añade 24 portables y seis macOS. CTest mantiene quince segundos por
escenario. Sanitizadores terminan ante error; la detección de fugas está desactivada.

Los dobles portables cubren fallos en cada lectura, manifiesto cambiado, mapping
alterado entre pasadas, revisión cambiada, retorno del conjunto a sus direcciones
previas, capacidad 256/257, digest fallido/cero, configuración ausente y terminales.
Las pruebas macOS componen nacimiento, descriptores, hashes y mappings reales de
una biblioteca de prueba. Comprueban reemplazo por otro archivo con los mismos
bytes y una carga/descarga real entre muestras o durante el cálculo de hashes.

Los casos positivos macOS proyectan **solo la fixture** mediante un puerto de
prueba y conservan la revisión del cargador real. No acreditan todo el proceso.
Un caso separado usa la enumeración completa y comprueba el rechazo: su manifiesto
de fixture no cubre el ejecutable y las dependencias del sistema. La observación
rechazada no contiene identidad ni digests parciales aprovechables.

Un vector codificado independientemente con `struct.pack('<Q')` y `hashlib` en
Python coincide con ambos hashes calculados en C++ mediante CommonCrypto.
Tres regresiones compiladas fueron detectadas: ignorar revisión, omitir comparación
entre pasadas de mappings e ignorar continuidad con la primera muestra.

LLVM registra **100 % de líneas y 92,07 % de ramas** en inventory.cpp. Se conserva
la cobertura anterior de los seis componentes usados. El pipeline host existente
recoge los nuevos targets CMake; no se ejecutó CI remoto, Linux o arm64 en esta
unidad. Host local: Apple Clang 21, SDK MacOSX26.5, binarios x86_64.

La primera etapa conserva 116 escenarios por modalidad, todos correctos. Mientras
terminaba se añadieron tres casos de frontera/cierre al workspace; su comprobación
final de igualdad con el snapshot rechazó esa diferencia. Se conservó la etapa
intacta y se ejecutó una segunda completa con las fuentes finales. No se presenta
el cierre fallido de la primera como validación de la versión final.

## Sondas de caché

La primera sonda resuelve ocho funciones SPI de introspección publicadas por Apple
y presentes en libdyld local. Obtiene UUID/base y siete rutas de caché; abre los
archivos solo para consultar metadata y mapear 4 KiB. La llamada de introspección
deja **344 imágenes cargadas** en la sonda. El diagnóstico solo imprime 256: no es
un inventario completo y excede la capacidad actual del ledger.

Su recorrido de submapas también contiene un error: después de entrar en un
submapa reutiliza la dirección inicial de la región, en vez de la dirección
objetivo. Se conserva fuente, binario, log y recibos; los objetos resultantes de
esa primera consulta no se usan como evidencia de mappings.

La segunda sonda usa TASK_DYLD_INFO y mach_vm_region_recurse sin la introspección
privada y restablece la dirección objetivo al descender. Observa dyld versión 17
y 45 imágenes. Mantiene simultáneamente catorce mappings de 4 KiB: MAP_PRIVATE
y MAP_SHARED de los siete archivos de caché. Los objetos de las regiones cargadas
de caché/AOT tienen profundidad de shadow 2 y **no coinciden** con esos mappings
de archivos. Este resultado no acredita un vínculo archivo→caché cargada.

Las [declaraciones de Apple](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/include/mach-o/dyld_introspection.h)
y su [implementación publicada](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld_introspection/dyld_introspection.cpp)
sirven como referencia de API, no prueban la revisión instalada. Las funciones de
contenido pueden materializar datos de disco; no sustituyen una lectura del mapping
vivo. Ninguna SPI se incorpora al núcleo ni al proveedor de PCSX2. No se copian
headers o implementaciones de Apple al repositorio.

Los archivos de caché examinados superan individualmente el límite de 256 MiB de
NM. No se cambian esos límites, no se calculan hashes de varios GiB y no se usa
una allowlist de rutas/UUID para declarar la caché acreditada.

## Custodia y siguiente trabajo

Dos etapas preservan snapshots de 25 fuentes propias, builds, fixtures y perfiles;
otras dos conservan las sondas. Los comandos están supervisados con reserva/floor
de 10 GiB y máximo de etapa de 512 MiB. Se verifican la etapa y sondas de SRC93,
los scripts anteriores, la fuente privada PCSX2 y los 42 binarios del candidato
por sus hashes. El cambio de CMake host solo añade targets; CMake raíz y CI anterior
conservan sus hashes. Dos auditorías idénticas preceden a la publicación.

**Siguiente dependencia: IP-NATIVE2c2, caché/subcachés/AOT.** El SPI ensayado aporta
ubicaciones, pero añade dependencias y no proporciona la prueba requerida. La vía
de objetos de VM ensayada tampoco vincula los archivos; falta resolver el origen
de sus shadows o establecer otra fuente verificable sin debilitar NI/NM/IP.
Después podrá integrarse la composición en IP-NATIVE3 y comprobar el peer.

No se ejecutó PCSX2, ISO, BIOS o VM ni se produjo captura o lectura de RAM del juego.
El candidato previo y el perfil productivo permanecen intactos. Admisión y
capacidades continúan vacías; estas pruebas no representan ejecución del port.
