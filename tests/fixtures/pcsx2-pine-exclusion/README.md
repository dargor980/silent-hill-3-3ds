# Fixtures de exclusión PINE

El harness contiene datos y dobles propios; los fragmentos del proveedor y del
adaptador se inyectan desde la etapa privada. La nueva copia aporta siete
fragmentos exactos: ParseCommand, MakeOkIPC, MakeFailIPC, SafetyChecks, declaración
del gate, API de cierre y dispatch. La anterior aporta cinco; su dispatch queda
desactivado en OFF y gate/API de cierre se representan por archivos vacíos.

Se comparan **44 escenarios comunes** en ON/OFF/sanitizadores/anterior OFF:
lecturas/escrituras de cuatro tamaños, truncamientos, VM inválida, metadatos,
comandos desconocidos, efectos parciales, guardado/carga y callbacks de error.
Respuestas, bytes sintéticos y contadores de efectos deben coincidir.

En ON y sanitizadores se añaden **13 escenarios de exclusión**: rechazo antes de
efectos, liberación por error, trabajos CPU pendientes, error retenido por save,
descarte de colas/copias, timeout, contendientes, escritor concurrente y observador
que responde, expira en cola o expira durante su callback. Los dos últimos usan
la espera real de dos segundos de Completion y el cuerpo exacto de dispatch.

El parser, formato de respuestas y SafetyChecks son cuerpos privados exactos.
FromSpan y ToResultVector son dobles que usan memcpy: no se ejercita el cast
desalineado de FromSpan del proveedor. RAM/VTLB, estados, metadatos, guardado,
carga, colas Qt y lector de captura son dobles. El lector devuelve rechazo por
pausa; no lee bytes del juego. La concurrencia usa hilos host controlados, no
trabajadores reales de PCSX2 ni sockets.

El resumen de efectos solo compara los 44 escenarios comunes; los trece casos
de rechazo intencional requieren oráculos distintos. No prueba equivalencia
exhaustiva del proveedor, finalización de GS/VU, cierre del servidor, integración
del coordinador, ausencia global de deadlocks ni continuidad real.

[Contrato PE01–PE09](../../../schemas/pine-exclusion-v1.md).
