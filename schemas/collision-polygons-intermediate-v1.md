# CF-T7 — Intermedio de recursos poligonales CLD

2026-10-23. Contrato **CPI01–CPI14**; CF-T7a–e completadas. Perfil
`ps2-cld-polygons-intermediate-v1`, convertidor `cld-polygons-lossless-v1`,
decoder `ps2-cld-polygons-v1`. RF02.04/RF02.05; preparación para RF05.01,
sin acreditar respuesta física. El [adaptador puro CF-T7b](../docs/execution/f03-04-collision-polygons-intermediate.md)
implementa las tres APIs. [CF-T7c](../docs/execution/f03-04-collision-polygons-preparation.md)
integra el preparador, custodia y writer exclusivo.
[CF-T7d](../docs/execution/f03-04-collision-polygons-intermediate-verification.md)
añade oráculo independiente, batería ampliada y gates permanentes.
[CF-T7e](../docs/execution/f03-04-collision-polygons-publication.md) publica A/B,
verifica reconstrucción sin fuentes y fidelidad externa; cierra este perfil estructural.
La comprobación inicial de ejemplos está en el
[informe CF-T7a](../docs/execution/f03-04-collision-polygons-intermediate-contract.md).

## Historia, decisión y alcance

Como implementador del port, necesito transportar recursos de colisión con
sus bytes completos, interpretación estructural y procedencia para poder
reconstruirlos desde un paquete sin volver a consultar ISO, extracciones o RAM.

Se crea un perfil separado de [IR-T7](collision-intermediate-v1.md). Ese
perfil de registros permanece cerrado e intacto; sus punteros no se
reinterpretan como polígonos. El nuevo intermedio conserva **todos** los
recursos seleccionados, incluidos no soportados y rechazados por el decoder.
No convierte un rechazo estructural en una importación de geometría válida.

La vista CP no conserva todo el padding. Por ello, el buffer íntegro es
la autoridad para reconstruir el CLD; la vista es derivada y comprobable.
Cada recurso tiene su propio JSON de vista: agregar las vistas de los 233
recursos aceptados en un solo árbol arriesga los límites del codec compartido.
No se aumenta ese límite para acomodar el corpus. Tampoco se deduplican
recursos por contenido: dos IDs distintos pueden tener bytes iguales.

Se distinguen tres resultados: coherencia estructural del paquete,
identidad frente a fuentes fijadas y evidencia histórica de enlace con RAM.
Un paquete autoconsistente no autentica por sí solo un catálogo externo.
Las formas dinámicas, la variante activa de 48 bytes, triangulación, escala,
origen aplicado, materiales físicos, solver, daño/muerte y SH3P quedan fuera.

## Requisitos EARS

- **CPI01:** CUANDO se importa una selección, el preparador DEBERÁ cotejar
  IDs, tamaños, hashes y procedencia contra catálogo, recibo de extracción y
  auditoría fijados antes de decodificar; una discrepancia DEBERÁ abortar
  la publicación, sin reclasificarla como rechazo del decoder.
- **CPI02:** CUANDO se conserva un recurso, el paquete DEBERÁ guardar su
  buffer completo, incluidos bytes opacos, padding, formas sin referencias,
  listas compartidas y registros no soportados; no DEBERÁ reconstruirlo
  serializando únicamente la vista.
- **CPI03:** CUANDO el decoder termina, el adaptador DEBERÁ registrar su
  clasificación y primer código exactos; una aceptación DEBERÁ tener vista
  completa y los otros resultados DEBERÁN tener vista nula, sin subconjuntos.
- **CPI04:** CUANDO se escribe una vista aceptada, DEBERÁ conservar todos los
  campos CP, tipos JSON, palabras f32, cero negativo, orden y multiplicidad,
  sin transformar coordenadas ni eliminar registros.
- **CPI05:** CUANDO se reconstruye, el lector DEBERÁ verificar inventario,
  tamaños, hashes, perfiles y relaciones, volver a decodificar cada buffer
  y comparar vista o error con lo declarado antes de devolver archivos.
- **CPI06:** MIENTRAS reconstruye desde el paquete, el adaptador DEBERÁ
  operar solo sobre los bytes suministrados, sin abrir fuentes, seguir
  punteros EE, consultar red, ejecutar PCSX2 o necesitar scripts locales.
- **CPI07:** CUANDO conserva procedencia, DEBERÁ preservar la fila completa
  del catálogo, incluidos campos desconocidos, y los pins de los documentos
  históricos; no DEBERÁ incluir rutas del host, run-id, timestamp o etiqueta
  A/B en los bytes lógicos del paquete.
- **CPI08:** CUANDO incluye enlaces de escena, DEBERÁ identificarlos como
  referencias a la auditoría histórica, conservar captura/fase y recurso,
  y no afirmar que reconstruir CLD vuelve a verificar RAM o continuidad.
- **CPI09:** SI faltan/sobran archivos, se repiten IDs/claves JSON, cambian
  tipos, se exceden presupuestos o hay una incoherencia de hashes/vistas,
  DEBERÁ rechazar el paquete completo sin salida parcial, también bajo `-O`.
- **CPI10:** CUANDO publica, el writer DEBERÁ usar un directorio privado
  exclusivo, relectura de hashes e inventario exacto, y enlazar el manifiesto
  final solo después de validar y reconstruir el conjunto; un fallo DEBERÁ
  impedir una entrega declarada completa y preservar los originales.
- **CPI11:** CUANDO compara A/B, la auditoría DEBERÁ reconstruir cada paquete
  sin fuentes y después cotejarlo con su extracción fijada; DEBERÁ comparar
  todos los archivos/manifiestos, incluidos recursos no aceptados.
- **CPI12:** CUANDO informa resultados, DEBERÁ mantener `capabilities=[]`,
  respuesta física y nueva ejecución desactivadas, y distinguir registro
  histórico, buffer reconstruido, vista derivada y operaciones no soportadas.
- **CPI13:** CUANDO valida la implementación, CI DEBERÁ usar solo datos propios,
  oráculo independiente, controles de fallo compartido, aislamiento e I/O;
  DEBERÁ exigir ≥80 % de líneas y ramas de cada módulo nuevo además del gate global.
- **CPI14:** SI una ampliación necesita geometría parcial, nuevas formas,
  evidencias RAM embebidas o capacidades físicas, DEBERÁ introducir otro
  contrato/versionado; no DEBERÁ modificar silenciosamente este perfil.

## Formato exacto del paquete

El paquete es un directorio plano. Inventario lógico: `intermediate.json`,
un `source-<hex-id>.bin` por recurso y un `polygons-<hex-id>.json` por
aceptado. `<hex-id>` es el sufijo de 64 dígitos hexadecimales minúsculos de
`asset:<hex-id>`, nunca el nombre histórico ni una ruta suministrada.
No se admite deduplicación por SHA ni referencias a archivos de otro paquete.

El manifiesto de transporte `manifest.json` se añade después. Con N recursos
y A aceptados hay **1+N+A archivos lógicos**, más el manifiesto. Para el
corpus CF-T6, CF-T7e publicó y comprobó 519 archivos lógicos y un manifiesto
por copia. El auxiliar del writer no pertenece al inventario lógico.

JSON lógico: codec [intermediate_json](../tools/pipeline/intermediate_json.py),
UTF-8, claves ordenadas, ASCII escapado, separadores compactos, una LF final,
números finitos. La raíz y las vistas almacenadas DEBERÁN ser canónicas;
el lector rechaza otra codificación en este perfil. Comparación exacta por
tipo y valor; `True`, `1` y `1.0` son distintos, al igual que `-0.0` y `0.0`.
El CLD se reconstruye byte por byte; el JSON original del catálogo no se
reconstruye con su espaciado, solo se conserva íntegra cada fila lógica.

### Raíz `intermediate.json`

Claves exactas: `schema_version`, `profile`, `converter`, `decoder`,
`conventions`, `provenance`, `resources`.

| Campo | Tipo y regla |
|---|---|
| `schema_version` | Entero exacto `1`. |
| `profile`, `converter`, `decoder` | Strings constantes indicados al inicio. |
| `conventions` | Objeto constante de la tabla inferior; sin extensiones. |
| `provenance` | `source_identity`, `anchors`, `scene_evidence`. |
| `resources` | Lista de 1..285 filas, ordenada por `id`, sin IDs repetidos. |

`conventions` tiene exactamente:

```json
{"byte_order":"little","coordinates":"source_untransformed","raw_authority":"complete_source_buffer","view":"complete_cp_v1","nonaccepted":"raw_and_error_only","scene_links":"historical_reference_only","state":"structural_observation","capabilities":[]}
```

`provenance.source_identity` tiene `kind`, `profile_id`, `image_id`, `crc`:

- `kind=private_eu`: perfil `ps2-sles-51434-9a94b95e777dae42`, imagen
  `iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`,
  CRC entero `0x5088CCDB`.
- `kind=synthetic`: perfil `synthetic-cld-v1`, imagen `synthetic:<64hex>`,
  `crc=null`; solo fixtures propios. No acredita edición ni capturas reales.

`anchors` tiene exactamente `catalog`, `extraction_receipt`, `classification_audit`,
cada uno con `size` entero positivo y `sha256` de 64 hex minúsculos.
Son pins de los documentos originales; **no se recalculan desde filas
proyectadas**. Esos documentos no son adjuntos ni reconstruibles desde el
paquete. Su verificación contra archivos externos compete al preparador.
`scene_evidence` es la constante `historical_report_only`.

Cada fila de `resources` tiene claves exactas `id`, `catalog_entry`, `source`,
`result`, `scene_links`:

| Campo | Regla |
|---|---|
| `id` | `asset:<64hex>` único. Identidad de catálogo, no hash deducido del payload. |
| `catalog_entry` | Fila íntegra con extensiones conservadas. Campos obligatorios: `id`, `source_name`, `container_id`, `container_offset`, `size`, `sha256`, `origin`. |
| `source` | Descriptor exacto `file/size/sha256`; nombre derivado del ID. |
| `result` | `classification`, `decoder_code`, `view`; sin extensiones. |
| `scene_links` | Lista ordenada por slot de referencias históricas, puede ser vacía. |

`catalog_entry.id/size/sha256` deben coincidir con fila y descriptor fuente.
`origin` conserva sus extensiones y contiene `image_id/profile_id` iguales
a la identidad raíz. `source_name` es string no vacío ≤256 caracteres;
`container_id=entry:<64hex>`, `container_offset` entero 0..2^64−1. La ubicación
es procedencia; no se reconstruye el contenedor MFA ni se calculan IDs nuevos.
Los demás campos se preservan sin asignarles semántica adicional. En todo
el árbol se rechazan rutas absolutas POSIX/Windows y `file:` según la política
del intermedio existente; una extensión prohibida causa error, no su eliminación.

Clasificación:

| `classification` | `decoder_code` | `view` |
|---|---|---|
| `accepted` | `null` | Descriptor `file/size/sha256` de la vista completa CP canónica. |
| `unsupported` | `CP_NONPOLYGON_UNSUPPORTED` o `CP_VARIANT_UNSUPPORTED` | `null`. |
| `rejected` | Otro código CP alcanzable con un `bytes` no vacío ≤65.536 | `null`. |

Los códigos son los del contrato CP; `CP_INPUT` no puede representar un
archivo publicado. No se aceptan códigos arbitrarios ni errores Python como
clasificación. Un recurso truncado no vacío puede conservarse como `rejected`;
un archivo vacío o mayor del presupuesto de transporte aborta la selección
antes de publicar. Que un archivo no sea soportado no valida sus campos
posteriores al primer error. Volver a decodificar DEBERÁ reproducir ese código.

### Enlaces históricos de escena

Cada enlace tiene claves exactas `slot`, `phase`, `state`, `receipt`, `stage`,
`room`, `resource_pointer`, `query_cell`, `pc`, `cycle`.
`state/receipt` son pins `size/sha256`; los estados no están embebidos.
Slot entero 1..99; sin duplicados globales; fase entre `control_puzzle`,
`continuous_post_phase`, `restored_diagnostic`; etapa 0..255; sala y PC u32;
ciclo u64; puntero positivo con `puntero+source.size ≤32 MiB`; celda 0..15.
Un enlace requiere un recurso aceptado. Sintéticos usan `scene_links=[]`.
Ninguna dirección se sigue durante reconstrucción.

La receta privada inicial conserva exactamente los 30 enlaces de CF-T6:
02/control/`tp1e.cld`/sala `0xEA` y 08–35/continuos más 36/diagnóstico/
`tp1d.cld`/sala `0xEB`; etapa `0x23`, celda 0, pins/PC/ciclo/punteros del
informe fijado. La receta verifica cada campo contra ese informe; el lector
del paquete solo verifica tipos, límites y enlaces internos. No presenta
esas referencias como una segunda lectura de RAM ni como reconstrucción
del estado de PCSX2. Las otras 283 filas tienen lista vacía.

### Manifiesto y determinismo

Campos exactos: `schema_version=1`, `scope=private_cld_polygons_intermediate`,
`profile`, `converter`, `state=structural_observation`, `capabilities=[]`,
`new_vm_execution=false`, `collision_response_verified=false`,
`scene_link_rechecked=false`, `original_container_rebuild=false`,
`counts={resources,accepted,unsupported,rejected}` y `files`.
`files` está ordenado por nombre y contiene descriptores `file/size/sha256`
de todos los archivos lógicos, nunca del propio manifiesto.

Se conserva la codificación del writer existente: claves ordenadas,
`indent=2`, ASCII escapado y LF final; solo valores validados/constantes.
El lector exige esa codificación. Los recuentos se recalculan desde las filas.
El writer compartido deja `.manifest.pending.json` como enlace auxiliar:
el lector de directorio puede admitirlo **solo si es archivo regular con bytes
idénticos a `manifest.json`**; no es parte del inventario lógico ni satisface
la presencia del manifiesto final. Cualquier otro extra aborta la carga.
Las APIs puras reciben el inventario lógico, sin ese auxiliar.

A/B usan los mismos pins históricos y no incluyen rutas, copy-label o run-id
en el contenido. La procedencia de cada ejecución se conserva en su recibo
local externo; así puede compararse el manifiesto byte por byte sin borrarla.

## Límites y errores

| Elemento | Presupuesto |
|---|---:|
| Recursos | 1..285; sin omisiones silenciosas para caber. |
| Buffer CLD transportado | 1..65.536 bytes; aceptación CP exige además 752..65.536. |
| Raíz lógica | ≤1 MiB; resto de límites del codec compartido. |
| Vista por recurso | ≤1 MiB; profundidad ≤32, ≤500.000 nodos, resto de límites IR. |
| Manifiesto | ≤256 KiB; ≤571 descriptores lógicos. |
| Suma de archivos lógicos | ≤40 MiB, sin manifiesto/auxiliar. |
| Enlaces históricos | ≤30 en total; mismos límites de árbol. |
| Estado/recibo citados | ≤64 MiB / ≤16 KiB, sin adjuntarlos. |
| Pins de catálogo/recibo de extracción/auditoría | ≤32 MiB / ≤8 MiB / ≤8 MiB. |
| Configuración local del preparador | ≤32 KiB. |

El presupuesto por archivo y el total se comprueban antes de leer/alocar
contenido excesivo. Las vistas se procesan una por una; no se construye un
árbol global de todos los polígonos. Ante exceso se aborta toda la entrega,
sin dividirla automáticamente o cambiar presupuestos de otros perfiles.

Error público de paquete: `CollisionPolygonIntermediateError(ValueError)`,
atributo `code`, texto igual al código, sin rutas/bytes originales. Orden:

1. `CPI_INPUT`: tipos de argumentos, buffers mutables o inventario no dict.
2. `CPI_BUDGET`: presupuestos de transporte; antes de parsear buffers grandes.
3. `CPI_JSON`: sintaxis/UTF-8, duplicados, no finitos, tipos JSON o no canónico.
4. `CPI_SCHEMA`: claves, versiones, convenciones, identidad, rutas, IDs/orden
   o referencias históricas mal formadas.
5. `CPI_INVENTORY`: nombres o conjunto de archivos/manifiesto inesperados.
6. `CPI_HASH`: tamaño/hash distinto del descriptor; primero raíz y luego
   archivos por nombre ascendente.
7. `CPI_CLASSIFICATION`: clasificación/código declarado distinto de CP.
8. `CPI_VIEW`: árbol de vista diferente del derivado, incluidos tipos y cero.
9. `CPI_PROVENANCE`: incoherencia fila/pin/origen o enlace con evidencia externa
   durante importación. El lector sin fuentes solo comprueba la parte interna.

Este orden se aplica a las APIs puras de paquete. El preparador comprueba
los pins externos antes de invocarlas, conforme a CPI01. Los presupuestos
de la etapa 2 se refieren a longitudes físicas; un descriptor que declara
un tamaño fuera de sus límites es metadato inválido (`CPI_SCHEMA`). Los
límites del árbol JSON se comprueban al parsearlo (`CPI_JSON`).
Cada etapa completa precede a la siguiente; dentro de recursos, orden por ID.
Las sumas declaradas del manifiesto incoherentes producen `CPI_PROVENANCE`.
Los CP capturados como resultado no se propagan como fallo de paquete.
Fallos de apertura/escritura, symlink, carrera o manifiesto final son errores
de I/O del preparador; CLI termina con 1 y emite solo tipo/código acotado.
No se convierte un fallo del oráculo en un recurso `rejected`.

## Arquitectura SOLID e interfaces

- `ps2_cld_polygons`: decoder existente, puro y sin cambios de perfil.
- `collision_polygon_intermediate`: validación, relación fuente/vista y
  reconstrucción en memoria. Reutiliza codec y checks de inventario; no
  importa scripts `build/`, rutas, emulador ni writer.
- `prepare_collision_polygon_intermediate`: custodia de entradas, proyección
  explícita de enlaces históricos, clasificación y coordinación de publicación.
- Wrapper de `private_texture_output`: nombres derivados de IDs validados;
  reutiliza escritura exclusiva/relectura/manifiesto final. Debe imponer el
  presupuesto del manifiesto de este perfil sin cambiar gates anteriores.
- Oráculo de pruebas: lector CP independiente más validación stdlib propia
  del paquete, sin importar el adaptador, constantes o serializador de producción.

Interfaces puras implementadas en
[collision_polygon_intermediate](../tools/pipeline/collision_polygon_intermediate.py):

```python
make_collision_polygons(provenance, catalog_entries, scene_links, sources) -> files
export_collision_polygons(intermediate_bytes, attachments) -> files
verify_collision_polygon_bundle(manifest_bytes, files) -> files
```

`sources` es dict exacto ID→bytes; `catalog_entries` está ordenado por ID;
`scene_links` es dict exacto ID→lista, incluso vacía. `attachments` contiene
todos los `.bin` y JSON de vista, sin raíz/manifiesto. `files` es dict nuevo
nombre→bytes de **todos** los archivos lógicos reconstruidos. Los buffers
inmutables pueden reutilizarse; las colecciones mutables no se comparten ni
se modifican. `export` regenera vistas, retorna CLD idénticos y raíz canónica
verificada. `verify_bundle` añade comprobación de manifiesto antes de exportar.

El preparador recibe `--inputs`, `--private-root`, `--run-id`. Configuración
exacta: `catalog`, `extraction_receipt`, `classification_audit` con
`path/size/sha256`, y `copy_root` absoluto. Rutas solo locales; archivos
derivados del recibo y sujetos a custodia/symlinks/cambios de lectura.
La selección inicial es el conjunto exacto de 285 IDs del CF-T6 fijado, no
un glob por extensión ni la lista de aceptados únicamente. Los dos directorios
A/B se convierten en ejecuciones separadas de esa misma receta.

Implementación CF-T7c: los tres pins están fijados en
[`collision_polygon_recipe`](../tools/pipeline/collision_polygon_recipe.py).
La configuración local puede cambiar ubicaciones, pero no elegir otra
auditoría como si fuese CF-T6; una receta distinta requiere revisión explícita.
Las dos tablas de copias del recibo se cotejan por ID, tamaño y hash antes
de leer la copia seleccionada. Los nombres se derivan del ID validado.
No se abre ninguna ruta histórica de estados/recibos: sus pins y metadatos
se proyectan desde la auditoría fijada; etapa `0x23` procede de su receta CF-T6.

[`collision_polygon_inputs`](../tools/pipeline/collision_polygon_inputs.py)
abre cada componente sin seguir symlinks, limita tamaño antes de leer y
compara descriptor, nombre, inode del padre, tamaño y tiempos de cambio.
Relee todos los documentos/CLD al terminar la preparación y de nuevo antes
de publicar; la CLI incluye la configuración en esa custodia.
`prepare_files(inputs)` no escribe; `prepare_and_write(inputs_path,
private_root, repository, run_id)` coordina la entrega.

[`collision_polygon_output`](../tools/pipeline/collision_polygon_output.py)
valida el manifiesto ≤256 KiB y reconstruye antes de crear el directorio.
Usa el writer compartido con un callback opcional antes del enlace final:
reverifica entradas, relee el directorio completo y reconstruye desde esos
bytes, coteja inventario e identidades y comprueba que el directorio siga
vinculado a su ruta. Los consumidores anteriores no cambian su comportamiento.
`read_collision_polygon_bundle(path)` exige manifiesto final, verifica el
auxiliar opcional y devuelve `(manifest_bytes, logical_files)` sin fuentes.
Los fallos dejan una entrega parcial sin manifiesto final; no se reanuda ni
borra automáticamente y un nuevo intento debe usar otro `run-id`.

El [oráculo independiente de CF-T7d](../tests/collision_polygon_package_oracle.py)
expone `inspect_package(files, manifest=None)` para reconstrucción/coherencia
y `compare_sources(files, entries, sources, provenance, scene_links)` para
fidelidad externa explícita. Solo importa stdlib y el oráculo CP; no abre
fuentes ni importa el adaptador, sus constantes o codec. Los pins internos
no sustituyen el segundo cotejo. Los gates permanentes de CI comprueban
cada uno de los cinco módulos CPI además del global y los cinco previos IR-T7/CP.

## Aceptación y tareas

- [x] **CF-T7a — Contrato y ejemplos comprobados** (CPI01–CPI14): este
  esquema, inventarios, errores y fixtures materializados; reconstrucción
  sintética independiente sin fuentes, conservación opaca y controles de
  manipulación. 24 ejemplos materializados (3 coherentes y 21 inválidos),
  comprobados en modo normal y `-O`, con acceso a archivos bloqueado durante
  reconstrucción; dos controles separan coherencia de fidelidad a fuentes.
  No equivale a integración o publicación privada.
- [x] **CF-T7b — Adaptador puro** (CPI02–CPI09/CPI12/CPI14): tres APIs y
  errores tipados implementados; fuente íntegra, vista regenerada, clasificaciones
  completas, procedencia interna y etapas globales. 139 pruebas aprobadas:
  24 ejemplos originales, fronteras/tipos/enlaces/aislamiento y `-O`, sin I/O;
  259/259 líneas y 64/64 ramas, gate local aprobado. Regresión CP/IR-T7:
  3.416 pruebas. El cotejo externo y writer corresponden a CF-T7c–e.
- [x] **CF-T7c — Preparador y writer** (CPI01/CPI07/CPI08/CPI10): pins fijos,
  filas íntegras y enlaces históricos sin rutas. Publicación exclusiva,
  presupuestos, relectura/reconstrucción y custodia hasta el precommit.
  104 pruebas propias: I/O, symlinks, sustituciones, cambios tardíos,
  concurrencia y reconstrucción sin fuentes normal/`-O`. Preparación real A/B
  solo en memoria: 519 archivos, 233/52/0 y manifiestos iguales; sin publicar
  paquetes privados ni sobrescribir IR-T7. [Evidencia](../docs/execution/f03-04-collision-polygons-preparation.md).
- [x] **CF-T7d — Oráculo y CI** (CPI05/CPI06/CPI09/CPI13): oráculo independiente
  de paquete y fidelidad externa; 279 pruebas nuevas, 78 manipulaciones,
  fallos compartidos, conservación opaca y fronteras. 102 paquetes por lector/modo
  normal/`-O` con I/O bloqueado. Gates permanentes individuales ≥80 % de líneas
  y ramas de los cinco módulos CPI, conservando global/IR-T7/CP; 30 controles
  del gate. Job de calidad verificado localmente: 8.829 pruebas principales,
  cero fallos/skips; CI remoto no ejecutado. [Evidencia](../docs/execution/f03-04-collision-polygons-intermediate-verification.md).
- [x] **CF-T7e — Publicación privada y reconstrucción** (CPI01/CPI05–CPI12):
  A/B publicados; 519 archivos lógicos y manifiestos idénticos byte por byte.
  Ocho procesos A/B × producción/oráculo × normal/`-O`, sin accesos externos
  durante reconstrucción. Cotejo íntegro posterior de CLD, filas, vistas,
  procedencia y 30 referencias históricas; 233/52/0 reproducidos y 575 entradas
  de conversión intactas. Primer intento relativo rechazado antes de crear
  destino, corregido sin cambiar producción. Recibos verificables; no acredita
  nueva RAM ni física. [Evidencia](../docs/execution/f03-04-collision-polygons-publication.md).

La batería ampliada deberá cubrir 1/285/286 recursos; suma exacta y exceso
de 40 MiB; raíz/vista/manifiesto en el límite y +1; ID repetido, misma fuente
con ID distinto, archivos extra/faltantes, permutas, duplicados JSON,
booleanos frente a enteros, signo de cero, variantes/precedencia CP, pins
externos incorrectos, modos normal/`-O`, rutas/symlinks/carreras y los tres
resultados de clasificación. Los ejemplos iniciales no sustituyen esa batería.

No se crean gates para módulos inexistentes. G02/G03, F03.04 global y la
respuesta física siguen abiertos después de reconstruir este perfil.
