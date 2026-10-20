# HC — Callbacks tardíos y duplicados en Host real

Historia: como investigador, necesito que una entrega tardía o repetida por Host
no vuelva a adquirir una sesión revocada ni use recursos ya retirados.

## Requisitos EARS

- **HC01:** WHEN un callback llegue después de cancelar o vencer el plazo del
  handoff THEN SHALL rechazar ejecución antes de llamar a la cola VM, sin crear
  ticket, adquirir ámbitos ni publicar una vinculación. SHALL conservar la causa.
- **HC02:** WHEN Host entregue dos veces la misma solicitud THEN SHALL llamar
  a la cola VM como máximo una vez. IF ya fue retirada THEN SHALL rechazar la
  repetición, sin adquirir ni publicar de nuevo.
- **HC03:** WHILE un callback siga encolado THEN SHALL conservar su handoff por
  propiedad compartida. WHEN IO retire sus recursos THEN SHALL haber retirado
  CPU y unido DW si llegaron a adquirirse; la copia tardía SHALL poder ejecutarse
  sin acceder a recursos destruidos. Tras consumir las copias SHALL liberarse.
- **HC04:** WHEN se valide THEN SHALL usar Host::RunOnCPUThread real, verificar
  identidad CPU, orden de eventos, llamadas a VM y resultado del consumidor.
  SHALL declarar demora/duplicación inyectadas y separar la cola real de dobles.
- **HC05:** WHEN se añada una sonda THEN SHALL conservar el plazo de cinco
  segundos, verificador, protocolo y flujo de cierre. No SHALL bloquear CPU,
  retrasar artificialmente la salida de UI ni habilitar admisión/captura.

## Diseño y límites

La implementación existente usa `started_.exchange(true)` para consumir una
solicitud una sola vez y revisa su causa/plazo antes de `queue_until`. El callback
captura un `shared_ptr`. Primero se contrasta ese código sin modificar producción.

Una sonda propia en una copia privada del frontend retiene el callback antes del
despacho para dos perfiles: cancelación desde la acción Salir y vencimiento del
plazo original. IO destruye sus recursos y después libera esa copia hacia Host.
Otros perfiles despachan dos copias normales o una copia normal y una repetición
tras retiro y destrucción IO. Cada copia recorre una invocación Qt encolada real;
la sonda no sustituye Host, VMManager, ticket, handoff ni el consumidor.

Se instrumentan entrada/salida, identidad CPU, `queue_until`, devolución de ticket,
cancelación, quiescencia, unión DW, destrucción IO y cierre CPU. Una referencia
débil observa la liberación terminal. La sonda fuerza el calendario de despacho;
no demuestra duplicados espontáneos del sistema operativo ni orden natural del
scheduler. El retraso ocurre antes de encolar, se declara expresamente y no se
presenta como retención dentro de Qt. El control limpio reutiliza SRC126 exacto.

Cada entrega Host entra por `BeforeObserverProducer`, que avanza revocación;
el despacho encolado no equivale a su ejecución. El flujo real retiene eventos
de aplicación durante el ámbito diagnóstico: el segundo despacho inmediato puede
ejecutarse después de completar las tres respuestas y revocar el ámbito. La
prueba SHALL acreditar ese orden y rechazar la segunda ejecución, sin reclamar
una duplicación dentro del ámbito activo. IF la segunda entrega antecede a la
vinculación THEN SHALL observar rechazo lifecycle, cero respuestas y retirada
sin segundo ticket. Si el peer ya cerró, el consumidor SHALL rechazar identidad
no disponible; esa ejecución no SHALL presentarse como peer autenticado.
Ambos órdenes se registran, sin forzar el scheduler. La repetición después de destrucción
IO también conserva las tres respuestas previas. Los dos
perfiles tardíos mantienen un peer autenticado abierto, sin enviar solicitudes,
hasta EOF: no prolongan el presupuesto del consumidor ni aceptan diagnósticos.

## Tareas y presupuesto HC-B

- [x] **HC-T1:** fijar SRC126 y las fuentes, especificar cuatro perfiles y repetir
  cada uno; revisar propietarios y puntos de liberación. HC01–HC05.
- [x] **HC-T2:** regresiones de copias tardías, repetición tras retiro y ejecución
  concurrente; integrarlas en CTest/pipeline y ejecutar sanitizadores. HC01–HC03.
- [x] **HC-T3 / RT-T3c.1c:** compilar sonda privada, ejecutar ocho perfiles Host,
  acreditar rechazo/adquisición única, retiro y vida útil; control limpio. HC01–HC05.
- [x] **HC-T4:** auditar hashes, resultados, fallos, presupuestos y límites;
  conservar pendientes de margen temporal y gates. HC04–HC05.

Build incremental: hasta dos bundles y sus fuentes/objetos/logs ≤512 MiB
combinados, inicio de secuencia ≥11 GiB, preflight/suelo por comando ≥10 GiB.
Comandos ≤180 s, secuencia build ≤600 s, procesos reales ≤100 s, muestras cada
0,5 s. Etapas nativas ≤512 MiB, inicio/suelo ≥10 GiB. IB02 para build completo
mantiene 20 GiB. No se recompilan dependencias; si hace falta modificar producción,
se revisará el plan y se construirá un candidato limpio independiente.
