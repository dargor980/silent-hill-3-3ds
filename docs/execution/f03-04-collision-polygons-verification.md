# F03.04 / CF-T5b — Oráculo poligonal y batería ampliada

2026-10-23. **CF-T5b completada.** Se cubre la tabla de aceptación de
[CP01–CP14](../../schemas/ps2-cld-polygons-v1.md), ampliando las pruebas de
[CF-T5a](f03-04-collision-polygons-decoder.md). El decoder conserva exactamente
sus bytes anteriores; también permanecen intactos los 50 vectores y las dos
bases de CF-T4. Todo el trabajo usa datos sintéticos públicos.

## Separación y comprobación independiente

- [Oráculo](../../tests/cld_polygon_wire_oracle.py): usa únicamente `math`.
  Lee enteros mediante slices y calcula f32 con signo, exponente, fracción y
  `ldexp`; no utiliza `struct` ni importa el decoder, sus constantes o el
  constructor. Deriva una vista completa o un código propio de rechazo.
- [Constructor](../../tests/cld_polygon_fixtures.py): usa únicamente `struct`;
  produce geometría propia, listas y alias. No genera vistas esperadas ni
  códigos de rechazo, ni importa los lectores.
- [Pruebas fijas](../../tests/python/test_cld_polygons.py): ambos lectores
  deben coincidir con las expectativas completas fijadas antes del decoder.
- [Batería ampliada](../../tests/python/test_cld_polygon_conformance.py):
  expectativas explícitas para rechazos, anclas literales del constructor,
  contraste de vistas y comprobaciones de comportamiento/propiedad.

El oráculo compara claves, tipos, enteros y valores f32 exactos, incluido
el signo del cero. Sus comprobaciones usan condiciones explícitas y siguen
activas con `-O`. Los tests de dependencias comprueban la separación de los
dos lectores y el constructor. Esto reduce errores compartidos; no se toma
la coincidencia entre lectores como prueba de física o procedencia.

## Resultado y trazabilidad

**3.159 pruebas del perfil aprobadas, sin fallos ni skips.** Incluyen las
69 iniciales y 3.090 adicionales. El decoder mantiene **99/99 líneas y
54/54 ramas cubiertas (100 %)**, con gate local aprobado. La regresión de
registros de colisión IR-T7 pasa con **257 pruebas**. Ruff, formato,
validación del repositorio y comprobación de whitespace pasan.

| Familia | Evidencia de CF-T5b | Contrato |
|---|---|---|
| Valores y referencias | Anclas literales, grupos distintos, celda 15, duplicados, alias entre grupos y cola compartida; ambas vistas contra las semillas CF-T4. | CP04–CP09 |
| f32 | 384 rechazos de NaN/+Inf/−Inf en todos los 16 componentes, dos variantes y cuatro grupos; 1.024 casos finitos con palabras exactas. Orígenes probados por separado, incluido NaN señalizante. | CP06 |
| Opacidad/geometría | Extremos de cabeceras opacas por grupo, selección 0/no nula, degenerados sin referencias; cuarto vector, W y no planaridad también cubiertos por los vectores fijos. | CP04–CP06/CP09 |
| Terminación de formas | Corrupción individual de los 368 bytes de los cinco terminadores; presencia/variante inválidas y registros cero interiores sin recorte silencioso. | CP02/CP04 |
| Buffer y grupos | Mínimo 752 y máximo 65.536 válidos; mínimo−1, máximo+1, cabeceras/truncamientos, strides, alineación, overflow, huecos, superposición, orden y bytes finales. | CP01/CP02 |
| Grupo 4 | Payloads de 48 bytes activos rechazados sin interpretarlos; las 16 listas del grupo vacío rechazan índice cero. | CP03/CP08 |
| Listas | 640 punteros inválidos distribuidos entre las 80 celdas, 80 sentinels al final de región, 240 índices inválidos y 64 listas sin terminador aisladas; un sentinel en formas no rescata una lista. | CP07/CP08/CP12 |
| Presupuestos | 512/513 polígonos en cada grupo y 768/769 con distintas distribuciones; 512/513 referencias por lista y 4.096/4.097 totales, con listas distintas y alias entre grupos. | CP10 |
| Estado/propiedad | Identidad única de cada colección mutable, separación entre invocaciones, vaciado de todas las colecciones y llamadas inválidas intercaladas; entrada y resultados posteriores conservados. | CP11/CP13 |
| Precedencia | 18 escenarios con fallos simultáneos; valida orden entre etapas y recorridos, incluido índice antes del presupuesto y terminador tardío antes de una forma temprana. | CP12 |
| Metamórficas | Traslado de datos con offsets ajustados, mutación de padding sin cambiar vista y reordenamiento de referencias con/sin alias explícitos. | CP07/CP11 |
| Sensibilidad | Diez vistas corruptas rechazadas y un lector con conteo erróneo por offset único detectado. Un control separado muestra que la comparación de valores sola no detecta colecciones compartidas. | CP04/CP08/CP10/CP11/CP14 |

Los diez fallos de vista son: eliminar duplicados, tratar `word_04` como
conteo, perder el cuarto vector, aplicar origen, eliminar una forma sin
referencias, perder el signo del cero, cambiar tipo, añadir/omitir claves
y alterar una palabra de coordenada. El control de presupuesto desactiva
temporalmente el conteo expandido en un test: 4.097 referencias parecen 513
si se cuentan offsets únicos; el oráculo rechaza esa aceptación falsa.
La modificación temporal se restaura al terminar el caso.

### Python normal y optimizado

Cada proceso ejecuta **2.742 buffers** más **nueve tipos inválidos** por
lector. Se ejecutan tanto el decoder como el oráculo en modo normal y `-O`:
11.004 observaciones en estos dos casos de pytest. Es un conteo de
observaciones internas, **no 11.004 tests adicionales**.

Los errores se comparan por código y mensaje. Las vistas se contrastan
mediante SHA-256 de JSON canónico contra la vista independiente; tipos
numéricos, signo del cero, claves, orden de listas y palabras se conservan
en esa codificación. El proceso padre mantiene activas sus aserciones.
También se comprueba que `oracle.identical(-0.0, 0.0)` rechace con `-O`.
La ejecución optimizada de las dos bases y los 50 vectores fijos de CF-T5a
sigue formando parte de la batería.

## Reproducción y evidencia

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_cld_polygons.py tests/python/test_cld_polygon_conformance.py -q --cov=tools.pipeline.decoders.ps2_cld_polygons --cov-branch --cov-report=json:build/cld-polygons/cf-t5b-coverage.json --cov-report=term-missing --junitxml=build/cld-polygons/cf-t5b-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/cld-polygons/cf-t5b-coverage.json --files tools/pipeline/decoders/ps2_cld_polygons.py
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_registry.py tests/python/test_collision_intermediate.py tests/python/test_collision_integration.py -q --junitxml=build/cld-polygons/cf-t5b-regression.xml
rtk proxy .venv/bin/python -m ruff check tools/pipeline/decoders/ps2_cld_polygons.py tests/cld_polygon_wire_oracle.py tests/cld_polygon_fixtures.py tests/python/test_cld_polygons.py tests/python/test_cld_polygon_conformance.py
rtk proxy .venv/bin/python -m ruff format --check tools/pipeline/decoders/ps2_cld_polygons.py tests/cld_polygon_wire_oracle.py tests/cld_polygon_fixtures.py tests/python/test_cld_polygons.py tests/python/test_cld_polygon_conformance.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

JUnit/cobertura se conservan bajo `build/cld-polygons/`. El comprobante local
`reports/local/f03-04-collision-polygons-verification-v1.json` fija sus hashes,
los de los archivos de implementación/prueba/contrato y los conteos medidos.
La identidad del decoder y el fixture se coteja contra el comprobante CF-T5a;
el fixture mantiene SHA-256
`f9218e872e29383dca73b03b895d746c991ee9c7e282d01de82a3863c1eb6b42`.

## Siguiente tarea y límites

**CF-T5c:** incorporar los dos helpers de tests al lint/formato y el decoder
al gate individual en CI; comprobar la regresión y los artefactos del pipeline.
El descubrimiento actual ya incluye los nuevos tests, pero no se ha ejecutado
CI remoto ni modificado su configuración en CF-T5b.

CF-T6 conserva el cotejo privado A/B como tarea separada; CF-T7 definirá e
integrará la vista de formas al intermedio. No se ha leído el corpus privado,
ejecutado PCSX2 ni compilado/probado la consola en esta tarea. Permanecen
abiertas la variante de 48 bytes, las listas dinámicas superpuestas y la
respuesta física; no se cierra F03.04 global, G02/G03 ni daño/muerte.
