# F03.04 / IR-T7d — Integración de registros de colisión

2026-10-23. **IR-T7d completada** conforme al
[perfil EARS IR19–IR27](../../schemas/collision-intermediate-v1.md).
IR-T7e/f, F03.04 global y G02/G03 permanecen abiertos.

El adaptador conserva los ocho rangos de cada captura y puede reconstruir
la observación sin consultar estados, ISO, recibos externos o PCSX2.
El preparador coteja las fuentes fijadas y publica mediante el writer privado
existente. La publicación se verificó con fixtures propios; las 30 capturas
reales se convirtieron y reconstruyeron **en memoria**, sin publicar todavía
las dos entregas privadas A/B de IR-T7f.

## Implementación y responsabilidades

- [collision_evidence](../../tools/pipeline/collision_evidence.py): política
  de identidad, fase y enlaces entre informes, recibos y observaciones.
  Compara valores con tipos JSON exactos y conserva metadatos desconocidos.
- [collision_intermediate](../../tools/pipeline/collision_intermediate.py):
  adaptador puro `make_collision`/`export_collision`. Valida inventario exacto,
  tamaños y hashes, vuelve a decodificar los bloques y coteja la vista derivada.
- [prepare_collision_intermediate](../../tools/pipeline/prepare_collision_intermediate.py):
  I/O acotado, pins contra inventario IR-T7a, comprobación de versión/CRC y
  PC/ciclo/GPR/delay; procesa un estado cada vez, sin extraer el ZIP a disco.
- [private_texture_output](../../tools/pipeline/private_texture_output.py):
  nuevo wrapper con nombres calculados desde los 30 slots permitidos.
  Reutiliza escritura exclusiva, permisos 0700/0600, relectura SHA-256 y
  publicación del manifiesto al final. No incorpora lógica de registros.

Son **242 archivos de contenido**: `intermediate.json`,
`collision-observations.json` y 240 bloques originales. El writer añade
`manifest.json` y conserva su enlace de preparación `.manifest.pending.json`,
igual que las entregas anteriores. La vista derivada no reemplaza al paquete.
Las salidas declaran `observed_registry`, `capabilities=[]` y falsos los flags
de nueva ejecución, reconstrucción de savestate, pointees de escenario,
respuesta física y transiciones de daño.

Durante el cotejo privado apareció una distinción relevante: `targets` del
informe incluye también los once actores `0x020C` antiguos en las capturas
posteriores, junto con los tres `0x0209`. Se verifican todos los campos que
proceden de la lista enlazada, conservando su orden. El banco de personajes
posterior sigue teniendo solo las dos entradas Heather/Alessa. La prueba
sintética reproduce los actores antiguos aún enlazados y rechaza contradicciones
sobre ellos. No se infiere capacidad de recibir daño desde esa presencia.

## Verificación sintética y regresión

[Suite nueva](../../tests/python/test_collision_intermediate.py): **106 casos**;
junto con los 100 del decoder, **206 aprobados**. Incluye:

- Dos bancos distintos, filas repetidas por propietario, actores antiguos,
  bytes inactivos/opacos y metadatos con bool/int/float/cero negativo.
- Conservación de documentos y recibos completos, ausencia de alias/mutación,
  regeneración idéntica y reconstrucción tras eliminar las fuentes sintéticas.
- Rechazo de cambios en bytes, nombres, tamaños, hashes, inventario, fases,
  identidad, recibos, informes, estados truncados y versión/CRC incorrectos.
- Bytes alterados con observación y hashes recalculados: se mantiene el rechazo
  de conteos, propietarios, sala, índices de escenario e instancias de fase.
- Symlink de entrada, salida existente sin sobrescritura, permisos privados,
  inventario de 242 archivos y hashes releídos desde el manifiesto.
- CLI mediante módulo con Python `-O`: un input inválido no publica salida ni
  imprime rutas o datos privados.

Cobertura de los cuatro módulos del perfil: **339/340 líneas (99,71 %)** y
**93/94 ramas (98,94 %)**, combinada **99,54 %**. El gate de líneas y ramas
≥80 % pasa. La línea/rama no contabilizada es el entrypoint de módulo, que se
prueba mediante subproceso separado. No se presenta como 100 %.

Regresión adicional: **282 pruebas** de los tres perfiles intermedios previos
y estados PCSX2; **180 pruebas** de textura/geometría y captura multirrango.
Total ejecutado en esta tarea: **668 pruebas aprobadas**.
Ruff check y format pasan sobre **247 archivos**; custodia del repositorio
pasa con cero errores. El job Python existente descubre la nueva suite y
mantiene su gate; no se declara una ejecución remota de CI ni una compilación ARM.

Comandos principales:

```sh
rtk proxy .venv/bin/pytest -q tests/python/test_collision_intermediate.py tests/python/test_collision_registry.py --override-ini addopts='' --cov=tools.pipeline.collision_evidence --cov=tools.pipeline.collision_intermediate --cov=tools.pipeline.prepare_collision_intermediate --cov=tools.pipeline.collision_registry --cov-branch --cov-report=term-missing --cov-report=json:build/collision-intermediate/integration-coverage.json --junitxml=build/collision-intermediate/integration-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/collision-intermediate/integration-coverage.json
rtk proxy .venv/bin/pytest -q tests/python/test_character_intermediate.py tests/python/test_character_render_intermediate.py tests/python/test_map_intermediate.py tests/python/test_pcsx2_state.py --override-ini addopts='' --junitxml=build/collision-intermediate/integration-regression.xml
rtk proxy .venv/bin/pytest -q tests/python/test_texture_inspection.py tests/python/test_geometry_inspection.py tests/python/test_observer_multirange.py --override-ini addopts='' --junitxml=build/collision-intermediate/integration-custody.xml
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

## Cotejo de las fuentes privadas

Se fijó el inventario IR-T7a con SHA-256
`c7f7a95b1bb191d956a9524ea601ed0d0fc3c76ce303b44975aac4524a8e6c69`.
Desde sus pins se preparó la configuración local ignorada
`build/collision-intermediate/inputs-v1.json`; no se copiaron rutas del host
al intermedio. Se releyeron y verificaron los tres informes y los 30 pares
estado/recibo, slots 02, 08–35 y 36. Se compararon los ocho bloques de cada
estado con los hashes inventariados, sin seguir los punteros de escenario.

La conversión produjo en memoria **1.571.670 bytes de bloques conservados** y
**2.001.816 bytes de contenido total** para los 242 archivos. Su reconstrucción
fue idéntica. Hash del `intermediate.json` resultante:
`333685a96773eec513ebcd7960cba2688dfb61b9663ac87544b45a8665766cf7`.
Los hashes de los informes fuente siguen iguales después del cotejo.

Comprobantes locales, sin buffers originales ni rutas privadas:

- `build/collision-intermediate/integration-validation-v1.json`, SHA-256
  `dd31be84b6c3caf85c0aa8605ed4b71ba8ed155979192b2643f91f2d9b62c08e`;
  vincula código, contrato, tests, cobertura, JUnit y la configuración por hash.
- `build/collision-intermediate/integration-dry-run-v1.json`, SHA-256
  `16101d08c12d6ea937d9ed24a32be5c7039c289e6a6e85a05afe8b82edfeb563`;
  conserva hashes de las 242 salidas calculadas en memoria y las limitaciones.

La futura publicación usa el CLI ya probado, con raíz privada externa y un
`run-id` nuevo. No se debe reutilizar un directorio ni reconstruir pins a partir
de fuentes modificadas para eludir un rechazo.

```sh
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_intermediate --inputs build/collision-intermediate/inputs-v1.json --private-root /Users/germancontreras/sh3-private-data --run-id f03-04-collision-intermediate-v1-a
```

## Siguiente tarea y límites

**IR-T7e:** completar el oráculo independiente del conjunto y la matriz de
fallos de integración/publicación, registrando la batería final del perfil.
Las 206 pruebas actuales y el gate son su base, no un cierre anticipado de
esa tarea. Después, **IR-T7f** publicará y releerá dos conversiones privadas
de las mismas capturas y verificará la reconstrucción desde sus paquetes.
A/B no serán adquisiciones independientes de VM.

No se arrancó PCSX2 ni se ejecutó el visor en consola. No se generó un build
para la SD. Colisión jugable, superficies, activadores, daño y muerte siguen
pendientes; los candidatos `.cld` permanecen sin contrato decodificado.

**Seguimiento:** [IR-T7e completada](f03-04-collision-verification.md), con
oráculo independiente, matriz de fallos y gate individual en CI. El siguiente
paso es IR-T7f; los resultados de IR-T7d anteriores conservan su alcance histórico.
