# Trazas privadas de preflight y registro

`preflight.inc` y `ledger.inc` reemplazan cuerpos propios en copias privadas
verificadas de PCSX2. Son instrumentación diagnóstica de [PF01–PF07](../../../schemas/native-preflight-diagnostic-v1.md);
no se incluyen en los targets de producción ni cambian el protocolo.

El primer fixture clasifica el rechazo del preflight. El segundo registra las
transiciones a fallo de `ImageLedger`; usa una línea de pila de 192 bytes y
una sola escritura, sin nueva asignación dinámica ni estado compartido.
Los veredictos, límites, ABI y orden de comprobaciones se conservan.

Los casos existentes de identidad, registro y origen se compilan contra las
copias: 60 ejecuciones iniciales y 138 al ampliar la traza, incluyendo ASan/UBSan,
eventos concurrentes, fork y bit de caché falsificado. Las fuentes y paquetes
anteriores permanecen intactos. El [informe](../../../docs/execution/f02-07-native-preflight.md)
distingue esa regresión del diagnóstico con VM y de las muestras aún pendientes.
