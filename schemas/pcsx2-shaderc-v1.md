# SC v1 — Shaderc para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-shaderc`.
Hereda [DB01–DB08](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **SC01 — Procedencia.** CUANDO prepare Shaderc 2026.2, el procedimiento
  DEBERÁ verificar sus cuatro archivos de receta, conservar originales y avisos,
  y ensamblar glslang/SPIRV-Headers/SPIRV-Tools en las revisiones fijadas,
  sin actualizar ramas ni descargar dependencias implícitas.
- **SC02 — Parches.** CUANDO aplique el parche PCSX2, el procedimiento DEBERÁ
  conservar su hash, resultado y diff frente al original. SI un diagnóstico
  demuestra un defecto en el parche, DEBERÁ aislar la corrección mínima en otro
  parche y conservar resultados antes/después, sin modificar el checkout PCSX2.
- **SC03 — Capacidad y build.** ANTES del build del grupo C++, el procedimiento
  DEBERÁ comprobar la reserva IB02. SI es insuficiente, DEBERÁ limitarse a
  preparación y diagnósticos pequeños. CUANDO compile, DEBERÁ usar Release
  x86_64, prefijo privado, búsquedas aisladas y paralelismo acotado; DEBERÁ
  declarar las suites omitidas por las opciones de la receta.
- **SC04 — Compilación.** CUANDO pruebe la API, el fixture DEBERÁ compilar
  shaders vertex/fragment propios, verificar éxito, etapa y versión SPIR-V,
  y validar los módulos completos con SPIRV-Tools del conjunto fijado.
  CUANDO active optimización o macros, DEBERÁ verificar resultados válidos y
  efectos observables de las opciones, sin exigir hashes binarios universales.
- **SC05 — Errores.** CUANDO reciba GLSL inválido o una etapa incompatible,
  el fixture DEBERÁ exigir fallo de compilación y diagnóstico no vacío.
  CUANDO el validador reciba SPIR-V truncado o corrupto, DEBERÁ rechazarlo
  con diagnóstico. DEBERÁ comprobar compilación válida después de un error.
- **SC06 — API personalizada.** CUANDO pruebe los headers instalados, el
  fixture DEBERÁ exigir `SHADERC_PCSX2_CUSTOM` y ejercitar la firma personalizada
  de información de depuración mediante API C y wrapper C++. DEBERÁ distinguir
  depuración convencional y no semántica mediante el módulo emitido.
- **SC07 — Consumo.** CUANDO instale una biblioteca aprobada, el procedimiento
  DEBERÁ repetir casos desde un consumidor nuevo de la biblioteca compartida
  explícita, rechazar un prefijo ausente y verificar arquitectura, símbolos,
  carga efectiva, manifiesto y conservación de bibliotecas anteriores.
- **SC08 — Continuidad.** CUANDO termine, el procedimiento DEBERÁ repetir
  CMake PCSX2 en un directorio nuevo y reevaluar IB. SI solo se prepararon
  fuentes o se comprobó sintaxis, DEBERÁ mantener pendientes compilación,
  instalación y pruebas de ejecución. F02.07/mapa/build completo seguirán
  pendientes hasta disponer de sus evidencias específicas.

## Diseño y tareas

Los originales y el árbol de trabajo parcheado permanecen separados. El
coordinador registra cada paso y comprueba IB02 antes de construir. CMake del
consumidor resuelve rutas explícitas; un helper RAII administra recursos de
Shaderc, otro valida SPIR-V. Los casos prueban APIs/errores y opciones con GLSL
propio. No se crea runtime gráfico ni se añade Shaderc al código 3DS.

1. Verificar cuatro archivos y avisos; ensamblar árbol privado (SC01).
2. Aplicar parche de receta y diagnóstico mínimo de headers; documentar y
   comprobar cualquier corrección necesaria (SC02/SC06).
3. Definir casos y oráculos; comprobar sintaxis con headers reales. Configurar
   biblioteca sin ejecutar todavía el build si IB02 no pasa (SC03–SC06).
4. Con reserva suficiente, compilar con dos jobs y registrar inventario CTest.
   Probar API y módulo con SPIRV-Tools, más smoke C original si es compatible
   con la API personalizada; conservar cualquier omisión (SC03–SC06).
5. Instalar únicamente tras pruebas satisfactorias, repetir consumidor,
   negativos, arquitectura, símbolos y carga (SC07).
6. Publicar evidencia, actualizar backlog y repetir CMake/gate (SC08).

Aceptación final: biblioteca y consumidores x86_64 probados, módulos validados
y CMake que supera Shaderc. La preparación no constituye esa aceptación y
la compilación de shaders no demuestra ejecución Vulkan/Metal/3DS.
