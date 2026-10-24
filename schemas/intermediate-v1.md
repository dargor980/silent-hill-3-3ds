# F03.04 — Intermedio v1, perfil de malla y animación PS2

Contrato inicial, 2026-10-23. RF02.04/RF02.05. Perfil acotado
`ps2-character-0209-v1`: MDL/ANM del caballo y clip de inspección `0x1449`.
G02/G03 y F03.03 global siguen abiertos; esta instancia reutiliza el perfil
SA/CM/GC contrastado y aceptado físicamente. No define el contenedor SH3P.

## Requisitos EARS

- **IR01** WHEN importa los documentos SHALL verificar manifiestos fijados,
  hashes/tamaños y que MDL/ANM sean los mismos en ambas procedencias.
- **IR02** WHEN serializa SHALL conservar todos los campos de los JSON
  decodificados y manifiestos, incluidos desconocidos, flags, palabras
  originales, déficits de peso, orden de caras/grupos y las 76 muestras ANM.
  SHALL versionar perfil, convertidor, recetas y convenciones por separado.
- **IR03** WHEN exporta inspección SHALL producir SAN/SCM con las recetas
  existentes y acompañarlos del intermedio completo como sidecar. SHALL
  declarar el recorte 0..23 y los datos no representados en los binarios.
- **IR04** WHEN reconstruye desde el sidecar SHALL regenerar SAN/SCM idénticos
  sin leer la ISO ni los documentos de origen. SHALL conservar enteros,
  booleanos, floats finitos y cero negativo en la representación lógica.
- **IR05** IF encuentra versión/perfil no soportado, identidad distinta,
  claves duplicadas, números no finitos, exceso de límites o incoherencia de
  esqueleto SHALL rechazar antes de publicar. SHALL validar nuevamente al leer.
- **IR06** WHEN escribe SHALL usar salida privada exclusiva, comprobar hashes
  y publicar manifiesto al terminar. SHALL conservar salidas anteriores.
  CI SHALL ejecutar únicamente fixtures sintéticos y cobertura ≥80 %.

## Modelo y límites

`intermediate.json` es JSON UTF-8 canónico de este proyecto: claves ordenadas,
ASCII escapado, separadores compactos `,`/`:`, una LF final, `allow_nan=False`.
No es una afirmación de conformidad con otro estándar de canonicalización.
La igualdad garantizada es de valores y tipos JSON y bytes de SAN/SCM; no
reconstruye el MDL original ni el espaciado de los JSON de entrada.

Campos raíz exactos: `schema_version=1`, `profile`, `converter`, `decoders`, `conventions`,
`documents`, `provenance`. `documents` contiene `skeleton`, `animation`, `mesh`;
son árboles completos de los decodificadores v1, con extensiones conservadas.
`provenance` conserva los manifiestos completos `skeleton` y `mesh`. Sus
listas de archivos describen los JSON de origen, no el JSON canónico nuevo.
El SHA del manifiesto nuevo describe los bytes nuevos.

`decoders` identifica los contratos v1 `ps2-mdl-skeleton-v1`,
`sh3-ps2-anm-0209-46-v1` y `mdl_v3_unmasked_skip_vif_integer_mesh_v1`.
Son versiones de contrato; no acreditan el hash del ejecutable histórico.
Los manifiestos de origen conservan sus estados históricos, incluidos
pendientes ya resueltos por informes posteriores, sin reescribirlos.

El perfil fija bosque `[-1,-1,1]`, modelo 0x0209, 76 muestras de 46 bytes y
recetas actuales. El esqueleto embebido en la malla debe coincidir con todos
los campos del esqueleto separado excepto su `schema_version` añadido.
No se infieren semánticas de campos desconocidos ni nuevas capacidades.

Convenciones explícitas: posiciones Q4 locales al hueso primario; normales y
UV Q12, sin normalización/V flip; pesos Q12 con déficit conservado; helpers
por columnas; raíces independientes; NLERP más corrección hemisférica;
selección `0x1449`, muestras 0..23, periodo Q12=98304, incremento observado
3686; previsualización 25 evaluaciones/s, sin afirmar cadencia PS2.
Mundo, base B, origen de inspección y escala se mantienen separados.

Presupuesto: entrada o intermedio ≤8 MiB, profundidad ≤32, ≤500.000 nodos,
claves ≤256 caracteres, strings ≤65.536 caracteres y UTF-8 válido,
texto UTF-8 acumulado ≤8 MiB, enteros de -2^63 a 2^64-1, floats finitos. La lectura de archivo es acotada
antes de JSON; la validación recorre el árbol con contadores. No se acepta
una extensión en campos raíz: un perfil nuevo necesita versión explícita.

## Diseño y tareas

`intermediate_json` posee codec JSON estricto/acotado, sin I/O. El adaptador
`character_intermediate` valida procedencias y convenciones y aplica las
recetas existentes; no reimplementa skinning. `prepare_character_intermediate`
coordina lecturas fijadas, round-trip y salida privada a través del writer
existente. Los bytes SAN/SCM se comparan con el visor aceptado.

- [x] **IR-T1** (IR01/IR02/IR05): fijar contrato, codec determinista y límites;
  probar duplicados, tipos, extensiones y estructuras malformadas.
- [x] **IR-T2** (IR01–IR05): adaptador malla/esqueleto/animación, convenciones
  explícitas y sidecar; probar round-trip y regeneración sin origen.
- [x] **IR-T3** (IR06): preparador privado, CLI, publicación exclusiva y
  batería sintética bajo el job Python existente; cobertura y fallos de I/O.
- [x] **IR-T4** (IR01/IR04/IR06): convertir las dos extracciones privadas independientes,
  intermedios/exportaciones idénticos y SAN/SCM iguales a GC-T5 físico;
  registrar hashes y límites sin recompilar ni atribuir nueva prueba física.
- [x] **IR-T5 — [perfil de render](character-render-intermediate-v1.md)**: incorporar materiales/texturas, luces y
  colocaciones con contratos y sidecars propios; después geometría de mapa,
  colisión, cámara y audio. No cerrar F03.04 global con el perfil inicial.
- [x] **IR-T6 — [perfil de mapa](map-intermediate-v1.md)**: geometría estática y material de mapa
  verificados; fijar contrato, preservar metadatos y reconstruir SGM/STX con
  fixtures y comparación privada A/B. Colisión/cámara/audio quedan posteriores.
- [x] **IR-T7 — [registros de colisión](collision-intermediate-v1.md)**:
  IR-T7a/b completadas: 30 capturas revalidadas, inventario y contrato
  `ps2-collision-registry-v1`; geometría/semántica física pendientes.
  IR-T7c completada: decoder puro, 100 tests sintéticos y cobertura 100 %.
  [IR-T7d completada](../docs/execution/f03-04-collision-intermediate.md):
  adaptador/preparador, 240 rangos conservados, reconstrucción de 242 archivos
  y cotejo en memoria de las 30 capturas.
  [IR-T7e completada](../docs/execution/f03-04-collision-verification.md):
  oráculo independiente, 257 pruebas del perfil y gate por módulo en CI.
  [IR-T7f completada](../docs/execution/f03-04-collision-publication.md):
  242 archivos y manifiestos privados A/B idénticos, cotejo con fuentes y
  reconstrucción independiente desde ambos paquetes sin acceso externo.
  Perfil de registros cerrado; formas/respuesta física y cámara/audio pendientes.
- [x] **CF-T7 — [formas poligonales](collision-polygons-intermediate-v1.md)**:
  CF-T7a completada: contrato CPI01–CPI14, fuente íntegra más vista por recurso,
  procedencia y clasificación completa; 24 ejemplos propios reconstruidos o
  rechazados según contrato, también con `-O`. CF-T7b completada: adaptador
  puro con tres APIs, 139 pruebas, cobertura 100 % de líneas/ramas y 3.416
  regresiones aprobadas. CF-T7c completada: preparador/writer exclusivo,
  custodia y 104 pruebas propias; A/B preparado en memoria con 519 archivos
  y manifiestos iguales. CF-T7d completada: oráculo independiente, fidelidad
  externa, 279 pruebas nuevas y gates permanentes CPI; calidad local con
  8.829 pruebas aprobadas. [CF-T7e completada](../docs/execution/f03-04-collision-polygons-publication.md):
  519 archivos y manifiestos A/B publicados e idénticos; ocho reconstrucciones
  sin fuentes, cotejo externo y 575 entradas intactas. 233/52/0 y 30 referencias
  históricas reproducidos. Perfil estructural cerrado, IR-T7 intacto;
  formas dinámicas, variante de 48 bytes y respuesta física pendientes.

[Ejecución, comprobantes y límites](../docs/execution/f03-04-character-intermediate.md):
167 tests aprobados, cobertura combinada 97,07 %, A/B idénticos y SAN/SCM
iguales al build físico `abe9a7a35464`; sin nueva compilación ni prueba física.
