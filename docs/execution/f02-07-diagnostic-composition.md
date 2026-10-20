# F02.07 — Composición privada del diagnóstico

Fecha: 2026-10-19. Fuente: **SRC111**. Contrato:
[DC01–DC08](../../schemas/diagnostic-composition-v1.md). Evidencia:
[diagnostic-composition-evidence.json](../compatibility/diagnostic-composition-evidence.json).

## Resultado

Completa **DC-T1–T3 / NW-T3c**, y con ello **NW-T3 / DW-T2 / PT-T5c.2** para
diagnóstico privado sin VM. Se ejecutan **20 casos finales** con consumidor BC,
trabajador DW, inventario y sink macOS en una copia PCSX2 `-testconfig`.
Las fuentes de producto de SRC109/SRC110 se reutilizan sin cambios.
**DW-T3, PT-T5c completo, PS-T4, PD-T5 y captura permanecen pendientes.**

Hay **21 procesos PCSX2**: uno rechaza por cambio del loader antes de alcanzar
la inyección de lectura; se conserva como intento no completado y se repite en
un proceso nuevo. No se relaja la política del inventario ni se reintenta dentro
de una sesión. El intento anterior de compilación de la sonda falla por omitir
`libbsm`; se conserva y se corrige el enlace en una etapa nueva, usando la misma
dependencia que el bridge nativo existente. Ese intento no ejecuta PCSX2.

## Composición y presupuestos

El launcher crea un endpoint Unix privado, inicia el hijo y obtiene su nacimiento
del kernel. El consumidor contrasta ese PID/nacimiento y el UID esperado. La
sonda contrasta al padre con datos nativos y conserva su identidad completa
para las escrituras. Las expectativas de manifiesto, política y plataforma se
fijan localmente antes de lanzar el proceso; no llegan en la solicitud PD.

La sonda se ejecuta al salir de `testconfig`, fuera del hilo CPU y de guardias
de emulación. El productor fija su deadline antes de conectar/recibir la primera
solicitud y antes de recibir las siguientes. El mismo plazo cubre preparación,
lectura, hash, serialización y entrega retenida. BC usa su propio reloj y plazo
total desde la comprobación del peer hasta admitir el frame. No se transmiten
ni equiparan relojes absolutos entre procesos.

Las tres sesiones positivas aceptan una muestra inicial y dos revalidaciones
cada una. El caso de hash en revalidación conserva solo la primera: **diez frames
aceptados en total**. En cada sesión se conservan identidad, nonce y evidencia;
se verifican correlación y plazo. Cada muestra clasifica **26 imágenes de
aplicación y 621 de plataforma**, revisión de loader **648**. Los 18 hechos
runtime permanecen desconocidos y las cuatro épocas en cero. El diagnóstico
sigue teniendo plataforma asumida y no concede permisos de captura.

El positivo básico tarda aproximadamente **1,03 s / 0,85 s / 0,80 s** en el
consumidor, dentro de 5 s/2 s. Son tiempos de esta ejecución, no garantías de
rendimiento del SO ni del juego.

## Matriz ejecutada

| Casos | Resultado observado |
| --- | --- |
| Positivo, fragmentación de 3 bytes y backpressure con reanudación | Tres muestras aceptadas por caso; cierre confirmado |
| Backpressure hasta deadline | Un byte enviado, 188 escrituras sin progreso; cero muestras aceptadas |
| Deadline en preparación, lectura o hash | Cero muestras; consumidor y productor terminan por deadline |
| Deadline de hash durante revalidación | Solo la primera muestra aceptada; segunda rechazada |
| Cancelación del productor en preparación, lectura o hash | Cero muestras; limpieza pendiente observada antes de liberar el bloqueo |
| Cancelación del consumidor durante lectura | BC conserva cancelación; DW observa pérdida del peer y termina |
| Cancelación de productor o consumidor durante envío | 17 bytes parciales, sin entrega confirmada ni muestra aceptada |
| Desconexión durante lectura o envío | Cero muestras; DW conserva pérdida del peer; envío parcial de 17 bytes en el segundo caso |
| Deadline durante envío | 17 bytes parciales; ninguna confirmación o admisión tardía |
| Manifiesto incorrecto | Rechazo de configuración antes de muestrear |
| Peer incorrecto en consumidor o productor | Rechazo en la frontera correspondiente; cero muestras |

El backpressure es **readiness real del socket**, provocado con `SO_SNDBUF` y
`SO_SNDLOWAT` de 1024 bytes y escrituras de un byte mientras el lector de prueba
retiene el drenaje. No se añade relleno ajeno a PD. Al reanudar tras 200 ms, los
882 bytes de las tres respuestas se transmiten con diez llamadas sin progreso.
Esto no representa saturación de un socket con configuración de producción.

En el caso de deadline por backpressure, la envoltura de prueba mantiene al
consumidor dentro de `recv` durante 5,2 s adicionales. BC observa el vencimiento
cuando vuelve el control, a unos **6,12 s** desde el inicio, y descarta la salida.
El productor conserva su plazo de 5 s y tampoco confirma la entrega. Se verifica rechazo tardío, **no** una latencia
máxima de retorno de 5 s frente a una llamada que no coopera. La demora de envío
también es un control local de prueba; no modifica el sink de producto.

Cada caso verifica unión del trabajador, limpieza DW, cierre del sink, cierre
del consumidor sin error y salida del hijo. Se compara la tabla de descriptores
**0–1023** antes/después en PCSX2; no se afirma observar todos los descriptores
posibles. La confirmación del productor y la admisión del consumidor se cuentan
por separado. Una nueva llamada tras el cierre no devuelve muestra.

## Custodia y verificación

Los **135 inputs de SRC110** se verifican y copian antes de actualizar estado.
Los 200 archivos regulares de cada copia PCSX2 se contrastan con la referencia
previa y después de cada intento. Los 26 archivos del manifiesto se verifican
antes/después; la copia del contrato usada para su hash se conserva congelada.
Se registran fuentes de sonda/launcher, bibliotecas verificadas, bridge arm64,
manifiestos, recibos supervisados y frames privados. Solo se publica metadata.

Los comandos usan reserva inicial y suelo de 10 GiB, máximo 512 MiB por etapa,
plazo de 60 s y cierre de grupo verificado. El fallo de enlace se registra con
salida 1; los 21 procesos posteriores terminan con salida 0 y validación de
resultados. No se recompila el emulador ni se modifica la aplicación instalada.

No se vuelve a atribuir cobertura, sanitizadores o CI remoto a esta sonda:
SRC109/SRC110 conservan esa evidencia de los componentes. Los **58 controles de
repositorio y supervisión** pasan después de publicar la evidencia preliminar;
dos auditorías finales idénticas verifican custodia y publicación. No se usa
ISO, BIOS ni VM; no se producen ReadEvents ni se ejecuta una compilación 3DS.

Sigue **DW-T3 / PT-T5c.3**: conectar el coordinador runtime, sus épocas y guardias
CPU/PINE/VU/GS y de JIT/caché/DMA/escritores; probar invalidación antes de destruir
VM, cambio/regreso y cada permiso ausente. La captura se evaluará por separado.
