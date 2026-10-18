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

Todos los presets fallan si no encuentran pruebas y limitan cada caso a 120 segundos, salvo límites específicos menores. Las pruebas Python de automatización requieren CMake/CTest en PATH. Presets adicionales: `host-release`, `host-sanitize` (ASan/UBSan) y `host-coverage` (GCC). Ejecutar `ctest` también en Release: los checks no desaparecen con `NDEBUG`. CTest incluye 49 casos: ocho suites de núcleo/archivos/métricas/smoke, treinta y tres contratos de composición 3DS, cinco del adaptador de audio, uno de recursos y dos del observador host. Compila composición y `tone.cpp` reales en targets host separados con dobles del SDK; esos casos no acreditan hardware ni escucha. La cobertura C++ se obtiene con `.venv/bin/python -m gcovr --config gcovr.cfg` tras construir y probar `host-coverage`.

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

## CI y mantenimiento

[GitHub Actions](.github/workflows/ci.yml) configura calidad Python, arquitectura y trazabilidad, tests host Linux/macOS, sanitizadores, cobertura y compilación 3DS. Selecciona artefactos de desarrollo sintéticos y reportes; no crea releases. La ejecución remota está pendiente. Antes de compartir los binarios debe completarse su revisión de avisos y fuentes [LIC07](docs/compatibility/licenses.md), también cuando procedan de CI.

Conservar dependencias fijadas y un test por regresión. Cada cambio de herramientas, esquema, contrato o receta requiere repetir las pruebas afectadas. La CI no necesita originales. La ISO local de `binaries` y los informes de `reports/local` están excluidos de Git; las extracciones siguen en un directorio externo.
