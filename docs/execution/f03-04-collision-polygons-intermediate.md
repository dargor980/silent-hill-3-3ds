# F03.04 / CF-T7b — Adaptador puro de formas de colisión

2026-10-23. **CF-T7b completada.** Implementado el adaptador
[collision_polygon_intermediate](../../tools/pipeline/collision_polygon_intermediate.py)
conforme a [CPI01–CPI14](../../schemas/collision-polygons-intermediate-v1.md),
con [139 pruebas propias](../../tests/python/test_collision_polygon_intermediate.py).
Continúa el [contrato y ejemplos CF-T7a](f03-04-collision-polygons-intermediate-contract.md).

## Comportamiento implementado

Las tres APIs reciben únicamente metadatos y buffers en memoria:

- `make_collision_polygons`: coteja las identidades suministradas de los
  buffers antes de llamar al decoder, conserva las filas completas y genera
  todas las clasificaciones y vistas.
- `export_collision_polygons`: valida raíz/adjuntos y reconstruye todos los
  archivos lógicos, regenerando cada vista aceptada desde el CLD.
- `verify_collision_polygon_bundle`: verifica además el manifiesto de
  transporte, sus hashes, inventario y recuentos antes de devolver los archivos.

El manifiesto y su enlace auxiliar no se incluyen en el dict de archivos
lógicos devuelto. La API pura rechaza `.manifest.pending.json` como extra;
el tratamiento del auxiliar en disco corresponde al preparador CF-T7c.

Se conserva el buffer completo de cada recurso, incluidos padding, datos
opacos y fuentes no soportadas o rechazadas. Las vistas se cotejan por JSON
canónico, distinguiendo bool/int/float, cero negativo, palabras f32 y todas
las referencias. Un recurso no aceptado conserva su primer código CP y no
tiene vista parcial. Dos IDs con los mismos bytes permanecen separados.

`CollisionPolygonIntermediateError` emite los nueve códigos CPI definidos,
sin rutas ni datos originales en el mensaje. Las etapas se verifican para
todo el paquete: formato, esquema, inventario, hashes, clasificación, vistas
y procedencia. Para que un error de vista de un recurso anterior no oculte
una clasificación inválida posterior, las aceptaciones se procesan en dos
pasadas acotadas. Solo se mantiene un árbol de vista a la vez.

El módulo reutiliza el decoder CP, codec JSON y comprobadores de inventario;
no añade I/O, writer, acceso a RAM, red, reloj o código del visor. Devuelve
dicts independientes y puede compartir buffers `bytes`, que son inmutables.
Las entradas y sus extensiones desconocidas permanecen intactas.

## Verificación realizada

Los **24 ejemplos materializados anteriores a la implementación** conservan
su SHA-256 `7101765a39b0b3ccee3930e0f48730af9d6ed8444b3bbd9efdfc131f0ba58446`.
Pasan tanto por exportación como por verificación del manifiesto: tres paquetes
coherentes reconstruidos y 21 alteraciones rechazadas con el código esperado.
El constructor reproduce exactamente los archivos lógicos de los tres casos
coherentes, incluidos siete recursos con las tres clasificaciones.

Los controles de padding/metadatos coherentemente modificados mantienen la
distinción del contrato: reconstruir un paquete no autentica sus fuentes
externas. Los tests comparan por separado buffers y catálogo originales.
Las vistas aceptadas también se contrastan con el oráculo CP independiente.

La batería adicional comprueba:

- 1/285 recursos admitidos y 0/286 rechazados; fuentes de 1, 752 y 65.536
  bytes conservadas, y 0/65.537 fuera del transporte. Un byte se conserva
  como recurso rechazado por CP, no como geometría aceptada.
- Raíz canónica exactamente de 1 MiB y exceso; frontera agregada de 40 MiB;
  vistas/manifiestos en su límite físico y +1. Llegar al límite físico no
  exime de validar JSON e inventario.
- Tipos exactos, bytes mutables, coerción, duplicados JSON, no finitos,
  UTF-8/surrogates, profundidad, rutas en campos desconocidos, códigos CP
  inexistentes y discrepancias de catálogo/origen.
- Pins y límites de enlaces históricos, 30 enlaces, duplicados globales,
  orden y prohibición de enlaces en recursos no aceptados. Los datos son
  propios incluso cuando usan la identidad europea para probar ese esquema;
  no se leen capturas privadas ni se verifican hechos históricos nuevos.
- Precedencia entre recursos, rechazo de inventarios adicionales, hashes
  de raíz, recuentos de manifiesto, aislamiento de resultados y entradas.

Dos subprocesos, normal y `-O`, ejecutan los 24 ejemplos. Para los casos
coherentes se ejercitan las tres APIs y se comparan bytes y hashes. Después
de importar módulos y cargar fixtures, un audit hook bloquea aperturas,
red y creación de procesos durante las llamadas; un intento de apertura
confirma que está activo. Ambos modos producen los mismos resultados.

Resultado local: **139 pruebas aprobadas**, cobertura del módulo
**259/259 líneas y 64/64 ramas = 100 %**. Pasa el gate individual de ≥80 %
de líneas y ramas aplicado localmente. No significa cobertura exhaustiva
de cada combinación de validaciones o de la futura publicación.

Regresión: **3.416 pruebas aprobadas**, correspondientes a 3.159 del decoder
poligonal y 257 del perfil de registros IR-T7. No se alteraron el decoder,
los vectores/oráculo CP ni el perfil de registros para aceptar los ejemplos.
El primer intento encontró un error de la prueba de aislamiento al serializar
buffers como JSON; se corrigió comparando sus valores/tipos, sin cambiar
expectativas de los vectores ni relajar el adaptador.

## Reproducción y alcance pendiente

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_polygon_intermediate.py -q --cov=tools.pipeline.collision_polygon_intermediate --cov-report=json:build/cld-intermediate-contract/cf-t7b-coverage.json --junitxml=build/cld-intermediate-contract/cf-t7b-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/cld-intermediate-contract/cf-t7b-coverage.json --files tools/pipeline/collision_polygon_intermediate.py
rtk proxy .venv/bin/python -m pytest tests/python/test_cld_polygons.py tests/python/test_cld_polygon_conformance.py tests/python/test_collision_registry.py tests/python/test_collision_intermediate.py tests/python/test_collision_integration.py -q --junitxml=build/cld-intermediate-contract/cf-t7b-regression.xml
```

Comprobante de metadatos:
`reports/local/f03-04-collision-polygons-intermediate-adapter-v1.json`.
Fija fuentes, tests, ejemplos, JUnit y cobertura. Ruff/formato, políticas de
repositorio, enlaces documentales y `git diff --check` pasan.
El descubrimiento de pytest y lint existentes incluyen los archivos nuevos;
el gate permanente específico de CI y el oráculo completo de paquetes
corresponden a CF-T7d. No se ejecutó CI remoto ni la suite global completa.

**Siguiente: CF-T7c**, preparar entradas privadas fijadas y publicar con el
writer exclusivo, verificando reconstrucción antes del manifiesto final.
La comprobación de los documentos históricos externos, los fallos de I/O,
concurrencia y las publicaciones A/B siguen pendientes. Las capacidades
permanecen vacías; no hay build nuevo, solver ni validación física añadida.
