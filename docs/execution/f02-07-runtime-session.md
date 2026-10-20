# F02.07 / LP-C — Sesión runtime y socket (SRC115)

## Resultado y límites

Completa **RS-T1/RS-T2 / RB-T3b.1–2** de
[RS01–RS07](../../schemas/runtime-session-v1.md). La sesión IO recibe solicitudes
parciales, usa el mismo vínculo de DW y conserva los plazos de adquisición y
revalidación. El dueño del socket macOS ahora recibe, entrega y cierra con la misma
identidad nativa completa y el mismo descriptor.

**RB-T3/DW-T3, launcher con inventario nativo válido, candidato enlazado, VM y
captura siguen pendientes.** Las pruebas exitosas usan inventario y coordinador
de prueba declarados. Se ejecutan hilos CPU, IO y DW, socket/identidad nativos y
el rechazo real de `MacOSDiagnosticWorkFactory` ante un manifiesto ausente.
No se ejecutaron ISO, BIOS, juego ni una compilación 3DS en esta etapa.

## Diseño y cierre

`RuntimeDiagnosticSession` toma prestados handoff, trabajador y canal; no crea
hilos ni posee DW. Comprueba identidad del objeto de vínculo, no solamente épocas
coincidentes. La primera recepción consume el deadline fijado antes de la cola;
las siguientes consumen dos segundos desde la entrega anterior, siempre acotados
por el alcance original de cinco segundos. La espera inactiva también cuenta.

El transporte se abstrae con `DiagnosticChannel`. `MacOSDiagnosticSink` conserva
la API de entrega y agrega lectura/conectividad sin exponer el descriptor. Verifica
PID, nacimiento, UID efectivo/real, versión PID y token antes y después de IO;
usa modo no bloqueante y esperas de hasta 20 ms redondeadas hacia abajo.

El cierre cancela alcance y trabajador, cierra el canal una vez y devuelve
`pending` mientras CPU no confirme retirada. Luego puede unir DW. `failed`
significa que la unión terminó pero falló limpieza del canal o de DW; no equivale
a pendiente. El destructor de sesión solo cancela: el dueño debe conservar sus
dependencias y completar `close_until` antes de destruir el trabajador.

## Validación

La [evidencia estructurada](../compatibility/runtime-session-evidence.json)
registra fuentes congeladas, recibos, logs, JUnit, cobertura y controles negativos.
El conjunto agrega 42 escenarios a CMake y a la matriz host existente:

- 27 casos de sesión: vínculo exacto, recepción parcial, desafío/secuencia,
  presupuesto acumulado, reloj, revocación, fallo IO y limpieza pendiente/fallida.
- Ocho casos nuevos de recepción macOS: progreso, lectura vacía, argumentos,
  identidad completa, EOF, cierre parcial y dueño del hilo.
- Siete casos de composición: respuestas y fragmentación por socket, identidad,
  EOF parcial, desconexión con DW bloqueado y manifiesto nativo ausente.

Una prueba inicial de 51 escenarios pasó. Después se ajustó únicamente la prueba
de manifiesto ausente para leer su telemetría después de unir DW, según el contrato
del proveedor; la versión final conserva una instantánea distinta.

La regresión final se ejecuta en Debug, Release, ASan/UBSan y cobertura x86_64,
con 517 casos por configuración. El caso histórico `diagnostic_worker_real_clock`
se compila y conserva registrado, pero no se repite en esta etapa. ThreadSanitizer
arm64 verifica los 27 casos de sesión. Los cuatro controles negativos suprimen,
por separado, vínculo exacto, ventana de revalidación, comprobación después de
verificar el peer y orden de retirada/unión; cada prueba debe fallar con su aserción.

Resultado final: **2.068 ejecuciones nativas, 27 TSan y 58 verificaciones de
repositorio/supervisión aprobadas**, más los cuatro negativos detectados. La
sesión registra 71/71 líneas y 56/62 ramas cubiertas; el transporte macOS,
66/67 líneas y 88/142 ramas. LLVM informó `63 functions have mismatched data`;
se conserva esa advertencia junto con los perfiles y no se presenta cobertura
completa de ramas. Las dos auditorías finales deben producir bytes idénticos.

Las etapas privadas usan piso/inicio de 10 GiB y máximo 512 MiB por etapa,
con supervisión de procesos, espacio y tiempo. No se modifica el proveedor privado
anterior ni la aplicación instalada. ASan desactiva detección de fugas, como la
matriz existente; TSan no constituye validación de PCSX2 o VM. No se ejecutaron
CI remoto ni Linux. Los scripts, salidas y snapshots locales se conservan en
`build/f02-07-runtime-session`; los binarios permanecen en etapas privadas.

## Siguiente tarea

**RS-T3 / RB-T3b.3:** integrar launcher e inventario nativo válido con el frontend
asíncrono privado. Fijar expectativas e identidad antes del lanzamiento, conservar
el mismo vínculo durante cada entrega y gestionar fuera de CPU la limpieza
pendiente. Preparar un candidato nuevo, enlazar bajo IB02 (20 GiB libres al
comenzar) y comprobar con VM lifecycle, callbacks tardíos, gates y escritores
JIT/caché/DMA. No convertir hechos desconocidos/violados en permisos de captura.
