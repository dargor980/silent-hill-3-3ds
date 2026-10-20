# Probe conjunto VU/GS

Fixture propio para SRC83. Recibe 64 fragmentos exactos desde una copia privada
del proveedor; no contiene esos cuerpos ni datos del juego.

Ejecuta juntos ExecuteRingBuffer, MainLoop, ThreadEntryPoint, puentes de control,
entradas/cierre, métodos del coordinador VMManager y el bloque de despacho de
EmuThread. Usa WorkerDrain/RetainedDrain/CpuBoundary/CooperativeGate reales,
WorkSema del proveedor, KernelSemaphore Darwin y entrega QtCore real.

Son dobles el wrapper de hilo, UserspaceSemaphore, ABI/tipos VU/GIF, renderer,
ejecución VU, servidor PINE, épocas host y efectos de aplicación. El reloj es real.
No ejecuta EmuThread completo, Qt Widgets, una VM PS2 ni la consola Nintendo.
La ruta GIF fijada es COPY_GS_PACKET_TO_MTGS=0; no acredita otras ramas.

El caso full_dependency llena todas las posiciones utilizables del ring GS con
escrituras privadas de prueba, después de bloquear un callback previo. El bucle GS
real libera la dependencia de FinishGSPacketMTVU simulado y espera semaXGkick;
VU termina sus efectos y acusa antes de que el coordinador solicite GS. El caso
no acredita ReserveSpace ni todos los productores de cola llena.

Los casos Qt conservan el payload de un callback encolado, permiten el bombeo
durante el drenaje inicial PINE y lo posponen durante control VU/GS. Un timeout
retira ambos propietarios antes de volver a entregar el callback.

Los escenarios de cancelación, plazo y época cubren VU pending, VU held/GS pending
y ambos held. Otros prueban productor tardío, cierre pending, reinicio y offline.
Normal, ASan/UBSan y TSan se ejecutan localmente con límites de tiempo/espacio.
El CI portable incorpora los tests del núcleo mediante CMake; este probe depende
del checkout privado, Qt local y Mach, y no forma parte del CI público.
