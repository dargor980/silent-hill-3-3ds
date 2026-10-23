# IR-T6 — Intermedio de geometría estática y material de mapa

2026-10-23. Perfil `ps2-map-glass-v1`, definido antes de implementar.
RF02.04/RF02.05 y GC01–GC06. Alcance observado: las dos formas de `hp34.map`
y la textura externa de paleta 0 verificadas en MR-T4d/MI-T4. Es un perfil
independiente de los personajes; no forma una escena ni define SH3P.

## Requisitos EARS

- **IR13** WHEN importa SHALL verificar hashes/tamaños de manifiestos,
  geometría, textura, referencia MR-T4d e informes GS/píxeles. SHALL comprobar
  identidad de recursos, enlaces de informes, capturas/modelo y formas.
- **IR14** WHEN serializa SHALL conservar los documentos/manifiestos completos,
  palabras i16 y atributos opacos, triangulación, omisiones, estado GS, colores
  y orden de dibujo. SHALL conservar exactamente el OBJ histórico y los trece
  archivos de textura: índices, cuatro paletas, cuatro RGBA y cuatro PNG.
- **IR15** WHEN reconstruye SHALL producir SGM/STX idénticos al visor aceptado
  usando solo el JSON intermedio y sus catorce adjuntos. SHALL comprobar OBJ
  contra geometría y RGBA contra índices/paletas, sin leer ISO ni capturas.
- **IR16** WHEN describe convenciones SHALL separar UV OBJ/checker con `1-V`
  de UV de material sin inversión, modelo de base/escala de inspección y alpha
  PS2 de PNG y STX. SHALL mantener los bytes de paletas no usadas, incluso
  alpha mayor que 128, sin asignarles semántica de material.
- **IR17** IF cambian versiones, identidades, tipos, inventarios, hashes,
  topología, captura, modelo o estado soportado SHALL rechazar antes de publicar.
  SHALL usar lecturas acotadas, nombres permitidos y salida privada exclusiva.
- **IR18** WHEN verifica SHALL ejecutar fixtures sintéticos y cobertura de
  líneas/ramas ≥80 % en el job Python; SHALL contrastar conversiones A/B y
  SGM/STX con la entrega física fijada, sin atribuir una prueba física nueva.

## Diseño y límites

Raíz exacta: `schema_version=1`, `profile`, `converter`, `conventions`,
`documents`, `provenance`. `documents` contiene `geometry`, `material_reference`,
`gs_report`, `pixels_report`. `provenance` conserva `geometry_manifest`,
`texture_manifest` y `source_sha256` con cinco entradas. Los hashes de fuentes
identifican los bytes históricos; el manifiesto nuevo protege el conjunto
recodificado. Se mantienen valores/tipos JSON, no su espaciado original.

Los adjuntos usan nombres fijos: `inspection.obj`, `indices.bin`,
`palette-{0,1,2,3}.{bin,rgba,png}`. El intermedio es JSON más esos catorce
archivos, no el JSON aislado. Los PNG se conservan por hash sin recodificar;
los RGBA de las cuatro paletas se reconstruyen desde índices para verificar
su coherencia. El perfil dibuja exclusivamente la paleta 0. Las estadísticas
de las cuatro paletas y los hashes de previsualización se comprueban.

JSON: límites del codec compartido, ≤8 MiB, profundidad 32 y 500.000 nodos.
Geometría: exactamente dos formas; topología/atributos según decoder MG y
presupuesto SGM de 3.072 vértices de dibujo. OBJ ≤4 MiB, índices 65.536 bytes,
paletas 1.024 bytes cada una, RGBA 262.144 bytes cada uno y PNG ≤1 MiB cada uno.
Manifiestos ≤64 KiB; referencia e informes ≤128 KiB cada uno. Inventarios
exactos: dos archivos de geometría y trece de textura. Salida: 17 archivos
más manifiesto, bajo el máximo compartido de 40 MiB.

El adaptador puro `map_intermediate` valida relaciones y aplica `verified_shapes`,
`encode_obj`, `material_geometry`, `material_texture` y `render_palette` ya
existentes. El preparador coordina I/O y publicación; los auxiliares de
inventario validan bytes/nombres. No cambia los encoders ni el renderer.

Modelo afín por columnas una vez, después base `(x,-y,-z)`, centrado y escala
uniforme de inspección. UV del material: palabras originales/32768 conservando
bit de U. RGB capturado `/128 × 227/256`; alpha STX `(A×255+64)//128`, distinto
de PNG `min(255,2*A)`. Material con alpha fuente, sin escritura de profundidad,
lineal/clamp y geometría plana frontal validada. Las unidades no se afirman
como metros; no se presume equivalencia numérica VU/GS/PICA.

CLI: `--inputs` apunta a JSON local ≤16 KiB con pares `path/sha256` para
`geometry`, `texture` (directorios/SHA de manifiesto), `reference`, `gs_report`
y `pixels_report` (archivos/SHA). Rutas absolutas solo en el preparador.
La reconstrucción no vuelve a ejecutar PCSX2 ni el oráculo de píxeles: verifica
los informes fijados y su coherencia, conservando sus límites y procedencia.

## Tareas

- [x] **IR-T6a** (IR13/IR14/IR16/IR17): contrato, inventarios y adaptador puro;
  conservar campos/adjuntos, validar geometría, paletas y relaciones MR/GS.
- [x] **IR-T6b** (IR13/IR15/IR17): preparador por entradas fijadas, reconstrucción
  desde el conjunto exportado, writer exclusivo y CLI con errores acotados.
- [x] **IR-T6c** (IR14–IR18): fixtures asimétricos de dos formas y paletas,
  valores esperados de UV/color/alpha/orden, metadatos desconocidos, negativos
  de identidad/formatos/topología/capturas y reconstrucción sin fuentes.
- [x] **IR-T6d** (IR13/IR15/IR18): convertir ambas extracciones privadas,
  releer y comparar todos los adjuntos/documentos; SGM/STX iguales al build
  `764be66e7762`. Registrar hashes, validación local y límites en el backlog.

F03.04 global permanece abierto: colisión, cámara y audio requieren perfiles
posteriores. Un circuito jugable y SH3P no quedan completados por este perfil.

[Ejecución y comprobantes](../docs/execution/f03-04-map-intermediate.md):
504 tests, cobertura combinada 98,15 %, 17 archivos y manifiestos A/B iguales;
SGM/STX idénticos a la entrega física fijada. Sin nuevo build ni prueba física.
