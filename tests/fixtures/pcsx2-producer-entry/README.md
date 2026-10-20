# Entradas productoras B2

Harness propio; 22 fragmentos exactos del proveedor fijado permanecen en la etapa
privada. Incluyen 16 cuerpos de entradas de MTGS/GIF/MTVU, Stop/Before/Activity,
slot/despacho CPU y el bloque de LocaleChanged. Los controladores RetainedDrain,
PineDrain, CpuBoundary y CooperativeGate son reales. El puerto de efectos es un
reemplazo que permite pendiente/retenido/rechazado; el puerto productivo sigue
rechazando. Las colas, semáforos, registros y operaciones GS/VU son dobles.

La matriz tiene 22 operaciones × 5 fases: sin intento, drenaje PINE con reserva
previa, fase posterior pendiente, retenida y rechazada sin retirar. Comprueba
orden de liberación, PINE cerrado durante release, datos FIFO, readAmount, bytes
VU, retorno y punteros de snapshot/freeze, y propiedad de un callback demorado.
El modo de copia GIF se fuerza en el doble para comprobar ambas ramas; no es
una prueba de ambas configuraciones reales del proveedor.

Seis escenarios de idioma: sin EmuThread, GS cerrado al despachar CPU,
FullscreenUI destruida antes del despacho GS, entrega normal, inicialización
tardía y retención vigente al llegar el callback CPU. Se ejecutan slot y
RunOnCPUThread reales con un reemplazo de QMetaObject/cola, sin event loop Qt.
La copia anterior OFF ejecuta su bloque histórico, cuya ruta directa y semántica
son distintas intencionalmente. Su digest comparable excluye estos seis casos.
ON/sanitizadores añaden un caso de hilo ajeno: no accede al propietario CPU;
el intento solo se retira cuando el aviso llega al propietario.

No se ejecutan los otros 22 hooks (solo compilación y auditoría de posición),
los cuerpos reales de Get_MTVUChanges/KickStart, ringbuffers, workers, Qt completo,
socket PINE ni VM. Get_MTVUChanges/KickStart usados por ExecuteVU son dobles que
registran efectos. No se prueba exclusión de hilos ajenos ni retención real.

Cuatro modalidades: ON, OFF, ASan/UBSan y SRC76 OFF. El fixture no pertenece al
CTest público porque requiere fuentes privadas; CI continúa sin esa dependencia.
Las compilaciones y el harness se ejecutan localmente con límites de tiempo y
almacenamiento. La evidencia y los comandos están en
[SRC77](../../../docs/execution/f02-07-producer-entry.md).
