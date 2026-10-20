# Probe de retención integrada GS

`probe.cpp` es propio. Compila con **30 fragmentos exactos privados** del commit
PCSX2 fijado y [gs_control.inc](../../../tools/observer/pcsx2/gs_control.inc),
según [GC01–GC08](../../../schemas/gs-control-v1.md). No publica cuerpos del
proveedor ni datos del juego.

Ejecuta MainLoop, ThreadEntryPoint, apertura/cierre, productores de paquetes,
WaitGS y guardias VMManager reales. WorkSema y KernelSemaphore usan los cuerpos
Darwin/Mach originales. WorkerControl y CpuBoundary son reales. El probe expone
el acceso privado de WorkSema mediante una macro, sin cambiar sus instrucciones,
para observar STATE_SLEEPING antes de solicitar el despertar.

Thread usa std::thread. UserspaceSemaphore, renderer, GSopen/GSclose, tipos/ABI,
registros, GIF, copia envuelta, VU, propietario PINE y frontend son dobles propios.
Estos dobles permiten bloquear y contar efectos; no simulan el juego ni GPU.
Se usa COPY_GS_PACKET_TO_MTGS=0, como la fuente fijada; no se ejercitan las ramas
alternativas GIFPath1–3 de la configuración 1 ni RINGBUF_DEBUG_STACK/DEVBUILD.

| Escenarios | Verificación |
|---|---|
| empty_wake | Worker realmente dormido, aviso directo sin cambiar CopyDataTally y mutex disponible durante held |
| batch | Reset, SoftReset, Freeze, FIFO, GSPacket, MTVUGSPacket, AsyncCall, VSync y señales antes del acuse |
| idle_boundary, stable_held | Idle iniciado termina antes de held; presentación/callback inyectado no avanzan bajo retención |
| cancel_pending, timeout_pending | Cancelación explícita mientras un callback bloquea; no hay acuse tardío |
| producer_release, owner_release | Cancelación por productor y retiro del intento; GS se libera antes de invocar el doble VU |
| close_held, close_pending, shutdown_held | Cierre cancela antes de flags/esperas; un flag de cierre directo no vence held |
| reopen, restart_thread, failed_open, opening, exhaustion | Generación por sesión exitosa, rechazo al abrir/fallar/agotarse y persistencia entre hilos |
| reject_actor | CPU/frontera/pausa, token y actor ajeno |
| mtvu_dependency | No acusar hasta consumir semaXGkick, paquete y Pop; VU/semaXGkick son dobles |
| signals_before_ack | Post de OnRingReset bloqueado debe terminar antes del acuse |
| publication_gap, signals_gap | Servicio exacto en worker propio: publicaciones posteriores a un vacío anterior impiden acusar |

Son 21 casos por modalidad normal, ASan/UBSan y TSan: **63 ejecuciones finales**.
Diecinueve por modalidad ejecutan MainLoop/ThreadEntryPoint; las dos intercalaciones
finales usan directamente el servicio en una frontera sintética. `opening` inicia
la apertura de forma asíncrona desde el probe para observar su estado intermedio.
El timeout usa release CPU explícito; no prueba el coordinador pendiente.

Seis negativos omiten desbloqueo, espera held, reconsulta de cola, señales,
despertar o cancelación. Se exige aserción prevista o plazo del supervisor y
cierre verificado del grupo. Las aserciones pueden terminar con SIGABRT al
destruir el wrapper std::thread global que sigue activo; no se interpreta como
un cierre limpio del proveedor.

La regresión VU vuelve a ejecutar los quince escenarios de SRC81 en tres modos,
con cuerpos VMManager actualizados y un doble privado de CancelObserverControl GS.
Los dos workers todavía no se prueban como una VM conjunta. Fuentes compuestas,
scripts, binarios y logs se conservan privados/locales. El probe no se incluye en
CI pública; [SRC82](../../../docs/execution/f02-07-gs-control.md) contiene la receta.
