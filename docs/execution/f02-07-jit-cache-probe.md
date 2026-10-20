# F02.07 / LP-C — Caché y rechazo conservador de entrada JIT

Fecha: 2026-10-18. Fuente: SRC68. Contrato:
[JC01–JC07](../../schemas/jit-cache-probe-v1.md). Evidencia:
[metadatos públicos](../compatibility/jit-cache-probe-evidence.json).

## Resultado y decisión

La copia privada nueva añade cinco puntos de observación: entrada al JIT EE,
escritura lógica de caché, devolución física de línea, reset de caché e
instrucción CACHE. Retira los dos rechazos VTLB previos a delegar escrituras de
caché; la hoja común los sustituye sin duplicación. Tres archivos modificados;
guardia, puente y fuentes SRC65–SRC67 conservados.

**JIT EE continúa sin admitirse para continuidad.** Su entrada invalida con
`lost`, antes de reset pendiente y antes del código compilado; la ejecución
original continúa. Los generadores constantes/dinámicos/fastmem permanecen intactos.
No se implementó cobertura por store JIT ni equivalencia intérprete/JIT. Esta
decisión permite avanzar con los productores del intérprete y la caché mientras
la admisión de modos y el armado real permanecen cerrados.

La barrera no depende de cuándo se compiló un bloque, pero solo actúa al pasar
por `recExecute`. **No cubre una conexión creada dentro de un bloque ya activo.**
El harness demuestra esa brecha deliberadamente. Por tanto no se añade comando
de armado PINE/VM ni se acepta un sello de la guardia como continuidad real.
LG-I1 sigue parcial; LG-I2–I4, captura LP-D y validación física siguen pendientes.

## Inventario fijado

Proveedor: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. La evidencia fija hashes
de once archivos del inventario, además del manifiesto completo privado.

| Superficie | Resolución/efecto observado en fuente | Tratamiento en SRC68 |
|---|---|---|
| `recStore`, stores parciales y COP1 en `iR5900LoadStore.cpp` | Delegan stores a generadores constantes/dinámicos | Intactos; no acreditan avisos físicos |
| `DynGen_DirectWrite`, `vtlb_DynGenWrite` | Destino resuelto desde vmap o acceso directo fastmem; tamaños 8/16/32/64/128 | JIT rechazado al entrar; fallbacks y backpatch pendientes de ensayo real |
| `vtlb_DynGenWrite_Const` | Destino host incrustado o handler; supone invalidación de bloques al cambiar TLB | Sin instrumentación de emisión. No se acredita que una barrera de entrada cubra todos los modos |
| `recExecute` | Reset pendiente, `fastjmp_set`, `EnterRecompiledCode`, profiler | Rechazo dinámico previo, conservando orden y ejecución |
| `prepareCacheAccess<true>` | Búsqueda/expulsión de línea, dirty y posterior store de 1/2/4/8/16 bytes | Rechazo antes de todas esas acciones, tanto llamada directa como vía VTLB |
| `CacheLine::writeBackIfNeeded` | Asignación de 64 bytes a `tag.addr() | (set << 6)` si dirty, valid y PFN válido | Aviso físico antes del efecto; sin aviso si no escribe |
| Lecturas `prepareCacheAccess<false>` / `getFreeCache` | Hit/miss, elección de vía, posible devolución sucia y carga | Lectura ordinaria conservada; devolución observada aunque se origine en lectura |
| `CACHE`, `resetCache` | Datos/tags, invalidate, writeback, descarte; también operaciones sin efecto RAM | Rechazo conservador antes de cualquier rama o reset |
| `vtlb_memWrite`, `vtlb_memWrite128` | Delegación a caché cuando corresponde | Se retiran solo dos rechazos anteriores; la hoja emite uno lógico y el writeback puede emitir otro físico distinto |
| `vtlbUnmappedPWrite`, `vtlbUnmappedPWriteLg` | Accesos de caché sin PFN válido después de bus error | Cubiertos por la hoja de caché; el bus error completo no se ejecuta en el harness |
| `COP0`, `VMManager`, `Interpreter`, `SaveState` | Map/unmap con limpieza de bloques; cambio de CPU/reset de caches/fastmem; writeback al salir del intérprete; reset de caché al restaurar | Inventario estático. Época, sincronización y transición real de modo siguen pendientes |

`recCACHE` del JIT está vacío en este proveedor y `recSYSCALL` puede omitir
FlushCache; no se presume que el JIT tenga la semántica del intérprete para caché.
La presencia de limpieza de bloques en COP0/VMManager es evidencia estática, no
una prueba de que todas las transiciones posibles estén cubiertas por el observador.
IOP/VU, escritores host y otras rutas siguen sujetos al inventario completo LG-I1.

## Diseño y SOLID

La lógica de invalidación permanece en `LifetimeGuard`; el puente solo traduce
destinos resueltos o comunica pérdida de cobertura. Los productores PCSX2 no
conocen perfiles, archivos, transporte ni el catálogo. No se incorporan tipos
del emulador al núcleo portable ni al runtime Nintendo.

Los hooks se eliminan de los objetos OFF. Sin conexión son inertes. Un fallo de
observación conserva escrituras, datos, flags, profiler y retornos originales.
El mutex existente protege callbacks, no serializa el efecto de memoria posterior.
No se cambia configuración del usuario, ejecutable instalado ni generación JIT.

## Compilación y pruebas

Cinco unidades reales se compilaron ON/OFF: `Cache`, `vtlb`, `iR5900`, `recVTLB`
e `iR5900LoadStore`, con las opciones del proveedor: Apple Clang 21, x86_64,
C++20, ThinLTO y SDK explícito. Diez objetos aprobados. OFF no referencia los
hooks; los generadores intactos tampoco los referencian en ON. No se enlazó ni
ejecutó la aplicación PCSX2 completa.

El [fixture propio](../../tests/fixtures/pcsx2-jit-cache-probe/harness.cpp) incluye
cuatro fragmentos privados exactos: cuerpo completo de caché sin includes, dos
funciones VTLB y `recExecute`. Mapa, registros, logger, `fastjmp` y callback de
entrada compilada son dobles explícitos. Se usan el puente y la guardia reales.

**70 casos por modalidad**, aprobados en ON, OFF y ON con ASan/UBSan:

- Stores de 8/16/32/64/128 bits, escritura directa y vía VTLB, hit/miss, valor
  repetido, cambio y restauración, handler y PFN inválido.
- Devolución de línea: ocho combinaciones dirty/valid/PFN, mismo valor, restauración,
  destino ajeno, offset de set y conexión ausente. Se conserva la limpieza de dirty.
- Lecturas puras, expulsión de línea protegida, línea limpia, PFN inválido, alias
  del mismo destino y elección de vía desbloqueada.
- Doce códigos CACHE más miss y reset; flags, TagLo, datos, devolución y descarte.
- Entrada JIT con/sin reset, dos resultados simulados de `fastjmp`, reentrada,
  conexión ausente y bypass deliberado. El callback ya existe antes de conectar;
  **no es un bloque PS2 recompilado ni una prueba real de saltos no locales**.

Los wrappers verifican que el aviso lógico precede a modificar la caché. Se
comprueba el contenido anterior al writeback y los efectos finales. Las tres
modalidades producen el mismo resumen FNV-1a de 64 bits `d4f40ee1adc19caf`, junto
con oráculos de bytes, flags y registros; los artefactos se identifican con SHA-256.
No se presenta ese resumen como prueba exhaustiva de equivalencia del emulador.

Regresión aprobada: **67 CTest** en cada configuración Debug, Release y
ASan/UBSan, y **3.096 pruebas Python**, sin fallos ni omisiones. La cobertura
Python alcanza 5.303/5.348 líneas (**99,16 %**) y 1.449/1.482 ramas
(**97,77 %**); ambas superan el gate del 80 %. Ruff, formato (137 archivos),
control del repositorio y `git diff --check` pasan. No se repite cobertura C++:
el núcleo y el puente conservan los mismos bytes verificados en SRC66.

## Custodia y pipeline

Se conserva el baseline, observador anterior, VTLB, DMA y la nueva copia. El parche
es reversible y los inputs públicos fijados por SRC65–SRC67 se reverifican sin
modificarlos. Permanecen privados los cuerpos GPL-3.0+, parche y ejecutables
compuestos; el repositorio contiene requisitos, fixture propio y metadatos.

Las dos auditorías privadas son idénticas: **10.361 bytes**, SHA-256
`84452ac37e522d6e338dc9004ed35049845e309473ab613b62529c2e707eac35`.
Verifican las seis copias de fuentes (incluida la tentativa fallida), los inputs
históricos, fragmentos exactos, objetos, ejecutables, logs y recibos. La evidencia
pública fija además los hashes de scripts operativos y artefactos de regresión.

Se preservaron dos rechazos preparatorios: patrón inverso ambiguo al retirar un
aviso VTLB, detenido antes de compilar, y constantes sin uso del fixture bajo
`-Werror`. Se acotó el patrón en otra copia y se eliminaron las constantes; no se
rebajaron advertencias. Compilación/ensayo usan supervisión, 180/30 segundos,
suelo de 10 GiB y etapa máxima de 1 GiB, con cierre verificado de grupos.

Pipeline local: preparar copia → compilar diez unidades → extraer fragmentos
exactos → ejecutar tres modalidades → auditar dos veces → gates host/Python.
La CI pública mantiene los tests del núcleo y puente; este harness requiere
los fragmentos privados y no se ejecuta automáticamente allí. No se ejecutaron
CI remota, cobertura GCC, build 3DS ni una nueva sesión PCSX2.

## Estado y siguiente unidad

JC-T1–T4 describen este lote conservador. Las tareas amplias JC-2–JC-4 conservan
pendientes la cobertura de código generado, bloques reales previos al cambio,
admisión durante ejecución, equivalencia intérprete/JIT y coste en VM. No se
modifican esos criterios para declarar terminado el soporte JIT.

La siguiente unidad ejecutable es **LG-I1 / escritores host**:

1. Inventariar arranque/cargadores, parches, depurador, IPC y copias host hacia EE:
   función, destino, cantidad, condición, hilo y delegación a rutas ya cubiertas.
2. En nueva copia privada, insertar avisos antes del efecto o rechazo conservador
   para rutas no acreditadas. Evitar duplicar avisos al usar VTLB; conservar bytes,
   retornos y errores. No exponer armado.
3. Ejecutar cuerpos del proveedor con fixtures propios: normalidad, fallo antes
   de escribir, efecto parcial, destino ajeno, mismo valor y restauración. Exigir
   efectos equivalentes ON/OFF y sanitizadores aprobados.
4. Compilar unidades y repetir gates/custodia. Después, LG-I2 debe quiescer
   escritores, rechazar JIT activo y GS pendiente, fijar época no restaurable e
   invalidar antes de reset/load/remap/configuración; LG-I3–I4 enlazan extremos y VM.

F02.07/Q05/G02, procedencia real, semántica, dos salas y New Nintendo 2DS XL siguen
pendientes. LP-D conserva español/Normal/Normal y los presupuestos vigentes.
