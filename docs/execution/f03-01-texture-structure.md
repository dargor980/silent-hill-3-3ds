# F03.01 — Estructura de texturas PS2

Fecha: 2026-10-20. Completada la instancia **referencia y sondeo estructural**.
F03.01 global, G02 y la decodificación visual permanecen abiertos.
[Contrato EARS](../../schemas/ps2-texture-probe-v1.md),
[matriz de formatos](../reverse-engineering/format-coverage.md) y
[ticket](../specs/sh3-3ds/tasks/F03.md#f0301).

## Resultado

Se inspeccionaron los 119 recursos con sufijo `.tex` del catálogo europeo
SLES-51434/PAL 1.02, 75.609.808 bytes en total. Las dos copias de F02.05 produjeron
informes idénticos: 119 candidatos estructurales, 321 bloques, 281 de 8 bits y
40 de 4 bits. No hubo rechazo dentro de ese conjunto. Esta cifra no incluye
texturas posiblemente embebidas en otros tipos, XBG0 ni AFS.

El parser recorre área, textura y CLUT, calcula los rangos de datos y exige final
exacto. Nueve bloques declaran 48 bytes de relleno pero contienen 32 según sus
tamaños; se conserva la discrepancia y se usa la diferencia de tamaños, conforme
al layout de la referencia. Las coordenadas opacas, flags y GIFtag no reciben
semántica inventada. Ningún píxel fue decodificado o exportado.

La selección para F03.02 es un bloque de 8 bits, 256×256, cuatro unidades CLUT.
El recurso tiene 69.808 bytes y SHA-256
`65173379ae86c13512b0c546edf68ae3a82b79b7267f5b011a39d8d44ccf35e4`.
Índices: offset 128, 65.536 bytes; CLUT: offset 65.712, 4096 bytes.
Su vínculo de sala y el contenido visual siguen sin identificar.

## Integridad y repetición

El catálogo y recibo se cargaron con sus hashes históricos:

| Evidencia | SHA-256 |
|---|---|
| Catálogo F02.04 | `39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d` |
| Recibo F02.05 | `74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943` |
| Cada sondeo, 501.439 bytes | `30566f4f8279d400f4f967f19531a3d9b5fde64a12167aea967f9530c6cbe7e7` |
| Selección, 1.668 bytes | `ec926c96f2143d563d7d667e0b4bb033760594841fbcff50ad084f988dc0f530` |

Antes de cada rango, el lector existente verifica tamaño y SHA-256 del recurso
completo; compara identidad y estabilidad al cerrar. Comprueba el conjunto de
archivos al inicio y al final. El puerto solo expone headers de 32/48 bytes al
parser. Los originales permanecen en las dos copias externas; no se releyó la ISO,
no se modificaron extracciones ni se incluyeron bytes del juego en tests o CI.

Informes ignorados:

- `reports/local/f03-01-texture-structure-v1.json`
- `reports/local/f03-01-texture-structure-v1-repeat.json`
- `reports/local/f03-01-texture-selection-v1.json`
- `reports/local/f03-01-execution-v1.json` (comandos, rutas y salidas)

Reproducción para cada copia, con destino nuevo:

```sh
rtk proxy .venv/bin/python -m tools.inspectors.texture_survey \
  --catalog reports/local/f02-04-asset-catalog.json \
  --catalog-sha256 39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d \
  --receipt /raiz/privada/f02-05/verified.json \
  --receipt-sha256 74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943 \
  --private-copy /raiz/privada/f02-05/copy-a \
  --output reports/local/nuevo-sondeo.json
```

La raíz del ejemplo es un marcador. Los comandos reales constan en el registro
privado. La publicación exclusiva ocurre después de cerrar el lector.

## Diseño y validación

`texture_probe` es un parser puro de rangos; `texture_survey` coordina selección,
evidencia y resumen mediante un puerto. La CLI compone el lector privado y el
publicador existentes. No añade dependencias, SDK ni código al runtime 3DS.

**261/261 pruebas aprobadas**, incluidas **69 nuevas**. Se ejecutaron
`test_texture_probe.py`, `test_candidates.py`, `test_camera_probe.py` y
`test_repository.py`. Se cubren 4/8 bits, varios bloques, límites de cantidad y
dimensión, dimensiones no potencia de dos, lectura solo de headers, datos opacos,
relleno discordante, truncamientos, tamaños extremos, conteo impar de píxeles de
4 bits, PSM/CLUT desconocidos, recibos mezclados, selección vacía, lectura corta,
corrupción real en archivo, cambios de conjunto, destino ocupado, error de
publicación, cierre previo y entrada CLI en subproceso.

Cobertura de los **dos módulos nuevos**: 111/112 líneas (99,1 %) y 19/20 ramas
(95 %). Parser puro: 100 % en ambas. La entrada `__main__` se probó en subproceso
sin sumar su cobertura a la del proceso padre. JUnit y cobertura:
`build/f03-01/final-tests.xml`, `final-coverage.json` y `final-coverage.xml`.
No se declara repetida toda la batería Python ni los tests C++/ARM.

Los primeros ensayos detectaron un campo `path` omitido en el fixture y una
selección de archivo errónea en el test de corrupción: apuntaba a un recurso no
seleccionado por el sondeo. Se corrigieron los fixtures; no se relajó el lector.
Ruff también exigió fijar el argumento de recurso en el callable, resuelto con
`partial`. Se conservan `initial-tests.xml` y `tests.xml`.

La CI existente descubre estos casos con datos propios y aplica sus controles de
formato, cobertura y custodia. La ejecución remota permanece pendiente.
La prueba física del corte sintético no demuestra renderizado de estos recursos.

Ruff check/format, gate de cobertura por líneas/ramas, arquitectura,
custodia/referencias y `git diff --check`: aprobados localmente.
`build/f03-01/source-manifest.json` identifica 16 archivos de implementación,
dependencias compartidas, pruebas, contratos y CI; SHA-256
`722c2b2d3e6b0119c3d9978fb982c1d1c511cf3dae983d732688264c0d291fe7`.
Excluye este informe para evitar autorreferencia. No se creó commit en esta instancia.
