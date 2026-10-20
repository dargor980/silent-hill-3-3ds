# Dependencias de frontend v1 — WF01–WF08

Detalle de IW-FRONT y B3-C/CQ3-D. Continúa WCJ sin habilitar captura.

- **WF01:** WHEN GS necesita una llamada síncrona a UI durante drenaje THEN
  la conducción CPU SHALL permitir que el hilo UI la entregue y GS continúe.
  SHALL NOT bombear callbacks CPU arbitrarios mientras conserva tokens.
- **WF02:** WHEN UI encola una operación CPU durante drenaje THEN SHALL conservar
  su payload y entrega única; el primer efecto SHALL ocurrir después del retiro.
- **WF03:** IF UI espera CPU y GS espera UI simultáneamente THEN la prueba SHALL
  demostrar la cancelación por plazo y la entrega posterior de ambos callbacks.
  SHALL registrar que UI puede permanecer bloqueada hasta ese plazo y SHALL NOT
  confundir recuperación acotada con UI disponible ni admitir ese perfil.
- **WF04:** WHEN se inventarían rutas THEN SHALL fijar hilo, primer efecto,
  conexión, locks relevantes, archivo, líneas y hash actuales. SHALL distinguir
  una llamada ya serializada de una ruta aún pendiente.
- **WF05:** WHEN se prueba frontend THEN SHALL usar QThread/QObject y entrega
  QtCore reales, distinguir dobles de Widgets/ventana y comprobar argumentos,
  orden, payload, cancelación y cierre. Los fallos SHALL quedar supervisados.
- **WF06:** WHEN se prepara enlace completo THEN SHALL verificar fuente y
  dependencias fijadas, usar etapa nueva y respetar reserva IB02. SHALL conservar
  la aplicación instalada y no habilitar captura por compilación o enlace.
- **WF07:** WHEN se evalúa una modificación de sincronización THEN SHALL partir
  de un fallo reproducible y preservar el contrato de retorno del llamador.
  SHALL NOT convertir silenciosamente una conexión bloqueante en asíncrona.
- **WF08:** WHILE faltan entradas, escritores o ejecución de VM completa THEN
  SHALL mantener admisión vacía, declarar límites y conservar evidencias previas.

## Diseño y aceptación

Se reutilizan los bucles conjuntos SRC83 y se añade un QObject CPU en QThread,
un QObject UI en el hilo principal, y los cuerpos exactos RunOnCPUThread,
runOnCPUThread, RunOnUIThread y runOnUIThread. El padre real de la ventana se
representa por el receptor UI; no se atribuye al probe la ejecución de Widgets.

Primero se verifica la ruta GS→UI con UI disponible. Después se introduce trabajo
CPU encolado durante drenaje y, por separado, una dependencia circular de las
conexiones existentes. El resultado de esta última prueba determina la siguiente
decisión: una cancelación por deadline puede recuperar el sistema y aun así no
satisfacer la disponibilidad de UI requerida por WB07.

El enlace completo utiliza la misma fuente fijada si no hay cambios del proveedor.
No requiere otra copia idéntica; sí una etapa de build distinta e inventario nuevo.

- **WF-T1 / IW-FRONT1:** inventario actual y contrato de rutas/locks.
- **WF-T2 / IW-FRONT2:** pruebas entre hilos y diagnóstico de espera circular.
- **WF-T3 / IW-FRONT3:** configurar/compilar frontend, custodiar el resultado y
  mantener separados enlace, arranque y captura real.
