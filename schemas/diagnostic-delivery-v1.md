# Entrega del productor bajo presupuesto — WD v1

Historia: como investigador, necesito conservar el presupuesto del trabajador
mientras un dueño externo transmite su diagnóstico, sin aceptar otro trabajo
ni admitir una entrega posterior a cancelación o deadline.

## Requisitos EARS

- **WD01:** CUANDO se envíe una solicitud con deadline absoluto local, DEBERÁ
  incluir tiempo transcurrido antes de crear el trabajador. Un deadline vencido
  DEBERÁ rechazar antes de crear recursos; uno posterior al máximo propio SHALL
  NOT ampliar los límites de 5 s iniciales/2 s de revalidación.
- **WD02:** CUANDO se retire una respuesta para transmitirla, DEBERÁ pasar a
  entrega pendiente y mantener el presupuesto activo, incluida expiración sin
  consultas del dueño. SHALL NOT volver a muestrear, aceptar otro trabajo ni
  completar automáticamente por haber copiado el payload.
- **WD03:** CUANDO termine el envío, DEBERÁ comprobar de nuevo presupuesto,
  cancelación e identidad de la operación antes de confirmar entrega. Mezclar
  recogida antigua y entrega retenida, completar dos veces o solapar solicitudes
  DEBERÁ rechazar sin reactivar la sesión.
- **WD04:** MIENTRAS se escriba el frame, DEBERÁ conservar una copia local de
  tamaño fijo, aceptar progreso parcial y comprobar presupuesto antes/después
  de cada llamada al sink. Las esperas deberán ser de hasta 20 ms y compartir el
  plazo restante. Error, progreso imposible o peer perdido DEBERÁ ser terminal.
- **WD05:** CUANDO venza, se cancele o cambie lifecycle durante la entrega,
  DEBERÁ descartar su confirmación y conservar primera causa. Los bytes enviados
  no podrán retirarse. La confirmación del productor SHALL NOT significar que el
  consumidor autenticó o admitió la respuesta.
- **WD06:** CUANDO se cierre, DEBERÁ diferenciar limpieza del trabajo DW de cierre
  del canal, que pertenece al dueño de transporte. SHALL NOT cerrar el descriptor
  desde otro hilo ni presentar la unión DW como prueba de cierre de ambos extremos.
- **WD07:** CUANDO se use el sink macOS, DEBERÁ retener un socket Unix propio,
  verificar identidad nativa esperada en ambas fronteras, usar IO no bloqueante
  y prevenir SIGPIPE. Una falla DEBERÁ ser terminal; no habrá reconexión.
- **WD08:** CUANDO se valide, DEBERÁ mantener pruebas anteriores y añadir plazos
  exactos, revalidación, progreso parcial, backpressure, peer perdido, cancelación
  y cierre. La sonda conjunta PCSX2 de NW-T3c seguirá pendiente hasta ejecutarse.

## Diseño

`submit_until` selecciona por sesión la entrega retenida y limita el deadline
externo al máximo propio. `take_for_delivery` extrae una sola copia sin desactivar
`pending`. `complete_delivery` serializa confirmación y cancelación bajo el mutex.
`delivery_checkpoint`/`delivery_remaining` prestan comprobaciones al dueño de IO.
La recogida anterior sigue disponible únicamente en sesiones del modo anterior.

`deliver_diagnostic` compone el trabajador con `DiagnosticDeliverySink`, un puerto
mínimo de escritura parcial y espera acotada. Solo un dueño llama a la función,
fuera del hilo CPU/guardias retenidas. El sink macOS posee el socket y el peer
esperado; no selecciona política, desafío o perfil. El dueño cierra el sink y une
DW al terminar. Un syscall no cooperativo puede demorar el cierre; no se promete
terminación forzosa. El destinatario BC impone además su propio plazo de admisión.

## Tareas

- [x] **WD-T1 / NW-T3b:** deadline externo, entrega retenida y confirmación;
  sink y bucle de envío, tests de propiedad, acumulación y fallos; pruebas nativas,
  sanitizadores, cobertura y controles de regresión.
- [x] **NW-T3c:** componer BC, DW, trabajo nativo y canal en sonda PCSX2 privada;
  conservar las identidades y evidencias, provocar fallos por fase y comprobar
  cierres antes de cerrar NW-T3/DW-T2. Runtime DW-T3 continúa por separado.

SRC110 verifica WD-T1 con 402 escenarios en cuatro modos, 41 ejecuciones TSan
y cinco regresiones detectadas. La sonda conjunta NW-T3c continúa pendiente.

SRC111 completa **NW-T3c**, según [DC01–DC08](diagnostic-composition-v1.md).
Se verifican ambos extremos con inventario real, escrituras parciales,
backpressure y fallos por fase. DW-T3 permanece pendiente y la captura cerrada.
