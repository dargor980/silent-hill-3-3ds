# F02.07 — Presupuesto total del consumidor de diagnóstico

Fecha: 2026-10-19. Fuente: **SRC109**. Contrato:
[BC01–BC08](../../schemas/budgeted-diagnostic-consumer-v1.md). Evidencia:
[budgeted-consumer-evidence.json](../compatibility/budgeted-consumer-evidence.json).

## Resultado

Completa **BC-T1 / NW-T3a**: el consumidor limita a **5 s la primera muestra y
2 s las posteriores**, desde antes de la primera consulta nativa del peer hasta
aceptar el diagnóstico completo. Envío, recepción, decode, segundo contraste de
identidad y publicación comparten el plazo; alcanzar su frontera exacta rechaza.
**NW-T3, DW-T2, PT-T5c y PS-T4 continúan abiertos.**

Se selecciona explícitamente con
`PlatformDiagnosticSession(..., budget_clock=time.monotonic)`. La configuración
local debe aportar un canal con `exchange_with_budget`; si falta, se rechaza sin
recurrir al intercambio anterior. El modo PS previo conserva sus pruebas y su
alcance de IO. La nueva opción aún no está conectada a la sonda PCSX2.

## Arquitectura y propiedad

`DiagnosticSessionBudget` posee el reloj, plazo y causa terminal; la sesión
compone validación PD e identidad del peer; el canal se ocupa de bytes y
readiness. Los puertos de transporte con y sin presupuesto están separados.
El deadline se comparte por referencia y no se reconstruye dentro del canal.

El socket usa IO no bloqueante. Cada espera dura como máximo el menor entre
20 ms y el tiempo restante; se comprueba el control antes/después de cada espera
y operación. Fragmentación, escrituras parciales, EINTR y EAGAIN no reinician el
plazo. Un frame incompleto, EOF, bytes adicionales disponibles o respuesta tardía
hacen terminal la sesión. Los bytes ya enviados no pueden retirarse y no equivalen
a una respuesta aceptada.

Cancelación y publicación se serializan bajo un bloqueo breve, sin IO ni llamadas
al canal en esa sección. Si cancelar gana, no se admite la muestra; si publicar
gana, puede existir una copia histórica. Ninguno de esos resultados es permiso
de captura. `last` deja de exponer la observación tras la señal de cancelación.

Otro hilo solo señala cancelación, cierre o cambio de dueño; no cierra recursos
activos. El dueño los libera cuando retorna la operación. Si está ocioso, debe
volver a `sample()` o `close()` para completar el cierre. `closed` indica que la
llamada de cierre terminó y `close_failed` distingue una limpieza no confirmada.
Un lector nativo bloqueado mantiene el cierre pendiente: no se promete terminar
forzosamente esa operación ni cumplir una latencia de planificación del SO.

Un fork puede heredar el mutex ocupado por un hilo que ya no existe. El hijo
rechaza por PID sin adquirir ese mutex y cierra únicamente su copia del canal;
las pruebas confirman que el padre conserva su conexión funcional.

## Verificación

- **384 pruebas Python** finales: 312 escenarios existentes y 72 nuevos. Incluyen
  tiempo acumulado y frontera exacta, primera muestra y revalidación, vencimiento
  en cada fase, reloj inválido/regresivo, publicación/cancelación concurrentes,
  cierre pendiente, fork real con mutex ocupado y sockets reales fragmentados.
- **100 carreras cancelación/publicación** dentro de la batería, además de casos
  deterministas donde cada operación gana. No se presenta como prueba formal de
  todas las intercalaciones posibles.
- **Cuatro regresiones deliberadas detectadas** en copias aisladas: omitir el
  deadline, omitir la comprobación al publicar, cerrar desde el hilo que cancela
  y aceptar bytes tras vencer el último poll. Los tests fallan por la conducta
  esperada, sin errores de importación ni de colección.
- **Ocho escenarios con procesos nativos macOS arm64**: positivo y fragmentado
  aceptan tres muestras cada uno; truncamiento, cancelación, peer equivocado y
  desconexión aceptan cero; deadline de revalidación y cambio de nonce conservan
  solo la primera. El timeout real de revalidación se observa tras unos 2 s.
  Todos los procesos hijos terminan y el dueño completa el cierre.
- El oráculo previo del bridge conserva **12 controles negativos**. Cobertura
  combinada de los tres módulos: **396/396 líneas ejecutables y 118/118 ramas**.
  Se excluyen solo declaraciones de puertos según la configuración de coverage;
  esta cifra no implica cobertura del emulador ni del productor C++.

Los procesos del oráculo usan identidad de kernel real y **payload PD sintético**
del fixture propio; no son muestras del inventario PCSX2. Las pruebas iniciales
(105, 167 y 382 casos) y los primeros oráculos se conservan. Tras añadir la
protección de fork se ejecutan de nuevo la batería final y los oráculos con las
fuentes finales; las dos generaciones quedan identificadas por hash.

El job Python existente descubre las nuevas pruebas. Se añade el oráculo del
consumidor al job nativo de macOS sin sanitizadores, después de compilar el bridge.
Lint y formato se verifican localmente. No se afirma ejecución remota de CI ni
Linux, ni nueva compilación C++/3DS o ejecución de PCSX2.

## Custodia y siguiente tarea

Los 121 inputs de SRC108 se verifican y copian antes de editar. La evidencia
conserva hashes de fuentes, fixtures, workflow, resultados, perfiles y controles.
Se reutiliza el bridge arm64 ya verificado por SRC106; no se descarga ni compila
una dependencia nueva. Los oráculos y mutantes usan supervisión de procesos con
reserva de 10 GiB, máximo 512 MiB y cierre de grupo verificado. La publicación
se verifica con dos auditorías idénticas. Los **58 controles del repositorio y
de supervisión** pasan después de publicar la evidencia preliminar.

Sigue **NW-T3b**: conservar activo el deadline del productor después de recoger
el resultado, hasta terminar el envío; recibir el plazo fijado antes de la
solicitud y no reiniciarlo al crear el trabajador. Separar resultado preparado,
bytes enviados y entrega completada; perder peer o cancelar debe impedir nuevas
operaciones y mantener recursos hasta confirmar cierre. Después, **NW-T3c**
integrará ambos extremos en copia privada PCSX2 sin VM, con bloqueos por fase,
envíos parciales, backpressure y desconexión. DW-T3 incorporará las guardias
runtime por separado. **La captura continúa deshabilitada.**
