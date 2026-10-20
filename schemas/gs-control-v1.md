# Retención integrada de MTGS v1

Historia: como investigador necesito retener la sesión GS después de sus efectos
anteriores y señales de finalización, sin bloquear VU mediante el mutex de cola.
Este acuse prepara una futura observación; no constituye exclusión global.

## Requisitos EARS

- **GC01:** CUANDO GSopen termine con éxito, el adaptador DEBERÁ iniciar una
  generación creciente antes de notificar apertura; SI falla, está abriendo o
  se agota la identidad, DEBERÁ rechazar solicitudes. Reset de WorkSema no DEBERÁ
  reciclar generaciones entre sesiones o reinicios del hilo.
- **GC02:** CUANDO CPU solicite retención, el adaptador DEBERÁ validar actor,
  frontera, pausa, sesión e identidad y notificar WorkSema después de request,
  sin publicar comandos ni utilizar SetEvent.
- **GC03:** CUANDO acuse retención, GS DEBERÁ haber terminado comandos, callbacks,
  publicación de readpos y señales OnRingReset/Vsync anteriores; DEBERÁ adquirir
  request antes de reconsultar cola, señales y estado operativo.
- **GC04:** MIENTRAS permanezca held, GS DEBERÁ esperar ControlWakeup sin poseer
  RingBufferBusy2 ni iniciar idle, presentación, métricas, callbacks o epílogos.
  Un plazo local no DEBERÁ liberar la retención.
- **GC05:** CUANDO CPU publique trabajo o cambie el ciclo de vida, DEBERÁ cancelar
  GS antes de VU y antes de efectos/flags/esperas de cierre. Un actor o token ajeno
  DEBERÁ ser rechazado. Este orden no DEBERÁ presentarse como coordinador global.
- **GC06:** CUANDO MainLoop termine, DEBERÁ resolver stop sin el mutex antes de
  descartar cola, Kill o GSclose; retry/held no DEBERÁN permitir salida prematura.
- **GC07:** CUANDO se pruebe la integración, DEBERÁN ejecutarse MainLoop y ciclo
  de vida exactos privados con datos/efectos propios, semáforos reales y controles
  negativos para acuse, mutex, espera, despertar y cancelación.
- **GC08:** CUANDO se cierre la unidad, DEBERÁN conservarse copias anteriores,
  compilar objetos ON/OFF y auditar evidencia repetible. EffectDrainPort DEBERÁ
  seguir rejected mientras no se verifiquen coordinador y escritores globales.

## Diseño

WorkerControl conserva la máquina de estados; el adaptador MTGS conecta cola,
sesión y mutex. VMManager valida CPU y cancela GS→VU antes de productores y
transiciones existentes. Tokens propios pertenecen a CPU, generación y estado
de sesión al worker; las consultas externas usan los atómicos del core.

ThreadEntryPoint inicia control únicamente después de GSopen exitoso y antes
de notificar al caller. MainLoop consulta antes de la próxima rama idle/espera;
al volver de WaitForWork procesa el lote y señales antes de la siguiente consulta.
El servicio adquiere token, revalida cola/señales/open, suelta el mutex y acusa.
Tras release readquiere el mutex; al cerrar publica offline antes del epílogo.
Un request concurrente con el vacío queda cubierto por reconsulta y WorkSema.

SetRunIdle pertenece al worker GS y permanece dentro de sus efectos. El canal
no añade waiter de WaitForEmpty, no cambia WorkSema y no utiliza UI para esperar.
Una sesión offline no acredita ausencia global de escritores durante GSclose.
El futuro coordinador solicitará GS después de VU; esta unidad no lo conecta.

## Tareas y aceptación

- **IW-GS1 / GC01,02,05:** copia nueva, API de sesión y cancelación CPU GS→VU;
  comprobar apertura fallida, reapertura, agotamiento y actor/frontera/pausa.
- **IW-GS2 / GC03,04,06:** servicio en MainLoop y epílogo; probar lote/señales,
  mutex disponible, idle estable, callbacks y dependencia MTVU antes del acuse.
- **IW-GS3 / GC07,08:** objetos ON/OFF, normal/ASan-UBSan/TSan, negativos,
  custodia SRC81 y auditorías repetibles; documentar límites de los dobles.
