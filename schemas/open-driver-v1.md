# Open driver v1 — OD01–OD09

Estado: contrato de apertura suministrada y comparación de extremos, F02.07/LP-C.

Como investigador quiero relacionar el resultado de apertura con el objeto del
driver y detectar discrepancias antes de atribuir continuidad a una lectura.

## Requisitos EARS

- **OD01:** WHEN se reciben origen y perfiles THEN el adaptador SHALL validar
  los contratos CA/DT y exigir tamaño de archivo, offset, tamaño y hash comunes;
  SHALL limitar esta unidad a solicitudes completas sin recorte EOF.
- **OD02:** WHEN se observa el retorno de apertura THEN el adaptador SHALL
  exigir ocho rangos `root,pool,object,vtable,code,path,descriptor,range`,
  código fijado, PC/RA de retorno, pila alineada, modo/banderas, descriptor
  reservado y rango esperado; SHALL comprobar la ruta normalizada del contenedor.
- **OD03:** WHEN se vincula el resultado THEN el adaptador SHALL exigir que r2
  sea el handle del objeto activo, contador coherente, posición cero, caché
  inválida, referencia backend no nula y estado inicial compatible con banderas.
- **OD04:** WHEN se compara apertura con despacho THEN el adaptador SHALL
  exigir identidad común, tres slots distintos, secuencias consecutivas,
  ciclos crecientes dentro del límite LP y backing estable de rangos comunes;
  SHALL rechazar cambios de mapa también en páginas compartidas por otras etiquetas.
- **OD05:** WHEN se comparan objetos THEN el adaptador SHALL exigir el mismo
  pool, dirección, handle, contador, tabla, backend, buffer y demás campos
  invariantes; SHALL permitir únicamente posición e índice de caché diferentes.
- **OD06:** WHEN se comprueba la lectura suministrada THEN el adaptador SHALL
  reutilizar DT para la pareja de despacho, argumentos, posición y payload;
  SHALL conservar los límites y rechazos de ese contrato.
- **OD07:** IF se solicita continuidad THEN el adaptador SHALL rechazar con
  `OPEN_DRIVER_LIFETIME_UNPROVEN`, incluso ante extremos idénticos; IF se solicita
  explícitamente diagnóstico THEN SHALL devolver solo consistencia, cero `Read`,
  vínculos y capacidades, sin acreditar ejecución, catálogo, archivo ni continuidad.
- **OD08:** WHEN se prepara el plan privado THEN la investigación SHALL fijar
  el retorno y la inicialización en ELF/estado, repetir el análisis con resultados
  idénticos y mantener instrucciones, direcciones y rutas privadas fuera del informe.
- **OD09:** WHEN se valida la unidad THEN las pruebas SHALL cubrir cierre,
  reciclado visible, ABA indistinguible, argumentos, rutas, mapas, presupuesto y
  publicación mínima con fixtures propios; SHALL pasar regresión y gates de CI.

## Diseño

`open_driver.reconcile_open_driver(source, opening, request, driver, stages,
require_continuity=True)` es una función pura. `CatalogSource`/`OpenProfile`
aportan la entrada anclable de SRC58; `DriverRequest`/`DriverProfile` y la pareja
DT aportan SRC59. No acepta un recibo JSON previo como prueba. La primera pausa
se sitúa al retorno del callee, antes del delay slot que copia el handle.

Decisión: usar una pausa específica de ocho rangos y dos pausas DT, 24 solicitudes
regionales. No concatenar las cinco regiones CA con las cuatro del objeto. Este
perfil **no ejecuta la reconciliación de selección del catálogo CA**: omite su
configuración y selección; conserva descriptor reservado, ruta y rango. La unión
completa con selección/finalización CA exige un nuevo perfil conjunto y queda
pendiente. Los sondeos de descubrimiento se presupuestan por separado.

La responsabilidad de interpretar el objeto permanece en `driver_object`; DT
valida la transferencia; OD valida apertura y comparación entre extremos. No
modifica contratos históricos, adquisición, emulador ni runtime Nintendo.

Igualdad de contador y handle no excluye reinicialización, restauración, escritura
ajena o vuelta completa del contador entre muestras. No se admite un booleano
suministrado como certificado de continuidad. Por defecto se falla cerrado;
el diagnóstico requiere `require_continuity=False` explícito y nunca promueve
el resultado a procedencia real. No hay modo de éxito de continuidad en v1.

## Tareas detalladas y aceptación

1. **OD-T1 / OD01–03:** fijar ABI al retorno y estado inicial de objeto; implementar
   validación de ruta/rango/descriptor. Aceptación: retorno negativo, objeto cerrado,
   tamaño distinto o ruta ajena se rechazan antes del diagnóstico.
2. **OD-T2 / OD04–07:** componer DT con apertura, mapas e invariantes; exigir modo
   diagnóstico explícito. Aceptación: reciclado visible falla y extremos ABA
   indistinguibles nunca acreditan continuidad ni producen `Read`.
3. **OD-T3 / OD08:** contrastar ventanas e instrucciones en originales privados;
   generar plan sin sobrescritura y dos informes iguales. Aceptación: fuentes
   previas intactas, 0700/0600 y ningún objeto residual promovido a activo.
4. **OD-T4 / OD09:** pruebas adversarias, regresión/cobertura, trazabilidad y tareas
   siguientes. Aceptación: gates aprobados, limitaciones y evidencia real separadas.
