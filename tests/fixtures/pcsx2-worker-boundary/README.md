# Probe de fronteras y despertar — SRC80

probe.cpp es orquestación propia; incluye ocho fragmentos exactos preparados
solo en una etapa privada. Ejecuta WorkerControl/ControlWakeup propios y la clase
WorkSema con CheckForWork, WaitForWork, WaitForEmpty, Kill y Reset del proveedor.
En modo nativo incluye también KernelSemaphore y sus cuerpos Darwin/MACH_CHECK.

Nueve casos comunes: aviso previo a espera, aviso cancelado, stop durante held,
idle, mutex ocupado, cola llena/dependencia VU→GS, reinicio, cierre pendiente y
timeout pendiente. El doble añade sleeping_wait: un hook justo antes de adquirir
el semáforo confirma que WorkSema ya publicó SLEEPING antes de enviar control.
El hook pertenece al doble, no modifica los cuerpos WorkSema del proveedor.

Los nueve casos pasan con semáforos Mach reales; esa variante no instrumenta el
instante exacto de entrada al kernel. No se presupone que cada aviso llegue cuando
el hilo ya está dormido. Ambos modos se prueban en normal, ASan/UBSan y TSan:
**57 ejecuciones**, más tres controles negativos separados.

Los workers, payloads, cola de una posición, mutex, idle y coordinador son modelos
propios. No se ejecutan MTGS::MainLoop, VU_Thread::ExecuteRingBuffer, renderer, UI,
VM, juego ni semáforos KernelSemaphore de Linux/Windows. La prueba se limita al
puente propuesto y no demuestra ausencia global de escritores del proveedor.

El compilador usa C++20, pthread, tools/observer/include, tests/cpp y la carpeta
privada de includes. WB_NATIVE_SEMAPHORE selecciona la variante Mach. Cada
ejecución recibe un caso; el runner local de build/f02-07-worker-boundary genera
binarios, logs, límites y recibos. El informe SRC80 conserva receta y hashes.
La CI pública no requiere ni incluye esos fragmentos privados.

Los controles negativos mutan copias privadas del probe: conservar el mutex
durante held, ejecutar idle antes de release y omitir NotifyOfWork. Los dos
primeros deben fallar por aserción; el tercero debe agotar el plazo del supervisor,
que termina el grupo de procesos y verifica que no queden hijos vivos.
