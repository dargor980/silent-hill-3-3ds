# Buffer copy v1 — CP01–CP08

Como investigador quiero enlazar la finalización del sector con su copia y el
retorno del driver, sin confundir bytes coincidentes con ejecución demostrada.

## Requisitos EARS

- **CP01:** WHEN se recibe el perfil THEN el adaptador SHALL validar los perfiles
  BC/DT y las llamadas directas lector→helper y helper→copiador, sus delays nulos,
  ventanas completas suministradas y tamaños de pila positivos/alineados, con
  espacio suficiente para los argumentos y retorno guardados del helper.
- **CP02:** WHEN se reciben evidencias THEN el adaptador SHALL exigir siete pausas
  de ocho rangos, una identidad, slots distintos, secuencias regionales consecutivas,
  ciclos crecientes dentro de 60 segundos y mapas estables; SHALL conservar las
  evidencias originales sin renumerar paquetes ni estados para reutilizar contratos.
- **CP03:** WHEN se enlaza el driver THEN el adaptador SHALL validar pool y generación
  en ambos extremos con DT, objeto estable salvo posición/caché, argumentos originales,
  posición final incrementada por los bytes solicitados y retorno exterior de esa cantidad.
- **CP04:** WHEN se enlaza la finalización THEN el adaptador SHALL ejecutar BC sobre
  sus tres pausas originales y exigir backend terminado, buffer completo y argumentos
  del helper estables hasta terminar la copia, además de la caché actualizada.
- **CP05:** WHEN se valida la copia THEN el adaptador SHALL exigir destino, fuente
  `buffer + offset dentro del sector`, longitud exacta, pila y retorno guardado
  correspondientes al lector; SHALL exigir que la función de copia devuelva el
  puntero de destino, y rechazar un retorno tratado como cantidad.
- **CP06:** WHEN se contrasta el resultado THEN el adaptador SHALL exigir bytes del
  destino iguales al tramo del buffer y conservación hasta el retorno exterior,
  sin solapamiento físico entre destino, buffer y controles; SHALL declarar destino preexistente
  sin atribuir una escritura nueva y rechazar cambios fuera del tramo del recurso en el buffer.
- **CP07:** WHEN se publica el resultado THEN el adaptador SHALL emitir metadatos
  con cero `Read`, vínculos y capacidades y mantener pendientes autenticación,
  apertura, continuidad, procedencia física y captura real; la investigación SHALL
  contrastar el perfil privado con ELF/ISO y repetir el informe sin cambiar fuentes.
- **CP08:** WHEN se valida el cambio THEN las pruebas SHALL usar datos propios,
  cubrir errores de fuente/destino/longitud/retorno/mapas, pasar regresión, cobertura
  y gates existentes y conservar evidencia de los ensayos fallidos y corregidos.

## Diseño y decisiones

`buffer_copy.reconcile_buffer_copy(source, request, profile, sector_sha256, stages)`
recibe `CopyProfile(completion, driver, copier, reader_call_pc, copy_call_pc)`.
Es puro; usa los modelos BC/DT, el inspector de pool de DT y LF. No modifica
contratos históricos, ni adquiere estados ni lee archivos. Los tamaños de los dos
frames se derivan de los prólogos suministrados `ADDIU sp,sp,-n`; la semántica del
resto del código no se autentica en el adaptador.

| Pausa | Rangos |
|---|---|
| Dispatch antes | root, pool, object, vtable, dispatch, reader, destination, args |
| Solicitud, aceptación, éxito | Las tres pausas BC originales |
| Llamada y retorno de copia | driver, backend, code, copier, args, buffer, destination, return |
| Dispatch después | Los ocho rangos DT del extremo inicial |

Son **siete estados y 56 solicitudes regionales**, antes del descubrimiento.
El contrato DT de dos pausas exige secuencias contiguas: no se puede invocarlo
sobre extremos separados por cinco pausas. Este contrato compone sus invariantes
de extremos y reutiliza `inspect_driver` directamente, conservando la secuencia
de adquisición real. Los argumentos exteriores y los del helper pertenecen a
frames diferentes; se comparan en sus respectivos niveles.

El subconjunto hereda BC: archivo normal, un sector, fallo de caché, aceptación
anterior al progreso del worker, sin cancelación. Se verifica identidad de pool
solo en los extremos; eso no demuestra ausencia de liberación/reasignación en
medio. El buffer completo permanece idéntico desde el éxito hasta la copia,
incluido padding capturado, aunque su hash de archivo excluya el padding.

El destino permanece igual desde dispatch hasta la llamada de copia y desde su
retorno hasta el retorno del lector. Se verifica únicamente su rango solicitado:
no se afirma ausencia de escrituras fuera de ese rango. Un destino ya coincidente
es consistencia válida y queda declarado. La prueba real de ejecución requiere
el perfil conjunto de apertura/continuidad y adquisición bajo guardia.

## Tareas y aceptación

1. **CP-T1 / CP01,05:** trazar copiador, frames y retorno del lector; fijar perfil.
   Aceptación: distinguir puntero devuelto por copia de cantidad devuelta por lector;
   contrastar prólogos y llamadas, sin publicar bytes ni direcciones originales.
2. **CP-T2 / CP02–06:** componer siete pausas sin fabricar evidencia y verificar
   mapas, objeto, backend, argumentos, buffer y destino. Aceptación: copia parcial,
   fuente ajena, buffer sustituido, alias físico y retorno corto rechazados.
3. **CP-T3 / CP07:** plan privado 0700/0600 sin sobrescribir, dos análisis iguales,
   origen intacto y lectores cerrados antes de publicar metadatos.
4. **CP-T4 / CP08:** fixtures propios, regresión completa, cobertura 80/80, lint,
   comprobaciones de custodia/enlaces/hashes y actualización de tareas.
