# F02.07 / LP-C — Ciclo de vida y época host

Fecha: 2026-10-18. Fuente: SRC70. Contrato [LC01–LC08](../../schemas/lifecycle-probe-v1.md).
Evidencia: [metadatos públicos](../compatibility/lifecycle-probe-evidence.json).

## Resultado y alcance

El puente incorpora causas tipadas de reset, restauración, remapeo, configuración
y cierre, y un contador **HostEpoch** independiente de la VM. Hay **24 puntos
nuevos** en cinco unidades PCSX2. La época avanza antes de notificar, incluso sin
conexión; no existe API de reset ni se incorpora a los save states. Al agotar u64
queda en cero permanentemente. Un proceso nuevo exige una sesión nueva.

`before_lifecycle` usa el mismo mutex que los avisos de escritura y la conexión
RAII. El núcleo LifetimeGuard permanece igual y conserva la primera causa de
fallo. Tipos ajenos al ciclo de vida se convierten en pérdida de cobertura, nunca
en checkpoint o cierre aceptado. Un ciclo emulado regresivo también falla; no
retrocede la época host. Un intervalo ya sellado sigue siendo inmutable.

**No se admite captura real.** La época todavía no está vinculada al protocolo
de armado/extremos y el bloqueo serializa avisos, no los efectos del emulador.
Exclusión de PINE/GS/CPU/escritores opcionales, cobertura exhaustiva y VM completa
siguen pendientes. LC-T1–T4 cierran este lote de funciones; LG-I2 no se declara completo.

## Inventario de fronteras

Proveedor: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`; catorce archivos de
inventario fijados, además del manifiesto completo. La posición se verificó en
código. La afinidad y exclusión real de hilos no se acreditan por esa inspección.

| Frontera | Puntos | Posición y tratamiento |
|---|---:|---|
| SysMemory Allocate/Release; memAllocate/Reset/Release | 5 | Antes de asignar/liberar ancla, iniciar reserva o reset. Una reserva fallida puede invalidar conservadoramente |
| `cpuReset` | 1 | Antes de borrar registros/ciclo/TLB; conserva la ejecución original |
| `PreLoadPrep` | 1 | Antes de esperar VU/GS, respaldar TLB, cambiar protección y limpiar caches |
| MapHandler/MapBlock/Mirror | 3 | Antes de cambiar tablas físicas; conserva verificaciones y bucles |
| VMap/VMapBuffer/VMapUnmap | 3 | Antes de fastmem y mapas virtuales; incluye remapeos de buffers |
| VTLB Init/Reset/Shutdown/ResetFastmem/Core_Free | 5 | Antes de limpiar tablas, mappings, datos de backpatch o anclas |
| ApplySettings/ApplyCoreSettings | 2 | Antes de sincronizar/mover configuración; reaplicar lo mismo también invalida |
| VMManager Shutdown | 1 | Antes de marcar Stopping y de guardar/cerrar/liberar subsistemas |
| VMManager Reset | 2 | Antes de diferir a Resetting; en pausa, después de confirmar y antes de efectos. Cancelación previa conserva observación |
| Execute, cambio de implementación CPU | 1 | Después de consumir el flag de cambio y antes de sustituir CPU/limpiar caches/fastmem. Ejecutar sin cambio no añade aviso |

En SaveState_UnzipFromDisk, abrir/verificar versión/comprobar componentes precede
a PreLoadPrep. Fallar allí no inicia la transición observada. Superada esa fase,
fallar al cargar estructuras o componentes puede dejar datos parciales y causar
un reset de recuperación: la guardia permanece inválida con su primera causa.
Las funciones internas de deserialización fuera de este flujo y otros modos
requieren auditar su alcanzabilidad antes de admisión.

Las fronteras pueden anidarse: un reset llama a otras rutinas instrumentadas.
La época identifica cambios observados, no cuenta operaciones del usuario.
La captura debe rechazar un cero por agotamiento y verificar la época dentro de
una sección que excluya escritores; leer `host_epoch()` por sí solo no basta.

## Diseño, evolución y SOLID

HostEpoch administra identidad con almacenamiento constante y sin archivos ni
tipos del emulador. PhysicalWrites transforma causas y comparte la conexión;
LifetimeGuard decide la invalidez. La lectura atómica relajada del contador no
publica memoria de la VM ni constituye una barrera de sincronización de efectos.
El núcleo no se enlaza al runtime Nintendo.

Para evolucionar el puente se guardaron snapshots anteriores de CMakeLists.txt,
physical_writes.cpp y su cabecera. La auditoría comprueba las evidencias históricas
contra esas versiones cuando corresponde y contra los archivos actuales para
los demás inputs. El snapshot histórico de CMake de SRC65 también se conserva.
No se cambian hashes históricos para atribuirles el nuevo código.

La copia privada nueva recibe los archivos propios actualizados y agrega
host_epoch.cpp a su lista CMake. Las copias privadas anteriores permanecen
intactas. Este ajuste de lista se inspecciona; no se ejecuta una nueva configuración
ni se enlaza la aplicación PCSX2 completa.

## Verificación

Las cinco unidades reales Memory, SaveState, vtlb, VMManager y R5900 compilan
en ON/OFF: **diez objetos** con Apple Clang 21, x86_64, C++20, ThinLTO y SDK
explícito. OFF no referencia callbacks de observación.

El [harness](../../tests/fixtures/pcsx2-lifecycle-probe/README.md) utiliza
21 fragmentos exactos y **54 escenarios** en ON/OFF/ASan-UBSan y funciones de
la copia anterior con OFF. Los cuatro modos conservan bytes, retornos, estado,
orden de llamadas y efectos controlados; resumen FNV-1a `499577d87d4e9261`.
El resumen acompaña oráculos y hashes SHA-256; no acredita equivalencia exhaustiva.

Se ejecutan 20 de los 24 hooks nuevos. **memReset, cpuReset, vtlb_Init y
VMManager::Shutdown solo se compilan**; dos son dependencias simuladas del harness.
Mapas/fastmem, ZIP, carga interna, trabajos, configuración y subsistemas también
usan dobles explícitos. No se ejecutan estados reales, sockets, hilos del proveedor,
JIT generado ni efectos concurrentes de una VM.

Las ocho pruebas portables nuevas incluyen agotamiento, unicidad concurrente de
épocas, serialización compartida de avisos, ausencia de conexión, causas inválidas,
terminales y retroceso de ciclo. La medición LLVM combina esas pruebas y las del
puente físico: **100 % de líneas y ramas** en host_epoch.cpp y physical_writes.cpp;
sus dos cabeceras tienen 100 % de líneas y ninguna rama. Este dato se limita a
estos cuatro archivos, no a PCSX2 completo. El gate permanece en 80 %.

La regresión aprueba **75 pruebas C++ por configuración** (Debug, Release y
ASan/UBSan) y **3.096 pruebas Python**, sin fallos ni omisiones. Python cubre
5.303/5.348 líneas (99,16 %) y 1.449/1.482 ramas (97,77 %); el gate separado
de líneas y ramas pasa sin reducir umbrales. Ruff, formato de los 137 archivos
del alcance CI, comprobación del repositorio y `git diff --check` pasan.

Las dos auditorías producen recibos idénticos de **28.409 bytes**, SHA-256
`4daae92d75ee0fc172bb26747078d1f8e296a2fd51c780b4d256be68f6257546`.
Comprueban inventarios, snapshots históricos, fuentes propias, parche, objetos,
fragmentos, ejecutables, logs y recibos de procesos supervisados.

CI pública: la nueva suite se integra en los presets host y el gate de cobertura
existente; no requiere originales. Harness privado, CI remota, GCC de CI, enlace
completo, captura real y prueba física New Nintendo 2DS XL quedan separados.

## Siguiente tarea: admisión y exclusión de escritores

1. Fijar perfil permitido y rechazar variantes no cubiertas: JIT activo, GS/VU
   pendiente, RDebug, RAIntegration y otros escritores no inventariados. El perfil
   debe incluir el estado real del proveedor, no una declaración del cliente.
2. Definir una sección de exclusión que cubra efectos: CPU, cola GS/VU y PINE.
   Verificar orden de bloqueos, cancelación y cierre sin deadlocks. Un mutex de
   callbacks o el flag Paused no sustituye esa comprobación.
3. Dentro de esa sección, crear conexión y guardia con sesión/época/ancla actuales;
   comprobarlas al adquirir extremos y al cerrar. Rechazar cambios, agotamiento,
   carreras de armado y restablecimiento. No exponer armado antes de los ensayos.
4. Ensayar transiciones/races y funciones pendientes, repetir compilación/custodia,
   y después integrar transporte/extremos y enlace/ejecución completos en LG-I3–I4.

F02.07/Q05/G02, procedencia y semántica reales, dos salas y LP-D siguen pendientes.
