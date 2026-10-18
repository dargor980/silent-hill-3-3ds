# RapidYAML: consumo de API del observador host

Contrato [RY01–RY07](../../../schemas/pcsx2-rapidyaml-v1.md). YAML original,
sin recursos del juego. Cinco casos propios: estructura/conversiones UTF-8,
propiedad de datos, roundtrip modificado, límites de emisión y errores/recuperación.
No constituyen una suite completa de conformidad YAML.

Configurar este proyecto CMake con `SH3_RYML_BUILD_DIR` para probar el target
exportado del build antes de instalar, o `SH3_RYML_CONFIG_DIR` para el paquete
instalado exacto 0.12.1. Proporcionar la arquitectura/SDK y prefijo privado como
en la receta documentada. Un directorio instalado ausente es un error incluso
si existe otro paquete en `CMAKE_PREFIX_PATH`.

Con `SH3_RYML_SOURCE` se compilan también `samples/quickstart.cpp` y
`samples/quickstart-ints.cpp` originales del release verificado (el segundo
usa dos implementaciones de `src_extra`). CTest ejecuta cada programa en su
propio directorio; el primero escribe un YAML de ejemplo. Sus comprobaciones
no dependen de `assert` en Release. No se habilita `RYML_BUILD_TESTS`: la suite
completa descarga c4fs/c4log y otros repositorios adicionales, algunos con
referencias móviles. Los quickstarts seleccionados no sustituyen esa suite.

Compilar con `cmake --build <build> --parallel 2` y ejecutar
`ctest --test-dir <build> --output-on-failure`. Los callbacks propios lanzan
una excepción de parseo y se restauran por RAII; la biblioteca mantiene sus
callbacks predeterminados y sus opciones originales.
