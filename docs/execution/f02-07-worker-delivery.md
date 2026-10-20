# F02.07 — Entrega del productor bajo presupuesto

Fecha: 2026-10-19. Fuente: **SRC110**. Contrato:
[WD01–WD08](../../schemas/diagnostic-delivery-v1.md). Evidencia:
[worker-delivery-evidence.json](../compatibility/worker-delivery-evidence.json).

## Resultado

Completa **WD-T1 / NW-T3b**. El productor conserva su plazo hasta confirmar el
envío completo. Retirar la respuesta del mailbox ya no desactiva el presupuesto
en el nuevo modo. **NW-T3c**, la composición privada con consumidor e inventario
PCSX2, sigue pendiente; **NW-T3 y DW-T2 permanecen abiertos**.

`submit_until` acepta el deadline absoluto que el dueño fijó antes de recibir
la solicitud y lo limita a 5 s iniciales/2 s posteriores. Si ya venció, rechaza
antes de crear el hilo. `take_for_delivery` conserva la operación pendiente;
`complete_delivery` comprueba el plazo y serializa confirmación/cancelación.
El trabajador también expira una entrega sin consultas del dueño. No vuelve a
muestrear ni acepta otra solicitud mientras espera esa confirmación.

El modo anterior `submit`/`take` se conserva. Mezclar modos, recoger dos veces,
confirmar sin entrega o confirmar de nuevo hace terminal la sesión. No se usa el
tiempo absoluto de otro proceso ni se afirma sincronizar relojes por el protocolo.

## Diseño y límites

`DiagnosticWorker` posee operación, deadline y cancelación. El puerto mínimo
`DiagnosticDeliverySink` abstrae escritura parcial y espera; `deliver_diagnostic`
conserva una copia fija de 294 bytes, limita cada espera a 20 ms y al presupuesto
restante, y comprueba el control antes/después de cada llamada. Una respuesta
preparada, bytes enviados y entrega confirmada son estados distintos.

`MacOSDiagnosticSink` posee el socket y la identidad esperada. Usa IO no
bloqueante, protege de SIGPIPE y contrasta PID, nacimiento, UID real/efectivo,
versión de PID y token nativo antes/después de las operaciones. El dueño del
canal transmite y cierra; otro hilo solo puede señalar el control DW. Un uso del
sink desde otro hilo o un fork rechaza; el hijo puede cerrar su propia copia.
No se cierra un descriptor desde otro hilo ni se reintenta un `close` fallido.

La unión del trabajador confirma limpieza de su inventario, no cierre del
socket. Ambos resultados se verifican por separado. Una cancelación durante un
syscall solo se observa cuando vuelve el control; no se promete terminación
forzosa. Los bytes enviados no pueden retirarse y confirmar entrega no implica
que el consumidor BC los autenticó o admitió. La integración debe imponer los
plazos locales de ambos extremos.

## Verificación

- **402 escenarios** en Debug, Release, ASan/UBSan y cobertura: **1608 ejecuciones**,
  incluidas 376 anteriores y 26 nuevas. Hay 403 registrados; el escenario anterior
  de reloj real completo se compila y conserva sin repetirlo en esta ejecución.
  El nuevo vencimiento autónomo usa un plazo real de 500 ms y sí se ejecuta.
- **41 ejecuciones con ThreadSanitizer arm64**: 24 casos del trabajador y 17 de
  entrega, sin diagnósticos del sanitizador. Incluyen 100 ciclos de revalidación
  inmediata y 100 carreras cancelación/confirmación por ejecución del caso.
- **Cinco regresiones deliberadas detectadas**: ignorar el plazo externo,
  desactivar `pending` al recoger, omitir la comprobación al confirmar, ampliar
  la espera del sink y omitir el token del peer. Cada copia compila y falla en
  la aserción prevista; las fuentes originales permanecen intactas.
- Sockets nativos reales verifican envío, backpressure y reanudación, peer
  incorrecto, desconexión, cierre fallido, dueño incorrecto y fork. Las
  observaciones del trabajador en estos tests son sintéticas; no son inventarios
  de una nueva ejecución PCSX2.

| Componente | Líneas | Ramas |
| --- | ---: | ---: |
| Trabajador DW | 224/226 (99,1%) | 167/176 (94,9%) |
| Bucle de entrega | 22/22 (100%) | 14/18 (77,8%) |
| Sink macOS | 40/41 (97,6%) | 55/80 (68,8%) |

El exportador agregado conserva **26 advertencias de funciones con datos
incompatibles**, frente a 23 en SRC108; no se presenta una exportación sin
advertencias. Los recuentos anteriores pertenecen a los archivos indicados.
El inventario nativo conserva 68/84 líneas y 46/90 ramas. No se atribuye cobertura
del emulador, del port ni de todas las intercalaciones posibles.

Los targets se incorporan al CMake nativo que ya ejecuta el pipeline. Se verifica
macOS x86_64 localmente y TSan arm64; no se afirma CI remoto, Linux, 3DS ni nueva
ejecución de PCSX2. ASan mantiene la configuración anterior sin detector de fugas.

## Custodia y siguiente paso

Se verifican y copian los **126 inputs de SRC109** antes de editar. Las fuentes,
binarios, perfiles y registros quedan vinculados por hash. Cada comando nativo
usa supervisión con reserva de 10 GiB, máximo 512 MiB por etapa y cierre del
grupo verificado. Los **58 controles del repositorio y supervisión** pasan con
la evidencia preliminar publicada; dos auditorías finales idénticas verifican
la publicación.

Sigue **NW-T3c**: ejecutar la composición BC/DW/inventario/sink en una copia
privada PCSX2 sin VM, con deadline/cancelación por fase, fragmentación,
backpressure y desconexión; verificar cierres y ausencia de admisión tardía.
DW-T3 conserva la integración de guardias runtime por separado.
**La captura continúa deshabilitada.**
