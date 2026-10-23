# IR-T7 — Perfil intermedio de registros de colisión

2026-10-23. **IR-T7a–f completadas; perfil de registros cerrado.**
Perfil `ps2-collision-registry-v1`; convertidor
`captured-eu-collision-registry-intermediate-v1`.
[Evidencias y comprobante IR-T7a](../docs/execution/f03-04-collision-inventory.md).

La [investigación posterior CF-T1–T3](../docs/execution/f03-04-collision-shapes-research.md)
identifica formas y listas en fuentes privadas; no cambia este contrato ni
añade sus payloads a los paquetes IR-T7. El decoder de formas requiere un
perfil posterior, separado de estos registros observados.
Requisitos: RF02.04/RF02.05; preparación para RF05.01, sin satisfacerlo todavía.

**Historia:** Como implementador del port, quiero conservar y reconstruir los
registros de colisión observados para investigar su relación con actores y
escenario sin perder bytes ni confundir inscripción con respuesta física.

## Decisión y alcance

Se elige un perfil de **observación de registros en RAM** de la edición
europea, CRC `5088CCDB`. Se descarta por ahora definir un formato de polígonos
desde el sufijo `.cld`: hay candidatos, pero no un contrato de ese recurso
ni su enlace a estas listas demostrado. Tampoco se reutiliza la malla visual
como colisión. F03.04 global, F03.02, F06.05, SC-T3b/c y G02/G03 siguen abiertos.

La primera importación usa las 30 capturas fijadas por SC-T3b.1: 02,
08–35 y 36. Conserva dos registros distintos: personajes con propietario y
escenario con punteros. No incluye el contenido completo de las listas
apuntadas, superficies, volúmenes, resolución de movimiento, activadores
ni código ejecutable de callbacks. Su estado es `observed_registry`,
`capabilities=[]`; no eleva recursos del catálogo a `decoded` o `validated`.

## Requisitos EARS

- **IR19** WHEN importa una captura THEN el preparador SHALL verificar tamaño
  y SHA-256 del estado y recibo, versión PCSX2, CRC, PC/ciclo y enlaces con
  los informes fijados; SHALL conservar la procedencia completa del recibo.
- **IR20** WHEN importa registros THEN el decodificador SHALL validar ambos
  bancos, contadores, selectores y pertenencia de propietarios a la lista
  enlazada de actores de la misma captura; SHALL mantener separados los
  punteros de escenario y los propietarios de personajes.
- **IR21** WHEN serializa THEN el intermedio SHALL conservar los ocho rangos
  binarios definidos por captura, incluidos espacios inactivos y bytes
  opacos, y los documentos completos de referencia; SHALL preservar valores
  y tipos JSON sin reinterpretar palabras desconocidas como floats.
- **IR22** WHEN reconstruye desde el intermedio THEN el adaptador SHALL
  regenerar la observación de registros y los ocho rangos byte por byte sin
  leer ISO, estados, recibos externos ni abrir PCSX2; SHALL cotejar la vista
  derivada con los rangos, no confiar solo en JSON de resumen.
- **IR23** WHEN informa resultados THEN el sistema SHALL distinguir control
  02, segmento 08–35 y diagnóstico restaurado 36; SHALL limitar ausencia de
  propietario/eventos a esas muestras y mantener pendientes daño/muerte.
- **IR24** IF una versión, identidad, hash, tipo, límite, relación o política
  de fase no coincide THEN el sistema SHALL rechazar antes de publicar;
  IF la cola contiene eventos THEN v1 SHALL rechazar esa variante como no
  soportada, sin descartar entradas ni asignarles semántica inventada.
- **IR25** WHEN publica THEN el writer SHALL exigir directorio privado nuevo,
  inventario exacto, relectura de hashes y manifiesto final; SHALL evitar
  rutas del host en el intermedio y mantener intactas las fuentes.
- **IR26** WHEN valida la implementación THEN CI SHALL usar únicamente
  fixtures propios y exigir ≥80 % de líneas y ramas; la auditoría privada
  SHALL comparar dos conversiones de las mismas capturas, todos los rangos
  y referencias, sin presentar esa repetición como adquisiciones independientes.
- **IR27** IF se solicita exportar colisión jugable, dereferenciar listas,
  ejecutar callbacks o normalizar coordenadas desde este perfil THEN el
  consumidor SHALL rechazar la operación no soportada; una ampliación SHALL
  aportar contrato y evidencia nuevos, sin cambiar silenciosamente v1.

## Modelo lógico

Raíz exacta: `schema_version=1`, `profile`, `converter`,
`conventions`, `documents`, `provenance`, `captures`.

| Campo | Contenido y autoridad |
|---|---|
| `conventions` | Constantes versionadas: LE, palabras u16/u32, direcciones EE solo como procedencia, ambos bancos conservados, sin escala/ejes físicos, cola vacía, pointees de escenario excluidos, callbacks sin ejecución. |
| `documents` | `collision_reference`, `alternatives_reference`, `continuity_reference`: árboles completos de los tres informes fijados, incluidos límites y desconocidos. |
| `provenance` | `source_identity` (perfil europeo/CRC y hashes ELF/overlay), `source_reports` (tamaño/hash de los tres JSON originales), `inventory_sha256` (IR-T7a). No contiene rutas del host. |
| `captures` | Lista ordenada por slot, exactamente `[2,8,…,35,36]` para esta primera receta; sin duplicados ni mezcla de estados de otra sesión. |

Cada captura tiene campos exactos `slot`, `state`, `receipt_source`, `receipt`,
`phase`, `ranges`, `observations`. `state` y `receipt_source` conservan
`size/sha256`; `receipt` conserva íntegro el JSON fuente. `phase` admite
`control_puzzle`, `continuous_post_phase`, `restored_diagnostic` según slot.
`ranges` contiene ocho registros `file/address/size/sha256`, con nombres
permitidos `capture-NN-<nombre>` de la tabla siguiente. `observations` es la
vista derivada y debe reconstruirse al importar y al leer el intermedio.

La identidad de una observación de actor es `(state.sha256, address)`. Los
campos `kind/instance` son valores observados, no IDs globales persistentes.
Un entero con el mismo valor que un booleano no satisface el tipo requerido.
Los hashes históricos identifican bytes originales; el manifiesto de salida
protege el JSON recodificado, que conserva semántica/tipos y no su espaciado.

### Rangos privados conservados

Todos se leen de `eeMemory.bin`, exactamente 32 MiB, sin extraer el ZIP al disco.
Los rangos son una selección de observación, no el formato de un recurso CLD.

| Nombre por captura | Dirección EE | Bytes | Alcance |
|---|---|---:|---|
| `character.bin` | `0x01D05FE0` | `0x480C` = 18.444 | Dos bancos de 32 × `0x120`, dos contadores u32 y selector u32. |
| `world.bin` | `0x01D04560` | `0x8C` = 140 | Dos bancos de `0x44`: contador u32 y hasta 16 punteros; selector al final. |
| `events.bin` | `0x01D000F0` | `0x2000` = 8.192 | Almacenamiento de 128 registros de `0x40`, preservado opaco incluso con cola vacía. |
| `event-count.bin` | `0x01D02130` | 4 | Contador; v1 requiere cero. El hueco anterior no está incluido. |
| `actors.bin` | `0x004481D0` | `0x6400` = 25.600 | Pool de 32 × `0x320`, incluidos slots no activos, conservados opacos. |
| `actor-head.bin` | `0x0044E5D4` | 4 | Cabeza de la lista enlazada; no apunta a una dirección del host. |
| `stage.bin` | `0x01CFB851` | 1 | Selector de etapa observado `0x23`. |
| `room.bin` | `0x01CB5770` | 4 | Sala `0xEA` para 02, `0xEB` para 08–36. |

Total **52.389 bytes por captura**, **1.571.670 bytes para 30**. Estos tamaños
se comprobaron en memoria en IR-T7d/e y en los dos paquetes privados de
IR-T7f, con reconstrucción idéntica desde cada paquete sin leer las fuentes.
Los bytes no incluidos del estado, código, modelos y listas apuntadas no se
declaran reconstruibles. Tampoco se reconstruye un savestate o CLD original.

### Vista derivada y reglas

`observations` contiene `stage`, `room`, `actors`, `character`, `world`,
`events`. La lista `actors` recorre desde `actor-head`: valida límites,
alineación relativa al pool, enlace anterior (`+0xB8`), siguiente (`+0xBC`),
ausencia de ciclos y máximo 32. Expone por actor `address`, `status` u32 en
`+4`, `kind/instance` u16 en `+0xC/+0xE` y `function` u32 en `+0xA0`.
El resto de los `0x320` bytes permanece opaco en el adjunto.

`character` contiene `selector`, `counts[2]`, `banks[2]`. Cada fila activa
expone `index`, `record`, `owner`, `kind`, `instance`, `presence_words[2]`
u16 en `+0x110/+0x112` y `callback` u32 en `+0x11C`. `owner` se lee de
`+0x60` y debe resolver a un actor activo de esa captura. Los conteos están
en `0x01D0A7E0/+4`, selector en `+8`; conteos 0..32, selector 0 o 1.
No se fusionan entradas del mismo propietario: el control tiene dos por caballo.
Las palabras de presencia no se convierten a bool ni se definen tipos de forma.

`world` contiene `selector`, `counts[2]`, `banks[2]` de punteros u32 ordenados.
Conteos 0..16, selector 0 o 1; las entradas activas deben estar en el rango EE
acotado por la auditoría (puntero positivo y `puntero+0x50 ≤32 MiB`). No se
siguen al reconstruir. Los 80 bytes de inspección histórica no demuestran la
longitud de una lista, un polígono o una forma; no se añaden como geometría.
Las entradas inactivas de ambos registros se conservan, pero no se interpretan.

`events` contiene `count=0`, `entries=[]`. Conservar `events.bin` completo no
significa que todos sus registros estén activos. La cola vacía en un punto no
prueba ausencia de eventos entre puntos ni resuelve la semántica de impactos.

La comprobación de fase compara esta vista con las filas equivalentes del
informe SC: 23 entradas de personajes y una lista de escenario por banco en
02; dos entradas de personajes y doce listas de escenario por banco en 08–36.
El control `0x020C` y el actor `0x0209` permanecen separados. Los detalles de
IA, flags y clips de los informes se conservan como evidencia histórica;
no se recomputan desde estos ocho rangos ni se atribuyen al decoder de registros.
El selector se conserva literalmente; no se asume que seleccione el banco de
lectura de todas las consultas, pues la ruta de impacto revisada usa el opuesto.

## Arquitectura SOLID e interfaces

1. `collision_registry`: decoder puro sobre rangos de bytes, límites e
   identidades de captura. Devuelve una observación o error tipado; sin rutas,
   acceso a PCSX2, lógica de daño, renderizador ni `assert` como validación.
2. `collision_intermediate`: codec/validador del perfil, vinculación de referencias
   y reconstrucción. Reutiliza `intermediate_json` e `intermediate_assets`;
   recibe todos los bytes, sin I/O oculto ni dependencia de scripts `build/`.
3. `prepare_collision_intermediate`: adaptador de I/O, verificación de entradas
   fijadas, lectura acotada de estados/recibos y publicación. Reutiliza
   `read_state_members`/`decode_ee_state` y el writer privado; no copia la lógica
   del auditor local con rutas constantes al dominio.
4. El renderer y el futuro solver de colisión son consumidores distintos.
   Este perfil no expone una interfaz de respuesta física ni crea callbacks
   ejecutables. Un perfil posterior de formas deberá tener contrato propio.

Interfaces implementadas: `decode_registry(ranges) -> observations`,
`make_collision(documents, provenance, captures, blobs) -> files` y
`export_collision(intermediate_bytes, blobs) -> files`. Las funciones puras
no alteran entradas. La vista y los adjuntos se vuelven a validar en cada
exportación.

### Contrato del decoder IR-T7c

`tools.pipeline.collision_registry.decode_registry(ranges)` recibe un `dict`
con exactamente los ocho nombres de rango de la tabla y valores de tipo
`bytes` de longitud exacta. No acepta buffers mutables ni conversiones
implícitas. Devuelve un árbol JSON nuevo con los seis campos de observación;
los ocho buffers de entrada se mantienen intactos y son responsabilidad del
adaptador IR-T7d al serializar. La vista derivada no sustituye esos buffers.
`REGISTRY_RANGES` expone direcciones/tamaños mediante un mapping inmutable.

El decoder valida etapa `0x23` y sala `0xEA/0xEB`, pero no infiere slots,
fase o identidad del juego desde ellas. Los conteos estructurales pueden ser
cero o alcanzar la capacidad; la comprobación de fase 23/2/12 del corpus
pertenece al adaptador. Un pool vacío requiere cabeza cero; puede contener
bytes residuales en slots inactivos. Direcciones únicas, alineadas dentro de
32 slots y sin ciclos acotan el recorrido a 32 actores. Función/callback y
palabras de presencia se conservan como u32/u16, sin imponer enum inventado.

Errores estables: `CollisionRegistryError(ValueError)` con atributo `code`
y mensaje igual al código, sin volcar datos originales:

| Código | Rechazo |
|---|---|
| `CR_RANGES` | Tipo de contenedor, nombres, inventario extra/incompleto. |
| `CR_RANGE_TYPE`, `CR_RANGE_SIZE` | Valor distinto de bytes o longitud incorrecta. |
| `CR_STAGE`, `CR_ROOM` | Contexto fuera del alcance estructural del perfil. |
| `CR_ACTOR_ADDRESS`, `CR_ACTOR_CYCLE`, `CR_ACTOR_PREVIOUS` | Enlace fuera del pool/desalineado, ciclo o enlace anterior inconsistente. |
| `CR_CHARACTER_COUNT`, `CR_CHARACTER_SELECTOR`, `CR_CHARACTER_OWNER` | Capacidad, selector o propietario no activo. |
| `CR_WORLD_COUNT`, `CR_WORLD_SELECTOR`, `CR_WORLD_POINTER` | Capacidad, selector o puntero fuera del rango acotado. |
| `CR_EVENT_COUNT` | Contador mayor que 128. |
| `CR_EVENTS_UNSUPPORTED` | Contador entre 1 y 128: variante no soportada en v1. |

La validación usa condiciones explícitas que siguen activas con Python `-O`.
El decoder no lee metadatos JSON aportados como observaciones; validarlos,
verificar hashes y preservar fases/documentos corresponde a IR-T7d.

Salida: `intermediate.json`, `collision-observations.json` y los
240 adjuntos, **242 archivos más manifiesto**. La segunda vista es derivada,
no sustituye al conjunto completo. Writer con inventario dinámico calculado
desde slots permitidos, nunca nombres arbitrarios aportados por el usuario.

### I/O y límites

Contrato concreto IR-T7d: la configuración tiene claves exactas `reports`,
`inventory`, `captures`. `reports` contiene `collision`, `alternatives`,
`continuity`; cada entrada y `inventory` tiene `path/size/sha256`.
Cada captura de configuración contiene `slot/state/receipt`, con dos entradas
del mismo tipo. Los pins se cotejan con el inventario IR-T7a antes de leer RAM.
El inventario también tiene un límite de 1 MiB. No se fija un hash del corpus
en el código: la configuración fija la evidencia y permite fixtures propios.

`source_identity` contiene exactamente `profile_id`, `crc`, `elf_sha256`,
`overlay_sha256`, fijados a la edición europea inventariada. `source_reports`
usa las tres claves anteriores con `size/sha256` originales. Los árboles JSON
completos se preservan; sus campos relacionados se comparan con tipos exactos
mediante JSON canónico. No se recalcula el hash original desde su recodificación.
Los manifiestos protegen esa representación nueva. Los metadatos no admiten
valores de ruta absoluta POSIX/Windows o URI `file:`; las rutas de entrada nunca
se copian a la salida. Los nombres relativos históricos permanecen opacos.

Las comprobaciones enlazan CRC/PID, PC/ciclo/GPR/delay del recibo con el estado,
el hash del estado con todos los informes que lo citan, y los rangos con el
inventario. Validan fase, conteos y propietarios por banco, actores objetivo,
inscripción de los tres actores en las listas de escenario del informe y el
actor del segmento continuo. Los ciclos de 08–35 deben crecer estrictamente;
36 queda fuera de esa prueba. Flags, IA, clips y geometría apuntada se conservan
como evidencia histórica, sin reinterpretarlos ni volver a verificarlos en RAM.

Las APIs puras rechazan con `ValueError` (incluidos errores del decoder); el
CLI devuelve código 1 y solo tipo de error, sin bytes ni rutas privadas.
El informe del paquete incluye `state=observed_registry` y las limitaciones
de ejecución/física descritas debajo. No ofrece operaciones de solver.

CLI: `--inputs`, `--private-root`, `--run-id`. Configuración ≤32 KiB:
tres entradas de informe `path/size/sha256`, inventario IR-T7a
`path/size/sha256` y 30 pares de estado/recibo fijados, ordenados por slot.
Las rutas absolutas quedan solo en configuración local. El preparador debe
comprobar sus pins contra inventario, informes y recibos, no autocertificar
las fuentes calculando y aceptando hashes nuevos al importar.

Presupuestos: informe ≤1 MiB cada uno; recibo ≤16 KiB; ZIP ≤64 MiB, miembros
de versión 36 bytes, internals ≤4 MiB, RAM exactamente 32 MiB. Reutilizar
las comprobaciones existentes de versión, duplicados ZIP, tamaños y tipos.
Procesar un estado a la vez; no retener treinta RAM de 32 MiB.
JSON intermedio y vista ≤8 MiB cada uno, profundidad 32, 500.000 nodos y
límites de strings/enteros del codec IR; salida total ≤40 MiB.
Rechazar symlinks en archivos, rutas inesperadas, estados truncados y cambios
durante lectura. Publicar únicamente tras validar y verificar la reconstrucción.

El manifiesto debe declarar `new_vm_execution=false`,
`original_state_rebuild=false`, `world_pointees_included=false`,
`collision_response_verified=false`, `damage_transitions_verified=false`,
`capabilities=[]`. Un resultado negativo no se convierte en fidelidad implementada.

## Plan de pruebas e incorporación

### Criterios de cierre IR-T7e

1. **IR22/IR26:** WHEN se verifica un paquete sintético THEN un oráculo de
   pruebas SHALL releer offsets LE y todos los bloques desde las fuentes sin
   importar constantes, decoder, codec ni exportador de producción. Comparará
   los 240 adjuntos completos, documentos/recibos con tipos exactos, CPU del
   estado y vista derivada. Su modo sin fuentes comprobará ambas vistas y
   adjuntos, sin afirmar que autentica los hashes históricos por sí solo.
2. **IR21/IR24:** IF se introduce un fallo deliberado compartido por importador
   y exportador THEN el oráculo SHALL detectarlo; se incluyen cambio de actor
   no objetivo, eliminación de bytes opacos y pérdida de metadatos desconocidos.
   Se comprobarán también truncamientos, ZIP/JSON inválidos, límites de entrada
   y cambio de contenido tras fijar los hashes, antes de publicar.
3. **IR25:** IF fallan escritura, fsync, relectura, inventario, identidad del
   directorio o enlace final THEN el writer SHALL propagar el rechazo y no
   crear `manifest.json`. Puede conservar residuos privados de diagnóstico;
   reusar el mismo `run-id` SHALL fallar. Dos publicaciones concurrentes con
   el mismo ID SHALL producir exactamente una entrega, sin sobrescritura.
4. **IR26:** WHEN CI ejecuta el perfil THEN SHALL exigir ≥80 % de líneas y
   ramas para sus cuatro módulos, además del gate global. El verificador
   independiente deberá formar parte del lint; sus pruebas solo usarán datos
   propios. Se registrarán resultados locales sin atribuir ejecución remota.

El oráculo es código de pruebas, con `int.from_bytes`, ZIP/JSON de la biblioteca
estándar y tabla propia derivada de este contrato. No añade otro decodificador
al runtime. El cotejo contra fuentes recibe un lector inyectado y procesa un
estado por vez, para poder reutilizarlo en la auditoría privada IR-T7f.

Fixtures propios: lista de actores mínima/máxima; dos bancos con contenidos
distintos; dos filas por propietario; presencias 0 y no cero; punteros de
escenario repetidos/ordenados sin asociarlos a actores; bytes inactivos con
patrones no nulos; cola vacía con bytes residuales; round-trip exacto y campos
desconocidos, cero negativo solo en metadatos JSON, reconstrucción sin fuentes.

Negativos: contador 33/17/129, selector 2, cola no vacía, enlace fuera de pool
o desalineado, ciclo/enlace anterior inconsistente, propietario no activo,
booleanos como enteros, puntero fuera de RAM, hash/tamaño inválido, captura
duplicada/ausente, mezcla de CRC/PC/ciclo/fase, diagnóstico etiquetado continuo,
contradicción con informe, bytes cambiados, rutas/symlinks y salida existente.

| Tarea | Requisitos | Trabajo y criterio de cierre |
|---|---|---|
| **IR-T7a — completada** | IR19/IR20/IR23 | Inventariar fuentes, releer 30 estados y recibos, comparar registros, código y hashes; registrar candidatos `.cld` como indicios. Informe y límites enlazados. |
| **IR-T7b — completada** | IR19–IR27 | Fijar perfil, ocho rangos, vista, procedencia, interfaces, presupuestos, errores y pruebas en este contrato. |
| **IR-T7c — completada** | IR20/IR21/IR24 | Decoder puro `collision_registry`, 100 tests sintéticos y cobertura de líneas/ramas 100 %. Bancos, lista de actores, datos opacos y errores tipados, también bajo `-O`. [Ejecución](../docs/execution/f03-04-collision-registry.md). |
| **IR-T7d — completada** | IR19/IR21–IR25/IR27 | Adaptador puro, preparador, CLI y writer exclusivo. Referencias/recibos íntegros, 240 bloques y reconstrucción de 242 archivos. 30 capturas reales cotejadas en memoria; 206 tests del perfil y 462 de regresión. [Ejecución](../docs/execution/f03-04-collision-intermediate.md). |
| **IR-T7e — completada** | IR22/IR24–IR26 | Oráculo stdlib independiente, 257 pruebas del perfil, fallos de publicación y exclusión concurrente. Gate ≥80 % por cada módulo en CI; cotejo independiente de las 30 capturas en memoria. [Ejecución](../docs/execution/f03-04-collision-verification.md). |
| **IR-T7f — completada** | IR19/IR22/IR23/IR26 | Dos conversiones privadas publicadas; 242 archivos y manifiestos A/B iguales byte por byte, cotejados con fuentes por el oráculo. Reconstrucción desde ambos paquetes en procesos con acceso externo bloqueado durante el cálculo. Son las mismas capturas, sin nueva ejecución de VM. [Ejecución](../docs/execution/f03-04-collision-publication.md). |

**Investigación posterior de formas:** seleccionar candidatos por evidencia
primaria del cargador/consumidor, verificar relación con sala y listas,
identificar registros/terminación/variantes, transformar con evidencia y crear
fixtures antes de un decoder. Una comprobación de navegación/colisión y otra
de activadores pertenecen a tareas posteriores; la de daño sigue SC-T3b/c.
No bloquean implementar el perfil de registros definido aquí.
