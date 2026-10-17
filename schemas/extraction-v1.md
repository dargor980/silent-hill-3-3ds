# Extracción repetible v1 — F02.05

Contrato de exportación de los rangos aceptados por [A01-A11](asset-catalog-v1.md). Requisitos RF02.03, RNF05.03, RNF06.01/RNF06.04/RNF06.07, RNF07.06-RNF07.09 y RNF11.05-RNF11.09; V02/V20, T01/T02. No convierte ni interpreta payloads y no concede capacidades al perfil.

## Criterios EARS

- **X01** WHEN comienza cada copia THEN el sistema SHALL verificar SHA-256 completo de ISO, perfil/selección y catálogo regenerado contra el catálogo esperado antes de escribir sus recursos.
- **X02** IF el catálogo no coincide con su SHA-256 esperado, excede 128 MiB, contiene JSON inválido/claves duplicadas o difiere del regenerado THEN la operación SHALL rechazarse.
- **X03** WHEN selecciona destino THEN el sistema SHALL exigir raíz absoluta existente, externa y no relacionada con el checkout, sin componentes simbólicos ni traversal; SHALL crear una sesión nueva exclusiva y dos directorios de copia nuevos.
- **X04** IF el destino está ocupado, fue sustituido, contiene enlaces/archivos extra o carece de espacio THEN el sistema SHALL rechazarlo sin sobrescribir datos previos.
- **X05** WHEN reserva espacio THEN el sistema SHALL exigir dos veces el payload, más 8192 bytes por recurso/copia y un margen de al menos 64 MiB o 10 % del payload conjunto, el mayor. La estimación SHALL no sustituir el manejo de ENOSPC.
- **X06** WHEN copia un recurso THEN el sistema SHALL crear exclusivamente `<64 hex del ID>.bin`, copiar exactamente el rango con bloques de hasta 1 MiB, completar escrituras cortas positivas y rechazar EOF/exceso/escritura sin progreso.
- **X07** WHEN verifica una copia THEN el sistema SHALL releer cada archivo regular sin seguir enlaces, comprobar tamaño/SHA-256 y exigir el conjunto exacto de archivos esperados, incluidos recursos vacíos.
- **X08** IF falla lectura, escritura, hash, estabilidad de origen/destino o publicación de recibo antes de confirmar el par THEN la sesión SHALL no anunciar éxito; conservar parciales y registrar fallo cuando sea posible, sin borrado automático ni reintento sobre el mismo destino. La limpieza posterior a una confirmación publicada se rige por H07 de F02.06.
- **X09** WHEN termina cada copia THEN el sistema SHALL emitir su recibo verificado solo después del cierre estable de la ISO. WHEN verifica ambas copias de nuevo THEN SHALL publicar el recibo final con igualdad de listas/tamaños/hashes contra el catálogo.
- **X10** WHILE registra evidencia THEN el sistema SHALL conservar versión/hashes/origen, conjunto de recursos y exclusiones; SHALL mantener XBG0, archivos fuera del alcance y semántica sin inspeccionar como pendientes.
- **X11** WHEN ejecuta CI THEN SHALL usar datos propios y destinos temporales; SHALL no leer ni publicar originales, destinos privados o nombres del juego.

## Diseño y secuencia

`transfer.copy_exact` es una operación de streams sin paths. `IsoImage.copy_range` valida confinamiento y abre una vez por recurso. `private_output.PrivateOutput` controla directorios, archivos, espacio y recibos usando descriptores de directorio POSIX y `O_NOFOLLOW`/creación exclusiva. `extract_assets` compara el catálogo regenerado, coordina dos aperturas independientes de ISO y compone la CLI. No duplica el parser ni interpreta nombres.

La CLI recibe ISO, perfil, SHA-256 de imagen, selección, catálogo, SHA-256 del archivo de catálogo, raíz privada existente y nombre de sesión. Los argumentos son explícitos; no crea raíces ni deriva destino del catálogo. La raíz se recorre componente a componente sin enlaces; las pruebas usan la ruta física de sus temporales. Todas las plataformas de ejecución soportadas aquí son POSIX (host macOS/Linux).

Carga acotada del catálogo y verificación de su hash → apertura de raíz → primera identidad/catálogo regenerado → comparación JSON canónica estricta (distingue booleanos, números y cadenas) → plan de recursos/espacio → reserva exclusiva de sesión y `copy-a`/`copy-b` → copia y relectura A → cierre ISO → recibo A → repetir verificación de fuente/copia/cierre/recibo B → relectura de ambas copias y comprobación de destino → recibo final. El plan rechaza IDs duplicados, tamaños inválidos y catálogo sin recursos.

Cada hash de copia debe coincidir durante streaming y al releer. La lectura de archivo verifica metadatos antes/después. Los directorios permanecen anclados a descriptores y se comprueba su vinculación a las rutas al terminar. Esto no promete protección frente a un actor con acceso de escritura concurrente después de la verificación ni durabilidad ante pérdida de energía.

## Destino y estados

`<raíz>/<sesión>/copy-a/<id>.bin` y `copy-b/<id>.bin`, archivos modo 0600 y directorios nuevos 0700. Sesión de 1..64 caracteres `[a-z0-9][a-z0-9_-]*`. Rechazar una sesión existente aun vacía. Las dos copias son hermanas distintas por construcción. Los nombres de origen solo existen en el catálogo privado; no se utilizan como rutas.

Recibos en la sesión: `started.json`, `copy-a.json`, `copy-b.json`, `verified.json`; `failed.json` si la ejecución falla después de reservar la sesión y el almacenamiento lo permite. Un proceso interrumpido puede dejar únicamente `started.json` y parciales: ausencia de `verified.json` implica par no verificado. El reintento exige otra sesión; no se limpian originales ni resultados previos.

Publicación de JSON: escribir completo y sincronizar un archivo exclusivo `.<nombre>.pending`, después crear el nombre final mediante hard link exclusivo. El archivo de preparación se conserva para diagnóstico; solo el nombre final cuenta como recibo publicado. Si no hay espacio ni siquiera para el fallo, stderr/stdout y ausencia del recibo final conservan el rechazo. No usar los recibos como garantía de durabilidad física.

Esquema 1 de recibos: herramienta `sh3-mfa-extract` versión 1 y pycdlib; SHA-256 del catálogo; identidad `source`, digest canónico `selection`; recursos ordenados por ID con ID/ruta relativa, contenedor, offset, tamaño y SHA-256; resumen de catálogo y exclusiones por IDs/códigos. Estados `started`, `copy_verified`, `verified` o `failed`. El recibo final conserva ambos inventarios iguales; no contiene payloads ni rutas absolutas/fechas. `payload_decoding=not_performed`, `capabilities=[]`. La repetibilidad es del conjunto aceptado, no del disco completo.

## Pruebas

Datos propios B8/D8 multibloque, vacío, hashes iguales con IDs distintos y contenedor desconocido; comparación memoria/ISO y dos sesiones. Alteraciones de catálogo/perfil/selección/imagen; límites de carga; destinos relacionados, traversal/enlaces, colisiones y sustitución; archivos extra/faltantes, symlink/hardlink/FIFO; lecturas/escrituras cortas y fallos intermedios/ENOSPC; corrupción al releer, cierre inestable, fallos de recibo y recursos parciales. Suite Python, cobertura separada ≥80 % líneas/ramas, Ruff y custodia sobre árbol estable.

F02.06 añade [H01-H07](extraction-hardening-v1.md) y concreta el cierre posterior a confirmación: la CLI conserva `status=verified`/exit 0 y añade `cleanup_warning=OUTPUT_CLOSE_ERROR` si falla únicamente la liberación de directorios después de publicar el recibo final. Se conservan esquemas y campos de recibos; el parser y la transferencia de bytes no cambian.
