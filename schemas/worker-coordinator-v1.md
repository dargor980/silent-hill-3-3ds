# Coordinación VU → GS v1 — WCJ01–WCJ10

IW-COORD conecta el puerto de efectos de RetainedDrain. No autoriza captura.

- **WCJ01:** WHEN empieza un intento THEN SHALL conservar su ID de 64 bits,
  plazo y épocas host/PINE, y fijar generaciones VU/GS operativas no nulas.
  IF un worker está offline, abriendo o cerrado THEN SHALL rechazar, sin inferir
  que está ausente por la configuración MTVU.
- **WCJ02:** WHEN se solicita control THEN SHALL usar tickets válidos separados
  del ID global, crecientes durante la vida del coordinador y sin wrap. IF se
  agota el presupuesto o existe conflicto de propiedad THEN SHALL rechazar.
- **WCJ03:** WHILE VU no está held THEN SHALL permitir progreso GS y SHALL NOT
  solicitar su retención. WHEN VU acusa THEN SHALL solicitar GS una sola vez.
- **WCJ04:** WHEN se consulta éxito THEN SHALL revalidar generaciones, estados,
  plazo y el sobre CPU/PINE/épocas. Offline, token desconocido o liberado SHALL
  producir rechazo. Los avisos SHALL NOT sustituir la consulta de estado.
- **WCJ05:** WHEN termina, falla o se cancela un intento THEN SHALL liberar los
  tokens aceptados en orden GS → VU antes de reabrir PINE. SHALL cubrir preparación
  parcial, acuse concurrente y reinicio; una identidad ajena SHALL NOT retirarlo.
- **WCJ06:** WHEN llega otro begin mientras hay un propietario THEN SHALL
  conservar sus tokens. WHEN se retira THEN SHALL permitir un intento posterior
  sin reutilizar tickets, incluso con nuevas generaciones de workers.
- **WCJ07:** WHILE hay efectos pendientes THEN CPU SHALL esperar como máximo
  un intervalo nominal de 1 ms entre consultas, sin despachar Qt ni callbacks.
  WHEN vuelve al despacho arbitrario THEN SHALL retirar primero el intento.
  El plazo global permanece limitado a cinco segundos; no es una garantía de
  planificación del sistema operativo ni de latencia de una UI ajena.
- **WCJ08:** WHEN se pide cierre o producción desde CPU THEN SHALL retirar el
  propietario completo antes de efectos/join. Las APIs de control SHALL NOT
  bloquear UI, reservar la cola de datos ni ejecutar callbacks de aplicación.
- **WCJ09:** WHEN se valida THEN SHALL cubrir secuencia, fallos parciales,
  cancelación/plazo/épocas en cada fase, generación nueva, agotamiento, cola llena
  y VU dependiente de GS, con sanitizadores y controles negativos. SHALL distinguir
  puertos modelados, cuerpos exactos, QtCore y VM completa.
- **WCJ10:** WHILE faltan escritores y frontend completo THEN SHALL mantener
  admisión vacía y captura deshabilitada. SHALL preservar fuentes y evidencias
  previas, incluidos intentos fallidos.

## Diseño y responsabilidades

WorkerDrain implementa EffectDrainPort y depende de dos WorkerPort pequeños.
RetainedDrain conserva CPU/PINE/épocas y libera el puerto antes de abrir PINE;
WorkerDrain conserva los tokens y ordena las dos fases. Los adaptadores privados
traducen las operaciones a VU_Thread y MTGS. No se modifica WorkerControl.

El contador de tickets de 29 bits no se reinicia con la sesión. Su presupuesto
configurable solo puede reducir el máximo del protocolo; cero rechaza todo.
Se consume un ticket por intento que llega a request VU, aunque sea rechazado.
Los IDs globales grandes no se convierten a 32 bits. Diagnósticos independientes
que hayan adelantado el contador del worker pueden causar un rechazo conservador;
no se buscan IDs libres ni se roba el token. El coordinador no se recrea por VM.

Ambas generaciones se fijan antes de solicitar VU: cambiar GS mientras VU drena
invalida el intento. No se permite omitir VU offline sin acreditar por separado
el modo sin worker. Los puertos son exclusivamente CPU y no reentrantes.

Qt conserva su bombeo temporizado durante el cierre inicial de PINE. Después de
begin, una espera de control breve sustituye ese bombeo; el siguiente paso consulta
el estado y el plazo. La UI continúa en su propio hilo. Rutas UI→CPU bloqueantes
o UI→GS directas siguen pendientes y mantienen el perfil rechazado.

## Tareas y aceptación

- **WCJ-T1 / IW-COORD1:** núcleo, contratos y tests de identidad/tickets/vida.
- **WCJ-T2 / IW-COORD2:** adaptadores privados, retiro coherente y compilación ON/OFF.
- **WCJ-T3 / IW-COORD3:** despacho acotado, protocolo conjunto, negativos,
  sanitizadores y custodia. B3-B3c/CQ3-C requieren evidencia adicional de bucles
  conjuntos y frontend; la compilación no los cierra.
