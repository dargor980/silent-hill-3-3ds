# Shaderc: fixtures del observador host

Contrato [SC01–SC08](../../../schemas/pcsx2-shaderc-v1.md). Shaders propios,
sin recursos del juego. Preparación y ejecución se registran por separado en
la evidencia: comprobar sintaxis no significa que estos casos hayan pasado.

`header_probe.cpp` reproduce el error del wrapper C++ del parche PCSX2 fijado.
`header-typo.patch` corrige únicamente el identificador mal escrito, después
del parche de receta y conservando ambos. No cambia la API personalizada.

El consumidor CMake exige rutas existentes y explícitas:

- `SH3_SHADERC_INCLUDE`: headers de Shaderc del árbol de trabajo o instalación.
- `SH3_SHADERC_LIBRARY`: dylib concreta del build o prefijo privado.
- `SH3_SPIRV_INCLUDE`: `include` de SPIRV-Tools fijado.
- `SH3_SPIRV_HEADERS_INCLUDE`: `include` de SPIRV-Headers fijado.
- `SH3_SPIRV_LIBRARY`: biblioteca estática SPIRV-Tools del mismo build.
- `SH3_SHADERC_SOURCE`: opcional, fuente privada para el smoke C original.

El target importado de Shaderc usa las mismas definiciones del módulo de PCSX2;
la receta parcheada no instala exports CMake. SPIRV-Tools es un validador de
test enlazado estáticamente, sin instalarlo en el prefijo de dependencias.

Seis casos: etapas vertex/fragment; macros/preprocesador/optimización;
GLSL inválido, etapa incompatible y recuperación; módulos truncados/corruptos;
depuración C convencional/no semántica; wrapper C++ personalizado.
Los módulos válidos pasan por `spvValidateBinary` con Vulkan 1.0/SPIR-V 1.0.
Después se inspeccionan etapas/imports/instrucciones de depuración.
No se usa un hash observado como oráculo ni se afirma ejecución de shaders.

El smoke C original se compila sin cambios con `-UNDEBUG`, enlazado a la dylib
personalizada. Esto no ejecuta la suite completa del proveedor, desactivada
por la receta. Compilar con `cmake --build <build> --parallel 2` y ejecutar
`ctest --test-dir <build> --output-on-failure`, antes y después de instalar.

Antes del build del grupo completo se debe satisfacer IB02. Los diagnósticos
pequeños admitidos incluyen `-fsyntax-only` con los headers reales y la
configuración CMake. Los helpers RAII, validación de módulo y casos mantienen
responsabilidades separadas; ninguno forma parte del runtime 3DS.
