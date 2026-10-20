# Retención integrada de MTVU v1

Historia: como investigador necesito detener MTVU después de sus comandos ya
publicados, para preparar una observación sin atribuir a ese acuse la exclusión
de GS, CPU, PINE ni otros escritores.

## Requisitos EARS

- **VC01:** CUANDO entre una nueva ejecución de MTVU, el adaptador DEBERÁ publicar
  una generación creciente, conservada entre Reset; SI se agota, DEBERÁ rechazar
  nuevas solicitudes sin reciclar identidades.
- **VC02:** CUANDO se solicite retención, el adaptador DEBERÁ admitirla solamente
  desde CPU pausada en frontera válida, con generación e ID válidos y sin otra
  solicitud propia; DEBERÁ publicar request antes de avisar WorkSema directamente.
- **VC03:** CUANDO MTVU despierte, DEBERÁ terminar los comandos anteriores,
  FinishGSPacketMTVU, semaXGkick, ciclos y CommitReadPos antes de acusar retención.
- **VC04:** MIENTRAS el token esté held, MTVU DEBERÁ esperar el canal de control
  sin ejecutar comandos, dormir en WorkSema ni salir por shutdown o plazo local.
- **VC05:** CUANDO CPU publique trabajo, reinicie o cierre, DEBERÁ cancelar su
  token antes de los efectos y de Join; una liberación de otra generación o
  desde otro hilo DEBERÁ rechazarse.
- **VC06:** CUANDO termine el worker, DEBERÁ resolver stop antes de Kill,
  reintentando retry y esperando release si está retenido; cancelación pendiente
  y cierre DEBERÁN impedir que un acuse tardío conserve la retención.
- **VC07:** CUANDO se verifique la integración, DEBERÁN ejecutarse los cuerpos
  exactos privados con comandos sintéticos, efectos dobles y semáforos nativos;
  DEBERÁN cubrirse cancelación, plazo, cierre, reinicio y dependencia de espacio GS.
- **VC08:** CUANDO se publique evidencia, DEBERÁN conservarse fuentes y fallos
  anteriores, compilar objetos ON/OFF y mantener rechazado el puerto global;
  la prueba aislada NO DEBERÁ presentarse como VM ni captura real.

## Diseño y tareas

WorkerControl conserva la máquina de estados; VU_Thread adapta vida, cola y
despertar. VMManager valida actor/frontera y cancela antes de transiciones.
El token propio pertenece exclusivamente a CPU; generación pertenece al worker.
Las consultas públicas usan solamente los atómicos del core. La instancia y sus
dos canales de aviso sobreviven a todas las ejecuciones del hilo.

Request no publica un paquete y no utiliza KickStart. El worker acusa al terminar
el lote, incluso si estaba vacío. Después de adquirir el token vuelve a comprobar
la cola: la consulta vacía anterior pudo preceder a la publicación CPU/request.
Un aviso entre esa consulta y WaitForWork queda
retenido por WorkSema. Durante held usa esperas acotadas de ControlWakeup para
reconsultar el estado, sin que el vencimiento libere permisos. GS permanece activo.

El guard de productor cancela también la solicitud VU aislada: todavía no existe
un coordinador global que la posea. StopObserverPineDrain cancela antes de sus
transiciones existentes. Esto no certifica productores arbitrarios ajenos a CPU.

- **IW-VU1 / VC01–02,05:** copia nueva, core privado, API y guardias de propiedad.
- **IW-VU2 / VC03–06:** servicio de lote y epílogo en ExecuteRingBuffer real.
- **IW-VU3 / VC07–08:** probe exacto, objetos ON/OFF, sanitizadores, controles
  negativos y auditoría de custodia. GS y coordinación siguen en tareas separadas.
