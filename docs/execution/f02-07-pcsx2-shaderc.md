# F02.07 — Preparación de Shaderc para el observador host

Fecha: 2026-10-17. Subunidad preparada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-shaderc/prepare`.
Contrato [SC01–SC08](../../schemas/pcsx2-shaderc-v1.md), evidencia
[SRC37](../compatibility/pcsx2-shaderc-evidence.json).

Los cuatro archivos fijados están verificados y ensamblados; CMake configura
Shaderc y sus componentes. Se reprodujo y corrigió un error del wrapper C++
del parche de PCSX2. Pasan comprobaciones de sintaxis C/C++ y el negativo de
biblioteca ausente. **El build de biblioteca, los tests de ejecución y la
instalación siguen pendientes de capacidad**; la unidad completa no está
aceptada. Tampoco se cierra F02.07/Q05/G02.

## Fuentes y avisos

Receta PCSX2 fijada al commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, sin modificar el checkout.

| Archivo/componente | Bytes comprimidos | SHA-256 |
|---|---|---|
| Shaderc 2026.2 | 228.959 | `f924178e75e3293082481b25ed64d5e48a795b479dac3bd3c83d23070855df42` |
| glslang `275822a6261ee689aadb1da5f09a0ec2f058685c` | 4.333.168 | `971848a1cc639ce8dc244e778b17efe0f690e32ac398a75e31d1c67ad06d3e0a` |
| SPIRV-Headers `58006c901d1d5c37dece6b6610e9af87fa951375` | 566.868 | `a6cb1b300bb8171795e116457e858e555334749f9cacaed8068ae0ef8681110c` |
| SPIRV-Tools `6337eb62cadd7d124ac6789bf39c0f71148f0a73` | 3.478.862 | `e156be0bd81c8812f1bff8e520422bfa9df61b3045587b9eb483185f1074a7b2` |

URLs y tamaños descomprimidos constan en SRC37. Se conservaron originales
separados del árbol ensamblado. Comparación: **217 + 3.348 + 115 + 1.738 =
5.418 archivos**, todos idénticos a sus archivos de origen. Las tres
dependencias incorporadas permanecen sin cambios en el árbol de trabajo.
No se ejecutaron scripts de actualización de ramas.

Shaderc y SPIRV-Tools conservan Apache-2.0; glslang conserva su inventario
BSD de dos/tres cláusulas, MIT y Apache-2.0. SPIRV-Headers conserva sus avisos
Khronos, excepciones por archivo, JsonCpp MIT/dominio público y CC-BY-4.0
para los archivos documentales indicados. Los textos completos y hashes se
retienen; no se asigna una única licencia a todo el conjunto ni se distribuye
un bundle. LIC08 permanece pendiente.

## Parche y defecto confirmado

El parche de receta `common/shaderc-changes.patch` tiene SHA-256
`351f0e758a723d165b418f5bc7c9dbcae2999193b69fd12072298bc05475ab57`.
Modifica ocho archivos: construye la dylib, limita instalación/exportación de
componentes y añade la API personalizada de depuración que consume PCSX2.

El wrapper `shaderc.hpp` declaraba `non_semantic_debug_info` y usaba
`non_sematic_debug_info`. La inclusión del header real falla con Apple Clang;
no es una inferencia basada solo en lectura del diff. La
[corrección separada](../../tests/fixtures/pcsx2-shaderc/header-typo.patch)
cambia únicamente ese identificador. El mismo
[probe](../../tests/fixtures/pcsx2-shaderc/header_probe.cpp) pasa después.
Se conserva el header previo, ambos parches y el diff final; el checkout
PCSX2 permanece limpio. Esta corrección es una desviación explícita respecto
de la receta, no una nueva versión de Shaderc.

La comparación inicial detectó cuatro backups `.orig` creados al aplicar el
parche y dos archivos Finder `.DS_Store`. Los backups coinciden con sus
originales y se conservaron; los metadatos Finder se identificaron como
archivos ajenos a compilación, sin borrarlos. Los ocho cambios de código son
exactamente los previstos por el parche y la corrección del header.

## Diseño y pipeline preparados

CMake configuró Release/x86_64, destino macOS 11.0, Apple Clang 21/SDK 26.5,
prefijo privado y búsquedas aisladas. La receta mantiene
`SHADERC_SKIP_TESTS=ON`, `SHADERC_SKIP_EXAMPLES=ON` y
`SHADERC_SKIP_COPYRIGHT_CHECK=ON`. SPIRV-Tools se configura estático y sin
ejecutables; el validador de fixtures enlazará esa biblioteca sin instalarla.

Los [fixtures propios](../../tests/fixtures/pcsx2-shaderc/README.md) separan
recursos RAII, validación SPIR-V, casos de API y resolución CMake. Usan shaders
originales, sin datos del juego. Seis casos preparados:

1. Vertex/fragment: éxito, modelo de ejecución y validación del módulo completo.
2. Opciones: macros, preprocesador y optimización con efectos observables.
3. Errores: GLSL inválido, etapa incompatible, diagnóstico y recuperación.
4. Validador: rechazo de módulo truncado/corrupto y aceptación del original.
5. API C personalizada: depuración convencional y no semántica.
6. Wrapper C++: paso de la opción de depuración personalizada al compilador.

También se prepara el smoke C original del proveedor, enlazado a la dylib y
con `-UNDEBUG`. No requiere GTest ni cambios del fuente original. La suite
completa necesita dependencias adicionales y queda expresamente sin ejecutar.

| Diagnóstico ejecutado | Resultado |
|---|---|
| Aplicación del parche fijado | Código 0 |
| Header C++ antes de corregir | Código 1 esperado; identificador no declarado |
| Corrección mínima + mismo header | Código 0 |
| Configuración CMake de biblioteca/componentes | Código 0 |
| Inventario CTest de biblioteca | 0 tests; no se cuenta como aprobación |
| Sintaxis del fixture C++ con warnings como errores | Código 0 |
| Sintaxis del smoke C original | Código 0 |
| Consumidor con biblioteca explícita inexistente | Código 1 esperado |

**Ninguno de los siete casos de ejecución preparados se ha ejecutado.** La
sintaxis no prueba enlace, compilación de GLSL ni validez SPIR-V. Tampoco se
ha probado render Vulkan/Metal/3DS, rendimiento o contenido del juego.

## Capacidad y estado preservado

La primera medición fue 17,58 GiB. Tras la respuesta del usuario, el control
previo al build midió **19,23 GiB**, por debajo de los 20 GiB de
[IB02](../../schemas/pcsx2-build-preflight-v1.md), y terminó antes de invocar
la compilación. Una segunda respuesta del usuario dio lugar a otra medición:
**19,12 GiB**, también insuficiente; `df` y la lectura directa coinciden.
Entre ambas comprobaciones se observaron 18,90 GiB. Esta
reserva es política del proyecto, no consumo medido ni requisito oficial de
Shaderc. Los cambios del volumen no se atribuyen íntegramente a este trabajo.

Se solicitó liberar margen adicional y se completó el trabajo independiente.
No se borraron fuentes, compilaciones previas ni archivos del usuario.
El coordinador vuelve a medir espacio inmediatamente antes de construir;
una respuesta del usuario no sustituye esa medición.

Las **20 dylibs existentes** conservan sus hashes. Este inventario incluye
`libc4core.0.2.12.dylib`, ya presente en el manifiesto de 155 entradas de SRC36,
pero no enumerada en su lista resumida de bibliotecas: 33.072 bytes, x86_64,
SHA-256 `b4954d00e2a8a37a7ce2b18c0a546400fcd020660acc85987d3b662b4604c6dc`.
SRC37 complementa ese inventario; ryml incorpora c4core y no enlaza esa dylib.

Van **16 de 25 archivos de receta verificados**, más NASM/FontTools auxiliares.
No se repitió CMake de PCSX2 porque aún no se instala Shaderc: el último
resultado sigue siendo `baseline-configure-v8` de SRC36. El gate
`preflight-v8.json` reutiliza ese resultado y los cuatro checks de SRC31;
mantiene `storage_reserve` y `pcsx2_configure`. No son nuevas ejecuciones.

Logs, argumentos, entorno, comparación y hashes quedan en la etapa privada
y `build/f02-07-pcsx2-shaderc/`. Los controles de repositorio y
`git diff --check` pasan. No se ejecutó CI remota ni se repitió la batería
Python histórica de 1.897 casos.

## Reanudación: `dependencies-shaderc/build-and-validate`

1. Medir al menos 20 GiB libres. Ejecutar el build configurado con dos jobs,
   conservando cualquier fallo; no reinstalar ni repetir la descarga.
2. Enlazar el consumidor con la dylib de build y SPIRV-Tools estático del mismo
   conjunto. Ejecutar los seis casos propios y el smoke C; registrar JUnit/logs.
3. Solo si pasan, instalar y repetir desde un consumidor nuevo del prefijo.
   Confirmar biblioteca ausente rechazada aun con prefijo válido, arquitectura,
   símbolos personalizados, carga privada y manifiesto.
4. Comparar otra vez fuentes y las 20 dylibs previas. Conservar parches y
   declarar la suite completa omitida; actualizar licencias/evidencia.
5. Ejecutar CMake PCSX2 en `baseline-configure-v9`, registrar el siguiente
   faltante real y reevaluar IB. Mantener pendientes build completo,
   exportador, estados, mapa efectivo, otros escritores y cargador.
