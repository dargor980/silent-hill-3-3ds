# Entradas y bombeo Qt — B3-A

Harness propio con QtCore instalado y 14 cuerpos exactos del proveedor, extraídos
como includes privados. RetainedDrain, PineDrain, gate y frontera son reales;
VMManager/GS/input/configuración son dobles. El receptor EmuThread es un QObject
propio con afinidad Qt real: no ejecuta la clase QThread completa del proveedor.

Matriz: ocho entradas × cinco fases × dos entregas (directa/encolada) = 80 casos.
Cubre pantalla completa, surfaceless, foco/input, polling, shutdown, configuración
y arranque/parada del timer. Otros 20 casos despachan un receptor QObject distinto,
un timer de intervalo cero, contexto destruido sin ejecutar callback y bombeo
anidado. Diez casos ejecutan RunOnCPUThread inline/encolado; dos invocan las rutas
reales de reenvío desde otro hilo. Total: 112 por modalidad ON/OFF/ASan-UBSan/
SRC77 OFF, comparando efectos y duración del payload retenido por Qt.

El puerto simulado permite pendiente/retenido/rechazado sin retirar. Se verifica
que release ocurre antes de flags, efectos y creación de eventos, que PINE sigue
cerrado durante release y que las reservas previas pueden progresar. El puerto
productivo permanece rechazado. En el probe CPU corresponde al hilo de la
QCoreApplication; el hilo remitente simula UI y no hay ventana gráfica.

Se ejecutan nueve entradas nuevas y cinco cuerpos previos del puente/despacho.
Otras 36 entradas y tres puntos del bucle principal se compilan/auditan, sin
ejecutar el EmuThread completo. Los timers y QMetaObject son reales; no se simulan
sus colas. No se prueban workers, ringbuffers, canales de control ni la VM.

Dos controles negativos aislados retiran el aviso de setFullscreen o del bombeo
Host: deben fallar al ejecutar flags/efectos con el intento todavía retenido.
No alteran las fuentes auditadas. El fixture requiere fuentes privadas y no se
incorpora a CTest público ni añade dependencias al runtime Nintendo.

Resultados, límites y receta: [SRC78](../../../docs/execution/f02-07-qt-dispatch.md).
