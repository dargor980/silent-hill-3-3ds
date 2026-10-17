# Sondeo de variantes MFA v2 — F02.03

Extiende [M01-M08](mfa-probe-v1.md) con selección de variante y diagnóstico limitado de nombres. Requisitos padre RF02.02, RNF06.01, RNF07.06-RNF07.09, RNF11.05-RNF11.09; V02/T02. No es un extractor ni una descripción completa de MFA.

## Criterios EARS

- **MV01** WHEN se solicita un layout B8 o D8 THEN el sondeo SHALL aplicar exclusivamente ese layout a cada candidato, sin intentar otro como recuperación ante errores.
- **MV02** IF el layout solicitado no está registrado THEN la operación SHALL fallar antes de leer el contenedor.
- **MV03** IF ambas cabeceras iniciales conocidas son plausibles según la política documentada THEN el archivo SHALL quedar `unknown` con `MFA_AMBIGUOUS_LAYOUT`, aunque se haya pedido una de ellas.
- **MV04** WHEN se valida B8 THEN el parser SHALL reutilizar límites de bloques, tablas, nombres, rutas y payloads de D8; solo SHALL cambiar la posición de la tabla inicial a 0xB8.
- **MV05** IF una entrada falla THEN el resultado desconocido SHALL incluir contexto numérico acotado de bloque y entrada, sin devolver conteos parciales como válidos.
- **MV06** IF el nombre tiene bytes no permitidos THEN el diagnóstico SHALL registrar longitud, cantidad de controles/no ASCII y resultados de decodificación estricta/round-trip para candidatos fijos; SHALL mantener la codificación `unresolved` y SHALL no incluir cadenas, bytes crudos ni reemplazos.
- **MV07** WHEN cambia la selección o el esquema del informe THEN la salida SHALL registrar versión 2 y layout aplicado, conservando los informes históricos sin sobrescribir.
- **MV08** WHEN se repite la misma selección sobre la imagen/perfil verificados THEN el JSON SHALL ser idéntico. Las regresiones D8 y los errores de transporte SHALL continuar aprobados con fixtures propios en CI.

## Evidencia de layout y selección

La fuente fijada del lector candidato ya consultada en F02.02 utiliza tablas iniciales en 0xB8 y 0xD8; [procedencia](../docs/compatibility/mfa-candidate-evidence.json). La inspección de cabeceras europeas comprueba las dos posiciones conocidas; no busca offsets arbitrarios. Son hipótesis estructurales, no firmas autenticadas.

La CLI recibe `--layout b8|d8` (por compatibilidad, omitirlo conserva D8). No hay modo auto. `mfa.inspect_layout` admite únicamente estas dos claves; `inspect_d8` conserva su interfaz anterior y delega en el mismo parser. Los bloques siguientes usan tabla en base + 8 para ambas variantes. Los offsets de datos son bytes relativos a base + 2048; los de nombres relativos a base. Todos los límites de M01-M08 continúan vigentes.

Plausibilidad de una cabecera inicial: cantidad positiva, tabla completa dentro de 2048 bytes, área de datos positiva/múltiplo de 2048 y fin dentro del contenedor. Se evalúan solamente esos campos de las dos posiciones conocidas para rechazar ambigüedad. Esta comprobación **no acepta** una variante ni sustituye la validación completa. Si la selección solicitada falla, el resultado sigue siendo desconocido incluso si la otra cabecera es plausible.

No se interpreta automáticamente el byte discriminador heurístico del candidato externo ni se vincula layout a la extensión. Los nombres `.mfa` solo seleccionan archivos para investigación. Una muestra válida bajo una política tampoco demuestra semántica de payload ni universalidad del formato.

## Diagnóstico y responsabilidades

`mfa` posee el recorrido común y anota `block_index` y `entry_index` (ambos desde cero), `entry_ordinal` (desde uno), `block_offset` y `name_offset` relativo. `mfa_names` produce estadísticas de un nombre acotado, sin I/O ni decisiones de aceptación. El tipo `MfaError` distingue datos no soportados de fallos de transporte `ProfileError`; `mfa_probe` compone verificación ISO y serialización después del cierre estable.

La política de aceptación permanece ASCII imprimible, terminación NUL y ruta segura. `name_diagnostics` recibe como máximo 1024 bytes y prueba candidatos fijos `utf-8`, `shift_jis` y `cp932` con errores estrictos. Para cada candidato informa si decodifica y si re-encodear produce los mismos bytes. Decodificar o round-trip por sí solos **no identifican** la codificación original. No se adopta Latin-1 como fallback, ni se sustituyen bytes o normalizan nombres originales.

Los errores de nombre distinguen rango fuera de tabla, ausencia de terminación dentro del límite y bytes no permitidos. Los mensajes y `details` no incluyen nombre, hexadecimal, base64 ni rutas del host. Los resultados siguen `structural_candidate` o `unknown`; `extraction` y `payload_validation` permanecen `not_performed`, `capabilities=[]`.

Informe `schema_version=2`, `tool.version=2`, `scope=mfa_structure_only`, `selection={mode:fixed_layout, layout:b8|d8}`. Cada resultado desconocido contiene código y `details` cuando existe contexto. El campo tool.layout utiliza `mfa-b8-blocks-v1` o `mfa-d8-blocks-v1`: v1 aquí identifica la política de layout; v2 identifica el informe/selección/diagnóstico. Los resultados aceptados conservan la forma anterior. No se cuentan entradas parciales de archivos rechazados.

## Pruebas y cierre

Fixtures propios: B8 con uno/múltiples bloques, errores compartidos parametrizados B8/D8, selección equivocada, cabeceras ambiguas, continuación inválida, nombres sintéticos multibyte/controles, codec que decodifica pero no hace round-trip y diagnóstico sin filtración de cadena. Contrato memoria/ISO y CLI con layout explícito, verificación completa previa e I/O que aborta. Preservar los tests históricos D8 sin debilitar aserciones.

Dos sondeos reales por layout y comparación exacta; metadatos ignorados bajo `reports/local`. El informe de investigación puede cerrar XBG0 como desconocido con evidencia de limitación; ello no autoriza su extracción ni cierra G02. F02.04 deberá consumir solo estructuras demostradas y conservar pendientes para codificación, AFS y otros contenedores.
