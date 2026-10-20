# Sesión de diagnóstico runtime — RS v1

Historia: como dueño IO, necesito intercambiar solicitudes por el socket autenticado
con el mismo trabajador y alcance CPU, sin prolongar sus plazos ni adelantar la unión.

## Requisitos EARS

- **RS01:** CUANDO comience una sesión, DEBERÁ usar el mismo objeto de vinculación
  publicado por el handoff y conservado por DW. Un trabajador sin vínculo o de otro
  alcance DEBERÁ rechazarse antes de leer el socket.
- **RS02:** CUANDO reciba una solicitud, DEBERÁ acumular exactamente 32 bytes,
  validar su formato y conservar el desafío y secuencia exigidos por DW. La
  recepción parcial y espera DEBERÁN consumir el plazo fijado antes del despacho CPU.
- **RS03:** CUANDO termine una respuesta, DEBERÁ iniciar una ventana de hasta dos
  segundos para la siguiente solicitud, acotada por el deadline original del
  alcance. Espera inactiva, lectura y entrega SHALL NOT renovar ese alcance.
- **RS04:** MIENTRAS espere DW o intercambie bytes, DEBERÁ verificar conexión,
  identidad nativa, cancelación, ciclo de vida y reloj. Una causa terminal DEBERÁ
  impedir solicitudes posteriores y conservar la primera causa observada.
- **RS05:** CUANDO el dueño cierre, DEBERÁ cancelar el alcance y DW, cerrar el
  socket una sola vez y devolver pendiente hasta confirmar retirada CPU. Solo
  después podrá unir DW; un cierre fallido DEBERÁ distinguirse de limpieza pendiente.
- **RS06:** CUANDO el transporte nativo lea, DEBERÁ usar el mismo descriptor y
  dueño de escritura/cierre, verificar identidad antes y después, y limitar cada
  espera a 20 ms o el presupuesto restante, el menor. EOF y lectura inválida
  DEBERÁN fallar permanentemente.
- **RS07:** CUANDO se publique evidencia, DEBERÁ distinguir transporte nativo,
  inventario sintético/nativo, proveedor de prueba y candidato PCSX2 con VM.
  Pruebas de la sesión SHALL NOT cerrar RB-T3/DW-T3 ni conceder captura.

## Diseño SOLID

`RuntimeDiagnosticSession` es una máquina de estados IO que toma prestados
handoff, DW y un puerto `DiagnosticChannel`. No crea hilos ni posee el trabajador;
su destructor solo cancela. El dueño externo conserva esos objetos y reintenta
`close_until` mientras devuelva pendiente, antes de destruir DW. El plazo de unión
usa el reloj real del trabajador; el plazo de protocolo usa el reloj del handoff.

DW expone únicamente una comparación de identidad de su vínculo inmutable. El
transporte implementa lectura, comprobación de conexión, entrega y cierre;
`MacOSDiagnosticSink` conserva su API previa e implementa ese puerto con un único
descriptor. No se expone un descriptor prestado ni se introducen alias propietarios.
Las expectativas del inventario siguen siendo configuración local del launcher.

## Tareas

- [x] **RS-T1 / RB-T3b.1:** implementar recepción parcial, vínculo exacto, plazos
  acumulados, fallo terminal y cierre cooperativo. Cubrir desafío/secuencia,
  callback tardío, desconexión, revocación, DW bloqueado y error de cierre.
- [x] **RS-T2 / RB-T3b.2:** conectar el puerto al socket nativo; verificar lecturas
  parciales, EOF, dueño, identidad completa y composición sesión–socket–DW.
- [ ] **RS-T3 / RB-T3b.3:** componer launcher e inventario nativo con el frontend
  privado; enlazar candidato bajo IB02 y validar con VM, guardias y escritores.
  Mantener separada cualquier prueba previa con proveedor o inventario de prueba.

Evidencia: [SRC115](../docs/execution/f02-07-runtime-session.md). El escenario
exitoso de RS-T2 usa inventario sintético; la fábrica nativa se prueba aquí en su
rechazo de un manifiesto ausente. Ninguno sustituye RS-T3.

Avance posterior: [NR01–NR08](native-runtime-composition-v1.md) y
[SRC116](../docs/execution/f02-07-native-runtime-composition.md) cubren **RS-T3a**
con inventario/socket nativos y frontend propio, aún con puertos CPU/Host de
prueba. **RS-T3b** mantiene integración real, enlace y VM pendientes.

Avance posterior: [RT01–RT07](runtime-service-v1.md) y
[SRC117](../docs/execution/f02-07-runtime-service.md) completan el servicio y el
enlace real. La VM pausada llega al rechazo nativo y cierra correctamente; falta
resolver `preflight`, obtener muestras y validar la matriz de RT-T3.
