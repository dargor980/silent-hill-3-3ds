# F01.08 — automatización y diagnóstico de cierre

Fecha: **2026-10-16** (America/Santiago). **Automatización local completada y verificada. Ensayo físico, ejecución remota de Actions y cierre G01 pendientes.** No se accedió a la ISO ni se extrajeron originales.

## Cambio y criterios

[Contrato EARS B01-B07](../compatibility/build-contract.md), [ticket detallado](../specs/sh3-3ds/tasks/F01.md#f0108) y [hoja de treinta minutos](../compatibility/diagnostic-soak.md). Se corrigen dos huecos: CTest podía aceptar cero pruebas y upload-artifact podía encontrar algunos archivos sin garantizar la presencia de todo el conjunto previsto.

Los cuatro presets ahora fallan si no encuentran tests y tienen límite general de 120 segundos por caso; los límites específicos menores siguen vigentes. El script ARM verifica los ocho archivos obligatorios antes de producir `artifact-check.json`: regularidad, contenido no vacío, ID, pareja ELF/3DSX, cabeceras básicas/ARM, fixture, checksums y digest de imagen esperado. El recibo conserva tamaños/hashes y se crea de forma exclusiva. La verificación posterior exige el mismo recibo canónico e inventario/imagen intactos; siete regresiones adicionales rechazan recibo ausente, vacío, enlazado, sobredimensionado, alterado o cambios de paquetes/imagen. `--record` nunca repara evidencia existente.

CI conserva JUnit, cobertura y logs de build incluso ante fallos, exige reportes no vacíos en la ruta exitosa y usa Bash con pipefail para no ocultar errores detrás de tee. El artefacto incluye el recibo. Se mantienen permisos de lectura, pins y retención de 14 días; no se ejecutó ni publicó un workflow remoto.

SOLID: el shell coordina procesos; el bundle conserva la verificación de depuración; QA verifica el conjunto completo; la CLI registra el recibo. Se reutilizan hashing y validación de ID. Las herramientas simuladas se sustituyen por PATH únicamente en pruebas. No se modificaron el runtime C++, dominio ni puertos.

## Evidencia local

Directorio: `build/f01-08/`, ignorado por Git. La copia `clean-project/` contiene **59 entradas sintéticas** enumeradas y hasheadas en `clean-inputs.json`; se verificó que coinciden con el workspace y la copia al terminar. No se copió caché ni build previo. Se conservó una primera ejecución bajo `initial-project/` y se repitió la copia limpia tras añadir la comparación del recibo; los resultados de la tabla corresponden a la copia final. Los cambios aún no están en un commit: la identidad de fuentes se conserva en manifiestos locales; el checkout real de Actions queda pendiente. Docker recibió solo esa copia y el venv Linux de herramientas en solo lectura, con imagen fijada, filesystem raíz de solo lectura, sin red, sin capabilities y tmpfs temporal.

| Validación | Resultado / archivo |
|---|---|
| Pruebas nuevas de automatización | **68/68**: ocho archivos × ausente/vacío/symlink, mezcla, formatos/metadata, script con fallos, evidencia conservada y cuatro presets × vacío/fallo/éxito |
| Batería Python 3.14.6 | **295/295**, `python-tests.log`, `pytest.xml` |
| Cobertura Python | **704/732 líneas (96,17 %)**; **289/304 ramas (95,07 %)**; `python-coverage.json/xml`; gate independiente aprobado |
| AppleClang 15, Release | **47/47 CTest**, sin omitidos; `clean-project/host-release.log` y JUnit |
| LLVM 22.1.4, ASan/UBSan | **47/47 CTest**, sin hallazgos ni omitidos; `clean-project/host-sanitize.log` y JUnit |
| GCC 12.2, Linux ARM64 | **47/47 CTest**, sin omitidos; `clean-project/host-coverage.log` y JUnit |
| Cobertura C++ portable | **302/303 líneas (99,67 %)**; **219/224 ramas (97,77 %)**; 38/38 funciones. XML/JSON en `clean-project/build/` |
| SDK oficial fijado | simple_tri compilado dos veces, 3DSX/SMDH idénticos; probe C++17 ARM aprobado. `clean-project/toolchain.log` y `build/toolchain-check/` |
| Diagnóstico ARM | 12 unidades C++; ELF/3DSX/SMDH generados, bundle y conjunto de artefactos aprobados; `clean-project/build-3ds.log` |
| Calidad | Ruff check/format, actionlint, Bash syntax y contratos de repositorio aprobados; `quality.log` |

El test del script ejecuta herramientas simuladas que devuelven error al configurar, compilar o consultar paquetes. También retira el SMDH. La canalización real a tee con pipefail devuelve error y no crea recibo en ninguno de esos casos. Los fixtures que comienzan con cabeceras válidas son bytes sintéticos de prueba; no se presentan como ejecutables funcionales.

Los 47 casos CTest y el alcance portable de cobertura no cambian. No se añade cobertura ficticia del SDK/hardware. gcovr avisa que su opción genérica `output` no se utiliza cuando se pasan destinos XML/JSON explícitos; ambos reportes se generaron correctamente. La suite Python requiere CMake/CTest en PATH para estas regresiones; las imágenes host de Actions los proporcionan y registran su versión, pero siguen sin ser entornos herméticos.

## Build conservado

`build/f01-08/artifacts/`, ID **7c369f7e8c79**, imagen `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.

El ID y los ocho archivos preexistentes coinciden con F01.07: las fuentes del runtime y el SDK no cambiaron, y las compilaciones usan la misma ruta interna `/work`. F01.08 aporta el recibo y los gates de automatización. Esta coincidencia concreta no garantiza reproducibilidad entre otros hosts o versiones.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| sh3_diagnostic.3dsx | 215924 | `6ae36ddfee92bf9eb2e648b0b13412e05dbb536765216905d14f2b3b53771115` |
| sh3_diagnostic.elf | 1863768 | `e98635a738949ab5f7ae7694178d2e8042e1458fa41382853c0b5a2e217422e1` |
| debug-bundle.json | 357 | `54b780cdee1ba276eab82ebf8a12053a4e4d80aedca9f04cf0839ab4ebbfabfd` |
| artifact-check.json | 1286 | `4b35c9fcdf4433bb2511bbafeaf36b733b52cc273b416a885671873a6003c00b` |

El inventario completo está en `build/f01-08/artifacts.json`; el recibo enumera los ocho archivos y la imagen esperada. Verificación repetible, desde la raíz del proyecto:

```sh
python -m tools.qa.build_artifacts --directory build/f01-08/artifacts \
  --probe tests/fixtures/synthetic/probe.txt --sdk-image toolchains/devkitpro-image.txt
python -m tools.debug.bundle verify --directory build/f01-08/artifacts --build-id 7c369f7e8c79
```

Para repetir el build usar otra copia limpia: `bash scripts/check_3ds_toolchain.sh` y `bash scripts/build_3ds.sh` dentro de la imagen fijada. Para host, configurar/construir los presets y ejecutar `ctest --preset PRESET --output-junit test-results.xml`. Los comandos completos y fuentes de esta ejecución quedan registrados junto a los logs. No regenerar manifiestos sobre una evidencia que no verifica.

## Pendientes y siguiente tarea

No se ejecutó este build en consola ni se realizó una sesión prolongada en emulador. `target.json` conserva `hardware_execution=not_tested`. El ring de 120 muestras no conserva treinta minutos de historial: la hoja física registra tiempo activo e interrupciones, checkpoints cada cinco minutos, audio observado y retorno al launcher. El error simbolizado del mismo build/entorno debe acompañar la sesión; la evidencia de depuración F01.05 es histórica.

F01.02-F01.07 mantienen sus validaciones físicas pendientes; **F01.08, G01 y M0 permanecen abiertos**. El recibo verifica consistencia, no procedencia firmada ni comportamiento de consola. LIC07 continúa aplicando antes de compartir binarios. La siguiente tarea independiente es **F02.01 — enumerar archivos y contenedores**, usando G00 y herramientas verificadas; cualquier escritura de derivados originales requiere la raíz privada externa explícita.

## Identidad de fuentes de esta entrega

`build/f01-08/source-manifest.json`: 73 archivos de código, pruebas, configuración y documentación, excluido este informe para evitar autorreferencia; SHA-256 `223ef961432629356f4c86ba056e1bf6df48ee240cfd0717fd85fd26bcb92c7d`. `clean-inputs.json`: 59 entradas del build; SHA-256 `f39c32182dea7345323acd3212640af5d59b6f650baa99af88186c5f24b764e9`. Comandos en `commands.txt`; artefactos completos en `artifacts.json`.
