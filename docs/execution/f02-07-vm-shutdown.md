# F02.07 — Apagar VM y cancelar la confirmación

Fecha: 2026-10-19. Contrato [VS01–VS05](../../schemas/runtime-vm-shutdown-v1.md).
Evidencia [SRC126](../compatibility/vm-shutdown-evidence.json).

**VS-T1–VS-T4, RT-T3c.1b.vm-shutdown y RT-T3c.1b completos.** Al solicitar
Apagar VM, el servicio retira el diagnóstico antes de abrir la confirmación.
Responder No conserva la VM y su estado previo; responder Sí vuelve a la lista
de juegos, con PCSX2 abierto. Pasan dieciséis perfiles con acciones Qt reales,
un control externo del candidato sin sonda y el control normal de tres respuestas.

## Causa y cambio

El timer diagnóstico anterior terminaba toda la aplicación al finalizar el
servicio. `requestShutdown` entraba en la confirmación y en operaciones de VM
sin diferirlas hasta retirar el diagnóstico. Aunque No conservara inicialmente
la VM, la salida automática posterior todavía podía cerrar PCSX2. Con Sí, esa
salida tampoco acreditaba una vuelta estable a la lista de juegos.

`RuntimeUIIntent` conserva exclusivamente la intención en el hilo UI: salir,
apagar VM con las opciones originales o esperar. No depende de Qt ni cancela,
une trabajadores o despacha operaciones. El servicio conserva la responsabilidad
de señalar cancelación y acreditar finalización y unión IO. Una petición repetida
conserva las primeras opciones; salir explícitamente tiene prioridad sobre el
apagado pendiente. La intención se consume una sola vez.

El hook de MainWindow difiere `requestShutdown`. El timer de QtHost espera
finalización, une IO, libera la propiedad especial del servicio y se detiene
**antes** de continuar la acción nativa, evitando reentrada desde el diálogo
modal. La continuación conserva confirmación, `VMLock`, opciones de guardado y
`onVMStopped` de PCSX2. No cambia el layout Qt ni MOC.

La primera solicitud cancela únicamente el diagnóstico; no constituye una
confirmación de apagado. Con No, la VM sigue funcionando, pero el diagnóstico
cancelado no se reinicia: permanece el contrato de una sesión por proceso.
Con el servicio inactivo se mantiene el flujo ordinario de PCSX2.

## Contraste real y matriz

Dos perfiles válidos del candidato base conservan los fallos: No mediante barra
acepta tres respuestas (`reason=0`), pero después cierra la aplicación; Sí mediante
menú termina por lifecycle (`reason=8`) y también cierra PCSX2. Ambos pulsan botones
del diálogo real y salen con código cero; ninguno alcanza la prueba de retención
de VM/lista ni el cierre explícito de prueba. Salida limpia no equivale a cumplir
el comportamiento solicitado.

La sonda corregida usa un timer de acción y otro independiente para responder al
`QMessageBox` real. Activa la acción de barra/menú al observar inventario con VM
pausada, o VM activa para el perfil en ejecución. No bloquea fases, sustituye el
diálogo ni amplía los plazos. Tras la decisión comprueba el estado durante un
segundo y solo después solicita salir para terminar la prueba. Ese segundo es
una ventana de observación de retención, no el mecanismo para elegir la fase.

| Estado inicial | Decisión | Barra | Menú | Resultado |
| --- | --- | ---: | ---: | --- |
| Pausado | No | 2 | 2 | VM válida, sigue pausada |
| Pausado | Sí | 2 | 2 | VM apagada, lista visible |
| En ejecución | No | 2 | 2 | VM válida, reanudada |
| En ejecución | Sí | 2 | 2 | VM apagada, lista visible |

Los **16 perfiles** registran `reason=6`, `clean=1`, `replies=0`, `admitted=0`,
ningún diagnóstico aceptado y salida cero. Las trazas ordenan acción/cancelación
→ destrucción IO → unión IO → diálogo → decisión → estado retenido → cierre
explícito de prueba → parada CPU. En los ocho perfiles inicialmente pausados,
retiro CPU y unión DW preceden a destrucción IO. Los ocho en ejecución cancelan
durante espera de pausa, antes de adquirir CPU/DW; no se atribuye una retirada
de recursos que no llegaron a adquirirse.

La respuesta No no despacha shutdown ni emite VM detenida antes del cierre de prueba. Sí
despacha exactamente un apagado sin guardar y acredita VM detenida y lista
visible antes de ese cierre. No se generan archivos de memcards o savestates.
El máximo observado de cancelación a unión IO fue **21,88 ms**, y el manejador
UI retornó en hasta **1,34 ms**. Son mediciones locales, no garantías de latencia.
La ventana de retención tampoco demuestra una duración indefinida.

## Control externo sin sonda

CUA seleccionó el bundle limpio por ruta absoluta durante la ejecución supervisada
del hijo 30006. Desde **Sistema → Apagar**, el diálogo mostró el guardado
desmarcado. Tras No permaneció Silent Hill 3, con velocidad 100 %, VPS 50 y
Pausar/Apagar habilitados. Otra solicitud y Sí devolvieron a `GameListWidget`,
con Lista de juegos seleccionada; Apagar/Pausar deshabilitados e Iniciar archivo
habilitado. PCSX2 seguía abierto. Solo entonces se usó Salir.

El perfil se llama `running-no-toolbar-manual` por sus etiquetas de lanzamiento;
sin sonda esa etiqueta no activa ningún control. La ruta externa efectivamente
usada fue **menú**, registrada así en la metadata. La biblioteca del perfil
aislado estaba vacía. Renderer Null permite comprobar estado de VM e interfaz,
no imagen ni jugabilidad. Solo la VM en ejecución y el menú se contrastan por
CUA; pausa y barra quedan cubiertas por acciones Qt reales instrumentadas.

La última lectura AX agotó su espera tras pulsar Salir. El launcher y el
supervisor verifican por separado código cero, `clean=1` y ausencia de
descendientes restantes. El candidato limpio no contiene trazas VS: el orden
interno procede de los perfiles instrumentados.

El control limpio sin cancelación acepta tres respuestas completas, conserva
30 imágenes por archivo, 1.040 de caché, revisión 1.071 y épocas `[53,3,1,1]`,
espera liberación del consumidor y termina con `reason=0` y código cero.

## Compilación, regresiones y trazabilidad

Se recompilan los tres consumidores de la cabecera de servicio: servicio,
MainWindow y QtHost; el candidato limpio reutiliza otras **467** entradas del
enlace. Los candidatos instrumentados recompilan además el trabajo diagnóstico
macOS: cuatro unidades y 466 reutilizadas. Se verifican las 470 entradas, 19
archivos estáticos con 390 miembros, MOC conservado, firma ad hoc y resolución
de frameworks. MainWindow compila con observer activado y desactivado.
El candidato limpio pasa `testconfig` y no contiene la sonda `SH3_VS`.

Ejecutable limpio SHA-256:
`716628b435ca3ee0e93cefad4646f09e742a4e443d954b137e29fa47b63788f4`.

| Suite | Aprobadas |
| --- | ---: |
| Debug x86_64 | 117 |
| Release x86_64 | 117 |
| ASan/UBSan x86_64 | 117 |
| TSan arm64 | 114 |
| Repositorio y supervisor | 58 |

Total: **465 ejecuciones nativas**. Los escenarios nuevos cubren cancelación
en espera, sesión con retirada CPU retenida y política UI: ocho combinaciones
de opciones, inactividad, duplicación, prioridad de salida y consumo único.
Se registran en CTest y en el pipeline nativo existente. ASan conserva
`detect_leaks=0`; TSan excluye `macos_sink_fork`, `macos_peer_process` y
`macos_peer_exec`. Los dobles nativos no se presentan como callbacks tardíos
reales en Host. El consumidor congelado de SRC122 no cambia; su batería de 304
pruebas no se repite ni se contabiliza aquí.

Se conservan los fallos preparatorios: una cabecera ausente impidió la primera
compilación de QtHost; un caso llamaba a salida de aplicación en vez de apagado
diferido (116 aprobadas y una fallida); y la primera sonda no podía responder al
diálogo desde el mismo timer que lo abrió. Ese perfil no tiene `dialog_click` y
queda excluido del contraste No. Se conservan sus dos bundles; la sonda definitiva
usa un timer de respuesta independiente. Una selección CUA anterior, después de
terminar el proceso, abrió el asistente predeterminado: se cerró con Cancel/Yes
sin editar opciones y no cuenta como validación.

VS-B documenta la ampliación antes de los builds adicionales: hasta cinco bundles
y fuentes/objetos/logs, **768 MiB combinados**, inicio de secuencia ≥11 GiB y
suelo por comando ≥10 GiB. Comandos ≤180 s, builds ≤600 s y sesiones ≤100 s;
muestreo cada 0,5 s. Cada etapa nativa mantiene ≤512 MiB. Los primeros comandos
conservaron su límite de 512 MiB; IB02 para build completo sigue en 20 GiB.
La auditoría conserva todos los recibos, muestras, hashes y etapas privadas de
SRC125. No se recompilan dependencias de terceros ni se redistribuyen ISO/BIOS.

## Siguiente tarea y límites

Sigue **RT-T3c.1c: callbacks tardíos y duplicados en la cola Host real**. Requiere
coordinar revocación antes de invocar el callback, acreditar que no adquiere ni
publica después, conservar sus objetos hasta el retiro y contrastar cierre sin
bloqueo con el candidato limpio. También siguen margen temporal y gates
JIT/caché/DMA/lifecycle. Esta evidencia no habilita captura, admisión, CI remota,
Linux ni ejecución en Nintendo 3DS.
