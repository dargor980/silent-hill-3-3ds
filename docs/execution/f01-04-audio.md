# F01.04 — tono sintético y diagnóstico NDSP

Fecha: **2026-10-16**. Implementación y validación C++/ARM locales completadas. **Escucha y ejecución física no verificadas**; F01.04/hardware, dependencias físicas F01.02/F01.03 y G01 siguen pendientes. No se leyó ni extrajo contenido de la ISO.

## Resultado y contrato

Se concreta [F01.04](../specs/sh3-3ds/tasks/F01.md#f0104) con [ocho criterios EARS locales](../compatibility/audio-contract.md), derivados de RF08.06/RF14.01. El diagnóstico prepara PCM16 mono propio de 440 Hz a 22050 Hz durante un segundo, un bloque de **44100 bytes**, amplitud máxima ±2048 y mezcla frontal 0.5/0.5. Usa una única cola en bucle del canal 0.

El adaptador distingue `NDSP_INIT_FAILED`, `PCM_ALLOC_FAILED` y `CACHE_FLUSH_FAILED`. Conserva los Result reales de las APIs; reserva fallida muestra N/A. La caché se comprueba antes de configurar o encolar. Los fallos parciales liberan inmediatamente los recursos adquiridos y mantienen el error visible. Una init fallida no llama exit; una reserva fallida finaliza NDSP; un flush fallido finaliza NDSP y después libera PCM.

La vista incluye escena, build, estado/etapa/Result, pausa solicitada y contadores brutos de frames NDSP, frames descartados y posición de muestra. `READY` solo acredita preparación y envío; `Listening: NOT_VERIFIED` conserva explícitamente la escucha pendiente. Los contadores pueden circular o reiniciarse; frames NDSP puede avanzar con el canal pausado. No se calculan segundos audibles, FPS ni progreso de reproducción.

Tone es el único propietario NDSP/canal 0 en esta aplicación y no es copiable/movible. Mute se aplica antes de encolar, pause evita llamadas redundantes y el cierre conserva cola/descriptor/PCM hasta completar clear → ndspExit → linearFree. La vista consume el snapshot; las reglas de aplicación y archivos siguen separadas. No se agregan dependencias SDK al dominio, un mezclador anticipado ni interfaces por muestra.

Las cabeceras de NDSP/canal/DSP se consultaron en la imagen fijada. La semántica de cierre/contadores se contrastó con [libctru v2.7.0](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/ndsp/ndsp.c): exit espera al hilo y finaliza DSP; frames se reinicia al inicializar/reanudar y la API devuelve el contador directamente. El adaptador maneja errores retornados, no abortos o bloqueos internos del SDK. Las referencias de APIs están en el contrato.

## Pruebas y límites de la evidencia

| Comprobación | Esperado | Observado |
|---|---|---|
| AppleClang Debug / Release | Todos los contratos y smoke pasan, checks activos en Release | **31/31 en cada build** |
| LLVM ASan + UBSan | Sin accesos inválidos ni comportamiento indefinido detectado | **31/31**, sin hallazgos |
| GCC Linux ARM64 host | Mismos casos contra dobles y bibliotecas portables | **31/31** |
| Cobertura C++ portable | ≥80 % de líneas y ramas | **260/261 líneas (99.62 %), 197/200 ramas (98.50 %), 30/30 funciones** |
| Build ARM SDK | Compilar 10 unidades C++17 y enlazar 3DSX/ELF/SMDH | Correcto, sin warnings del proyecto |
| Calidad y regresiones Python | Tests, cobertura, arquitectura/custodia/EARS/enlaces y formato | **185/185 Python; checks de calidad aprobados** |
| GitHub Actions | Ejecución remota identificada | No ejecutada; los jobs existentes recogen las suites mediante CTest |
| New Nintendo 2DS XL / emulador | Tono, contadores, controles, salida y suspensión reales | **No ejecutados** |

Los cinco casos de `test_ctr_tone` compilan el `tone.cpp` real contra funciones SDK controladas: normal, mute inicial, init fallida, reserva fallida y flush fallido. Verifican rango, 440 cruces ascendentes, media, energía y borde de bucle sin duplicar la fórmula de generación. Comprueban parámetros, mute antes de add, pause idempotente, contadores en u32 máximo/cero, ausencia de consultas tras fallo y liberación única con descriptor/PCM vivos hasta exit.

Los diecinueve casos de composición usan un Tone doble separado y la función real `run_diagnostic`. Se añaden salida visible ante reserva/flush fallidos y sleep/wake con tono activo, mute y pausa previa. Los siete casos restantes cubren núcleo, archivos y smoke. Los dobles no ejecutan DSP, no prueban ABI/timings de consola ni demuestran escucha. La compilación ARM contrasta las declaraciones con el SDK real. El alcance de cobertura portable se conserva, excluyendo 3DS/dobles.

## Entornos, comandos y evidencias

Evidencia local ignorada por Git bajo `build/f01-04/`. Debug/Release usan los presets del repositorio, compilador AppleClang 15.0.0; sanitizadores usan LLVM 22.1.4 en directorio separado. Linux host usa GCC 12.2.0. SDK: devkitARM r68-1/GCC 16.1.0, libctru 2.7.0-1, Citro2D 1.7.0-1 y Citro3D 1.7.1-2, inventario completo junto a los artefactos.

```sh
rtk proxy cmake --preset host-debug
rtk proxy cmake --build --preset host-debug --parallel 2
rtk proxy ctest --preset host-debug --output-junit test-results.xml
# Repetir con host-release.
rtk proxy cmake -S . -B build/f01-04/host-sanitize -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON -DSH3_SANITIZERS=ON -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++
rtk proxy cmake --build build/f01-04/host-sanitize --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --test-dir build/f01-04/host-sanitize --output-on-failure --output-junit test-results.xml
```

La copia limpia contiene **44 entradas** de fuentes/headers/tests, CMake/presets/gcovr, script de build, pin y fixture. Manifiesto `build/f01-04/final-clean-inputs.json`, SHA-256 `5e9229385379b63339822eccb1eca9c916d4cdd3d03c68502d7d0fecdfd491d0`. Imagen fijada `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`; contenedor read-only, sin red/capacidades, con tmpfs temporal. Solo se montaron esa copia y el entorno Linux de gcovr en lectura; ninguna ISO, extracción o informe privado.

Comandos dentro del contenedor, secuenciales y con fallo propagado: `bash scripts/build_3ds.sh`; `cmake --preset host-coverage`; `cmake --build --preset host-coverage --parallel 2`; `ctest --preset host-coverage --output-junit test-results.xml`; `/venv/bin/python -m gcovr --config gcovr.cfg --xml build/cpp-coverage.xml --json build/cpp-coverage.json`. gcovr emitió únicamente el aviso de que el destino output configurado se sustituye por los destinos explícitos; ambos reportes existen y los umbrales pasan.

Logs: `host-debug.log`, `host-release.log`, `host-sanitize.log`; en `final-clean-project/`, `build-3ds.log`, `host-coverage.log`, `coverage.log`, XML/JSON de cobertura y JUnit de GCC. JUnit Debug/Release queda en `build/host-debug` y `build/host-release` y copiado a `build/f01-04/*-tests.xml`; el de sanitizadores en `build/f01-04/host-sanitize`. Metadatos del artefacto en `build-evidence.json`. La CI conserva sus cuatro jobs y las nuevas suites quedan incluidas en Release/sanitizadores/GCC; no requiere un job que simule escucha.

Calidad final: pytest **185/185**, Python 3.14.6, cobertura de líneas **576/602 (95.68 %)** y ramas **235/248 (94.76 %)**. Reportes `python-tests.log`, `pytest.xml`, `python-coverage.xml/json`; gate independiente de líneas/ramas aprobado. Ruff check/format, clang-format sobre 38 fuentes/headers, actionlint, sintaxis Bash y `tools.qa.check_repository` (0 errores) pasan; logs `quality.log` y `format.log`. Se conservan 160 requisitos EARS y 120 tareas de la matriz; los ocho criterios de audio son locales.

Manifiesto de código/tests/configuración/documentación vigente: `build/f01-04/source-manifest.json`, **53 archivos**, SHA-256 `b16ae15d013d90f578de5413f1787bd2acf508f95bb6047df518c43371c59f61`. Excluye este informe para evitar autorreferencia. Se verificó que las 44 entradas de la copia limpia coinciden con las fuentes actuales.

## Artefacto para la siguiente validación

Build ID **632a72b68533**, calculado a partir de engine y CMakeLists. Artefactos en `build/f01-04/artifacts/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| sh3_diagnostic.3dsx | 209376 | `2d24c0744cb6522fdd7994113ac8171b8f0723b01f2c52df5f0ecc06f10a3f8e` |
| sh3_diagnostic.elf | 1756980 | `8b6d479f8b1c88fadf0cfe38902691caf27743d1aef8efe0a522185386aaa760` |
| sh3_diagnostic.smdh | 14016 | `6464e274c665720387708c966a272bd04fae4b19a9debbfe0da7e6b3011bafea` |
| probe.txt | 16 | `b5ecd4976f9ee278f1a384e5d346f44797c531ea6b47b62d14ca48261d8cfc4a` |
| toolchain-packages.txt | 2492 | `d357299f735481553637bfa4cb464fd10343fc66f8b741aa2b5027b3cc1af7a9` |

No hay commit ni distribución nueva. Los artefactos históricos de F01.02/F01.03 se conservan. Para esta tarea usar el [procedimiento físico de audio](../compatibility/audio-probe.md) y registrar exactamente este build/hash; no atribuirle resultados de otro binario. La próxima tarea independiente es **F01.05 — emulador y depuración real**, conservando los pendientes físicos y el ELF correspondiente.
