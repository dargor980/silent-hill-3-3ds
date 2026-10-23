# F03.03 — Convenciones de geometría estática verificadas

2026-10-20. **GC-T1–GC-T3 completadas**, instancia estática de
[GC01–GC06](../../schemas/geometry-conventions.md). GC-T4 y F03.03 global
siguen pendientes: pose, huesos, raíz animada, tiempos e interpolación no
se deducen de las dos formas estáticas.

Actualización 2026-10-23: [GC-T4](f03-03-character-world.md) añade el perfil
del personaje `0x0209` / `0x1449` con evidencia SA/CM y convenciones de mundo.
La situación descrita arriba corresponde al cierre estático del 2026-10-20.

## Resultado

`geometry_transform.py` separa modelo afín por columnas, cambio de base del
visor y UV de material del empaquetado, normalización y estado de render.
El modelo se valida al construirlo, conserva una copia inmutable de sus
columnas y rechaza reflexiones, singularidades, proyección, valores no finitos
y magnitudes fuera del perfil. Posiciones malformadas, resultados no finitos
y UV que no sean palabras i16 originales producen `ValueError`.

`material_inspection.py` usa estas operaciones sin cambiar orden de formas,
centrado, escala de inspección, colores, restricciones planas ni formato SGM.
No se modificaron lectores C++, renderer o binarios de consola. Las unidades
mundiales se conservan; no se ha establecido una relación con metros.

El fixture público es propio: cuatro puntos no coplanares, UV asimétricos
y una matriz con giro, cizalla, escala y traslación. Los valores esperados
están fijados independientemente de la implementación. Su volumen firmado
se multiplica por 24 al aplicar el modelo y se conserva al cambiar de base.
La prueba integrada recorre registros MAP sintéticos → decoder → modelo →
base → UV, conservando el round-trip de las palabras y atributos originales.

Siete controles incorrectos son detectados: matriz transpuesta, modelo
aplicado dos veces, base antes del modelo, reflexión de un solo eje, winding
invertido, inversión de V y eliminación del bit de control de U.
Los 51 casos nuevos incluyen esos controles y entradas inválidas/límites.

## Validación

- **519 pruebas Python aprobadas**: convenciones, material, geometría,
  sondeos MAP/render, texturas y scripts de build.
- Nuevo módulo: **35/35 líneas ejecutables y 10/10 ramas**.
  Junto con material: **89/90 líneas y 33/34 ramas**, 98,39 % combinado;
  pasa el umbral independiente de líneas/ramas.
- Ruff, formato y comprobaciones de repositorio: aprobados.
- El job `quality` existente de `.github/workflows/ci.yml` descubre el nuevo
  archivo bajo `tests/python`; usa solo el fixture propio. No se afirma una
  ejecución remota de CI ni una nueva prueba física.

```sh
rtk proxy .venv/bin/python -m pytest \
  tests/python/test_geometry_conventions.py tests/python/test_material_inspection.py \
  tests/python/test_geometry_inspection.py tests/python/test_map_geometry.py \
  tests/python/test_map_probe.py tests/python/test_map_render_probe.py \
  tests/python/test_texture_decode.py tests/python/test_texture_inspection.py \
  tests/python/test_texture_probe.py tests/python/test_render_build_script.py \
  --cov=tools.pipeline.geometry_transform --cov=tools.pipeline.material_inspection \
  --cov-branch --cov-report=json:build/geometry-conventions/coverage.json \
  --cov-report=term-missing --junitxml=build/geometry-conventions/regression.xml -q
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/geometry-conventions/coverage.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

## Regresión de la entrega física

Se llamó `prepare_files` en memoria para las extracciones A/B usando los
hashes fijados en el manifiesto de `f03-02-3ds-material-v1`, la referencia
MR-T4d y el directorio compilado que produjo `764be66e7762`.

Los seis archivos, incluido el ZIP, coinciden byte a byte con la entrega
anterior; tamaños y SHA-256 coinciden con su manifiesto. Los informes de
preparación también coinciden entre copias y con los campos de ese manifiesto.
No se sobrescribieron las entregas privadas ni la SD.

Informe local: `reports/local/f03-03-static-geometry-v1.json`, SHA-256
`a246a5a3dd03ba346ef518353f192d01bdcf55b0ac985d95958ae16b941e69fa`.
Conserva hashes de los cuatro archivos de código/fixture/pruebas y de los
seis artefactos comparados. La evidencia física corresponde a la
[confirmación del usuario para MI-T4](../compatibility/material-inspection.md);
la regresión actual acredita que el cambio host conserva esa entrega.

Siguiente dependencia: identificar y decodificar un recurso de esqueleto y
animación en F03.02 antes de fijar GC-T4; no se presume pose ni frecuencia
de animación a partir del framerate del juego.
