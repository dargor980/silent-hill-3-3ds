# F02.05 — dos extracciones verificadas

17 de octubre de 2026. **Completada para el conjunto aceptado de F02.04**: dos copias independientes de 1740 recursos de 61 MFA, con 1.562.367.840 bytes por copia. Las listas de IDs, tamaños y SHA-256 coinciden exactamente entre ambas y con el catálogo previo. [Ticket detallado](../specs/sh3-3ds/tasks/F02.md#f0205), [contrato EARS X01-X11](../../schemas/extraction-v1.md).

El usuario indicó una raíz privada externa durante esta ejecución. Se creó con modo 0700 y se usó la sesión nueva `f02-05`, con directorios hermanos `copy-a` y `copy-b`. La ubicación absoluta y el comando completo se conservan únicamente en `reports/local/f02-05-extraction.json`, ignorado. Los recursos originales extraídos permanecen fuera del checkout y no forman parte de fixtures, builds ni artefactos CI.

## Resultado observado

| Comprobación | Resultado |
|---|---|
| Aperturas independientes y verificación completa de ISO | Dos; identidad y catálogo regenerados antes de copiar |
| MFA aceptados / bloques / recursos por copia | 61 / 66 / 1740 |
| Payload por copia | 1.562.367.840 bytes |
| Payload total escrito | 3.124.735.680 bytes |
| Presupuesto requerido, incluidos metadatos y margen | 3.465.717.408 bytes |
| Archivos faltantes, extra o hashes distintos | Ninguno en el conjunto aceptado |
| Desconocidos y fuera de alcance | XBG0 y 51 archivos ISO, incluidos AFS |
| Decodificación / capacidades del perfil | No realizada / vacías |

El prechequeo observó 8.771.936.256 bytes disponibles, superior al presupuesto. La fórmula es payload de ambas copias + 8192 bytes por recurso/copia + el mayor entre 64 MiB y 10 % del payload conjunto. Es una estimación conservadora, no una reserva del filesystem; el adaptador también propaga ENOSPC durante escritura.

Cada recurso se verificó durante streaming y al releer el archivo. Después de terminar las dos copias se volvieron a leer ambos conjuntos antes de publicar `verified.json`. Los dos inventarios ordenados por ID son iguales y coinciden con F02.04. SHA-256 del JSON canónico del inventario (`sort_keys`, separadores `,`/`:`): `ed3928d2e21e51eecb30fe9b24024404e7941913acd58ab976db9428ff547d3a`.

Los recibos de copia tienen hashes distintos porque incluyen `copy-a`/`copy-b`; sus campos `files` son idénticos. No se exige que los recibos con contexto distinto tengan los mismos bytes. La reconciliación final también confirmó el conjunto de archivos regulares y sus tamaños, el origen y la ausencia de recibo fallido; evidencia en `build/f02-05/reconciliation.json`.

## Identidad y recibos

ISO europea SLES-51434/PAL 1.02, 3.586.785.280 bytes, SHA-256 `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`. Perfil `ps2-sles-51434-9a94b95e777dae42`, sin modificar; su campo histórico `extractor_version=none-inspection-only-v1` identifica el perfil de inspección. La herramienta usada aquí queda identificada separadamente en los recibos como `sh3-mfa-extract` v1, pycdlib 1.22.0; no se atribuye compatibilidad completa al perfil.

Catálogo de entrada: `reports/local/f02-04-asset-catalog.json`, SHA-256 `39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d`. Selección canónica: `96245ed121887fbed7f7344ba5b69311a789a2f99809fc94bfd5bdb6d8c7f8a0`. Los hashes restantes de perfil/selección constan en [F02.04](f02-04-asset-catalog.md). En cada copia se regeneró el catálogo completo y se comparó mediante JSON canónico estricto antes de escribir recursos.

Recibos relativos a la sesión privada:

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `started.json` | 802.702 bytes | `73404a68919e747390afb5824d41aac795f8ee1a0ca930fdebc833ecba4eb1ff` |
| `copy-a.json` | 1.304.666 bytes | `b592274b82dca1a17a9c4177d49e0649f103fcac91a2bfa4847e75efe85e420c` |
| `copy-b.json` | 1.304.666 bytes | `fe7afaacc7afc298fc4abb033ea37a68423b8cb0f09fd61ef2388a396cd7b1a5` |
| `verified.json` | 1.848.367 bytes | `74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943` |

Registro privado de ubicación/comando/resumen: `reports/local/f02-05-extraction.json`, 2124 bytes, SHA-256 `19c5e63343f7fd90898d91de1e85a09492dff77e8e324f7f6e1950a4494e4519`. El resumen técnico compartible omite la ubicación absoluta y nombres internos; los payloads nunca se incluyen en recibos.

## Implementación y SOLID

- `transfer.copy_exact` y `write_all` trabajan con streams, límites y hashes, sin conocer rutas ni MFA. Admiten lecturas/escrituras cortas positivas, rechazan ausencia/exceso de progreso y nunca consumen bytes adyacentes al rango.
- `IsoImage.copy_range` confina el rango al miembro y lo abre una sola vez por recurso. Comparte el parser/catálogo existentes mediante la coordinación, sin duplicar la interpretación de MFA.
- `PrivateOutput` posee los descriptores POSIX. Recorre componentes sin enlaces, rechaza destinos relacionados con el repositorio, reserva directorios exclusivos, crea archivos modo 0600 por ID, verifica conjuntos exactos y detecta sustitución de directorios/archivos.
- `extract_assets` depende de puertos `CopyReader`/`OutputStore`, coordina dos sesiones de lectura y compone la CLI. La verificación de fuente, catálogo y estado final queda separada de la escritura. Los dobles inyectan fallos sin modificar el código del juego ni el SDK.

Las salidas usan `<64 hex del ID>.bin`; los nombres del contenedor no se convierten en rutas del host. El sufijo `.bin` indica bytes sin interpretar, no un formato identificado. Los recursos vacíos conservan identidad y archivo vacío. Se excluye el contenedor rechazado completo, sin exportar su prefijo de entradas válidas.

Los recibos se preparan en archivos exclusivos `.<nombre>.pending`, se sincronizan y se publican mediante hard link exclusivo al nombre final. Se conserva el archivo de preparación como diagnóstico; solo el nombre final cuenta como recibo publicado. No hay sobrescritura ni limpieza automática. Un fallo conserva parciales y `failed.json` cuando puede escribirse; sin `verified.json` no hay par aceptado. No se promete durabilidad ante corte físico ni inmutabilidad frente a cambios posteriores de otro proceso.

## Batería y pipelines

**686/686 pruebas Python aprobadas**, incluidas **104 nuevas**. Cubren dos copias y sesiones repetidas con datos propios, variantes B8/D8 multibloque, vacío, IDs distintos con bytes iguales, catálogo alterado aun con hash de archivo actualizado, identidad/selección, cambio de fuente al cerrar o entre copias, rangos inválidos, copia acotada, lecturas/escrituras cortas, ENOSPC y contrato de hashes.

También se prueban raíz relacionada con checkout, traversal/componentes simbólicos, destinos ocupados/concurrentes, sustitución de raíz/sesión/copia, archivos faltantes/extra/corruptos, symlink/hardlink/FIFO, cambio durante relectura, corrupción tardía de la primera copia, fallos de recibo y publicación parcial sin éxito. Dos errores iniciales de fixture —cifra esperada de presupuesto y doble aplicado a un atributo de instancia de pycdlib de solo lectura— se corrigieron; la suite focalizada pasó después con 104 casos.

Cobertura: **1501/1533 líneas (97,91 %)** y **525/544 ramas (96,51 %)**; transferencia y adaptador de salida, 100 % en ambas. Gate independiente ≥80 %, Ruff check/format y contratos de arquitectura/custodia/trazabilidad registrados en `build/f02-05/verification.json` y `quality.log`. Logs completos, JUnit, cobertura JSON/XML, comandos y entorno se conservan en `build/f02-05`.

Entorno local: macOS 26.5 ARM64, Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0, Ruff 0.17.1, pytest-cov 7.1.0 y coverage 7.16.2. El job quality existente descubre las pruebas; las APIs POSIX usadas corresponden a hosts macOS/Linux. No cambian dependencias, workflow ni runtime C++/ARM. No se ejecutó CI remota ni hardware; G01 permanece pendiente.

## Reproducción y siguiente tarea

Con una raíz externa existente y una sesión nueva, desde el checkout:

```sh
rtk proxy .venv/bin/python -m tools.pipeline.extract_assets \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --profile reports/local/europe-profile-identified.json \
  --image-sha256 9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91 \
  --selection reports/local/f02-04-selection.json \
  --catalog reports/local/f02-04-asset-catalog.json \
  --catalog-sha256 39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d \
  --private-root /ruta/privada/externa \
  --run-id nueva-sesion
```

La ruta mostrada es un marcador; el comando real y salida exitosa están registrados. No reutilizar ni borrar la sesión `f02-05`; la CLI rechaza sesiones existentes incluso vacías. Cada repetición vuelve a necesitar espacio para ambas copias. Los únicos pasos manuales de esta ejecución fueron indicar la raíz; no se aplicaron ajustes de bytes ni herramientas GUI.

Sigue [F02.06](../specs/sh3-3ds/tasks/F02.md#f0206), detallada para mutaciones deterministas, fronteras de límites, fallos de filesystem y terminación de subprocesos con datos propios. XBG0, AFS, tipos/dependencias y corpus del slice siguen pendientes. **Esta extracción parcial repetible no cierra G02 ni demuestra contenido jugable.**

## Identidad de fuentes

`build/f02-05/source-manifest.json`: 64 archivos, SHA-256 `fb4b8d68b7a3b9ae4632960edc96f786773efa985a86ac68ee1f4b1772fe1a86`. Registra fuentes propias, pruebas, contratos y configuración; excluye este informe para evitar autorreferencia y no contiene recursos privados. Los cambios permanecen sin commit.
