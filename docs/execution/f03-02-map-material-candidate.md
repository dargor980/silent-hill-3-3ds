# F03.02 — Estructura del mapa candidato a la textura

2026-10-20. Completadas MP-T1–MP-T3 del
[contrato MP01–MP07](../../schemas/ps2-map-probe-v1.md).
Se localizó y verificó una estructura de mapa asociada **por nombre** a la
textura presentada en 2DS XL. El lector propio obtiene 8 grupos, 10 mallas,
10 submallas y 31 formas, con 15.882 vértices declarados. No decodifica esos
vértices ni demuestra todavía la relación material/textura.

Continuidad: [MG-T1–MG-T3](f03-02-map-geometry.md) ya decodifican las dos formas
del grupo menor, con 56 vértices y 32 triángulos. La
[captura posterior MR-T4b/c](f03-02-map-runtime-binding.md) verifica la asociación
del banco, CLUT 0 y TEX0 para ambas formas. Su transformación y comparación
final de dibujo siguen pendientes.

Actualización: [MR-T1–MR-T3](f03-02-map-render-metadata.md) delimitan las raíces
por contador y localizan el registro base mediante el ejecutable europeo.
La cola compartida descrita abajo es estructural: la ruta que empieza en 304
consume solo ese grupo. El vínculo con el payload se demuestra en la captura
posterior; los informes estáticos originales conservan sus límites.

## Resultado y límite de la asociación

El catálogo privado sitúa el MAP y la textura en el mismo contenedor, con
raíz de nombre común y sufijo `TR` en la textura. El par se eligió explícitamente.
Se mantienen `material_binding=unverified`, `capabilities=[]`, G02/G03 abiertos.
La coincidencia de nombre no identifica una sala ni una superficie.

MAP: 2.134.960 bytes, SHA-256
`fe6661eeb4d7df7e3baf6cd015452e1c9d3548416a862e503e1f2370a1f289c9`.
Textura externa: 69.808 bytes, SHA-256
`65173379ae86c13512b0c546edf68ae3a82b79b7267f5b011a39d8d44ccf35e4`.
IDs completos y nombres permanecen en el catálogo/recibos locales.

Las raíces de grupos son `[0, 304, 1472]`. La cadena de 304 llega a 1472:
ambas raíces comparten una cola. El lector conserva ambas rutas y cuenta cada
grupo una sola vez. Contar cada raíz como una escena independiente duplicaría
parte de la geometría en este recurso.

| Grupo, offset absoluto | Campo u32 +16 / +20, semántica pendiente | CLUT candidatos por malla | Formas | Vértices declarados |
|---:|---|---|---:|---:|
| 304 | 2 / 0 | 0 | 2 | 56 |
| 1472 | 3 / 1 | 0 | 4 | 8022 |
| 130224 | 3 / 2 | 0, 1 | 7 | 1764 |
| 159136 | 3 / 3 | 0 | 5 | 4170 |
| 226320 | 3 / 4 | 0 | 2 | 378 |
| 232640 | 3 / 5 | 0, 14 | 7 | 898 |
| 247696 | 3 / 6 | 0 | 2 | 364 |
| 253792 | 3 / 7 | 0 | 2 | 230 |

El grupo menor para una primera investigación está en 304: malla 352, submalla
400, formas 448 y 928. Declaran 26 y 30 vértices, en rangos 512/416 bytes y
992/480 bytes. Ambas indican índice de transformación 1; el flag candidato de
la malla vale 1. Estos números no justifican aplicar la matriz o activar alpha
sin interpretar el código que los consume.

La hipótesis explícita de sección de texturas en offset **258048** pasa el
parser TEX y consume exactamente los 1.876.912 bytes restantes del MAP.
Contiene **siete bloques de 8 bits, 512×512**; seis declaran cuatro unidades
CLUT y uno, ordinal 4, declara dieciséis. Esta sección es distinta del bloque
externo de 256×256 que ya se mostró en consola.

Que los campos +20 tomen valores 0–7 y existan siete bloques embebidos más uno
externo es una pista coherente. **No demuestra** qué banco corresponde a cada
grupo, cómo se selecciona la CLUT ni que ese grupo se dibuje en el juego.

## Implementación SOLID y pruebas

- `map_probe.py`: parser puro sobre un puerto de rango; jerarquía, límites,
  contención y presupuesto. Solo lee cabeceras de 48/64 bytes.
- `map_survey.py`: selección explícita y coordinación de catálogo/recibo,
  parser MAP, parser TEX y salida de metadatos. No publica nombres ni payloads.
- `VerifiedPrivateReader` verifica el hash completo antes de exponer cada
  rango; la publicación exclusiva ocurre después de cerrar el lector.

**233/233 pruebas aprobadas**: 72 nuevas MAP, 69 TEX, 57 PX y 35 repositorio.
Los tests propios cubren raíces compartidas/en orden inverso, ciclos,
solapamientos, escape del padre, contadores, tamaños, desbordamientos de rango,
presupuestos, respuesta corta del puerto, selección inválida, copia corrupta,
conjunto modificado, error de publicación y el CLI real.

Los dos módulos nuevos alcanzan **124/125 líneas (99,2 %) y 27/28 ramas
(96,4 %)**. El parser puro tiene 100 %; la línea restante es el despachador
`__main__`, ejecutado en subprocess y en las lecturas privadas. Informes:
`build/f03-02-material/tests-final.xml` y `coverage-final.json`.
CI descubre estas pruebas por su job Python existente. No se ejecutó CI
remota ni se recompiló ARM; no cambió el ejecutable instalado en la consola.

Las dos copias privadas producen informes finales **idénticos de 37.402 bytes**:
`reports/local/f03-02-map-pair-{a,b}-v2.json`, SHA-256
`02b3a1a43cee6e28e6a4f8bf87a718804395c399027d0656b589d27629c44834`.
`build/f03-02-material/comparison.json` resume la comparación.
Los informes v1, anteriores al sondeo de la sección embebida, se conservan.

## Referencias inspeccionadas

Se leyeron las revisiones fijadas en MP, sin ejecutar Noesis ni Blender.
Los archivos y licencias MIT están en `build/f03-02-material/reference/`.
No se incorporan esos plugins al pipeline.

| Referencia | Bytes | SHA-256 |
|---|---:|---|
| Sparagas `fmt_sh3_ps2_map.py` | 8138 | `9a35a37171d296a34cda44889d9ae53b44ce386def6f6311410ffaf6a426214d` |
| Sparagas `sh3_map_ps2.bt` | 3667 | `79f92022db6e7459cdc551faa74ca662ed29f9316444e817e1e2ceb044be27f6` |
| Murugo `import_map.py` | 5666 | `e0a728cbccc9463de22427dca9c82bfbce769d80db124afa54f04dd3ffd6c449` |
| Murugo LICENSE | 1062 | `282aef12fe79c159cda7d95f2977b8fb6c97ad132faff63fef1acd900657a413` |
| Sparagas LICENSE | 1076 | `26f743052bafcf49c229e0a9f8bb694b3f0a5e22fafc099a2e8231778a059e54` |

Ambos importadores conservan geometría/UV, pero no resuelven la asignación de
texturas del material: Murugo asigna un material genérico y Sparagas deja la
asignación comentada. Ejecutarlos no aportaría por sí solo la comparación
material pendiente. Las convenciones de transformación y UV de estos visores
son referencias para investigar, no equivalencias con la GPU original.

## Reproducción y continuación

```sh
rtk proxy .venv/bin/python -m tools.inspectors.map_survey \
  --catalog reports/local/f02-04-asset-catalog.json \
  --catalog-sha256 39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d \
  --receipt /raiz/privada/f02-05/verified.json \
  --receipt-sha256 74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943 \
  --private-copy /raiz/privada/f02-05/copy-a \
  --map-id asset:464325b2533b0e0a0702d4ad52f7050d41e9a02ba308dea7bce2a3268e83d4ae \
  --texture-id asset:0af58e26e1e91e71293f018ef07da3daed14ad44fd94d4ecea6b7d4eb4d72c3b \
  --embedded-offset 258048 \
  --output reports/local/nueva-inspeccion.json
```

Usar la raíz privada autorizada y un destino nuevo; repetir con copy-b.
Próximos pasos de MP-T4:

1. Rastrear el consumidor PS2 de campos de grupo +16/+20 y CLUT de malla +16;
   verificar selección entre el recurso externo y los bloques embebidos.
2. Decodificar las dos formas pequeñas con fixtures propios de strips/UV y
   transformaciones, conservando datos originales y convenciones no resueltas.
3. Contrastar una captura de dibujo o estado de PS2 que use ese recurso:
   registrar escena/estado, buffers, TEX0/CLUT, UV y alpha. No alcanza el
   arranque anterior del juego ni la demo de textura de 2DS.
4. Solo con esa evidencia fijar el material; la geometría puede inspeccionarse
   con un material de diagnóstico explícito mientras la asociación sigue abierta.
