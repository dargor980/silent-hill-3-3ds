# F02.07 — Preparación del build instrumentado

**Actualización posterior:** este informe conserva la etapa SRC31. El
[primer lote de dependencias, SRC32](f02-07-pcsx2-dependencies.md), verifica la
capacidad inicial liberada, prepara NASM/JPEG/Zstd/LZ4/WebP y avanza CMake hasta
SDL3. El plan JSON enlazado aquí conserva su snapshot histórico; el progreso
actual figura en SRC32.

2026-10-17 · `origin/effective-mapping/instrumented-build` ·
[IB01–IB06](../../schemas/pcsx2-build-preflight-v1.md) ·
[evidencia SRC31](../compatibility/pcsx2-build-evidence.json).

**Checkout, piloto libpng y diagnóstico base completados; build completo pendiente.**
El fixture x86_64/C++20 funciona y libpng/APNG 1.6.58 quedó compilada, probada e
instalada en prefijo privado. La segunda configuración ya detecta PNG y se
detiene ante JPEG. Xcode 26.6 y Metal Toolchain 17F109 quedaron instalados desde
Apple. Con selección explícita del toolchain por proceso, los cuatro ensayos
C++20/ejecución/Metal/enlace pasaron. Las demás dependencias siguen pendientes.
El usuario liberó espacio: se observaron 18,46 GiB antes de instalar Xcode y
10,37 GiB al iniciar la tercera configuración diagnóstica y 17,41 GiB al evaluar
el último gate. Son mediciones puntuales de un espacio que puede variar. La reserva IB02
de 20 GiB todavía no se cumple y se comprobará de nuevo antes de las operaciones
grandes. No se construyó el conjunto completo de dependencias.

## Evidencia local

| Comprobación | Resultado | Qué demuestra |
|---|---|---|
| Checkout oficial | Commit `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, árbol limpio | Fuente fijada; coincide con los ocho archivos consultados en SRC30 |
| Compilación C++20 inicial | Código 0, binario x86_64 de 9.464 bytes | Este fixture propio compila con Apple Clang 15.0.0 |
| Ejecución del fixture | Código 0 bajo Rosetta | Las operaciones C++20 del fixture funcionan; no prueba el emulador |
| Compilación Metal inicial | Código 72: herramienta `metal` no encontrada | Fallo histórico previo a instalar Xcode |
| Enlace Metal inicial | No ejecutado | Se omitió tras el fallo de compilación |
| Primera configuración PCSX2 | Código 1: falta PNG ≥ 1.6.40 | Diagnóstico histórico conservado |
| Piloto libpng/APNG | Build y 37 pruebas CTest aprobados | Biblioteca x86_64 instalada solo en prefijo privado |
| Segunda configuración PCSX2 | PNG 1.6.58 detectada; código 1 ante JPEG | Primer bloqueo resuelto; dependencias posteriores aún no evaluadas |
| Instalación Xcode | 26.6, build de producto 17F113, mínimo macOS 26.2 | App Store ofrece «Abrir» y los plist locales identifican la versión instalada |
| Primer inicio Xcode | Acuerdo autorizado por el usuario y aceptado; `-checkFirstLaunchStatus` devuelve 0 | Configuración básica completada; Git vuelve a funcionar |
| C++20 con Xcode nuevo | Compilación y ejecución 0; x86_64, 9.408 bytes | Apple Clang 21.0.0 funciona con el fixture y la selección explícita del toolchain |
| Metal tras instalación | Compilación y enlace 0; AIR de 3.024 bytes y metallib de 2.898 bytes | Apple Metal 32023.883 genera los artefactos; no prueba GPU ni shaders del emulador |
| Tercera configuración PCSX2 | Apple Clang 21 y PNG 1.6.58 detectados; código 1 ante JPEG | Configuración limpia del entorno nuevo; aún faltan dependencias |

El árbol Git es `6932dd7cfae6ecb615bc30fc496c45524110f557`, con 2.934 archivos
versionados y 129.603.536 bytes de archivos regulares. No hay submódulos.
Se conserva `COPYING.GPLv3` y el checkout queda fuera del repositorio del port.
Una primera descarga interrumpida se conserva aparte; el resultado aceptado
procede de `source-baseline`, cuyo HEAD y estado se verificaron. El árbol sigue
limpio después de instalar Xcode y aceptar el acuerdo con confirmación explícita.

La configuración real utilizó Unix Makefiles, Release, arquitectura x86_64,
`DISABLE_ADVANCE_SIMD=ON`, IPO activado, PCH desactivado y FFmpeg enlazado.
Se indicó un prefijo privado nuevo `dependencies-x86_64` y se excluyó
`/opt/homebrew` de la búsqueda de dependencias para evitar mezclar bibliotecas
ARM64. CMake 4.2.3 identificó Apple Clang 15.0.0 y completó sus comprobaciones
básicas de compilador y pthread antes de fallar inicialmente en PNG; una repetición limpia, después del piloto,
se detuvo ante JPEG. Esto no permite afirmar
que las demás bibliotecas estén presentes ni que el proyecto completo compile.
La tercera configuración, también en un directorio nuevo y con selección
explícita de Metal, identificó Apple Clang 21.0.0 y volvió a detectar PNG antes
de detenerse en JPEG. El checkout permaneció limpio al cerrar esa comprobación.

El CMake de PCSX2 incluye compilación/enlace de Metal bajo `APPLE`; la revisión
del commit fijado no encontró una opción soportada para omitir esa etapa del
bundle. El workflow oficial usa Xcode 26.2 con Metal Toolchain. App Store ofreció
una versión compatible con macOS 26.5 y terminó instalando Xcode 26.6, aunque
su ficha anunciaba 27.1. `version.plist` identifica el producto como build
17F113; el campo `DTXcodeBuild` de `Info.plist` es 17F112 y se registra aparte.
Durante la instalación, el directorio de desarrollo activo pasó de
`/Library/Developer/CommandLineTools` a
`/Applications/Xcode.app/Contents/Developer`, sin ejecutar una selección manual.
Los resultados iniciales se conservan como evidencia del entorno previo.
El usuario confirmó la aceptación del acuerdo EA1990; después se completó el
primer inicio con macOS integrado, desmarcando iOS y deteniendo la descarga
opcional del modelo predictivo. La revisión automática rechazó inicialmente
esas deselecciones por interpretarlas como selecciones; el estado visual
confirmó que ya estaban marcadas y las deselecciones individuales se aprobaron.

`xcodebuild -downloadComponent MetalToolchain` terminó con código 0 y Xcode
identifica Metal 26.6 (17F109) instalado. La búsqueda por defecto siguió fallando
tanto dentro como fuera del sandbox. `-showComponent MetalToolchain -json`
devolvió el identificador `com.apple.dt.toolchain.Metal.32023.883`; seleccionar
ese identificador mediante `TOOLCHAINS` solo en el proceso permitió compilar y
enlazar. Esta variable está documentada en el manual local de `xcrun`. La última
validación completa usa esa selección y ejecución fuera del sandbox; no se
cambió una preferencia global para forzarla. La causa del fallo del selector
por defecto no está determinada. La configuración/build siguientes deben
conservar esta variable explícita hasta resolver esa diferencia.

## Dependencias preparadas y alcance de licencia

[Plan fijado de 25 descargas](../compatibility/pcsx2-build-dependencies.json):
URL, nombre y SHA-256 esperado de cada archivo de la receta oficial. Contiene,
entre otros, Qt 6.11.1, SDL 3.4.12, libpng 1.6.58 y FFmpeg 8.1. El registro
`download_verified` distingue hashes esperados de descargas verificadas: dos
archivos de libpng/APNG ya fueron descargados y contrastados; los otros 23 siguen
pendientes. La receta completa no se ejecutó. El piloto manual conserva sus
argumentos, pruebas y archivos instalados por separado.

Se revisaron prefijo de instalación, descargas, verificación de hashes,
construcción y limpieza de esa receta. Sus borrados se dirigen al área de build;
antes de ejecutarla se usará un directorio de trabajo exclusivo y se conservarán
logs/manifiestos fuera de su limpieza final. El script fija x86_64 y destino
macOS 11.0. No instala globalmente mediante `sudo`.

El piloto descargó 1.080.767 bytes y extrajo 6.336.919 bytes de fuente propia
de libpng, manteniendo el área de trabajo en unos 11,3 MB. Aplicó el parche APNG
fijado por la receta y habilitó `PNG_TESTS=ON` para validar antes de instalar.
Pasaron 37/37 pruebas CTest; las 33 entradas del manifiesto de instalación
pertenecen al prefijo privado. La dylib se comprobó x86_64. El archivo `LICENSE`
conservado declara PNG Reference Library License version 2; el parche aplicado
y su procedencia quedan registrados. No se atribuye autoría de libpng al port.

La consulta y el checkout conservan la licencia del emulador; no incorporan sus
fuentes al runtime 3DS. Los términos de cada dependencia y un eventual bundle
siguen sujetos a LIC08. No se redistribuye un binario modificado en esta etapa.

## Implementación, pruebas y pipeline

`tools/qa/pcsx2_preflight.py` separa la política de preparación de la ejecución
de herramientas: función pura, resultados explícitos y ningún instalador/I/O.
Rechaza esquemas incompletos, códigos booleanos, pruebas dependientes ejecutadas
tras fallar su productor y falta de espacio. Un éxito significa únicamente
prerrequisitos suministrados coherentes; siempre conserva
`pcsx2_build_verified: false` y `mapping_verified: false`.

Los fixtures versionados en `tests/fixtures/pcsx2-build` contienen únicamente
código propio. La batería suma **48 casos nuevos y 1.897 pruebas Python
aprobadas**. Gate nuevo: **19/19 líneas y 12/12 ramas**. Cobertura global:
**3621/3666 líneas (98,77 %) y 1156/1188 ramas (97,31 %)**. Ruff, formato,
cobertura y controles del repositorio aprobados. Las pruebas Python se ejecutaron
antes de completar la instalación de Xcode; la validación del toolchain nuevo
corresponde a los cuatro ensayos reales de `toolchain-v5`, todos con salida 0.

El job `quality` existente ejecuta las nuevas pruebas del gate sin descargar
PCSX2 ni requerir macOS. Las pruebas reales de C++20 y Metal fueron locales;
CI remota, compilación completa de PCSX2 y build 3DS no se ejecutaron. La
validación Python no sustituye ninguno de esos resultados.

Artefactos locales: `build/f02-07-pcsx2-build/{source-manifest.json,
toolchain-results.json,configure-result.json,configure-result-v2.json,configure-result-v3.json,
png-manifest.json,xcode-observation.json,metal-install-result.json,
toolchain-v5/results.json,preflight.json,preflight-v2.json,junit.xml,coverage.json}`.
El manifiesto conserva las rutas privadas; `configure-result.json` contiene
los argumentos exactos y el hash del log. La fuente quedó limpia después de
la configuración. `preflight.json` conserva el diagnóstico inicial; no representa
el espacio ni las herramientas posteriores a la instalación. `preflight-v2.json`
registra el entorno nuevo: pasan las cuatro pruebas del toolchain, pero mantiene
`storage_reserve` y `pcsx2_configure` como bloqueos. No se inició una sesión de
juego ni se modificó la app habitual.

## Continuación concreta

1. **Espacio — pendiente; herramientas — verificadas con fixtures.** Comprobar
   la reserva de 20 GiB justo antes de las operaciones grandes. Tras Xcode/Metal
   y las pruebas, el espacio observado volvió a quedar por debajo de esa reserva;
   se solicitó capacidad adicional o un destino alternativo. No se eliminaron
   archivos del usuario. Conservar la selección `TOOLCHAINS` registrada y repetir
   el fixture si cambia el toolchain.
2. **Dependencias x86_64 — libpng completada.** Conservar el piloto probado y
   continuar con JPEG y las demás descargas fijadas, en el mismo prefijo aislado
   y con hashes/avisos. El workflow oficial también instala NASM: comprobar y
   preparar esa herramienta antes de libjpeg-turbo, conservando versión/origen.
   Resolver PNG no equivale a tener todo el entorno listo.
3. **Build base — pendiente.** Repetir CMake en directorio nuevo, evaluar gate,
   compilar, ejecutar tests del emulador y comprobar el bundle y su identidad.
   Para construir dependencias basta resolver capacidad/toolchain; el gate
   completo se exige antes del build base, una vez instaladas esas dependencias.
4. **Instrumentación y mapa — pendiente.** Validar el estado de entrada con el
   build base antes de implementar el exportador acotado. Después ejecutar el
   contrato del adaptador y la sesión nueva de entrada/par/retorno según SRC30.
   La revisión de `Host::RunOnCPUThread` confirma un punto de integración; debe
   cubrirse cierre con una solicitud pendiente sin bloquear el hilo de CPU al
   esperar la terminación del servidor. Esta sincronización aún no está implementada.

Fuentes principales fijadas:
[CMake del emulador](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/CMakeLists.txt),
[receta de dependencias](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/.github/workflows/scripts/macos/build-dependencies.sh).
F02.07/Q05/G02, origen del recurso y mapa efectivo permanecen abiertos.
