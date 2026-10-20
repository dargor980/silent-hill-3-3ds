# Composición nativa con sesión runtime — NR v1

Historia: como responsable de integración, necesito verificar que el inventario
nativo y el consumidor conservan el vínculo runtime durante el intercambio real,
antes de enlazar la nueva instrumentación con una VM.

## Requisitos EARS

- **NR01:** CUANDO el launcher inicie al candidato privado, DEBERÁ fijar antes
  sus expectativas de política, plataforma y manifiesto, y autenticar el proceso
  hijo mediante PID/nacimiento/UID obtenidos del kernel. El productor DEBERÁ
  verificar al padre y conservar su identidad completa para todo IO.
- **NR02:** CUANDO solicite CPU, DEBERÁ usar el frontend asíncrono existente y
  fijar el deadline antes de conectar/encolar. El inventario nativo DEBERÁ usar
  el mismo vínculo que la sesión; ningún plazo se reiniciará al adquirir CPU.
- **NR03:** CUANDO acepte muestras, DEBERÁ validar correlación, identidad nativa,
  nonce, evidencia, hechos y épocas a través de recepción, DW y entrega. El
  consumidor SHALL NOT interpretar ese diagnóstico como permiso de captura.
- **NR04:** CUANDO ocurra revocación, vencimiento o desconexión durante IO o
  trabajo nativo, DEBERÁ detener la sesión y descartar respuestas tardías o
  parciales. Una revalidación DEBERÁ conservar el alcance original.
- **NR05:** CUANDO cierre con CPU retenida o DW bloqueado, DEBERÁ conservar
  recursos y comprobar pendiente antes de la retirada CPU y antes de liberar
  el trabajo bloqueado. Solo después podrá confirmar unión y limpieza.
- **NR06:** CUANDO un callback cancelado/vencido finalmente se ejecute, DEBERÁ
  realizar cero adquisiciones. Un rechazo de cola DEBERÁ impedir crear trabajo
  nativo, y mantener cerrado el transporte al terminar.
- **NR07:** CUANDO cambie el loader durante preparación o muestreo, DEBERÁ conservar el
  intento fallido y descartar esa sesión; podrá repetir en un proceso nuevo
  sin relajar el manifiesto ni la política.
- **NR08:** CUANDO publique resultados, DEBERÁ identificar por separado app
  privada sin VM, inventario/socket nativos, frontend propio y dobles Host/CPU.
  Este ensayo SHALL NOT cerrar la validación de VM ni RB-T3/DW-T3.

## Diseño y tareas

La fixture inyectada se ejecuta al terminar `-testconfig` en una copia privada
verificada de PCSX2. Usa el frontend propio mediante inclusión exacta; los nombres
Host/VMManager se redirigen explícitamente a dobles locales para evitar colisiones
con símbolos del emulador. Un hilo CPU consume el callback sin bloqueo de IO.
Solo ese hilo crea/publica/retira el ticket; la generación permite revocación.
DW usa `MacOSDiagnosticWorkFactory` real, la sesión RS y el transporte macOS.

Los controles de error son locales a la fixture. El launcher usa el consumidor
BC existente y un socket Unix privado. Registra por separado confirmaciones del
productor y muestras aceptadas por el consumidor, con sus propios relojes.
El éxito exige tres muestras sin inventario sintético. Los hechos runtime son
datos declarados por el doble CPU, no observaciones de una VM.

- [x] **NR-T1 / RS-T3a:** componer launcher, frontend propio, sesión y fábrica
  nativa; congelar manifiesto/inputs antes de lanzar y verificar tres muestras.
- [x] **NR-T2 / RS-T3a:** cubrir fragmentación, backpressure, vínculo revocado,
  plazos, peers incorrectos, callback tardío, fallo de manifiesto y limpieza
  pendiente; conservar intentos y demostrar custodia antes/después.
- [ ] **RS-T3b:** integrar el dueño IO con Host/VMManager reales; preparar,
  enlazar bajo IB02 y verificar lifecycle/gates/escritores en VM. Conservar
  pendientes captura y hechos desconocidos hasta su evidencia correspondiente.

Evidencia: [SRC116](../docs/execution/f02-07-native-runtime-composition.md).
El control de plazo de la segunda muestra se alcanza con traza del loader;
sus tres intentos anteriores rechazan por cambio de imágenes. No se afirma
repetibilidad sin traza de ese control ni estabilidad del loader en general.
