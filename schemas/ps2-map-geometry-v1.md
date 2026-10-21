# MG01–MG07 — Decodificación de un grupo MAP para inspección

2026-10-20. Continuación de F03.02 / MP-T4. RF02.04/RF02.05/RF02.08,
RNF06.01, RNF08.01. Se decodifica el grupo menor ya localizado; la asociación
de textura y la transformación del juego siguen siendo comprobaciones distintas.

## Requisitos EARS

- **MG01** WHEN se selecciona un ID y offset de grupo THEN el coordinador SHALL
  reconciliar catálogo/recibo fijados y volver a recorrer el MAP; SHALL rechazar
  grupos ausentes y presupuesto excedido antes de leer payloads.
- **MG02** WHEN decodifica registros de 16 bytes THEN SHALL conservar exactamente
  posiciones, palabras UV y atributos empaquetados originales; SHALL comprobar
  una reconstrucción byte a byte antes de publicar.
- **MG03** WHEN el bit 0 de la palabra U está desactivado THEN SHALL emitir el
  triángulo que termina en ese vértice, con paridad alternada por posición de
  vértice; IF ocurre antes del tercer vértice THEN SHALL rechazar el bloque.
- **MG04** WHEN crea una vista UV THEN SHALL registrar explícitamente
  `(U/32768, 1-V/32768)`, conservando el bit de control dentro de U como hacen las
  referencias. SHALL NOT confundir esa vista con UV/material verificados en PS2.
- **MG05** WHEN exporta geometría THEN SHALL mantener índices locales por forma,
  registrar triángulos degenerados sin descartarlos y separar grupos/formas.
  SHALL NOT aplicar escala, matriz, giro, soldadura ni asignación de material
  sin un contrato verificado.
- **MG06** WHEN escribe salidas THEN SHALL usar un directorio privado nuevo,
  exclusivo y fuera del checkout; SHALL producir JSON canónico, OBJ de
  inspección y manifiesto con hashes, sin originales en CI.
- **MG07** WHEN documenta aceptación THEN SHALL distinguir fixtures propios,
  integridad/repetición, inspección visual y correspondencia con el juego.
  La comparación de material y la presentación de geometría en 3DS SHALL
  permanecer pendientes hasta contar con sus propias evidencias.

## Formato y responsabilidades

Referencias de layout y strips: las revisiones Sparagas y Murugo fijadas en
[MP](ps2-map-probe-v1.md). Ambas usan el mismo orden de atributos y regla de
triangulación; no constituyen prueba de la semántica completa del render PS2.
No se ejecutan los plugins ni se importa código de sus hosts.

Cada registro: ocho i16 LE: `X,Y,Z,packedX,U,V,packedY,packedZ`.
El bit 0 de U omite el triángulo que termina en ese vértice. Para índice `i`
par: `(i-2,i-1,i)`; impar: `(i,i-1,i-2)`. La paridad se reinicia por forma,
no al encontrar una omisión. Los atributos empaquetados se conservan opacos;
no se inventan normales o colores a partir de ellos.

Límites de esta instancia: 3–65536 vértices por forma; máximo 65536 por grupo,
validado antes de leer datos. MAP conserva el presupuesto de MP. Lecturas
de payload ≤4096 bytes. Las posiciones permanecen en unidades locales i16;
el índice de transformación del header se registra sin aplicarlo.

- `decoders/ps2_map_geometry.py`: datos inmutables, lectura pura, strips,
  reconstrucción y detección exacta de triángulos de área cero con enteros.
- `decode_map_geometry.py`: selección, integridad, jerarquía, rangos, manifiesto.
- `geometry_obj.py`: adaptador de inspección; `v/vt` por vértice y caras con
  índices globales 1-based en OBJ; nombres generados desde offsets.
- Writer privado compartido: conjunto fijo `geometry.json`, `inspection.obj`,
  manifiesto final. OBJ no incorpora texturas ni materiales del juego.

## Tareas y validación

- [x] **MG-T1:** decoder y tests de signo, extremos, omisiones consecutivas,
  paridad tras omisión, formas independientes, degenerados y tamaños inválidos.
- [x] **MG-T2:** coordinador/OBJ/writer; pruebas de selección, presupuesto,
  corrupción, lectura corta, salida repetida, orden de cierre y JSON/OBJ coherentes.
- [x] **MG-T3:** repetir grupo 304 desde ambas copias, comparar los archivos,
  inspeccionar geometría y UV; registrar cantidades y límites.
- [x] **MG-T4:** demostrar matriz/material contra PS2 y preparar presentación
  de geometría en 3DS con sus pruebas propias. Depende de MP-T4 para fidelidad;
  la presentación de inspección ya se completó en
  [GI-T1–GI-T5](../docs/execution/f03-02-geometry-inspection.md), incluida
  confirmación física del usuario. Matriz/material de estas dos formas
  comprobados por [MR-T4d](../docs/execution/f03-02-map-draw-state.md);
  [MI-T1–MI-T4](../docs/execution/f03-02-material-inspection.md) integran
  ambos y el usuario confirma paneles con transparencia, controles y ciclo
  de vida en New 2DS XL. Cierre acotado, sin equivalencia de píxeles PICA/GS.

[Ejecución](../docs/execution/f03-02-map-geometry.md): 253 pruebas, dos bundles
idénticos, 56 vértices y 32 triángulos inspeccionados en el host.
