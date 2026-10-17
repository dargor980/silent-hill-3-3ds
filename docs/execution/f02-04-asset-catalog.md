# F02.04 — catálogo interno con identidad y hashes

17 de octubre de 2026. **Completada para los 61 MFA con estructura aceptada del perfil europeo**: 1740 recursos, 66 bloques y 1.562.367.840 bytes de payload catalogados. Dos ejecuciones de solo lectura produjeron documentos idénticos byte a byte. [Ticket](../specs/sh3-3ds/tasks/F02.md#f0204) y [contrato EARS A01-A11](../../schemas/asset-catalog-v1.md).

Cada recurso tiene ID estable, origen, contenedor, bloque/ordinal, offsets MFA/ISO, tamaño, SHA-256 y nombre ASCII conservado como metadato privado. Los hashes identifican rangos; no demuestran que sean texturas, geometría, lógica o audio válidos. Todos los tipos semánticos siguen `unknown` y sus dependencias `not_inspected`, con lista conocida vacía. No se exportaron recursos ni se ejecutó contenido del juego.

## Resultado y límites

| Unidad | Resultado |
|---|---|
| Candidatos MFA seleccionados | 62: 59 B8 y 3 D8 |
| Contenedores completos aceptados | 61: 59 B8 y 2 D8 |
| Bloques / recursos | 66 / 1740 |
| Bytes de los recursos aceptados | 1.562.367.840 |
| Contenedor desconocido | XBG0: `MFA_NAME`, codificación no resuelta |
| Otros archivos ISO fuera del alcance interno | 51, incluidos los 35 AFS |
| Extracción / decodificación | `not_performed` / `not_performed` |
| Capacidades del perfil | Vacías, sin cambios |

Cada resultado de contenedor coincide exactamente con su sondeo seleccionado de [F02.03](f02-03-container-variants.md), incluido el rechazo de XBG0. Se reconciliaron cantidades y bytes por contenedor, IDs únicos y recalculados, offsets absolutos/relativos y hashes de longitud válida. No se sumaron entradas parciales del contenedor rechazado. La comparación y los hashes de los artefactos están en `build/f02-04/reconciliation.json`.

XBG0 sigue fallando en bloque 4, base 65.947.648, entrada 43/ordinal 237; nombre de 33 bytes con 8 no ASCII. Shift-JIS y CP932 recuperan los mismos bytes, sin evidencia para elegir una codificación. Su diagnóstico conserva estadísticas y posición; no publica el nombre. Resolverlo exige una instancia propia con contrato y fixtures. El catálogo tampoco inspecciona entradas AFS ni resuelve dependencias entre recursos. Q05/G02 permanecen abiertos.

## Identidad y custodia

Imagen de 3.586.785.280 bytes, SHA-256 `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`; perfil `ps2-sles-51434-9a94b95e777dae42`, SLES-51434/PAL 1.02. Cada ejecución verificó la imagen completa y el conjunto exacto de archivos/tamaños/hashes del perfil antes de interpretar MFA, y comprobó estabilidad al cerrar la ISO.

Todos los archivos de esta tabla están ignorados bajo `reports/local`:

| Archivo | Tamaño | SHA-256 del archivo |
|---|---:|---|
| `europe-profile-identified.json` | 17.037 bytes | `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9` |
| `f02-04-selection.json` | 10.727 bytes | `d4531ea51e5be95f5e982ba1c815185d9a23e4896e6720350467f4dc62ce00c2` |
| `f02-04-asset-catalog.json`, `f02-04-asset-catalog-repeat.json` | 1.838.826 bytes cada uno | `39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d` |

La selección se preparó con los 59 B8 y 2 D8 aceptados en F02.03, comprobando los hashes de esos informes y que sus conjuntos fueran disjuntos. Se añadió XBG0/D8 para conservar la hipótesis y el rechazo conocidos. Cada elección copia ruta/tamaño/SHA-256 del perfil canónico. El código exige que estén todos los MFA, rechaza duplicados y vuelve a validar sus bytes; no acepta el sondeo histórico como sustituto de la lectura actual.

Digest **canónico** de selección: `96245ed121887fbed7f7344ba5b69311a789a2f99809fc94bfd5bdb6d8c7f8a0`, calculado según A09; difiere intencionalmente del hash del archivo JSON. El catálogo no incluye fechas ni rutas del host, y su orden es estable aun permutando la selección.

Los nombres de recursos solo se guardan en metadatos privados; no se usaron para crear rutas ni se copiaron a fixtures, documentación o CI. Los hashes se calcularon sin exportar payloads. No se ha configurado una raíz externa de extracción; será necesaria en F02.05. Los informes anteriores permanecen intactos.

## Implementación y SOLID

`asset_selection` valida el contrato de selección y su digest. `mfa.parse_layout` comparte el único recorrido estructural con los sondeos anteriores y entrega descriptores congelados solo después de validar toda la cadena. `asset_catalog.collect_assets` coordina inventario, parser e identidad mediante `AssetReader`; la CLI compone argumentos, ISO y escritura exclusiva del JSON tras el cierre estable.

`IsoImage.hash_range` abre cada miembro una vez por recurso. `fingerprint_range` expone un EOF lógico para reutilizar el hashing por bloques de hasta 1 MiB, sin consumir bytes vecinos. Acepta lecturas cortas positivas, detecta truncamiento/exceso y trata rangos vacíos sin leer. Las ubicaciones se validan antes de leer. El límite global de 100000 recursos complementa los límites por contenedor existentes.

Un error estructural conserva el contenedor como desconocido y descarta sus descriptores. Un error de identidad, transporte, hashing, presupuesto o estabilidad aborta el catálogo. Los IDs derivan de origen/posición y distinguen recursos con bytes iguales. El parser desconoce filesystem; el coordinador funciona con lector de memoria o ISO bajo el mismo contrato. No se añadieron dependencias externas ni se adoptó el extractor candidato.

## Pruebas y pipelines

**582/582 pruebas Python aprobadas**, incluidas **89 nuevas**. Antes de la suite completa también pasaron 178 regresiones de MFA/variantes/ISO. Las nuevas cubren selección inválida/duplicada/incompleta/desactualizada, orden de selección, IDs distintos para bytes iguales, offsets y hashes contrastados en ISO sintética, rangos vacíos, lectura acotada y una apertura por recurso, fallos intermedios, parser con error tardío sin aceptación parcial, límite global, salida existente, identidad alterada, estabilidad y repetibilidad CLI.

Cobertura: **1208/1239 líneas (97,50 %)** y **434/452 ramas (96,02 %)**. Selección, parser MFA y hashing tienen 100 % de líneas/ramas. El gate independiente exige ≥80 % en ambas métricas. Ruff check/format y controles de arquitectura/custodia/trazabilidad se registran en `build/f02-04/verification.json` y `quality.log`.

La primera suite pasó 581 casos y rechazó custodia del informe creado simultáneamente. El control obtiene primero una lista de ignorados y después recorre el árbol; su contrato requiere un árbol estable. Se confirmó la exclusión Git de ambos catálogos y se repitió la suite tras terminar las escrituras: 582 aprobadas, sin modificar el control ni sus reglas. Se conserva el intento fallido como `initial-python-tests.log`, `initial-test-command.json`, `initial-pytest.xml` y cobertura `initial-*` en `build/f02-04`.

Entorno: macOS 26.5 ARM64, Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0, Ruff 0.17.1, pytest-cov 7.1.0 y coverage 7.16.2. Logs, JUnit, cobertura JSON/XML y comandos están en `build/f02-04`. El job `quality` existente descubre los casos nuevos y usa solo fixtures propios; no se modificó el workflow ni se ejecutó CI remota. No cambió C++/ARM, por lo que no se repitieron sus builds ni se atribuye prueba física; G01 sigue pendiente.

## Reproducción y siguiente trabajo

Desde la raíz, con un destino nuevo:

```sh
rtk proxy .venv/bin/python -m tools.inspectors.asset_catalog \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --profile reports/local/europe-profile-identified.json \
  --image-sha256 9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91 \
  --selection reports/local/f02-04-selection.json \
  --output reports/local/f02-04-asset-catalog.json
```

Repetir con una salida nueva `-repeat.json`; los informes existentes se rechazan. Los dos comandos y sus resultados están en `build/f02-04/catalog-commands.json`.

La siguiente tarea es [F02.05](../specs/sh3-3ds/tasks/F02.md#f0205): implementar exportación acotada por ID y repetirla en dos directorios externos vacíos. El ticket detalla contrato, ubicación, presupuesto, fallos, verificación y evidencias. El mínimo medido de payload para ambas copias es **3.124.735.680 bytes**, más metadatos, asignación de bloques y margen. Se deberá indicar una raíz privada externa antes de exportar. XBG0, AFS, semántica de payloads y corpus permanecen fuera de lo acreditado; esta tarea no cierra G02.

## Identidad de fuentes

`build/f02-04/source-manifest.json`: 59 archivos, SHA-256 `488d58f53c045597066a68341206505947176efad422d7397eb7a4a18f72d000`. Registra fuentes propias, pruebas, contratos y configuración; excluye este informe para evitar autorreferencia y no incluye datos privados ni fuentes externas crudas. Los cambios permanecen sin commit.
