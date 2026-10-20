# Llamadores bloqueantes y dependencias — BC01–BC07

Como mantenedor necesito distinguir las esperas retiradas por ExternalWaits de
los locks y esperas del propio callback, antes de acreditar exclusión global.

- **BC01:** WHEN se inventarían llamadores THEN SHALL fijar fuente/hash/rango,
  argumento block y destino. Las llamadas asíncronas con una espera posterior
  SHALL identificarse aparte, sin atribuirles automáticamente el scope Qt.
- **BC02:** WHEN un callback bloqueante toma un lock, espera red/dispositivo o
  despacha síncronamente a otro hilo THEN SHALL registrar esa dependencia y su
  propietario; la ausencia de un lock en el llamador SHALL NOT demostrar que
  el cuerpo completo sea no bloqueante.
- **BC03:** IF una ruta depende de backend, cuenta, plataforma o ramas no
  ejecutadas THEN SHALL conservar estado desconocido o rechazo. Un grep o una
  prueba con dobles SHALL NOT conceder admisión global.
- **BC04:** WHEN la ruta usa PINE Work y espera Completion THEN SHALL comprobar
  el alcance de la reserva y distinguir el rechazo de nuevas entradas del
  trabajo ya encolado, que debe poder terminar sin una retención VU/GS activa.
- **BC05:** WHEN se prueba una dependencia de lock adversaria THEN SHALL
  diferenciar cancelación del observador y progreso del callback. El ensayo
  SHALL terminar de forma acotada y liberar el lock controlado sin esconder
  un bloqueo real con una supresión o un resultado de timeout aceptado.
- **BC06:** WHEN se publica el inventario THEN SHALL conservar cuerpos privados,
  publicar metadatos y verificar dos resultados iguales contra fuentes fijadas.
  Una modificación del proveedor exige nueva copia y su propia validación.
- **BC07:** WHILE existan dependencias desconocidas THEN SHALL mantener admisión
  vacía y transporte de armado cerrado; no cambiar funciones ajenas para que
  un ejemplo sintético aparente progreso.

## Diseño y tareas

Inventario de lectura sobre SRC85: referencias léxicas más revisión del argumento
final y del cuerpo relevante. Se separan metadatos verificables, inferencias y
validación pendiente. La búsqueda no pretende resolver un grafo C++ universal.
Un ensayo QtCore propio con un lock controlado verifica el límite del protocolo.
No usa cuentas ni servicios externos y no modifica el proveedor.

- **IW-CALLERS1 / BC01–04:** fijar llamadas RunOnCPUThread, conexiones Qt
  bloqueantes, ruta Completion/PINE y dependencias de los callbacks síncronos.
- **IW-CALLERS2 / BC05:** reproducir cancelación seguida de callback esperando
  un lock de un hilo adversario; comprobar retiro anterior al efecto y entrega única
  al liberar el adversario. Normal, ASan/UBSan y QtCore TSan, sin red.
- **IW-CALLERS3 / BC03,06,07:** auditar custodia, clasificar lo demostrado y lo
  desconocido, y concretar la prueba pendiente PINE/frontend/VM sin cambiar
  admisión por inferencia.
