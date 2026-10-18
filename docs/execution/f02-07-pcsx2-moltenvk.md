# F02.07 — MoltenVK del observador host

Estado: **MoltenVK 1.4.1 instalado y validado; CMake PCSX2 resuelve las
dependencias preparadas y el gate IB queda listo al cierre**.
[Contrato MV01–MV08](../../schemas/pcsx2-moltenvk-v1.md),
[consumidores propios](../../tests/fixtures/pcsx2-moltenvk/README.md) y
[evidencia SRC48](../compatibility/pcsx2-moltenvk-evidence.json).
El build completo del emulador y la instrumentación siguen pendientes.

## Procedencia y configuración

Archivo 1.4.1 de la receta PCSX2 fijada, **1.249.866 bytes**, SHA-256
`9985f141902a17de818e264d17c1ce334b748e499ee02fcb4703e4dc0038f89c`.
Extracción validada: 4.776.524 bytes, **263 archivos y diez enlaces**.
Se completan **25/25 descargas de receta verificadas** entre las etapas.
Las siete dependencias adicionales se obtuvieron con fetch superficial de
sus commits exactos, conservando originales y copias privadas:

| Dependencia | Commit de ExternalRevisions |
| --- | --- |
| cereal | `a56bad8bbb770ee266e930c95d37fff2a5be7fea` |
| Vulkan-Headers | `6aefb8eb95c8e170d0805fd0f2d02832ec1e099a` |
| SPIRV-Cross | `adec7acbf41a988713cdb85f93f26c8ca5ea863e` |
| SPIRV-Tools | `262bdab48146c937467f826699a40da0fdfc0f1a` |
| SPIRV-Headers | `b824a462d4256d720bebb40e78b9eb8f78bbb305` |
| Vulkan-Tools | `013058f74e2356347f8d9317233bc769816c9dfb` |
| Volk | `59660878571aa99e3c9a366bb1d19fdcd701f0e7` |

Son **6.963 archivos transitivos, 83.350.393 bytes**, verificados sin cambios
en originales y copias. Se usaron las cabeceras SPIRV-Tools pregeneradas del
archivo oficial. Volk/Vulkan-Tools se obtienen por el script del proveedor;
sus demos no se construyen en esta batería.

La [documentación fijada del proveedor](https://github.com/KhronosGroup/MoltenVK/tree/v1.4.1)
y sus proyectos se inspeccionaron antes del build. Los esquemas Xcode no
declaran Testables. Se aplicaron los dos parches PCSX2 y sus ajustes de
fetch/Makefile. El primero falló con fuzz=0 por campos de contexto ausentes
en 1.4.1. En una segunda copia se adaptó solo ese contexto: se conserva el
cambio Mac2→Mac1, sin añadir los campos ausentes. Ambos parches pasan con
fuzz=0; siete archivos difieren del original, incluidos los dos scripts.
Primer intento, rechazo, originales y diff final permanecen privados.

Xcode 26.6/Apple Clang 21, SDK macOS 26.5 y toolchain Metal instalado;
**Release, x86_64, mínimo macOS 11.0**, dos jobs, firma desactivada y
DerivedData/temporales privados. Settings, argumentos y Mach-O verificados.
El inventario completo incluye **298 entradas de compilación**: 241 externas
y 57 del paquete/conversor. El filtro inicial por sufijo omitía el target
estático; se corrigió antes de construir el paquete.

La receta fija `MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS=0` y
`MVK_CONFIG_USE_METAL_PRIVATE_API=1`. Esta última no habilita el soporte
compilado: falta `MVK_USE_METAL_PRIVATE_API`, cuyo valor predeterminado es 0;
el proveedor normaliza la configuración efectiva a 0. Flags, fuentes y
consulta runtime lo comprueban. Se mantiene la receta, sin añadir soporte
privado. La versión de driver usa formato decimal 10401, distinto de Vulkan.

## Capacidad y fallos conservados

MV03 exige 14 GiB para preparar, 13 GiB antes de construir, parada bajo
10 GiB y máximo de 4 GiB presupuestados/asignados en la etapa activa. IB
conserva su reserva general de 20 GiB. Se miden fuentes, copias, logs,
DerivedData y temporales; el muestreo no es una cuota de filesystem.

Los dos primeros intentos externos se interrumpieron al crear Xcode archivos
CAS dispersos: v8.index reserva 8 GiB y v8.data 16 GiB, con 16 KiB asignados
cada uno en la primera inspección. Desactivar la caché no evitó su creación.
La detención devolvió EPERM después de SIGTERM; se comprobó posteriormente
que no quedaban procesos de build. Ambos intentos permanecen fallidos.
El primero perdió sus muestras completas; el segundo conserva las lecturas
previas al error. DerivedData y logs fallidos se mantienen.

La política propia reconoce únicamente esos nombres/rutas/tamaños, cuenta
todos sus bloques y registra aparte la reserva lógica. Los demás archivos
conservan el mayor de tamaño lógico/asignado. **Siete pruebas** verifican
reservas, crecimiento, archivos ordinarios, tamaños inesperados y ocupación
completa; no prueban la detención de Xcode. El wrapper persiste ahora lecturas
y errores antes de salir. El supervisor base se conserva por hash; sus siete
controles históricos no se repitieron.

| Build aceptado | Duración | Muestras | Máximo presupuestado | Máximo asignado | Mínimo libre |
| --- | --- | --- | --- | --- | --- |
| Dependencias externas, v3 | 159,95 s | 101 | 1.335,68 MiB | 343,98 MiB | 20,60 GiB |
| Paquete MoltenVK | 53,88 s | 34 | 1.498,43 MiB | 522,74 MiB | 20,55 GiB |
| Consumidor final previo | 5,01 s | 5 | 547,17 MiB | 547,17 MiB | 20,51 GiB |
| Consumidor instalado | 5,29 s | 5 | 555,24 MiB | 555,24 MiB | 21,51 GiB |

El presupuesto incluye el tamaño lógico de archivos dispersos distintos de
los dos CAS reconocidos; no se elimina para mejorar la cifra.

## Pruebas y resultados

**8/8 antes y 8/8 después: 16 ejecuciones CTest finales**, sin fallos ni
omisiones. **Diez trazas adicionales** verifican la dylib exacta, sin
DYLD_LIBRARY_PATH. Diez ejecutables x86_64/macOS 11.0 verificados; ejecución
con Rosetta sobre host arm64 y GPU **Apple M2**.

| Caso | Resultado verificado |
| --- | --- |
| Perfil | Versión 1.4.1, driver correcto, Vulkan ≥1.1, carga privada y flags efectivos en 0. |
| Errores | Dylib/extensión inexistentes rechazadas, función desconocida ausente y recuperación posterior. |
| Transferencia | 256 palabras copiadas por GPU, barreras/fence y patrón CPU exacto. |
| Cómputo | GLSL propio→SPIR-V con Shaderc privado; 256 resultados i² × 3 + 7 exactos. |
| Imagen | Clear RGBA8 de 8×8, transiciones y lectura de 64 píxeles; RGB ±1 por UNORM, alpha exacto. |
| Tres originales | small_vector, msl_constexpr_test y msl_resource_bindings sin modificar. |

Los dos programas MSL comprueban API/uso de recursos con el wrapper C original
contra SPIRV-Cross de Xcode. No comparan todo el texto MSL ni representan la
suite completa. small_vector prueba headers, no código de la dylib. Tres
configuraciones negativas rechazan biblioteca y raíces de headers ausentes.
Los shaders coinciden por SHA-256 entre ambos consumidores.

Se conservan fallos iniciales del consumidor: namespace del wrapper C,
propagación al test de headers y uso de portability_enumeration sin loader.
CTest se inició una vez sobre un build incompleto; queda registrado como
fallido, y ahora el coordinador exige un build aceptado antes de probar.
Otro intento falló en dos casos por asumir soporte privado activo; se corrigió
la expectativa según fuente/flags, conservando biblioteca y tests originales.

RAII separa propiedad y operaciones; los oráculos CPU son independientes.
Las fences esperan cinco segundos y cada CTest tiene treinta segundos.
No se afirma rasterización/presentación, Vulkan CTS, validation layers,
sanitizers, rendimiento, estrés ni compatibilidad con todas las GPU.

## Instalación y continuidad

Se añadió **un archivo y ningún enlace**; los **5.227 archivos y 70 enlaces
anteriores** se preservan. Dylib de **5.359.904 bytes**, SHA-256
`451dc3872d37cc1cfb86d0529805726eaf170b5944fac46a790e4ecd5284ccae`,
idéntica por bytes a la compilada. x86_64, mínimo macOS 11.0, ID
`@rpath/libMoltenVK.dylib` y dependencias del sistema comprobados, sin rutas
de build en load commands. SPIRV-Cross/Tools permanecen privados, fuera del
prefijo instalado.

**CMake v18 configura y genera PCSX2**, encuentra MoltenVK y mantiene
FFmpeg/Qt/LinguistTools/KDDockWidgets resueltos. Desaparece el aviso anterior.
Checkout PCSX2 limpio. Gate **ready_for_baseline_build**, sin bloqueadores,
con **21,47 GiB** al cierre; debe repetirse antes de construir. Los cuatro
checks C++20/Metal son evidencia reutilizada de SRC31.

No se ejecutó el build completo PCSX2, CI remota, suite Python completa,
macOS 11 físico ni consola Nintendo. Instrumentación, mapa efectivo,
dos salas conectadas, F02.07 y Q05/G02 siguen pendientes.

La validación del repositorio termina **PASS, cero errores**; `git diff
--check` no detecta problemas. Se contrastaron ocho artefactos propios,
159 archivos de evidencia local antes del recibo de QA, el hash de SRC47
y 463 enlaces Markdown locales. No se encontraron rutas privadas en los
quince archivos públicos revisados. La CI remota y suite Python completa
no se ejecutaron en esta unidad.

## Siguiente unidad detallada

**origin/effective-mapping/instrumented-build/baseline-build**:

1. Revalidar commit limpio, hashes del prefijo y gate con al menos 20 GiB.
   Inventariar unidades, generación de recursos, LTO y bundle; fijar presupuesto
   para temporales/enlace y concurrencia. No extrapolar el consumo de MoltenVK.
2. Preparar carpeta/logs nuevos con Apple Clang/Metal y x86_64. Preservar la
   instalación oficial y su perfil. Añadir una comprobación documentada de
   cierre de procesos Xcode tras los EPERM antes de otro build largo.
3. Construir el baseline sin instrumentación bajo supervisión. Conservar
   fallos; aplicar cualquier corrección de compatibilidad en copia separada,
   con parche/hash y tests originales intactos.
4. Auditar ejecutable/bundle, frameworks/plugins, arquitectura, rutas y
   símbolos. Ejecutar tests originales disponibles y arranque acotado con
   perfil aislado. Distinguir compilación, configuración y ventana/ejecución
   observada; no cargar datos del juego en CI.
5. Tras aprobar el baseline, diseñar el observador: puntos de captura/pausa,
   traducción efectiva de rangos, evidencia de sesión y rechazo de capturas
   incompletas. Construirlo por separado y repetir el protocolo antes de
   retomar las dos salas del corpus.
