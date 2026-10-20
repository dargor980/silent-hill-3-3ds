# Trabajo nativo de diagnóstico — NW v1

Historia: como investigador, necesito que el inventario nativo consulte el
presupuesto DW durante su trabajo y libere sus recursos antes de confirmar cierre.

## Requisitos EARS

- **NW01:** CUANDO se cree el trabajo nativo, DEBERÁ recibir configuración local
  inmutable: ruta/hash del manifiesto, política PD y dirección de la imagen
  principal. SHALL NOT aceptar estos valores desde el mensaje de diagnóstico.
- **NW02:** CUANDO se prepare, DEBERÁ abrir y validar el manifiesto dentro del
  trabajador y de su presupuesto, contrastar sus evidencias con la política local
  y crear allí los adaptadores. La configuración inválida DEBERÁ terminar la sesión.
- **NW03:** MIENTRAS se abran archivos o procesen sus bytes, DEBERÁ comprobar
  cancelación antes/después de cada operación de lectura y digest, y durante el
  recorrido de directorios. Los bloques DEBERÁN seguir limitados a 64 KiB. Un
  rechazo DEBERÁ borrar la salida y permanecer terminal aunque el control vuelva
  a aceptar. La ausencia del puerto opcional DEBERÁ conservar el comportamiento
  anterior de los adaptadores usados fuera de DW.
- **NW04:** CUANDO se prepare el catálogo de imágenes/orígenes, DEBERÁ comprobar
  el presupuesto en sus fronteras y callbacks. CUANDO el SO no permita interrumpir
  una operación ya iniciada, DEBERÁ descartar su salida al retornar si el control
  ha vencido; SHALL NOT atribuir una garantía de cierre forzoso a esa comprobación.
- **NW05:** CUANDO se muestree, DEBERÁ usar el mismo presupuesto recibido por DW,
  conservar identidad/línea base y devolver únicamente el diagnóstico de cabeceras
  de aplicación con plataforma asumida. Sin guardias runtime, hechos AP y épocas
  DEBERÁN permanecer desconocidos/cero.
- **NW06:** CUANDO se cancele o finalice, DEBERÁ destruir guardias y adaptadores
  en orden inverso de dependencia y en el trabajador. La confirmación DW DEBERÁ
  ocurrir después de esa destrucción; SHALL NOT cerrar recursos prestados desde
  el controlador ni mantener descriptores abiertos tras el cierre confirmado.
- **NW07:** CUANDO se pruebe en PCSX2, DEBERÁ usar una copia privada, `testconfig`
  y ninguna VM; registrar el hilo, muestras, plazos, rechazo y cierre. DEBERÁ
  inducir excedencias/cancelación en preparación, lectura y hash, contrastar los
  archivos antes/después y conservar resultados fallidos sin reinterpretarlos.
- **NW08:** CUANDO se informe el resultado, DEBERÁ distinguir presupuesto del
  inventario de presupuesto total del canal. El transporte de PS y la integración
  de guardias runtime seguirán pendientes hasta verificarse explícitamente; una
  sonda sin canal SHALL NOT cerrar DW-T2 ni PT-T5c completos.

## Diseño y tareas

`InspectionControl` es un puerto mínimo de comprobación por fase, sin conocimiento
de PD, hilos ni sockets. Los adaptadores nativos lo aceptan opcionalmente y
conservan sus rechazos terminales. `MacOSDiagnosticWorkFactory` compone ese puerto
con `DiagnosticBudget` y posee solo configuración antes de `create()`; el trabajo
posee todos los recursos del inventario. El control adicional de pruebas es local
y prestado, no seleccionable por protocolo, y debe sobrevivir al trabajador.

El registro de callbacks de dyld es infraestructura de vida de proceso y debe
estar inicializado en el controlador antes de arrancar trabajadores, conforme a
su contrato existente. No se espera un trabajador desde un constructor que
retenga el bloqueo del cargador. La sonda se ejecuta al cerrar `testconfig`,
con el controlador libre de guardias de CPU y sin emulación.

- [x] **NW-T1 / DW-T2a:** puerto de control, adaptación de archivos/digest/
  preparación de orígenes y composición nativa DW. Pruebas con archivos reales
  propios, fallo de control antes/después de operaciones y ausencia de fugas.
- [x] **NW-T2 / DW-T2b:** integrar sonda privada sin canal, tres muestras estables,
  plazo de primera muestra/revalidación y cancelación por fase; cierre confirmado,
  pipeline, sanitizadores, cobertura y custodia. Mantener captura deshabilitada.
- [x] **NW-T3 / DW-T2c:** extender la transacción del canal PS al mismo plazo
  desde antes de la preparación hasta recibir/publicar, sin reiniciar reloj ni
  perder identidad del peer. Probar desconexión, escritura parcial, backpressure,
  cancelación y salida tardía; registrar qué bytes ya enviados no son retractables.
  Solo después podrá marcarse DW-T2 completo. DW-T3 mantiene las guardias runtime.

SRC109 completa **BC-T1 / NW-T3a**, consumidor con presupuesto total, en el
[contrato BC](budgeted-diagnostic-consumer-v1.md). **NW-T3 sigue abierto**: faltan
NW-T3b (productor con deadline activo durante envío) y NW-T3c (sonda conjunta
PCSX2). El consumidor con presupuesto se selecciona explícitamente por política
local; los resultados de procesos sintéticos no sustituyen esa sonda.

SRC110 completa **WD-T1 / NW-T3b**, entrega retenida bajo el plazo del productor
según [WD01–WD08](diagnostic-delivery-v1.md). Falta **NW-T3c**, sonda privada que
componga ambos extremos; NW-T3 y DW-T2 siguen abiertos.

SRC111 completa **NW-T3 / DW-T2c** mediante el [contrato DC](diagnostic-composition-v1.md):
consumidor y productor bajo sus plazos locales, inventario real, 20 escenarios
finales sin VM, cierre verificado y ninguna admisión tardía. DW-T2 queda completo
para diagnóstico privado; DW-T3 y captura continúan pendientes.
