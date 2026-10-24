# F03.04 / CF-T7d — Oráculo independiente y gates permanentes

2026-10-23. **CF-T7d completada.** Verificación del [perfil CPI01–CPI14](../../schemas/collision-polygons-intermediate-v1.md),
continuación del [preparador CF-T7c](f03-04-collision-polygons-preparation.md).
La evidencia de esta tarea usa solo datos propios; la publicación y el cotejo
de los paquetes privados A/B corresponden a CF-T7e.

## Oráculo y fidelidad externa

[`collision_polygon_package_oracle`](../../tests/collision_polygon_package_oracle.py)
implementa dos operaciones separadas:

- `inspect_package(files, manifest=None)` valida JSON, gramática, presupuestos,
  inventario, hashes, clasificación, vistas completas y procedencia interna.
  Reconstruye los archivos lógicos desde los bytes suministrados, conservando
  buffers íntegros y regenerando las vistas de los aceptados.
- `compare_sources(files, entries, sources, provenance, scene_links)` compara
  el paquete con datos originales suministrados explícitamente. Detecta pérdida
  de padding, campos desconocidos, tipos o recursos enteros aun cuando se hayan
  recalculado todos los hashes del paquete para hacerlo autoconsistente.

El oráculo usa stdlib y el [lector CP independiente](../../tests/cld_polygon_wire_oracle.py).
No importa módulos `tools`, el codec JSON, constantes del adaptador ni
constructores de fixtures. La validación de árbol JSON usa recorrido iterativo;
la comparación completa conserva tipos y signo del cero mediante el comparador
independiente CP. La clasificación precede globalmente a las vistas y estas a
la procedencia, según el contrato. No contiene `assert` como validación de datos.

El [constructor de paquetes propios](../../tests/collision_polygon_package_fixtures.py)
es otro módulo, sin importaciones de producción ni del oráculo de paquete.
Conserva intactos los 24 ejemplos materializados de CF-T7a. Los límites,
códigos y campos del contrato permanecen sin cambios.

## Pruebas ampliadas

La [batería de conformidad](../../tests/python/test_collision_polygon_conformance.py)
añade **248 pruebas**. Incluye:

- Los 24 ejemplos originales y 78 paquetes manipulados: hashes actualizados
  no ocultan coordenadas, palabras, tipos, signo de cero, referencias, formas
  sin uso, vistas incompletas, códigos o procedencia incorrectos.
- Los 49 vectores CP no vacíos que caben en el transporte: cada fuente se
  conserva íntegra con su primer código, y las aceptaciones se comparan
  también con sus vistas materializadas originales.
- Recursos 0/1/285/286, fuentes 0/1/751/752/65.536/65.537 bytes, raíz y vista
  de 1 MiB y exceso, manifiesto de 256 KiB y exceso, agregado de 40 MiB y
  exceso. Un límite físico exacto no implica aceptación si falla después
  la gramática, el inventario o la semántica.
- Árbol JSON en límites y exceso de nodos, profundidad, claves, strings e
  enteros; UTF-8, duplicados, no finitos, surrogates y tipos de argumentos.
  Enlaces históricos: límites escalares, pins, total y duplicados entre filas.
- Dieciséis fallos inyectados en el decoder compartido por constructor y
  exportador: su round-trip sigue pasando, pero el oráculo independiente los
  detecta. Otro control cambia la clasificación del primer error. Un fallo
  del serializador elimina una extensión: solo el cotejo externo detecta
  esa pérdida en un paquete internamente coherente.
- Omisión coherente de recursos no soportados/rechazados, cambios opacos y
  pérdida de extensiones/tipos. No se confunde coherencia con autenticación
  de fuentes ni se inventan vínculos RAM desde un pin autoconsistente.
- Integración completa con 285 fuentes propias, 30 enlaces históricos
  sintéticos y las tres clasificaciones. Todos los valores esperados del
  cotejo externo proceden del corpus original, incluidos procedencia/enlaces;
  se reconstruye después de retirar las fuentes.

Los 102 paquetes de ejemplos/manipulaciones se ejecutan en subprocesos
normal y `-O`, con cada lector: **408 evaluaciones**. El guard de auditoría
bloquea aperturas, red y procesos durante reconstrucción y se comprueba
mediante una apertura deliberada que debe fallar. El proceso del oráculo
además bloquea importar `tools`. Resultados, bytes e inmutabilidad coinciden
en ambos modos. El control AST verifica sus dependencias y las del constructor.

La primera ampliación de la prueba de vectores CP intentó leer `expected_code`
en los diez ejemplos de aceptación, cuyo contrato usa `expected` para la vista.
Se corrigió el consumidor de fixtures y se agregó su cotejo completo de vista;
no se cambiaron expectativas, fixtures ni producción. Se conserva ese JUnit
fallido como `build/cld-intermediate-contract/cf-t7d/first-focused-attempt.xml`.

## CI y comprobaciones locales

El job `quality` de [ci.yml](../../.github/workflows/ci.yml) incluye los dos
helpers nuevos y el constructor de receta CF-T7c en lint/formato. Pytest
mantiene descubrimiento completo, sin selecciones ni exclusiones nuevas.

Se conservan el gate global y los cinco gates individuales IR-T7/CP, y se
agregan estos cinco, cada uno con mínimo **80 % de líneas y de ramas**:

- `collision_polygon_intermediate.py`
- `collision_polygon_inputs.py`
- `collision_polygon_recipe.py`
- `collision_polygon_output.py`
- `prepare_collision_polygon_intermediate.py`

La [prueba de contrato de CI](../../tests/python/test_collision_polygon_ci.py)
añade **31 pruebas**: una valida configuración/artefactos y treinta comprueban
los cinco módulos con seis controles por módulo. Con un global al 100 %,
exactamente 80 % pasa; 79 % de líneas, 79 % de ramas, módulo ausente,
denominadores vacíos o fila inválida fallan. Se utiliza el gate real y los
nombres extraídos del YAML; no se rebaja el umbral ni se modifica su código.

La lista exacta de diez módulos y los helpers también queda cubierta por
la [prueba de integración existente](../../tests/python/test_collision_integration.py).
Se mantienen `python-coverage.xml`, `python-coverage.json` y `pytest.xml`
con subida `always()` y 14 días de retención. Los jobs `host`, `cpp-coverage`,
`nintendo-3ds`, dependencias y ajustes generales coinciden con la base Git.

La comprobación focalizada pasa: **280 pruebas** (279 nuevas y una prueba
de contrato de CI ya existente). La ejecución completa de los comandos de
calidad del YAML se registra bajo `build/cld-intermediate-contract/cf-t7d/`.
Su ejecutor solo sustituye `python` por el de `.venv` y añade RTK. El sandbox
bloquea `/bin/ps`; se ejecuta con el permiso necesario para las pruebas
sintéticas de supervisión de procesos, sin omitirlas ni alterar su lógica.

Los ocho comandos seleccionados del job pasan: lint, formato, contratos,
suite Python completa, gate global, gate individual y comprobación de
artefactos. **8.829 pruebas principales aprobadas**, cero fallos, errores
o skips. El perfil CPI suma 522 pruebas (139 del adaptador, 104 del preparador,
248 de conformidad y 31 de CI); las 3.159 CP originales también están presentes.

| Ámbito | Líneas | Ramas |
|---|---:|---:|
| Global Python | 10.142/10.298 = 98,49 % | 3.111/3.214 = 96,80 % |
| Adaptador CPI | 259/259 | 64/64 |
| Custodia de entradas | 53/53 | 8/8 |
| Receta | 101/101 | 16/16 |
| Writer/lector | 64/64 | 8/8 |
| Preparador/CLI | 53/54 = 98,15 % | 7/8 = 87,50 % |

El arranque `__main__` se ejecuta en subprocesos, pero esa cobertura no se
agrega a la medición principal; no se excluye del denominador. Se conservan
los umbrales, exclusiones y configuración global previos.

JUnit declara 8.885 ejecuciones y contiene 8.829 nodos `testcase`. Se verificó
la diferencia mediante la prueba de iluminación: 17 casos y 56 subcasos
`unittest.subTest` aprobados, 73 declarados. Los XML originales se conservan
sin corregir contadores; el comprobante distingue las tres cifras y coteja
los contadores de cobertura XML/JSON.

Entorno local: macOS, Python 3.14.6 y versiones instaladas concordantes con
los 16 paquetes aplicables del lockfile. No se reinstalaron dependencias.
El runner configurado sigue siendo Ubuntu 24.04/Python 3.13.7; no se ejecutó
GitHub Actions remoto. Se verificaron 14 archivos previos de producción,
decoder/oráculo CP, pruebas y semillas sin cambios respecto a sus pins.

Comprobantes locales, ignorados por Git:

- `reports/local/f03-04-collision-polygons-intermediate-verification-v1.json`:
  resumen, pins, resultados y alcance.
- `build/cld-intermediate-contract/cf-t7d/quality-execution.json`: comandos
  del YAML, entorno, versiones y logs `step-00.log`–`step-07.log`.
- `build/cld-intermediate-contract/cf-t7d/quality-artifacts/`: copias verificadas
  de cobertura XML/JSON y JUnit de la corrida completa.
- `build/cld-intermediate-contract/cf-t7d/quality-validation.json` y
  `junit-subtests-check.xml`: reconciliación independiente de artefactos.

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_polygon_conformance.py tests/python/test_collision_polygon_ci.py -q
rtk proxy .venv/bin/python build/cld-intermediate-contract/cf-t7d/run_quality.py
```

La primera orden usa solo archivos versionados. La segunda es el auxiliar
local conservado que reproduce los comandos de calidad del YAML; requiere
que la consulta de procesos esté permitida para las pruebas del supervisor.

## Continuación

**CF-T7e:** publicar ambas conversiones privadas, verificar sus manifiestos e
inventarios, reconstruir con ambos lectores sin fuentes y después cotejar
los CLD completos, filas y enlaces contra sus entradas fijadas. Los conteos
233/52/0 y 519 archivos siguen siendo la evidencia de preparación en memoria
de CF-T7c hasta completar esa publicación.

Esta tarea no ejecuta PCSX2 ni la 2DS XL, no compila un nuevo visor y no
valida solver, formas de 48 bytes, listas dinámicas, daño/muerte o SH3P.
F03.04 global y G02/G03 permanecen abiertos.
