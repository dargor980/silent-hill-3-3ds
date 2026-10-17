# F02.07 — PlutoVG y PlutoSVG para el observador host

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-plutovg-plutosvg`.
Contrato [PV01–PV07](../../schemas/pcsx2-pluto-v1.md), evidencia
[SRC35](../compatibility/pcsx2-pluto-evidence.json).

PlutoVG **1.3.2** y PlutoSVG **0.0.7** quedaron compilados e instalados como
bibliotecas x86_64. Los ocho casos propios pasan contra la instalación final,
incluido render real de un glifo SVG sintético mediante FreeType. La séptima
configuración limpia de PCSX2 supera ambos paquetes y se detiene ante **ryml**.
El checkout sigue limpio. Build completo, exportador y mapa efectivo permanecen
pendientes; esta unidad no cierra F02.07/Q05/G02.

## Procedencia y configuración

Los archivos coinciden con la receta del commit PCSX2
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`:

| Archivo | Bytes | SHA-256 |
|---|---|---|
| [plutovg-1.3.2.tar.gz](https://github.com/sammycage/plutovg/archive/v1.3.2/plutovg-1.3.2.tar.gz) | 236.686 | `7bd4e79ce18b1d47517e7e91fbb7cf19d4f01942804a519bc7c0bf32b6325dd5` |
| [plutosvg-0.0.7.tar.gz](https://github.com/sammycage/plutosvg/archive/v0.0.7/plutosvg-0.0.7.tar.gz) | 116.434 | `78561b571ac224030cdc450ca2986b4de915c2ba7616004a6d71a379bffd15f3` |

Los **35 archivos regulares de PlutoVG y 21 de PlutoSVG** se compararon contra
sus archivos comprimidos después del build, sin cambios. Se conservaron sus
avisos MIT y, en PlutoVG, los siete archivos derivados de FreeType que citan
FTL y los tres headers stb con alternativas MIT/dominio público. El MIT raíz
no sustituye esos avisos. La FTL íntegra ya conservada en SRC34 permanece
disponible; un eventual bundle sigue sujeto a LIC08.

Se aplicó la receta sin parches ni cambios de opciones: compartidas, Release,
x86_64, destino macOS 11.0 y ejemplos OFF; PlutoSVG con FreeType ON. Apple
Clang 21/SDK macOS 26.5, cuatro jobs para bibliotecas y dos para fixtures.
CMake/pkg-config se aislaron y los registros de paquetes se desactivaron.
PlutoSVG resolvió el PlutoVG privado instalado y FreeType 2.14.3; no utilizó
el subdirectorio de fallback `plutovg` del archivo fuente.

## Pruebas

Los [casos y oráculos](../../tests/fixtures/pcsx2-pluto/README.md) quedaron
definidos antes de compilar. Comprueban todos los píxeles de rectángulos
alineados, composición alfa premultiplicada, clipping/traslación, stride,
padding/guardas, dimensiones inválidas, SVG a dos escalas, extents/ID y
rechazo de entradas inválidas. Los resultados esperados provienen de la
geometría propia, sin convertir salidas observadas en resultados de referencia.

| Etapa | Resultado |
|---|---|
| Fixture contra PlutoVG antes de instalar | 4/4 CTest |
| Fixture contra PlutoSVG antes de instalar, con PlutoVG/FreeType instalados | 8/8 CTest |
| Proyecto nuevo contra los paquetes instalados | 8/8 CTest |
| Directorio explícito PlutoVG inexistente, con prefijo válido alternativo | Rechazo CMake esperado, código 1 |
| Directorio explícito PlutoSVG inexistente, con prefijo válido alternativo | Rechazo CMake esperado, código 1 |

Son **ocho casos distintos y veinte ejecuciones CTest**, sin fallos, skips ni
tests deshabilitados. RAII libera recursos y mantiene vivos los buffers de
entrada durante su uso. Los checks siguen activos en Release; timeout de 15 s
por caso. La API de memoria externa recibe únicamente un buffer válido con
stride suficiente: las guardas comprueban el dibujo, no una promesa de validar
memoria arbitraria del llamador.

Los builds CMake de los proveedores registran **cero tests**. Se conserva ese
inventario como ausencia de suite, sin contarlo como aprobación. Los ejemplos
desactivados no se presentan como tests ejecutados. No se validan todas las
funciones SVG/OpenType, imágenes/font loader stb, todos los operadores,
rendimiento, datos originales ni render 3DS.

### Camino FreeType → PlutoSVG → PlutoVG

El generador añade una tabla SVG original a la fuente geométrica de SRC34.
FontTools 4.60.1 se reutiliza desde su instalación host aislada, sin nueva
descarga. Dos generaciones idénticas: **1.548 bytes**, SHA-256
`019a5919f32f9ad9906e0b896a2f276666d828598af124a6978f882d07b0639a`.

El caso instala los hooks exportados por `plutosvg_ft_svg_hooks()`, igual que
el consumidor ImGui del PCSX2 fijado, cuyo hash se registra. Comprueba carga
del glifo A como SVG y render BGRA rojo de **20×35 y 40×70 píxeles**, origen,
avance y repetición a 50 px/em en la misma cara. El fixture consume el
adaptador de la biblioteca; no compila una copia header-only de ese adaptador.

Una ejecución diagnóstica adicional con `DYLD_PRINT_LIBRARIES=1` confirma
PlutoSVG, PlutoVG, FreeType y HarfBuzz desde el prefijo privado, sin Homebrew.
El chequeo auxiliar inicial comparó el soname FreeType `.6` literalmente; el
cargador muestra el archivo real `.6.20.6`. Se corrigió el chequeo para resolver
enlaces simbólicos, conservando el mismo log. No hubo fallo de biblioteca o
fixture ni se cambió la expectativa de render.

## Instalación y continuidad

| Biblioteca | Bytes | SHA-256 |
|---|---|---|
| `libplutovg.1.dylib` | 287.440 | `26c682a3cf0ffd72fbcce579f10600ff8bc0dcd859b27114b99f3458143d2226` |
| `libplutosvg.0.dylib` | 81.096 | `0479436303333bb4bf9cbef5a20e4e45bfe6a8a2c2c798695d191fa0c382ae79` |

Ambas dylibs y los dos ejecutables propios son x86_64. Manifiestos: ocho
entradas PlutoVG y nueve PlutoSVG, todas presentes. Los enlaces/cache no
contienen dependencias objetivo Homebrew; las quince dylibs comprobadas de
SRC32–SRC34 conservan sus hashes.

`baseline-configure-v7` resuelve ambos `Config.cmake` desde el prefijo privado
y se detiene en `find_package(ryml)` con código 1. Mantiene el checkout limpio,
Metal por proceso y pkg-config aislado. Las dependencias posteriores todavía
no se comprueban. Van **11 de 25 archivos de receta verificados**, además de
NASM y FontTools auxiliares; el plan inicial permanece como snapshot histórico.

Espacio observado: aproximadamente **16,63 GiB al inicio y 16,55 GiB** al
cerrar CMake. Esta etapa acotada conserva la reserva IB de 20 GiB para builds
grandes; no se eliminan datos ni se atribuye todo el cambio del volumen a
esta compilación. `preflight-v6.json` mantiene `storage_reserve` y
`pcsx2_configure`. Los cuatro checks C++20/Metal se reutilizan de SRC31; no se
presentan como nuevas ejecuciones.

## Pipeline y trazabilidad

Generador de datos, helpers de recursos/píxeles, casos de API y resolución
CMake mantienen responsabilidades separadas. No cambia el runtime 3DS ni el
gate puro IB. El proyecto de fixture se ejecuta sin red una vez disponibles
los insumos; los comandos están en su README. Argumentos, entorno, logs,
JUnit y verificaciones quedan en `build/f02-07-pcsx2-pluto/` y la etapa privada.
SRC35 publica solo metadatos y hashes. Los controles de repositorio pasan con
cero errores; Ruff/formato del generador, `git diff --check`, nueve hashes de
fuentes propias, 34 archivos locales, 21 logs y siete enlaces locales también
pasan. No se ejecutó CI remota ni build completo
PCSX2/3DS; la batería Python de 1.897 casos de SRC31 no se repitió.

## Siguiente unidad: `prerequisites/dependencies-rapidyaml`

1. **Procedencia:** verificar `rapidyaml-0.12.1-src.tgz` contra la receta;
   inventariar c4core y demás componentes incluidos, sus versiones/avisos y
   opciones de tests. No asumir que el archivo incluye o descarga todas las
   dependencias de pruebas.
2. **Contrato y diseño:** definir EARS y fixtures YAML propios antes del build:
   mapas/secuencias anidados, escalares vacíos, valores numéricos y texto UTF-8;
   errores de sintaxis y límites. Fijar cómo capturar errores sin ocultarlos
   ni abortar el coordinador, según la API de esa versión.
3. **Build y pruebas:** compilar compartida x86_64 en prefijo privado; mantener
   CMake/pkg-config aislados. Ejecutar la suite disponible y el fixture antes
   de instalar, registrando cualquier dependencia o subconjunto no ejecutado.
4. **Consumo instalado:** resolver el target `ryml` exportado en un proyecto
   nuevo, probar parseo/emisión y conservación semántica con oráculos propios,
   negativos y versión; verificar arquitectura, enlaces y manifiestos.
5. **Cierre:** repetir CMake PCSX2 que supere `ryml`, registrar el siguiente
   faltante y reevaluar IB. Mantener pendientes exportador, estados, mapa real,
   otros escritores y cargador. Revalidar capacidad antes de operaciones grandes.

Aceptación: biblioteca y fixture instalados verificados y CMake que supera
ryml; no implica soporte de formatos del juego ni ejecutable PCSX2 completo.
