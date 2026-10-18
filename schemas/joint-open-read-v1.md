# Joint open/read v1 — JR01–JR08

Como investigador quiero contrastar una selección de catálogo y su apertura con
el recorrido completo hasta el destino, conservando la evidencia original y los
límites de lo que permiten concluir observaciones separadas.

## Requisitos EARS

- **JR01:** WHEN se recibe el perfil conjunto THEN el adaptador SHALL validar
  CA y CP y exigir el mismo contenedor, recurso, tamaño y tramo en ambos modelos.
- **JR02:** WHEN se reciben evidencias THEN el adaptador SHALL exigir once pausas,
  una identidad, once slots distintos, secuencias regionales consecutivas y ciclos
  crecientes dentro de un único presupuesto de 60 segundos; SHALL rechazar cambios
  de backing o traducción de páginas entre apertura y recorrido.
- **JR03:** WHEN se compone CA con CP THEN el adaptador SHALL consumir los estados
  y paquetes originales, sin renumerarlos, recodificarlos ni fabricar subcapturas;
  SHALL validar CA sobre sus cuatro pausas y CP sobre sus siete pausas consecutivas.
- **JR04:** WHEN el descriptor queda finalizado THEN la misma pausa SHALL incluir
  raíz, pool completo y vtable del driver en tres rangos adicionales; el adaptador
  SHALL exigir que el handle devuelto corresponda al objeto validado por CP.
- **JR05:** WHEN se enlaza ese pool con el inicio de dispatch THEN el adaptador
  SHALL exigir cabecera, fila seleccionada, vtable y sus ubicaciones físicas y
  virtuales coincidentes, posición igual al offset del recurso, caché inicial
  inválida y modo asíncrono correspondiente a los flags de apertura.
- **JR06:** WHEN se contrasta buffer y destino THEN el adaptador SHALL rechazar
  solapamientos físicos con los controles capturados durante catálogo/apertura,
  además de conservar las restricciones internas de CP.
- **JR07:** IF se exige continuidad THEN el adaptador SHALL rechazar la serie
  por continuidad no demostrada, incluso con extremos coincidentes; WHEN se
  solicita explícitamente diagnóstico sin continuidad THEN SHALL emitir solo
  metadatos de consistencia, cero `Read`, vínculos y capacidades, sin acreditar
  ejecución, lectura física, vida continua ni autenticación semántica del perfil.
- **JR08:** WHEN se entrega el cambio THEN la investigación SHALL contrastar
  posicionamiento y perfil contra las fuentes privadas, repetir el análisis,
  conservar fuentes e históricos y aprobar fixtures propios, regresión y gates.

## Diseño y decisiones

`joint_open_read.reconcile_joint_open_read(catalog, opening, source, request,
copy, sector_sha256, stages, require_continuity=True)` es un adaptador puro.
Reutiliza modelos y validadores CA/CP/LF. La política predeterminada falla de
forma cerrada; `require_continuity=False` habilita únicamente diagnóstico.
La adquisición, el acceso a archivos y la semántica original quedan fuera del
adaptador. Los módulos históricos permanecen intactos.

| Pausa | Rangos | Cantidad |
|---|---|---:|
| Selección | Los siete rangos CA | 7 |
| Llamada de apertura | Los cinco rangos CA | 5 |
| Retorno de apertura | Los cinco rangos CA | 5 |
| Descriptor finalizado | code, config, descriptor, path, range, driver_root, driver_pool, driver_vtable | 8 |
| Siete pausas de recorrido | Las siete pausas CP originales | 56 |

Son **11 estados y 81 solicitudes regionales**, sin descubrimiento. El pool
completo ocupa `24 + 48 * count` bytes, como máximo 4.096: el subconjunto admite
hasta 84 filas. Se compara su cabecera y fila seleccionada directamente con las
observaciones CP ya validadas; no se transforma el bloque en paquetes nuevos.
Otras filas del pool pueden diferir entre pausas.

Los tres rangos adicionales van al final de la última pausa CA. Su prefijo de
cinco rangos pertenece al mismo estado real y conserva las secuencias que espera
CA; la primera pausa CP empieza inmediatamente después del octavo rango. Añadir
rangos en una pausa CA intermedia rompería la continuidad regional del contrato.

La apertura posiciona el driver antes de finalizar el descriptor. Por eso este
testigo exige el offset del recurso, no posición cero. CP ya valida pool, índice,
generación, posición, backend, finalización, copia y retorno; JR enlaza el handle
de CA y compara la fila completa con el extremo inicial CP. Esto demuestra solo
consistencia entre capturas suministradas. No prueba que no hubiera cierre,
reutilización, escritura ajena o restauración entre ellas.

Se mantiene el subconjunto CP: archivo normal, un sector, fallo de caché,
aceptación anterior al progreso del worker y sin cancelación. No se acepta una
captura fuera de ese subconjunto como prueba de fallo del juego.

## Tareas y aceptación

1. **JR-T1 / JR01,04,05:** trazar apertura→posicionamiento→descriptor y fijar las
   ventanas privadas. Aceptación: posición postapertura derivada de código y
   contrastada con ELF/estado; ninguna dirección o instrucción original pública.
2. **JR-T2 / JR02–07:** componer las once pausas, comparar pool completo con
   rangos CP originales y aplicar política cerrada. Aceptación: identidad cruzada,
   salto de secuencia, remapeo, handle ajeno, pool truncado y alias rechazados;
   diagnóstico positivo sin atribuir continuidad ni generar eventos.
3. **JR-T3 / JR08:** publicar dos análisis iguales tras cerrar lectores, plan
   privado 0700/0600 creado sin sobrescritura y fuentes/históricos intactos.
4. **JR-T4 / JR08:** pruebas propias y de límites, regresión completa, cobertura
   80/80, Ruff, custodia, hashes y enlaces; registrar resultados y pendientes.

## Próxima unidad: condiciones para una captura real

- **Continuidad:** identificar y observar escrituras de liberación, asignación y
  generación del objeto seleccionado desde su apertura hasta el retorno. Integrar
  guardia de sesión y eventos de restauración/reset; una ausencia de eventos solo
  cuenta si se acredita cobertura continua, sin huecos ni pérdida de registros.
- **Progreso temprano:** observar publicación/ejecución interna de la solicitud
  antes del retorno, o definir otro contrato que permita avance del worker sin
  deducir causalidad a partir de bytes ya presentes. Conservar negativas actuales.
- **Descubrimiento:** derivar punteros bajo la misma guardia; incorporar cada
  sondeo, estado y hit al presupuesto, sin renumerar evidencias para omitirlos.
  Los 81 rangos dejan un máximo teórico de 175 solicitudes y los once estados
  dejan 37 estados; no son todavía una reserva ejecutable ni cubren hits internos.
- **LP-D:** solo después de esas condiciones, iniciar antes de la carga en
  español/Normal/Normal; ≤48 estados, ≤256 solicitudes/hits, 60 segundos activos,
  3.600 de pared, 8 GiB de etapa y 10 GiB libres, sin restaurar entre puntos.
