# F03.04 / IR-T7e — Verificación independiente del perfil de colisión

2026-10-23. **IR-T7e completada.** Cierre de verificación del
[perfil de registros](../../schemas/collision-intermediate-v1.md), requisitos
IR21/IR22/IR24–IR26. El alcance es integración y custodia; no acredita
respuesta física ni nuevas transiciones de daño/muerte.

## Oráculo independiente

[collision_wire_oracle.py](../../tests/collision_wire_oracle.py) usa solo
biblioteca estándar, una tabla propia de los ocho rangos y `int.from_bytes`.
Construye una tabla de los 32 slots de actor antes de recorrer enlaces; no
importa constantes, decoder, codec, preparador ni exportador de producción.
Una prueba de arquitectura impide introducir esas dependencias.

`inspect_package(files, manifest=None)` contrasta nombres, tamaños, hashes,
los campos de los dos bancos y la lista de actores, las fases y ambas vistas
JSON. `compare_sources(files, read_source)` coteja además los 240 bloques
completos con RAM extraída de ZIP mediante la biblioteca estándar, los 30
recibos completos, tres informes, inventario y PC/ciclo/GPR/delay/CRC.
El lector de fuentes se inyecta; cada estado se consume antes del siguiente.
La igualdad de metadatos distingue bool/int/float y el signo de cero flotante.

El modo sin fuentes acredita coherencia del paquete. No puede autenticar por
sí solo que un hash histórico corresponda al contenido declarado: ese vínculo
requiere las fuentes fijadas o custodia previa del manifiesto. Se prueba esta
limitación introduciendo pérdidas coherentes localmente que el cotejo de origen
sí detecta.

## Matriz de integración

[Suite IR-T7e](../../tests/python/test_collision_integration.py): **51 casos**.
Se suman a los 206 casos de IR-T7c/d, para **257 pruebas del perfil**.

| Área | Evidencia de prueba |
|---|---|
| Origen independiente | 30 estados, 30 recibos, tres informes, inventario; 240 bloques completos, incluidos espacios inactivos. |
| Fallo compartido | Exportador y vista aceptan un estado de actor no objetivo alterado mediante un decoder sustituido; el oráculo independiente lo rechaza. |
| Pérdida silenciosa | Bytes de actor/personaje inactivo y cola vacía modificados con hashes recalculados; campos desconocidos borrados de informe/recibo. El cotejo con fuentes detecta todas las pérdidas. |
| Metadatos | Vista discrepante, bool cambiado por int, signo de cero flotante, JSON duplicado, inventario incompleto/extra y afirmación física falsa en manifiesto. |
| Entradas privadas | Archivo vacío/truncado, cambio del mismo tamaño, directorio, FIFO, symlink y tamaño excesivo; rechazo antes de llamar al writer. |
| ZIP con nuevos pins sintéticos | RAM ausente/duplicada, datos añadidos, deflate dañado, cifrado, internals excesivos y ZIP64; rechazo antes de construir el intermedio. |
| Publicación | Fallos en apertura, escritura parcial/ENOSPC, fsync, relectura de hash, archivo extra, reemplazo de directorio, escritura del manifiesto temporal, enlace final y archivo preexistente. |
| Orden de publicación | El enlace final solo se intenta después de releer los 242 archivos y el manifiesto temporal; el oráculo verifica ese contenido en disco. |
| Exclusividad | Dos hilos con el mismo ID: exactamente uno publica y el otro recibe `FileExistsError`; paquete final verificado independientemente. |
| Reconstrucción | Desaparecen todas las rutas configuradas de origen; se reconstruye solo con intermedio y bloques de salida y se coteja con el oráculo. |
| Python optimizado | El oráculo detecta el paquete alterado con `python -O`; no depende de `assert` para sus comprobaciones. |

Tras los fallos de publicación puede quedar una carpeta privada parcial para
diagnóstico, pero no un `manifest.json` de éxito. Reintentar con el mismo ID
falla y conserva esos archivos. No se promete rollback de archivos parciales
ni resistencia frente a cualquier mutación externa posterior a la publicación.

## CI y cobertura

El [gate](../../tools/qa/coverage_gate.py) conserva el modo global y añade
`--files` para exigir el umbral **en cada módulo solicitado**. Seis negativos/
positivos nuevos prueban que un total global alto no oculta un módulo con
líneas o ramas inferiores al 80 %, sin medición o ausente del informe.
La suite del gate tiene diez casos; ejecución enfocada: **267 pruebas aprobadas**.

El [workflow](../../.github/workflows/ci.yml) aplica el gate a los cuatro módulos
`collision_registry`, `collision_evidence`, `collision_intermediate` y
`prepare_collision_intermediate`, usando el mismo informe del job Python.
El oráculo se añade a Ruff. No se añade dependencia ni material privado a CI.

Medición enfocada del perfil: **339/340 líneas (99,71 %)** y **93/94 ramas
(98,94 %)**. Los tres módulos puros alcanzan el 100 %; el preparador tiene
82/83 líneas y 11/12 ramas. El entrypoint se prueba en un subproceso separado,
que esa medición no contabiliza. Los cuatro pasan el gate individual.
Los wrappers de otros perfiles del writer compartido se cubren en la suite
global; no se presenta su cobertura parcial enfocada como cobertura completa.

Regresión completa: **5.142 aprobadas y seis fallos** del supervisor de
procesos porque el sandbox impide ejecutar `/bin/ps`. Se conservó ese JUnit.
Al repetir exclusivamente `test_supervised_process.py` fuera del sandbox,
sus **23 casos pasaron**, incluidos los seis anteriores. Quedan verificados
los **5.148 casos únicos** del conjunto, sin cambiar ni omitir pruebas.
No se presenta el intento inicial como una ejecución completamente verde.

El gate global y los cuatro gates del perfil pasan sobre el informe de la
suite completa: 9.499/9.665 líneas (98,28 %) y 2.944/3.054 ramas (96,40 %),
medidas en el intento restringido; no se mezcló la cobertura del reintento. El writer compartido obtiene 103/103 líneas y 20/20 ramas.
Ruff check/format pasa sobre 249 archivos y la custodia del repositorio
pasa con cero errores. No se ha ejecutado GitHub Actions ni una compilación ARM.

Comandos reproducibles:

```sh
rtk proxy .venv/bin/pytest -q tests/python/test_collision_registry.py tests/python/test_collision_intermediate.py tests/python/test_collision_integration.py tests/python/test_coverage_gate.py --cov=tools.pipeline.collision_registry --cov=tools.pipeline.collision_evidence --cov=tools.pipeline.collision_intermediate --cov=tools.pipeline.prepare_collision_intermediate --cov=tools.pipeline.private_texture_output --cov=tools.qa.coverage_gate --cov-branch --cov-report=term-missing --cov-report=json:build/collision-intermediate/verification-coverage.json --junitxml=build/collision-intermediate/verification-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/collision-intermediate/verification-coverage.json --files tools/pipeline/collision_registry.py tools/pipeline/collision_evidence.py tools/pipeline/collision_intermediate.py tools/pipeline/prepare_collision_intermediate.py
rtk proxy .venv/bin/pytest --cov=tools --cov-report=json:build/collision-intermediate/verification-full-coverage.json --cov-report=xml:build/collision-intermediate/verification-full-coverage.xml --cov-report=term --junitxml=build/collision-intermediate/verification-full-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/collision-intermediate/verification-full-coverage.json
# Reintento local con acceso a /bin/ps fuera del sandbox:
rtk proxy .venv/bin/pytest -q tests/python/test_supervised_process.py --junitxml=build/collision-intermediate/verification-supervisor-retry.xml
```

## Fuentes reales: comprobación local de lectura

El preparador convirtió nuevamente las 30 capturas en memoria. El oráculo,
mediante un lector independiente de las fuentes, verificó los **1.571.670 bytes**
de los 240 bloques, tres documentos completos, 30 recibos, CPU y procedencia.
Los informes fuente siguen intactos. El SHA-256 del intermedio permanece igual
al de IR-T7d: `333685a96773eec513ebcd7960cba2688dfb61b9663ac87544b45a8665766cf7`.

Se conserva `build/collision-intermediate/verification-private-memory-v1.json`
como comprobante local de metadatos. No contiene rutas del host ni bytes del
juego. El oráculo aplicado tiene SHA-256
`39e63921ced90764e56f6b5a6fb8bbd9525ffe9aa84db626bd6b649ff2a62e6a`.
Esta comprobación no forma parte de CI y no publica las entregas A/B.

## Comprobantes locales

`build/collision-intermediate/verification-validation-v1.json`, SHA-256
`92f9294d441fd54ea8c0eb59b0ac59cca4506505f1c0987701921fa97a81c8e6`,
vincula por hash contrato, código, tests, workflow, cobertura y los tres JUnit:
el enfocado, el global con sus fallos y el reintento del supervisor.
Se comprobaron los nombres de los seis casos fallidos contra el reintento
aprobado; el intento original no se borró ni se sustituyó.

El comprobante de cotejo privado en memoria,
`build/collision-intermediate/verification-private-memory-v1.json`, tiene
SHA-256 `0e600f0fb68755a25da1417aa86386b40d55c6965ed5f798461bf7eae8b4b2be`.
Solo contiene metadatos y límites; las fuentes privadas no se incluyen en los
artefactos de CI. Los comprobantes IR-T7d anteriores permanecen históricos.

## Siguiente tarea

**IR-T7f:** publicar dos conversiones privadas de las mismas 30 capturas,
releer los 242 archivos y sus manifiestos, compararlos y verificar la
reconstrucción desde los paquetes con este oráculo. No son dos adquisiciones
independientes de PCSX2.

F03.04 global, G02/G03, formas físicas, activadores y daño/muerte siguen
pendientes. No se arrancó PCSX2, no se compiló un visor ni se modificó la SD.

**Seguimiento:** [IR-T7f completada](f03-04-collision-publication.md), con
publicación y comparación A/B y reconstrucción desde ambos paquetes. Las
mediciones y el alcance histórico de IR-T7e anteriores se conservan.
