# TEX01–TEX07 — Sondeo estructural de texturas PS2

Instancia preparatoria de [F03.01](../docs/specs/sh3-3ds/tasks/F03.md#f0301).
Aplica RF02.02, RNF05.01 y RNF06.01. Versión 1, 2026-10-20.

## Requisitos EARS

- **TEX01:** WHEN se inspeccionan recursos THEN el coordinador SHALL reconciliar
  catálogo y recibo fijados por SHA-256, verificar el conjunto privado antes y
  después, y usar lecturas cuya integridad completa comprueba `VerifiedPrivateReader`.
- **TEX02:** WHEN el sufijo privado es `.tex` THEN el sondeo SHALL tratarlo solo
  como criterio de selección; una entrada aceptada SHALL seguir sin capacidad de
  decodificación, vínculo de sala ni soporte de juego declarado.
- **TEX03:** WHEN la entrada coincide con el subconjunto descrito abajo THEN el
  parser SHALL producir rangos y metadatos deterministas de todos sus bloques,
  sin leer ni exportar índices o colores a través de su puerto.
- **TEX04:** IF un tamaño, cantidad, formato, dimensión, marcador o rango no
  satisface el contrato THEN el sondeo SHALL marcar la entrada desconocida con
  código estable, sin devolver una lista parcial de bloques como aceptada.
- **TEX05:** WHEN un campo carece de interpretación comprobada THEN el informe
  SHALL conservar su valor numérico o la huella del header que lo contiene,
  sin convertirlo en semántica de material, alpha, orientación o dependencia.
- **TEX06:** IF falla la integridad, el puerto devuelve una lectura incompleta o
  no puede publicarse el informe THEN la CLI SHALL fallar sin anunciar éxito;
  SHALL rechazar destinos existentes y publicar después de cerrar el lector.
- **TEX07:** WHEN se documenta cobertura THEN el informe SHALL distinguir
  estructura inspeccionada, decodificación de píxeles, ejecución de Noesis y
  comparación visual; SHALL fijar revisión/licencia de la referencia y conservar
  originales fuera del repositorio y de CI.

## Referencia y subconjunto v1

Referencia primaria: Sparagas/Silent-Hill, revisión
`f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35`, plugin
[`tex_sh2_sh3_ps2_tex_tbn2.py`](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/Noesis%20-%20Python%20Plugins/tex_sh2_sh3_ps2_tex_tbn2.py)
y plantilla
[`sh2_sh3_ps2_tex_tbn2.bt`](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/010%20Editor%20-%20Binary%20Templates/sh2_sh3_ps2_tex_tbn2.bt).
Licencia MIT, autores del formato en esas herramientas: Laurynas Zubavičius y
Rodolfo Nuñez. Son referencias del layout; no se incorpora su implementación ni
se ejecuta Noesis. El parser propio tiene límites explícitos más estrechos.

Todo entero multibyte es little-endian. Presupuestos del sondeo (no límites
universales del formato): 16 MiB por recurso, 256 bloques, dimensión 1–1024.
No se reserva memoria usando el tamaño de un payload.

| Cabecera | Campos y reglas |
|---|---|
| Área, 32 bytes | i32 en 0 = -1; u32 en 8 = 32; u32 en 20 = cantidad 1–256. u32 en 12 debe señalar el inicio del último bloque o el final exacto. Los demás u32 se conservan opacos. |
| Textura, 48 bytes | i32 ID en 0, u16 X/Y en 4/6 opacos, u16 ancho/alto en 8/10, u8 bpp en 12 = 4 u 8. u8 relleno declarado en 13 se conserva; no determina el rango. u16 importancia en 14 opaco. |
| Tamaños de textura | u32 `data_size` en 16 = ancho × alto × bpp / 8, división exacta; u32 `all_size` en 20 incluye header, relleno e índices. `all_size >= 48 + data_size`. Índices en `inicio + all_size - data_size`. |
| Resto de textura | u8 send-PSM en 24 = 0, draw-PSM en 25 = 0x14 para 4 bpp / 0x13 para 8 bpp; 26/27 opacos; exponentes en 28/29 coherentes con floor(log2(dimension)); u16 en 30 = 0x9999. Huella SHA-256 del header conserva evidencia de los 16 bytes finales opacos. |
| CLUT, 48 bytes | Inmediatamente después de `all_size`; u32 tamaño en 0; u8 cantidad en 12 = 4, 8 o 16; tamaño = cantidad × 1024. Dimensiones declaradas en 14/15 = 64/64, conservadas sin usarlas para inferir un raster. Offsets en 4/8 y byte 13 opacos; huella del header para bytes restantes. |
| Payload CLUT | Rango después de su header, seguido del próximo bloque. Debe terminar exactamente al final del recurso después de la cantidad declarada. |

Los layouts SH2, sin cabecera, bpp 24, contador cero con bloque adicional, otros
PSM y otras distribuciones CLUT quedan desconocidos en v1. Un rechazo no demuestra
que el recurso sea inválido para el juego. No se interpreta ni valida el GIFtag.
La cantidad CLUT **no** se declara cantidad de imágenes exportables: el mapeo de
paletas, subpaletas de 4 bits, desentrelazado, alpha y orientación son F03.02.

## Diseño y salida

`texture_probe` recibe tamaño y un callable de rango, sin filesystem ni SDK.
`texture_survey` reconcilia/selecciona/colecta; adapta `CandidateReader` al parser,
manteniendo errores de integridad fuera de los rechazos estructurales.
La CLI reutiliza el lector privado y la publicación exclusiva existentes.

JSON v1: `scope=ps2_texture_structure_survey`, método
`sh3-ps2-indexed-texture-structure-v1`, evidencia catálogo/recibo, revisión de
referencia, origen, lista ordenada por ID y resumen. Cada entrada conserva
ID/contenedor/tamaño/hash, `classification.type=unknown`, dependencias
`not_inspected` y resultado `structural_candidate` o `unknown`.
Cada bloque aceptado registra offsets/tamaños, dimensiones, bpp/PSM, ID numérico,
relleno declarado/calculado, metadatos opacos y hashes de headers.
No incluye nombres, rutas privadas, índices, colores ni previews.
`payload_decoding=not_performed`, `capabilities=[]`, G02 y F03.01 global pendientes.

## Tareas y validación

- [x] TEX-T1: implementar parser puro; fixtures propios de 4/8 bits, varios
  bloques, límites, relleno discordante y metadatos opacos. TEX03–TEX05.
- [x] TEX-T2: coordinar y exponer CLI; casos de recibos inconsistentes, corrupción,
  lectura corta, selección vacía, rechazo y destino ocupado. TEX01, TEX02, TEX06.
- [x] TEX-T3: releer las dos copias de los 119 candidatos y exigir informes
  idénticos; publicar matriz de cobertura con hashes de referencia y evidencia.
  TEX01, TEX07. El número 119 es la selección observada, no una constante del lector.
- [x] TEX-T4: elegir un bloque de 8 bits por ID/offset/tamaño para F03.02 y
  documentar verificaciones pendientes de píxeles. TEX02, TEX07.

La CI existente descubre los tests Python con datos propios; Ruff, cobertura y
custodia se ejecutan sin originales ni red. No requiere recompilar ARM.
Resultados: [informe F03.01](../docs/execution/f03-01-texture-structure.md).
