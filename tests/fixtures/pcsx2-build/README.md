# Fixtures del entorno PCSX2

Código propio, sin datos del juego. Son pruebas locales del entorno host; no
acreditan compilación del emulador, ejecución de shaders en GPU ni compatibilidad
con 3DS. El contrato es [DB](../../../schemas/pcsx2-dependencies-v1.md).

| Fixture | Comprobación |
|---|---|
| `toolchain.cpp` / `toolchain.metal` | C++20 x86_64 y generación/enlace Metal, según IB |
| `nasm.asm` + `nasm_driver.cpp` | NASM produce Mach-O x86_64; ABI de llamada y aritmética de 32 bits |
| `zstd.cpp` | Versión de cabecera/biblioteca, ocho recuperaciones exactas, truncamiento y destino insuficiente |
| `lz4.cpp` | Versión de cabecera/biblioteca, ocho recuperaciones exactas y destinos insuficientes |
| `webp.cpp` | Tres imágenes RGBA propias con recuperación sin pérdida, dimensiones, truncamiento y destino insuficiente |

Los patrones de Zstd/LZ4 incluyen longitudes 0, 1, 4.096 y 65.537, con contenido
repetido y pseudoaleatorio de semilla fija. WebP usa imágenes opacas de 1×1,
17×9 y 64×64. No se pretende cubrir todos los modos de cada API.

## Repetición local

Desde la raíz del repositorio, con las bibliotecas ya verificadas e instaladas
en el prefijo privado, indicar `SH3_PREFIX` y ejecutar:

```sh
set -eu
: "${SH3_PREFIX:?Indicar el prefijo privado dependencies-x86_64}"
mkdir -p build/f02-07-pcsx2-dependencies/recheck
for SH3_CODEC in zstd lz4 webp; do
  /usr/bin/clang++ -arch x86_64 -std=c++20 -Wall -Wextra -Werror \
    "tests/fixtures/pcsx2-build/${SH3_CODEC}.cpp" \
    "-I${SH3_PREFIX}/include" "${SH3_PREFIX}/lib/lib${SH3_CODEC}.dylib" \
    "-Wl,-rpath,${SH3_PREFIX}/lib" \
    -o "build/f02-07-pcsx2-dependencies/recheck/${SH3_CODEC}"
  "build/f02-07-pcsx2-dependencies/recheck/${SH3_CODEC}"
done
```

La ruta de búsqueda embebida es necesaria para bibliotecas que usan `@rpath`.
La compilación debe usar el SDK de Xcode y no mezclar cabeceras o bibliotecas
ARM64 de Homebrew. Los argumentos, entorno y resultados exactos de la primera
ejecución están en los manifiestos locales de SRC32.

La secuencia de cada dependencia es configuración → compilación → pruebas del
proveedor disponibles → fixture contra el build → instalación privada → fixture
contra la instalación → arquitectura/enlaces. Un fallo detiene sus dependientes;
la instalación por sí sola no constituye aceptación. Las pruebas del proveedor
no se sustituyen por estos fixtures y sus omisiones se registran aparte.

Estos ensayos requieren macOS y dependencias privadas; no se incorporan al job
Python ni al runtime 3DS. El pipeline general existente sigue en
[ci.yml](../../../.github/workflows/ci.yml). No se anuncia una ejecución remota
de estas pruebas locales.
