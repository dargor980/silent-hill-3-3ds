# Silent Hill 3 PS2 → Nintendo 3DS

Proyecto de adaptación nativa con origen PS2 y destino confirmado **New Nintendo 2DS XL**. Estado: F00 completada y G00 aprobada para identificación, alcance y custodia; F01/diagnóstico sintético en curso. Todavía no hay juego portado. La ISO europea del usuario permanece como entrada local ignorada en `binaries`.

- [Especificaciones EARS y backlog](docs/SPEC.md).
- [Alcance M0-M5: primera alpha en español y Normal/Normal](docs/scope.md).
- [Normas SOLID, testing y CI](docs/engineering.md).
- [Cierre de F00 e incógnitas](docs/execution/f00-07-decisions.md).
- [F01.01: ejemplo oficial reproducible, C++17 y pruebas del SDK](docs/execution/f01-01-toolchain.md).
- [F01.02: diagnóstico compilado, contratos y prueba física pendiente](docs/execution/f01-02-diagnostic.md).
- [F01.03: archivos, opciones y errores de I/O](docs/execution/f01-03-files.md).
- [F01.04: tono, errores NDSP y contadores](docs/execution/f01-04-audio.md).
- [F01.05: símbolos, integridad y breakpoints en Azahar](docs/execution/f01-05-debugging.md).
- [F01.06: recursos, ventana acotada y protocolo de métricas](docs/execution/f01-06-resources.md).
- [F01.07: suspensión, reanudación y controles reservados](docs/execution/f01-07-lifecycle.md).
- [F01.08: builds, gates y protocolo de treinta minutos](docs/execution/f01-08-builds.md).
- [F02.01: inventario verificado de 113 archivos ISO](docs/execution/f02-01-inventory.md).
- [Avance y evidencia de la primera ejecución](docs/execution/foundation.md).
- [Política de datos privados](docs/private-data.md).
- [Inventario de fuentes y perfil canónico](docs/compatibility/sources.md).
- [Licencias, procedencia y pendientes de adopción](docs/compatibility/licenses.md).
- [Edición europea identificada e inspección ISO](docs/compatibility/edition-comparison.md).

## Build y pruebas host

Requiere CMake ≥3.21, compilador C++17 y Python ≥3.11. En un entorno Python aislado:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m ruff check tools tests/python
.venv/bin/python -m ruff format --check tools tests/python
.venv/bin/python -m tools.qa.check_repository
.venv/bin/python -m pytest --cov=tools --cov-report=json:build/python-coverage.json --cov-report=term-missing
.venv/bin/python -m tools.qa.coverage_gate build/python-coverage.json
cmake --preset host-debug
cmake --build --preset host-debug --parallel 2
ctest --preset host-debug
```

Todos los presets fallan si no encuentran pruebas y limitan cada caso a 120 segundos, salvo límites específicos menores. Las pruebas Python de automatización requieren CMake/CTest en PATH. Presets adicionales: `host-release`, `host-sanitize` (ASan/UBSan) y `host-coverage` (GCC). Ejecutar `ctest` también en Release: los checks no desaparecen con `NDEBUG`. CTest incluye 67 casos: ocho suites de núcleo/archivos/métricas/smoke, treinta y tres contratos de composición 3DS, cinco del adaptador de audio, uno de recursos, dos del observador host, once de la guardia de continuidad y siete del puente de escrituras físicas. Compila composición y `tone.cpp` reales en targets host separados con dobles del SDK; esos casos no acreditan hardware ni escucha. La cobertura C++ se obtiene con `.venv/bin/python -m gcovr --config gcovr.cfg` tras construir y probar `host-coverage`.

Para identificar el fixture propio, sin ejecutar extracción:

```sh
.venv/bin/python -m tools.pipeline.verify \
  --profile tests/fixtures/synthetic/game-profile.json \
  --data-root tests/fixtures/synthetic
```

## Inspección local de la ISO

El [procedimiento de inspección](docs/execution/europe-iso.md) genera un manifiesto con tamaños y SHA-256 de todos los archivos sin exportarlos. La copia disponible es `SLES-51434`, PAL; `VER=1.02` es el valor de arranque observado. La imagen completa coincide con Redump 1064: versión 1.02 y lista de idiomas en/fr/de/es/it. [F00.02 completada](docs/execution/f00-02-edition-identification.md). El usuario seleccionó español y Normal/Normal para la primera alpha; [F00.04 completada](docs/execution/f00-04-scope.md). Las pruebas de ejecución siguen pendientes.

## Build 3DS aislado

El [chequeo F01.01](docs/execution/f01-01-toolchain.md) construye el ejemplo oficial en dos directorios limpios y verifica C++17 antes del build de CI. Incluye instrucciones para repetirlo montando solo scripts y fixtures propios. F01.02 ya tiene validación local y build identificados; su [prueba física](docs/compatibility/diagnostic-startup.md) sigue pendiente. F01.03 ya incorpora lectura, opciones persistentes y errores de I/O con pruebas locales; F01.04 añade validación de NDSP, PCM, contadores y liberación. F01.05 ya alcanzó breakpoints en Azahar y rechaza símbolos mezclados; conserva pendiente la consola y una anomalía gráfica tras reconectar GDB. F01.06 añade consultas de recursos, SELECT para métricas y protocolo inicial; B_app y entorno físicos siguen pendientes. F01.07 evita entrada durante suspensión, conserva pausa/mute y exige liberar botones al volver. F01.08 verifica el conjunto completo de artefactos, rechaza presets sin tests y conserva reportes/logs. El ensayo físico de treinta minutos y G01 siguen pendientes; F02.01 completó el catálogo ISO con dos informes idénticos y desconocidos explícitos. F02.02 evaluó el candidato MFA y añadió un sondeo propio: dos informes idénticos, B0/MV0 estructuralmente válidos y 60 desconocidos; [evidencia](docs/execution/f02-02-mfa-candidate.md). F02.03 añadió B8 y diagnóstico de nombres: [61 contenedores/1740 entradas estructurales](docs/execution/f02-03-container-variants.md), 493 pruebas; XBG0 conserva codificación pendiente. F02.04 completó [dos catálogos idénticos](docs/execution/f02-04-asset-catalog.md) con IDs, offsets y SHA-256 para 1740 recursos, y 582 pruebas Python aprobadas. Tipos y dependencias semánticas siguen sin inspeccionar. [F02.05](docs/execution/f02-05-repeatable-extraction.md) extrajo dos copias privadas de esos 1740 recursos, verificadas contra el catálogo; 686 pruebas Python aprobadas. [F02.06](docs/execution/f02-06-extraction-hardening.md) añadió 142 casos adversos y corrigió propiedad/cierre de descriptores y estado posterior a confirmación: 828 pruebas aprobadas. [F02.07](docs/execution/f02-07-slice-corpus.md) completó el inventario inicial: 1740 candidatos releídos en ambas copias, dos informes idénticos y 919 pruebas aprobadas. [El sondeo de cámara](docs/execution/f02-07-camera-probe.md) examinó esos 285 candidatos y registró discrepancias con SH2 en 154 archivos; dos informes idénticos y 985 pruebas aprobadas. [La búsqueda estática del ejecutable europeo](docs/execution/f02-07-camera-consumer.md) encontró dos sitios candidatos, con dos informes idénticos y 1101 pruebas aprobadas. [El seguimiento del puntero](docs/execution/f02-07-camera-pointer.md) alcanzó una referencia externa y dos fronteras de llamada, sin vínculo de recurso probado; dos informes idénticos y 1240 pruebas aprobadas. [El análisis de fronteras](docs/execution/f02-07-camera-boundary.md) distingue el argumento de A después del slot y mantiene sin demostrar los efectos de las dos llamadas de B; dos informes idénticos y 1307 pruebas aprobadas. [El plan y validador de observación](docs/execution/f02-07-camera-observation.md) añaden 128 casos propios (1435 pruebas aprobadas) y dos planes idénticos de tres fronteras/25 puntos. [PCSX2 y BIOS europea configurados](docs/execution/f02-07-ps2-boot.md), con carga del ejecutable europeo comprobada por logs. [Primera tentativa en ejecución](docs/execution/f02-07-camera-runtime-attempt.md): nueve breakpoints cargados, seis rangos de memoria coincidentes y aviso de tarjeta verificado visualmente; dos recibos sin observaciones y 128 pruebas del validador aprobadas. [Captura posterior completada](docs/execution/f02-07-camera-runtime-capture.md): nueve eventos en tres invocaciones, seis rangos coincidentes y dos recibos idénticos `validated_observations`; lector privado de estados con contrato EARS, 82 casos nuevos y 1.517 pruebas Python aprobadas. [Búsqueda exacta de recursos completada](docs/execution/f02-07-camera-resource-link.md): diez muestras, seis hits sobre un candidato de 1.536 bytes, dos informes idénticos y 1.583 pruebas Python aprobadas. [Comparación completa del candidato](docs/execution/f02-07-camera-origin.md): los 1.536 bytes coinciden en entrada A; 40 bytes ya difieren al retornar y permanecen iguales en seis estados posteriores. Dos informes idénticos y 1.649 pruebas aprobadas. [Primera escritura observada](docs/execution/f02-07-camera-writer.md): par BEQ+SW coherente con tres bytes modificados, siete estados nuevos, dos recibos idénticos y 1.720 pruebas aprobadas. La [repetición con retorno](docs/execution/f02-07-camera-return.md) añade otra sesión: mismo par BEQ+SW y retorno completo idéntico al histórico; dos recibos iguales y 1.758 pruebas aprobadas. [El contrato de mapa efectivo y su validador](docs/execution/f02-07-effective-mapping.md) pasan 91 casos nuevos (1.849 pruebas totales). macOS denegó el puerto de lectura de PCSX2 con EPERM; la captura real requiere un build instrumentado separado. [Preparación del build](docs/execution/f02-07-pcsx2-build.md): checkout fijado y fixture C++20/x86_64 aprobado; libpng/APNG x86_64 compilada con 37 pruebas aprobadas; Xcode 26.6 y Metal instalados, con compilación/ejecución C++20 y generación/enlace Metal aprobados; CMake con Apple Clang 21 avanzó hasta JPEG en esa etapa. [Primer lote de dependencias completado](docs/execution/f02-07-pcsx2-dependencies.md): NASM (301 pruebas aprobadas, una omitida), JPEG (332/332), Zstd, LZ4 y WebP x86_64 probados e instalados; la cuarta configuración alcanzó SDL3. [SDL3 3.4.12 completada](docs/execution/f02-07-pcsx2-sdl3.md): 19 controles aplicables del proveedor, un no-op identificado y cuatro casos propios aprobados antes/después de instalar; la quinta configuración supera SDL3 y alcanza FreeType. [FreeType 2.14.3 y HarfBuzz 14.2.0 completados](docs/execution/f02-07-pcsx2-fonts.md): siete casos propios pasan contra la instalación final x86_64, con fuente geométrica original y enlace privado comprobado; la sexta configuración alcanzó PlutoVG. [PlutoVG 1.3.2 y PlutoSVG 0.0.7 completados](docs/execution/f02-07-pcsx2-pluto.md): ocho casos propios pasan contra la instalación final, incluido un glifo SVG mediante FreeType; la séptima configuración supera ambos paquetes y alcanza ryml. [RapidYAML 0.12.1 completado](docs/execution/f02-07-pcsx2-rapidyaml.md): cinco casos propios y dos programas del proveedor pasan antes/después de instalar; biblioteca x86_64 y carga privada comprobadas. La octava configuración alcanza Shaderc. [Preparación de Shaderc completada](docs/execution/f02-07-pcsx2-shaderc.md): cuatro archivos verificados, parche corregido y sintaxis C/C++ comprobada; el build quedó pendiente en esa etapa. [Shaderc 2026.2 compilado y validado](docs/execution/f02-07-pcsx2-shaderc-build.md): intento acotado documentado, catorce ejecuciones CTest aprobadas y dylib privada x86_64 instalada; CMake v9 alcanza Qt 6 y también avisa de FFmpeg ausente. [Preparación de Qt Base 6.11.1](docs/execution/f02-07-pcsx2-qtbase.md): archivo y tres parches verificados, configuración x86_64 aprobada, headers generados con syncqt y fixtures preparados; build Qt pendiente de reserva IB02. [Qt Base compilado y validado](docs/execution/f02-07-pcsx2-qtbase-build.md): intento específico vigilado, ocho casos antes/después de instalar, herramientas y plugins x86_64 verificados; CMake v10 resuelve Core/Gui/Widgets y se detiene en LinguistTools. [Qt SVG compilado y validado](docs/execution/f02-07-pcsx2-qt-svg.md): seis casos antes/después de instalar, renderer y plugins de imágenes/iconos comprobados; cuatro binarios x86_64 y prefijo anterior intacto. CMake v11 sigue en LinguistTools. [Qt imageformats compilado y validado](docs/execution/f02-07-pcsx2-qt-imageformats.md): 16 ejecuciones CTest aprobadas, WebP/TGA/WBMP/TIFF y carga privada comprobados; siete plugins x86_64 instalados, tres solo verificados estructuralmente. CMake v12 sigue en LinguistTools. [Qt Tools/LinguistTools compilado y validado](docs/execution/f02-07-pcsx2-qt-tools.md): 16 ejecuciones CTest aprobadas, traducciones/UiTools y herramientas privadas verificadas; ocho ejecutables, tres dylibs y un objeto instalados. CMake v13 supera LinguistTools y alcanza KDDockWidgets. [Qt translations generado e instalado](docs/execution/f02-07-pcsx2-qt-translations.md): 304 QM repetibles, 4.502 mensajes españoles contrastados y diez ejecuciones CTest aprobadas; prefijo preservado. CMake v14 sigue en KDDockWidgets. [QtApng corregido, compilado e instalado](docs/execution/f02-07-pcsx2-qt-apng.md): 18 ejecuciones CTest finales y ocho trazas aprobadas; composición, QMovie y errores verificados, fallos históricos conservados. Plugin privado x86_64 y prefijo intactos. CMake v15 sigue en KDDockWidgets. [KDDockWidgets 2.4.1 completado](docs/execution/f02-07-pcsx2-kddockwidgets.md): 16 ejecuciones CTest finales y seis trazas aprobadas; paneles y persistencia verificados. Se corrigió una cabecera omitida por la instalación sin cambiar C++ ni tests originales. Prefijo conservado; CMake v16 resuelve KDDockWidgets y alcanza FFmpeg. [FFmpeg 8.1 compilado e instalado](docs/execution/f02-07-pcsx2-ffmpeg.md): cinco bibliotecas x86_64, 22 ejecuciones CTest finales, diez trazas y cuatro negativos de configuración aprobados; originales y prefijo conservados. CMake v17 configura y genera PCSX2 con FFmpeg resuelto; persiste el aviso de MoltenVK ausente. [MoltenVK 1.4.1 compilado e instalado](docs/execution/f02-07-pcsx2-moltenvk.md): 25 archivos de receta y siete revisiones transitivas verificados, 16 ejecuciones CTest finales, diez trazas y siete pruebas de capacidad aprobadas; transferencia/cómputo/lectura de imagen GPU contrastados en Apple M2. CMake v18 encuentra MoltenVK y el gate queda listo con 21,47 GiB al cierre. [Baseline PCSX2 compilado y validado](docs/execution/f02-07-pcsx2-baseline.md): 113 tests originales aprobados, paquete local con 42 binarios auditados, depurador observado y cierre limpio; 1.920 pruebas Python. Firma/ID/RPATH corregidos en copias conservando originales. Se verificó la reserva inicial tras liberar espacio; debe reevaluarse antes de builds grandes. 1.920 pruebas Python en el cierre del baseline. Otros escritores, cargador, tipo y salas permanecen pendientes. XBG0, AFS, semántica/corpus y G02 siguen pendientes.

Docker debe estar iniciado. La imagen está fijada por digest; no hace falta instalar devkitARM globalmente:

```sh
image=$(cat toolchains/devkitpro-image.txt)
docker pull "$image"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$PWD,dst=/work" -w /work \
  "$image" bash scripts/build_3ds.sh
```

Salida: `build/3ds/sh3_diagnostic.3dsx`, ELF con símbolos, SMDH, `probe.txt`, `build-id.txt`, `debug-bundle.json`, checksums, inventario de paquetes y `artifact-check.json`. El recibo exige los ocho archivos regulares/no vacíos, fixture/ID/checksums coherentes y cabeceras básicas; no acredita ejecución. El manifiesto vincula ELF/3DSX por SHA-256; se rechaza reutilizar una carpeta que ya contiene evidencia registrada. Conservar el build anterior y usar una copia limpia para el siguiente. En una instalación devkitPro nativa verificada se puede ejecutar directamente `bash scripts/build_3ds.sh`.

El diagnóstico usa figuras sintéticas y un tono PCM propio. `A` pausa/reanuda; `START` sale; `SELECT` alterna audio/archivos y recursos. `X` cambia y guarda el tono; `Y` restaura y guarda su valor predeterminado. Se muestran build ID, estado/etapa/Result de audio, contadores SDK y estados Probe/Load/Save. Después de suspensión o combinaciones bloqueadas, soltar todos los botones antes de una nueva acción; el aviso indica cuándo hacerlo. La escucha permanece NOT_VERIFIED hasta registrarla en la prueba física. No contiene assets del juego. Su compilación no demuestra ejecución, audio o estabilidad en consola.

Para la prueba manual actual, copiar el `.3dsx` y `probe.txt` a `/3ds/sh3_diagnostic/` de la SD y abrirlo con Homebrew Launcher. El build actual está identificado en el [informe F01.08](docs/execution/f01-08-builds.md); seguir el [ensayo de treinta minutos](docs/compatibility/diagnostic-soak.md), la [guía de ciclo de vida](docs/compatibility/lifecycle-probe.md), la [guía de recursos](docs/compatibility/resource-probe.md) y la [guía de depuración](docs/compatibility/debugging.md). La [guía de audio](docs/compatibility/audio-probe.md) conserva la identidad de F01.04: registrar el ID/hash nuevo al repetirla. La [guía de archivos/opciones](docs/compatibility/file-probe.md) conserva su build histórico; si se repite con el actual, registrar su nueva identidad. El programa escribe solo `options-a.dat` y `options-b.dat` en esa carpeta. La prueba de arranque de F01.02 sigue pendiente. FBI corresponde a una futura ruta CIA independiente; esta iteración no produce CIA.


[Observador interno preparado](docs/execution/f02-07-pcsx2-observer.md): contrato EARS,
núcleo/adaptador propios y parche privado optativo; siete objetos compilados
con headers reales. 2.027 pruebas Python y 49 CTest en Release y ASan/UBSan
aprobadas. [Build instrumentado validado](docs/execution/f02-07-pcsx2-observer-build.md):
113 tests originales, 2.072 Python y 39 casos PINE reales sin juego aprobados;
fallo SIGPIPE corregido, firma/ID/RPATH comprobados y cierre limpio con lectura
pendiente.

[Coordinador de adquisición implementado](docs/execution/f02-07-observer-acquisition.md):
conexión persistente, estado con ciclo u64, comparación de memoria/PC/CRC,
custodia privada y publicación atómica; 124 pruebas nuevas y 2.196 totales
aprobadas. El candidato exacto rechaza una sesión sin juego sin generar
estados ni recibos de aceptación.

[Sesión real MP08 completada](docs/execution/f02-07-observer-live.md): arranque
nuevo desde la ISO europea y cuatro capturas con mapa/estado/PINE coherentes;
respaldo coincidente entre las cuatro pausas y dos reimportaciones idénticas.
La entrada conserva los 1.536 bytes del candidato, el paso modifica 3 bytes y
el retorno reproduce los 40 bytes cambiados del histórico. AC11 admite la cola
variable del estado con un presupuesto explícito y mantiene intacto el lector
histórico. 37 pruebas nuevas, 2.233 totales aprobadas.

[Escrituras restantes conciliadas](docs/execution/f02-07-remaining-writers.md):
66 capturas nuevas desde una copia de la entrada SRC53, 32 pares SW y dos
reimportaciones idénticas reconstruyen los 1.536 bytes del retorno y explican
sus 40 bytes modificados. Un primer intento incompleto por plazo se conserva
rechazado. 54 casos nuevos, 2.287 pruebas Python aprobadas. Sigue
`origin/load-provenance`.

[Origen y modelo de carga preparados](docs/execution/f02-07-load-provenance-plan.md):
ISO/MFA y ambas extracciones coinciden con el candidato; 86 registros del
estado concuerdan con el índice. Modelo puro de lectura/copia/entrega con
78 casos nuevos y 2.365 pruebas Python aprobadas. Anclaje y seguimiento
estático generan dos informes idénticos cada uno. Sigue el adaptador de
evidencia y la captura anterior a la carga; procedencia real, semántica,
dos salas y port jugable continúan pendientes.

[Fronteras de carga y validadores multirrango](docs/execution/f02-07-load-frontier.md):
LP-C distingue rutas estáticas de destino directo y caché; comprueba mapas de
código/datos, argumentos y retorno de una llamada. 68 casos nuevos y 2.433
pruebas Python aprobadas. Sigue vincular el descriptor activo al archivo y
adquirir la ruta usada; una transferencia coherente aún no demuestra lectura.

[Generación de descriptores y adquisición multirrango](docs/execution/f02-07-descriptor-acquisition.md):
se rechazan descriptores cerrados o reciclados y se coordinan hasta ocho rangos
contra un único estado guardado. Nueve ventanas estáticas coincidentes y dos
informes iguales; 103 casos nuevos y 2.536 pruebas Python aprobadas. Sigue
vincular la apertura y selección de catálogo con el archivo activo antes de
la captura real de carga.

[Selección de catálogo y apertura](docs/execution/f02-07-catalog-open.md):
una entrada de 1.704 coincide con el origen ISO/MFA; nueve ventanas de código
y dos informes repetibles fijan el plan. Adaptador de cuatro pausas con 96
casos nuevos y 2.632 pruebas Python aprobadas. Sigue identificar el objeto
del driver, su posición y la ruta de lectura/caché antes de la captura real.

[Objeto del driver, despacho y posición](docs/execution/f02-07-driver-transfer.md):
14 ventanas estáticas y dos informes iguales fijan el perfil; los 16 objetos
del estado conservado están cerrados. Dos validadores puros con 99 casos nuevos
y 2.731 pruebas Python aprobadas contrastan generación, posición, retorno y
payload sin certificar una lectura. Siguen el puente con la apertura, identidad
del backend, origen de caché y captura real.

[Apertura y objeto del driver](docs/execution/f02-07-open-driver.md):
validador de tres pausas/24 rangos, con 63 casos nuevos y 2.794 pruebas Python
aprobadas. Comprueba los extremos y rechaza por defecto una continuidad aún
no demostrada. Dos análisis estáticos idénticos; siguen backend/sector, copia,
perfil conjunto de catálogo y captura real.

[Referencia backend, archivo y sector](docs/execution/f02-07-backend-sector.md):
cadena de descriptores contrastada con la extensión ISO, con 19 ventanas y dos
análisis iguales. Validador de una pausa/ocho rangos, 87 casos nuevos y 2.881
pruebas Python aprobadas. Sigue comprobar finalización, llenado del buffer,
copia al destino y continuidad mediante captura real.

[Finalización backend y buffer](docs/execution/f02-07-backend-completion.md):
contrato de tres pausas/24 rangos que comprueba aceptación, éxito, cantidad
completada y hashes del sector y recurso. Incluye 95 casos nuevos, 2.976 pruebas
Python aprobadas y dos análisis estáticos iguales. Un buffer preexistente no acredita lectura nueva;
siguen copia al destino, perfil conjunto y continuidad mediante captura real.

[Copia de buffer y retorno del driver](docs/execution/f02-07-buffer-copy.md):
validador de siete pausas/56 rangos, con 71 casos nuevos y 3.047 pruebas Python
aprobadas. Comprueba retornos,
fuente, destino y cantidades; mantiene pendientes ejecución real y continuidad.
Sigue integrar apertura, resolver progreso temprano y preparar la captura conjunta.

[Catálogo, apertura y recorrido conjunto](docs/execution/f02-07-joint-open-read.md):
once pausas/81 rangos enlazan apertura y copia sin recodificar evidencias. Incluye
49 pruebas propias y 3.096 pruebas Python aprobadas; rechaza continuidad no demostrada por defecto y permite un
diagnóstico explícito sin generar `Read`. Siguen observación de continuidad,
progreso temprano del worker y descubrimiento para la captura real.

[Núcleo de guardia de continuidad](docs/execution/f02-07-lifetime-guard.md):
contrato LG01–LG08 y núcleo C++17 que invalida escrituras protegidas, reciclaje,
huecos y restauraciones. Once escenarios nuevos; 60 pruebas host pasan en Debug,
Release y ASan/UBSan, con cobertura del núcleo del 100 % en líneas y ramas.
3.096 pruebas Python aprobadas y dos análisis estáticos iguales. La integración
de escritores y ciclo de vida de PCSX2 sigue pendiente; aún no acredita continuidad.

[Primer lote de productores VTLB](docs/execution/f02-07-physical-write-probe.md):
cuatro rutas de escritura instrumentadas en una copia privada, con ocho hooks.
Cuatro unidades reales PCSX2 x86_64 compiladas; 26 casos de funciones del proveedor
pasan con ON, OFF y sanitizadores usando memoria propia y dobles explícitos.
67 pruebas host por configuración, 3.096 Python y cobertura del puente del 100 %.
Siguen DMA, JIT/caché y ciclo de vida antes de habilitar continuidad real.

[Segundo lote: productores DMA](docs/execution/f02-07-dma-write-probe.md):
diez puntos de aviso en SPR/MFIFO/SIF/IPU y rechazo conservador del retorno GS.
26 unidades reales compiladas ON/OFF y 54 casos por modalidad ON/OFF/sanitizadores,
con los mismos efectos comprobados. LG-I1 sigue parcial; la siguiente unidad
es JIT/caché. La sincronización global, ciclo de vida y captura real siguen pendientes.

[Caché y barrera de entrada JIT](docs/execution/f02-07-jit-cache-probe.md):
devoluciones físicas de líneas observadas y rechazo conservador de escrituras
lógicas, mantenimiento y entrada JIT. Diez unidades ON/OFF y 70 casos por modalidad
ON/OFF/sanitizadores aprobados. JIT generado y armado durante ejecución siguen
sin cobertura; la siguiente unidad es escritores host, antes de época y admisión.

[Productores host](docs/execution/f02-07-host-write-probe.md): nueve puntos nuevos
en arranque y funciones auxiliares, conservando las hojas compartidas de
depurador/PINE/parches. Dieciséis objetos ON/OFF y 85 casos por modalidad,
incluida la copia anterior, con efectos equivalentes. Siguiente: ciclo de vida,
época y exclusión de escritores antes de admitir captura.

[Barrera cooperativa de PINE](docs/execution/f02-07-pine-exclusion.md): reservas
que siguen solicitudes y callbacks, incluso tras respuesta o timeout. Cierre
consultable con rechazo de nuevas entradas, cancelación y drenaje. Cinco objetos,
44 casos comunes en cuatro modos y trece casos adicionales ON/sanitizadores.
Pendiente integrar el coordinador CPU y GS/VU; no habilita captura real.

[Diagnóstico de admisión](docs/execution/f02-07-admission-profile.md): evaluador
de 18 condiciones y sampler interno del proveedor, con incompatibilidades y
desconocidos separados. Comprueba hilo CPU, reentrada, configuración y punteros;
PINE/GS/VU y otros escritores siguen sin exclusión demostrada. 34 escenarios en
cuatro modos y cuatro objetos ON/OFF. No habilita captura ni admite una VM.

[Ciclo de vida y época host](docs/execution/f02-07-lifecycle-probe.md): contador
no restaurable y 24 puntos de invalidación en reset, carga, remapeo, configuración
y cierre. Diez objetos reales, 54 escenarios por modalidad y ocho pruebas nuevas
del núcleo. Siguiente: admisión con exclusión de CPU/trabajos/PINE y validación de VM.

[Frontera CPU explícita](docs/execution/f02-07-cpu-boundary.md): el diagnóstico
exige una iteración exterior sin actividad ni reentrada. Despacho Qt y catorce
entradas VM revocan la frontera hasta la siguiente iteración. Cuatro objetos
ON/OFF, 45 casos comunes por modalidad y cinco adicionales ON/sanitizadores;
100 pruebas CTest por configuración. Sigue la coordinación PINE y el drenaje
GS/VU antes de habilitar captura real.

[Coordinación de drenaje PINE](docs/execution/f02-07-pine-coordinator.md): cierre
retenido entre iteraciones CPU, callbacks sin Execute durante drenaje y cancelación
por plazo/cambio de épocas. Seis objetos ON/OFF, 110 CTest por preset y probe con
QtCore real. La API sigue interna; quedan servidor completo, GS/VU y captura real.

[Productores y dependencias VU/GS](docs/execution/f02-07-worker-producers.md):
matriz de catorce familias, entrada UI directa a GS y esperas VU↔GS. Cinco pruebas
aisladas en normal/sanitizadores confirman que cola vacía no concede exclusión.
CQ3-A completada; sigue implementar cierre de productores y acuses de trabajadores.

[Propietario persistente del intento](docs/execution/f02-07-retained-drain.md):
PINE permanece cerrado hasta liberar la fase posterior. Diez escenarios nuevos,
120 CTest por preset, cuatro objetos ON/OFF y 26 casos adicionales con cuerpos
del proveedor. La fase GS/VU se rechaza hasta implementar sus barreras; sigue B2.

[Entradas productoras CPU](docs/execution/f02-07-producer-entry.md): 38 avisos antes
de efectos y cambio de idioma por CPU→GS. Seis objetos ON/OFF y 110 casos comunes
más seis de idioma en cuatro modos. B2 completada; sigue B3, eventos Qt restantes
y canal de control. GS/VU continúa rechazado hasta demostrar sus retenciones.

[Entradas y bombeo Qt](docs/execution/f02-07-qt-dispatch.md): B3-A completada con
48 avisos previos a efectos/despacho y 112 escenarios por modo con QtCore real.
Cancelar antes de Qt protege el intento; el drenaje real continúa pendiente.

[Canal CPU↔worker](docs/execution/f02-07-worker-control.md): B3-B1 y núcleo de
B3-B2 completos, con identidad, cancelación, acuses y avisos fuera de la cola de
datos. 138 CTest por configuración, diez escenarios TSan y tres controles
negativos. Sigue B3-B3: fijar los puntos reales VU/GS y sus esperas para integrar
el canal. El puerto productivo permanece rechazado hasta demostrar retención.

[Fronteras y despertar VU/GS](docs/execution/f02-07-worker-boundary.md): B3-B3a/b
definidas y puente de despertar probado con WorkSema real, semáforo doble y Mach.
57 ejecuciones normal/ASan-UBSan/TSan y tres negativos detectados. Sigue integrar
VU en una copia nueva y probar su bucle real; GS y captura permanecen pendientes.

[Retención MTVU integrada](docs/execution/f02-07-vu-control.md): IW-VU1–3
completadas en una copia privada corregida, con cancelación CPU y reconsulta de
cola antes del acuse. 45 ejecuciones finales con Mach y sanitizadores, seis
objetos ON/OFF y cinco negativos. El bucle MTVU usa efectos dobles en estas
pruebas; siguen GS, coordinación global y validación de la VM completa.

[Retención MTGS integrada](docs/execution/f02-07-gs-control.md): IW-GS1–3
completadas, con generación por apertura exitosa, señales antes del acuse y mutex
liberado durante held. Pasan 63 ejecuciones GS y 45 de regresión VU con sanitizadores,
seis objetos ON/OFF y seis negativos. Sigue el coordinador VU→GS; los efectos y
el worker contraparte de estos probes son dobles y la captura global sigue pendiente.

## CI y mantenimiento

[GitHub Actions](.github/workflows/ci.yml) configura calidad Python, arquitectura y trazabilidad, tests host Linux/macOS, sanitizadores, cobertura y compilación 3DS. Selecciona artefactos de desarrollo sintéticos y reportes; no crea releases. La ejecución remota está pendiente. Antes de compartir los binarios debe completarse su revisión de avisos y fuentes [LIC07](docs/compatibility/licenses.md), también cuando procedan de CI.

Conservar dependencias fijadas y un test por regresión. Cada cambio de herramientas, esquema, contrato o receta requiere repetir las pruebas afectadas. La CI no necesita originales. La ISO local de `binaries` y los informes de `reports/local` están excluidos de Git; las extracciones siguen en un directorio externo.

[Coordinador conjunto VU/GS](docs/execution/f02-07-worker-coordinator.md):
IW-COORD1–3 incorpora retención VU→GS, retiro GS→VU e identidad por intento/sesión.
154 CTest por preset, 60 ejecuciones de los bucles conjuntos con sanitizadores y
QtCore, ocho objetos ON/OFF y seis controles negativos. Sigue la validación del
frontend completo; admisión vacía y captura global deshabilitada.

[Frontend y enlace completo](docs/execution/f02-07-worker-frontend.md): nuevo
candidato privado compilado/enlazado, 113 tests originales y testconfig aprobados.
Pruebas entre hilos Qt con TSan instrumentado; una espera circular se recupera
por deadline y requiere cancelación prioritaria. Sin VM ni captura nueva.

[Cancelación ante esperas externas](docs/execution/f02-07-external-waits.md):
CPU retira el intento antes de atender una llamada bloqueante; conserva payload,
retorno y scopes concurrentes. 160 CTest por preset, 24 casos Qt con sanitizadores,
cinco negativos y nuevo build completo con 113 tests originales/testconfig.
Continúan pendientes dependencias de callbacks, PINE conjunto y VM.

[Llamadores y dependencias](docs/execution/f02-07-blocking-callers.md):
106 llamadas clasificadas y seis ensayos con mutex real. Retirar el observador
no garantiza progreso de un callback con otras esperas; siguen PINE conjunto,
locks/backend y VM. No se modifica el proveedor ni se amplía admisión.

[Servidor PINE conjunto](docs/execution/f02-07-pine-joint.md): 63 pruebas finales
con sanitizadores, tres controles negativos y dos objetos ON/OFF. Corrige
alineación, cierre concurrente y mensajes consecutivos; veintidós copias
preservadas. El [enlace SRC88](docs/execution/f02-07-pine-link.md) está completado: 113 tests
originales, firma del candidato y testconfig aprobados. No inicia VM ni habilita
capturas del juego.


[RDebug en el candidato](docs/execution/f02-07-rdebug-artifact.md): auditoría de
403 objetos, 19 archivos estáticos, 806 dependencias y 42 binarios, con siete
controles negativos. La evidencia está ligada al artefacto; falta vincularla al
proceso y completar el perfil de diagnóstico antes de habilitar capturas.

[Identidad y diagnóstico](docs/execution/f02-07-process-diagnostic.md): inventario
del proveedor, matriz de dieciocho condiciones y consumidor con 87 pruebas.
Detecta cambios o pérdida de identidad y descarta el diagnóstico permanentemente.
El adaptador nativo que vincule el proceso real continúa pendiente; las pruebas
del consumidor usan dobles y no habilitan captura ni cambian el perfil productivo.

[Nacimiento nativo del proveedor](docs/execution/f02-07-native-birth.md): adaptador
macOS con PID/nacimiento del sistema y nonce propio. 88 ensayos finales, incluidos
exec/fork reales, tres controles negativos y pipeline host dedicado. Falta ligar
esta clave a las imágenes cargadas y al canal de PCSX2; la admisión sigue cerrada.

[Mappings y eventos nativos](docs/execution/f02-07-native-images.md): vínculo de
archivo con región del kernel y registro de cargas/descargas, probado con
reemplazos reales. IP-NATIVE2 sigue abierto por manifiesto/digests y evidencia de
caché del sistema; no habilita capturas.

[Manifiesto nativo de archivos](docs/execution/f02-07-native-manifest.md): hashes
desde descriptores retenidos y dos pasadas del manifiesto; 42 binarios conservados
comprobados. Caché/AOT y composición del inventario siguen pendientes.

[Composición del inventario](docs/execution/f02-07-native-inventory.md): combina
nacimiento, manifiesto, mappings y revisión del cargador; rechaza todo el conjunto
si una imagen carece de evidencia. 476 ejecuciones finales y tres controles
negativos. La caché del sistema y AOT siguen pendientes; las pruebas positivas
usan bibliotecas propias y no habilitan la ejecución del port.

[Vínculo de páginas de caché](docs/execution/f02-07-native-pages.md): la consulta
del kernel relaciona puntos de las catorce partes x86_64/AOT y 44 bibliotecas con
archivos retenidos. 576 ejecuciones finales y cuatro negativos. Falta verificar
integridad y cobertura completa de la caché antes de integrar el proveedor.

[Integridad y rangos de caché](docs/execution/f02-07-native-cache-integrity.md):
hashes completos de catorce archivos y recorrido exhaustivo de rangos declarados,
con políticas de tamaño separadas del bundle. 664 ejecuciones y cuatro regresiones
detectadas. Una segunda sonda verificó el manifiesto local fijado; falta integrar
la cobertura de todos los segmentos del candidato y acotar la revalidación.

[Inventario de segmentos del candidato](docs/execution/f02-07-native-layout.md):
645 imágenes y 3020 segmentos enumerados en una copia privada de diagnóstico,
con revisión estable del cargador. Se amplió el inventario a 1024 imágenes sin
cambiar los límites de archivos del bundle. 756 ejecuciones y cuatro regresiones
detectadas; falta acreditar los objetos de datos transformados y todos los rangos.

[Unión de intervalos y dependencias](docs/execution/f02-07-native-range-plan.md):
el planificador conserva los 3020 segmentos del censo en 2442 intervalos disjuntos,
sin sumar aliases: 2550806551 bytes virtuales únicos. 820 ejecuciones y cuatro
regresiones detectadas. Incluye clasificación zero-fill, conflictos y límites;
siguen pendientes el origen de páginas transformadas y la enumeración AOT real.

[Mapa virtual y cobertura AOT](docs/execution/f02-07-native-region-map.md):
enumeración desde cero con dos pasadas, límites y rechazo de cambios. 880
ejecuciones finales y cuatro regresiones detectadas. El diagnóstico localiza
caché AOT y traducciones individuales fuera de los segmentos Mach-O, incluido
dyld, y un heap ejecutable de Rosetta. Falta acreditar su origen e integrar la
verificación de páginas con un coste de revalidación acotado.

[Asociación puntual de región y archivo](docs/execution/f02-07-native-region-vnode.md):
912 ejecuciones y cuatro regresiones detectadas. Las 24/27 traducciones AOT
observadas tienen vnode, pero sus archivos devuelven EPERM y no hay descriptores
retenibles en esas fases. La API de nombres puede apuntar a otro mapping y se
excluye como prueba de origen. La [dirección de confianza en la plataforma](docs/execution/f02-07-platform-trust-decision.md)
se desarrolla mediante un perfil separado; captura y admisión permanecen cerradas.

[Perfil de aplicación con plataforma asumida](docs/execution/f02-07-platform-inventory.md):
núcleo PT con tipos, evidencias y hashes propios; 1016 ejecuciones en cuatro
configuraciones, cuatro regresiones detectadas y 122 pruebas Python. Una sonda
aislada clasifica 343 de 345 cabeceras por membresía exacta en la caché de dyld
y rechaza una biblioteca que imita el nombre de otra del sistema. Sigue PT-T3:
adaptador nativo y validación dentro del candidato PCSX2. El perfil aún no está
integrado y no acredita páginas AOT ni permite captura.

[Origen nativo del perfil PT](docs/execution/f02-07-platform-origin.md): adaptador
implementado con 1096 ejecuciones, cuatro regresiones detectadas y 122 pruebas
Python. Clasifica las 557 cabeceras del arranque de PCSX2; rechaza la salida por
el mapping de `libobjc-trampolines.dylib`, cuyo slice x86_64 empieza en offset
16384. Sigue PO-T3b: contrato y vinculación de slices Mach-O universales.
Este límite queda resuelto en [Slices Mach-O y PT v2](docs/execution/f02-07-macho-slices.md):
parser y vínculo nativo con perfil explícito; 1216 ejecuciones C++, cuatro regresiones
detectadas y 153 Python. Testconfig clasifica 557 cabeceras al inicio y 647 al
cerrar, incluido el slice universal a offset 16384. PT-T3 completo; sigue PT-T4,
manifiesto esperado y medición de costes.

[Manifiesto previo y composición PT v2](docs/execution/f02-07-launch-manifest.md)
completa PT-T4: 26 archivos fijados antes de lanzar, seis muestras positivas y
cuatro controles de rechazo en PCSX2. 1292 ejecuciones C++ y 153 Python correctas.
Cada muestra relee 215,10 MiB y tarda 832–875 ms en la ejecución medida. Sigue
PT-T5: diagnóstico/peer y presupuesto con cancelación. La captura sigue deshabilitada.

[Diagnóstico tipado PT v2](docs/execution/f02-07-platform-diagnostic.md) completa
PT-T5a: mensajes acotados, evidencias locales y consumidor separado de IP.
1328 ejecuciones C++, 230 Python y seis mensajes de una copia testconfig validados.
Sigue PT-T5b: autenticar peer y vincular la sesión; después deadline/cancelación.
El codec no autentica el canal ni habilita captura.

[Peer y sesión de diagnóstico](docs/execution/f02-07-diagnostic-peer.md) completa
PT-T5b: identidad nativa del canal y rechazo terminal de replay/cambios/pérdidas.
1356 ejecuciones C++, 335 Python y nueve testconfig privados verificados. Sigue
PT-T5c: presupuesto total, cancelación fuera del hilo CPU y gates del emulador;
la captura sigue cerrada.

[Ejecutor de diagnóstico](docs/execution/f02-07-diagnostic-worker.md) completa
DW-T1 / PT-T5c.1: presupuesto único de 5 s/2 s, cancelación cooperativa y cierre
confirmado después de terminar el trabajador. 1456 ejecuciones x86_64, 24 con
ThreadSanitizer arm64 y seis regresiones detectadas. Sigue DW-T2: integrar los
adaptadores nativos y comprobarlos en PCSX2; la captura permanece deshabilitada.

[Inventario nativo con presupuesto](docs/execution/f02-07-native-diagnostic-work.md)
completa NW-T1–2 / DW-T2a–b: preparación, lectura/hash y cierre en el trabajador.
1504 ejecuciones C++ finales, cuatro regresiones detectadas y nueve casos privados
finales de PCSX2 sin VM. Sigue NW-T3 / DW-T2c, presupuesto del canal; después
DW-T3, guardias runtime. DW-T2 sigue abierto y la captura deshabilitada.

[Consumidor con plazo total](docs/execution/f02-07-budgeted-consumer.md) completa
BC-T1 / NW-T3a: 5 s/2 s desde peer hasta admisión, IO no bloqueante y cancelación
señalada al dueño. 384 pruebas Python, cuatro regresiones detectadas y ocho
escenarios de procesos nativos con payload sintético. Siguen NW-T3b, productor,
y NW-T3c, sonda conjunta PCSX2. Captura deshabilitada.

[Entrega del productor](docs/execution/f02-07-worker-delivery.md) completa
WD-T1 / NW-T3b: el plazo sigue activo hasta confirmar el envío, con escrituras
parciales y cierre del canal por su dueño. Pasan 1608 ejecuciones C++, 41 TSan
y cinco controles de regresión. Sigue NW-T3c, composición privada PCSX2.
La captura continúa deshabilitada.

[Composición privada](docs/execution/f02-07-diagnostic-composition.md) completa
NW-T3 / DW-T2: 20 casos finales de PCSX2 sin VM y diez muestras de inventario
aceptadas, con plazos por extremo, backpressure, fallos y cierres verificados.
Se conserva un intento rechazado antes de alcanzar su inyección. Sigue DW-T3,
integración de guardias runtime; la captura continúa deshabilitada.


[Vinculación runtime revocable](docs/execution/f02-07-runtime-diagnostic-binding.md)
completa RB-T1 / DW-T3a: el trabajador invalida muestras y entregas al retirar su
alcance, incluso mientras espera ocioso. Pasan 1712 ejecuciones finales, 67 TSan
y ocho controles negativos. Sigue RB-T2, conexión con el coordinador privado;
la VM y la captura todavía no se validan con esta vinculación.

[Coordinador runtime privado](docs/execution/f02-07-runtime-coordinator.md) completa
RB-T2 / DW-T3b: conserva guardias CPU/PINE/VU/GS y revoca antes de las transiciones
cubiertas. Pasan 108 pruebas privadas, 1.820 nativas, 94 TSan adicionales y diez
controles negativos; se compilan unidades completas ON/OFF. Sigue RB-T3, enlace
y validación con VM. DW-T3 y captura permanecen pendientes.

[Entrega asíncrona IO–CPU](docs/execution/f02-07-runtime-handoff.md) completa
RB-T3a: el callback conserva el plazo original, rechaza intentos tardíos y confirma
liberación antes de unir DW. Pasan 1.900 pruebas nativas, 148 de integración,
114 TSan adicionales y seis negativos. Sigue RB-T3b: socket/inventario nativo,
candidato enlazado y VM. RB-T3, DW-T3 y captura siguen pendientes.

[Sesión runtime y socket](docs/execution/f02-07-runtime-session.md) completa
RS-T1/RS-T2: vínculo exacto con DW, recepción macOS autenticada, plazos acumulados
y cierre después de retirada CPU. Agrega 42 escenarios al pipeline nativo.
Sigue RS-T3: launcher/inventario nativo válido, candidato enlazado y VM.
RB-T3, DW-T3 y captura permanecen pendientes.

[Composición nativa con runtime](docs/execution/f02-07-native-runtime-composition.md)
completa RS-T3a sin VM: 17 controles alcanzados y 11 muestras con inventario
nativo real. El último control requiere traza del loader; se conservan los
rechazos previos. Host/CPU siguen siendo dobles. Sigue RS-T3b: integración real,
candidato enlazado y validación con VM; la captura permanece pendiente.

[Servicio del candidato enlazado](docs/execution/f02-07-runtime-service.md)
completa RT-T1/RT-T2: integra IO con Host/VMManager reales, construye un candidato
firmado y repara su cierre. La ISO europea inicializa una VM pausada; el inventario
rechaza su preflight y el candidato final sale correctamente. La siguiente tarea
es diagnosticar ese rechazo. Aún no hay muestras aceptadas ni captura habilitada.

[SRC118 — Diagnóstico del preflight](docs/execution/f02-07-native-preflight.md)
completa RT-T3a: el registro se invalida ante un alta con sus 1.024 entradas
ocupadas. Pasan 198 regresiones; dos repeticiones confirman la misma causa y
cierre correcto. Falta medir la demanda completa y corregir capacidad con
presupuesto explícito; no hay inventario válido ni muestras aceptadas.

[SRC119 — Censo independiente](docs/execution/f02-07-native-census.md) completa
RT-T3b.1: el alta 1.025 es nueva y las repeticiones miden 1.067 módulos sin VM y
1.069 con VM pausada. Pasan 186 casos nativos y 27 TSan. Se propone evaluar
2.048 entradas con tamaños ABI medidos; faltan presupuesto de pila/plazo,
ajuste coordinado del contrato y validación positiva. El límite sigue en 1.024
y la captura permanece pendiente. El harness final añade 80 ejecuciones de
portabilidad en GCC/Clang y sanitizadores locales.

[SRC120 — Capacidad y almacenamiento](docs/execution/f02-07-image-capacity.md)
completa RT-T3b.2 en fuentes y pruebas: 2.048 entradas, buffers propios fuera
de pila y protocolo PD v2 coordinado con Python. Pasan 2.224 ejecuciones nativas,
48 TSan, seis GCC y 304 Python. Sigue RT-T3b.3: reconstruir los 128 objetos
afectados del candidato y verificar muestras positivas con VM y sus plazos.
El candidato anterior conserva sus bytes; la captura permanece pendiente.

[SRC121 — Candidato y componentes del host](docs/execution/f02-07-capacity-candidate.md)
reconstruye los 128 objetos afectados y verifica 390 miembros estáticos. El
manifiesto fija tres componentes Apple fuera de la caché; dos perfiles aceptan
dos muestras PD v2 cada uno. Pasan 304 pruebas Python. El cierre inmediato del
productor impide aceptar la tercera respuesta y mantiene RT-T3b.3 abierto;
la captura continúa pendiente.

[SRC122 — Liberación de la última respuesta](docs/execution/f02-07-service-release.md)
completa RT-T3b/RT-T3b.3: el productor espera el medio cierre autenticado del
consumidor y dos perfiles de confirmación aceptan tres respuestas cada uno.
Pasan 433 ejecuciones nativas, 304 Python y 58 de repositorio/supervisor.
Se conserva un intento que agotó el plazo global; el margen bajo carga sigue
pendiente. Continúa RT-T3c: cancelación/callbacks tardíos, coste del inventario
y validación independiente de escritores y ciclo de vida. Captura aún cerrada.

[SRC123 — Abandono del consumidor](docs/execution/f02-07-peer-exit.md) completa
RT-T3c.1a: ocho perfiles con VM verifican cierre antes de pedir datos, tras la
primera o tercera respuesta y rechazo de bytes adicionales. Todos terminan
limpiamente con el motivo esperado; pasan 58 pruebas de repositorio/supervisor.
El candidato se conserva sin recompilar. Siguen cancelación UI, callbacks
tardíos, margen temporal y gates de escritores.

[SRC124 — Cancelación desde la interfaz](docs/execution/f02-07-ui-cancel.md)
completa RT-T3c.1b.UI: doce perfiles observados y dos acciones visibles en el
candidato sin sonda cancelan limpiamente; IO se une antes de detener CPU.
El control normal conserva las tres respuestas. Pasan 445 ejecuciones nativas
y 58 de repositorio/supervisor. Siguen entrega parcial, Apagar VM, callbacks
tardíos, margen temporal y gates de captura.

[SRC125 — Cancelación durante entrega parcial](docs/execution/f02-07-partial-cancel.md)
completa RT-T3c.1b.partial-delivery: la señal de UI se consulta dentro del envío.
Ocho perfiles con prefijos de 1/293 bytes y contrapresión inyectada rechazan el
frame incompleto y cierran ordenadamente; el control sin sonda conserva tres
respuestas. Pasan 453 nativas y 58 de repositorio/supervisor. Siguen Apagar VM,
callbacks reales, margen temporal y gates; no se habilita captura.

[SRC126 — Apagar VM y confirmación](docs/execution/f02-07-vm-shutdown.md) completa
RT-T3c.1b: No conserva la VM y su estado de pausa; Sí vuelve a la lista de juegos
con PCSX2 abierto. Pasan dieciséis perfiles Qt, el contraste CUA sin sonda,
el control normal de tres respuestas, 465 ejecuciones nativas y 58 pruebas del
repositorio/supervisor. Siguen callbacks tardíos/duplicados en Host real, margen
temporal y gates; la captura permanece cerrada.

[SRC127 — Callbacks en Host real](docs/execution/f02-07-host-callback.md) completa
RT-T3c.1: ocho perfiles verifican rechazo tardío, ejecución única y vida útil del
handoff; no cambia producción. Se conservan los dos órdenes del duplicado y el
rechazo de un peer ya cerrado. Pasan 228 ejecuciones nativas, ocho negativas del
checker y 58 pruebas de repositorio. Sigue medir el margen temporal del inventario;
gates y captura permanecen pendientes.

[SRC128 — Margen temporal del inventario](docs/execution/f02-07-inventory-timing.md)
completa RT-T3c.2: doce sesiones aceptan 36 respuestas y cierran limpiamente.
Los manifiestos consumen alrededor del 95 % del muestreo; el margen global
mínimo observado es 463 ms. Se conserva producción y se documentan límites de
la medida; pasan 20 pruebas propias y 58 de repositorio/supervisor. Sigue el mapa
de hechos/gates de JIT, caché, DMA y lifecycle; no se habilita captura.
