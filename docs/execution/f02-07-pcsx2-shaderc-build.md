# F02.07 — Shaderc compilado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-shaderc/build-and-validate`.
Contratos [SC01–SC08](../../schemas/pcsx2-shaderc-v1.md) y excepción acotada
[SB01–SB05](../../schemas/pcsx2-shaderc-bounded-build-v1.md); evidencia
[SRC38](../compatibility/pcsx2-shaderc-build-evidence.json).

Shaderc **2026.2** quedó compilado e instalado como biblioteca compartida
x86_64. Pasan **7/7 casos antes y 7/7 después de instalar**, incluidos errores,
opciones, API personalizada y validación completa de módulos SPIR-V. CMake de
PCSX2 supera Shaderc y se detiene ante **Qt 6**. FFmpeg también sigue ausente,
según el aviso previo de esa configuración. Build completo PCSX2, exportador,
mapa efectivo y F02.07/Q05/G02 permanecen pendientes.

## Capacidad: corrección de una decisión demasiado conservadora

La [preparación SRC37](f02-07-pcsx2-shaderc.md) había aplicado la reserva
genérica de 20 GiB a Shaderc sin medir su build. En esta continuación el
volumen todavía informó unos 19,1 GiB. Se sustituyó ese bloqueo para esta
biblioteca por una excepción explícita, documentada antes de compilar:
inicio con al menos 18 GiB, dos jobs, presupuesto de 2 GiB de archivos de
build y terminación si el volumen baja de 16 GiB libres.

El coordinador puso temporales del compilador dentro del directorio medido,
inició su propio grupo de procesos y vigiló espacio y tamaño nominalmente
cada segundo. No borró archivos ni amplió límites. La reserva general de
20 GiB del evaluador IB permanece intacta para builds grandes y PCSX2 completo.
La excepción no se extiende automáticamente a Qt o MoltenVK.

| Medición del build | Resultado |
|---|---|
| Duración | 139,98 s |
| Muestras | 140 |
| Espacio libre inicial | 20.517.216.256 bytes, aproximadamente 19,11 GiB |
| Mínimo libre observado | 20.432.064.512 bytes, aproximadamente 19,03 GiB |
| Máximo lógico del directorio | 102.962.234 bytes |
| Máximo asignado del directorio | 105.697.280 bytes, aproximadamente 100,80 MiB |
| Salida / motivo de terminación preventiva | 0 / ninguno |

La vigilancia es muestreo, no una cuota de disco ni una garantía de capturar
picos entre muestras. No se provocó falta de disco para probar la terminación
de emergencia. El cambio del espacio del volumen tampoco se atribuye
íntegramente a la compilación. El tamaño medido muestra que la reserva de
20 GiB era excesiva para este intento concreto; no predice otros builds.

## Procedencia y configuración

Se reutilizaron los cuatro archivos verificados de SRC37 y sus revisiones,
sin nuevas descargas. Se comprobaron hashes de contrato/fixtures y parches
antes de compilar. Release, destino macOS 11.0, Apple Clang 21/SDK 26.5,
x86_64 y búsquedas privadas aisladas.

El parche de la receta PCSX2 y la corrección de `non_sematic_debug_info`
permanecen separados. El diff posterior coincide con el anterior:
`19b571ed8eec8661404a3b748b3b45b9c2d3c4f5aad2e4ff6380bf539e8ead7e`.
Los **5.418 archivos originales** siguen intactos; el árbol de trabajo conserva
solo los ocho archivos modificados previstos. Los tres componentes
incorporados no recibieron parches.

El build generó cinco caches Python `__pycache__`. El primer comprobador los
detectó como archivos adicionales; se registraron por separado y se verificó
que cada fuente `.py` pertenece al archivo original. Se conservan también los
backups del parche y metadatos Finder identificados en SRC37. No se borraron
para hacer pasar la comparación. Fuentes/licencias y checkout PCSX2 permanecen
conservados; LIC08 sigue pendiente para un eventual bundle.

## Pruebas reales

Se ejecutaron los [fixtures definidos previamente](../../tests/fixtures/pcsx2-shaderc/README.md)
sin cambiar sus expectativas después de observar resultados.

| Caso | Evidencia |
|---|---|
| Etapas | Vertex/fragment propios compilan; modelos de ejecución y SPIR-V 1.0 correctos |
| Opciones | Preprocesador expande macros; macros y optimización cambian el módulo; resultados válidos |
| Errores | GLSL inválido y etapa incompatible rechazados con diagnóstico; compilación posterior recuperada |
| Validador | SPIRV-Tools acepta el módulo y rechaza truncado/magic corrupto con diagnóstico |
| Depuración C | API personalizada distingue sin depuración, convencional y no semántica |
| Depuración C++ | Wrapper corregido transmite la opción no semántica; ambos resultados válidos |
| Smoke C original | Compila un shader del proveedor mediante la dylib personalizada, con `-UNDEBUG` |

Son siete casos distintos, **catorce ejecuciones CTest**, sin fallos, skips ni
deshabilitados. Cada resultado válido pasa por `spvValidateBinary` para Vulkan
1.0/SPIR-V 1.0 antes de inspeccionar instrucciones/imports; no se verifica solo
la cabecera binaria. No se usa un hash observado como referencia de contenido.

El validador estático del mismo conjunto es x86_64, pesa **3.330.544 bytes** y
tiene SHA-256 `1542b4d40dbbb635fbd66be7fac869204d897d55515a4b0fff414cddfe026259`.
Permanece en el build de pruebas, sin instalarlo en el prefijo del emulador.
La biblioteca Shaderc y ambos ejecutables consumidores son x86_64.

La receta mantiene la suite completa desactivada: inventario CTest del
proveedor de cero casos, sin contarlo como aprobación. Se ejecutó únicamente
su smoke C seleccionado, además de los seis casos propios. No se validaron
shaders arbitrarios, fuzzing, sanitizers, ejecución GPU, rendimiento o datos
del juego.

## Instalación y configuración PCSX2

| Biblioteca instalada | Bytes | SHA-256 |
|---|---|---|
| `libshaderc_shared.1.dylib` | 7.167.128 | `d4f56abb1792667be32f4e5434377c866a0688fecfe30f156bd861e4adf43b9f` |

El manifiesto contiene ocho entradas presentes: cinco headers, dylib,
symlink y `shaderc.pc`. Los headers instalados coinciden con la fuente
parcheada. Se verificaron símbolos de compilación y depuración, carga de la
dylib privada y ausencia de includes/enlaces Homebrew en los targets. Las
**20 dylibs anteriores** conservan sus hashes. Un consumidor con biblioteca
explícita ausente sigue siendo rechazado aunque el prefijo instalado sea válido.

`baseline-configure-v9` encuentra Shaderc privado, CURL 8.7.1 y PCAP del SDK;
el ensayo de enlace de PCAP pasa. La ausencia de `pcap_get_pfring_id` y Vtune
no detiene esta configuración. FFmpeg no se encuentra y CMake avisa que usa
headers incluidos. Esto no acredita FFmpeg enlazado: `USE_LINKED_FFMPEG=ON`
se mantiene y su instalación sigue pendiente.

El primer error fatal ahora es `find_package(Qt6 6.10.1 ...)`: faltan los
paquetes Qt. No se deshabilitó su interfaz para ocultar el requisito. El
checkout PCSX2 sigue limpio; no se comprueban todavía todas las dependencias
posteriores. Van **16/25 archivos de receta verificados**, más NASM/FontTools
auxiliares; el snapshot inicial no se modifica.

El gate `preflight-v9.json` mantiene `storage_reserve` y `pcsx2_configure`:
al verificar la instalación había aproximadamente **18,98 GiB** libres. Sus
cuatro resultados de toolchain se reutilizan de SRC31; CMake v9 sí es nuevo.
El build acotado de Shaderc no convierte ese gate en aprobado.

## Pipeline y siguiente unidad

Contratos, administración de procesos, compilación, helpers RAII, validación
SPIR-V y resolución CMake mantienen responsabilidades separadas. Logs,
argumentos, mediciones, JUnit y hashes se conservan en la etapa privada y
`build/f02-07-pcsx2-shaderc-build/`. SRC38 publica solo metadatos.
Controles del repositorio y `git diff --check` aprobados; no se ejecutó CI
remota ni se repitieron los 1.897 tests Python históricos.

Sigue **`prerequisites/dependencies-qtbase`**:

1. **Procedencia y capacidad:** verificar `qtbase-everywhere-src-6.11.1.tar.xz`
   contra la receta. Medir espacio antes del build grande con la reserva IB02
   de 20 GiB; la excepción de Shaderc no aplica. Separar herramientas host,
   bibliotecas x86_64 y builds auxiliares si la configuración lo requiere.
2. **Contrato y diseño:** definir EARS para Core/Gui/Widgets y herramientas
   `moc`/`rcc`/`uic`; fixtures propios de señales/eventos, recursos, imágenes
   y widgets con plataforma sin ventana cuando proceda. Distinguir prueba
   offscreen de UI visible y de render del emulador.
3. **Parches y build:** revisar los parches de receta `qt-macos11compat.patch`,
   `qt110-xcode264.patch` y el cambio inline de `macdeployqt`; comprobar su
   aplicación sobre 6.11.1 sin asumir compatibilidad por el nombre. Conservar
   originales/diffs y usar las opciones MinSizeRel/no-framework de la receta,
   con PNG/JPEG/zlib/FreeType/HarfBuzz privados y búsqueda aislada.
4. **Validación:** ejecutar un subconjunto explícito de tests del proveedor
   y fixtures propios; compilar un consumidor nuevo con targets Qt exportados,
   verificar versiones, herramientas, plugins, arquitectura, carga y manifiesto.
   Instalar solo después de pasar la validación disponible.
5. **Continuidad:** registrar módulos aún pendientes. PCSX2 también exige
   LinguistTools (Qt Tools); Qt Base por sí solo no satisface toda su búsqueda.
   Mantener en backlog Qt SVG/imageformats/translations/Tools, QtApng,
   KDDockWidgets, FFmpeg y MoltenVK según la receta y los faltantes observados.
   Repetir CMake/gate sin anunciar completado el emulador ni el mapa.
