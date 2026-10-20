# Propietario del intento de exclusión v1 — RD01–RD08

Implementa B1 de CQ3-B, [WD02,09](worker-drain-v1.md). B2/B3 y las retenciones
reales VU/GS siguen pendientes. Los resultados del puerto de pruebas no acreditan
el proveedor completo.

- **RD01:** WHEN se acepta un request THEN SHALL conservar ID creciente,
  identidades y plazo del mismo intento. Reentrada y solicitudes simultáneas
  SHALL rechazarse sin reemplazar el propietario.
- **RD02:** WHILE hay reservas PINE anteriores THEN SHALL permitir su progreso
  sin iniciar la fase siguiente. WHEN PINE queda retenido THEN SHALL iniciar esa
  fase una sola vez y SHALL conservar PINE durante todas sus consultas.
- **RD03:** WHEN la fase siguiente informa pendiente THEN SHALL mantener el
  intento activo; WHEN informa retenido THEN SHALL revalidar antes de completar.
  IF el proveedor carece de una barrera acreditada THEN SHALL rechazar esa fase.
- **RD04:** WHEN vence el plazo, cambia la identidad o se pierde la frontera/pausa
  THEN SHALL invalidar sin éxito implícito. El controlador SHALL revalidar también
  después de llamadas al puerto; una llamada al puerto SHALL ser acotada.
- **RD05:** WHEN se cancela, termina o invalida THEN SHALL publicar estado terminal
  antes de liberar. SHALL liberar primero la fase siguiente y después PINE,
  incluso si begin solo llegó a preparar parte de sus recursos.
- **RD06:** IF un puerto reentra en step THEN SHALL invalidar el intento;
  IF solicita cancelar THEN SHALL conservar ese terminal. Retire dentro de
  begin/poll/release SHALL NOT liberar recursivamente ni sustituir el request.
- **RD07:** WHEN entra una transición VM instrumentada THEN SHALL cancelar y
  retirar antes del primer efecto. WHEN entra un callback CPU instrumentado y
  comenzó la fase siguiente THEN SHALL hacer lo mismo antes del callback.
  Los callbacks previos a esa fase SHALL poder drenar reservas PINE.
- **RD08:** WHEN se valida THEN SHALL separar pruebas del controlador, cuerpos
  del proveedor con dobles, compilación ON/OFF y ejecución completa de VM.
  SHALL mantener desconocidas las condiciones de exclusión no demostradas.

## Diseño

RetainedDrain compone PineDrain sin cambiarlo. EffectDrainPort contiene solo
begin(request), poll(id) y release(id), con estados pending/held/rejected.
El puerto debe progresar sin reservar colas de datos ni esperar CPU/UI. Su release
debe deshacer preparaciones parciales y respetar el orden GS antes de VU; el
controlador no conoce semáforos ni renderizadores. No asigna memoria propia.

Los estados públicos reutilizan PineDrain::State, pero held/completed del
propietario requieren también la fase siguiente. Los terminales retienen recursos
hasta retire. El ID no se reinicia al retirar; los epochs se comprueban en cada
paso. El caller aporta identidades actuales antes de cada step/complete; no se
infieren épocas de un resultado viejo. El plazo no interrumpe un puerto bloqueado,
por lo que el contrato exige llamadas acotadas.

VMManager conserva los nombres internos Queue/PollObserverPineDrain para no
introducir un nuevo transporte. Su propietario pasa a RetainedDrain y el puerto
de producción devuelve rejected hasta implementar B2/B3/CQ3-C. No existe un
fallback que simule éxito. Los scopes de bombeo Qt solo revocan la frontera;
cancelarlos indiscriminadamente impediría avanzar reservas anteriores. Las
entradas instrumentadas del slot y del fast path inline cancelan después de
iniciada la fase siguiente; los demás productores permanecen pendientes de B2/B3.

## Tareas

1. **RD-T1 / RD01–06:** controlador, puerto pequeño y pruebas de propiedad,
   fases, identidad/plazo, rechazo, cancelación, reentrada y liberación.
2. **RD-T2 / RD03,07:** nueva copia del proveedor; propietario con puerto
   rechazado por defecto, catorce entradas VM y dos callbacks CPU instrumentados.
3. **RD-T3 / RD01–08:** CTest/CI host, cobertura, cuerpos reales aislados y objetos
   ON/OFF; preservar fuentes y evidencia. No cerrar B2/B3 ni acreditar captura.
