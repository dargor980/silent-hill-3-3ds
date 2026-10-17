# F02.07 — primer lote de dependencias del observador

**Continuación:** [SRC33](f02-07-pcsx2-sdl3.md) completa SDL3 y avanza la
configuración hasta FreeType. Este informe conserva el lote y los valores
históricos de SRC32.

Fecha: 2026-10-17. Unidad:
`camera-resource-link-eu/origin/effective-mapping/instrumented-build/prerequisites`.
Contrato [DB01–DB08](../../schemas/pcsx2-dependencies-v1.md), extensión de IB;
metadatos revisables en [SRC32](../compatibility/pcsx2-dependencies-evidence.json).

Se completaron NASM y cuatro dependencias: libjpeg-turbo, Zstd, LZ4 y WebP.
La cuarta configuración limpia de PCSX2 detecta estas bibliotecas y se detiene
ahora ante **SDL3 ≥ 3.2.6**. El checkout oficial permanece limpio. El emulador
todavía no se ha compilado ni instrumentado; F02.07/Q05/G02 siguen abiertos.

## Alcance aceptado y pruebas

| Componente | Resultado local | Límite de la evidencia |
|---|---|---|
| NASM 3.02 | Host ARM64; genera Mach-O x86_64. Suite Python: 301 PASS, 0 FAIL, 1 SKIP. Fixture propio ensamblado, enlazado y ejecutado | `time.1` está deshabilitado por el proveedor; no se presenta como aprobado |
| libjpeg-turbo 3.2.0 | SIMD requerido, dos dylibs x86_64; 332/332 pruebas CTest aprobadas, sin omisiones | No demuestra integración/render de PCSX2 |
| Zstd 1.5.7 | `fuzzer` y `zstreamtest` aprobados con semilla 1 y 1.000 iteraciones cada uno, además de sus comprobaciones unitarias. Fixture propio: ocho recuperaciones exactas y rechazos de truncamiento/destino corto | Subconjunto de CTest; no se ejecutaron `fullbench` ni `playTests` (CLI desactivada) |
| LZ4 1.10.0 | `fuzzer` y `frametest` aprobados con semilla 1 y 1.000 iteraciones cada uno, además de sus comprobaciones unitarias. Fixture propio: ocho recuperaciones exactas y destinos insuficientes | No se ejecutó toda la batería del proveedor |
| WebP 1.6.0 | Cinco dylibs x86_64; fixture propio con tres imágenes RGBA, igualdad completa, dimensiones y rechazos de truncamiento/destino corto | No se ejecutó la suite externa `fuzztest`; las bibliotecas demux/mux/sharpyuv se comprobaron por build, arquitectura y enlaces, sin pruebas funcionales propias de sus API |

Las nueve bibliotecas nuevas se verificaron con `lipo` y `otool`; sus enlaces no
apuntan al prefijo ARM64 de Homebrew. Zstd/LZ4/WebP se ejecutaron contra el build
y nuevamente contra la instalación privada. Los tests upstream de Zstd/LZ4
utilizan sus objetos estáticos; los fixtures propios comprueban adicionalmente
las bibliotecas compartidas destinadas al emulador. La biblioteca PNG anterior
conserva su hash. NASM es una herramienta ARM64 ejecutada en el host; las
bibliotecas que enlazará PCSX2 son x86_64.

## Procedencia, aislamiento y fallos conservados

El [plan de 25 descargas](../compatibility/pcsx2-build-dependencies.json) permanece
como snapshot histórico de SRC31, con su hash original. SRC32 registra el
progreso: **6 de esas 25 descargas verificadas**, incluidas PNG/APNG anteriores;
NASM es una descarga adicional. Los cinco archivos nuevos se contrastaron de
nuevo antes del informe. No se ejecutó la receta monolítica de PCSX2 ni se
copiaron fuentes externas al runtime del port.

NASM procede de la [distribución oficial 3.02](https://www.nasm.us/pub/nasm/releasebuilds/3.02/nasm-3.02.tar.xz),
con SHA-256 contrastado con el [registro de Homebrew](https://formulae.brew.sh/api/formula/nasm.json).
Las cuatro bibliotecas usan las versiones/URLs/hashes de la receta del commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Fuentes, avisos y logs quedan bajo
la raíz privada autorizada; `host-tools` y `dependencies-x86_64` son prefijos
separados. Se conservaron los avisos NASM, IJG/libjpeg-turbo, Zstd, LZ4 y
WebP/PATENTS; la matriz de [licencias](../compatibility/licenses.md) distingue
bibliotecas, programas de prueba y futura redistribución.

Se conservan tres incidencias y sus correcciones:

1. El primer `configure` de NASM terminó con 77 porque la invocación directa de
   Clang carecía de sysroot y no encontraba `libSystem`. Se repitió en una
   extracción nueva con SDKROOT/CFLAGS explícitos; terminó con 0.
2. El `make test` antiguo de NASM devolvió 0 pero imprimió **190 comparaciones
   no disponibles**; no se acepta como suite aprobada. La suite Python falló
   primero por faltar `_version.stdout`. El target oficial genera ese texto
   desde el archivo de versión distribuido; después pasaron 301 casos. No se
   regeneraron resultados binarios esperados con el ensamblador bajo prueba.
   NASM ya se había instalado tras el código 0 del test antiguo y el fixture
   propio; su aceptación quedó pendiente y no se inició JPEG hasta completar
   la suite Python.
3. El primer fixture de Zstd instalado terminó con señal 6: su ejecutable no
   tenía `LC_RPATH` para `@rpath/libzstd.1.dylib`. Se añadió la ruta del prefijo al
   enlace del fixture y la ejecución pasó. La biblioteca no se modificó. LZ4 y
   WebP comenzaron únicamente después de resolver esa comprobación.

## Capacidad y configuración de integración

El usuario confirmó espacio liberado. Al iniciar se observaron
**21.486.219.264 bytes (20,01 GiB)**, suficientes para la reserva inicial.
Después de las compilaciones y de CMake se observaron
**20.047.466.496 bytes (18,67 GiB)**. La diferencia es espacio libre del volumen,
no una medición del tamaño de este lote; no se atribuye toda a las dependencias.
No se eliminaron archivos del usuario. IB02 se volverá a evaluar antes de
dependencias grandes o del build completo.

La configuración `baseline-configure-v4` usa Apple Clang 21, Release, x86_64,
prefijo privado, exclusión de Homebrew y la selección por proceso de Metal ya
verificada: `TOOLCHAINS=com.apple.dt.toolchain.Metal.32023.883`.
Detecta PNG 1.6.58, JPEG ABI 62, ZLIB 1.2.12 del SDK, Zstd, LZ4 y WebP.
JPEG ABI 62 es la versión de interfaz indicada por CMake; la fuente construida
es libjpeg-turbo 3.2.0. CMake termina con 1 ante SDL3; no comprueba los requisitos
posteriores. No se inicia el build base mientras esa configuración falle.

`preflight-v3.json` conserva `storage_reserve` y `pcsx2_configure` como bloqueos
del **build completo**. Reutiliza las cuatro comprobaciones de toolchain de
SRC31, cuyo entorno no cambió en este lote, y añade la configuración/espacio
actuales. No reinterpreta el preflight histórico como un resultado vigente.

## Diseño, pipeline y evidencia reproducible

Los [fixtures propios](../../tests/fixtures/pcsx2-build/README.md) están separados
por biblioteca. Cada uno comprueba comportamiento observable; el gate IB sigue
siendo una función pura y no descarga ni instala software. Los proyectos de
los proveedores construyen sus bibliotecas y el procedimiento local conserva
argumentos, entorno, resultados y hashes. Esta separación mantiene el runtime
3DS independiente de las herramientas de investigación.

Secuencia del lote: hash/fuentes → configure → build → pruebas → instalación
privada → ejecución instalada → arquitectura/enlaces → CMake nuevo de PCSX2.
La batería general Python sigue con la evidencia histórica de **1.897 pruebas**;
no se volvió a ejecutar ni se suman pruebas de proveedores a ese total. El job
`quality` y el pipeline 3DS existentes no cambiaron. No se ejecutó CI remota,
una compilación completa de PCSX2 ni un build 3DS en esta unidad.

Artefactos locales en `build/f02-07-pcsx2-dependencies/`:
`start.json`, `stage-manifest.json`, `extra-downloads.json`, `jpeg-result.json`,
`jpeg-junit.xml`, `codecs-result.json`, `zstd-junit.xml`,
`configure-result-v4.json`, `preflight-v3.json` e
`installed-fixtures-recheck.json`. Conservan los comandos exactos
y rutas privadas. SRC32 publica únicamente metadatos: hashes de cinco descargas,
38 logs de etapas contrastados y hashes de bibliotecas/fixtures/contrato.
La repetición final compila los tres fixtures de códec usando cabeceras y dylibs
instaladas, y los tres se ejecutan correctamente. Controles del repositorio:
PASS, cero errores; `git diff --check`, hashes referenciados y enlaces locales
del contrato/informe/README de fixtures, aprobados.

## Tareas siguientes y aceptación

1. **`prerequisites/dependencies-sdl3`.** Descargar SDL 3.4.12 con el hash fijado;
   revisar avisos/opciones de su fuente, construir x86_64 en el mismo prefijo y
   ejecutar los tests disponibles para este entorno. Registrar explícitamente
   pruebas que requieran ventana/audio/dispositivos. Verificar un fixture de API
   propio y la resolución de `SDL3Config.cmake` desde el prefijo privado.
   Aceptación: pruebas seleccionadas pasan y un CMake nuevo supera SDL3.
2. **`prerequisites/dependencies-remaining`.** Seguir el primer faltante real:
   FreeType/Harfbuzz, PlutoVG/PlutoSVG, rapidyaml y los componentes gráficos,
   multimedia y Qt de la receta. La integración FreeType/Harfbuzz requiere las
   dos pasadas previstas por el proveedor. Antes de Qt/MoltenVK u otra operación
   grande, revisar IB02, tamaño previsto y paralelismo; el host tiene 8 GiB RAM.
   Aceptación por biblioteca: origen fijado, build/pruebas, avisos y resolución
   aislada, sin marcar como verificadas dependencias todavía no alcanzadas.
3. **`baseline-build`.** Con dependencias completas, repetir CMake y el gate.
   Solo con resultado satisfactorio compilar PCSX2, ejecutar sus tests y
   comprobar bundle/identidad/compatibilidad de estados en el perfil privado.
4. **`instrumentation` y `effective-mapping/capture`.** Después del build base,
   implementar el observador interno acotado y probar cierre con una solicitud
   pendiente. Finalmente capturar entrada/par/retorno según MP. La semántica del
   recurso, los otros escritores y el cargador requieren evidencia adicional.
