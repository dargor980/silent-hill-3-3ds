# Consumidor de diagnóstico con plazo total — BC v1

Historia: como investigador, necesito que el consumidor descarte la respuesta
cuando verificación del peer, transporte y validación acumulen demasiado tiempo,
y que otro hilo pueda solicitar cancelación sin cerrar un descriptor en uso.

## Requisitos EARS

- **BC01:** CUANDO se habilite localmente el consumidor con presupuesto, DEBERÁ
  fijar 5 s para la primera muestra y 2 s para las posteriores antes de la primera
  consulta al peer. Verificación previa, envío, recepción, decode, verificación
  posterior y publicación DEBERÁN compartir ese plazo sin reiniciarlo por fase.
- **BC02:** CUANDO el reloj sea inválido, retroceda o alcance el deadline,
  DEBERÁ invalidar permanentemente la sesión y borrar su observación vigente.
  CUANDO el instante coincida exactamente con el deadline, DEBERÁ rechazar.
  CUANDO se detecte fork, DEBERÁ rechazar sin adquirir el mutex heredado ni
  modificar el descriptor que conserva el proceso padre.
- **BC03:** MIENTRAS se envíen/reciban bytes, DEBERÁ usar IO no bloqueante y
  comprobar presupuesto y cancelación antes/después de cada espera y operación.
  Las esperas cooperativas DEBERÁN ser de hasta 20 ms; no se promete tiempo de
  planificación del SO ni interrupción forzosa de un lector nativo bloqueado.
- **BC04:** CUANDO otro hilo cancele o solicite cierre, DEBERÁ señalarlo sin
  destruir ni cerrar el canal. El dueño DEBERÁ cerrar tras retornar la operación
  en curso. DEBERÁ distinguir solicitud de cancelación de cierre confirmado.
- **BC05:** CUANDO cancelación compita con publicación, DEBERÁ serializar ambas:
  cancelar primero impide aceptar la muestra; publicar primero deja una copia
  histórica, sin permiso de captura. Ninguna llamada al canal ocurrirá bajo ese
  bloqueo. La primera causa DEBERÁ conservarse, incluso si falla el cierre.
- **BC06:** CUANDO haya fragmentación, envío parcial, EAGAIN, EINTR o backpressure,
  DEBERÁ continuar únicamente dentro del presupuesto restante. EOF, mensaje
  incompleto, bytes adicionales o respuesta tardía DEBERÁN invalidar la sesión.
  Los bytes ya enviados no son retractables; no equivalen a respuesta aceptada.
- **BC07:** CUANDO se seleccione este modo, DEBERÁ exigir el puerto de transporte
  con presupuesto; SHALL NOT recurrir silenciosamente al intercambio anterior.
  El modo PS anterior DEBERÁ conservar sus pruebas y declarar su alcance de IO.
- **BC08:** CUANDO se informe la verificación, DEBERÁ separar dobles, sockets
  reales y peer nativo. Esta parte completa solo NW-T3a: productor, integración
  PCSX2 y guardias runtime seguirán pendientes; SHALL NOT cerrar NW-T3/DW-T2.

## Diseño

`DiagnosticSessionBudget` posee reloj, plazo y primera causa, con un bloqueo
breve que serializa cancelación/publicación. Solo el dueño consulta el reloj.
`PlatformDiagnosticSession(..., budget_clock=time.monotonic)` crea ese control
local, verifica el puerto `exchange_with_budget` y lo pasa al canal. La opción
explícita conserva el contrato síncrono anterior mientras se verifica el productor.

`UnixDiagnosticChannel.exchange_with_budget` conserva el socket, lo configura
no bloqueante y limita cada `select` al mínimo entre 20 ms y tiempo restante.
El dueño verifica el peer en ambas fronteras y solo publica un PD íntegro y válido.
`cancel()`/`close()` desde otro hilo señalan una causa; `closed` confirma que el
dueño soltó el canal y `close_failed` informa si no pudo verificar su cierre.
Si el dueño está ocioso, debe volver a `sample()`/`close()` para procesar la señal.

## Tareas

- [x] **BC-T1 / NW-T3a:** presupuesto consumidor, publicación/cancelación
  serializadas, IO fragmentado con espera acotada; tests de tiempo acumulado,
  frontera exacta, reloj inválido/regresivo, backpressure y cierre pendiente.
  Conservar pruebas PS, ejecutar oracle nativo, cobertura y controles de regresión.
- [x] **NW-T3b:** extender el productor DW para conservar el plazo durante envío
  y confirmación, sin desactivar el presupuesto al recoger el resultado; pasar
  el plazo previo al recibo de solicitud sin reiniciarlo al crear el trabajador.
- [x] **NW-T3c:** componer ambos extremos en copia privada PCSX2 sin VM;
  probar deadline/cancelación en cada frontera, conexión perdida, envío parcial,
  cierre de recursos y ausencia de admisiones tardías. Solo entonces cerrar NW-T3.

Avance SRC110: **NW-T3b** queda verificado en el [contrato WD](diagnostic-delivery-v1.md).
Esta sección conserva la secuencia original; la integración NW-T3c continúa abierta.

SRC111 completa **NW-T3c** en la sonda privada PCSX2 del [contrato DC](diagnostic-composition-v1.md).
Los plazos locales se verifican por separado; la composición cierra NW-T3/DW-T2
y mantiene pendientes las guardias runtime DW-T3 y la captura.
