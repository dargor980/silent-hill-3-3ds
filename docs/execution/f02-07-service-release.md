# F02.07 — Liberación tras la última respuesta

Fecha: 2026-10-19. Contrato [FC01–FC05](../../schemas/runtime-service-release-v1.md).
Evidencia [SRC122](../compatibility/service-release-evidence.json).

## Resultado y alcance

**FC-T1–FC-T3 y RT-T3b/RT-T3b.3 completos para diagnóstico positivo.** El servicio
conserva el canal después de su tercera respuesta para que el consumidor la
valide y anuncie el fin de solicitudes. Dos perfiles nuevos de confirmación
aceptan consecutivamente tres respuestas y cierran con código cero. El primer
perfil exploratorio también pasa; el segundo agota el plazo global y se conserva.
No se amplía ningún límite ni se habilita captura.

La prueba dirigida reproduce el problema de SRC121: el cierre inmediato deja
EOF junto al último frame. El rechazo ordinario del consumidor es correcto.
Ahora el productor espera liberación dentro del menor entre el plazo original
de cinco segundos y dos segundos desde la última entrega. Revisa cancelación,
reloj e identidad antes/después de IO y sondea como máximo cada 20 ms.

## Contrato de cierre e identidad

El servicio decide cuándo terminar; `MacOSDiagnosticSink` conserva el descriptor
y comprueba transporte/identidad. La operación terminal no cambia layout ni
tabla virtual. No solicita una cuarta muestra y cualquier byte adicional es un
error de protocolo. Conserva CPU/handoff/DW hasta la limpieza existente.

El launcher valida las tres respuestas con el mismo codec y sesión de SRC121,
hace `shutdown(SHUT_WR)` y mantiene su descriptor hasta recibir EOF del productor.
En macOS un cierre físico retira las credenciales del socket: se rechaza por
identidad no disponible. El medio cierre permite verificar dos veces PID,
nacimiento, usuarios, versión de PID y audit token antes de terminar. El lector
terminal está separado del lector ordinario y de la ABI Python; estos siguen
rechazando EOF. Observar liberación no prueba por sí solo publicación: los
resultados del consumidor son la evidencia independiente de aceptación.

## Compilación y pruebas

La matriz de dependencias identifica tres unidades afectadas: `macos_peer`,
`macos_diagnostic_sink` y `runtime_service`. Se reconstruyen en un stage nuevo,
con una superposición de 106 fuentes propias; se reutilizan 467 de 470 entradas
de enlace y se preservan fuentes, objetos y bundle anteriores. La matriz también
verifica dependencias de 390 miembros en 19 archivos estáticos.

El candidato contiene 200 archivos regulares y 42 Mach-O; resolución de
frameworks, firma ad hoc y `testconfig` pasan. Ejecutable SHA-256:
`45c78a01a374f24ee271e7c0736a42f0ac9d086639f123a8458fdb078cda8689`.
El build dura 40,36 s y el enlace 22,612 s. FC-B exige inicio ≥11 GiB, suelo
10 GiB, máximo 256 MiB de etapa y 180 s por comando; la secuencia tiene 600 s.
IB02 general sigue en 20 GiB. No se recompilan dependencias de terceros.
El mínimo observado entre las etapas supervisadas fue 11,50 GiB libres y el
máximo medido del candidato, incluidos perfiles y logs, fue 125,23 MiB.

Se fija un consumidor de 92 archivos y un manifiesto de 46 archivos/cinco raíces,
incluidos los tres componentes Apple verificados en SRC121. ISO/BIOS se leen y
contrastan por hash; no se copian al repositorio.

| Suite final | Ejecuciones aprobadas | Alcance |
| --- | ---: | --- |
| Debug x86_64 | 109 | Canal, peer, servicio, sesión y entrega |
| Release x86_64 | 109 | Mismas regresiones |
| ASan/UBSan x86_64 | 109 | Sin detección de fugas; aborta ante errores |
| TSan arm64 | 106 | Excluye los tres casos fork/exec declarados |
| Python | 304 | Codec, canal, sesión y presupuesto |
| Repositorio/supervisor | 58 | Arquitectura, custodia, specs y procesos |

Son **433 ejecuciones nativas aprobadas**. Se añaden 18 casos: última entrega,
cierre inmediato, medio cierre, cierre físico, bytes adicionales, silencio,
cancelación, plazo, identidad, dueño y errores de IO. Los intentos Debug iniciales
con tres y un fallos se preservan junto con sus fuentes; llevaron a separar el
lector terminal y a exigir medio cierre. No son ejecuciones aprobadas.
Los casos nuevos están registrados en CTest; no se ejecutó CI remota ni Linux.
La primera comprobación documental detectó tres enlaces al JSON aún no generado
en un caso de prueba. Ese resultado queda conservado; tras generar la evidencia
se repiten y aprueban los 58 casos.

## Todas las sesiones con VM

| Perfil | Consulta 1 | Consulta 2 | Consulta 3 | Aceptadas | Resultado |
| --- | ---: | ---: | ---: | ---: | --- |
| Primero | 1,595 s | 1,504 s | 1,440 s | 3 | Liberación correcta |
| Repetición inicial | 1,891 s | 1,689 s | 1,407 s | 2 | Plazo global agotado |
| Confirmación 1 | 1,703 s | 1,411 s | 1,413 s | 3 | Liberación correcta |
| Confirmación 2 | 1,886 s | 1,412 s | 1,404 s | 3 | Liberación correcta |

Los tiempos corresponden a consultas del consumidor; el plazo nativo empieza
antes de conectar y encolar CPU. En el rechazo suman 4,987 s y el productor
registra `reason=5`, `replies=2`, `release_waited=0`: vence durante el inventario
de la tercera consulta, antes de entrar en la nueva fase de liberación. No se
ha demostrado una causa externa concreta de esa variación. El margen temporal
bajo carga sigue pendiente; repetir con éxito no elimina este resultado.

Cada perfil exitoso registra `reason=0`, `inventory=0`, `replies=3`,
`release_waited=1`, `clean=1`, `admitted=0`. Las muestras conservan identidad,
nonce, revisión 1.071 y épocas `[53, 3, 1, 1]` dentro de su sesión; inventario
de 30 imágenes por archivo y 1.040 de caché. Se decodifican los 11 frames
aceptados de las cuatro sesiones con sus expectativas fijadas. El control sin
VM rechaza por indisponibilidad, sin muestras, y cierra correctamente.

`cpu_pending=1` indica que la limpieza tuvo que esperar retirada CPU; no que
quede trabajo pendiente al salir. Los procesos supervisados terminan sin hijos
pendientes. Las condiciones desconocidas/violadas de las muestras se conservan.
No se capturó RAM, no se compilaron binarios 3DS y no se validaron los gates
RS-T3/RB-T3/DW-T3 de JIT, caché, DMA y ciclo de vida.

## Próximas tareas

1. **RT-T3c.1:** diseñar y probar cancelación antes/después del despacho CPU,
   callbacks tardíos y cierre durante trabajo con los adaptadores reales;
   verificar ausencia de publicaciones posteriores y retirada de recursos.
2. **RT-T3c.2:** medir el coste por fase del inventario y su variación, preservando
   el rechazo de esta etapa. Proponer una optimización que mantenga todas las
   verificaciones y plazos; no atribuir el problema a carga sin medirlo.
3. **RT-T3c.3:** contrastar por separado las condiciones pendientes de escritores
   JIT/caché/DMA y ciclo de vida. Una respuesta diagnóstica válida no las satisface.
