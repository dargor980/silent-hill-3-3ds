# Integración SDL3 del entorno host

Fixture propio del contrato [SD01–SD06](../../../schemas/pcsx2-sdl3-v1.md).
Cuatro casos CTest independientes: eventos FIFO/contenido, mando virtual con
límites/ejes/botón y liberación, conversión PCM S16 → F32 sin dispositivo, y
lectura de un buffer con EOF/seek. Cada proceso comprueba la versión de
cabeceras frente a la biblioteca. No usa originales ni produce audio real.

El caso de mando desactiva HIDAPI/IOKit/MFi por variables de proceso y solo
modifica el dispositivo virtual que crea. Los recursos usan destrucción
automática, incluidos los caminos de fallo. Estos casos no prueban mandos
físicos, render, audio real ni comportamiento del juego.

Desde la raíz del repositorio, indicar un directorio de configuración SDL
privado y un directorio de build nuevo. Para la prueba previa a instalar,
`SH3_SDL_CONFIG_DIR` es el árbol de build de SDL; para validar la instalación,
es `dependencies-x86_64/lib/cmake/SDL3`:

```sh
cmake -S tests/fixtures/pcsx2-sdl3 -B "$SH3_FIXTURE_BUILD" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=x86_64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  "-DSH3_SDL_CONFIG_DIR=$SH3_SDL_CONFIG_DIR"
cmake --build "$SH3_FIXTURE_BUILD" --parallel 2
ctest --test-dir "$SH3_FIXTURE_BUILD" --output-on-failure \
  --output-junit "$SH3_FIXTURE_BUILD/junit.xml"
```

El proyecto requiere SDL 3.4.12 exacta y usa `SDL3::SDL3-shared`. Una ruta
explícita inexistente provoca error; no se busca otra instalación como respaldo.
La ejecución inicial conserva SDK, entorno y argumentos exactos en
`build/f02-07-pcsx2-sdl3/`. CMake configura el rpath del target importado.

Al construir las pruebas del proveedor se habilitan `SDL_TEST_LIBRARY` y
`SDL_TESTS`; el resto de exclusiones procede de PCSX2. Además de excluir
Homebrew mediante CMake, establecer `PKG_CONFIG_LIBDIR` al `lib/pkgconfig`
privado y dejar `PKG_CONFIG_PATH` vacío. No ejecutar la batería interactiva;
inventariar CTest y registrar qué tests requieren funciones desactivadas.

Este proyecto se valida localmente en macOS. No cambia el job Python ni añade
SDL3 al runtime 3DS; su aprobación tampoco acredita un build de PCSX2.
