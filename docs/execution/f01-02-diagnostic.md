# F01.02: aplicación sintética y contratos del adaptador 3DS

Fecha: 2026-10-16. Estado: **implementación, pruebas host y compilación ARM completadas; ejecución física pendiente**. La casilla F01.02 y G01 siguen abiertas. Requisitos RNF12.02, RNF11.01, RNF11.03, RF12.04 y normas RNF07/RNF11. Responsable de las instancias locales: agente de desarrollo.

## Cambio y alcance

[main.cpp](../../engine/platform/3ds/main.cpp) delega en [diagnostic.cpp](../../engine/platform/3ds/diagnostic.cpp), que conserva la composición por constructor y las responsabilidades de gráficos, entrada, vista y hook. El dominio, la aplicación y los tres puertos permanecen portables. La separación permite compilar **la misma composición de producción** contra dobles controlados del SDK/Tone en host, sin introducir ramas de prueba ni interfaces genéricas en el runtime.

El error gráfico ahora informa `CITRO3D`, `CITRO2D` o `SCREEN_TARGET`, además del build y START para salir. No construye audio, vista ni hook de aplicación tras un arranque gráfico fallido. Solo finaliza los servicios inicializados y devuelve 1 en ese caso. START tiene prioridad sobre A; A actúa sobre flancos, y la salida por APT no presenta un frame adicional.

Se corrigió el orden de liberación: retirar hook → destruir tono → eliminar target esperando trabajo GPU pendiente → finalizar Citro2D → finalizar Citro3D → liberar framebuffers. El orden anterior podía liberar buffers de vértices antes de esperar el último envío. Esta conclusión se basa en revisión del código del SDK y una regresión con cola simulada; **no es un fallo reproducido en consola**.

La base técnica es que [C2D_Fini en citro2d 1.7.0](https://github.com/devkitPro/citro2d/blob/v1.7.0/source/base.c) libera sus buffers, mientras que [C3D_RenderTargetDelete en citro3d 1.7.1](https://github.com/devkitPro/citro3d/blob/v1.7.1/source/renderqueue.c) espera la cola antes de destruir/desenlazar el target. Se conserva la finalización de Citro3D posterior; no hay doble eliminación del target. Las firmas también se comprobaron en las cabeceras del SDK fijado.

La prueba de NDSP no disponible detectó además que convertir directamente un `Result` negativo a `unsigned long` imprime 16 dígitos en hosts de 64 bits. Se convierte primero a `u32`, preservando los ocho dígitos del código de 32 bits en ambos entornos. Esta corrección afecta representación diagnóstica; el servicio de audio real sigue en F01.04.

## Batería y límites

[test_ctr_diagnostic.cpp](../../tests/cpp/test_ctr_diagnostic.cpp) ejecuta diez escenarios independientes, además de los cuatro casos CTest anteriores. Los [dobles](../../tests/cpp/ctr_doubles/sdk.cpp) verifican precondiciones de cada llamada y orden de vida, registran geometría/entrada y rechazan uso después de cierre o liberación con GPU pendiente. La captura de stdout comprueba el mensaje emitido, no la legibilidad física de la pantalla.

| Caso nuevo | Criterio comprobado |
|---|---|
| `ctr_normal` | Patrón exacto, verde/ámbar/ámbar/verde, A por flanco, START sin frame extra, liberación tras último envío |
| `ctr_start_priority` | A+START termina sin dibujar ni pausar |
| `ctr_apt_exit` | APT termina antes del primer tick: sin entrada ni dibujo |
| `ctr_hook_exit` | Hook de salida lleva al estado terminal antes del tick |
| `ctr_fail_citro3d` | Mensaje/etapa/build exactos; solo se libera gfx |
| `ctr_fail_citro2d` | Mensaje exacto; se libera Citro3D y gfx, sin finalizar Citro2D fallido |
| `ctr_fail_target` | Mensaje exacto; A no sale, START sí; sin tono/hook/vista y sin borrar target nulo |
| `ctr_error_apt_exit` | El error también termina si APT cierra; conserva código de fallo |
| `ctr_frame_rejected` | Frame no abierto no se dibuja/finaliza; START sigue disponible |
| `ctr_audio_unavailable` | El fallo de Tone no bloquea dibujo/salida; código `0xffffffff` de 32 bits |

Cada caso tiene timeout CTest de diez segundos y comprobaciones activas también con `NDEBUG`. El doble de Tone comprueba uso y vida, **no** DSP, asignaciones de audio ni colas reales. Los dobles del SDK no son emuladores, no reproducen su ABI ni demuestran ausencia de errores internos de esas bibliotecas. `gfxInitDefault` es una llamada sin resultado recuperable: la garantía de mensaje comienza una vez disponible la consola básica.

La regresión de orden GPU falló con el código anterior en `!state.pending_gpu`; log preservado en `build/f01-02/gpu-order-regression.log`. Tras eliminar el target antes de Citro2D pasa la suite. Se conservan las ejecuciones exploratorias aparte de la evidencia final.

| Verificación final | Resultado |
|---|---|
| macOS / AppleClang 15 / Debug | 14/14 CTest pasan |
| macOS / AppleClang 15 / Release | 14/14 CTest pasan; checks activos |
| macOS / LLVM 22.1.4 / ASan + UBSan | 14/14 CTest pasan; sin hallazgos |
| Linux ARM64 / GCC 12.2 / cobertura | 14/14 CTest pasan; bibliotecas portables: 48/48 líneas y 32/32 ramas (100 %) |
| Build ARM / devkitARM r68-1 GCC 16.1.0 | Pasa; seis unidades C++17, ELF/SMDH/3DSX generados |
| Python 3.14.6 / pytest | 185/185 pasan; líneas 576/602 (95,68 %), ramas 235/248 (94,76 %) |
| Formato y calidad | clang-format, Ruff lint/formato, actionlint y arquitectura/custodia/EARS pasan |
| Hardware / emulador / CI remota | No ejecutados |

La cobertura se calcula con el alcance existente de `gcovr.cfg`: dominio, aplicación y log común. El adaptador 3DS y los dobles no se incorporan al porcentaje de bibliotecas portables ni se presentan como cobertura física. Los nuevos casos se ejecutan automáticamente en los jobs host y cobertura existentes; el job ARM compila `diagnostic.cpp` con cabeceras/bibliotecas reales. Ningún archivo de `tests/` aparece en sus seis órdenes de compilación.

## Build identificado

Se creó una copia limpia de **27 archivos** de CMake, engine, pruebas propias, configuración de cobertura, script y pin. Solo esa copia se montó en el contenedor; no se leyó ni montó la ISO ni informes privados. Manifiesto: `build/f01-02/final-clean-inputs.json`, SHA-256 `5ebeba13534fbd7c82626f2b372170efbaa9cc672933fe8a3876b79618e92075`.

Imagen: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`. Paquetes: libctru 2.7.0-1, citro2d 1.7.0-1 y citro3d 1.7.1-2. Se conserva el inventario completo con el resultado. Build ID visible: **`eabba802d179`**.

| Artefacto final | Bytes | SHA-256 |
|---|---:|---|
| `sh3_diagnostic.3dsx` | 179.980 | `f297720d4e68931b2d29028835b919077ba51e7c4d80e61be84f1848bf4bc181` |
| `sh3_diagnostic.elf` | 1.619.844 | `449be1a312d89926d323b86f760cafd1e8cc34e8b960fb846813379ebe2a10a3` |
| `sh3_diagnostic.smdh` | 14.016 | `6464e274c665720387708c966a272bd04fae4b19a9debbfe0da7e6b3011bafea` |

Copias para la prueba local: `build/f01-02/artifacts/`, con `SHA256SUMS` e inventario de paquetes. El ELF corresponde exactamente al mismo enlace que el 3DSX. Estos artefactos sintéticos permanecen locales e ignorados. No se publicó una release ni se ejecutó el workflow remoto; LIC07 conserva su revisión antes de compartir binarios.

## Reproducción y evidencia

Desde la raíz:

```sh
rtk proxy cmake --preset host-debug
rtk proxy cmake --build --preset host-debug --parallel 2
rtk proxy ctest --preset host-debug
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --parallel 2
rtk proxy ctest --preset host-release
rtk proxy cmake --preset host-sanitize -B build/f01-02/host-sanitize \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++
rtk proxy cmake --build build/f01-02/host-sanitize --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ctest --test-dir build/f01-02/host-sanitize --output-on-failure
```

La ruta LLVM corresponde a este equipo. Los builds finales Debug/Release usan los mismos presets con `-B build/f01-02/host-debug` y `host-release`. Logs `debug-final.log`, `release-final.log` y `sanitize-final.log`; JUnit `host-*/test-results.xml`, todos bajo `build/f01-02/`.

En la copia limpia montada como `/work` dentro de la imagen, con red deshabilitada, raíz de contenedor de solo lectura y `/tmp` efímero:

```sh
bash scripts/build_3ds.sh
cmake --preset host-coverage
cmake --build --preset host-coverage --parallel 2
ctest --preset host-coverage --output-junit test-results.xml
python -m gcovr --config gcovr.cfg --xml build/cpp-coverage.xml --json build/cpp-coverage.json
```

La última orden usa la instalación local existente de gcovr 8.6 para Linux montada en `/venv`, invocada mediante `/venv/bin/python`; no descarga dependencias. Se conservan `build-3ds.log`, `host-coverage.log`, JUnit y cobertura bajo `build/f01-02/final-clean-project/`. `build/f01-02/build-evidence.json` registra identidad y hashes. No hay commit nuevo; el manifiesto identifica los fuentes usados. La cobertura portable final es 100 % por líneas y ramas. gcovr avisó que el `output` predeterminado de la configuración no se usó porque se indicaron destinos XML/JSON explícitos; ambos reportes existen y pasaron los umbrales.

Las regresiones Python, reportes de cobertura y JUnit quedan en `build/f01-02/python-coverage.json`, `python-coverage.xml` y `pytest.xml`. Pasan el umbral independiente por línea/rama, Ruff, clang-format, actionlint 1.7.12 y `tools.qa.check_repository` (cero errores). Estos resultados no sustituyen una ejecución remota de Actions.

Manifiesto de los cambios de esta tarea, sin incluir este informe para evitar autorreferencia: `build/f01-02/source-manifest.json`, **17 archivos**, SHA-256 `95db4f91cbdd283f1111f07165340b4d83812548aa5ae0cdcee37e64f4756d2d`. El manifiesto de 27 entradas citado arriba identifica por separado la copia de compilación.

## Continuidad

La instancia **F01.02/hardware** requiere completar el [procedimiento de arranque](../compatibility/diagnostic-startup.md) con el build indicado. Hasta entonces F01.02 permanece abierta y el destino sigue `not_tested`. Q01/Q08/Q13 y G01 no cambian por una compilación exitosa.

La siguiente implementación independiente es **F01.03 — archivos y configuración**: lectura de fixture propio, escritura/verificación de opciones y errores de archivo ausente, lectura parcial o escritura fallida. Puede comenzar en host con la composición ya comprobada; su integración física conserva la dependencia pendiente de F01.02/hardware.
