# Catálogo interno de recursos v1 — F02.04

Alcance: metadatos y SHA-256 de entradas MFA B8/D8 con estructura completa validada. No extracción ni decodificación. Requisitos padre RF02.01, RF02.07, RNF06.01, RNF07.06-RNF07.09 y RNF11.05-RNF11.09; V02/V20, T01/T02. Reutiliza [M01-M08](mfa-probe-v1.md) y [MV01-MV08](mfa-probe-v2.md).

## Criterios EARS

- **A01** WHEN se solicita el catálogo THEN el sistema SHALL validar selección, SHA-256 completo de imagen, perfil PS2 y conjunto exacto de archivos/tamaños/hashes antes de interpretar recursos.
- **A02** IF la selección contiene esquema/campos/layout inválidos, rutas duplicadas/extra/faltantes o identidad desactualizada THEN el sistema SHALL rechazar la operación, sin seleccionar otro layout como recuperación.
- **A03** WHEN el parser entrega entradas THEN SHALL haber validado la cadena completa del contenedor, sin exponer descriptores parciales ni leer payloads de un contenedor rechazado.
- **A04** WHEN una entrada se cataloga THEN el sistema SHALL registrar ID estable, origen, contenedor, bloque/ordinal, offset de datos relativo al MFA y absoluto ISO, tamaño, SHA-256 y nombre ASCII original como metadato privado.
- **A05** WHEN calcula el hash de un recurso THEN el lector SHALL abrir su miembro ISO una sola vez por recurso, leer exactamente el rango validado por bloques de hasta 1 MiB y no consumir bytes del recurso siguiente.
- **A06** IF falla un hash, lectura, rango, presupuesto o estabilidad de la imagen THEN el catálogo SHALL abortar sin persistir un resultado aceptado.
- **A07** WHILE las dependencias o el tipo semántico de un recurso no están demostrados THEN su estado SHALL permanecer `not_inspected`/`unknown`; una lista vacía SHALL no certificar independencia.
- **A08** IF un contenedor tiene formato/nombre no soportado THEN el informe SHALL conservar su identidad, selección, código y contexto acotado, sin sumar sus entradas parciales. Los archivos ISO fuera de la selección SHALL figurar fuera del alcance interno.
- **A09** WHEN cambie el orden de la selección o se repita el catálogo con las mismas entradas/herramienta THEN el resultado ordenado, IDs y digest canónico de selección SHALL ser idénticos.
- **A10** WHEN persiste el catálogo THEN el sistema SHALL crear exclusivamente un JSON nuevo después de cerrar la imagen estable; SHALL no modificar originales ni crear archivos nombrados por los recursos. La CLI SHALL imprimir solo estado/conteos/errores sin nombres internos.
- **A11** WHILE construye el catálogo THEN el sistema SHALL limitarlo a 100000 recursos, además de los límites MFA existentes. La CI SHALL usar únicamente fixtures propios y mantener regresiones de sondeos y transporte.

## Selección explícita

Archivo de metadatos JSON UTF-8, máximo 2 MiB, sin claves JSON duplicadas. Claves exactas: `schema_version=1`, `image_sha256`, `profile_id`, `containers`. Perfil con ID de 1..64 caracteres `[a-z0-9][a-z0-9_-]*`; hash de 64 hexadecimales minúsculos. Lista de 1..10000 contenedores, cada uno con claves exactas `path`, `size`, `sha256`, `layout` (`b8` o `d8`). Rutas relativas seguras, únicas sin distinguir mayúsculas; tamaño entero 0..2^63-1, no booleano. El conjunto debe coincidir exactamente con los archivos de extensión `.mfa` del perfil; las demás entradas ISO se registran fuera del alcance.

La selección liga hipótesis a bytes concretos; no acredita la estructura ni autoriza ejecutar recursos. El perfil y la imagen se verifican de nuevo, y el parser aplica los checks completos. XBG0 puede seleccionarse con D8 para conservar su rechazo demostrado; no se omite silenciosamente.

ID de selección: SHA-256 de JSON canónico del esquema anterior, contenedores ordenados por ruta, claves ordenadas, UTF-8 sin ASCII escapado, separadores `,` y `:`. Este digest identifica el contenido normalizado, **no los bytes del archivo JSON**; el hash del archivo se documenta aparte. No incluye fecha, rutas del host ni IDs de un informe anterior.

## Interfaces y algoritmo

`mfa.parse_layout` es el único recorrido estructural. Retorna resumen y tupla de descriptores congelados (`MfaEntry`) después de comprobar todos los bloques. `inspect_layout` y `inspect_d8` consumen su resumen, conservando el formato de sondeo. Los nombres no se convierten en rutas del host.

`asset_selection` valida y normaliza la matriz; `asset_catalog.collect_assets` coordina sobre `AssetReader` (inventario, rangos y `hash_range`); `IsoImage` implementa el acceso/estabilidad. `hashing.fingerprint_range` adapta un stream a un final lógico para reutilizar `fingerprint_stream`: el EOF lógico evita que el chequeo de tamaño lea bytes contiguos ajenos. Se admiten lecturas cortas positivas, se rechaza EOF prematuro y un lector que devuelva más bytes de los pedidos. Un rango vacío devuelve SHA-256 del vacío sin leer del stream.

Orden: validar matriz contra perfil → inventario/verificación completa → por ruta, parsear contenedor completo → presupuesto → hash por descriptor → persistir únicamente después del cierre estable. Error de formato `MfaError`: contenedor desconocido; errores de identidad/transporte/contrato `ProfileError`: abortar todo. No calcular hashes de entradas parciales de XBG0 ni inferir su codificación.

## Catálogo JSON

`schema_version=1`, `scope=selected_mfa_entries`, `tool` (nombre/versión/pycdlib), `source` del inventario ISO, `selection` (digest canónico/esquema), `containers`, `entries`, `outside_scope`, `summary`, `extraction=not_performed`, `payload_decoding=not_performed`, `capabilities=[]`.

Cada contenedor conserva ID ISO, ruta, offset ISO, tamaño/hash, layout y resultado. Aceptados: resumen estructural completo; rechazados: `unknown`, código y detalles. `outside_scope` conserva las entradas de inventario de otros archivos ISO, no les atribuye análisis interno.

Cada recurso conserva:

- `id=asset:` + SHA-256 del texto UTF-8 unido con NUL: namespace `sh3-asset-v1`, ID del contenedor ISO, base del bloque y ordinal de entrada dentro del bloque (ambos decimales, desde cero). El ID del contenedor liga imagen/perfil/ruta. Mismo payload en dos posiciones produce IDs distintos.
- `origin` con imagen/perfil; `container_id`; `block_index`, `block_offset`, `entry_index` desde cero; `entry_ordinal` desde uno.
- `container_offset` de datos desde inicio del MFA, `iso_offset=offset ISO del contenedor + container_offset`, `size`, `sha256` del payload.
- `source_name`, `source_name_encoding=ascii`, `source_name_offset` desde inicio del MFA; `unknown_word` sin semántica inventada.
- `classification={type:unknown, reason:not_decoded}`, `dependencies={status:not_inspected, known:[]}`, `support=metadata_and_hash_only`.

El catálogo privado puede contener nombres de archivo como metadatos; no contiene payloads ni tablas crudas. No supone que un nombre corresponda a malla, colisión, texto o sonido. Se ordena por ruta de contenedor y orden de entradas original. `summary` reconcilia contenedores, bloques, recursos y bytes con la inspección previa; el programa no fuerza los conteos europeos esperados.

## Validación prevista

Fixtures propios con dos layouts y múltiples bloques, nombres con espacios, tamaño cero, bytes iguales en ubicaciones distintas, hashes conocidos de payload y posiciones contrastadas directamente en ISO sintética. Selecciones invertidas/duplicadas/incompletas/alteradas, JSON malformado/grande, rangos truncados, fallos de I/O tras una lectura, errores tardíos de tabla/nombre y límite global. Comprobar que un contenedor rechazado no entrega descriptores ni hashes parciales; memoria/ISO deben producir mismo resultado.

Dos catálogos europeos nuevos bajo `reports/local`, comparación byte a byte y reconciliación con F02.03: expectativa 61 contenedores/1740 entradas, XBG0 pendiente y 51 archivos ISO fuera del alcance MFA. Ningún test depende de estos datos reales. Custodia: catálogo/selección ignorados; originales no exportados. La extracción posterior exigirá raíz externa explícita y un contrato de salida separado.
