# F02.07 — Callbacks tardíos y duplicados en Host real

Fecha: 2026-10-19. Contrato [HC01–HC05](../../schemas/runtime-host-callback-v1.md).
Evidencia [SRC127](../compatibility/host-callback-evidence.json).

**HC-T1–HC-T4, RT-T3c.1c y RT-T3c.1 completos.** Ocho perfiles de PCSX2 real
validan rechazo tardío, ejecución única y conservación del handoff hasta consumir
las copias. No fue necesario modificar producción: se contrastaron las guardas
existentes y se añadieron regresiones, sonda privada y evidencia. El control
limpio reutiliza el ejecutable exacto de SRC126 y acepta tres respuestas.

## Propiedad y ejecución

`RuntimeDiagnosticHandoff::execute` consume `started_` atómicamente antes de
consultar causa/plazo y llamar a `queue_until`. El callback captura un
`shared_ptr`; IO conserva solicitud, trabajador y canal hasta quiescencia CPU
y unión DW. La revocación no sustituye esa retirada.

La sonda separa observación de coordinación: el header propio guarda una copia
y una referencia débil; el insertor modifica únicamente las copias privadas de
frontend, servicio y QtHost. No sustituye Host, VMManager, ticket, handoff o
consumidor. Cada invocación atraviesa `Host::RunOnCPUThread(..., false)` y la
conexión Qt encolada real. Las trazas confirman identidad CPU y ausencia de
ejecución de esos callbacks en UI.

Para los casos tardíos se retiene el despacho **antes de encolarlo en Host**;
se libera después de que `run` destruye sus recursos IO. La cancelación procede
de la acción Qt Salir; el otro caso espera el plazo original de cinco segundos.
La sonda no bloquea CPU ni demora la salida de UI. Esto prueba despacho tardío
inyectado por una cola real, no retención dentro de Qt ni demoras espontáneas
del scheduler.

Para duplicados inmediatos se encolan dos copias desde IO. Para duplicados tras
retiro se encola la primera normalmente y la segunda después de destrucción IO.
Una referencia débil, consultada después de detener CPU, debe estar expirada.
Los ámbitos de CPU/DW se retiran antes de destruir los recursos IO adquiridos.

## Resultados reales

| Perfil | Ejecuciones | Llamadas a VM por proceso | Respuestas aceptadas | Resultado |
| --- | ---: | ---: | ---: | --- |
| Tardío tras cancelación UI | 2 | 0 | 0 | Callback rechazado, causa 6 |
| Tardío tras plazo original | 2 | 0 | 0 | Callback rechazado, causa 5 |
| Dos despachos inmediatos | 2 | 1 | 3 / 0 | Segunda ejecución rechazada, dos órdenes reales |
| Repetición tras destrucción IO | 2 | 1 | 3 por proceso | Segunda ejecución rechazada, causa 6 |
| Control limpio sin sonda | 1 | Flujo ordinario sin contador | 3 | Finalización normal |

Los ocho perfiles terminan con código cero, `clean=1`, `admitted=0` y sin
memcards/savestates. En los cuatro tardíos, el callback comienza después de
revocación, quiescencia y destrucción IO: `execute=false`, `binding=null`, cero
llamadas a VM y ningún trabajador creado. El peer permanece autenticado y abierto
sin enviar solicitudes hasta EOF; su espera de observación no extiende el
presupuesto de aceptación de un diagnóstico.

Los dos duplicados tras destrucción IO completan tres respuestas, revocan el
handoff, retiran CPU, unen DW y destruyen IO antes de encolar otra copia.
La segunda ejecución no llama a VM ni devuelve una vinculación. Las copias
tardías todavía poseen el handoff durante la invocación; al terminar, la
referencia débil expira. Todas las trazas acreditan unión IO antes de parada CPU.

Los duplicados inmediatos muestran dos órdenes permitidos por el flujo real:

1. Host deja la segunda copia pendiente mientras el diagnóstico conserva su
   ámbito. Se aceptan tres respuestas; tras revocación, la segunda copia se
   ejecuta y rechaza con causa 6, sin otra adquisición.
2. La segunda copia se entrega antes de publicar la vinculación. La entrada
   `BeforeObserverProducer` avanza la generación, y el handoff rechaza por
   lifecycle (8). No se crea trabajador ni se acepta una respuesta.

En el segundo orden el cierre fue tan rápido que el lector nativo del consumidor
rechazó `peer_unavailable`. **Ese peer no se presenta como autenticado.** No se
relajó el consumidor ni se admitió ningún frame. La evidencia de ejecución Host
procede de stdout del hijo lanzado directamente, con ejecutable fijado por hash,
trazas CPU y cierre supervisado. El verificador exige esa causa, cero respuestas,
cero trabajador, una sola llamada a VM y el orden correspondiente; no acepta
errores arbitrarios del consumidor como éxito.

Los dos resultados originales del checker para duplicados quedaron con
`case_passed=false`: primero esperaba solo lifecycle y luego solo finalización
normal. Se conservan intactos y se añaden reevaluaciones separadas de sus logs.
La validación final distingue ambos órdenes por las trazas y la causa, sin
modificar los resultados ni forzar el scheduler. Ocho pruebas negativas del
checker rechazan adquisición/publicación tardía, hilo incorrecto, orden imposible,
retención de referencias, aceptación sin peer, error ajeno y segunda adquisición.

En total se decodifican de nuevo **12 frames completos**, todos diagnósticos
no admitidos para captura: nueve de perfiles con sonda y tres del control limpio.
Conservan 30 imágenes por archivo, 1.040 de caché, revisión 1.071 y épocas
`[53,3,1,1]`. El protocolo y el consumidor congelado de SRC122 no cambian.

## Compilación y regresiones

La sonda recompila frontend, servicio y QtHost; reutiliza otras **467 entradas**
verificadas del enlace de SRC126. Se verifican 470 entradas, fuentes completas
base, firma ad hoc, resolución de frameworks y MOC conservado. Se conserva la
auditoría anterior de 19 archivos estáticos y 390 miembros. No se recompilan
dependencias. El candidato limpio conserva su SHA-256:
`716628b435ca3ee0e93cefad4646f09e742a4e443d954b137e29fa47b63788f4`.

Sonda corregida SHA-256:
`868133ddabdf65a7e8637ae99667fd0d5e8b10d2238c6e5cfe979c59a8fca14c`.

| Suite local | Aprobadas |
| --- | ---: |
| Debug x86_64 | 57 |
| Release x86_64 | 57 |
| ASan/UBSan x86_64 | 57 |
| TSan arm64 | 57 |
| Negativas del checker | 8 |
| Repositorio y supervisor | 58 |

Son **228 ejecuciones nativas** de handoff, ticket y servicio. Las tres nuevas
regresiones cubren copias tardías concurrentes sin propietario IO, repetición de
una solicitud ya retirada y duplicado mientras la primera llamada a la cola está
en curso y se cancela. Están registradas en CTest y el pipeline nativo existente.
ASan mantiene `detect_leaks=0`; las 57 seleccionadas de TSan no tienen exclusiones.
No se reejecutan las 304 pruebas del consumidor ni se cuentan como nuevas.

Se preservan dos fallos preparatorios adicionales. El primer runner apuntó a
una ruta base inexistente: falló su comprobación de identidad antes de copiar o
compilar. La primera sonda movió un `std::function` sin vaciar su origen: el estado
movido es válido pero no está especificado, y quedó una referencia global viva.
Su perfil tardío rechazó correctamente y cerró, pero falló `final_expired`.
La sonda corregida vacía explícitamente ese origen. Este fallo pertenecía a la
sonda; no se atribuye una fuga al frontend de producción.

HC-B mantiene ≤512 MiB combinados para dos bundles y fuentes/objetos/logs,
inicio de secuencia ≥11 GiB y suelo por comando ≥10 GiB. Los builds tardaron
51,58 y 44,41 s. Se registran muestras cada 0,5 s, procesos reales ≤100 s y
etapas nativas ≤512 MiB. IB02 para un build completo sigue en 20 GiB. Las etapas
y evidencia de SRC126 permanecen intactas; ISO, BIOS y bundles son privados.

## Siguiente tarea

Sigue **RT-T3c.2: margen temporal del inventario**. Se deben medir las fases y
su variación con una sonda separada, conservar intentos fallidos y coste de
instrumentación, y contrastar cualquier optimización con el candidato limpio
sin cambiar plazos, identidades ni verificadores. RT-T3c.3 y los gates de
JIT/caché/DMA/lifecycle siguen pendientes. Esta tarea no habilita captura,
admisión, CI remota, Linux ni ejecución en Nintendo 3DS.
