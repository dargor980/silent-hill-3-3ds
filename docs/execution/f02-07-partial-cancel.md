# F02.07 — Cancelación durante entrega parcial

Fecha: 2026-10-19. Contrato [PC01–PC05](../../schemas/runtime-partial-cancel-v1.md).
Evidencia [SRC125](../compatibility/partial-cancel-evidence.json).

**PC-T1–PC-T4 y RT-T3c.1b.partial-delivery completos.** La señal de UI se consulta
dentro del bucle de entrega, antes y después de cada escritura. Ocho perfiles
con un prefijo real y contrapresión inyectada terminan por cancelación, rechazan
la respuesta incompleta y cierran ordenadamente. El candidato sin sonda conserva
el flujo ordinario de tres respuestas.

## Causa y cambio

SRC124 consulta cancelación entre pasos de sesión. Sin embargo, un paso puede
permanecer dentro de `deliver_diagnostic` hasta completar la respuesta o agotar
su presupuesto. La bandera de UI no llegaba a ese bucle. En dos perfiles del
candidato anterior, la acción Qt llega después de enviar/recibir el prefijo,
pero el productor termina con `reason=5` (plazo), no cancelación. Ambos cierran
limpiamente, sin respuestas aceptadas. No se presenta como bloqueo indefinido.

Las nuevas sobrecargas de entrega y sesión reciben la señal atómica por referencia
constante durante la llamada. IO la consulta y cancela el trabajador; la sesión
propaga la causa al handoff. Se conservan las firmas anteriores, el layout de
clases, los presupuestos, el protocolo y la primera causa terminal. El servicio
usa la nueva sobrecarga. La UI sigue sin acceder al socket, unir trabajadores o
esperar CPU. Transporte, cancelación y retirada mantienen responsabilidades
separadas.

La cancelación es cooperativa. Puede coincidir con una escritura ya iniciada;
los bytes enviados no se retiran. La garantía es comprobar la señal en cada
frontera de escritura y no iniciar otra después de observarla. Un consumidor
solo publica un frame completo que supera sus comprobaciones ordinarias.

## Contraste con PCSX2 real

La sonda privada limita la primera escritura real a **1 o 293 de 294 bytes**.
Después devuelve progreso cero en turnos acotados por el presupuesto recibido.
El consumidor registra los bytes devueltos por `recv` y crea un indicador local;
el timer Qt invoca cerrar ventana o la acción Salir al observarlo. La sonda no
cancela por sí misma ni amplía los plazos. Esta coordinación acredita el punto
de interrupción sin depender de una espera arbitraria.

La contrapresión está **inyectada**. No se afirma que el sistema operativo haya
fragmentado espontáneamente una respuesta tan pequeña. Las acciones Qt son
programáticas; esta etapa no añade pruebas de clics físicos ni CUA. La sesión y
el canal Python de SRC122 conservan sus bytes: el envoltorio solo observa `recv`,
sin alterar timeout, identidad, contenido o EOF.

| Prefijo recibido | Cierre de ventana | Salir de PCSX2 | Diagnósticos aceptados |
| --- | ---: | ---: | ---: |
| 1 byte | 2 perfiles | 2 perfiles | 0 |
| 293 bytes | 2 perfiles | 2 perfiles | 0 |

Los ocho perfiles corregidos registran `reason=6`, `replies=0`, `clean=1`,
`admitted=0` y salida cero. El consumidor recibe EOF tras el prefijo, rechaza
el intercambio, conserva `last=None` y cierra sin error. El decodificador también
rechaza por separado los bytes truncados guardados en la evidencia.

Las trazas verifican envío de prefijo → recepción acreditada → acción/señal UI
→ retiro CPU → DW unido → objetos IO destruidos → IO unido → parada CPU. El
socket puede cerrarse antes de terminar la retirada, para terminar el intercambio;
los objetos compartidos se conservan hasta que CPU y DW dejan de usarlos.
La señal y la acción corren en UI; los controles de retiro/unión de DW, en IO.
La UI retorna sin esperar esa unión. El máximo observado de señal a unión IO fue
47,12 ms; a retiro CPU, 30,63 ms; el manejador UI retornó en hasta 1,31 ms. Son
mediciones de esta tanda, no garantías de latencia ni evaluación de rendimiento.

El control normal del candidato sin sonda acepta tres respuestas, termina con
`reason=0`, espera liberación del consumidor y sale con código cero. Conserva
30 imágenes por archivo, 1.040 de caché, revisión 1.071 y épocas `[53,3,1,1]`.
Los dos perfiles base y sus rechazos por plazo se mantienen como evidencia
negativa; uno recibe EOF y el otro agota también el presupuesto del consumidor.

## Compilación y regresiones

La auditoría de dependencias localiza cuatro consumidores de las cabeceras:
entrega, sesión, sink macOS y servicio. Se recompilan los cuatro para el candidato
limpio, reutilizando 466 entradas verificadas del enlace. El candidato observado
recompila además QtHost: cinco unidades y 465 reutilizadas. La base observada
recompila tres unidades, conservando el comportamiento anterior. Se verifican
19 archivos estáticos, sus 390 miembros, firma ad hoc y resolución de frameworks.
No se recompilan dependencias de terceros. El candidato limpio pasa `testconfig`
y no contiene la sonda `SH3_PC`.

Ejecutable limpio SHA-256:
`e44fd1f36fa403ddacf39f791c56e10871d8b9771ef7a7d93224ff323b75df02`.

| Suite | Aprobadas |
| --- | ---: |
| Debug x86_64 | 114 |
| Release x86_64 | 114 |
| ASan/UBSan x86_64 | 114 |
| TSan arm64 | 111 |
| Repositorio y supervisor | 58 |

Total: **453 ejecuciones nativas**. Dos nuevos escenarios agrupan señal previa,
conexión/lectura, progreso cero, prefijos, último byte y conservación de la primera
causa. Se comprueba que no hay una escritura posterior al rechazo y que la unión
espera la retirada. Las APIs previas mantienen su batería. Los casos nuevos
quedan registrados en CTest y en el pipeline nativo existente. ASan mantiene
`detect_leaks=0`; TSan conserva las exclusiones fork/exec declaradas en SRC124.
Ruff, formato y comprobaciones del repositorio pasan. Las 304 pruebas del
consumidor de SRC122 no se vuelven a ejecutar ni se contabilizan aquí.

Se conserva un fallo preparatorio del runner: el preflight apuntaba inicialmente
a una ruta inexistente; falló antes de copiar fuentes o compilar. También se
conserva un fallo al procesar el primer resultado base: el checker confundía el
prefijo numérico con el marcador del log. Se recuperó el resultado del log
original después de corregir el checker, sin repetir ni alterar esa ejecución. La primera
pasada del auditor también confundió el timestamp posterior al cierre del archivo
indicador con su creación: en dos casos UI ya había observado el archivo. Se
conserva ese rechazo del auditor. La prueba de recepción previa procede del orden
`recv` → creación exclusiva del indicador → comprobación de existencia en UI;
no se afirma que el timestamp posterior preceda a la acción. Las trazas dentro
del productor conservan su orden verificado y no se modifican resultados.

PC-B supervisa cada comando, sin abandonar la reserva general IB02 de 20 GiB
para un build completo. Esta secuencia incremental parte de ≥11 GiB y mantiene
suelo de 10 GiB y ≤512 MiB combinados para los candidatos. Los tres builds tardan
42,41/48,88/62,74 s. Fuentes, bundles y etapas privadas de SRC124 se verifican
sin cambios; ISO, BIOS y perfiles se mantienen privados.

## Límites y siguiente tarea

Sigue **RT-T3c.1b.vm-shutdown**: botón Apagar VM, confirmaciones y retorno a la
lista de juegos, incluida la decisión de cancelar el diálogo. También siguen
callbacks tardíos/duplicados reales, margen temporal y gates JIT/caché/DMA/lifecycle.
Esta etapa no habilita captura, ni demuestra contrapresión natural, CI remota,
Linux o ejecución en Nintendo 3DS.
