# F02.07 / LP-C — Composición nativa con runtime (SRC116)

Fecha: 2026-10-19. Contrato: [NR01–NR08](../../schemas/native-runtime-composition-v1.md).
Evidencia: [native-runtime-composition-evidence.json](../compatibility/native-runtime-composition-evidence.json).

## Resultado y alcance

Completa **NR-T1/NR-T2 / RS-T3a**: consumidor BC en un proceso y sesión RS,
frontend asíncrono, DW e inventario nativo en una copia PCSX2 `-testconfig`.
Se alcanzan **17 controles**, con **11 muestras aceptadas** en total. El último
control se alcanza con traza del loader; sus tres intentos sin traza se detienen
antes por cambios de imágenes. No se afirma que ese control se reproduzca sin
traza ni que el loader sea estable en todos los arranques.

**Host/VMManager y los hechos/épocas CPU son dobles declarados.** Los hilos CPU,
IO y DW son distintos; identidad de proceso, socket, peer, manifiesto, archivos,
mapas, slices, cache y hashes son nativos. El frontend propio se incluye sin
modificarlo, redirigiendo explícitamente sus puertos a los dobles. No se ejecuta
VM, ISO ni BIOS, ni se recompila el emulador. **RS-T3b, RB-T3/DW-T3 y captura
permanecen pendientes.**

## Recorrido verificado

El launcher congela las expectativas antes del lanzamiento, crea un endpoint
Unix privado y contrasta el nacimiento/PID/UID del hijo mediante el bridge nativo.
El productor contrasta al padre y conserva su identidad completa. El deadline
de cinco segundos se fija antes de conectar y despachar CPU; el mismo alcance
cubre adquisición, inventario y las tres entregas. La revalidación tiene además
su ventana de dos segundos, incluida recepción y espera inactiva.

Las muestras aceptadas clasifican **26 imágenes de aplicación y 620 de
plataforma**, con revisión de loader **647**. Dentro de cada sesión se conservan
nonce, identidad, evidencia y épocas. El doble declara seis hechos satisfechos,
uno violado (`vif_dynarec_disabled`) y once desconocidos, con épocas
`11/12/13/14`. Esos valores no se atribuyen a una VM real ni habilitan captura.

El positivo básico registra aproximadamente **0,91 / 0,91 / 0,85 s** en el
consumidor. El presupuesto total del alcance CPU se mantiene; esos tiempos son
mediciones locales, no garantías de latencia del sistema operativo.

## Controles

| Escenario | Muestras aceptadas | Resultado |
| --- | ---: | --- |
| Positivo, fragmentación y backpressure con reanudación | 3 por caso | Identidad y vínculo conservados; cierre confirmado |
| Manifiesto incorrecto | 0 | Rechazo de configuración |
| Peer incorrecto en productor o consumidor | 0 | Rechazo en la frontera correspondiente |
| Cancelación antes del callback y callback vencido | 0 | Cero adquisiciones y cero trabajo nativo |
| Cola CPU rechazada | 0 | No se crea trabajo nativo |
| Revocación o cancelación durante lectura nativa | 0 | Causa conservada y limpieza pendiente |
| Desconexión o cancelación del consumidor durante lectura | 0 | Pérdida del peer y limpieza pendiente |
| Revocación al recibir la segunda solicitud | 1 | Segunda entrega rechazada |
| Cancelación o revocación durante envío | 0 | 17 bytes parciales; ninguna entrega confirmada |
| Plazo de segunda solicitud, con traza del loader | 1 | Segunda muestra rechazada por vencimiento |

El backpressure usa `SO_SNDBUF/SO_SNDLOWAT=1024`, escrituras de un byte y una
pausa local de 200 ms del lector después de observar falta de progreso. No se
añade relleno al protocolo ni se atribuye esa configuración al producto.

Los cuatro controles de lectura bloqueada verifican dos estados pendientes:
antes de que CPU retire el ticket y después, mientras DW sigue bloqueado.
Solo al liberar el bloqueo se confirma unión y limpieza. Se verifica cierre del
socket, del consumidor y ausencia de diferencias en descriptores **0–1023**;
no se afirma observar todos los descriptores posibles.

## Intentos conservados

- **Etapa v1:** compilación y preflight correctos; el hijo no conecta durante
  los 15 segundos del launcher. Se conserva la salida 1 del launcher y el cierre
  de su grupo. El log no identifica la causa interna; no se atribuye a una
  reparación concreta el éxito posterior.
- **Etapa v2:** error del script al seleccionar un nombre de contrato inexistente.
  Se conserva la preparación parcial; no compila ni ejecuta PCSX2.
- **Etapa v3:** 19 procesos; 16 controles alcanzados y tres rechazos de loader
  antes del control pretendido. Dos ocurren durante preparación y uno durante
  el primer muestreo. El script conserva su fallo al no completar el último caso.
- **Replay:** dos procesos nuevos con binario, manifiesto y política idénticos;
  ambos rechazan por cambio del loader antes del control de segunda solicitud.
  Se conserva el agotamiento del máximo de tres intentos normales de ese caso.
- **Traza:** un proceso con `DYLD_PRINT_LIBRARIES` habilitado solo en el hijo
  alcanza el último control. Registra la carga de `Dyld.framework` después de
  entrar en la sonda; esa observación en un proceso exitoso no identifica por sí
  sola la imagen que cambió en los cinco rechazos anteriores.

En total se lanzan **23 procesos PCSX2**: 22 producen resultados de la sonda
y uno no completa la conexión inicial. Se conservan cinco rechazos de loader
sin relajar la política ni reintentar dentro de una sesión.

## Custodia y validación

Los 193 inputs de SRC115 se verifican y copian antes de editar documentación.
Los componentes de producto y sus bibliotecas Release se reutilizan con sus
hashes verificados; no se modifica su código ni se atribuyen nuevos sanitizadores
o cobertura a esta sonda. Las tres copias de app conservan los 200 archivos de
la referencia y sus enlaces; los 26 archivos de cada manifiesto se contrastan
antes/después. Las expectativas permanecen congeladas, incluida la instantánea
original del contrato usada por la política, aunque el documento de tareas se
actualice posteriormente.

Se conservan scripts, fuentes de fixture, manifiestos, logs, recibos, intentos y
frames privados. Cada comando supervisado usa inicio/suelo de **10 GiB**, máximo
de **512 MiB** por etapa y plazo de **60 s**. La aplicación instalada y las
copias previas no se modifican. Solo se publican fuentes propias y metadata/hash.
No se ejecutan CI remoto, Linux ni compilación 3DS; el pipeline existente queda
sin cambios. Los controles de repositorio/supervisión y dos auditorías finales
verifican la publicación.

## Siguiente tarea

**RS-T3b:** integrar el dueño IO con Host/VMManager reales, preparar un candidato
nuevo y enlazarlo bajo IB02, que exige 20 GiB libres al comenzar. Validar con VM
pausa, lifecycle, callbacks tardíos, gates y escritores JIT/caché/DMA. La
inestabilidad de arranque/loader observada queda registrada como limitación de
repetibilidad; deberá mantenerse el rechazo ante cambios.
