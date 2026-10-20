# Fronteras y despertar VU/GS v1 — WB01–WB10

B3-B3a/b concreta la integración del [buzón WC](worker-control-v1.md) y del
[drenaje WD](worker-drain-v1.md). Estas obligaciones no habilitan captura.

- **WB01:** WHEN VU acusa retención THEN SHALL haber terminado todos los comandos
  anteriores, sus efectos, FinishGSPacketMTVU, semaXGkick y CommitReadPos. WHILE
  VU drena THEN GS SHALL poder consumir y liberar espacio. Un programa VU todavía
  ejecutándose SHALL NOT ser considerado retenido por igualdad de posiciones.
- **WB02:** WHEN GS acusa THEN SHALL haber terminado comandos, callbacks y
  señales de fin de lote, y SHALL soltar RingBufferBusy2 antes del acuse. WHILE
  está held THEN SHALL NOT consumir, presentar, actualizar métricas ni cerrar GS.
  El siguiente efecto y la readquisición del mutex requieren liberación CPU.
- **WB03:** WHEN CPU publica una solicitud aceptada THEN el adaptador SHALL
  notificar directamente WorkSema después de request. SHALL NOT reservar datos,
  usar AsyncCall ni llamar un productor que cancele el propio intento. Un aviso
  sin datos SHALL ser legal; un aviso por sí solo SHALL NOT significar acuse.
- **WB04:** WHEN el worker despierta o alcanza fin de lote THEN SHALL volver a
  comprobar control/cierre antes de entrar en otra espera. WHILE held THEN SHALL
  esperar solo liberación en ControlWakeup, sin WaitForEmpty, Qt ni mutex del
  proveedor. Un aviso antiguo SHALL NOT reactivar un token cancelado.
- **WB05:** WHEN empieza un worker VU o una sesión GS operativa THEN SHALL
  publicar una generación nueva desde su hilo. WHEN acaba THEN SHALL publicar
  offline antes de teardown/Kill y solo tras retirar held. GS cerrado, abriendo,
  fallido o sin generación disponible SHALL producir rechazo, nunca éxito vacío.
- **WB06:** WHEN hay cierre, reset, reapertura o trabajo tardío CPU THEN SHALL
  liberar GS antes de VU y antes del primer efecto o join. IF stop retorna
  retained/retry THEN el worker SHALL continuar vivo hasta resolver el resultado.
  La bandera open, Joinable o MTVU=false SHALL NOT sustituir evidencia de vida.
- **WB07:** WHEN el plazo CPU expira THEN SHALL cancelar/liberar y rechazar el
  intento antes de despachar Qt. Un plazo de espera del worker SHALL NOT retirar
  held por su cuenta. UI deberá poder atender callbacks síncronos de GS; una
  ruta CPU/UI bloqueante desconocida SHALL mantener el perfil no admitido.
- **WB08:** WHEN se selecciona una frontera THEN SHALL inventariar efectos y
  locks a ambos lados con archivo, líneas y hash de la fuente fijada. SHALL
  distinguir apagado ordenado de terminación abrupta y una sesión GS del hilo
  nativo persistente. Una salida no instrumentada SHALL impedir admisión.
- **WB09:** WHEN se valida el puente THEN SHALL probar avisos antes/durante espera,
  cancelación, cola llena, dependencia VU→GS, idle, mutex, cierre y reinicio;
  SHALL distinguir WorkSema real, semáforo nativo/doble y bucles modelados de
  ExecuteRingBuffer/MainLoop y frontend completos.
- **WB10:** WHILE no se conectan y validan las fronteras reales THEN SHALL
  conservar EffectDrainPort rechazado, modos admitidos vacíos y fuentes previas
  intactas. Un probe del puente SHALL NOT autorizar captura ni cierre de CQ3-C.

## Decisiones de diseño

El adaptador de cada worker publica request y después llama al NotifyOfWork de
su WorkSema, sin tocar cola o contadores de paquetes. Se reutiliza la puerta de
despertar del bucle existente y se conserva el buzón como única autoridad del
acuse. No se añade un segundo consumidor ni se modifica el algoritmo WorkSema.
No se usa VU::KickStart: su guardia BeforeObserverProducer cancelaría la fase de
efectos. Tampoco se usa MTGS::SetEvent, que además cambia CopyDataTally.

La futura integración ejecutará el servicio de control al volver de WaitForWork
y al terminar el lote, antes de poder dormir/presentar otra vez. Un request
publicado entre una comprobación y WaitForWork queda representado por
NotifyOfWork; el retorno de esa espera siempre debe consultar el buzón. Un aviso
recibido mientras el worker ya trabaja puede generar otra vuelta sin datos.

La transición a held se permite únicamente con productores CPU cerrados y datos
anteriores drenados. VU acusa después del último CommitReadPos. GS acusa después
del fin de lote y señales OnRingReset/Vsync, con su unique_lock liberado y antes
de la siguiente presentación ociosa. Si llega control durante un efecto/idle,
este termina antes del acuse; no se interrumpe ni descarta a mitad de comando.

Una vez held, el worker consulta su token y espera en ControlWakeup hasta que CPU
lo retire. El acuse fallido por cancelación no detiene el trabajo. Release publica
permiso de continuar; no acredita que GS ya haya vuelto a ejecutar. El orden de
liberación GS→VU evita mantener la retención de GS cuando VU vuelve a producir.

VU publica vida en ExecuteRingBuffer; una sesión GS la publica después de GSopen
exitoso y antes de MainLoop. GSopen fallido no publica una sesión operativa.
MainLoop termina su generación antes de igualar posiciones/Kill/GSclose; VU lo
hace antes de Kill. El contador de generación sobrevive al Reset de WorkSema y
a las reaperturas del hilo GS. Su agotamiento rechaza la observación.

El coordinador conserva PINE mientras libera ambas fases. Solo el actor CPU
cancela; una solicitud de cierre ajena debe entregarse a ese actor sin modificar
flags primero. No hay revocación de held por timeout local del worker ni permiso
para ejecutar teardown desde otro hilo. Fallos abruptos, bypass de epílogos y
rutas de UI/CPU no cubiertas siguen siendo impedimentos de admisión.

## Tareas

- **WB-T1 / WB01–08:** fijar puntos/orden de efectos y vida en fuentes reales;
  B3-B3a/b, incluyendo mutex, idle, métricas y callbacks de ventana.
- **WB-T2 / WB03,04,06,09:** probe con cuerpos exactos de WorkSema y WC real,
  doble determinista y KernelSemaphore Darwin real; sanitizadores y controles
  negativos del puente. Modelar VU/GS sin atribuirles ejecución del proveedor.
- **WB-T3 / WB08,10:** custodia y trazabilidad; dejar B3-B2 integración y
  B3-B3c/CQ3-C pendientes con aceptación concreta.
