# Probe de semáforo para CQ3-A

`work_sema.cpp` aporta únicamente orquestación y un reemplazo de KernelSemaphore
mediante semáforos de C++20. La clase WorkSema, cinco cuerpos de sus métodos y
WaitVU se extraen sin cambios a siete includes privados del proveedor fijado.
Los hooks del reemplazo ordenan los adversarios sin sleeps ni carreras deliberadas.

Cinco escenarios: publicación de efectos completados, muerte durante/antes de
la espera, efectos ociosos después de señalar vacío, productor posterior a la
señal y descarte del resultado fallido en el cuerpo real de WaitVU.

El código compuesto se ejecuta en normal y con ASan/UBSan. WorkSema y WaitVU son
reales; KernelSemaphore, el bucle de trabajador y los efectos son propios. No se
ejecutan MTGS::MainLoop, un renderizador, los semáforos nativos de PCSX2, Qt ni VM.
El probe demuestra por qué estas APIs no bastan para conceder exclusión.

Los includes y ejecutables permanecen privados. Este fixture no pertenece al
CTest público porque necesita esas fuentes; no añade dependencias a CI ni al
runtime Nintendo. Los resultados y hashes están en
[SRC75](../../../docs/execution/f02-07-worker-producers.md).
