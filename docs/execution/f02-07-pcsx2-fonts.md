# F02.07 — FreeType y HarfBuzz para el observador host

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-freetype-harfbuzz`.
Contrato [FH01–FH07](../../schemas/pcsx2-fonts-v1.md), evidencia
[SRC34](../compatibility/pcsx2-fonts-evidence.json).

FreeType **2.14.3** y HarfBuzz **14.2.0** quedaron compilados, probados con
fixtures propios e instalados en el prefijo privado x86_64. La sexta
configuración limpia de PCSX2 encuentra FreeType y se detiene ante
**PlutoVG ≥ 1.1.0**. El checkout sigue limpio. Esta unidad no cierra F02.07,
Q05 ni G02 y no constituye un build completo ni una captura del mapa efectivo.

## Procedencia y compilación

Las dos descargas coinciden con los SHA-256 de la receta fijada en
PCSX2 `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`:

| Archivo oficial | Bytes | SHA-256 |
|---|---|---|
| [freetype-2.14.3.tar.xz](https://sourceforge.net/projects/freetype/files/freetype2/2.14.3/freetype-2.14.3.tar.xz) | 2.670.220 | `36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f` |
| [harfbuzz-14.2.0.tar.gz](https://github.com/harfbuzz/harfbuzz/archive/14.2.0/harfbuzz-14.2.0.tar.gz) | 37.408.544 | `c652d5d94971031654ab3989891a490a895d3e3f2b71171c62692b28e94b1b93` |

Se compararon contra los archivos comprimidos **855 archivos regulares de
FreeType y 3.718 de HarfBuzz**, sin cambios. Los avisos permanecen junto a
las fuentes; sus hashes están en SRC34. FreeType ofrece FTL o GPLv2-or-later,
con avisos subordinados. HarfBuzz declara Old MIT. No se distribuye un bundle;
la revisión de una eventual entrega sigue en LIC08.

Se siguió FreeType sin HarfBuzz → HarfBuzz → FreeType final, con tres builds
separados y fuentes conservadas. Release, x86_64, destino macOS 11.0, Apple
Clang 21 y SDK macOS 26.5. FreeType exige PNG/zlib y desactiva Bzip2/Brotli.
HarfBuzz conserva utilidades/GPU desactivados; subset/raster/vector y CoreText
siguen activados por sus valores de receta. `HB_HAVE_FREETYPE` permanece OFF:
la integración comprobada es FreeType → HarfBuzz. Se limitaron búsquedas
CMake/pkg-config al prefijo privado y se desactivaron registros de paquetes.

### Ajuste explícito: carga de HarfBuzz

FreeType 2.14.3 activa `FT_DYNAMIC_HARFBUZZ` por defecto. Su CMake omite la
búsqueda obligatoria cuando detecta `dlopen`, aunque se haya indicado
`FT_REQUIRE_HARFBUZZ=TRUE`; `src/autofit/ft-hb.c` intenta entonces resolver
símbolos globales o cargar `libharfbuzz.0.dylib` por nombre. La receta CMake de
HarfBuzz produjo aquí **`libharfbuzz.dylib`**, sin el sufijo `.0`.

La variante final añade **`FT_DYNAMIC_HARFBUZZ=OFF`**, manteniendo
`FT_REQUIRE_HARFBUZZ=TRUE`. Es una desviación documentada de las opciones
literales de la receta, sin parchear fuentes: CMake debe resolver la biblioteca
privada y FreeType queda enlazado a ella. `otool` y una ejecución diagnóstica
con `DYLD_PRINT_LIBRARIES=1` confirman esa ruta durante el caso auto-hinting.
No se cambian variables globales del sistema. La verificación inicial de
enlaces suponía el nombre `.0`; se corrigió para contrastar el nombre real,
sin cambiar la biblioteca ni aceptar una ruta externa.

## Pruebas y límites

El [fixture propio](../../tests/fixtures/pcsx2-fonts/README.md) genera una fuente
geométrica de 1.356 bytes: rectángulos con métricas, cmap, ligadura `AV` y
kerning definidos antes de observar resultados. No usa fuentes ni textos del
juego. FontTools **4.60.1**, wheel puro Python verificado por SHA-256 de PyPI,
se usa exclusivamente para generarla; no se instala globalmente ni en el
prefijo de bibliotecas objetivo. Conserva licencia MIT y avisos externos.

Dos generaciones iniciales y otras dos después del ajuste de lint dieron el
mismo SHA-256: `cdd254e7aec2ce13f35942b815da8374d8b0f36a61ef99ba4a4519c2dda81b97`.
El ajuste usa `zip(strict=True)` para rechazar longitudes distintas, sin
modificar los datos de prueba.

| Etapa CTest del fixture | Resultado |
|---|---|
| FreeType bootstrap antes de instalar | 4/4 |
| HarfBuzz antes de instalar, con FreeType bootstrap instalado | 7/7 |
| FreeType final antes de instalar, con HarfBuzz instalado | 7/7 |
| Ambos instalados, proyecto CMake nuevo | 7/7 |
| Prefijo inexistente, con prefijo válido disponible como alternativa | Rechazo CMake, código 1 esperado |

Son **siete casos distintos**, repetidos según la etapa (25 ejecuciones CTest),
sin fallos ni skips. FreeType comprueba versión, cmap, avance, origen y todos
los píxeles de A a dos tamaños, auto-hinting, fuente truncada e índices inválidos.
HarfBuzz comprueba IDs, clusters, avances y offsets con ligadura activada,
desactivada y kerning, además de espacio, texto vacío, carácter ausente y
fuente truncada. Se exige el shaper OpenType. Cada caso libera recursos con
RAII y devuelve errores explícitos; Release no desactiva las comprobaciones.

**Las suites de los proveedores no se ejecutaron.** Los tres inventarios
CMake registran cero tests, lo cual no cuenta como aprobación. FreeType
documenta su test Meson y descarga adicional de fuente; los tests API de
HarfBuzz requieren GLib, desactivado en esta configuración. Su CMake advierte
que el soporte lo mantiene la comunidad. Se conserva la receta CMake de PCSX2
y se registra esa cobertura pendiente, sin añadir otro toolchain de pruebas.
No se validaron todos los formatos, tipografía original, español completo,
CoreText ni las API subset/raster/vector de HarfBuzz.

## Instalación, integración y capacidad

Se verificaron cinco dylibs x86_64: FreeType, HarfBuzz principal, subset,
raster y vector. No enlazan bibliotecas de Homebrew. El manifiesto FreeType
contiene 64 entradas y el de HarfBuzz 47; sus rutas existen. Las diez dylibs
de SRC32/SRC33 mantienen sus hashes. Los dos ejecutables del fixture final
también son x86_64. Versiones, hashes y tamaños están en SRC34.

`baseline-configure-v6` resuelve FreeType 2.14.3 desde el prefijo privado y
falla, con código 1, en `find_package(plutovg 1.1.0)`. Aún no se comprueban
dependencias posteriores. Conserva selección de Metal por proceso y aislamiento
de pkg-config; no modifica el checkout del emulador.

Al comienzo de la descarga había aproximadamente 17,90 GiB libres; al cerrar
CMake, 17,55 GiB. Esta unidad fue un build acotado. El gate conserva los
bloqueos `storage_reserve` y `pcsx2_configure`: se mantienen los 20 GiB de
reserva de trabajo para operaciones grandes, sin borrar datos del usuario.
El cambio de espacio total del volumen no se atribuye íntegramente a este build.
Los cuatro ensayos C++20/Metal del gate se reutilizan de SRC31; la configuración
y capacidad nuevas están en `preflight-v5.json`.

## Pipeline y trazabilidad

El generador, la resolución CMake y los casos de API tienen responsabilidades
separadas. El proyecto CMake del fixture se puede ejecutar sin red una vez
disponibles sus insumos; no depende del runtime 3DS. Los argumentos, entorno,
logs, JUnit, manifiestos y hashes quedan en `build/f02-07-pcsx2-fonts/` y en
la etapa privada. SRC34 publica metadatos y referencia esos resultados.
Los controles de repositorio, Ruff del generador, enlaces locales y
`git diff --check` pasan. No cambió el pipeline general ni se ejecutó CI remota.
Las 1.897 pruebas Python de SRC31 conservan su carácter histórico; no se
repitieron para esta unidad de bibliotecas. No hay build completo PCSX2/3DS.

## Siguiente unidad: `prerequisites/dependencies-plutovg-plutosvg`

1. **Procedencia y contrato:** verificar PlutoVG **1.3.2** y PlutoSVG **0.0.7**
   contra la receta; revisar avisos, API y tests disponibles. Definir EARS,
   expectativas geométricas y negativos antes de construir.
2. **PlutoVG:** compilar compartida x86_64, con ejemplos OFF; probar dibujo
   sintético en memoria, tamaño/stride, color, transparencia y límites según
   las API documentadas. Conservar resultados antes de instalar.
3. **PlutoSVG:** compilar con `PLUTOSVG_ENABLE_FREETYPE=ON`, compartida y
   ejemplos OFF. Probar un SVG propio con dimensiones/colores conocidos y
   entradas inválidas; verificar la integración FreeType disponible sin
   atribuir cobertura al formato SVG de fuentes originales.
4. **Integración y calidad:** proyecto CMake de consumo instalado, arquitectura,
   enlaces, negativos y manifiestos; mantener aislamiento y registrar suites
   no ejecutadas. Conservar fallos y resolverlos antes de continuar.
5. **Cierre:** configuración nueva de PCSX2 que supere ambos paquetes y gate
   actualizado. Seguir el primer faltante observado; reevaluar capacidad antes
   de Qt/MoltenVK/build completo. Exportador, estados, mapa real, otros
   escritores y cargador permanecen pendientes.

Aceptación: ambas bibliotecas verificadas, fixtures aprobados y CMake que
supere PlutoVG/PlutoSVG. No equivale a render del juego ni a compatibilidad 3DS.
