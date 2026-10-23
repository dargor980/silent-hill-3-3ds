# F03.04 / IR-T5 — Materiales, texturas, iluminación y colocaciones

2026-10-23. **IR-T5a–d completadas** para `ps2-character-0209-render-v1`.
[Contrato EARS IR07–IR12](../../schemas/character-render-intermediate-v1.md).
Compone el [intermedio inicial](f03-04-character-intermediate.md) sin cambiarlo.
F03.04 global y G02/G03 permanecen abiertos.

## Resultado

El intermedio incorpora los documentos completos de materiales CT, estados
GS observados, referencias CT/LI/GC, preset de iluminación, tres matrices de
colocación y procedencias. Conserva **21 archivos binarios originales**:
tres imágenes de índices, doce paletas, tres RGBA y tres PNG. No recodifica
los PNG ni normaliza el alpha de los RGBA. Conserva campos desconocidos y
estados históricos de los manifiestos. El JSON mide **401.879 bytes**; los
27 archivos exportados suman **8.092.736 bytes**, sin contar el manifiesto.

Regenera **SAN, SCM, SCT, SCL y SCW idénticos** a los datos de los visores
entregados. La reconstrucción recibe únicamente el JSON y sus 21 archivos
adjuntos; no necesita directorios de extracción, ISO ni estados PCSX2.
El JSON aislado no contiene los texeles.

Las variantes siguen separadas: SCL describe el preset de una captura,
recalculado por pose; SCW describe tres colocaciones fijas con luz neutra.
No se demuestra que ese preset ilumine correctamente las tres instancias
combinadas ni se implementan selección de luces, trayectoria o IA. El
material mantiene ATE=ABE=0: los texeles alpha cero no implican descarte ni
mezcla. Las paletas 1..3 se conservan sin atribuirles uso en dibujo.

## Responsabilidades y entradas

`character_render_intermediate` valida relaciones y reconstruye mediante los
encoders existentes; reutiliza el validador puro de estados GS y la conversión
de índices/paletas. `prepare_character_render_intermediate` coordina siete
entradas fijadas, lecturas acotadas y extracción GC. El writer privado exige
inventario exacto y directorio nuevo; publica el manifiesto tras comprobar
las escrituras. El renderizador C++ y los visores no cambian.

La importación comprueba MDL/ANM comunes, enlaces CT/LI, ventanas de código
y recursos residentes de GC. Guarda las matrices extraídas y la referencia
completa, no la RAM ni el estado original. La lectura del intermedio vuelve
a validar dependencias, tipos, límites, registros GS sin alias, inventario,
hashes/tamaños, material y matrices. Índices y paleta 0 deben reproducir
exactamente cada RGBA; el hash de la previsualización con alpha normalizado
debe coincidir con los metadatos CT.

## Pruebas locales y CI

**231 tests aprobados**: 59 nuevos y 172 regresiones del intermedio base,
materiales, luces y colocaciones. Cobertura de los dos módulos nuevos:
**98,92 % de líneas**, **97,30 % de ramas**, **98,46 % combinada**; gate ≥80 %
aprobado. El adaptador puro alcanza 100 % de líneas/ramas.

Se verifican bytes conocidos de SCT/SCW, conservación de blobs/desconocidos,
cero negativo, reconstrucción después de retirar fuentes sintéticas, CLI y
rechazo de sobrescritura. Los negativos incluyen identidades mezcladas,
alpha GS incompatible, registros con alias, tipos incorrectos, referencias
incoherentes, inventarios duplicados, tamaños/hashes erróneos, paletas
incompatibles, symlinks y matrices inválidas. Las entradas privadas reales
se conservaron intactas.

```sh
.venv/bin/python -m pytest \
  tests/python/test_character_render_intermediate.py \
  tests/python/test_character_intermediate.py \
  tests/python/test_character_material_inspection.py \
  tests/python/test_character_lighting_inspection.py \
  tests/python/test_character_world_inspection.py \
  --cov=tools.pipeline.character_render_intermediate \
  --cov=tools.pipeline.prepare_character_render_intermediate \
  --cov-report=json:build/character-render-intermediate/coverage.json \
  --cov-report=term-missing \
  --junitxml=build/character-render-intermediate/pytest.xml -q
.venv/bin/python -m tools.qa.coverage_gate build/character-render-intermediate/coverage.json
```

El job Python existente descubre estos tests sintéticos y aplica cobertura;
no necesita datos privados ni cambios de configuración. Ruff y formato
aprueban su alcance de 237 archivos. No se ejecutó CI remoto ni una nueva
compilación ARM: se compararon datos exportados sin cambiar ejecutables.

## Conversión privada y comprobante

Configuración local: `build/character-render-intermediate/inputs-{a,b}.json`,
según el contrato. Las conversiones usan extracciones A/B de materiales v2 e
intermedios base A/B, con las mismas capturas históricas verificadas CT/LI/GC.

```sh
.venv/bin/python -m tools.pipeline.prepare_character_render_intermediate \
  --inputs /Users/germancontreras/silent-hill-3-3ds/build/character-render-intermediate/inputs-a.json \
  --private-root /Users/germancontreras/sh3-private-data \
  --run-id f03-04-character-render-intermediate-a-v1
```

Para B se cambian configuración y run-id. Repetir exige run-id nuevo.
Salidas: `/Users/germancontreras/sh3-private-data/f03-04-character-render-intermediate-{a,b}-v1/`.
Los 27 archivos y manifiestos A/B son idénticos tras releerlos. El auditor
compara todos los árboles de entrada con JSON estándar, todos los blobs con
sus originales y tres matrices mediante una lectura ZIP/struct independiente
del estado fijado. Después reconstruye desde cada intermedio guardado.

| Dato exportado | Bytes | SHA-256 |
|---|---:|---|
| intermediate.json | 401.879 | `422c32d211cdd8cfbd98fac4233b65dc3957751f64d3d408a9d97bf09551e77c` |
| animation.san | 1.248 | `8adbe5e59f05923c65d0813e2acfc6d88c9364db1d7e18641bdec27f6ac89381` |
| character.scm | 47.670 | `3ccf6bbbce726ccedd0b481cd7667ebe95213acc1a2f1dcdf3b27c5a2f792479` |
| character.sct | 3.145.796 | `9b1ab590c10a8ce2de0b0fa333dc9b7339a7ab64d5650e543c426c2e29932bf3` |
| character.scl | 872 | `fb22a0084b06cf92346197545966eee256598ccf7b946738fda8cd04de030a56` |
| character.scw | 264 | `33885ccd954c413887761824be79ab4d11a6bce8d61a729d31069d8a90965ddd` |
| manifest.json | — | `04a971c861b93463f37ff901743c8b8572c3bbb2a492a433fe8767a32f56de24` |

La comparación verifica primero los manifiestos de las entregas físicas:

| Entrega | Build | SHA-256 del manifiesto |
|---|---|---|
| CT material v2 | `ced27c955e41` | `26c865aacb083a4e5ecbc0f7d6db3419cc50168a2cdb79cf0dad6bcff0d87581` |
| LI lighting v1 | `b27d16a1671e` | `247e463e55380046527090f433d4dbc5e3512474f50da2d6d8702a235e2dea66` |
| GC world v1 | `abe9a7a35464` | `98a0a130b1d4bec9df09655c37f4a63bc12944e2e30422b02e6cc6cc58321f53` |

Auditor local `build/character-render-intermediate/audit.py`, SHA-256
`c2775df32f82ad34f7818ab1ed741525e602e94d6549cef9ad49278e20f5d230`.
Comprobante privado `f03-04-character-render-intermediate-check-v1/roundtrip.json`,
SHA-256 `d3dbf386b7a60d5268d1b0980b25674ecdceac62a28b5ad45c9104f20aeb6a24`.
Incluye hashes de las siete fuentes, implementación y todas las salidas.
Esta igualdad no constituye una nueva prueba física ni requiere copiar otro build.

## Siguiente tarea

**[IR-T6 completada](f03-04-map-intermediate.md):** perfil de geometría estática
y material de mapa ya verificados, conservación de metadatos y adjuntos,
SGM/STX idénticos al visor aceptado mediante fixtures y conversiones A/B.
Colisión, cámara y audio requieren perfiles posteriores; SH3P requiere F03.05.
