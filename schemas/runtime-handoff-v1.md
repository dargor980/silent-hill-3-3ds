# Entrega asíncrona IO–CPU — RH v1

Historia: como dueño IO, necesito solicitar un alcance CPU sin espera bloqueante,
descartar callbacks tardíos y confirmar liberación antes de unir DW.

## Requisitos EARS

- **RH01:** CUANDO IO cree la solicitud, DEBERÁ fijar ID y deadline local de hasta
  cinco segundos antes de encolarla. La espera en la cola consumirá ese mismo
  plazo; CPU SHALL NOT reiniciarlo al adquirir guardias.
- **RH02:** CUANDO CPU reciba el callback, DEBERÁ consumir la solicitud una sola
  vez. Un callback repetido o cancelado antes de ejecutarse SHALL NOT adquirir
  otro alcance. El callback conservará la solicitud compartida, nunca punteros
  a variables de pila del dueño IO.
- **RH03:** CUANDO cancelación y publicación concurran, DEBERÁ conservar la primera
  causa y cancelar cualquier ticket que se publique después. IO SHALL NOT leer
  el puntero compartido antes de su publicación completa.
- **RH04:** CUANDO CPU retire el intento, DEBERÁ confirmar retirada solamente
  después de liberar las guardias. Solo el dueño CPU del ticket podrá confirmarla.
  Cancelado/revocado SHALL NOT equivaler a retirado.
- **RH05:** CUANDO IO cierre el diagnóstico, DEBERÁ cancelar solicitud y DW,
  devolver limpieza pendiente mientras CPU no confirme retirada y unir DW
  después. Un hijo bloqueado conservará recursos y podrá seguir pendiente.
- **RH06:** CUANDO el proveedor conecte el callback, DEBERÁ usar despacho CPU
  no bloqueante y un ID de intento no reutilizable. El cierre del frontend,
  ausencia de callback y rechazo de cola SHALL NOT crear una adquisición tardía.
- **RH07:** CUANDO IO reciba el ticket listo, DEBERÁ usar su misma vinculación
  para componer DW y conservar deadline, épocas y hechos. El transporte y las
  expectativas nativas existentes SHALL NOT proceder del payload del solicitante.
- **RH08:** CUANDO se valide esta etapa, DEBERÁ distinguir pruebas del núcleo,
  cuerpos privados/dobles y candidato enlazado con VM. La primera parte de
  RB-T3 SHALL NOT cerrar RB-T3/DW-T3 ni habilitar captura.

## Diseño y tareas

La solicitud tiene un único publicador CPU, un puntero escrito una vez y señales
atómicas de publicación/cancelación. No usa un mutex compartido ni despacha
callbacks desde DW. El puerto `RuntimeDiagnosticQueue` recibe un deadline absoluto
local. El adaptador privado compone ese puerto con VMManager y `RunOnCPUThread`
asíncrono. El propietario IO conserva la solicitud y cancela antes de abandonarla.
Reloj y puertos deberán sobrevivir a sus usos; el callback solo toma referencias
al puerto durante la ejecución CPU.

El ticket distingue revocación de retirada. El dueño runtime confirma retirada
después de `RetainedDrain::retire`; su destructor solo revoca y no inventa una
confirmación. El cierre cooperativo puede devolver pendiente y exige reintento
del dueño IO; no se destruye DW ni se atribuye unión cuando falta esa evidencia.

- [x] **RH-T1 / RB-T3a:** implementar solicitud, deadline y confirmación CPU;
  probar publicación/cancelación, callback tardío, duplicado, reloj y agotamiento.
- [x] **RH-T2 / RB-T3a:** conectar adaptador privado IO→CPU→ticket→DW/entrega;
  ejecutar cuerpos exactos, rechazo/cierre y unidades completas ON/OFF.
- [x] **RH-T3 / RB-T3a:** regresiones, sanitizadores, controles negativos,
  custodia y pipeline. Mantener pendientes el enlace y VM de RB-T3b.
- [ ] **RB-T3b / DW-T3c:** conectar launcher/socket/inventario nativo al frontend
  enlazado bajo IB02, ejecutar con VM y validar lifecycle/callbacks/gates/escritores.

Evidencia: [SRC114](../docs/execution/f02-07-runtime-handoff.md). RB-T3b requiere
la sesión nativa completa y un candidato enlazado probado con VM.

Desglose posterior de RB-T3b: [RS01–RS07](runtime-session-v1.md). RS-T1/RS-T2
completan protocolo de sesión y transporte; RS-T3 conserva launcher, inventario
nativo válido, enlace y VM pendientes.
