# Ejecución inicial: fundación sintética

Informe histórico de la etapa inicial. Estado posterior de la edición: [F00.02 completada por contraste con catálogo](f00-02-edition-identification.md). Las cifras y limitaciones de esta etapa se conservan como evidencia histórica.

Fecha: 2026-10-16. Alcance: F00/F01 y validación sintética anticipada del perfil. No hay extracción del juego, lógica recuperada ni certificación de consola.

## Decisión de destino

El usuario confirmó New Nintendo 2DS XL, Homebrew Launcher y FBI. F00.01 queda completada como definición de destino, con evidencia en [target.json](../compatibility/target.json). Firmware, versiones de launcher, configuración CPU y resultados en hardware permanecen sin medir. La edición PS2 sigue pendiente; no se crea un perfil real con hashes supuestos.

## Trabajo entregado

| Trabajo | Evidencia implementada | Estado del ticket fuente |
|---|---|---|
| Detallar las 120 tareas | 15 documentos con entradas, dependencias, pasos, rutas, SOLID, pruebas, riesgos y evidencia | Completado como refinamiento documental |
| Reglas SOLID/testing/CI | RNF11.05-RNF11.09 y RNF07.06-RNF07.09, [normas](../engineering.md), targets separados y verificador de dependencias | Aplicadas a la fundación; futuras capacidades conservan sus tareas |
| F00.02/F00.05 | Perfil lógico, CLI read-only, inspector inyectable, fixture sintético y política privada | Parcial; falta copia real identificada |
| F00.06 | SDK y herramientas fijadas, manifiesto de paquetes y referencias de procedencia | Parcial; revisión de todas las herramientas futuras y distribución pendiente |
| F01.01/F01.02 | Build host y cross-build C++17; diagnóstico 3DS con geometría sintética y controles | Compilación verificada; ejecución física pendiente |
| F01.04 | Tono PCM sintético, estado de inicialización NDSP y limpieza RAII | Compilado; audio físico pendiente |
| F01.07 | Máquina de estados, tests y hooks de plataforma | Host verificado; tapa/HOME/retorno físicos pendientes |
| F01.08 | Workflow con calidad, matriz host, cobertura y build 3DS | Comandos locales probados según tabla inferior; ejecución remota pendiente |

## Registro de verificaciones

Los reportes ejecutables locales se almacenan en `build/` y no se versionan. Las siguientes cifras corresponden a ejecuciones terminadas de esta iteración; la matriz remota todavía no se ha ejecutado.

| Verificación | Estado y límite de evidencia |
|---|---|
| C++ Debug en macOS / Apple Clang 15 | 4/4 suites CTest aprobadas, incluyendo smoke host |
| C++ Release en macOS / Apple Clang 15 | 4/4 suites aprobadas con checks activos en Release |
| C++ con GCC 12.2 en Linux arm64 | 4/4 suites aprobadas; 48/48 líneas y 32/32 ramas del núcleo portable cubiertas (100 %); 9/9 funciones |
| ASan/UBSan con Apple Clang 15 | No ejecutable en este macOS: aborto del runtime `sanitizer_malloc_mac.inc:189` antes de los tests, también fuera del sandbox |
| ASan/UBSan con LLVM 22.1.4 | 4/4 suites aprobadas en macOS; sin hallazgos |
| ASan/UBSan con GCC 12.2 | 4/4 suites aprobadas en Linux arm64; sin hallazgos |
| Python 3.14.6 / pytest 9.1.1 | 63 casos aprobados; 223/230 líneas (96,96 %) y 99/106 ramas (93,40 %); ambos umbrales ≥80 % pasan |
| Cross-build ARM devkitARM | `.3dsx`, ELF y SMDH generados; reconstrucción desde copia limpia produce hashes idénticos; falta prueba física |
| Ejemplo oficial devkitPro | Template `templates/application` compilado en el contenedor; sin ejecución física |
| Workflow GitHub | `actionlint` 1.7.12 pasa; sin push ni run remoto en esta iteración |

Los targets de pruebas usan checks que permanecen activos en Release. La cobertura se exige separadamente para líneas y ramas del código portable y herramientas Python; los adaptadores libctru/citro/NDSP quedan fuera de cobertura host y requieren pruebas físicas. El checker de arquitectura es una barrera parcial verificable, no una demostración automática de todos los principios SOLID.

Artefacto: `build/3ds/sh3_diagnostic.3dsx`, 179624 bytes, SHA-256 `eed7b652dbc0b868eb2ac3858286e59880f6cec597db7964f4eb96a634065c6a`. Los checksums de ELF y SMDH y el inventario de herramientas están junto al binario. El código fuente sigue sin commit en esta iteración; la evidencia describe los archivos actuales, no un supuesto run de CI sobre un commit publicado.

Comandos reproducibles principales:

```sh
.venv/bin/python -m pytest --cov=tools --cov-report=json:build/python-coverage.json --cov-report=term-missing
.venv/bin/python -m tools.qa.coverage_gate build/python-coverage.json
.venv/bin/python -m tools.qa.check_repository
cmake --preset host-release
cmake --build --preset host-release --parallel 2
ctest --preset host-release
cmake -S . -B build/host-sanitize-llvm -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++ -DCMAKE_BUILD_TYPE=Debug -DSH3_SANITIZERS=ON
cmake --build build/host-sanitize-llvm --parallel 2
ctest --test-dir build/host-sanitize-llvm --output-on-failure
```

La ruta LLVM es específica de este equipo y se usó para resolver la incompatibilidad del runtime Apple 15. En Linux se utilizaron `host-coverage`, `gcovr.cfg` y un build separado `linux-sanitize`. El [README](../../README.md) contiene la invocación del SDK fijado. La reconstrucción limpia usó una copia de fuentes sin `.git`, entornos virtuales ni builds previos, montada en la misma ruta `/work`.

## Prueba manual pendiente en New Nintendo 2DS XL

1. Registrar build ID, checksum, versión de Homebrew Launcher, firmware/entorno y modelo.
2. Copiar el diagnóstico bajo `/3ds/` y abrirlo con Homebrew Launcher.
3. Comprobar patrón superior sin deformación y mensajes inferiores legibles.
4. Comprobar tono; si NDSP falla, registrar código y dejar audio como fallido.
5. Pulsar A para pausar/reanudar: color y audio deben reflejar el estado.
6. Probar tapa y retorno desde HOME; comprobar que una pausa previa se conserva.
7. Pulsar START y comprobar salida controlada. Repetir durante ejecución y pausa.
8. Registrar duración y observaciones; treinta minutos forman parte de G01, pero no cierran G01 mientras falten prueba de archivos, medición de recursos y depuración con símbolos.

G00/G01 siguen abiertas. Próximos trabajos independientes: F01.03 (probe de archivos/configuración), F01.06 (recursos reales) y F01.05 (depuración). F02 específico del juego y F04 necesitan la edición PS2 identificada.
