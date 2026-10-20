# F02.07 — Fronteras y despertar VU/GS (SRC80)

Fecha: 2026-10-18. Completa **B3-B3a/b / WB-T1–T3**, definición de puntos reales y
prueba aislada del puente, según [WB01–WB10](../../schemas/worker-boundary-v1.md).
Se mantiene pendiente **B3-B2 integración y B3-B3c/CQ3-C**: no se han insertado
los puntos de retención en los bucles del proveedor ni habilitado captura.

## Decisión y puntos de integración

Se revisa la copia SRC78 del commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, conservando sus 2.957 archivos.
La evidencia fija **30 referencias en once archivos**, incluidas sincronización,
vida de los hilos, presentación, métricas y callbacks de ventana. Las referencias
son ubicaciones revisadas; no equivalen a treinta fronteras instrumentadas ni a
un grafo transitivo de llamadas. Las líneas siguientes pertenecen a esa copia.

| Lugar | Efectos y frontera propuesta | Condición de espera/vida |
|---|---|---|
| MTVU.cpp:137, ExecuteRingBuffer | Drenar comandos completos; Execute termina FinishGSPacketMTVU, semaXGkick.Post (:164), publicación de ciclos y CommitReadPos (:212; cuerpo :295) | Consultar al retornar de WaitForWork y después del lote. Acusar únicamente al terminar los efectos anteriores; GS permanece activo |
| MTVU.cpp:92/107/120, Open/Close/Reset | Reset y publicación de shutdown pertenecen a CPU; las guardias previas ya retiran el intento | Publicar nueva generación desde entrada del worker. Close debe liberar antes de flag/Notify/Join; offline antes de Kill (:216), nunca salir con held |
| MTGS.cpp:150, ThreadEntryPoint | GSopen puede fallar o requerir UI. El hilo nativo persiste entre sesiones y resetea WorkSema después de GSclose | Generación operativa después de GSopen exitoso y antes de MainLoop; closed/opening/failed no son retención ni ausencia certificada |
| MTGS.cpp:329, MainLoop | Terminar todos los comandos, AsyncCall completo, consumo MTVU, actualización readpos y señales OnRingReset/Vsync al acabar el lote | Liberar unique_lock RingBufferBusy2 (:338) antes de acusar; esperar control sin ese mutex. Readquirir solo después de release |
| MTGS.cpp:344, rama idle | CheckForWork vacío puede ir seguido de GSPresentCurrentFrame y GSThrottlePresentation | Servicio de control antes de la siguiente rama idle y al volver de WaitForWork. Un idle ya iniciado termina antes del acuse; held prohíbe iniciar otro |
| MTGS.cpp:482, dependencia MTVU | GS espera semaXGkick y suelta/reobtiene el mutex; consume paquete, reduce readAmount y retira su descriptor | VU acaba sus paquetes antes de acusar. Solo después se pide GS; retener GS mientras VU espera espacio puede bloquear ambos |
| MTGS.cpp:619, epílogo | El cierre iguala posiciones y mata WorkSema; después ThreadEntryPoint ejecuta GSclose y avisa al caller | Resolver stop y publicar offline antes del epílogo. Igualdad por descarte de cierre nunca se toma como drenaje exitoso |
| MTGS.cpp:118/132/894/919 | Start/Shutdown/WaitForOpen/WaitForClose cambian flags y pueden esperar a GS/UI | Cancelación CPU antes del primer efecto, release GS→VU y ninguna espera de cierre manteniendo held |

El puente propuesto publica **request y luego NotifyOfWork directamente** sobre
el WorkSema del worker. No inserta un comando ni reserva espacio. No utiliza
VU::KickStart (:437), cuya guardia BeforeObserverProducer cancelaría la fase de
efectos; tampoco MTGS::SetEvent (:681), que además modifica CopyDataTally.
Se envía un aviso por solicitud aceptada, no uno por cada consulta. Un aviso sin
datos puede causar otra vuelta vacía y no debe convertirse en comando ficticio.

WorkSema preserva el aviso tanto si el worker va a dormir como si ya publicó
SLEEPING. El bucle integrado debe consultar control después de cada retorno de
WaitForWork y antes de dormir nuevamente. El segundo canal ControlWakeup se usa
durante held; no se añade otro waiter de WaitForEmpty ni se cambia ese algoritmo.
La secuencia se prueba aquí; aún no está conectada a los bucles del proveedor.

## UI, métricas y límites del acuse

El acuse GS debe quedar fuera del comando VSync y de la presentación. VSync llama
a PerformanceMetrics::Update; PerformanceMetrics.cpp:236 llega a
Host::OnPerformanceMetricsUpdated (QtHost.cpp:1283), que llama directamente a
updatePerformanceMetrics. Este camino modifica campos y encola texto de UI desde
GS. La guardia TLS de CPU de SRC78 es inerte allí: hace falta retener el worker
en la frontera externa después de completar estos efectos.

GSRenderer::PresentCurrentFrame (:958) realiza presentación mediante
BeginPresentFrame/EndPresentFrame. Su cuerpo no contiene la llamada a
PerformanceMetrics::Update revisada en VSync; ambas rutas deben quedar cubiertas
por la frontera GS, sin atribuirles exactamente los mismos efectos.

GSDevice.cpp:394 solicita una ventana; QtHost.cpp:1082/1087 reenvía adquisición y
liberación a EmuThread. MainWindow.cpp:627/628 conecta ambas con
BlockingQueuedConnection. UI debe permanecer disponible durante drenaje y cierre.
No se autoriza esperar sincrónicamente la captura desde UI ni afirmar que ninguna
otra ruta pueda esperar CPU: callbacks arbitrarios, locks de settings/renderer y
otras raíces todavía requieren la validación del frontend completo.

CPU conserva PINE hasta liberar ambas fases y cancela antes de despachar Qt
arbitrario. Un plazo vencido del worker no le permite retirar held por su cuenta.
Release GS→VU publica permisos en ese orden, sin afirmar que GS ya ejecutó otra
instrucción. La vida de los objetos abarca ambos actores y todas las notificaciones.
La generación sobrevive a Reset de WorkSema; agotamiento y sesión no operativa
rechazan. Terminación abrupta que evita epílogos no se presenta como offline seguro.

## Pruebas ejecutadas

El [probe propio](../../tests/fixtures/pcsx2-worker-boundary/README.md) compila con
ocho fragmentos exactos privados: WorkSema y cinco métodos, KernelSemaphore y
sus cuerpos Darwin/MACH_CHECK. WorkerControl y ControlWakeup de SRC79 son reales.

| Modalidad | Semáforo controlado | KernelSemaphore Darwin / Mach real |
|---|---:|---:|
| Normal | 10/10 | 9/9 |
| ASan/UBSan | 10/10 | 9/9 |
| ThreadSanitizer | 10/10 | 9/9 |

**57 ejecuciones correctas**, sin informes de los sanitizadores. Nueve casos
comunes cubren aviso antes de espera, cancelación antes del acuse, stop retenido,
frontera idle, liberación del mutex, cola llena/dependencia VU→GS, reinicio,
cierre pendiente y timeout pendiente. El caso adicional del doble fuerza el
aviso después de publicar SLEEPING; Mach usa los cuerpos originales sin ese hook.

La cola llena es un modelo de una posición: GS libera espacio, VU termina y acusa,
GS consume su resultado y entonces acusa. La prueba confirma el protocolo de
ese modelo con WorkSema real; no ejecuta el ringbuffer, semaXGkick, renderer ni
workers reales de PCSX2. Las pruebas de idle/mutex también usan efectos propios.
El caso de cierre no prueba crash, cancelación de hilo nativo ni GSopen fallido.

Tres controles negativos sobre copias del probe detectan conservar el mutex
durante held, producir idle antes de release y omitir el aviso WorkSema. Dos
fallan por la aserción prevista; el último no progresa y el supervisor lo detiene
a los tres segundos, verificando cierre del grupo. Se preservan fuente, binario,
log y recibo de cada mutación. No hubo fallos en las seis variantes de referencia.

## Custodia, pipeline y reproducción

La etapa nueva contiene includes y binarios compuestos privados; no modifica
ninguna copia del proveedor ni la aplicación instalada. SRC79 se audita de nuevo
con SHA-256 histórico
`76738bc2c60d63c3aa71fffcc60bee44f5b37a0dd31b512ea985699489235cde`.
Se verifican las catorce copias y los hashes de los fragmentos, referencias,
core propio, harness y recibos. Dos auditorías SRC80 idénticas sustentan la
[evidencia pública](../compatibility/worker-boundary-evidence.json).

Receta local; prepare requiere una etapa inexistente y no sobrescribe fuentes:

```text
rtk proxy .venv/bin/python build/f02-07-worker-boundary/prepare.py
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py normal-double
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py normal-native
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py sanitize-double
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py sanitize-native
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py tsan-double
rtk proxy .venv/bin/python build/f02-07-worker-boundary/run_probe.py tsan-native
rtk proxy .venv/bin/python build/f02-07-worker-boundary/negative_controls.py
rtk proxy .venv/bin/python build/f02-07-worker-control/audit.py f02-07-worker-control-v1-src80-custody.json
rtk proxy .venv/bin/python build/f02-07-worker-boundary/audit.py f02-07-worker-boundary-v1.json
rtk proxy .venv/bin/python build/f02-07-worker-boundary/audit.py f02-07-worker-boundary-v1-repeat.json
```

Apple Clang, x86_64 y C++20; piso libre 10 GiB, etapa máxima 256 MiB, compilación
120 s, caso 15 s y negativo bloqueante 3 s. Recibos y scripts locales excluidos
de Git. CMake, core y CI pública no cambian; los 138 CTest de SRC79 no se repiten
en este lote ni se presentan como evidencia nueva. Ruff, repositorio y whitespace
se comprueban. No se ejecutan CI remota, suite Python completa, build 3DS,
aplicación PCSX2 completa ni consola física.

## Siguiente tarea ejecutable

**B3-B2 integración, primera unidad VU:** crear una copia privada nueva; introducir
el adaptador de vida/control dentro de VU, notificación directa y servicio en las
fronteras indicadas. Probar el cuerpo ExecuteRingBuffer con comandos sintéticos,
cancelación, shutdown y reinicio, compilar MTVU ON/OFF y verificar ausencia de
efectos bajo held. Mantener el puerto global rechazado mientras falta GS.

Después integrar la sesión GS, desbloqueo del mutex, fin de lote/idle y epílogos;
probar MainLoop con cuerpos reales/dobles y objetos ON/OFF antes de conectar el
coordinador VU→GS. B3-B3c/CQ3-C, B3-C/B4 y CQ3-D/CQ-4 verifican dependencias,
callbacks CPU/UI, cierre y frontend completo. AD-3, admisión y captura siguen
pendientes; no se extrapolan los modelos de este lote a esas condiciones.
