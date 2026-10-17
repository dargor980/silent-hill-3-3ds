# F01.03: archivos sintéticos y opciones persistentes

Fecha: 2026-10-16. Responsable de implementación y validación local: agente de desarrollo. Estado: **implementación, pruebas host y compilación ARM completadas; SD/consola pendientes**. F01.03, F01.02/hardware y G01 permanecen abiertos. Requisitos RNF03.04, RF11.06, RF14.01 y normas RNF07/RNF11.

## Resultado y contrato

El diagnóstico lee `probe.txt`, muestra Probe/Load/Save junto al build y conserva salida mediante START ante errores de archivos. X cambia y guarda la opción de tono; Y restaura y guarda su valor predeterminado. Las opciones se cargan una vez, antes del audio; el tono recibe su pausa inicial antes de encolar PCM. La actualización del resultado de X/Y aparece en el siguiente frame.

Se creó el [contrato v1 con ocho criterios EARS locales](../../schemas/diagnostic-options-v1.md). Es un formato propio de 16 bytes con versión, booleano, generación little-endian y checksum; no representa archivos ni partidas de Silent Hill 3. El perfil español/Normal/Normal permanece sin cambios. El fixture tiene exactamente 16 bytes ASCII y se conserva inmutable.

Dos slots alternos permiten conservar el registro anterior mientras se escribe y verifica el candidato. La aplicación comprueba la escritura, flush, cierre y relectura; confirma las opciones en memoria solo después de igualdad completa. La lectura acotada detecta exceso, el parser rechaza truncamientos y datos inválidos, y los errores inciertos o generaciones contradictorias impiden escribir. La generación máxima no desborda.

La garantía de esta tarea es conservación del slot seleccionado y del estado en memoria ante fallo del candidato. **No es una garantía de durabilidad ante corte de energía.** Un error tardío puede dejar un candidato completo seleccionable al reiniciar; se informa operación no confirmada. No se utiliza rename ni se declara rollback físico. La política presupone una instancia y ausencia de ediciones externas concurrentes.

## Diseño SOLID e integración

| Componente | Responsabilidad |
|---|---|
| [diagnostic_options.cpp](../../engine/domain/diagnostic_options.cpp) | Codec puro, campos explícitos y checksum; sin SDK ni filesystem |
| [files.hpp](../../engine/ports/include/sh3/ports/files.hpp) | Puertos separados de lectura y escritura; IDs cerrados, búfer acotado y errores tipados |
| [options_store.cpp](../../engine/application/options_store.cpp) | Selección de generación, recuperación y confirmación de opciones tras verificar |
| [stdio_files.cpp](../../engine/platform/common/stdio_files.cpp) | Archivos stdio, rutas propias acotadas, clasificación de errores y cierre de handles |
| [file_probe.cpp](../../engine/platform/3ds/file_probe.cpp) | Fixture conocido, acciones del diagnóstico y estado para la vista |
| [diagnostic.cpp](../../engine/platform/3ds/diagnostic.cpp) | Composición por referencias, precedencia START/Y/X/A, presentación y aplicación de mute |

El mismo adaptador stdio se compila para host y ARM. Su tabla de seis llamadas permite inyectar fallos deterministas sin cambiar el núcleo. La composición host del adaptador 3DS usa archivos en memoria y dobles SDK; el build ARM enlaza stdio real y `tone.cpp`. Ningún archivo de pruebas aparece en sus diez órdenes C++17.

La biblioteca [libctru 2.7.0 inicializa FS y monta SD en su appInit predeterminado](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/system/appInit.c). El proyecto usa esa inicialización y una ruta absoluta `sdmc:/3ds/sh3_diagnostic/`; los fallos se diagnostican mediante stdio. Este soporte de código no acredita el montaje ni la I/O en la consola del usuario.

El script [build_3ds.sh](../../scripts/build_3ds.sh) copia el fixture propio junto al ejecutable y calcula hashes de 3DSX, ELF, SMDH y fixture. El job de CI conserva también `probe.txt`; no incluye slots generados ni datos privados. Los presets existentes incorporan automáticamente las nuevas suites y escenarios.

## Pruebas y evidencia observada

| Batería | Resultado observado |
|---|---|
| Codec | Vector de bytes esperado, ambos valores de tono, generaciones límite, todos los bytes alterados, todas las longitudes truncadas, dato extra, puntero nulo y generación cero |
| Aplicación/slots | Primer inicio, alternancia, reapertura, recuperación, slots corruptos, I/O incierta, empate idéntico/contradictorio y contador saturado |
| Fallos de escritura | Parcial/disco lleno, permiso, escritura, flush, cierre y relectura fallidos o distintos; sin confirmación de memoria ni escritura del slot anterior |
| Stdio real | Directorio temporal independiente, faltante, archivo vacío/parcial/normal/excesivo y restauración/reapertura; fixture no escribible desde el puerto |
| Dobles stdio | Cantidades parciales y fallos por etapa sobre handles reales; cada apertura adquirida termina cerrada, también ante error |
| Composición 3DS con SDK doble | 14 escenarios: los 10 de F01.02 y X, Y, guardado fallido y fixture parcial; prioridad START incluye X/Y/A simultáneos |
| macOS AppleClang 15 Debug | **21/21 casos CTest pasan** |
| macOS AppleClang 15 Release | **21/21 pasan**, checks activos con NDEBUG |
| macOS LLVM 22.1.4 ASan+UBSan | **21/21 pasan**, sin hallazgos; UBSan detiene ante error |
| Linux ARM64 GCC 12.2 | **21/21 pasan** |
| Cobertura portable GCC | **260/261 líneas (99,62 %), 197/200 ramas (98,5 %), 30/30 funciones**; límites independientes ≥80 % satisfechos |
| Build 3DS devkitARM r68-1 / GCC 16.1.0 | Pasa desde copia limpia; diez unidades C++17, sin warnings del proyecto |
| Python 3.14.6 / pytest | **185/185 pasan**; 576/602 líneas (95,68 %), 235/248 ramas (94,76 %) |
| Calidad | clang-format, Ruff lint/formato, Bash, actionlint 1.7.12 y arquitectura/custodia/EARS pasan |
| Hardware / emulador / CI remota | No ejecutados |

Suites nuevas: [codec](../../tests/cpp/test_diagnostic_options.cpp), [almacén](../../tests/cpp/test_options_store.cpp), [stdio](../../tests/cpp/test_stdio_files.cpp); ampliación de [composición](../../tests/cpp/test_ctr_diagnostic.cpp). La cobertura incluye dominio, aplicación y adaptadores comunes como stdio; excluye platform/3ds y los dobles, sin atribuir cobertura física a GPU/SD/NDSP.

En la primera compilación de tests se corrigió la declaración host de `mkdtemp` incluyendo `unistd.h`. La pasada Linux detectó después que el doble de `ferror` necesitaba `noexcept` para coincidir con su cabecera; se corrigió y se repitieron las cuatro configuraciones. La copia exploratoria y su fallo de build quedan separados en `build/f01-03/clean-project`; la evidencia final corresponde a `final-clean-project`.

## Artefactos identificados

Build visible: **`69dad0b82f77`**. Imagen oficial: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`. Paquetes principales: libctru 2.7.0-1, citro2d 1.7.0-1 y citro3d 1.7.1-2. Inventario completo conservado junto al resultado.

Se montaron exclusivamente **41 archivos propios** de código, pruebas, configuración, script, pin y fixture en una copia limpia; no se leyó ni montó la ISO ni informes privados. Manifiesto `build/f01-03/final-clean-inputs.json`, SHA-256 `e8a8547fe9fc08447b69c9398fa8583f14ad2d0a20b84f26e0a33c64c47bd199`. Se comprobó que todos sus hashes coinciden con el workspace final.

| Archivo en `build/f01-03/artifacts/` | Bytes | SHA-256 |
|---|---:|---|
| `sh3_diagnostic.3dsx` | 208.264 | `6f4d9d422cd25cf0f347547057a474495f2a7e922c60f490b5739396869cf0c3` |
| `sh3_diagnostic.elf` | 1.752.836 | `a1b8354eeecb82caac57a60c5dd2673dfb2d4d1cbb21d8a780e4317bdb940dff` |
| `sh3_diagnostic.smdh` | 14.016 | `6464e274c665720387708c966a272bd04fae4b19a9debbfe0da7e6b3011bafea` |
| `probe.txt` | 16 | `b5ecd4976f9ee278f1a384e5d346f44797c531ea6b47b62d14ca48261d8cfc4a` |

También se conservan `SHA256SUMS` e inventario de paquetes. ELF y 3DSX proceden del mismo enlace. Los artefactos permanecen locales e ignorados; no se publicó una release. LIC07 conserva su revisión antes de compartir binarios.

## Reproducción

Desde la raíz, repetir con `host-release` o `host-sanitize` para las otras configuraciones:

```sh
rtk proxy cmake --preset host-debug -B build/f01-03/host-debug
rtk proxy cmake --build build/f01-03/host-debug --parallel 2
rtk proxy ctest --test-dir build/f01-03/host-debug --output-on-failure --output-junit test-results.xml
```

La configuración sanitizada local añade `-DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++` y ejecuta CTest con `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Se conserva evidencia en `build/f01-03/{debug,release,sanitize}-final.log` y `host-*/test-results.xml`.

Dentro del contenedor fijado, copia limpia montada como `/work`, sin red, con raíz de contenedor de solo lectura y `/tmp` efímero:

```sh
bash scripts/build_3ds.sh
cmake --preset host-coverage
cmake --build --preset host-coverage --parallel 2
ctest --preset host-coverage --output-junit test-results.xml
/venv/bin/python -m gcovr --config gcovr.cfg --xml build/cpp-coverage.xml --json build/cpp-coverage.json
```

`/venv` es la instalación Linux existente de gcovr 8.6, montada de solo lectura; no se descargaron dependencias. Logs `build-3ds.log`, `host-coverage.log` y `coverage.log`, JUnit y reportes XML/JSON bajo `build/f01-03/final-clean-project/`. El aviso de gcovr sobre `output` no usado corresponde al destino predeterminado sustituido por XML/JSON explícitos; ambos reportes se generaron y pasaron los umbrales. Metadatos en `build/f01-03/build-evidence.json`.

La primera pasada Python detectó el enlace al informe antes de que se creara este archivo; se conservó bajo `initial-*` y se repitió tras completar la documentación. La pasada final tiene 185/185 aprobadas y reportes `pytest.xml`, `python-coverage.xml/json` bajo `build/f01-03/`. `tools.qa.check_repository` informa cero errores. Esta validación local no representa una ejecución remota de Actions.

Manifiesto de fuentes/configuración/documentación de esta tarea (excluye este informe para evitar autorreferencia): `build/f01-03/source-manifest.json`, **50 archivos**, SHA-256 `69bbca9f1c1dee5ef8cceb016d6aeb5e4dbb9fb8623ce7da62ec551ab5d18e7d`. El manifiesto de 41 entradas identifica por separado la copia limpia del build; no se creó commit.

## Continuidad

F01.03/hardware debe ejecutar la [guía de lectura y persistencia](../compatibility/file-probe.md) con este build. Las instancias locales están completadas; la casilla matriz y G01 no se cierran sin consola. La SD real, sus errores, legibilidad y persistencia tras reapertura siguen sin comprobarse.

La siguiente implementación independiente es **F01.04 — tono y servicio de audio**: validar asignaciones/colas NDSP, errores de inicialización y memoria, contadores y liberación. Su aceptación física también necesita la New Nintendo 2DS XL.
