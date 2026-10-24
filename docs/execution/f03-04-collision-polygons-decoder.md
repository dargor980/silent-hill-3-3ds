# F03.04 / CF-T5a — Decoder poligonal puro

2026-10-23. **CF-T5a completada.** Se implementa el
[decoder](../../tools/pipeline/decoders/ps2_cld_polygons.py) conforme a
[CP01–CP15](../../schemas/ps2-cld-polygons-v1.md), con
[pruebas públicas](../../tests/python/test_cld_polygons.py) sobre los vectores
fijados en CF-T4. La batería ampliada CF-T5b, la integración del gate en CI
CF-T5c y el cotejo privado CF-T6 siguen pendientes.

## Implementación y responsabilidades

`decode_polygons(raw: bytes) -> dict` acepta exclusivamente `bytes`, limita
el buffer a 752–65.536 bytes y produce la vista exacta del contrato. Usa solo
`math` y `struct`, sin I/O, fuentes privadas, SDK, emulador o estado mutable
global. `CollisionPolygonError(ValueError)` conserva el código en `code` y
como mensaje, sin contenido de entrada ni resultados parciales.

Se separan validación del layout/terminadores, lectura de formas y resolución
de listas. Se comprueban todos los grupos antes de leer formas, y todas las
formas antes de recorrer listas. Las 17 categorías de error respetan la
precedencia del contrato; los límites se comprueban antes de expandir formas
o añadir referencias. Los alias cuentan por celda y reciben listas propias.

Se conservan cabeceras opacas, selección, vectores completos, palabras f32,
cero negativo, subnormales, duplicados y formas sin referencias. No se aplica
origen ni transformación. El grupo 4 activo rechaza todo el recurso como
variante no soportada; su payload no se interpreta. Los bytes originales
siguen bajo responsabilidad del llamador para conservar el padding opaco.

## Validación realizada

**69 pruebas aprobadas**, sin skips:

- Los 50 casos de CF-T4: diez vistas aceptadas y cuarenta códigos de rechazo.
- Dos fixtures base con comparación de cada clave, tipo, entero y f32 exacto;
  se compara también el signo del cero, sin tolerancia geométrica.
- Identidad del inventario y sus hashes. El fixture conserva el SHA-256
  `f9218e872e29383dca73b03b895d746c991ee9c7e282d01de82a3863c1eb6b42`.
- Nueve tipos inválidos, incluida una subclase de `bytes` y un objeto que
  falla si se intenta coerción o consultar su longitud antes del tipo.
- Fronteras 512/513 polígonos por grupo y 768/769 totales, con grupos/listas
  válidos antes del presupuesto; rechazo de 65.537 bytes antes de la cabecera.
- Aislamiento inicial entre listas compartidas, invocaciones y entrada;
  una llamada inválida intercalada no contamina las siguientes.
- Ejecución de las dos bases y los 50 casos con Python `-O` en un proceso
  hijo; las comparaciones permanecen activas en el proceso padre.

Las expectativas JSON preceden al decoder y no se generan con él. Estas
pruebas **no sustituyen el oráculo público ni los barridos, metamórficas y
controles de sensibilidad de CF-T5b**. La cobertura alcanzada no cierra esas
obligaciones funcionales.

Cobertura del módulo: **99/99 líneas ejecutables y 54/54 ramas (100 %)**.
El gate local independiente de líneas/ramas pasa. Ruff y formato de los
dos archivos nuevos pasan. La regresión del perfil de registros IR-T7 pasa
con **257 pruebas**; no se ha modificado ese perfil.

Comandos ejecutados:

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_cld_polygons.py --cov=tools.pipeline.decoders.ps2_cld_polygons --cov-branch --cov-report=json:build/cld-polygons/cf-t5a-coverage.json --cov-report=term-missing --junitxml=build/cld-polygons/cf-t5a-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/cld-polygons/cf-t5a-coverage.json --files tools/pipeline/decoders/ps2_cld_polygons.py
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_registry.py tests/python/test_collision_intermediate.py tests/python/test_collision_integration.py --junitxml=build/cld-polygons/cf-t5a-regression.xml
rtk proxy .venv/bin/python -m ruff check tools/pipeline/decoders/ps2_cld_polygons.py tests/python/test_cld_polygons.py
rtk proxy .venv/bin/python -m ruff format --check tools/pipeline/decoders/ps2_cld_polygons.py tests/python/test_cld_polygons.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

JUnit/cobertura se conservan bajo `build/cld-polygons/`. El comprobante local
`reports/local/f03-04-collision-polygons-decoder-v1.json` fija hashes del
decoder, tests y fixture, conteos JUnit y cobertura. Los nuevos tests son
descubiertos por el job Python existente; el gate individual adicional se
incorporará en CF-T5c, junto con el oráculo de CF-T5b. No se afirma haber
ejecutado CI remoto, el corpus privado, PCSX2 ni un build/prueba de consola.

## Siguiente tarea

**CF-T5b:** completar el oráculo independiente y la batería contractual:
barridos de f32 y terminadores, grupos y fronteras restantes, alias entre
grupos, precedencia múltiple, aislamiento completo, metamórficas y sensibilidad.
Ampliar también los controles bajo `-O` más allá de los vectores fijos.

Después: CF-T5c (gate CI), CF-T6 (fuentes A/B) y CF-T7 (contrato e integración
de formas al intermedio). Permanecen abiertas la variante de 48 bytes, las
listas dinámicas superpuestas y la respuesta física; no se cierra F03.04
global, G02/G03 ni las transiciones de daño/muerte.
