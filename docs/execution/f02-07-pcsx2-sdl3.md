# F02.07 — SDL3 para el observador host

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-sdl3`.
Contrato [SD01–SD06](../../schemas/pcsx2-sdl3-v1.md), evidencia
[SRC33](../compatibility/pcsx2-sdl3-evidence.json).

SDL **3.4.12** quedó compilada, probada e instalada como biblioteca x86_64 en
el prefijo privado. La quinta configuración limpia de PCSX2 supera SDL3 y se
detiene ante **FreeType ≥ 2.10**. El checkout del emulador continúa limpio.
Esto cierra esta unidad de dependencia; no cierra F02.07, Q05 ni G02, y no
constituye un build de PCSX2 ni una captura del mapa efectivo.

## Fuente, opciones y alcance

La [descarga oficial](https://libsdl.org/release/SDL3-3.4.12.tar.gz), de
15.629.574 bytes, coincide con el SHA-256 fijado por la receta PCSX2:
`f07b958a9ac5020fb7a44cadb957f658b2149c3c8abb4f63145fac9303249db7`.
Se compararon nuevamente los **2.183 archivos regulares** de la fuente con el
archivo comprimido después del build: ninguno cambió. `LICENSE.txt` conserva
el aviso permisivo de SDL, de estilo zlib; los avisos subordinados permanecen
con las fuentes. La revisión de un eventual bundle sigue en LIC08.

Se mantuvieron las opciones de la receta: vídeo, energía, sensores, diálogos y
bandeja desactivados; biblioteca compartida, Release, x86_64 y destino macOS
11.0. Se usaron Apple Clang 21 y el SDK macOS 26.5 de Xcode. La ampliación para
validación activa `SDL_TEST_LIBRARY`, `SDL_TESTS` y enlace compartido de tests;
desactiva SDL estática y la instalación de ejecutables de prueba. Los 98
registros instalados incluyen cabeceras, configuración CMake/pkg-config,
biblioteca compartida y biblioteca auxiliar de tests.

## Pruebas y omisiones explícitas

| Comprobación | Resultado | Alcance |
|---|---|---|
| CTest del proveedor | 20 procesos con salida satisfactoria; 0 fallos | **19 ejecutan comprobaciones o diagnósticos aplicables**; `testevdev` es un no-op en este host |
| Tests registrados pero excluidos | `testautomation`, `testautomation-no-simd`, `testbounds` | Requieren inicialización de vídeo, desactivado por la receta; no cuentan como aprobados |
| Omisión interna | `testevdev` imprime que SDL no tiene comprobación evdev | CTest lo registra como PASS, pero no se acepta como verificación funcional de evdev |
| Fixture propio contra el build | 4/4 CTest aprobados | Eventos, mando virtual, audio en memoria y buffer |
| Fixture contra la instalación | 4/4 CTest aprobados | Proyecto CMake separado, cabeceras y target compartido instalados |
| Prefijo incorrecto | Configuración rechazada con código 1 esperado | No usa otra instalación disponible como respaldo |
| Arquitectura/enlaces | Dylib y fixture x86_64; sin enlaces a Homebrew | No demuestra dispositivos físicos ni juego |

El [fixture versionado](../../tests/fixtures/pcsx2-sdl3/README.md) comprueba:

- Versión de cabeceras igual a la del binario; eventos FIFO, contenido y cola
  agotada; rechazo de una reserva de cero eventos.
- Creación de mando virtual, ejes mínimo/neutro/máximo, pulsación/liberación,
  índices fuera de rango y desaparición tras cerrar/desconectar.
- Conversión exacta dentro de tolerancia de cinco muestras PCM S16 a F32, con
  tamaño esperado y rechazo de cero canales; no abre dispositivo de audio.
- Lectura limitada al tamaño del buffer, contenido y cola del destino intacta,
  EOF, seek y cierre.

Los casos propios desactivan HIDAPI/IOKit/MFi mediante variables del proceso y
solo modifican su mando virtual. CTest del proveedor usa audio dummy. No se
ejecutó la batería interactiva, ni se validaron vídeo, mandos físicos, audio
real o semántica del juego. La lista completa de tests seleccionados/excluidos
está en SRC33 y en el inventario local.

## Incidencias conservadas y corrección

El primer build se detuvo al enlazar el test opcional `testffmpeg`:
`pkg-config` había encontrado FFmpeg ARM64 de Homebrew pese a
`CMAKE_IGNORE_PREFIX_PATH`. Esa exclusión de CMake por sí sola no aislaba la
consulta de metadata de `pkg-config`. El build fallido y su cache se conservan.

La repetición en `build-v2` limita `PKG_CONFIG_LIBDIR` al `lib/pkgconfig`
privado, vacía `PKG_CONFIG_PATH` y desactiva registros externos de paquetes
CMake. No aplica parches a SDL ni desactiva una prueba que haya fallado en
ejecución: el test opcional de FFmpeg deja de construirse al no existir una
dependencia compatible en ese prefijo. FFmpeg x86_64 sigue pendiente en su
propia etapa. La cache final se revisó para descartar rutas de bibliotecas o
includes de Homebrew; el build completo de SDL y sus targets seleccionados
terminó con código 0. Esta configuración de búsqueda también se usa en PCSX2.

El primer build del fixture propio detectó que `SDL_SetMainReady` se declara
en `SDL_main.h`. Se añadió esa cabecera con `SDL_MAIN_HANDLED`, conservando la
fuente previa y el log de compilación fallido. Después pasaron los cuatro
casos antes de instalar. No se debilitó ningún criterio ni resultado esperado.

## Instalación e integración

`libSDL3.0.dylib` tiene 2.071.464 bytes y SHA-256
`e406136a0c33a801a87ec1b8c8b9f281e2e0d4c6d6735ac9fa27ee164eaeff00`.
La inspección `lipo` confirma x86_64; `otool` muestra referencias al prefijo
privado y bibliotecas/frameworks del sistema. Los hashes de las nueve dylibs
del lote SRC32 permanecen iguales.

El proyecto de integración exige SDL 3.4.12 exacta, un directorio explícito de
`SDL3Config.cmake` y el target `SDL3::SDL3-shared`. La prueba negativa conserva
una instalación válida en `CMAKE_PREFIX_PATH`, pero solicita un directorio
inexistente: CMake falla según lo previsto, sin recurrir a esa instalación.

`baseline-configure-v5` mantiene el commit PCSX2 fijado, Release/x86_64,
prefijo privado y selección de Metal por proceso. Su cache resuelve SDL3 en
el paquete recién instalado y la salida se detiene en `FindFreetype`, con
código 1. Las dependencias posteriores todavía no se han comprobado.

La lectura inicial de espacio fue aproximadamente 18,49 GiB y la de cierre de
CMake 18,15 GiB. Este fue un build de dependencia acotado; el gate del build
completo sigue bloqueado por `storage_reserve` y `pcsx2_configure`. No se
eliminaron datos del usuario ni se redujo la reserva IB02 para operaciones
grandes. Los cuatro ensayos de toolchain reutilizados proceden de SRC31;
la configuración y el espacio actuales están en `preflight-v4.json`.

## Pipeline y trazabilidad

El proyecto de fixture separa la resolución de paquete de los casos de API;
cada caso maneja sus propios recursos y no acopla el runtime 3DS a SDL. Las
pruebas usan errores explícitos y CTest, sin depender de `assert` desactivable
en Release. El gate IB continúa puro y sin descargas/instalaciones.

Artefactos privados/locales en `build/f02-07-pcsx2-sdl3/`:
`download-result.json`, `build-result.json`, `build-result-v2.json`,
`provider-test-inventory.json`, `provider-test-selection.json`,
`provider-junit.xml`, `tests-result.json`, `fixture-main-v1.cpp`,
`fixture-build-junit.xml`, `install-result.json`, `fixture-installed-junit.xml`,
`configure-result-v5.json` y `preflight-v4.json`.
Conservan argumentos, entorno y hashes. SRC33 publica solo metadatos y
contrasta 14 logs de etapas, la descarga y la dylib instalada.
Los controles del repositorio pasan con cero errores; `git diff --check`,
los hashes referenciados y los seis enlaces locales del contrato/informe/
README del fixture también pasan.

La batería Python conserva su resultado histórico de 1.897 casos; no se
repitió ni se suman a ella los procesos SDL. El pipeline general no cambió;
este proyecto CMake se ejecutó localmente. No se ejecutó CI remota, build
completo de PCSX2 ni build 3DS.

## Siguiente unidad

**`prerequisites/dependencies-freetype-harfbuzz`:** verificar los archivos
FreeType 2.14.3 y Harfbuzz 14.2.0 fijados en la receta, conservar sus avisos y
definir fixtures propios antes de compilar. Construir FreeType inicial sin
Harfbuzz, después Harfbuzz y finalmente FreeType con esa integración, según la
receta. Mantener CMake/pkg-config aislados, registrar las pruebas disponibles
y evitar usar fuentes o textos del juego como fixtures.

Aceptación: bibliotecas x86_64 verificadas; prueba funcional de carga/raster de
una fuente redistribuible con procedencia documentada y shaping con resultado
comprobable; repetición CMake de PCSX2 que supera FreeType. No declarar
soporte de fuentes originales ni texto del juego con ese ensayo. Después
seguir el primer faltante real y reevaluar IB antes de Qt/MoltenVK/build base.
