# Sondeo MFA D8 v1 — evaluación F02.02

Estado: contrato de una inspección estructural; no extractor ni especificación universal MFA. Requisitos matriz RNF05.01/.04, RF02.02, RNF06.01, RNF07.06-.09 y RNF11.05-.09. Caso V02/T02 con datos propios. F02.03 tratará la variante B8.

## Criterios EARS

- **M01** WHEN se solicita el sondeo de una ISO THEN el sistema SHALL comprobar su SHA-256 completo y todos los archivos del perfil PS2 antes de interpretar tablas.
- **M02** WHEN una entrada candidata satisface la variante D8 y todos sus bloques THEN el sistema SHALL informar `structural_candidate`, conteos y rangos; las capacidades de extracción/decodificación/runtime SHALL permanecer vacías.
- **M03** IF una tabla, nombre o rango viola el contrato o un límite THEN el sistema SHALL registrar `unknown` con código tipado para ese archivo, sin devolver un resultado parcial aceptado.
- **M04** WHILE inspecciona tablas THEN el sistema SHALL limitar las lecturas a sectores de metadatos de 2048 bytes, a 4096 bloques y a 100000 entradas por contenedor, independientemente del tamaño de sus payloads.
- **M05** WHEN valida nombres THEN el sistema SHALL exigir terminación NUL, ASCII imprimible y ruta relativa segura; SHALL preservar espacios, rechazar duplicados sin distinguir mayúsculas y conflictos archivo/directorio. SHALL no renombrar silenciosamente.
- **M06** IF falla la lectura, la identidad o la estabilidad de la ISO THEN el sistema SHALL abortar sin generar un informe aceptado; un fallo de I/O SHALL no confundirse con variante desconocida.
- **M07** WHEN persiste un informe THEN el sistema SHALL hacerlo tras cerrar una lectura estable, en un destino nuevo, sin payloads, prefijos crudos, nombres internos ni rutas absolutas del host.
- **M08** WHEN se repite el sondeo con mismos bytes, perfil y versión THEN el sistema SHALL producir el mismo JSON. La CI SHALL probar exclusivamente fixtures propios y aplicar sus gates existentes.

## Procedencia y alcance del layout

Referencia consultada: [MFA Tool, mfa_reader.cpp fijado](https://github.com/RayneDuarte/MFA-Tool-for-Silent-Hill-3-PS2-/blob/6c362d2c163236c0496c42ed297eb9c07487ab69/mfa_reader.cpp) y su cabecera. Se consultó el código externo para investigar campos; no se incorpora ni se ejecuta. La implementación propia tiene procedencia documentada y **no se presenta como clean room**. Sin licencia global identificada, la adopción del candidato sigue LIC04.

El candidato usa palabras de 32 bits y sectores de 2048 bytes. El sondeo define explícitamente little-endian y offsets en **bytes**, aunque el candidato los llame LBA. El bloque inicial tiene base 0 y tabla en 0xD8. Cada bloque siguiente tiene base igual al fin de datos anterior y tabla en base + 8. Dos palabras son cantidad de entradas y longitud del área de datos. Cada registro de 16 bytes contiene offset relativo del nombre, offset relativo de datos, una palabra de significado desconocido y tamaño. El dato comienza en base + 2048 + offset; el nombre, en base + offset. Se conserva desconocido el significado del tercer campo y del resto de la cabecera. No se elige tabla por extensión, por cadenas mágicas supuestas o por probar offsets arbitrarios.

Política conservadora propia: tamaño total positivo, múltiplo de 2048 y <= 2^63-1; sector y tabla completos; cantidad positiva, tabla dentro del sector; área de datos positiva y múltiplo de sector; fin dentro del contenedor. Cada nombre debe comenzar después de la tabla, terminar antes del fin del sector y medir como máximo 1024 bytes. Cada intervalo de payload debe caber en su bloque; intervalos no vacíos no se solapan. Se permiten entradas vacías dentro del rango. La cadena de bloques avanza y termina exactamente en EOF; relleno final u otra variante requiere investigación, no aceptación tolerante. Dos nombres que compartan bytes de la tabla de cadenas no se consideran corrupción por sí solos; se valida cada nombre completo.

La tabla D8 y estos límites son una **hipótesis estructural contrastable**, no una firma autenticada. La variante con tabla inicial B8, extensiones engañosas, alias o cualquier disposición fuera de esta política quedan `unknown`. No se leen payloads para validar su semántica ni se calculan hashes por recurso en este ticket. Los hashes completos de origen ya proceden de M01.

## Interfaces, resultados y errores

`mfa.inspect_d8` depende del puerto mínimo `RangeReader.read_at(offset, length)` y tamaño. El adaptador de miembro delega en `IsoImage.read_range(path, offset, length)`, que confina la lectura al archivo ISO y limita cada llamada a 4096 bytes. El parser no conoce rutas locales, ISO, CLI ni disco de salida. `mfa_probe` compone el catálogo verificado existente, selecciona nombres `.mfa` como candidatos de investigación y aplica el parser; la selección no atribuye formato.

Informe v1: `source` de inventario, versión de herramienta/layout, `scope=mfa_d8_structure_only`, entradas ordenadas con ID ISO, ruta, hash/tamaño y resultado. Un candidato estructural incluye bloques (base, tabla, fin, cantidad, bytes de payload y palabras desconocidas observadas), totales y bytes de metadatos leídos. Un desconocido incluye código. No incluye tablas crudas ni nombres internos. `extraction=not_performed`, `payload_validation=not_performed`, `capabilities=[]` en ambos casos.

Errores de formato usan `MfaError` y códigos `MFA_SIZE`, `MFA_TABLE`, `MFA_BLOCK_RANGE`, `MFA_NAME`, `MFA_PATH`, `MFA_DUPLICATE_PATH`, `MFA_PAYLOAD_RANGE`, `MFA_OVERLAP`, `MFA_LIMIT`. Lecturas inválidas/cortas o I/O usan `ProfileError` (`READ_LIMIT`, `READ_RANGE`, `SHORT_READ`, `ISO_READ_ERROR`) y abortan la operación. No se imprime contenido binario ni nombres internos en mensajes.

## Verificación prevista

Fixtures generados en memoria: uno/múltiples bloques, espacios y tamaño cero, variantes B8/desconocidas, tablas/cadenas truncadas, conteos y tamaño extremos, rutas inseguras, colisiones entre bloques, solapamientos y budgets. Contrato del adaptador ISO frente a memoria; identidad/perfil, estabilidad al cierre y salidas exclusivas. Dos ejecuciones reales solo de lectura comparan JSON completo bajo `reports/local`. Ninguna prueba de CI necesita originales ni red. La exportación real seguirá requiriendo raíz privada externa explícita y su propio verificador.
