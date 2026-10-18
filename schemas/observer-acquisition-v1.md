# Coordinador de adquisición — AC01–AC11

Complementa OB07–OB08, PS y MP. Alcance: PCSX2 SRC51, macOS x86_64,
perfil europeo español/Normal/Normal; sin cambios al runtime Nintendo.

El hash del perfil se fija tras inicializar la UI: cualquier normalización
automática debe inspeccionarse y registrarse antes de fijarlo. No se acepta
un cambio de perfil durante la adquisición ni se actualiza su hash al fallar.

## Requisitos EARS

- **AC01:** WHEN importe el estado THEN SHALL exigir la versión PS fijada,
  bloque cpuRegs completo de 1.160 bytes, PC sin delay slot y ciclo u64 en
  offset 1.088; SHALL contrastar RAM, PC y ciclo con el observador.
- **AC02:** WHEN inicie THEN SHALL fijar petición/sesión, ejecutable, perfil,
  PID/identidad de inicio, socket privado y PID del peer; SHALL rechazar
  identidad distinta antes y después de adquirir y no reconectar.
- **AC03:** WHILE adquiera THEN SHALL poseer una conexión, directorio privado
  anclado y lock exclusivo; SHALL acotar todo a 30 segundos y 256 consultas
  de guardado como máximo. Un fallo de transporte SHALL inutilizar la conexión.
- **AC04:** WHEN solicite guardar THEN SHALL comprobar previamente destino y
  backup ausentes, pausa, CRC esperado y captura A válida; SHALL encolar
  SaveState y B desde la misma conexión. Solo `SAVE_PENDING` permite repetir B.
- **AC05:** WHEN la cola esté vacía THEN SHALL exigir un archivo nuevo regular
  0600, sin enlaces, de hasta 64 MiB, identidad/hash estables y estado válido;
  respuesta SaveState o ausencia de trabajos SHALL NOT probar escritura exitosa.
- **AC06:** WHEN valide THEN SHALL comparar A/B/C, PID, PC, ciclo, CRC, mapa,
  contenido, RAM del estado y lecturas PINE del rango virtual. C se obtiene
  después de leer el estado y PINE. Un alias distinto SHALL conservarse.
- **AC07:** WHEN contraste CRC THEN SHALL distinguir disco (PINE/observador)
  de ejecutable activo (estado); esta unidad SHALL aceptar solo su igualdad
  con el CRC esperado, rechazando otros ejecutables sin normalizarlos.
- **AC08:** WHEN termine THEN SHALL conservar estados/paquetes privados y
  cerrar todos los lectores, conexión y lock antes de publicar metadatos.
  Fallos de lectura, escritura o cierre SHALL impedir devolver éxito.
- **AC09:** WHEN publique THEN SHALL escribir/flush/fsync/cerrar un temporal
  exclusivo y enlazarlo sin sobrescribir. IF falla después del enlace THEN
  SHALL informar publicación comprometida/incierta y prohibir reintento
  automático; SHALL NOT prometer rollback de una publicación ya visible.
- **AC10:** WHEN reporte THEN SHALL ocultar rutas, registros, CRC y bytes;
  SHALL distinguir coherencia de entradas suministradas de captura real y
  autenticación. Pruebas sintéticas y rechazos sin VM SHALL mantener la
  adquisición real y MP08 pendientes.
- **AC11:** WHEN importe estructuras internas del estado de juego THEN SHALL
  admitir hasta 4 MiB descomprimidos en esta extensión, validar el CRC ZIP del
  miembro completo y decodificar solo el prefijo conocido. Un tamaño superior
  SHALL ser rechazado antes de abrir el miembro. El lector PS histórico SHALL
  conservar su límite de 1 MiB. Este presupuesto es una política local, no
  una afirmación de tamaño máximo del formato PCSX2.

La sesión real posterior a SRC52 observó 2.597.162 bytes de estructuras
internas y rechazó correctamente el límite anterior. `FreezeInternals` incluye
subsistemas después de cpuRegs y `gifPathFreeze` serializa un buffer de tamaño
variable. AC11 permite ese caso dentro de un presupuesto explícito; no cambia
versión, ABI, CRC ni otros criterios de aceptación.

## Diseño

`observer_transport.Session` posee el socket y un deadline total. El códec
OB interpreta sus replies. `observer_state` interpreta el prefijo ampliado y
una ventana física de RAM. `observer_acquisition` coordina mediante puertos
de canal, custodia, identidad y reloj, sin dependencias de UI o PCSX2 C++.
`observer_files` implementa custodia POSIX; `observer_identity` fija proceso,
perfil y endpoint; la publicación ocurre fuera de todos sus contextos.

La sesión sigue CRC/pausa → A → comprobar ausencia → SaveState → B sin
trabajos → leer estado → PINE → C → releer hash → guardar paquetes → cerrar
→ revalidar identidad → publicar. Los paquetes se decodifican con el hash
real del estado una vez disponible; un hash provisional nunca se publica.
La conexión no se reutiliza tras error y no se reintenta un guardado.

PINE solo recibe lecturas, consulta de estado/CRC y un SaveState de slot
1–99. El nombre del destino se deriva de serial/CRC/slot según la revisión
fijada. El launcher debe vincular ese directorio con el perfil esperado y
no permitir edición concurrente de UI, carga de estados ni otros escritores.
El lock coordina clientes cooperantes; no autentica procesos ni impide todos
los escritores del mismo usuario. Dos muestras iguales tampoco lo hacen.

La ABI se comprueba compilando un programa propio con las cabeceras y opciones
reales de SRC51. El lector PS previo conserva su contrato de prefijo; solo
AC exige el bloque completo y el ciclo. Los CRC difieren semánticamente aunque
en el alcance europeo solicitado deban coincidir para aceptar una captura.

## Tareas y aceptación

1. [x] Contrastar ABI/serialización y añadir lector estricto con ciclos altos,
   truncamientos y CRC distinto (AC01/07).
2. [x] Conexión persistente, deadline único, peer y envenenamiento tras error;
   preservar el cliente de una operación y sus tests (AC02/03).
3. [x] Secuencia inyectable A/SaveState/B/estado/PINE/C con oráculo independiente,
   pendientes acotados y todos los desacuerdos rechazados (AC04–07).
4. [x] Custodia anclada, lock, archivos nuevos, cierre y publicación con punto
   de commit explícito; pruebas de I/O adverso (AC08/09).
5. [x] Integrar identidad/perfil/socket y probar el candidato exacto sin VM;
   regresión/cobertura/CI sintética, metadatos y próxima sesión MP08 (AC10).

## Evidencia y trabajo pendiente

[SRC52](../docs/execution/f02-07-observer-acquisition.md) acredita la ABI,
124 casos adicionales, 2.196 pruebas Python aprobadas y el rechazo real
`ACQUIRE_PAUSE` sin juego. La CI existente descubre estos tests; su ejecución
remota sigue sin comprobarse. El caso positivo completo utiliza datos propios
sintéticos, incluido el filesystem; no acredita una captura del juego.

- [x] Validar una adquisición positiva con el candidato exacto y la ISO europea.
- [x] Completar entrada/pre-SW/post-SW/retorno en una sesión nueva MP08.

[SRC53](../docs/execution/f02-07-observer-live.md) completa ambos puntos para
una invocación real, incorpora AC11 y compara la serie mediante
[OS01–OS06](observer-series-v1.md). La evidencia histórica SRC52 conserva los
hashes y límites vigentes en su entrega; SRC53 registra esta extensión.

`state_binding_verified=true` acredita coherencia entre entradas suministradas;
el recibo mantiene `live_acquisition_verified=false` y autenticación no provista.
Una sesión real necesita evidencia adicional externa al códec/coordinador.
