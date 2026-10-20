# F02.07 / LP-C — Coordinador runtime privado (SRC113)

## Resultado y alcance

Completa **RB-T2 / DW-T3b** y **RC-T1–3** de
[RC01–RC08](../../schemas/runtime-coordinator-v1.md): el coordinador privado
conserva CPU/PINE/VU/GS durante el intento diagnóstico, publica un ticket de un
solo uso y revoca antes de retirar las guardias o de las transiciones cubiertas.
**RB-T3 / DW-T3c, DW-T3 completo y captura siguen pendientes.**

La prueba ejecuta cuerpos privados exactos, los controles propios y dos hilos
VU/GS reales. Configuración VM, colas vacías, servidor PINE y dependencias Qt son
dobles declarados. Los 17 prefijos de entrada verifican el hook anterior al efecto;
no ejecutan el resto de esas funciones. Se compilan además las unidades completas.
No se enlaza ni ejecuta un nuevo PCSX2, ni se abre una VM, ISO o BIOS.

## Implementación y responsabilidades

`RuntimeDiagnosticTicket` separa publicación CPU de consulta/cancelación IO y
del trabajo DW. La vinculación mantiene su snapshot inmutable. Una generación
atómica permite invalidarla desde otros hilos antes de un efecto, sin callbacks,
IO ni unión de trabajadores. Agotar la generación o los IDs es terminal; no se
reinician. El reloj y la fuente de generación prestados deben sobrevivir a la
vinculación compartida. La generación global vive durante el proceso.

La fábrica captura errores de asignación en una unidad con excepciones habilitadas;
VMManager conserva sus flags originales sin excepciones. Los puertos, el reloj y
el validador mantienen el núcleo independiente de VMManager. El dueño CPU controla
guardias; el dueño IO cancela por su ticket y une DW después de liberarlas.
Esta distribución conserva responsabilidades pequeñas y sustituibles según SOLID.

`QueueObserverRuntimeDiagnostic` valida dueño, pausa, exclusión de intentos, ID y
plazo de hasta cinco segundos. Fija el deadline antes de asignar o adquirir guardias.
El ticket sigue pendiente durante el drenaje. Cuando este queda retenido, el
coordinador toma épocas de host/PINE y lifecycle VU/GS, usa el sampler AP privado,
revalida guardias y publica una única vinculación. Cambios posteriores revocan;
regresar a los valores anteriores no rehabilita el ticket. Cancelar uno viejo no
afecta al siguiente intento.

La frontera CPU privada revoca antes de destruir su guardia. Entrar en actividad
o anidar una frontera revoca antes del cambio. Qt mantiene la misma instancia
lexical mientras espera controles o diagnóstico, sin despachar eventos dentro
de la retención. Una salida de aplicación o espera externa cancela. Antes de
retener, despachar un evento Qt puede invalidar conservadoramente el ticket
pendiente; el futuro dueño IO deberá tratarlo como intento rechazado y crear otro.
La ruta histórica de drenaje sin ticket sigue completándose en una muestra.

Las entradas cubiertas incluyen inicio/parada PINE, notificación de productores,
hooks de lifecycle, liberación/inicio/parada de controles VU/GS y entradas VM de
estado, configuración, inicialización, apagado, reset, savestate, cachés y ejecución.
La señal atómica precede al efecto o a la espera serializada. **Es invalidación,
no prueba de sincronización de memoria ni cobertura total de escritores.**

La retención PINE acredita el cierre cooperativo observado aunque el servidor
esté habilitado. Se mantienen desconocidos `rdebug_excluded` y
`other_writers_excluded`, y violado `vif_dynarec_disabled` en el proveedor fijado.
JIT/caché/DMA y demás rutas no reciben acreditación nueva por este cambio.

## Verificación

- **108 ejecuciones de integración privadas:** 26 escenarios ON y uno OFF en
  Debug, Release, ASan/UBSan x86_64 y TSan arm64. Incluyen frontera, Qt, cancelación,
  cambio/regreso, productores ajenos a CPU, PINE, VU/GS, perfiles y trabajo bloqueado.
  El caso bloqueado libera guardias antes de desbloquear y unir DW; CPU no espera
  su limpieza. Las dependencias Qt son dobles, incluso al ejecutar su rama exacta.
- **Diez compilaciones completas de proveedor:** VMManager, PINE, MTVU, MTGS y
  QtHost en ON/OFF, con MOC correspondiente. Los objetos OFF no referencian símbolos
  del observador. Se compilan también cinco unidades propias con flags del proveedor,
  y excepciones solo donde corresponden. Esto no sustituye un enlace final.
- **455 escenarios nativos por variante**, 1.820 ejecuciones en Debug, Release,
  ASan/UBSan y cobertura: conserva los 428 anteriores y añade 12 de ticket y
  15 regresiones existentes de escrituras físicas/lifecycle. El caso largo previo
  de reloj real permanece compilado y excluido; no se cuenta como ejecutado.
- **94 ejecuciones adicionales TSan arm64:** 24 DW, 17 entrega, 26 vinculación,
  12 ticket, siete escrituras y ocho lifecycle. Las 27 de integración TSan están
  incluidas en las 108 anteriores; no se suman otra vez a ese total.
- **Diez controles negativos:** retiro temprano, falta de cierre de frontera,
  bucle Qt anterior, omisión de señal de productor/host/PINE, ignorar generación,
  omitir revalidación AP y omitir señales de liberación GS/VU. Cada copia provoca
  una aserción de la prueba; un timeout no se acepta como detección.
- Cobertura registrada: vinculación **103/103 líneas**, ticket **29/29** y fábrica
  **4/4**, generación **14/14**. Ramas: vinculación **116/126**, ticket **22/24** y
  generación **6/6**. LLVM conserva el aviso agregado de 33 funciones con datos
  incompatibles. No se atribuye cobertura completa al proveedor o coordinador.
  ASan usa `detect_leaks=0`; no acredita ausencia de fugas.
- **58 controles de repositorio y supervisión**, auditoría repetida con bytes
  idénticos y publicación de metadata. El CMake nativo incorpora los nuevos casos
  al pipeline existente; esta ejecución local no acredita CI remoto, Linux o 3DS.

## Intento conservado y custodia

La primera sonda pasó 18 escenarios y falló en `entry_hooks`: después de simular
inicialización/apagado CPU, la fixture no restablecía su actor antes del caso
independiente siguiente. Se conserva ese fallo, incluido el aborto posterior por
destrucción de un hilo aún unible. Se corrigió solo esa preparación de la prueba
y se ejecutaron las cuatro variantes completas en una etapa nueva. No cambió el
producto privado entre esos intentos. Los abortos de controles negativos tampoco
se presentan como evidencia de limpieza ordenada.

Tras detectar los dos primeros negativos, el control del bucle Qt anterior fue
rechazado por `-Werror`: dejaba sin uso el parámetro de apagado. Se conserva el
fallo de compilación y se añade únicamente un uso explícito sin efecto en esa
copia negativa. Los ocho controles restantes se ejecutan en una etapa nueva;
los dos ya detectados no se repiten. El código del producto permanece igual.

Los 154 inputs SRC112 se congelaron antes de modificar la vinculación, su cabecera,
CMake y los apéndices de estado. Otras tres fuentes propias se contrastan con sus
copias privadas anteriores. La fuente original conserva sus 2.966 archivos;
la nueva copia tiene 2.983, con ocho modificados y 17 añadidos. El parche queda
privado, junto con 33 fragmentos exactos y sus offsets/tipos. El repositorio
contiene código propio, contratos y hashes, sin cuerpos de terceros extraídos.

Se verifican dependencias de compilación, objetos, binarios, logs, muestras y
recibos de supervisión. Cada etapa mantiene reserva/suelo de 10 GiB y límite de
512 MiB. Los builds usan límites temporales separados; no se ejecuta el enlace
completo que exige la reserva IB02 de 20 GiB. Se conservan el proveedor original,
el candidato instalado y todas las etapas previas.

## Siguiente tarea: RB-T3 / DW-T3c

1. Congelar el nuevo proveedor y preparar un candidato enlazado con identidad,
   entorno y presupuesto IB02 verificados. Añadir la conexión del dueño IO con
   la cola CPU/ticket y el trabajador nativo; verificar que el enlace incorpora
   todos los hooks y que OFF conserva su comportamiento.
2. Con VM privada, validar pausa/retención, plazos, cancelación, callbacks tardíos,
   reapertura y cierre. Contrastar épocas/hechos observados y el orden
   revocación → liberación GS/VU/PINE → unión DW, también ante fallos.
3. Probar cada gate ausente y revisar cobertura de escritores JIT/caché/DMA,
   PINE/RDebug y lifecycle. Mantener desconocidas las rutas sin evidencia y
   conservar rechazos, recursos, hashes y revalidación final del candidato.

Solo esa validación puede cerrar DW-T3. La admisión de captura es una decisión
posterior e independiente; esta entrega no produce ReadEvents ni capacidades.
