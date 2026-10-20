# Harness privado de frontera CPU

El archivo público contiene únicamente dobles, datos sintéticos y oráculos propios.
Los cuerpos fijados de PCSX2 se extraen a includes privados, con hashes de origen
y fragmento. No se publica código del proveedor ni memoria del juego.

Se ejecutan CPUThreadInitialize, CPUThreadShutdown, Execute, DoLoadState,
EmuThread::run, Host::PumpMessagesOnCPUThread, las fábricas de ámbitos y el sampler.
Las ramas de inicialización específicas de arquitectura no se ejecutan aquí.
Los nueve fragmentos nuevos incluyen el estado de hilo y ScopedGuard; la copia
anterior aporta siete fragmentos y se usa únicamente con el observador OFF.

Los 45 casos comunes incluyen los 34 diagnósticos previos, cinco recorridos de
DoLoadState y seis recorridos de run/pump. ON y ASan/UBSan añaden cinco casos:
rechazo sin frontera, reentrada, actividad anidada, Execute y cierre/reinicio CPU.
Se compara el resumen de efectos de los casos comunes entre ON, OFF,
ON sanitizado y funciones anteriores OFF. Las bibliotecas propias actuales se
enlazan en todos los modos; esto no compara aplicaciones completas históricas.

QEventLoop, miembros auxiliares de EmuThread, configuración, objetos CPU,
asignación, subsistemas, estado de PINE y dependencias de DoLoadState son dobles.
La prueba no ejecuta el event loop Qt real, discos/estados, una VM, sockets ni
GS/VU. Reset/destroyVM dentro del bucle Qt son dobles; las otras transiciones
instrumentadas se compilan y sus entradas se auditan, sin afirmar ejecución de
todos sus cuerpos. Los tests portables de CpuBoundary sí entran en CTest/CI;
este harness requiere las fuentes privadas y no se ejecuta en CI pública.
