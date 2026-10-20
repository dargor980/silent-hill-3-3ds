# Entradas y bombeo Qt v1 — QD01–QD08

Detalle de CQ3-B/B3-A. Complementa [WD](worker-drain-v1.md),
[RD](retained-drain-v1.md) y [EP](producer-entry-v1.md).

- **QD01:** WHEN un slot CPU instrumentado entra después del inicio de la fase
  de efectos THEN SHALL cancelar y retirar el intento antes de su primera
  instrucción original, incluidos cambios de flags, señales, timers e input.
- **QD02:** WHEN CPU va a bombear eventos Qt arbitrarios y comenzó esa fase
  THEN SHALL liberar el intento antes de crear temporizadores o despachar eventos.
  SHALL NOT confiar en que todos los receptores pasen por RunOnCPUThread.
- **QD03:** WHILE PINE drena reservas previas THEN SHALL permitir el despacho
  y preservar el cierre hasta terminar esas reservas. El aviso SHALL ser inerte
  para un hilo ajeno al propietario y no acreditará exclusión de ese hilo.
- **QD04:** WHEN se cancela por una entrada tardía THEN SHALL conservar el
  comportamiento original, argumentos, señales y entrega de trabajo; SHALL NOT
  descartar callbacks ni cambiar silenciosamente una conexión Qt a síncrona.
- **QD05:** IF un callback ya posee locks antes de entrar a una función protegida
  o corre en GS/UI/otro hilo THEN SHALL mantener sin acreditar esa ruta hasta
  probar su protocolo. La cobertura SHALL distinguir cuerpo y llamador.
- **QD06:** WHEN se valida THEN SHALL ejecutar cuerpos exactos con dependencias
  identificadas, entrega QtCore real y casos directos, temporizados y encolados.
  SHALL comparar ON/OFF/anterior OFF y ejecutar sanitizadores y controles negativos.
- **QD07:** WHILE no existe un canal separado acreditado THEN SHALL rechazar el
  drenaje productivo. Cancelar antes del bombeo SHALL NOT presentarse como una
  solución de progreso para workers retenidos.
- **QD08:** WHEN se publica THEN SHALL conservar fuentes anteriores y separar
  inventario, compilación, probes aislados y aplicación completa. No se concederán
  captura, modos admitidos ni cobertura de escritores desconocidos.

## Diseño de B3-A

El puente BeforeObserverProducer sigue siendo la única decisión sobre el intento
CPU; no se crea otro estado ni un detector de eventos en cada widget. Se añade
al inicio de los slots restantes de EmuThread y de sus ayudantes mutadores CPU.
El slot RunOnCPUThread ya estaba protegido. Se añade también antes de los tres
despachos del bucle principal y de Host::PumpMessagesOnCPUThread.

Esto cubre un receptor QObject arbitrario durante esos bombeos antes de ejecutar
su código o filtros. Instrumentar solo EmuThread::event no cubriría filtros previos,
otros receptores ni llamadas directas. Se conservan los scopes CpuBoundary existentes.
Las APIs GS/UI directas, los filtros nativos y locks adquiridos por llamadores
fuera de este recorrido no se convierten en productores excluidos.

El timer local de progreso no inicia una retención: si una fase posterior quedó
pendiente, este recorrido la cancela antes de entrar a Qt. Es una política
conservadora explícita, útil para cerrar entradas, sin acreditar progreso del drenaje.

## Decisión para B3-B: control separado de los datos

Se selecciona un buzón de control por trabajador y un mecanismo de despertar que
no reserve ringbuffer ni publique AsyncCall. CPU será el único solicitante;
VU/GS publicarán sus propios acuses asociados a ID y generación. Pedir/consultar/
liberar no ejecutará callbacks de aplicación ni esperará CPU/UI. La liberación
habilitará GS antes de VU y tolerará preparación parcial y acuses tardíos.

El próximo diseño ejecutable debe fijar estados, orden de memoria, cambio de
generación, cancelación concurrente con el acuse, pérdida de avisos y cierre.
Debe integrarse en puntos donde el trabajador terminó sus efectos y pueda
permanecer sin producir, cubriendo presentación ociosa. La espera CPU de ese
canal no bombeará Qt arbitrariamente mientras haya retenciones; si necesita
despachar trabajo de aplicación, primero cancelará por el recorrido protegido.

No se implementa aquí ese buzón ni se sustituye WorkSema. CQ3-C conectará los
puntos de acuse de workers y B3-C probará cola llena y dependencias inversas.

## Tareas

- **QD-T1 / QD01–05,08:** inventario de slots, bombeos y rutas directas; nueva
  copia privada, hooks reversibles y objetos QtHost ON/OFF con moc regenerado.
- **QD-T2 / QD03–06:** fixture propio con QtCore real y cuerpos privados, flags
  previos a MTGS, foco/input, timers, shutdown, callbacks con payload y receptor
  distinto de EmuThread; ON/OFF/anterior OFF, ASan/UBSan y controles negativos.
- **QD-T3 / QD07–08:** custodias e informes repetidos; detallar B3-B/B3-C pendientes
  sin promover los estados pending/held del puerto de prueba al proveedor real.
