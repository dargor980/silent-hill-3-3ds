# F02.07 — Inventario nativo bajo presupuesto del trabajador

Fecha: 2026-10-19. Fuente: **SRC108**. Contrato:
[NW01–NW08](../../schemas/native-diagnostic-work-v1.md). Evidencia:
[native-diagnostic-work-evidence.json](../compatibility/native-diagnostic-work-evidence.json).

## Resultado y arquitectura

Completa **NW-T1 / DW-T2a** y **NW-T2 / DW-T2b**. El inventario nativo consulta
el mismo presupuesto de `DiagnosticWorker` durante preparación, apertura,
identificación, lectura por bloques de hasta 64 KiB, hash y catálogo de orígenes.
El plazo comienza antes de crear recursos: 5 s iniciales y 2 s por revalidación.
**DW-T2 / PT-T5c.2 sigue abierto** hasta incluir el transporte del canal.

`InspectionControl` separa la comprobación de tiempo/cancelación de los
adaptadores de archivos, digest y orígenes. Su dependencia opcional conserva el
uso existente sin trabajador. `MacOSDiagnosticWorkFactory` recibe configuración
local inmutable y crea el trabajo; el mensaje remoto no elige rutas ni evidencias.
El trabajo abre el manifiesto, contrasta sus hashes y compone los adaptadores en
su hilo. Guardias y recursos se destruyen en orden inverso de dependencia.

La cancelación es terminal y cooperativa. Se comprueba antes y después de las
operaciones; si una syscall retorna después de vencer, se descarta su resultado.
No se promete terminar por fuerza una syscall bloqueada. `close()` comprueba la
liberación de archivos y mapeos retenidos y propaga errores. La espera del dueño
solo confirma cierre después del retorno y unión del hilo, como exige DW.

El registro de eventos dyld se inicializa antes del trabajador. La sonda corre al
salir de `testconfig`, sin esperar bajo el bloqueo de un constructor del cargador.
Los detalles de diagnóstico son prestados a un solo escritor y se leen tras la
unión. No se cambian el núcleo de DW, el inventario de plataforma ni el canal PS.

## Pruebas y pipeline

La versión final pasa **376 escenarios × cuatro modos = 1504 ejecuciones C++**:
Debug, Release, ASan/UBSan y cobertura, x86_64 bajo Rosetta. Se añaden 13 escenarios
y se ejecutan 363 anteriores. CMake registra 377: el caso con reloj real de SRC107
se conserva y compila, pero se excluye de estas suites para respetar su límite de
60 s; su evidencia previa sigue separada. Una primera versión también pasó 1504
ejecuciones y queda conservada; la segunda añade detalle del rechazo nativo.

Los nuevos casos usan archivos propios reales y prueban control de apertura,
identidad, lectura y hash, cancelación terminal, preparación, manifiesto ausente,
evidencias incorrectas, vencimiento por fase y errores de cierre. **Cuatro
regresiones deliberadas se detectan**: omitir control de lectura, de hash, de
orígenes o ignorar el error de cierre. El pipeline nativo incorpora los tests por
CMake. No se ejecutó CI remoto, Linux ni una nueva batería ThreadSanitizer.

Cobertura final del trabajo nativo: **68/84 líneas (80,95 %) y 46/90 ramas
(51,11 %)**; no es cobertura completa. Los adaptadores de archivos, manifiesto,
páginas y orígenes alcanzan respectivamente 99,34 %, 100 %, 98,98 % y 100 % de
líneas. El exportador agregado informa 23 avisos de funciones con datos
incompatibles (SRC107 registraba 15); la exportación aislada de estos tests conserva ocho
avisos y coincide en las cifras del trabajo nativo. Se retienen ambos resultados.
La sonda PCSX2 positiva usa Release y no aumenta estas cifras de cobertura.

## Sonda privada y resultados conservados

Se ejecutan cuatro etapas nuevas de PCSX2 con `testconfig`, sin ISO, BIOS ni VM.
Cada una usa una copia de 200 archivos verificados antes/después y un manifiesto
local de 26 archivos. No se relinka PCSX2 ni se modifica el candidato existente.
Se conservan **14 ejecuciones de PCSX2**, incluidas dos que no alcanzaron el caso
que pretendía probar el arnés:

- La primera etapa obtiene tres muestras positivas y rechaza correctamente un
  plazo de preparación. Su intento de bloquear lectura termina antes por rechazo
  de inventario; no llega a inyectar el bloqueo. Sin detalle de origen en esa
  versión, no se atribuye una causa concreta.
- La segunda registra `PlatformOriginFailure::changed` durante preparación y
  rechaza antes de muestrear. No se identificó qué imagen cambió. Se conserva la
  regla de rechazo y la preparación existente, sin aceptar inventarios cambiantes.
- La tercera añade observación de eventos del cargador y obtiene tres muestras
  estables; no registra imágenes añadidas en esa ejecución.
- La cuarta ejecuta la matriz final de **nueve casos**, todos en su primer proceso.
  El arnés admite repetir únicamente un rechazo de preparación por cambio del
  cargador, siempre en un proceso nuevo y conservando el intento; no fue necesario
  repetir. Esto no demuestra que los cambios espontáneos hayan desaparecido.

| Caso final | Muestras aceptadas | Resultado |
| --- | ---: | --- |
| Positivo | 3 | Identidad estable; cancelación normal al cerrar |
| Plazo en preparación, lectura y hash | 0 por caso | Deadline; salida tardía descartada |
| Plazo en hash de revalidación | 1 | Primera muestra válida; segunda descartada |
| Cancelación en preparación, lectura y hash | 0 por caso | Cancelación terminal |
| Hash de manifiesto incorrecto | 0 | Configuración rechazada |

Cada caso verifica hilo de trabajo distinto del controlador, cierre, unión y
ningún resultado tardío. En los siete bloqueos/cancelaciones inducidos, la primera
espera breve mantiene el cierre pendiente hasta que el trabajador puede salir.
El inventario de descriptores **0–1023** coincide antes/después; ese rango no
representa una enumeración exhaustiva de todos los descriptores posibles.

Las tres muestras positivas finales tardan aproximadamente **1655, 1584 y 1566
ms** y contienen 26 imágenes de aplicación y 621 de plataforma. La primera
muestra del caso de revalidación tarda 1666 ms. La observación adicional de dyld
influye en esos tiempos; no son un presupuesto de frame del port. Las diez
respuestas conservadas entre las etapas tienen los 18 hechos AP desconocidos y
las cuatro épocas en cero. Ninguna otorga capacidad de captura.

## Custodia y siguiente tarea

Se verifican los 115 inputs de SRC107 antes de editar y se conservan sus copias.
Las siete etapas privadas, fuentes, binarios, manifiestos, perfiles, logs y recibos
se comprueban por hash. Hay 62 comandos supervisados, con reserva de 10 GiB,
máximo 512 MiB por etapa y cierre del grupo verificado. La publicación final
se verifica mediante dos auditorías con resultado idéntico. Los 58 controles
del repositorio y de supervisión pasan después de publicar la evidencia preliminar.

Sigue **NW-T3 / DW-T2c**: compartir el plazo desde antes de preparar hasta recibir
y publicar por PS; preservar autenticación del peer; manejar envío parcial,
backpressure, desconexión y cancelación sin reiniciar el reloj. Debe distinguir
bytes enviados, que no pueden retirarse, de una muestra todavía no admitida por
el consumidor. Probar interrupciones por fase, rechazo del frame incompleto y
cierre confirmado. Después, **DW-T3** unirá lifecycle y guardias runtime del
coordinador. **PS-T4, PD-T5 y PT-T5c siguen abiertos; captura deshabilitada.**
