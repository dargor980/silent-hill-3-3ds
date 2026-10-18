# F02.07 — RapidYAML para el observador host

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-rapidyaml`.
Contrato [RY01–RY07](../../schemas/pcsx2-rapidyaml-v1.md), evidencia
[SRC36](../compatibility/pcsx2-rapidyaml-evidence.json).

RapidYAML **0.12.1** quedó compilado e instalado como biblioteca compartida
x86_64. Pasan cinco casos propios y dos programas originales del proveedor,
tanto antes como después de instalar. La octava configuración limpia de PCSX2
supera `find_package(ryml)` y se detiene ante **Shaderc**. Build completo,
exportador y mapa efectivo permanecen pendientes; no se cierra F02.07/Q05/G02.

## Procedencia y configuración

El [release 0.12.1](https://github.com/biojppm/rapidyaml/releases/tag/v0.12.1)
se verifica contra la receta PCSX2 del commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`:

| Archivo | Bytes | SHA-256 |
|---|---|---|
| `rapidyaml-0.12.1-src.tgz` | 10.391.033 | `e9efcdd17f86287748793cf21d106e461fcad8d103a3e5a23632afe93828660d` |

Incluye c4core **0.2.12**, incorporado en la misma dylib, y fast_float **8.2.4**
(versión declarada en el header amalgamado). debugbreak, rng e inplace_function
se identifican por sus archivos/hash, sin atribuirles commits no demostrados.
Se compararon **747 archivos regulares y 40 enlaces simbólicos** contra el
archivo descargado, sin cambios ni archivos extra. No hubo parches.

Se conservaron avisos MIT de RapidYAML/c4core/c4Project y rng; BSD de dos
cláusulas de debugbreak; Boost de inplace_function y los textos MIT/Boost/Apache
incluidos por fast_float. El header amalgamado conserva su aviso MIT. Los hashes
de textos y componentes constan en SRC36; LIC08 sigue abierto para un eventual
bundle, que no se produce aquí.

Receta aplicada: `BUILD_SHARED_LIBS=ON`, Release, x86_64, destino macOS 11.0,
Apple Clang 21/SDK 26.5, dos jobs. `RYML_DEFAULT_CALLBACKS=ON`,
`RYML_DEFAULT_CALLBACK_USES_EXCEPTIONS=OFF` y `C4CORE_WITH_FASTFLOAT=ON` conservan
sus valores originales. El fixture instala un callback temporal de parseo;
no cambia el comportamiento predeterminado de la biblioteca. Búsquedas
CMake/pkg-config aisladas y registros de paquetes desactivados.

## Pruebas y alcance

Los [fixtures](../../tests/fixtures/pcsx2-rapidyaml/README.md) usan un YAML propio.
Sus comprobaciones permanecen activas en Release:

| Caso propio | Comprobaciones |
|---|---|
| `structure` | Mapas/secuencia, ocho campos, UTF-8, escalar vacío no nulo, conversiones bool/int/double y clave ausente |
| `ownership` | Arena conserva valores tras cambiar el origen; in-place referencia el búfer vivo y refleja su modificación |
| `roundtrip` | Modifica entero, añade elemento/texto con signos y salto de línea; emite, vuelve a leer y verifica semántica |
| `bounds` | Consulta tamaño, salida insuficiente con puntero nulo/tamaño requerido, capacidad exacta y guardas intactas |
| `invalid` | Dos errores sintácticos activan callback de parseo con ubicación; RAII restaura callbacks y la lectura posterior funciona |

Además se compilan sin modificar `samples/quickstart.cpp` y
`samples/quickstart-ints.cpp`; este último con sus dos implementaciones de
`src_extra`, igual que en el CMake de tests del proveedor. El primer programa
informa **1.842 comprobaciones satisfactorias** en cada etapa; el segundo
compara el buffer de eventos con su referencia y termina con código 0. Cada
programa tiene un directorio de trabajo privado: quickstart escribe un YAML.

| Etapa | Resultado |
|---|---|
| Target exportado del build, antes de instalar | 7/7 CTest |
| Proyecto nuevo con paquete instalado exacto 0.12.1 | 7/7 CTest |
| Paquete explícito ausente con prefijo alternativo válido | Rechazo esperado de CMake, código 1 |
| Diagnóstico de carga del consumidor instalado | ryml desde el prefijo privado, código 0 |

Son **siete casos distintos y catorce ejecuciones CTest**, sin fallos, skips ni
deshabilitados. La versión de headers y binario coincide en los cinco casos
propios. Timeouts: 15 segundos por caso propio y 60 por programa del proveedor.

El build de biblioteca no registra tests porque el desarrollo está desactivado.
La **suite completa del proveedor no se ejecutó**: su configuración descarga
c4fs/c4log y otros repositorios, algunos desde ramas móviles. Los dos programas
seleccionados son también registrados por su CMake de tests, pero no se
presentan como ejecución de aquella suite. No se hicieron pruebas de fuzzing,
sanitizers, conformidad YAML completa, rendimiento ni datos del juego.

## Instalación y continuidad

| Biblioteca | Bytes | SHA-256 |
|---|---|---|
| `libryml.0.12.1.dylib` | 367.744 | `0b91d13df74657b1142d99c7969f545e4c8863459d1d3bc325a06f407bb1b3cd` |

La biblioteca y los tres consumidores instalados son x86_64. El manifiesto
contiene **155 entradas**, todas presentes dentro del prefijo. Las **18 dylibs
previas** conservan sus hashes. Flags/enlaces de los targets no contienen
includes ni bibliotecas Homebrew; el ejecutable host de CMake sí procede de
Homebrew. El diagnóstico de dyld confirma la ruta privada de ryml.

`baseline-configure-v8` resuelve `ryml_DIR` desde el prefijo privado y llega a
`Could NOT find Shaderc (missing: SHADERC_LIBRARY SHADERC_INCLUDE_DIR)`.
El checkout PCSX2 sigue limpio y fijado. Van **12 de 25 archivos de receta
verificados**, más NASM/FontTools auxiliares; el plan inicial se conserva como
snapshot histórico. No se afirma disponibilidad de dependencias posteriores.

Espacio observado: aproximadamente **15,54 GiB al inicio y 17,58 GiB** al cerrar
la verificación. La variación pertenece al volumen completo y no mide el coste
de esta etapa. El gate `preflight-v7.json` conserva `storage_reserve` y
`pcsx2_configure`: la reserva de 20 GiB para builds grandes sigue vigente.
Los cuatro resultados C++20/Metal se reutilizan explícitamente de SRC31.

## Pipeline y trazabilidad

Requisitos, fixtures de API, ámbito RAII de callbacks y resolución CMake tienen
responsabilidades separadas; no cambia el runtime 3DS ni el evaluador IB.
El proyecto consumidor se construye sin red una vez presentes los insumos.
Argumentos, entorno, logs, JUnit y comprobaciones quedan en la etapa privada
y `build/f02-07-pcsx2-rapidyaml/`; SRC36 publica metadatos y hashes.

Se conservaron tres correcciones del comprobador auxiliar de evidencia:
distinguir enlaces simbólicos del archivo, leer el log CTest completo porque
JUnit trunca salidas satisfactorias, y separar el contador de enlaces del
texto de `otool`. La verificación final compara 747 archivos y 40 enlaces;
estas correcciones no modificaron fuentes, biblioteca ni fixtures ni exigieron
repetir los tests. Los logs completos confirman las 1.842 comprobaciones.

Controles del repositorio y `git diff --check` aprobados; hashes de los cinco
archivos propios y evidencias locales verificados. No se ejecutó CI remota,
build PCSX2/3DS completo ni se repitieron los 1.897 tests Python históricos.

## Siguiente unidad: `prerequisites/dependencies-shaderc`

1. **Capacidad y procedencia:** comprobar espacio antes de compilar este grupo
   C++; conservar la reserva IB para builds grandes. Verificar los cuatro
   archivos de la receta: Shaderc 2026.2, glslang
   `275822a6261ee689aadb1da5f09a0ec2f058685c`, SPIRV-Headers
   `58006c901d1d5c37dece6b6610e9af87fa951375` y SPIRV-Tools
   `6337eb62cadd7d124ac6789bf39c0f71148f0a73`. Inventariar sus avisos.
2. **Contrato y diseño:** definir EARS, fixtures GLSL propios y criterios de
   aceptación antes del build. Cubrir vertex/fragment válidos, rechazo de
   sintaxis inválida y diagnósticos, opciones/etapas, formato SPIR-V y consumo
   de la API instalada. Separar compilación host de ejecución en GPU.
3. **Preparación y build:** revisar/aplicar el parche
   `common/shaderc-changes.patch` de la receta fijada, conservar original,
   parche y diff. Ensamblar `third_party` con las revisiones verificadas, sin
   actualizar ramas. Compilar x86_64 con búsquedas aisladas y paralelismo
   acotado. Registrar que la receta usa `SHADERC_SKIP_TESTS=ON` y decidir
   explícitamente el subconjunto de pruebas disponible.
4. **Validación e instalación:** probar compilación/errores y consumir el
   paquete o biblioteca exportada en un proyecto nuevo; verificar arquitectura,
   enlaces, símbolos, manifiestos y dependencias previas. No sustituir la
   validación del resultado por una mera cabecera SPIR-V si hay validador
   disponible; registrar las limitaciones si no lo hay.
5. **Cierre:** repetir CMake PCSX2 en otro directorio, registrar el siguiente
   faltante real y reevaluar IB. Mantener pendientes exportador, estados,
   mapa real, otros escritores y cargador.

Aceptación: consumidor Shaderc probado y CMake que supere esa búsqueda;
no implica render Vulkan/Metal ni ejecutable completo de PCSX2.
