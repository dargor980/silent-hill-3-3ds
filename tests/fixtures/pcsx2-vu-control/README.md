# Probe de retención integrada MTVU

`probe.cpp` es propio. Necesita **37 fragmentos exactos privados** de PCSX2 y los
métodos propios de `tools/observer/pcsx2/vu_control.inc`. No incluye assets ni
código del proveedor en Git. La etapa final usa `source-vu-control-v2` del commit
fijado en [SRC81](../../../docs/execution/f02-07-vu-control.md).

Ejecuta ExecuteRingBuffer, Open/Close/Reset, lectura/publicación/reserva de cola,
WriteDataMem, guardias CPU y WorkSema/KernelSemaphore Darwin. La declaración de
VU_Thread es exacta, con acceso privado expuesto solo por macros del probe.
Thread usa std::thread; memoria, tipos VIF/VU, CpuVU1, GIF, semaXGkick, estado VM
y propietario PINE son dobles propios. CpuBoundary/WorkerControl son reales.
Los dobles no reproducen ABI, emulación, renderer ni efectos completos del juego.

Quince escenarios por modalidad normal/ASan-UBSan/TSan:

| Casos | Verificación |
|---|---|
| empty_wake, command_batch | Despertar sin paquete, ocho tipos útiles de comando, publicación completa antes de held |
| cancel_pending, timeout_pending | Cancelación mientras Execute está bloqueado; no aparece acuse tardío |
| stable_held | Un segundo paquete inyectado por acceso privado no se consume durante held; avanza tras release |
| producer_release | WriteDataMem real cancela antes de publicar trabajo |
| close_held, close_pending, shutdown_held | Close libera antes de Join; un shutdown directo no vence la retención |
| restart, reject_actor, exhaustion | Generación nueva, CPU/frontera/pausa, actor ajeno y agotamiento |
| full_gs_dependency | FinishGSPacketMTVU doble espera espacio; el acuse no precede a su finalización |
| wrap | ReserveSpace/NULL_PACKET y lectura real al volver al inicio |
| publication_gap | Servicio exacto en un worker de prueba: cola antes vacía, publicación CPU/request y rechazo del acuse |

Los primeros catorce casos ejecutan el bucle real. `publication_gap` usa una
frontera sincronizada propia para forzar el intervalo; no ejecuta ExecuteRingBuffer.
La dependencia GS utiliza una señal sintética de espacio, sin MainLoop GS ni su
cola real. El timeout simula vencimiento CPU con release explícito; no ejercita
el coordinador global. No se fuerzan deterministicamente los CAS retry de stop.

Cinco mutaciones privadas verifican la detección de acuse temprano, omisión de
la reconsulta de cola, omisión de espera held, despertar y cancelación CPU.
Fuentes, objetos, binarios, fallos y logs permanecen privados. La receta local
supervisada y los límites están en el informe SRC81; este probe no forma parte
de CI pública porque requiere fragmentos del proveedor.
