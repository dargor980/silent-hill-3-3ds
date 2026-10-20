# F02.07 / LP-C — Entrega asíncrona IO–CPU (SRC114)

## Resultado y alcance

Completa **RH-T1–3 / RB-T3a** de [RH01–RH08](../../schemas/runtime-handoff-v1.md).
La nueva conexión privada recibe una solicitud IO, la despacha a CPU sin espera
bloqueante, publica el ticket y permite componer DW con su vinculación. La
cancelación y la confirmación de retirada son estados separados: IO solo une DW
después de que CPU confirme haber liberado las guardias.

**RB-T3 completo / DW-T3 siguen pendientes.** Se prueba el recorrido con inventario
y sink sintéticos, cuerpos privados exactos y una cola Host local. No se conecta
todavía el launcher/socket autenticado e inventario nativo al frontend con VM.
No se enlaza un nuevo PCSX2 ni se ejecutan VM, ISO o BIOS. Captura deshabilitada.

## Implementación y SOLID

`RuntimeDiagnosticHandoff` administra una solicitud de un solo uso. IO fija ID y
deadline antes de encolarla; `RuntimeDiagnosticQueue` recibe ese deadline absoluto
local. El callback comparte la solicitud y no captura referencias a la pila IO.
Solo CPU escribe el puntero al ticket, una vez; su publicación atómica precede
a las lecturas. La cancelación conserva la primera causa y cubre ambos órdenes
de la carrera publicación/cancelación. Un callback duplicado no vuelve a encolar;
uno cancelado o vencido antes de ejecutarse no adquiere guardias.

La vinculación y DW mantienen sus responsabilidades anteriores. El adaptador
`pcsx2::queue_runtime_diagnostic` proporciona IDs monotónicos propios y llama a
`Host::RunOnCPUThread(..., false)`. Rechaza llamadas desde CPU, trata agotamiento
como terminal y captura excepciones de asignación/despacho fuera de CPU. Una cola
sin callback no se presenta como aceptada: al cancelar o vencer el plazo, un
callback posterior se vuelve inerte. El coordinador conserva su rechazo de IDs
ya consumidos o intentos concurrentes; el adaptador no sustituye ese control.

`QueueObserverRuntimeDiagnosticUntil` usa el mismo deadline, sin añadir el tiempo
ya consumido en IO/cola. La API anterior por duración sigue disponible y conserva
sus regresiones. La asignación del ticket sigue en la fábrica con excepciones;
VMManager mantiene sus flags sin excepciones.

`RuntimeDiagnosticTicket::retire` solo acepta al hilo dueño y revoca antes de
confirmar. El dueño runtime lo llama después de retirar `RetainedDrain`, con
GS/VU/PINE ya liberados. Su destructor solo revoca: no fabrica una confirmación
de liberación. Estos son contratos de componentes confiables, no una atestación
frente a código arbitrario que use incorrectamente esas APIs.

`wait_runtime_diagnostic_stopped` cancela solicitud y DW y devuelve `false` sin
esperar a CPU mientras no haya confirmación. Tras recibirla puede esperar/unir
DW hasta el plazo dado. El dueño IO conserva los objetos; un trabajo bloqueado
puede seguir pendiente. Un cierre fallido también devuelve `false`: el estado
DW distingue limpieza fallida y unión ya realizada. No hay destrucción forzada,
callback de retorno ni unión desde CPU. El reloj debe sobrevivir a solicitud,
callbacks, tickets y trabajador; el dueño IO debe cancelar antes de abandonar
la operación, incluso si otra referencia mantiene vivo su callback.

Los puertos separan cola CPU, validez runtime, trabajo, entrega y cierre. Las
pruebas sustituyen únicamente las dependencias declaradas y ejercitan el mismo
adaptador privado propio, manteniendo la separación SOLID del núcleo y proveedor.

## Verificación

- **475 escenarios nativos por variante**, **1.900 ejecuciones** en Debug,
  Release, ASan/UBSan y cobertura x86_64. Conserva los 455 anteriores y añade 20.
  Incluye 100 carreras cancelación/publicación y 100 de publicación/lectura por
  escenario correspondiente, dueño ajeno, plazo consumido en cola, callback
  retenido, trabajo bloqueado y fallo de cierre. El escenario largo anterior de
  reloj real permanece compilado y excluido; no se cuenta como ejecutado.
- **148 ejecuciones de integración:** 36 casos ON y uno OFF en esas tres
  variantes y TSan arm64. Los 26 casos RC anteriores se repiten con confirmación
  de retirada; se añaden diez casos frontend. IO, VU/GS y DW son hilos distintos
  reales. La cola Host comprueba `block=false`; VM/Qt/PINE/colas son dobles.
- El retorno completo y el callback duplicado entregan un frame sintético de
  **294 bytes** mediante escrituras de tres bytes. El trabajo bloqueado mantiene
  cero cierres antes de liberarlo; IO observa liberación de guardias antes de
  desbloquear/unir DW. El deadline del snapshot coincide con el fijado por IO.
  Esto no prueba el canal nativo autenticado ni inventario real dentro de VM.
- **114 ejecuciones adicionales TSan arm64**, sin avisos de carreras: las 94
  anteriores y 20 de handoff. Las 37 de integración TSan están dentro de las
  148 anteriores, sin doble contabilización.
- **Seis controles negativos detectados:** adquirir tras cancelación previa,
  reiniciar deadline, omitir cancelación tardía, confundir revocación con retirada,
  aceptar confirmación de otro hilo y unir antes de liberar. Se exige la aserción
  esperada y salida 1; un timeout no cuenta como detección.
- **Diez compilaciones completas ON/OFF** de VMManager, PINE, MTVU, MTGS y QtHost,
  con MOC correspondiente, más tres unidades propias: handoff, ticket y frontend.
  Se verifica el adaptador contra la declaración real de Host y los flags del
  proveedor. Esto no acredita enlace ni ejecución del frontend Qt.
- Cobertura del núcleo handoff: **53/53 líneas, 63/66 ramas**. Ticket:
  **36/36 líneas, 25/26 ramas**. LLVM conserva el aviso agregado de 41 funciones
  con datos incompatibles. No se atribuye cobertura completa al proveedor.
  ASan usa `detect_leaks=0`; no acredita ausencia de fugas.
- **58 controles de repositorio/supervisión**, auditoría final repetida con
  bytes idénticos y publicación de metadata. CMake incorpora los escenarios al
  pipeline nativo existente; no se acredita CI remoto, Linux o build 3DS.

## Custodia y siguiente tarea

Se congelan los 175 inputs públicos de SRC113 antes de cambiar ticket, dueño,
coordinador, CMake y apéndice de estado. La copia anterior conserva sus 2.983
archivos; la nueva tiene 2.988, con cinco modificados y cinco añadidos. Las 19
entradas propias copiadas se contrastan con el repositorio. Los 33 fragmentos
privados conservan hash, tipo, rango de caracteres Unicode y LF añadido por la
extracción; 17 son prefijos de entrada y no ejecutan el resto de sus funciones.

Fuentes de terceros, parche y binarios quedan privados. Se conservan fuentes,
objetos, dependencias, perfiles, logs y muestras de supervisión. Las etapas usan
reserva/suelo de 10 GiB y máximo 512 MiB. El enlace completo mantiene la reserva
IB02 de 20 GiB; las compilaciones de unidades pequeñas no lo sustituyen.

**RB-T3b / DW-T3c:** conectar la sesión de socket y el inventario nativo ya
verificados con este adaptador; conservar el mismo handoff para iniciar,
revalidar, cancelar y cerrar. Fijar identidad/manifiestos antes de lanzar el
candidato, comprobar IB02 y enlazar en una etapa nueva. Después, con VM, probar
pausa, cierre, callbacks tardíos, plazos y gates ausentes; revisar cobertura de
escritores JIT/caché/DMA y lifecycle. No convertir los hechos aún desconocidos
o violados en permisos. Solo esa validación puede cerrar RB-T3/DW-T3; la admisión
de captura se evalúa aparte.
