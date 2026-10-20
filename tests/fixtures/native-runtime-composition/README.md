# Fixture propia NR

Composición privada de frontend, sesión RS, trabajador y fábrica de inventario
nativo con un consumidor BC en otro proceso. `producer.cpp` se inyecta en una
copia PCSX2 `-testconfig` y corre al salir, sin VM. Incluye el frontend propio
sin modificarlo, sustituyendo explícitamente los puertos Host y VMManager por
dobles. CPU/IO/DW son hilos distintos; los hechos/épocas CPU son valores de prueba.

La identidad del proceso, archivos, mapas, slices, cache, hash, socket y peer son
nativos. Las expectativas del manifiesto se congelan antes del lanzamiento y
no proceden del payload. Los controles de bloqueo, fragmentación, revocación y
backpressure solo pertenecen a la fixture. Los binarios, app clonada, manifiesto
y frames permanecen fuera del repositorio; los recibos siguen supervisión
10 GiB/512 MiB. La prueba no instala ni modifica PCSX2.

La preparación y ejecución privadas se describen en
[el informe NR](../../../docs/execution/f02-07-native-runtime-composition.md).
La prueba requiere un macOS con el candidato y dependencias ya custodiados;
no forma parte de CI público ni reemplaza el enlace nuevo y validación con VM.
