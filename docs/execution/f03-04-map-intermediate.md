# F03.04 / IR-T6 — Geometría estática y material de mapa

2026-10-23. **IR-T6a–d completadas** para `ps2-map-glass-v1`.
[Contrato EARS IR13–IR18 y tareas](../../schemas/map-intermediate-v1.md).
Alcance: las dos formas ya verificadas de `hp34.map` y su textura externa,
paleta 0. F03.04 global y G02/G03 permanecen abiertos.

## Resultado y conservación

El intermedio conserva los documentos de geometría, referencia de material,
informe GS e informe de píxeles, junto con los manifiestos de extracción.
Mantiene los **56 vértices originales, 32 triángulos**, palabras i16,
atributos opacos, omisiones de strip, matriz, colores y orden de dibujo.
Se conservan tipos JSON, campos desconocidos y estados históricos; no se
conserva el espaciado de los JSON de origen.

Incluye **14 adjuntos originales**: OBJ, índices, cuatro paletas, cuatro
RGBA y cuatro PNG. Los PNG no se recodifican. Las paletas 1–3 de esta fuente
contienen `0xCC`, incluido alpha 204; se conservan sin atribuirles uso en
dibujo. El material verificado utiliza exclusivamente la paleta 0.

El JSON mide **32.321 bytes** y las 17 salidas suman **1.487.880 bytes**,
sin contar el manifiesto. La reconstrucción usa solo ese JSON y los catorce
adjuntos; no lee ISO, archivos de extracción ni capturas PCSX2. Regenera
**SGM/STX idénticos** a los de la entrega de material `764be66e7762`, aceptada
por el usuario en 2DS XL con ambos paneles transparentes y controles.
La igualdad se refiere a los datos, no constituye otra ejecución física.

## Responsabilidades y validación

`map_intermediate` valida las relaciones y aplica los validadores y encoders
existentes. `intermediate_assets` comprueba inventarios, tamaños y hashes.
`prepare_map_intermediate` coordina las cinco entradas fijadas y las lecturas
acotadas; el writer privado publica en una carpeta nueva, con permisos
restrictivos y manifiesto posterior a las escrituras verificadas. No cambia
el código del visor, los encoders ni sus archivos de entrada originales.

Se verifican inventarios exactos, identidades de MAP/textura, enlaces de
referencia, las dos capturas y el hash de la matriz. Los informes deben
coincidir en estados de transparencia/profundidad, conteos por forma, frames
y orden de triángulos. El OBJ debe reconstruirse desde las palabras de
geometría. Los cuatro RGBA y sus estadísticas deben coincidir con índices y
paletas; también se comprueban hashes de previsualización normalizada.

El contrato separa UV del OBJ histórico (`1-V`) de los del material (sin
inversión), matriz por columnas aplicada una vez de base/escala de inspección,
y alpha PS2 de PNG y STX. STX usa `(A×255+64)//128`; PNG histórico usa
`min(255,2*A)`. Se conserva la receta de RGB capturado con fog, filtrado
lineal/clamp y transparencia sin escritura de profundidad.

La importación comprueba los hashes de los bytes fuente; los hashes históricos
se conservan como procedencia. El nuevo manifiesto protege el JSON recodificado
y todos los adjuntos. La regeneración no vuelve a ejecutar los oráculos GS o
de píxeles: comprueba la coherencia de los informes fijados. Se mantiene su
procedencia de replay diagnóstico con cámara intervenida; no se transforma
esa evidencia en una captura de juego normal.

## Pruebas locales y CI

**504 tests aprobados:** 80 nuevos y 424 regresiones de geometría, convenciones,
material, textura y los dos perfiles intermedios de personaje. Los tres
módulos nuevos alcanzan **98,65 % de líneas**, **97,06 % de ramas** y
**98,15 % combinada**. Gate de líneas/ramas ≥80 % aprobado.

Los fixtures propios comprueban dos formas con colores distintos, orden de
dibujo, coordenadas conocidas, palabras UV con bit de control, alpha, paletas
no usadas, metadatos desconocidos y cero negativo. Se prueba la reconstrucción
tras retirar únicamente las fuentes sintéticas y la publicación exclusiva.
Los negativos cubren tipos booleano/número, versiones, topología, palabras,
capturas/modelo, registros GS, fuentes mezcladas, inventarios, tamaños,
hashes, symlinks y JSON duplicado. Las fuentes privadas reales se mantienen.

```sh
.venv/bin/python -m pytest \
  tests/python/test_map_intermediate.py \
  tests/python/test_map_geometry.py \
  tests/python/test_geometry_inspection.py \
  tests/python/test_geometry_conventions.py \
  tests/python/test_material_inspection.py \
  tests/python/test_texture_decode.py \
  tests/python/test_texture_inspection.py \
  tests/python/test_character_intermediate.py \
  tests/python/test_character_render_intermediate.py \
  --cov=tools.pipeline.map_intermediate \
  --cov=tools.pipeline.prepare_map_intermediate \
  --cov=tools.pipeline.intermediate_assets \
  --cov-report=json:build/map-intermediate/coverage.json \
  --cov-report=term-missing --junitxml=build/map-intermediate/pytest.xml -q
.venv/bin/python -m tools.qa.coverage_gate build/map-intermediate/coverage.json
```

El job Python existente descubre las pruebas sintéticas y aplica el gate sin
datos privados. Ruff y formato aprueban el alcance de CI de 241 archivos.
No se ejecutó CI remoto ni compilación ARM: esta tarea modifica la conversión
y verifica la igualdad de los datos, sin cambiar ejecutables.

## Conversión privada y comprobante

Configuraciones locales `build/map-intermediate/inputs-{a,b}.json`.
Cada variante usa su extracción independiente de geometría y textura, con
los mismos informes y referencia históricos. Hashes de entrada:

| Fuente | SHA-256 |
|---|---|
| Manifiesto geometría A/B | `6714a2c7f96c4c168cdd0fe02583041f42876f3f84fab351cb35bf9248053318` |
| Manifiesto textura A/B | `9d7b684ca600b34ea8862c057c1b1e2f7d85e8f026dd4e6d6667a573eeb736d1` |
| Referencia MR-T4d | `e4cdb9f7c55d17409d5b1da8b48f706dbfe51440ad0a69716351e305e41c1e37` |
| Informe GS | `aa7c2bdde2d0fed8b3bcd5743f57184ea8ee68d55ab578f8a45aebc07d696661` |
| Informe píxeles | `befdcbd7fa06305310f2ba76187e6d8315556666b8d8a3d417821a16e5eed285` |

```sh
.venv/bin/python -m tools.pipeline.prepare_map_intermediate \
  --inputs /Users/germancontreras/silent-hill-3-3ds/build/map-intermediate/inputs-a.json \
  --private-root /Users/germancontreras/sh3-private-data \
  --run-id f03-04-map-intermediate-a-v1
```

Para B cambian configuración y run-id; repetir exige un run-id nuevo.
Salidas: `/Users/germancontreras/sh3-private-data/f03-04-map-intermediate-{a,b}-v1/`.
Los **17 archivos y manifiestos A/B son idénticos** tras releerlos. El auditor
compara todos los árboles con JSON estándar, todos los adjuntos con sus
originales y reconstruye desde cada intermedio guardado. Comprueba primero
el manifiesto fijado de la entrega aceptada y después sus SGM/STX.

| Salida | Bytes | SHA-256 |
|---|---:|---|
| intermediate.json | 32.321 | `39d5a5a37e46aa485fd40e7631936ae3e40d86f607163c1b97dd963fbe17f263` |
| geometry.sgm | 3.096 | `ae67b60d1ff8349fc385d1760b42e0edc889423456aa599408751b0ec858d5f6` |
| texture.stx | 262.168 | `55c90e160f02701a9c246c617d8d15e68284f8eaab9b95d05b9736725192b579` |
| manifest.json | — | `2e7a06a7ae99d495f4e2c15b50add704d13e715d89fb78f3ed390c489eb86f6b` |

Entrega aceptada: `f03-02-3ds-material-v1`, build `764be66e7762`, manifiesto
`a16da2ef6965bf81868c3475eb27994fab4146a949b68597627888d4139a5b30`.
Auditor local `build/map-intermediate/audit.py`, SHA-256
`4353d93b81a7f3c7604bf8f198cc0282f903a869b39282863b9158df83a7aff2`.
Comprobante privado `f03-04-map-intermediate-check-v1/roundtrip.json`, SHA-256
`bbfb77fda5bf8651d16b486462b673ead4442bb1223e233d647ef5c878967248`.
Incluye hashes de fuentes, implementación, pruebas, contrato y salidas.

## Límites y continuación

Este perfil cubre las dos formas verificadas y su receta plana de inspección;
no generaliza materiales de todo el mapa, unidades métricas ni equivalencia
numérica VU/GS/PICA. Conserva lo decodificado, sin reconstruir el MAP original
completo. No crea una escena jugable, un paquete SH3P ni una entrega nueva
para la SD. La validación de transparencia/controles continúa siendo la
[aceptación MI-T4](f03-02-material-inspection.md).

Quedan los perfiles de colisión, cámara y audio de F03.04.
[IR-T7a/b](f03-04-collision-inventory.md) ya inventarió la evidencia y definió
el contrato de registros de colisión, separando datos opacos de semánticas
verificadas. [IR-T7c](f03-04-collision-registry.md) implementa el decoder puro
y sus fixtures; sigue IR-T7d, adaptación y preparación intermedias. SH3P
mantiene su tarea F03.05 independiente.
