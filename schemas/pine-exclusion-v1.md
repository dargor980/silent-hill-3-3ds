# PINE exclusion v1 — PE01–PE09

Lote acotado de AD-2/EX-2. Protege solicitudes PINE y la vida de sus callbacks;
no acredita exclusión de toda la VM.

## Requisitos EARS

- **PE01:** WHEN comienza una solicitud PINE THEN SHALL adquirir una reserva
  de trabajo antes de efectos; IF la puerta está cerrada o falta capacidad THEN
  SHALL devolver fallo sin ejecutar el paquete.
- **PE02:** WHEN se solicita cierre THEN SHALL impedir nuevas reservas y SHALL
  informar drenaje mientras exista trabajo anterior, sin esperar al CPU/GS/VU.
- **PE03:** WHEN una solicitud encola trabajo CPU u otro callback retenido THEN
  SHALL compartir su reserva hasta destruir la última copia, incluso tras error,
  respuesta temprana, timeout o descarte de la cola.
- **PE04:** WHEN ya no existe trabajo y no venció el plazo THEN el propietario
  exclusivo SHALL observar estado retenido. Una consulta diagnóstica del contador
  SHALL NOT sustituir la posesión del cierre.
- **PE05:** IF vence el plazo THEN SHALL informar timeout y mantener cerrada la
  puerta hasta cancelación/destrucción explícita; SHALL NOT autorizar captura ni
  reabrir de forma asíncrona mientras el propietario usa el ámbito.
- **PE06:** WHEN se cancela/destruye el cierre THEN SHALL reabrir exactamente una
  vez; una solicitud de cierre competidora SHALL NOT liberar el cierre ajeno.
- **PE07:** WHILE los efectos, callbacks o despachos se ejecutan THEN SHALL NOT
  mantenerse el mutex interno de contabilidad. El propietario SHALL avanzar por
  consultas/eventos, sin bloquear el CPU esperando callbacks que necesitan CPU.
- **PE08:** WHEN la puerta está abierta THEN SHALL conservar efectos, respuestas
  y errores del proveedor. IF un paquete ya produjo efectos antes de fallar THEN
  SHALL conservar esos efectos parciales y liberar correctamente sus reservas.
- **PE09:** WHILE GS/VU, otros escritores y transiciones no estén excluidos THEN
  SHALL mantener desconocida la admisión global y no habilitar armado real.

## Diseño y SOLID

`CooperativeGate` administra contabilidad, capacidad y un único cierre RAII.
`Work` comparte un token opaco: copiarlo no inicia trabajo nuevo y conserva la
reserva original. `Closure` es exclusivo, no copiable ni movible; `poll` comprueba
plazo y trabajo bajo un mutex breve. Ningún método espera colas ni invoca callbacks.
El objeto gate debe vivir más que todos sus Work y Closure. Closure pertenece a
un único hilo; Work puede transferirse/copiarse entre hilos.

La puerta no serializa los trabajadores entre sí: excluye al propietario del
cierre de los trabajadores ya admitidos y rechaza entradas posteriores. La
publicación de efectos anteriores depende de liberar el último Work antes de
que poll observe cero bajo el mismo mutex. El plazo usa steady_clock.

El adaptador PINE rodea ParseCommand completo. Las lambdas save/load conservan
Work y el callback de error de save lo prolonga por el trabajo ZIP retenido.
El dispatch del observador lleva Work hasta el callback CPU, aunque expire la
espera de respuesta. Una cola que retenga callbacks impide el cierre de forma
conservadora hasta descartarlos o terminar; nunca equivale a finalización.

La API privada de cierre no tiene caller productivo en este lote. No cambia la
admisión SRC71, no detiene GS/VU y no ejecuta capturas reales.

## Tareas y aceptación

1. **PE-T1 / PE02,03,07,09:** inventariar ParseCommand, despacho Qt, Completion,
   guardado/carga y callbacks retenidos; fijar fuentes y orden sin esperas circulares.
2. **PE-T2 / PE01–07:** implementar gate y reservas opacas; instrumentar nueva
   copia privada y dispatch propio, preservando fuentes/evidencias históricas.
3. **PE-T3 / PE01–08:** probar drenaje, contendientes, timeout, cancelación,
   capacidad, publicación entre hilos y callbacks tardíos/descartados; cuerpos
   reales del parser con dobles explícitos y comparación ON/OFF/anterior.
4. **PE-T4 / PE08,09:** compilar unidades, sanitizar, medir cobertura y regresión,
   repetir auditorías y dejar pendientes coordinación CPU/GS/VU y armado.
