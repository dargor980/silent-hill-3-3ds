# Driver transfer v1 — DT01–DT09

Estado: contrato de consistencia suministrada de F02.07/LP-C; no acredita I/O.

Como investigador quiero distinguir un objeto activo del driver de una fila
residual y contrastar posición, despacho y resultado antes de atribuir una carga.

## Requisitos EARS

- **DT01:** WHEN se reciben entradas THEN el validador SHALL exigir tipos exactos,
  hash SHA-256 canónico, identificador no negativo, tamaño de archivo con signo,
  solicitud de 1–4096 bytes y un resultado positivo explicado por la solicitud
  o por el límite del archivo; SHALL rechazar transferencias entre sectores.
- **DT02:** WHEN se interpreta el pool THEN el validador SHALL comprobar raíz,
  cabecera de 24 bytes, capacidad 1–256, desplazamiento 0–31 y objetos de 48 bytes
  contiguos tras la cabecera; SHALL usar el desplazamiento observado sin derivarlo
  de la capacidad, y exigir que el índice calculado pertenezca al pool.
- **DT03:** WHEN se identifica el objeto THEN el validador SHALL exigir el handle
  completo, contador posterior a asignación y fórmula sin desbordamiento
  `((contador - 1) << desplazamiento) + índice == handle`, bloqueo activo,
  tamaño/posición esperados, referencia backend no nula y tabla de funciones
  cuyo primer destino coincida con el perfil suministrado.
- **DT04:** WHEN se comparan dos pausas THEN el validador SHALL exigir ocho rangos
  LF por pausa, slots distintos, identidad común, secuencias consecutivas, ciclos
  crecientes dentro del límite LP, mapas estables y código igual al perfil.
- **DT05:** WHEN se valida el despacho THEN el validador SHALL comprobar las dos
  cargas de tabla, JALR y delay slot nulo, PC de llamada/retorno, marco de pila,
  argumentos guardados, objeto/destino/tamaño y cantidad devuelta exactos.
- **DT06:** WHEN se acepta la pareja THEN el validador SHALL exigir posición final
  igual a posición inicial más resultado, metadatos estables salvo posición e
  índice de caché, buffer de sector válido, índice inicial vacío o dentro del
  archivo e índice final correspondiente al sector esperado; SHALL comparar el
  hash del destino final incluso cuando los bytes iniciales ya eran iguales.
- **DT07:** WHEN se publica el recibo THEN el validador SHALL emitir solo hashes,
  tamaños, conteos, etiquetas y alcance; SHALL declarar no acreditados el origen
  del archivo, generación durante apertura, ruta interior, origen de caché,
  lectura de disco y ejecución real, y SHALL producir cero eventos `Read`,
  vínculos o capacidades.
- **DT08:** WHEN se prepara el plan operativo THEN la investigación SHALL anclar
  ventanas privadas al ELF y estado fijados, conservarlos sin cambios, repetir
  el análisis con salida idéntica y mantener rutas, instrucciones, punteros y
  registros del juego fuera de los artefactos públicos.
- **DT09:** WHEN se valida la implementación THEN las pruebas SHALL usar fixtures
  propios para cierre, reciclado, capacidad/desplazamiento independientes,
  desbordamientos, mapas, CPU, recorte EOF, caché y payload preexistente, y SHALL
  aprobar regresión, cobertura y controles de repositorio de CI.

## Diseño y límites

`driver_object.inspect_driver` interpreta cuatro rangos LF (`root`, `pool`,
`object`, `vtable`) y devuelve una vista privada inmutable. No abre archivos.
`driver_transfer.reconcile_driver_transfer` añade `dispatch`, `reader`,
`destination`, `args` y compara dos pausas. Recibe un `DriverRequest` y un
`DriverProfile`; adquisición, custodia y publicación siguen en SRC55/SRC57.
Las dependencias son validadores existentes y biblioteca estándar; no se
modifican los contratos históricos ni el runtime de Nintendo.

El subconjunto admite una transferencia positiva dentro de un sector de 2048
bytes con buffer asignado. Caché, referencia backend y contador se observan en
los extremos: no prueban el camino ejecutado ni excluyen cierre/reapertura entre
pausas. Un código suministrado coincidente no autentica su semántica completa.
El handle suministrado aún no se une a SRC58: falta observar el objeto y su
generación durante la apertura. Un recibo consistente tampoco prueba la ruta
interna de copia, finalización del backend o identidad del sector.

## Tareas y aceptación

1. **DT-T1 / DT01–03:** modelar el pool y asignación; rechazar filas cerradas,
   token de archivo confundido con handle de driver y contador reciclado.
2. **DT-T2 / DT04–07:** implementar pareja de despacho y posición; aceptar caché
   sin cambio de payload únicamente como consistencia sin `Read`.
3. **DT-T3 / DT08:** fijar ventanas, inventario residual y plan privado; publicar
   dos informes deterministas sin datos originales.
4. **DT-T4 / DT09:** ejecutar casos adversarios, regresión y cobertura; registrar
   evidencia y detallar puente de apertura, caché y descubrimiento bajo guardia.
