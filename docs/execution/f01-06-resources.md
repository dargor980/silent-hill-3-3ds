# F01.06 — recursos y diagnóstico acotado

Fecha: **2026-10-16**. Implementación y validación automatizada completadas; build ARM **327b5e3355ee**. Arranque observado en Azahar, nueva página no confirmada mediante entrada automatizada. **B_app, CPU/launcher físicos y consola pendientes; F01.06/G01 permanecen abiertos.** No se leyó ni montó la ISO.

## Cambios y límites

[Ticket detallado](../specs/sh3-3ds/tasks/F01.md#f0106), [contrato EARS R01-R10 y protocolo diagnostic-v1](../compatibility/resource-contract.md), [procedimiento físico](../compatibility/resource-probe.md).

`ResourceProbe` consulta capacidad heap/lineal, libre lineal/VRAM, capacidad y uso de región APPLICATION, familia New, flag homebrew y límite APT. Conserva Result de cada servicio y distingue disponible, desconocido, error e inválido. Rechaza uso negativo/superior a capacidad, lineal libre superior a capacidad y porcentaje mayor que 100. La salida escrita por un servicio fallido no se presenta como válida. La región APPLICATION no es memoria exclusiva del proceso; no se suman pools. El flag homebrew no identifica launcher/versiones y el porcentaje APT no mide MHz. B_app, heap libre y reloj físico quedan UNKNOWN.

`TimingWindow` es portable y conserva 120 intentos tras 60 de calentamiento, sin asignaciones dinámicas propias; sobrescribe el más antiguo. Calcula p95 nearest-rank y máximo sobre intervalos válidos, con cantidades válidas/no disponibles. Hay tres fronteras: FrameBegin (espera y SDK), dibujo/envío y lectura de contadores audio. Se mide tiempo transcurrido en el hilo CPU, incluido posible bloqueo; no es tiempo activo puro ni ejecución GPU/DSP. No se suman subsistemas ni se inventa instrumentación de simulación, animación o carga todavía ausentes. Un retroceso del contador invalida el intervalo; cero sigue siendo válido.

La vista añade SELECT para alternar páginas sin guardar opciones; START tiene prioridad. Los recursos/resúmenes se renuevan en el primer intento y cada 60 posteriores. Estado running/paused y hooks de suspensión/reanudación reinician ventana/calentamiento. El ring lifecycle previo conserva sus 32 eventos. No se escribe un log de telemetría por frame ni se prueba memoria mediante agotamiento. Las responsabilidades de consulta, retención/estadística y vista quedan separadas; dominio y puertos siguen sin dependencias SDK.

## Validación ejecutada

| Entorno / caso | Resultado |
|---|---|
| AppleClang 15, Debug | **37/37 CTest** |
| AppleClang 15, Release/NDEBUG | **37/37 CTest** |
| LLVM 22.1.4, ASan + UBSan | **37/37**, sin hallazgos |
| GCC 12.2, Linux ARM64 limpio | **37/37 CTest** |
| Cobertura de bibliotecas portables | **300/301 líneas (99.67 %)**, **217/222 ramas (97.75 %)**, **38/38 funciones** |
| Python 3.14.6 | **227/227**; líneas **641/668 (95.96 %)** y ramas **260/274 (94.89 %)**; gate aprobado |
| Calidad | Ruff check/format (22 archivos), comprobador del repo (0 errores), actionlint y sintaxis Bash pasan |
| SDK ARM real | **12 unidades C++**, ELF/SMDH/3DSX generados; create/verify del bundle PASS |
| CI remota | No ejecutada; targets CMake quedan incluidos en los jobs existentes |

Los seis casos CTest nuevos son `timing_window`, `ctr_resources` y cuatro escenarios de composición: `resources_page`, `resources_failure`, `resources_refresh`, `resources_sleep`. Hay 29 casos con etiqueta sdk-double. Se ejercitan ceros/fallos/valores inválidos, salida del servicio escrita aun con Result fallido, percentil con outlier (p95 distinto de máximo/media), reloj regresivo, ring vacío/parcial/10000 escrituras, reset tras ventana llena, prioridad SELECT/START y frecuencia de muestreo. La vista de recursos normal capturada en host ocupa como máximo 39 columnas y 29 filas. Los checks siguen activos en Release.

Los dobles validan contratos de adaptador y composición, no kernel/APT/GPU físicos. Cobertura excluye código 3DS y dobles; no se amplió su denominador para aparentar validación del hardware. GCC/gcovr generó XML y JSON correctamente; avisó que su opción genérica de output no se usó al pasar destinos explícitos. No hubo warnings de compilación en los logs del proyecto.

Comandos: `cmake --preset host-debug/host-release/host-sanitize` (cada preset por separado), build y CTest con JUnit; sanitize usa `/opt/homebrew/opt/llvm/bin/clang++` y `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Python: `.venv/bin/python -m pytest --cov=tools --cov-report=xml:build/f01-06/python-coverage.xml --cov-report=json:build/f01-06/python-coverage.json --junitxml=build/f01-06/pytest.xml`, seguido por `tools.qa.coverage_gate`. Logs y JUnit se conservan en `build/f01-06/host-*.log`, `host-*-tests.xml`, `python-tests.log`, `pytest.xml`, `quality.log` y los reportes de cobertura.

## Ejecución emulada

Azahar **2126.2 ARM64**, macOS 26.5/Apple M2, New3DS/JIT/CPU 100 %, Vulkan/MoltenVK y audio HLE. Se reutilizó el paquete oficial verificado en F01.05 y su carpeta portátil de trabajo; se archivaron nuevas copias de log/config en F01.06. No se lanzó GDB, no se agregó firmware ni contenido original.

Observación visual mediante Computer Use: patrón verde, build **327b5e3355ee**, estado running, `Probe: OK`, `Load: MISSING`, `Save: NOT_RUN`; NDSP sigue `NDSP_INIT_FAILED`, Result **0xd880a7fa**, canal unavailable. Esto prueba arranque/render de la página inicial y lectura del fixture en ese entorno; no escucha ni recursos físicos.

SELECT está mapeado en el perfil a tecla N (código 78). Los intentos mediante pressKey no confirmaron el cambio de página: reapareció una captura negra transitoria y la siguiente mostró la página original. Una acción de foco devolvió `noWindowsAvailable`; consultas posteriores recuperaron la ventana. **No se registra PASS de SELECT ni ninguna cifra de pools/p95 de emulación.** La causa de entrada/captura/refresco sigue sin aislar; la anomalía previa de F01.05 continúa abierta y no puede atribuirse exclusivamente a GDB, ya que aquí no se activó. Las capturas están en la conversación, no en un PNG local inexistente.

El log conserva el aviso de `ConfigureNew3DSCPU` no implementado y un intento fallido del comprobador de actualizaciones del emulador. El perfil preexistente no se alteró para ocultarlos. Se cerró Azahar por su UI (Sí); el proceso terminó con código 0. No se acreditan START ni retorno al launcher mediante esta salida.

## Artefactos e identidad

Compilación en `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`: read-only, sin red/capacidades, tmpfs y montaje de copia sintética limpia; venv Linux solo en lectura para gcovr. devkitARM r68/GCC 16.1, libctru 2.7.0-1, Citro2D 1.7.0-1 y Citro3D 1.7.1-2. Receta: `bash scripts/build_3ds.sh`, presets host-coverage/CTest y gcovr dentro de esa copia.

`build/f01-06/clean-inputs.json` contiene **55 entradas**, SHA-256 `0f7bc6ddd13fbae6ef6ce5d12230550150b1e09647341cba9d33fdc1f15bc1d5`. Sus hashes coinciden con los fuentes actuales; no se copiaron cachés ni originales. Logs ARM/GCC y cobertura están en `build/f01-06/clean-project/`. El build ID etiqueta fuentes/CMake; los hashes de artefactos identifican los binarios exactos.

Archivos en `build/f01-06/artifacts/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| sh3_diagnostic.3dsx | 215508 | `3ceca33946f54d0fa6e59d8a0aa95f44cd6a13f7c2c8088f9f325f79e6ad0495` |
| sh3_diagnostic.elf | 1861184 | `311c943c1fd0866d03aa6f1276477a0b061d892ba557bf49885a08322c62ac68` |
| debug-bundle.json | 357 | `f09da93d3336578cf41ea0eb653d551f7df2e6cbc262131691fd41eb560a81be` |
| probe.txt | 16 | `b5ecd4976f9ee278f1a384e5d346f44797c531ea6b47b62d14ca48261d8cfc4a` |

SMDH, build-id, checksums e inventario de paquetes también están archivados; tamaños/hashes en `build/f01-06/artifacts.json`. Log Azahar: `build/f01-06/azahar.log`, SHA-256 `2128a4949845d90217fd3976a3103f1aa903bc25bc0fc13b9229361439b3e071`. Configuración: `build/f01-06/azahar-config.ini`, SHA-256 `d19e0a8d4f891fbe09f5c26b963277a010bb83ad21fc2694fb623b0e04dd9c70`. Fuentes/config/tests/docs se inventarían en `build/f01-06/source-manifest.json` (excluye este informe para evitar autorreferencia).

## Pendientes y continuidad

F01.06/hardware requiere ejecutar el manual y caracterizar B_app/CPU/launcher, incluyendo picos y coexistencia para Q08. Q13 queda parcial: diagnostic-v1 fija muestreo/retención/percentil iniciales, pero no corpus real ni criterio de rendimiento de campaña. Ningún dato de emulador se escribe en target.json físico. Los gates y el margen de 80 % siguen pendientes. La nueva página necesita confirmación visual interactiva en un entorno de entrada fiable. LIC07 sigue pendiente antes de compartir binarios; no se publicaron ni se creó commit.

La siguiente tarea independiente es **F01.07 — probar ciclo de vida y controles reservados**. Puede ampliar contratos de pausa/tapa/HOME/reanudación mientras la validación física de F01.02-F01.06 permanece abierta.
