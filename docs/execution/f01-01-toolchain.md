# F01.01: SDK fijado y ejemplo oficial reproducible

Estado: **completada para compilación y reproducibilidad local**. Fecha: 2026-10-16. Responsable: agente de desarrollo. Requisitos RNF05.01/RNF05.02, V19 y normas RNF07/RNF11. G01 continúa pendiente de ejecución física, diagnóstico completo y depuración.

## Resultado

El ejemplo oficial `graphics/gpu/simple_tri`, del paquete `3ds-examples 20240917-1`, compila dos veces desde directorios nuevos. Sus **3DSX y SMDH son idénticos byte a byte**. Se usa el Makefile, C y shader originales del SDK; el ejemplo está escrito en C, por lo que una prueba propia separada comprueba C++17 con cabeceras 3DS y genera un objeto ELF32 ARM.

La misma secuencia configurada en CI —comprobar SDK y construir el diagnóstico propio— pasó localmente en una copia limpia de 16 archivos del proyecto, sin caché previa, originales ni informes privados. Las cinco unidades C++ del motor se compilaron con `-std=c++17`. El diagnóstico volvió a producir el SHA-256 ya registrado en la fundación.

Se implementó [check_3ds_toolchain.sh](../../scripts/check_3ds_toolchain.sh), un [probe C++17 propio](../../tests/fixtures/synthetic/toolchain/cxx17.cpp) y [cinco casos de error](../../tests/python/test_toolchain_script.py). El script separa validación del entorno, compilación de entradas conocidas y conservación de evidencia. Copia únicamente los tres fuentes inspeccionados del ejemplo, evitando reutilizar objetos precompilados. Rechaza destinos existentes sin borrar ni sobrescribir evidencia, y solo escribe `result.txt` después de que todas las comprobaciones pasan.

El job `nintendo-3ds` ejecuta esta comprobación antes del build propio. Un fallo impide continuar; una etapa `always()` conserva únicamente reportes, logs y hashes del chequeo. No selecciona fuentes, icono ni binarios del ejemplo oficial para subirlos. El workflow conserva su selección previa del diagnóstico propio, cuya revisión de distribución LIC07 sigue pendiente. **No se ejecutó CI remota ni se publicó un artefacto.**

## Identidad y procedencia

| Entrada | Identidad observada |
|---|---|
| Imagen oficial fijada | `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5` |
| Imagen local de ejecución | `sha256:23e9c452eafb9bd85c7a5fbf1f6ebb05f22f086f5f14cc73fcc6dbcd5a32a71c`, Linux ARM64 |
| Compilador / Make | devkitARM r68-1, GCC ARM 16.1.0; GNU Make 4.3 |
| SDK gráfico | libctru 2.7.0-1, citro3d 1.7.1-2; diagnóstico propio también citro2d 1.7.0-1 |
| Generadores | picasso 2.7.2-3, general-tools 1.4.4-1 (`bin2s`), 3dstools 1.3.1-3 |
| Ejemplo | `examples/3ds/graphics/gpu/simple_tri`; Makefile, `source/main.c` y `source/vshader.v.pica` del paquete fijado |
| Copia limpia propia | `build/f01-01/final-clean-inputs.json`, 16 archivos; SHA-256 `a1a01ef4ecc1fcb67e6699e3a22e46742093ad8374e034658e2325b2e58ea324` |

La [evidencia pública](../compatibility/toolchain-check-evidence.json) conserva hashes de los tres fuentes, README, identidad de imagen, versiones y salidas. El manifiesto completo de paquetes queda en los resultados locales. El README instalado de ejemplos coincide con el revisado en F00.06 y declara Public Domain Mark 1.0; se preserva junto con la evidencia local. El icono predeterminado proviene de libctru y queda identificado por hash. La compilación no sustituye la revisión del contenido de una distribución.

`general-tools` declara ISC en metadata, pero su `COPYING` instalado contiene GPLv3; se incorpora a **LIC01** junto a la discrepancia de los generadores ya observada en 3dstools. Se registra el dato sin resolverlo por la etiqueta más permisiva. El inventario de licencias mantiene pendientes las fuentes/avisos exactos antes de empaquetar herramientas o compartir binarios. No cambian la licencia propia ni los locks del SDK.

## Resultados comprobados

| Comprobación | Esperado | Observado |
|---|---|---|
| Fuentes oficiales | Copias idénticas a los tres archivos del SDK, sin objetos previos | Pasa; hashes originales coinciden en ambos directorios |
| Compilación oficial repetida | Dos ejecuciones completas, salidas no vacías | Pasa; shader, C, enlace, SMDH y 3DSX generados en ambos casos; logs sin warnings |
| Reproducibilidad desplegable | Igualdad binaria de 3DSX/SMDH en el mismo SDK/plataforma | Pasa por `cmp`; no se exige igualdad del ELF con información de depuración |
| C++17 ARM | `__cplusplus=201703L`, `if constexpr`, `is_integral_v`, deducción de `std::array` y structured bindings | Pasa; objeto ELF32 ARM compilado con warnings como errores; no ejecutado |
| Build propio tras chequeo | Compilación limpia C++17 y diagnóstico identificable | Pasa; cinco unidades C++17, sin cambio del hash del 3DSX anterior |
| SDK ausente / vacío / incompleto | Error antes de crear evidencia | Pasa: DEVKITPRO ausente/vacío, DEVKITARM ausente y ruta de SDK incompleta |
| Destino existente | Rechazo sin alterar el resultado anterior | Pasa; sentinel anterior conservado íntegro |
| Batería Python | Cero fallos y cobertura ≥80 % por línea/rama | **185/185 pasan**; **576/602 líneas = 95,68 %**, **235/248 ramas = 94,76 %** |
| Lint/formato y script | Cero errores | Ruff, formato Python, clang-format del probe y sintaxis Bash comprobados |
| Workflow | Sintaxis y referencias de Actions válidas | actionlint 1.7.12 pasa; ejecución remota pendiente |
| Arquitectura, custodia y EARS | Sin errores de dependencias, ubicaciones o referencias | `Repository checks: PASS (0 errors)` |

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `simple_tri.3dsx`, ambos directorios | 81.668 | `c51a303bd5328637c08ed5cc89b6b57343c7f40b5cee2aa89988ee0317a10f27` |
| `simple_tri.smdh`, ambos directorios | 14.016 | `d3611b1cc63bdbb16e9b205203f25e5107fd4049c05897ad9d6ed5549d55b555` |
| `sh3_diagnostic.3dsx`, copia limpia | 179.624 | `eed7b652dbc0b868eb2ac3858286e59880f6cec597db7964f4eb96a634065c6a` |

Los ELF del ejemplo conservan hashes distintos en cada carpeta y símbolos para esa compilación. La igualdad demostrada corresponde a 3DSX/SMDH con este SDK Linux ARM64; no se generaliza a otros hosts/compiladores. El digest de la imagen es multiarquitectura y el runner Linux de GitHub no se ha probado en esta tarea.

## Reproducción

Desde la raíz, para repetir la comprobación sin montar originales en el contenedor, elegir un destino nuevo para cada ejecución:

```sh
rtk proxy mkdir -p build/toolchain-runs
rtk proxy docker run --rm --read-only --network none \
  --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev \
  --mount "type=bind,src=$PWD/scripts,dst=/work/scripts,readonly" \
  --mount "type=bind,src=$PWD/toolchains,dst=/work/toolchains,readonly" \
  --mount "type=bind,src=$PWD/tests/fixtures/synthetic,dst=/work/tests/fixtures/synthetic,readonly" \
  --mount "type=bind,src=$PWD/build/toolchain-runs,dst=/evidence" -w /work \
  devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
  bash scripts/check_3ds_toolchain.sh /evidence/run-001

rtk proxy .venv/bin/python -m pytest -q --cov=tools \
  --cov-report=json:build/f01-01/python-coverage.json \
  --cov-report=xml:build/f01-01/python-coverage.xml \
  --junitxml=build/f01-01/pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/f01-01/python-coverage.json
rtk proxy .venv/bin/python -m ruff check tools tests/python
rtk proxy .venv/bin/python -m ruff format --check tools tests/python
rtk proxy bash -n scripts/check_3ds_toolchain.sh
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

En el SDK, la secuencia del pipeline es `bash scripts/check_3ds_toolchain.sh && bash scripts/build_3ds.sh`. Se ejecutó en `build/f01-01/final-clean-project`, una copia creada con CMake, engine, scripts, pin del SDK y probe propio; manifiesto y logs en `build/f01-01/final-clean-inputs.json` y `final-clean-build.log`. Solo esa copia se montó en el contenedor de integración. No se leyó ni se montó la ISO privada.

Evidencia final: `build/f01-01/final-clean-project/build/toolchain-check/` y `build/3ds/` dentro de esa copia; `pytest.xml`, cobertura JSON/XML, identidad de imagen y metadata de general-tools bajo `build/f01-01/`. Las primeras pruebas exploratorias se conservan en carpetas separadas; los hashes del JSON público corresponden a la copia final. Los artefactos están ignorados por Git.

Fuentes sin commit: `build/f01-01/source-manifest.json`, **17 archivos**, SHA-256 `8d2a81fe8d9ddf0abca523e18ec509053e0c75f4dfc184b0ba6e67e8b76194a9`. El manifiesto incluye scripts, fixture, tests, workflow, configuración y documentación; excluye este informe para evitar autorreferencia. La copia limpia de los fuentes del motor se identifica por separado en `final-clean-inputs.json`.

## Continuidad

F01.01 queda cerrada con ejemplo oficial reproducible, C++17 comprobado, fallos de entorno cubiertos e integración en CI. El runtime y las bibliotecas del motor no cambiaron; no se repitieron pruebas host C++ ni se anunció ejecución de consola a partir de esta compilación.

La siguiente tarea es **F01.02 — Crear aplicación sintética .3dsx**: completar la revisión de composición, inicialización, dibujo, entrada y salida del diagnóstico existente, con pruebas de error y evidencia de arranque. Los subcasos físicos y G01 siguen pendientes; este build no demuestra audio, rendimiento ni estabilidad en la New Nintendo 2DS XL.
