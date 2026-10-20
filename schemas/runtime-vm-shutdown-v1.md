# VS — Apagar VM y conservar la decisión del usuario

Historia: como investigador, necesito apagar la VM desde PCSX2 sin confundir esa
acción con salir de la aplicación, y poder rechazar el diálogo sin perderla.

## Requisitos EARS

- **VS01:** WHEN se solicite Apagar VM con diagnóstico iniciado THEN SHALL
  cancelar y retirar primero el diagnóstico, manteniendo UI y CPU disponibles;
  SHALL unir IO antes de continuar con el diálogo o apagar la VM. No SHALL usar
  la salida automática de aplicación como prueba de apagado de VM.
- **VS02:** WHEN el usuario responda No THEN SHALL conservar la VM y restaurar
  su estado previo pausado/en ejecución mediante el flujo ordinario de PCSX2.
  No SHALL despachar shutdownVM, cerrar la aplicación ni escribir savestates.
- **VS03:** WHEN el usuario responda Sí THEN SHALL respetar las opciones de la
  solicitud, despachar el apagado una vez y volver a la lista de juegos en modo
  normal; SHALL dejar la aplicación abierta y utilizable.
- **VS04:** IF no hay diagnóstico iniciado THEN SHALL conservar el flujo nativo.
  WHEN se repita la solicitud pendiente THEN SHALL conservar una sola solicitud
  y sus opciones originales. WHEN se solicite salir explícitamente mientras se
  retira el diagnóstico THEN SHALL dar prioridad a salir y descartar el apagado
  diferido, sin mostrar un diálogo tardío después de salir.
- **VS05:** WHEN se valide THEN SHALL usar acciones y diálogo Qt reales, observar
  estado inicial/final de VM, ausencia de guardados, retirada y unión, y retorno
  a lista. SHALL conservar fallos y separar sonda, control sin sonda y cola de
  prueba. Las confirmaciones reales no SHALL sustituirse por respuestas de un
  falso diálogo.

## Diseño

El servicio ya tiene una única sesión por proceso. Una política pequeña, exclusiva
de UI y sin dependencia de Qt, conserva la intención terminal: salida automática,
apagado de VM pendiente o salida explícita prioritaria. La solicitud de apagado
detiene únicamente el diagnóstico. No expresa consentimiento para apagar la VM.

El timer existente espera finalización y une IO; consume una sola vez la intención
y libera la propiedad especial de salida. Para apagar VM, vuelve a llamar a
requestShutdown con las opciones originales. Esta segunda llamada sigue el
flujo nativo de confirmación, VMLock, savestate y onVMStopped. Así un No conserva
la VM y no puede disparar después el cierre automático del diagnóstico. La UI
no manipula recursos del transporte o del trabajador. No se modifica el layout
de clases Qt ni su MOC, ni se permite otra sesión diagnóstica en el proceso.

La sonda de validación observa inventario o VM iniciada, activa la acción real
de barra/menú y pulsa el botón Yes/No del QMessageBox real. Registra la vuelta
del diálogo, VM pausada/en ejecución, señal onVMStopped, lista visible y cierre
posterior de prueba. No retiene fases ni cambia plazos. Los perfiles usan modo
normal, sin -batch; memcards y savestate desactivados, con confirmación activada.
Se distingue apagar la VM de cerrar la aplicación al terminar la prueba.

## Presupuesto VS-B y tareas

Build incremental: hasta cinco bundles y sus fuentes/objetos/logs, ≤768 MiB
combinados; inicio de secuencia ≥11 GiB, preflight/suelo por comando ≥10 GiB.
Comandos ≤180 s, build ≤600 s, sesiones ≤100 s, supervisión 0,5 s. Regresiones
nativas en etapas ≤512 MiB con inicio/suelo ≥10 GiB. No se reconstruyen
dependencias; IB02 para build completo sigue en 20 GiB.

- [x] **VS-T1:** fijar base, contrato y reproducción en modo normal; contrastar
  Sí/No con candidato anterior, conservando todos los resultados. VS01–VS05.
- [x] **VS-T2:** política UI sin Qt, API de intención y continuación tras unión;
  pruebas de inactividad, repetición, prioridad de salida, opciones y consumo
  único; integrar CTest y sanitizadores. VS01–VS04.
- [x] **VS-T3 / RT-T3c.1b.vm-shutdown:** ejecutar Sí/No con VM inicialmente
  pausada y en ejecución, barra y menú; repetir los casos, comprobar retorno
  a lista y ausencia de guardados. Contrastar el candidato sin sonda. VS01–VS05.
- [x] **VS-T4:** registrar resultados, hashes, fallos, límites y tareas pendientes;
  no cerrar callbacks tardíos ni gates de captura con esta evidencia. VS05.

Ampliación acotada de VS-B: se preservan dos bundles con la primera sonda, cuyo
timer de acción no podía responder a su propio diálogo modal. Se añaden dos
bundles con timer de respuesta independiente y el candidato limpio; los comandos
anteriores conservaron su límite de 512 MiB. Inicio/suelo y plazos no cambian.
