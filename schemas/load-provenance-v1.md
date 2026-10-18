# Procedencia de carga — LP01–LP10

F02.07/origin/load-provenance. La primera unidad implementa anclaje del origen,
modelo puro de linaje y plan de fronteras. La adquisición real y su adaptador
de evidencia son unidades separadas y necesarias para cerrar la procedencia.

## Requisitos EARS

- **LP01:** CUANDO prepare el origen, el adaptador DEBERÁ fijar por hash ISO,
  catálogo, contenedor, entrada y recurso, volver a interpretar el índice MFA
  y comprobar su rango contra el candidato y ambas extracciones privadas.
  Los nombres SHALL NOT constituir evidencia semántica.
- **LP02:** CUANDO modele eventos, el validador DEBERÁ exigir una identidad de
  sesión/entorno/proceso, secuencias consecutivas desde uno y ciclos EE u64
  crecientes; DEBERÁ rechazar entradas mal tipadas, campos extra y mezclas.
- **LP03:** CUANDO reciba una lectura, DEBERÁ comprobar identidad de archivo,
  tamaño solicitado/recibido y límites del archivo y RAM. DEBERÁ contrastar
  la intersección con los bytes del candidato y atribuir solo esa intersección.
  Los bytes ajenos al candidato SHALL NOT presentarse como verificados.
- **LP04:** CUANDO reciba una copia directa, DEBERÁ exigir igualdad de los bytes
  observados en origen y destino y conservar únicamente el linaje previamente
  conocido del origen. Una copia de bytes iguales sin origen conocido SHALL
  NOT crear procedencia. Un codec o transformación no soportada DEBERÁ fallar.
- **LP05:** CUANDO un evento sobrescriba un rango, DEBERÁ invalidar su linaje
  anterior antes de asignar el nuevo. Las copias solapadas DEBERÁN tomar el
  linaje del preestado, equivalente a una copia temporal, sin inferir que el
  juego usa memmove. Las escrituras externas declaradas solo invalidan.
- **LP06:** CUANDO reciba la entrega final, DEBERÁ comprobar longitud, bytes y
  correspondencia byte a byte con los offsets del candidato. DEBERÁ rechazar
  huecos, bytes de origen distinto, entrega ausente, duplicada o no final.
- **LP07:** MIENTRAS procese, DEBERÁ limitar a 256 eventos, 4 KiB por candidato
  y por evento, 16 KiB de bytes con linaje retenidos y 60 segundos de ciclos EE.
  RAM física normal DEBERÁ limitarse a 32 MiB, sin aceptar alias virtuales.
  Los eventos DEBERÁN consumirse incrementalmente, sin guardar payloads en
  el informe. El adaptador DEBERÁ acotar también tiempo de pared y slots.
- **LP08:** CUANDO publique el modelo, DEBERÁ indicar que valida efectos
  suministrados: no autentica una ejecución, una lectura de disco, su orden
  completo ni traducciones. DEBERÁ mantener vacíos vínculos/capacidades y
  pendiente la procedencia real incluso si acepta fixtures sintéticos.
- **LP09:** CUANDO adquiera evidencia real, el adaptador DEBERÁ verificar cada
  evento contra fronteras de código fijadas, identidad de archivo y rango,
  estado/PC/registros/bytes y observación AC/MP de todas las páginas relevantes.
  DEBERÁ normalizar a offsets físicos solo con esa prueba, observar antes de la
  lectura y prohibir restauraciones dentro de la serie. La entrada SRC53 ya
  cargada SHALL NOT satisfacer este requisito. Una dirección encontrada en
  pila o tabla SHALL NOT convertirse por sí sola en llamada ejecutada.
- **LP10:** CUANDO cierre una unidad, DEBERÁ conservar fallos y datos privados,
  producir dos informes deterministas y ejecutar pruebas/gates del pipeline.
  DEBERÁ mantener F02.07/Q05/G02, semántica y hardware pendientes hasta disponer
  de evidencia propia; código del juego y estados SHALL NOT publicarse.

## Diseño

`load_lineage` es una función pura sobre dataclasses inmutables, un candidato
de bytes fijados y un iterable de eventos. Un mapa acotado relaciona cada byte
físico conocido con su offset en el candidato. Las lecturas introducen linaje,
las copias lo trasladan, las sobrescrituras lo invalidan y la entrega exige una
cadena completa. La igualdad final es necesaria, pero insuficiente.

Este modelo no lee archivos, no controla PCSX2, no interpreta instrucciones ni
valida mapas. La custodia/ISO/MFA reutiliza adaptadores existentes. Un adaptador
futuro deberá construir los eventos a partir de evidencia LP09; no se acepta
un booleano de JSON como sustituto de esa validación. Los eventos fuera del
fragmento candidato se consideran desconocidos, aun si se conservan sus bytes
temporalmente para comprobar una copia. No se añade un codec por conjetura.

## Unidades y aceptación

- [x] LP-A: anclaje ISO/MFA/extracciones y fronteras candidatas, con dos informes.
- [x] LP-B: modelo de linaje y pruebas sintéticas positivas/adversas LP02–08.
- [ ] LP-C: adaptador LP09 y selección de fronteras de lectura/transferencia.
- [ ] LP-D: sesión anterior a la carga, dos reimportaciones y cierre real LP10.

LP-A/B se documentan en [SRC55](../docs/execution/f02-07-load-provenance-plan.md).
La comparación del índice y las ventanas de código no identifica todavía una
lectura completada: LP-C debe distinguir búsqueda/caché, lectura y transferencia
antes de producir eventos `Read` del modelo.

LP-A/B no cierran LP-C/D. La siguiente sesión deberá fijar hasta 48 adquisiciones,
256 hits, 60 segundos activos, 3.600 segundos de pared, 8 GiB de etapa y 10 GiB
libres mínimos; si las fronteras exigen más capturas, se rediseña el plan antes
de arrancar. Estos son presupuestos locales de trabajo, no límites de PCSX2.
