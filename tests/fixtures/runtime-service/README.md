# Servicio del candidato enlazado

`launcher.py` conecta el consumidor BC al servicio compilado dentro de PCSX2.
No inyecta una biblioteca ni reemplaza Host/VMManager. Recibe configuración local
del procedimiento privado antes de crear el hijo, autentica su identidad nativa
y conserva respuestas/resultado de cierre. Los originales y perfiles son privados.

Las pruebas `test_runtime_service.cpp` y `runtime_service_oracle.py` usan el
servicio y socket reales, pero **cola CPU y snapshot de VM de prueba**. Cubren
configuración, ausencia de activación, espera de pausa, cancelación, callback
tardío, rechazo de cola, manifiesto ausente, desconexión y retiro CPU retenido.
No producen evidencia de inventario válido ni equivalen a ejecutar una VM.

El launcher de candidato conserva fallos de proceso y no acepta `clean=1` de IO
como prueba de salida correcta: exige también código cero del hijo. Fija
`TMPDIR` (PINE en macOS) y `XDG_RUNTIME_DIR` a un directorio privado corto y
registra los sockets PINE presentes al conectar. Los perfiles
batch deben desactivar el diálogo de confirmación
de apagado y evitar guardados. El modo batch requiere una ISO/BIOS de arranque;
el control sin VM usa el frontend normal. Véase [RT01–RT07](../../../schemas/runtime-service-v1.md).

Excepción explícita: los perfiles [VS](../../../schemas/runtime-vm-shutdown-v1.md)
usan modo normal, confirmación activada y guardados/memcards desactivados.
`vm_shutdown_integration.py` aplica las inserciones propias sobre las fuentes
privadas fijadas. `vm_shutdown_probe.hpp` y `vm_shutdown_probe_qt.inc` observan
acciones, diálogo real y retención de VM/lista; se excluyen del candidato limpio.
`vm_shutdown_launcher.py` conserva consumidor y verificador congelados, registra
trazas y exige salida real del hijo. Los perfiles externos sin sonda requieren
además observación CUA: un resultado de proceso no prueba por sí solo la decisión
del diálogo. Véase [SRC126](../../../docs/execution/f02-07-vm-shutdown.md).

Las fixtures `host_callback_*` corresponden a [HC](../../../schemas/runtime-host-callback-v1.md).
La demora se inyecta antes de despachar a Host y la duplicación usa invocaciones
Qt encoladas reales. La sonda queda fuera del candidato limpio. Los perfiles
`tardíos` mantienen un peer autenticado sin solicitudes hasta EOF; los duplicados
usan el consumidor congelado. Un peer ya cerrado puede ser rechazado antes de
autenticarse: no se publica identidad ni diagnóstico a partir de ese rechazo.
Los logs originales, reevaluaciones del checker y límites se conservan en
[SRC127](../../../docs/execution/f02-07-host-callback.md).
