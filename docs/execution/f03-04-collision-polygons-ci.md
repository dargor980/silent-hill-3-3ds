# F03.04 / CF-T5c — Integración del decoder poligonal en CI

2026-10-23. **CF-T5c completada: configuración integrada y job de calidad verificado localmente.**
Continúa [CF-T5b](f03-04-collision-polygons-verification.md) y el contrato
[CP01–CP15](../../schemas/ps2-cld-polygons-v1.md).

## Configuración integrada

El job `quality` de [ci.yml](../../.github/workflows/ci.yml) incorpora
`tests/cld_polygon_wire_oracle.py` y `tests/cld_polygon_fixtures.py` a Ruff y
a la comprobación de formato. Los tests del perfil se descubren mediante
la configuración habitual de pytest.

El gate individual ahora comprueba cinco módulos: los cuatro de registros
IR-T7 y `tools/pipeline/decoders/ps2_cld_polygons.py`. Cada uno debe alcanzar
al menos 80 % de líneas **y** de ramas. Se conserva el gate global separado.
La [prueba de contrato de CI](../../tests/python/test_collision_integration.py)
verifica la lista exacta de módulos y la presencia de los tres helpers de
colisión en ambos comandos de Ruff.

Se conserva la publicación de `python-coverage.xml`, `python-coverage.json`
y `pytest.xml` con `if: always()` y retención de 14 días. La comparación del
YAML con la versión base confirma que los jobs `host`, `cpp-coverage` y
`nintendo-3ds`, sus dependencias, las acciones fijadas, permisos y disparadores
no cambian. El decoder, los vectores, el oráculo, el constructor y las pruebas
del perfil conservan los hashes del comprobante CF-T5b.

## Verificación local y alcance

Se ejecutan los comandos de lint, formato, contratos de repositorio, suite
Python completa, gates y comprobación de archivos **leídos del YAML**.
El ejecutor local solo sustituye `python` por el intérprete de `.venv` y
envuelve cada comando con RTK; conserva orden, argumentos y resultados.
Los logs y comprobantes están bajo `build/cld-polygons/cf-t5c/`.

Entorno local: macOS, Python 3.14.6; coinciden las versiones de los 16 paquetes
del lockfile aplicables a esta plataforma. `colorama` tiene condición Windows
y no se exige aquí. No se reinstalaron dependencias. El runner remoto sigue
siendo Ubuntu 24.04 con Python 3.13.7: esta ejecución local no acredita esa
plataforma ni una corrida de GitHub Actions.

La primera corrida bajo sandbox aprobó 8.301 pruebas y falló en seis casos
de supervisión de procesos porque `/bin/ps` devolvió `Operation not permitted`.
Se conservan logs, cobertura, JUnit y recibo de ese intento en
`build/cld-polygons/cf-t5c/sandbox-attempt/`. Al ejecutar con permiso para
consultar procesos, las 23 pruebas de `test_supervised_process.py` pasan.
No se alteraron ni omitieron esas pruebas, ni se modificó el supervisor.

La repetición completa con ese permiso aprueba los ocho comandos del job:
**8.307 pruebas principales aprobadas, cero fallos, errores o skips**.
Incluye las 3.159 pruebas del perfil poligonal. Cobertura medida:

| Ámbito | Líneas | Ramas |
|---|---:|---:|
| Global Python | 9.609/9.764 = 98,41 % | 3.006/3.108 = 96,72 % |
| Decoder poligonal | 99/99 = 100 % | 54/54 = 100 % |

Pasan el gate global y el individual de los cinco módulos. La validación
adicional interpreta los XML y JSON, coteja sus contadores de cobertura y
verifica que los 3.159 casos poligonales están presentes y sin fallos.
Se conservan copias del XML/JSON de cobertura y JUnit bajo
`build/cld-polygons/cf-t5c/quality-artifacts/`.

### Conteo JUnit reconciliado

El resumen JUnit declara 8.363 ejecuciones mientras contiene 8.307 nodos
`testcase`. La diferencia corresponde a 56 subcasos `unittest.subTest` de
las pruebas de iluminación. Se verificó por separado el mismo archivo:
17 pruebas y 56 subcasos aprobados; su JUnit declara 73 y contiene 17 nodos.
El código instalado de pytest 9.1.1 contabiliza los informes de subcasos en
el resumen. Los reportes se conservan sin reescribirlos; el comprobante
distingue **8.307 pruebas principales**, **56 subcasos** y **8.363 declarados**.
No se contabiliza la corrida aislada como pruebas adicionales del proyecto.

### Controles del gate sobre la cobertura medida

Se generan siete informes de control con los totales globales medidos y
las filas de los cinco módulos. Solo se altera la fila del decoder en los
casos de frontera o fallo. Se usa el mismo `coverage_gate --files` del YAML:

| Control | Gate global | Gate individual |
|---|---|---|
| Medición original | Aprobado | Aprobado |
| Exactamente 80 % de líneas y ramas | Aprobado | Aprobado |
| 79 % de líneas | Aprobado | Rechazado |
| 79 % de ramas | Aprobado | Rechazado |
| Módulo ausente | Aprobado | Rechazado |
| Denominadores vacíos | Aprobado | Rechazado |
| Fila inválida | Aprobado | Rechazado |

Las catorce ejecuciones CLI producen los códigos esperados. Los casos de
cobertura baja/vacía identifican el módulo afectado; ningún resultado de
control sustituye el informe real. No se relajaron umbrales ni se modificó
el código del gate.

## Reproducción

```sh
rtk proxy .venv/bin/python -m ruff check tools tests/python tests/observer_wire_oracle.py tests/texture_wire_oracle.py tests/geometry_wire_oracle.py tests/animation_wire_oracle.py tests/character_wire_oracle.py tests/character_material_wire_oracle.py tests/character_lighting_wire_oracle.py tests/character_world_wire_oracle.py tests/collision_wire_oracle.py tests/cld_polygon_wire_oracle.py tests/cld_polygon_fixtures.py
rtk proxy .venv/bin/python -m ruff format --check tools tests/python tests/observer_wire_oracle.py tests/texture_wire_oracle.py tests/geometry_wire_oracle.py tests/animation_wire_oracle.py tests/character_wire_oracle.py tests/character_material_wire_oracle.py tests/character_lighting_wire_oracle.py tests/character_world_wire_oracle.py tests/collision_wire_oracle.py tests/cld_polygon_wire_oracle.py tests/cld_polygon_fixtures.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy .venv/bin/python -m pytest --cov=tools --cov-report=xml:build/python-coverage.xml --cov-report=json:build/python-coverage.json --cov-report=term-missing --junitxml=build/pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/python-coverage.json
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/python-coverage.json --files tools/pipeline/collision_registry.py tools/pipeline/collision_evidence.py tools/pipeline/collision_intermediate.py tools/pipeline/prepare_collision_intermediate.py tools/pipeline/decoders/ps2_cld_polygons.py
rtk proxy test -s build/python-coverage.xml
rtk proxy test -s build/pytest.xml
```

El comprobante final se conserva en
`reports/local/f03-04-collision-polygons-ci-v1.json`.
Fija hashes del workflow, prueba de integración, fuentes CF-T5b, logs,
artefactos, verificación de subcasos y controles negativos. La revisión final
de contratos/documentación y `git diff --check` también pasan.
No se han ejecutado builds C++/ARM nuevos, el emulador ni la consola; esos
jobs no forman parte del cambio. El cotejo del decoder con fuentes privadas
A/B corresponde a **CF-T6**. La extensión del intermedio CF-T7 y la respuesta
física permanecen pendientes.
