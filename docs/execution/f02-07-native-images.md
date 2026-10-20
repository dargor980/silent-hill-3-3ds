# F02.07 — Mappings y eventos del cargador (SRC92)

Fecha: 2026-10-18. Desarrolla **IP-NATIVE2a/2b y NI-T1–3** bajo
[NI01–NI11](../../schemas/native-image-identity-v1.md), después de
[SRC91](f02-07-native-birth.md). **IP-NATIVE2 completo permanece abierto**:
faltan manifiesto/digests y acreditación de las imágenes de la caché del sistema.

## Qué se implementó

`ImageBinding` separa lectura de identidad de archivo y consulta de mapping.
Compara dispositivo, inodo, tamaño, mtime/ctime y región en dos lecturas; conserva
la identidad inicial e invalida permanentemente ante error, pérdida o cambio.
La salida fallida queda vacía. `MacOSFileAnchor` mantiene un descriptor abierto
y contrasta fstat/lstat contra el objeto inicial. `MacOSMappingSource` consulta
PROC_PIDREGIONPATHINFO para el proceso propio, valida respuesta completa y PID
estable y exige un vnode regular con región válida y offset cero.

El resultado acredita el objeto que respalda la **región de la cabecera**, dentro
del perfil inicial de Mach-O delgado. No verifica todos los segmentos ni compara
bytes de memoria con el disco. No es aún una vinculación con artefacto aprobado:
un manifiesto y el hash desde el descriptor se incorporarán en la siguiente parte.

`ImageLedger` mantiene hasta 256 direcciones y una revisión monotónica. El
adaptador macOS registra callbacks de dyld y conserva el registro durante toda
la vida del proceso. Copia los datos bajo mutex, sin dereferenciar imágenes ni
consultar dyld con el mutex tomado. Rechaza duplicados, descargas desconocidas,
agotamiento, dirección nula y registro heredado por fork. No reinicia la revisión
cuando el conjunto de imágenes vuelve a coincidir.

## Comprobaciones reales y dobles

Las pruebas locales usan Apple Clang 21.0.0, SDK MacOSX26.5 y ejecutables **x86_64**
sobre macOS 26.5; el inventario observado incluye libRosetta. No se afirma una
ejecución arm64 nativa ni CI remoto.

- Vínculo estable de la cabecera del ejecutable propio y una biblioteca propia.
- Sustitución por rename con una copia de los mismos bytes y con otra biblioteca:
  el kernel sigue identificando el inodo antiguo del mapping, mientras la ruta
  resuelve al nuevo. Se rechaza el ancla anterior y el vínculo con el archivo nuevo.
- Pérdida de ruta y restauración posterior: el rechazo anterior continúa terminal.
- Rechazo de directorio, archivo vacío, symlink final, ruta ausente/relativa y
  cambio de tamaño de un archivo anclado.
- Nueva dependencia, descarga y recarga: el conjunto original vuelve, con cuatro
  revisiones adicionales. Cuarenta ciclos desde otro hilo producen ochenta eventos
  mientras el hilo principal consulta snapshots coherentes.
- fork heredado: el hijo rechaza antes de bloquear; el padre conserva la revisión.

Los dobles prueban respuesta fallida/corta, PID cambiado, vnode/campos inválidos,
región posterior, offset distinto de cero, overflow y funciones ausentes. El
núcleo prueba comparaciones, cambios persistentes/transitorios, terminales,
capacidad y agotamiento. Los fallos del kernel y de pthread no se provocan en el
sistema; no se declara cobertura exhaustiva de esos componentes.

## Caché del sistema: límite comprobado

La sonda inicial obtuvo un vnode válido para su ejecutable. Para las bibliotecas
que dyld clasifica dentro de la caché compartida, PROC_PIDREGIONPATHINFO devolvió
dispositivo/inodo cero y ruta vacía. Se conservan sus resultados privados. Una
prueba comprueba que el adaptador rechaza esa ausencia de evidencia.

La clasificación `_dyld_shared_cache_contains_path` se usa únicamente como testigo
de esa limitación. No aprueba imágenes por prefijo /usr/lib o /System, no acepta
el nombre como evidencia de mapping y no presenta una lectura parcial como
inventario acreditado. **IP-NATIVE2c** deberá definir y comprobar identidad de
caché y política del host, además del manifiesto y digests de archivos propios.

## Validación y custodia

La suite final contiene **48 escenarios por modalidad**, incluidos los 22 de
nacimiento previos: 192 ejecuciones en Debug, Release, ASan/UBSan y cobertura.
Son 26 escenarios nuevos (15 portables y 11 macOS). Las aserciones permanecen
activas en Release; ASan/UBSan interrumpe ante error, sin detección de fugas.

Se preservan dos etapas completas. La segunda añade garantías de compilación
para registro sin destructor y atómicos lock-free, y carpetas únicas para repetir
las fixtures sin sobrescribir resultados anteriores. Tres mutantes compilados
eliminan respectivamente la comparación inicial, el rechazo terminal y el avance
de revisión; la batería debe detectar los tres.

LLVM mide 100 % de líneas y 94,55 % de ramas en el núcleo nuevo; 96,30 % de
líneas y 80 % de ramas en el adaptador macOS. Las dos fuentes de nacimiento
conservan 100 % de líneas/ramas. Los errores de once/mutex y algunas carreras
de syscalls no se fuerzan; estos porcentajes no acreditan cobertura del kernel.
El workflow host existente incluye automáticamente los
targets nuevos por CMake: núcleo en Linux/macOS, adaptadores solo en macOS.
No se ejecutó Linux ni el workflow remoto. El CMake raíz y CI anterior se conservan.

Se conserva el CMake de SRC91 en su snapshot privado con el hash histórico; el
CMake host actual se amplía. Las otras entradas públicas de SRC91, sus scripts,
la fuente privada pine-transport v2 y el candidato SRC88 se vuelven a contrastar.
Etapas limitadas a 512 MiB, reserva/floor de 10 GiB, CTest de 15 segundos por caso
y procesos supervisados. Este incremento pequeño no requiere compilar PCSX2.

No hubo ISO, BIOS, VM ni lectura de RAM. No se produjo Observation completa,
no se modificó el perfil AP ni se habilitaron admisión o capacidades. Quedan
pendientes IP-NATIVE2c, integración/peer IP-NATIVE3 y los gates de VIF/escritores,
frontend/VM y AD-3.
