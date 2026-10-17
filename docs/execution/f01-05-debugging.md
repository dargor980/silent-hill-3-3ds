# F01.05 — identidad de símbolos y depuración observada

Fecha: **2026-10-16**. Build y herramientas de integridad completados; **breakpoints alcanzados en Azahar**. Consola no probada y anomalía de refresco tras reconexión GDB abierta. F01.05 y G01 permanecen abiertos. No se usó la ISO ni se importó firmware o contenido original.

## Cambios y trazabilidad

[Ticket detallado](../specs/sh3-3ds/tasks/F01.md#f0105), [contrato EARS D01-D06](../compatibility/debugging-contract.md) y [procedimiento repetible](../compatibility/debugging.md). `tools/debug/bundle.py` genera/verifica un manifiesto estricto con build ID, tamaño y SHA-256 de los dos archivos fijos ELF/3DSX. La verificación recibe el ID registrado para la sesión y rechaza archivos alterados, faltantes, vacíos, especiales o de otro build. No interpreta ELF ni conecta al dispositivo; GDB mantiene esa responsabilidad.

CMake genera `build-id.txt`. El script 3DS crea/verifica `debug-bundle.json` después del enlace y la CI conserva ambos junto a los artefactos. Una carpeta con evidencia registrada se rechaza antes de compilar, para evitar sobrescribir el par anterior. No cambió la lógica C++ del diagnóstico; su nuevo ID procede del cambio de CMake. El ID no reemplaza los hashes exactos ni firma la autenticidad de la evidencia.

## Entorno ejecutado

- Host: macOS **26.5 arm64**, Apple M2.
- Emulador: **Azahar 2126.2 ARM64**, [publicación oficial](https://github.com/azahar-emu/azahar/releases/tag/2126.2), publicada el 2026-10-08; ZIP de 99740365 bytes, SHA-256 `c24dec2bd5111b7d79513d686c5aece6612cdbf9737b2e6ea99cfc426f1d4aef`, contrastado con el digest del asset oficial.
- Configuración registrada por el emulador: New3DS, JIT activado, CPU 100 %, Vulkan/MoltenVK y audio HLE. Es configuración emulada, no medición de la consola.
- GDB: **devkitARM GNU GDB 14.1** en la imagen fijada; SDK GCC 16.1.0/libctru 2.7.0-1. Cliente Docker Desktop conectado a `host.docker.internal:24689`.
- Binario probado: build **db2dd53fb5dc**, fuentes montadas en `/work`, mismo ELF que el registrado en el manifiesto.

Azahar se extrajo en `build/f01-05/tools/`; no se instaló en Applications. El chequeo `codesign --verify --deep --strict` informó formato ambiguo en QtGui.framework del ZIP oficial; se conservó el paquete sin re-firmarlo ni retirar protecciones. La ejecución normal de su ayuda y del diagnóstico funcionó. El intento offscreen falló porque el paquete solo incluye el plugin Cocoa. La ejecución restringida de Cocoa abortó al acceder a servicios macOS; la ejecución con acceso gráfico autorizado funcionó. No hubo rechazo de la revisión automática de permisos.

Las variables XDG no aislaron el ensayo inicial: Azahar creó/usó su configuración y caché en `~/Library/Application Support/Azahar/`; se conserva su log como exploratorio. Se verificó el código oficial y se creó `user/` al lado de Azahar.app para los siguientes ensayos; sus logs/configuración/SD sintética quedaron dentro de build. No se borró el perfil general. [Fuentes de selección de carpeta y pasos](../compatibility/debugging.md).

## Resultado observado

| Caso | Esperado | Observado / evidencia |
|---|---|---|
| Símbolos estáticos del ELF | Función y línea propias resolubles | `run_diagnostic`: 0x100f94, diagnostic.cpp:18; `Tone::snapshot`: 0x1015d4, tone.cpp:67; `symbols.log` |
| Breakpoint de inicio | Detener realmente la CPU emulada | Alcanzado en run_diagnostic; pila incluye main.cpp:6; `gdb-start.log` |
| Error con símbolos | Capturar código, estado y pila del build cargado | Breakpoint alcanzado en Tone::snapshot; `ndsp_init_failed`, `0xd880a7fa`, initialized=false, samples=null; `gdb-portable-error.log` |
| Error visible | Mensaje real y salida gráfica diagnóstica | Primer ensayo: patrón verde, build correcto, NDSP_INIT_FAILED y Probe MISSING visibles |
| Fixture en SD portátil | Lectura propia correcta | `Probe: OK` tras colocar fixture en user/sdmc/3ds/sh3_diagnostic; no se cambió el runtime |
| Reconexión GDB | Reanudar presentación íntegra | Se observó refresco gráfico parcial/negro tras una segunda conexión; causa **no aislada**, incidencia abierta |
| Arranque sin GDB | Contraste de la anomalía | Tras cerrar y abrir sin -g se observó de nuevo el patrón verde; no acredita estabilidad prolongada |
| ELF mezclado real | Rechazo antes de depurar | ELF de F01.04 con 3DSX/manifiesto nuevos: exit 1, `ARTIFACT_MISMATCH: sh3_diagnostic.elf`; `wrong-elf.log` |
| Cierre del ensayo | Sin servidor persistente | Azahar cerrado por UI; lsof sin listener TCP 24689; `debugger-closed.txt` |
| Hardware | Breakpoint/error en New Nintendo 2DS XL | **No ejecutado**; versión/menú/endpoint de Rosalina pendientes |

GDB resolvió la entrada en el constructor gráfico inline, no en la línea de declaración de la función. El getter inline `FileProbe::fixture_status` no existía como símbolo separado: esa consulta falló y queda en `symbols-inlined-getter.log`; la comprobación corregida usa Tone::snapshot y pasa. Al conectar a un proceso ya activo GDB mostró un aviso de fuente `svc.s` del SDK ausente; las fuentes propias, campos y pila sí se resolvieron. Los logs conservan el aviso.

No se provisionó un componente DSP. Se diagnosticó el error retornado sin modificar registros, forzar READY ni simular audio. La cadena de llamadas observada es Tone::snapshot → View::present → DiagnosticApp::step → run_diagnostic → main. La escucha sigue no verificada. El log de Azahar también registra `ConfigureNew3DSCPU` no implementado y avisos del entorno HLE; no se atribuye compatibilidad de CPU física a esta ejecución.

La inspección visual proviene de la ventana mediante Computer Use; las capturas están en la conversación, no se presenta un archivo PNG inexistente. No se acreditan A/START, guardado, audio ni tapa por esta sesión: se cerró el emulador mediante su UI. La anomalía de refresco se conserva sin decidir prematuramente si corresponde a GDB, captura de ventana, renderer o aplicación.

## Build y pruebas

Copia limpia: **47 entradas**, `build/f01-05/clean-inputs.json`, SHA-256 `28ba60fd83b1e956f071f214196497896f3360e0937a6d5798dc3c3235734431`. Incluye engine/tests C++, CMake/presets/gcovr, build script, pin, fixture y herramienta Python. Sin ISO, reportes privados ni cachés de compilación.

El build se ejecutó en `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`, read-only, sin red/capacidades, con tmpfs y la copia limpia como único proyecto. `bash scripts/build_3ds.sh` compiló diez unidades C++17 y produjo 3DSX/ELF/SMDH, ID y manifiesto; ambos comandos create/verify terminaron PASS. GDB estático se ejecutó sin red. Las sesiones remotas usaron red únicamente para conectar al emulador local y montajes de fuentes/ELF en lectura; no se montó el repositorio con originales.

| Validación | Resultado |
|---|---|
| Nuevos tests de integridad/CLI/build | **42/42** |
| CTest host Debug, configuración CMake actual | **31/31** |
| Suite Python completa, cobertura y calidad | **227/227**; líneas **641/668 (95.96 %)**, ramas **260/274 (94.89 %)**; gate aprobado |
| Build ARM y verificación de bundle | Correctos |
| Sanitizadores C++ | No repetidos: no cambió el runtime; resultados de F01.04 permanecen como evidencia histórica |
| CI remota | No ejecutada; se actualizó retención de manifiesto/ID |

Comandos de calidad: `.venv/bin/python -m pytest --cov=tools --cov-report=xml:build/f01-05/python-coverage.xml --cov-report=json:build/f01-05/python-coverage.json --junitxml=build/f01-05/pytest.xml`; gate independiente de líneas/ramas; Ruff, formato, Bash, actionlint y comprobador del repositorio. Los nuevos tests cubren pares alterados del mismo tamaño, truncamiento, vacío/ausencia, ID erróneo, esquema/tipos inválidos, límites del manifiesto, enlaces/FIFO/directorios y conservación de evidencia. Son integridad local, no simulación de GDB remoto.

Calidad final: Ruff check/format (22 archivos), actionlint, sintaxis Bash y `tools.qa.check_repository` pasan (0 errores). Reportes en `python-tests.log`, `pytest.xml`, `python-coverage.xml/json`, `quality.log`, `host-debug.log` y `host-tests.xml`. Los 47 inputs del build limpio coinciden con las fuentes actuales. Manifiesto de código/configuración/tests/documentación (sin este informe): `build/f01-05/source-manifest.json`, **60 archivos**, SHA-256 `a321d0d53abcb786801918db1803cd16d29cd0413118be09542c61549aad6bcc`. Las transcripciones y el manifiesto de artefactos tienen hashes registrados en `docs/compatibility/debugging-evidence.json`.

## Artefactos y continuidad

Disponibles en `build/f01-05/artifacts/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| sh3_diagnostic.3dsx | 209376 | `e157d32c6162658a581809ff8a03100ecc5bf93b9f517e39d66e7cd9c0d9e8b8` |
| sh3_diagnostic.elf | 1756980 | `963fd9e05c97b56a9d242e866ba5e5a2a596fa99b52c02ff53458446bc0a6cfc` |
| debug-bundle.json | 357 | `ef2d53995d99aadfa337a06465b2463aec93fe32a0af91b1abd9a7b7661942b7` |
| probe.txt | 16 | `b5ecd4976f9ee278f1a384e5d346f44797c531ea6b47b62d14ca48261d8cfc4a` |

También se conserva SMDH, inventario de paquetes, build-id y SHA256SUMS. Transcripciones/scripts GDB, logs de Azahar con/sin GDB, configuración y rechazo de mezcla quedan bajo `build/f01-05`. Los reportes identifican este par; no sustituyen la evidencia histórica F01.04. No se creó commit ni se publicaron binarios o datos.

F01.05/consola requiere confirmar el entorno de depuración del usuario y ejecutar el [procedimiento físico](../compatibility/debugging.md). El refresco tras reconexión requiere investigación adicional; la matriz y G01 siguen abiertas. La siguiente tarea independiente es **F01.06 — medir recursos y configurar diagnóstico**.
