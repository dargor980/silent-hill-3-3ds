# Servidor PINE y coordinador — SRC87

`server.cpp` ejecuta los cuerpos exactos privados de Initialize, AcceptClient,
MainLoop, ClientLoop, ParseCommand, Deinitialize y dispatch. Usa sockets Unix y
thread nativos; VM, RAM de 256 bytes y efectos de save/load son dobles propios.
Cada proceso recibe TMPDIR corto y privado, slot 38187, sin acceder al servidor,
ISO, BIOS o sesión del usuario. El supervisor exige terminar todos sus procesos.

Catorce casos en normal, ASan/UBSan y TSan: status, memory, partial, closed,
queued, observer_timeout, connected_stop, partial_stop, coalesced, restart,
disconnect, idle_stop, discard y stress_stop. Son 42 ejecuciones finales. Los
reinicios incluyen clientes inactivos, mensajes parciales y ausencia de cliente.
La fragmentación enviada por el cliente no garantiza cómo el kernel agrupa cada
lectura; coalesced sí comprueba dos respuestas para dos mensajes consecutivos.

`joint.cpp` y `joint_support.hpp` sustituyen el doble PINE de SRC83 por ese
servidor, conservando 71 fragmentos exactos de workers, Mach, dueño y Qt, más
servidor y dispatch. CPU es el hilo principal de QCoreApplication; PINE es un
thread distinto y su callback atraviesa invokeMethod/slot reales. VU/GS ejecutan
sus bucles reales con efectos sintéticos. No es una prueba de QWidget ni VM.

Siete casos en las tres modalidades: prior, discard, timeout, generation,
stop_pending, deadline y late. Son 21 ejecuciones finales. Comprueban:

- Reserva anterior impide solicitar VU/GS y permite progreso de la cola CPU.
- Timeout de Completion no libera trabajo aún encolado; no ejecuta Reader tarde.
- removePostedEvents destruye el callback y libera su reserva sin ejecutar el efecto.
- Cambio de generación invalida intentos, incluso con trabajo previo todavía vivo.
- Deadline retira el intento; el callback puede terminar después sin retenciones.
- Entrada posterior al cierre falla antes de escribir; recuperación acepta trabajo.

TSan usa QtCore 6.11.1 instrumentado previamente y verifica la librería cargada.
No emplea supresiones. Tres mutaciones eliminan reservas de load/Completion o
congelan la generación, y deben provocar la aserción correspondiente. Los fallos
de fuente base, la primera reparación incompleta y su pila se conservan privados.

La reproducción necesita la fuente fijada y el staging privado; no se publican
fragmentos PCSX2, parches ni binarios compuestos. Las fixtures públicas son código
propio y no leen recursos del juego. El enlace completo nuevo requiere IB02;
estos probes y los dos objetos ON/OFF no lo sustituyen.
