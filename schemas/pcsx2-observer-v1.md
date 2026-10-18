# Observador interno PCSX2 — OB01–OB10

Complementa [MP v1](effective-mapping-v1.md) para la revisión fijada en SRC49.
El transporte contiene datos privados y no constituye un formato del port.

## Requisitos EARS

- **OB01:** WHEN se configure el emulador THEN el observador SHALL permanecer
  desactivado por defecto; su habilitación SHALL requerir una copia privada
  identificada y opción de compilación explícita, sin modificar el baseline.
- **OB02:** WHEN llegue una petición THEN el adaptador SHALL aceptar únicamente
  un comando aislado de versión conocida, sesión no nula, secuencia 1–256,
  PC alineado y rango de 1–4096 bytes sin overflow; SHALL rechazar campos
  reservados, longitudes o cobertura adicionales.
- **OB03:** WHEN se atienda una petición THEN la adquisición SHALL ejecutarse
  en el hilo CPU, exigir pausa, PC esperado y ausencia de escrituras pendientes
  de savestate. SHALL obtener dos muestras de mapa y contenido iguales, sin
  reanudar ni modificar memoria, registros, breakpoints o configuración.
- **OB04:** WHEN traduzca el rango THEN el lector SHALL sumar el bias de cada
  página módulo 2^64, rechazar handlers y segmentos fuera de los 32 MiB de RAM
  EE, y exigir respaldo contiguo. SHALL informar un alias distinto del offset
  esperado sin normalizarlo ni convertirlo en igualdad.
- **OB05:** IF la petición no se atiende en dos segundos THEN el transporte
  SHALL responder timeout; una tarea tardía SHALL conservar propiedad segura
  de sus datos y omitir la captura si ya fue cancelada. El hilo PINE SHALL
  poder terminar sin esperar indefinidamente al hilo CPU.
- **OB06:** WHEN se consulte un guardado THEN el adaptador SHALL distinguir
  cola de compresión vacía de archivo válido. La ausencia de trabajos SHALL
  comprobarse bajo el mutex original, sin join ni espera en el hilo CPU.
- **OB07:** WHEN se relacione una captura con un estado THEN el coordinador
  SHALL exigir mismo proceso, sesión, secuencia, PC, ciclo, CRC, mapa y bytes
  antes/después; archivo de destino inicialmente ausente, escritura terminada,
  hash estable y coincidencia con RAM/PC/ciclo importados del estado y PINE.
  Una respuesta a MsgSaveState SHALL NOT considerarse confirmación de escritura.
- **OB08:** WHEN se publiquen resultados THEN SHALL conservar blobs, sockets y
  estados en la raíz privada y publicar solo metadatos depurados tras cerrar
  lectores. IF falla I/O, cierre o coherencia THEN SHALL rechazar la evidencia.
- **OB09:** WHEN se valide el parche THEN SHALL probar dominio, protocolo,
  cancelación y errores con dobles propios en CI, y compilar el adaptador con
  los headers reales en la copia privada; SHALL distinguir eso de un build
  completo, captura real o aprobación MP08.
- **OB10:** WHILE observe THEN SHALL usar PINE en un socket Unix de directorio
  privado, con un único coordinador y sin edición manual concurrente. SHALL
  conservar la limitación de MP03: muestras iguales no prueban ausencia de
  modificaciones intermedias ni autentican ejecución.

## Diseño

El núcleo propio `tools/observer` depende de un puerto `Reader`, sin PCSX2,
filesystem ni SDK Nintendo. Valida, resuelve segmentos y compara dos lecturas.
Un códec separado maneja enteros little endian explícitos, sin cast de buffers
desalineados. El adaptador privado convierte globals del emulador a ese puerto.
El lector Python valida el transporte y reutiliza MP; nunca expone direcciones
en la representación o en sus metadatos públicos.

Se añade un comando experimental **0xE0** a PINE solo al habilitar el build.
El servidor original atiende un cliente y procesa sus mensajes secuencialmente.
La petición se encola al hilo CPU sin `BlockingQueuedConnection`; PINE espera
una finalización con plazo y propiedad compartida. Usar directamente la
invocación bloqueante permitiría un ciclo con `PINEServer::Deinitialize`, que
hace join desde el hilo CPU. El timeout limita esa espera, no el coste de otras
operaciones del emulador ni el transporte original completo.

`VMManager::HasPendingSaveStateWrites()` consulta la lista bajo su mutex.
No se llama `WaitForSaveStateFlush()` dentro del observador. El coordinador
solicitará captura A, MsgSaveState y captura B en la misma conexión; la cola
CPU conserva el orden de ese productor. B puede devolver `save_pending` y
debe repetirse con plazo externo. Un error de guardado puede dejar la cola
vacía: se exige igualmente archivo nuevo válido y comparación de contenido.
Ese coordinador de adquisición y custodia real corresponde a la unidad
posterior; esta entrega prepara su contrato y el productor del snapshot.

La integración usa `eeMem->Main`, `vtlbdata.vmap[page].raw()` y las constantes
de la revisión fijada, con aserciones de tamaño/layout. No usa offsets ABI
calculados externamente ni desreferencia direcciones host suministradas por
el cliente. La petición solo contiene direcciones virtuales PS2 y offsets
esperados de RAM.

## Protocolo privado v1

Todos los enteros son little endian. PINE añade longitud u32 al request y
longitud u32 + resultado u8 al reply. El comando debe viajar solo.

Request: **40 bytes** sin la longitud PINE: opcode u8=0xE0, versión u8=1,
reservado u16=0, sesión de 16 bytes, cinco u32 (secuencia, PC esperado,
dirección virtual, tamaño, offset esperado). Máximo total: 44 bytes.

Reply del observador: magic `SH3O`, versión u8=1, estado u8, reservado u16=0,
sesión de 16 bytes, los mismos cinco u32, tamaño de payload u32, offset
resuelto u32, coincidencia u32 (0/1), dos snapshots y payload. Cabecera con
snapshots: **232 bytes**; máximo con PINE: **4.333 bytes**.

Cada snapshot ocupa **88 bytes**: PID u64, PC u32, ciclo u64, base EE u64,
vmap u64, RAM expuesta u32, flags u32 (pausa=1, guardado pendiente=2),
CRC de disco u32, número de páginas u32; dos entradas (página u32, reservado u32=0,
bias u64), y reservado u32=0. Entradas no utilizadas deben ser cero.

Estados: 0 válido, 1 petición, 2 pausa, 3 guardado pendiente, 4 anchors/ABI,
5 PC inesperado, 6 handler, 7 fuera de RAM, 8 respaldo no contiguo,
9 muestra inestable, 10 lectura fallida, 11 contenido cambiante, 12 timeout.
En error se omiten snapshots, offset y payload (campos binarios a cero);
se conserva únicamente el eco de la petición y el código. Peticiones que
no cumplen el framing/versionado se rechazan con el fallo PINE original.

## Alcance de la evidencia

La sesión y secuencia son etiquetas del coordinador, no autenticación.
PID, PC/ciclo y CRC ayudan a rechazar mezclas; la identidad del ejecutable y
perfil debe fijarse externamente. Pausa y cola CPU aíslan la ejecución EE/IOP
y el servidor PINE durante el callback; no se afirma auditar todos los
escritores posibles de UI, plugins o agentes externos. No editar ni cargar
estados entre las muestras que forman una observación. Las cuatro paradas
reales, continuidad física y vínculo de recurso siguen sujetos a MP08.

## Tareas y aceptación

- [x] Definir OB01–OB10 y frontera con MP02; revisar las fuentes fijadas.
- [x] Implementar `Reader`, dominio, códec y finalización cancelable propios.
- [x] Probar fronteras de página/RAM, ciclos superiores a 2^32, aliases,
  handlers, pausa, guardado pendiente, cambios de identidad/mapa/contenido,
  framing inválido, respuestas truncadas y timeout con callback tardío.
- [x] Preparar parche privado identificable; configurar OFF/ON y compilar
  unidades modificadas con headers reales. Mantener originales intactos.
- [x] Enlazar/empaquetar el build instrumentado y probar PINE real con plazo
  y cierre: [SRC51](../docs/execution/f02-07-pcsx2-observer-build.md).
- [x] Implementar coordinador OB07–OB08: importación de ciclo u64 del estado,
  custodia, fallos de lectura/escritura/cierre y publicación atómica del recibo.
  [SRC52](../docs/execution/f02-07-observer-acquisition.md): pruebas sintéticas
  positivas y rechazo real sin VM; adquisición positiva del juego pendiente.
- [ ] Ejecutar cuatro paradas MP08 con el juego y verificar vínculo físico.

La batería del productor no simula un filesystem: el núcleo carece de I/O.
Los fallos de lectura/escritura/cierre/publicación del coordinador se comprueban
por separado en [AC01–AC10](observer-acquisition-v1.md); no están acreditados
por las pruebas del códec ni implican cuatro observaciones reales aceptadas.
En macOS esta revisión de PINE usa `TMPDIR`; el lanzamiento posterior deberá
fijarlo a un directorio privado corto, con permiso 0700, umask 077 y longitud
compatible con `sockaddr_un`. No se reutilizará un socket de otro proceso.
