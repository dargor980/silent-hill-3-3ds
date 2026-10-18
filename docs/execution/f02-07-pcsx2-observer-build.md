# F02.07 — Build y validación del observador PCSX2

Unidad: `origin/effective-mapping/instrumented-build/build-and-validate`.
Fecha: 2026-10-18. Estado: **build y transporte aceptados; captura del juego pendiente**.
Contrato [OBT01–OBT07](../../schemas/pcsx2-observer-build-v1.md),
[evidencia SRC51](../compatibility/pcsx2-observer-build-evidence.json).

## Build y custodia

Se revalidaron los 2.934 archivos del baseline, los 2.941 de la copia SRC50,
sus siete archivos propios y el prefijo de 5.228 archivos/70 enlaces. El
checkout conserva la revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`.
Los nueve chequeos del toolchain Apple/Metal pasan. CMake genera 814 entradas,
tres propias, con el observador habilitado explícitamente.

Se inventariaron y retiraron 623 objetos `.o` reconstruibles de tests propios
(75,74 MiB), conservando fuentes, ejecutables, logs y recibos. La primera
muestra del build completo acredita 20,0369 GiB libres; no se redujo su
reserva de entrada de 20 GiB. La etapa nueva se limitó a dos jobs, 8 GiB,
suelo de 10 GiB y 45 minutos. El primer enlace completo tardó 335,654 s;
máximo medido durante ese proceso 328,94 MiB, mínimo libre 18,756 GiB.

Se usa Apple Clang 21, SDK macOS 26.5, Metal explícito, x86_64/macOS 11 y
ThinLTO en Apple M2 mediante Rosetta. Compilación y pruebas son locales;
no implican ejecución de la CI remota ni del runtime Nintendo.

Otros fallos conservados de la preparación: un entero de timeout demasiado
grande causó OverflowError en la validación inicial; se cambió a una comparación
de rango y los 45 casos finales pasan. Una escritura de log de símbolos fuera
del workspace fue rechazada por el sandbox y se completó con acceso autorizado.

## Transporte propio y SOLID

[El cliente](../../tools/inspectors/observer_transport.py) posee una conexión
Unix por operación. Recibe exactamente la cabecera y el cuerpo, limita el
reply a 4.333 bytes y aplica un único deadline a conexión, envío y todos los
fragmentos. Cierra en éxito y error; un fallo de cierre invalida la respuesta.
Los errores públicos contienen códigos, sin rutas ni bytes capturados.

Socket y reloj son puertos inyectables. El transporte no interpreta memoria,
no decide si una captura es válida y no publica evidencia. El lector OB
separa esas validaciones; el futuro coordinador será responsable de proceso,
perfil, conexión persistente, estado y custodia. El dominio C++ sigue intacto.

Los 45 tests nuevos cubren fragmentación, EOF, longitudes, timeout total,
creación y cierre fallidos, errores combinados y entradas inválidas. La
regresión completa pasa **2.072 tests Python**. El transporte alcanza
**65/65 líneas y 22/22 ramas**; el total alcanza 98,84 % de líneas y 97,44 %
de ramas, con gate independiente 80/80 aprobado. El job Python existente
recoge estos tests automáticamente; no necesita emulador ni originales.

## Fallo real y corrección

El primer paquete abre el depurador y responde a las pruebas negativas,
pero termina por **SIGPIPE (salida -13)** cuando un cliente envía la petición
y se cierra antes de recibir. El recibo del supervisor confirma el cierre del
grupo; no se cuenta esta ejecución como aceptada.

Se aisló el comportamiento con un programa x86_64 de sockets: configurar
`SO_NOSIGPIPE` antes de cerrar el extremo remoto permite devolver EPIPE;
configurarlo después de ese cierre devuelve EINVAL y una escritura sin
protección termina por SIGPIPE. PINE ignoraba el retorno de `setsockopt`.
La [documentación de Apple](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setsockopt.2.html)
describe la protección por socket; la reproducción local determina el fallo
concreto de esta plataforma.

La revisión privada del parche comprueba ese retorno y cierra/rechaza el
socket antes de cualquier escritura si no pudo protegerlo. Se limita al
build con observador, sin instalar un manejador global de señales. Se
conservan la fuente anterior completa, ambos parches, el primer bundle
original y candidato, y todos los recibos fallidos. La reparación incremental
reutiliza solo la etapa propia identificada, con suelo de 10 GiB y 15 minutos.

## Paquete y validación final

La reparación incremental tarda **79,703 s**, con salida cero y grupo cerrado.
El parche final tiene SHA-256:

`a4072fb169db8376a657b2e8c578d5cb9777ce361678f03cda92ecea205abbd0`

Los dos programas originales pasan **31 + 82 = 113 tests**, tanto antes como
después de la reparación. No se modificaron sus fuentes. El empaquetador
original dejó errores de firma y referencias absolutas: se conservaron esos
bundles y se normalizaron ID/RPATH en candidatos separados. El paquete final
contiene **200 archivos regulares y 42 Mach-O x86_64**, sin dependencias ni
RPATH hacia el prefijo privado/Homebrew, mínimo macOS 11. Firma ad hoc profunda
estricta aprobada y entitlements iguales a los originales. Es un paquete local,
sin notarización. Contiene **37 símbolos del observador**, incluido dispatch.

SHA-256 del ejecutable firmado probado:

`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`

`-testconfig` termina correctamente en 13,714 s con perfil nuevo. PINE usa
un directorio 0700, umask 077 y socket privado del mismo usuario. Los **39
casos reales** verifican estado apagado, respuesta `OBSERVER_PAUSE`, framing,
versión y campos inválidos, deadline del cliente y reconexión. Incluyen
**21 reconexiones después de un cierre temprano**; ninguna termina el proceso.
Los replies negativos se comparan byte a byte, incluidos sus campos vacíos.

El depurador abre en español y responde al seleccionar Puntos de interrupción.
Los controles de ejecución están deshabilitados al no haber VM. Lsof registra
29 archivos cargados desde el bundle, sin prefijo/Homebrew. Con una petición
incompleta esperando respuesta, se cierra mediante la UI: el cliente recibe
EOF, PCSX2 sale con código cero, el grupo queda cerrado y el socket desaparece.
La sesión completa dura 29,619 s; la medición de 4,985 s del cliente incluye
el intervalo hasta la acción manual y no es una latencia de apagado.

La verificación posterior confirma firma, identidad del candidato, fuente,
prefijo, baseline y copias previas intactos. Los artefactos, scripts de
operación y logs privados quedan identificados por hashes en SRC51. Ruff,
formato, contratos del repositorio y gate 80/80 pasan. No se repitieron los
49 tests C++ propios de SRC50 porque el núcleo/adaptador propio no cambió;
la reparación afecta la integración PINE privada y se prueba con el binario real.

## Continuidad

Después corresponde `observer-acquisition-coordinator` (OB07–OB08): importar
ciclo u64 del estado y vincular captura A/guardado nuevo/B en una sola conexión.
Debe comprobar archivo inicialmente ausente, escritura terminada, contenido
estable y RAM/PC/ciclo/CRC/PINE coherentes antes de publicar un recibo atómico.

No se arrancó BIOS ni juego en esta unidad. Las respuestas sin VM son errores
esperados, no capturas de RAM. El timeout del cliente no demuestra el timeout
interno del hilo CPU. Cuatro paradas MP08, relación de recurso, otras escrituras,
dos salas, F02.07, Q05/G02 y pruebas físicas siguen pendientes.
