# PX01–PX07 — Primera textura PS2 de 8 bits

2026-10-20. Instancia F03.02, a partir del
[sondeo TEX01–TEX07](ps2-texture-probe-v1.md). RF02.04, RF02.05, RF02.08,
RNF06.01 y RNF08.01. No cierra G02/G03 ni acredita una sala.

## Requisitos EARS

- **PX01:** WHEN se solicita un ID de recurso y ordinal THEN el pipeline SHALL
  reconciliar catálogo/recibo fijados, volver a comprobar su estructura y leer
  sus rangos con verificación completa de SHA-256 antes de decodificar.
- **PX02:** IF el bloque no es 8 bpp, send-PSM 0, draw-PSM 0x13, cuatro unidades
  CLUT de 1024 bytes o dimensiones admitidas THEN el decoder SHALL rechazarlo
  antes de reservar buffers de salida.
- **PX03:** WHEN se convierten los índices THEN el decoder SHALL producir un
  raster por filas sin invertir ejes; el direccionamiento SHALL coincidir con
  un oráculo independiente PSMCT32→PSMT8 para todos los píxeles probados.
- **PX04:** WHEN se interpretan los 4096 bytes CLUT THEN el decoder SHALL
  conservar cuatro paletas RGBA de 256 entradas, aplicar la permutación de
  índices de color y conservar incluso paletas uniformes 0x00/0xCC.
- **PX05:** WHEN se generan imágenes THEN el pipeline SHALL conservar RGBA con
  alpha PS2 intacto y generar por separado PNG con `A=min(255,2*A_PS2)`;
  SHALL identificar esta transformación y sus pérdidas en el manifiesto.
- **PX06:** WHEN se publican resultados THEN el writer SHALL usar una sesión
  privada nueva fuera del repositorio, archivos exclusivos y manifiesto final
  con hashes; IF hay fallo THEN SHALL conservar parciales sin declarar éxito.
- **PX07:** WHEN se comunica validación THEN el informe SHALL distinguir
  fixtures, direccionamiento contrastado, repetición de datos reales, inspección
  visual y comparación con el juego original; una imagen plausible SHALL NOT
  promover automáticamente soporte de material ni selección de paleta.

## Diseño y contrato

Decoder puro en `tools/pipeline/decoders/ps2_indexed8.py`, sin filesystem/SDK.
Entrada: dimensiones, índices swizzled de `w*h` bytes, CLUT de 4096 bytes.
Anchos 128/256/512/1024; altos 64/128/256/512/1024; máximo 1.048.576 píxeles.
Son límites de este corte, no del formato general. Datos inmutables; sin resize,
gamma, compresión con pérdida, flip ni deducción de UV.

El envío PSMCT32 se modela con ancho/alto a la mitad y cuatro bytes por texel;
el destino se lee como PSMT8 de ancho/alto completos. La implementación compacta
se contrasta con escritura/lectura de páginas, bloques y columnas del GS, sin
usar esa misma expresión para generar los esperados.
Referencia de tablas: PCSX2 `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`,
`pcsx2/GS/GSTables.cpp` (GPL-3.0+), solo en el ensayo externo.
SHA-256: `a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8`.
El pipeline no incorpora ni enlaza código PCSX2.

CLUT: cuatro columnas de 64 bytes por fila; 16 filas. Para entrada de color `i`,
intercambiar bits 3 y 4 para obtener `j`; la entrada de paleta `p` se lee de
`(j//16)*256 + p*64 + (j%16)*4`. Referencia de distribución: plugin
Sparagas fijado en el contrato TEX. RGBA original mantiene los cuatro canales.
Un alpha mayor que 127 satura a 255 en la vista; la salida original permite
revisar esa pérdida. La interpretación material del alpha sigue pendiente.

La coordinación reutiliza `probe_texture` y `VerifiedPrivateReader`: rangos
largos leídos en fragmentos de ≤4096 bytes, cada uno verificado contra el recurso
completo. El informe registra ID, hash de origen, ordinal, headers/rangos,
receta, dimensiones, estadísticas de paleta y hashes de cada salida.
No se necesita el informe del sondeo para confiar en offsets: se recalculan.

El writer y el encoder PNG se separan del decoder. PNG RGBA8 con filtro cero,
sin metadatos variables. Resultados privados: índices lineales, cuatro paletas
originales, cuatro RGBA originales y cuatro PNG normalizados, más manifiesto.
La CI solo usa datos propios. Versiones zlib y hashes RGBA se conservan; la
repetibilidad de bytes PNG se verifica en el entorno registrado.

## Tareas y aceptación

- [x] PX-T1: decoder y fixtures asimétricos; límites, tamaños incorrectos,
  direccionamiento exhaustivo, colores y alpha extremos. PX02–PX05.
- [x] PX-T2: CLI con selección explícita y writer privado; integridad, recursos
  ausentes, variante no soportada, publicación fallida/sesión ocupada. PX01, PX06.
- [x] PX-T3: generar oráculo desde tablas externas fijadas y comparar mapas;
  repetir la muestra desde las dos copias y comprobar todos los hashes. PX03, PX07.
- [x] PX-T4: inspeccionar PNG privados, documentar lo observable y las
  comparaciones pendientes antes de integrar la textura en 3DS. PX05, PX07.

[Ejecución y límites](../docs/execution/f03-02-indexed-texture.md): 318 pruebas,
20 tamaños contrastados y dos conversiones idénticas. La comparación con el
material en el juego permanece pendiente; la presentación privada en 3DS se
completó en [TI-T1–TI-T5](../docs/specs/sh3-3ds/texture-inspection.md).
