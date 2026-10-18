# Consumidores MoltenVK 1.4.1

Código propio para [MV01–MV08](../../../schemas/pcsx2-moltenvk-v1.md).
Los consumidores usan Vulkan directamente contra una dylib explícita.
No contienen datos del juego ni descargan dependencias.

| Caso | Comprobación |
| --- | --- |
| `mv_profile` | Carga mediante dladdr, versión decimal 10401, driver MoltenVK, Vulkan ≥1.1 y configuración efectiva. |
| `mv_errors` | Dylib ausente, extensión inexistente, función desconocida y posterior instancia/dispositivo válidos. |
| `mv_transfer` | Copia GPU de 256 palabras con patrón propio, barreras, fence y comparación exacta en CPU. |
| `mv_compute` | Shader GLSL propio convertido con Shaderc privado; 256 resultados de `i² × 3 + 7` calculados en GPU y contrastados exactamente. |
| `mv_image` | Imagen RGBA8 de 8×8, clear, transiciones y copia a memoria host; RGB admite ±1 por cuantización UNORM, alpha exige 255. |
| `provider_small_vector` | Programa original de contenedores, headers y namespace original, asserts activos. No acredita el código de una dylib. |
| `provider_msl_constexpr_test` | Programa/datos originales; API C contra SPIRV-Cross de MoltenVK y comprobaciones originales de samplers/uso. |
| `provider_msl_resource_bindings` | Programa/datos originales; bindings y uso de recursos MSL. No compara todo el texto MSL contra una referencia. |

`fixture.hpp` separa propiedad de instancia/dispositivo, comandos y buffers.
Los recursos se liberan después de una fence; la espera es de cinco segundos.
Si la GPU no termina, el proceso falla sin liberar objetos en uso; CTest acota
cada proceso a treinta segundos. No se confunde una consulta API con un trabajo
GPU completado. No hay presentación en pantalla, rasterización de geometría,
Vulkan CTS, capas de validación, sanitizers ni pruebas físicas en Nintendo 3DS.

Configurar con las siete rutas explícitas `SH3_VULKAN_INCLUDE`,
`SH3_MVK_INCLUDE`, `SH3_MVK_LIBRARY`, `SH3_SHADERC_INCLUDE`,
`SH3_SHADERC_LIBRARY`, `SH3_CROSS_SOURCE` y `SH3_CROSS_LIBRARY`, además del
toolchain x86_64/macOS 11.0. Las rutas ausentes se rechazan. Compilar con CMake
y ejecutar CTest con `--output-on-failure --output-junit`. Repetir en una
carpeta nueva después de instalar, sin `DYLD_LIBRARY_PATH`; las trazas
`DYLD_PRINT_LIBRARIES` deben confirmar la ruta exacta en cada caso propio.

Los originales SPIRV-Cross se leen del checkout privado, sin cambiarlos.
Se compila su wrapper C con `SPIRV_CROSS_NAMESPACE_OVERRIDE=MVK_spirv_cross`
para coincidir con la biblioteca Xcode; esa definición es privada al wrapper.
El programa small_vector conserva el namespace original de sus headers.
Se retienen los fallos iniciales de enlace/namespace e integración Vulkan.

La extensión portability_enumeration solo se activa si está anunciada; la
conexión directa a MoltenVK no la anuncia. La receta fija argument buffers en
0 y solicita configuración de API privada en 1, pero no compila soporte
`MVK_USE_METAL_PRIVATE_API`; el proveedor fuerza el valor efectivo a 0.
El consumidor verifica ambos valores efectivos en 0. La expectativa inicial
incorrecta se conserva como fallo, con la explicación basada en fuente/flags.

`capacity.py` mide todos los bloques asignados. Solo reconoce las reservas
dispersas CAS de 8/16 GiB observadas en Xcode y mantiene su tamaño lógico por
separado; cualquier otro archivo conserva ambos límites. Ejecutar sus siete
pruebas con `python -m unittest discover -s tests/fixtures/pcsx2-moltenvk
-p test_capacity.py -v`. Esta batería prueba la política de medición, no la
detención de procesos ni una cuota de filesystem.
