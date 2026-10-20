# F02.07 — Ejecutor de diagnóstico con presupuesto y cierre

Fecha: 2026-10-19. Fuente: **SRC107**. Contrato:
[DW01–DW09](../../schemas/diagnostic-worker-v1.md). Evidencia:
[diagnostic-worker-evidence.json](../compatibility/diagnostic-worker-evidence.json).

## Resultado y alcance

Completa **DW-T1 / PT-T5c.1**, el núcleo de ejecución. `DiagnosticWorker` crea el
trabajo en otro hilo, comparte un deadline de 5 s entre preparación y primera
muestra, y asigna 2 s a cada revalidación. El buzón contiene un solo resultado;
recogerlo después del plazo también lo descarta. El reloj no se reinicia entre
fábrica, preparación, lectura, hash y publicación.

Se separan reloj, presupuesto, fábrica, proveedor y dueño de sesión mediante
puertos. La fábrica solo aporta configuración antes de comenzar; adquiere los
recursos dentro de `create()`. Preparación, muestreo, cierre y destrucción del
trabajo ocurren en el trabajador. El presupuesto es prestado durante esa vida y
no puede escapar a otros objetos/hilos. Sin hilo creado solo existe configuración.

Cancelación, peer perdido, época distinta, reloj regresivo, error y cambio de
identidad invalidan permanentemente el buzón. Se conserva la primera causa,
incluso si el proveedor retorna otra después. Secuencia, desafío, política,
inventario y épocas se comprueban antes de publicar. Un cambio seguido del valor
original no recupera la sesión. Los hechos AP pueden variar, nunca dan permisos.

## Cancelación y propiedad

Cancelar no destruye objetos ni cierra descriptores usados por otro hilo. La
espera distingue trabajo pendiente, hilo terminado y cierre confirmado. Si
`close()` falla, el hilo puede estar unido sin que la limpieza esté confirmada.
El propietario retiene el ejecutor cuando vence su espera de cierre. El destructor
cancela y une el hilo; no usa `detach` y debe ejecutarse fuera del hilo CPU y de
guardias retenidas.

La cancelación es **cooperativa**. Una syscall bloqueada o un adaptador que no
retorne puede retrasar el cierre: el resultado queda rechazado, pero no se declara
un cierre inexistente. No se implementa terminación forzosa de hilos C++.

## Verificación ejecutada

- **363 escenarios × cuatro modos = 1452 ejecuciones x86_64**, Debug, Release,
  ASan/UBSan y cobertura. Se conservan los 339 escenarios anteriores y se añaden
  24 del ejecutor. Las comprobaciones siguen activas en Release.
- **Cuatro ejecuciones adicionales con reloj real**, una por modo: vencimiento
  inicial de 5 s sin que el consumidor consulte el buzón y revalidación de 2 s
  observada cooperativamente por el proveedor. Los 24 escenarios anteriores
  usan además tiempo inyectado para comprobar fronteras exactas y acumulación.
- **24 escenarios con ThreadSanitizer arm64**, sin errores detectados. Incluyen
  100 ciclos de recogida inmediata, 100 carreras cancelación/recogida, retención
  del objeto durante destrucción, callback tardío y cierre fallido.
- **Seis regresiones detectadas**: omitir deadline, reiniciarlo por fase, omitir
  comprobación al recoger, ignorar lifecycle, ignorar identidad y anticipar cierre.
- Cobertura del núcleo en la batería principal: **176/183 líneas (96,17 %)** y
  **129/140 ramas (92,14 %)**. No se presenta como cobertura completa; esta cifra
  excluye la ejecución adicional con reloj real. Exportación aislada sin warnings;
  el exportador agregado conserva los 15 avisos preexistentes de funciones inline.

Los tests comprueban cada gate AP desconocido/violado, el caso de todos satisfechos
y el rechazo de hechos satisfechos sin épocas de VM. El resultado sigue siendo
diagnóstico tipado; no existe una capacidad de captura en esta API.

El pipeline `native-process.yml` incorpora los nuevos ejecutables a través de
CMake y conserva Linux/macOS con y sin ASan/UBSan. ThreadSanitizer se ejecutó
localmente; no se afirma ejecución remota de CI ni de Linux. Se configura el
CMake final para el test de reloj en una etapa nueva, manteniendo intactas las
fuentes y los resultados de la primera batería.

La primera comprobación de documentación detectó únicamente los tres enlaces al
JSON aún no publicado (57 controles correctos y uno fallido). Se conserva ese
recibo y se repite después de generar la evidencia, sin relajar el validador.

## Custodia y siguiente tarea

Se conserva una copia verificada de los **108 inputs de SRC106** antes de editar.
Fuentes propias, binarios, recibos de supervisión, perfiles de cobertura y mutantes
quedan en etapas nuevas. Las ejecuciones mantienen la reserva de 10 GiB, máximo
512 MiB por etapa, límites por comando y comprobación del cierre del grupo.
Dos auditorías independientes comprueban hashes y producen la misma evidencia.

No se ejecutó PCSX2, VM, ISO o BIOS en esta etapa; tampoco se modificó el candidato
ni el perfil productivo. El trabajo probado usa hilos reales y proveedores
sintéticos. **PT-T5c, PS-T4 y PD-T5 siguen abiertos.**

Sigue **DW-T2 / PT-T5c.2**: pasar el presupuesto por preparación nativa,
lectura/hash y canal, componer una sonda privada con este dueño, e inducir stalls
y desconexiones comprobando cierre. Después, **DW-T3** unirá lifecycle y guardias
runtime del coordinador. JIT/caché, DMA, escritores y exclusión del emulador siguen
siendo requisitos independientes. La captura continúa deshabilitada.
