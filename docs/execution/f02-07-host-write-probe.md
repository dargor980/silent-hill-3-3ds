# F02.07 / LP-C — Productores host

Fecha: 2026-10-18. Fuente: SRC69. Contrato [HW01–HW08](../../schemas/host-write-probe-v1.md).
Evidencia: [metadatos públicos](../compatibility/host-write-probe-evidence.json).

## Resultado

La nueva copia privada incorpora **nueve puntos de observación en cuatro archivos**:
seis escrituras directas de argumentos/nombre de arranque, una palabra de estado
Deci2 HLE, el callback opcional RAIntegration y el rechazo conservador de la
descarga de una tabla auxiliar TLB. No se alteran guardia, puente, emisores JIT,
transporte ni fuentes históricas. Los destinos directos se resuelven una sola vez
y las cadenas incluyen su terminador en el tamaño notificado.

Depurador, PINE y parches ya delegan a hojas VTLB instrumentadas. Se conserva esa
delegación sin duplicar avisos. Los casos prueban también una escritura parcial
que devuelve fallo: los bytes ya escritos se observan y no se deshacen. Las
operaciones idempotentes sin escritura no generan avisos; una asignación real del
mismo valor sí invalida cuando toca un rango protegido.

**LG-I1 sigue parcial y ningún modo queda admitido para captura.** Reset/load,
remapeos generales, escritores opcionales y serialización global siguen pendientes.
PINE escribe desde su hilo servidor; el mutex del puente no protege el efecto
posterior ni transforma el acceso a la guardia en una operación concurrente segura.

## Inventario y decisión

Proveedor fijado: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Veinte archivos del
inventario se identifican por hash, además del manifiesto completo privado.
Los contextos de hilo siguientes proceden del código, no de trazas de una VM.

| Superficie | Destino, longitud y condición | Contexto y tratamiento |
|---|---|---|
| `ParseArgumentString` | Byte de cada separador encontrado, hasta el límite original de argumentos | Llamada de arranque CPU; aviso físico por efecto. Null, vacío y texto sin espacios no escriben |
| `eeloadHook` | Separadores, argumentos y nombre de ejecutable, con NUL en copias | Intérprete/recompilador CPU; tres puntos directos. Punteros de argumentos conservan delegación VTLB |
| `eeloadHook2` | Separador y argumentos con NUL, si hay argumentos y ubicación conocida | CPU; dos puntos directos, parser y tabla de punteros originales conservados |
| `__Deci2Call` | Cuatro bytes de estado al completar reqsend con estructura presente | HLE de instrucción CPU; aviso antes de asignar. Lecturas/logs no crean escrituras |
| `RACallbackWriteMemory` | Un byte en Main o Scratch si pasa límite de 64 bits | RAIntegration opcional; aviso físico, memoria ajena a Main ignorada por el puente. Afinidad no acreditada |
| `GoemonUnloadTlb` | Remapeo y cuatro campos de cada entrada válida con clave coincidente | Auxiliar CPU dependiente de configuración; `lost` antes del primer unmap, aunque el efecto esté fuera de rangos protegidos |
| `R5900DebugInterface::Write*` | Tamaños 1/2/4/8/16 y bloques; validación escalar y copia por páginas | MemoryView agenda en CPU; hoja `vtlb_memSafeWriteBytes` ya cubierta, sin hook nuevo |
| PINE `MsgWrite8/16/32/64` | Hoja `vtlb_ramWrite`; handler rechazado, mapa resuelto | Hilo servidor; no hay nuevo hook. Socket/parser/concurrencia real no probados |
| Parches regulares, extendidos y reemplazos dinámicos | EEMemoryInterface/MemoryInterface → memWrite o safeWrite; igualdad puede suprimir el efecto | Aplicación por CPU en el flujo normal; hojas existentes. El memcpy de carga de bytes de Patch es almacenamiento del parche, no RAM EE |
| `ElfObject` | Lectura del archivo y metadatos locales | No se encontró copia hacia EE en sus rutinas de encabezados; no se presume que toda carga del juego pase por ellas |
| `memReset`, `memRelease` | Cero de eeMem y desaparición del ancla | Ciclo de vida pendiente: invalidar antes de reset/remapeos/liberación, no solo antes del memset final |
| `PreLoadPrep`, `FreezeMem`, `MemorySavestateEntry` | Estructuras y carga directa desde ZIP, potencialmente parcial | Ciclo de vida pendiente; observar copia no sustituye invalidar época antes de restaurar |
| `RDebug/deci2_dbgp.cpp` | Copias directas y argumentos de arranque | Fuentes enumeradas, sin unidad en compile_commands del build fijado. No instrumentadas ni admitidas |

RAIntegration está condicionado por `ENABLE_RAINTEGRATION`, ausente en los
comandos macOS verificados. Su cuerpo se ejecuta en el harness aislado, pero el
build de esa rama con Windows y sus dependencias permanece sin verificar.
El rechazo de descarga de tabla TLB tampoco sustituye cubrir los demás remapeos.

## Diseño y SOLID

Se mantienen responsabilidades separadas: la guardia valida continuidad, el
puente transforma destinos y los productores avisan antes del efecto. Los
productores no conocen perfiles, archivos ni transporte. La conexión RAII y el
núcleo portable permanecen iguales. OFF elimina las llamadas del observador;
sin conexión las operaciones originales se conservan.

Un fallo de observación nunca cancela la operación del emulador. Los tests
comprueban que continúan escrituras posteriores, datos, argumentos y retornos.
La nueva instrumentación no modifica los límites originales de las rutinas de
cadenas ni acredita seguridad de cualquier argumento o mapa posible del proveedor.

## Compilación y ensayos

**16 objetos reales** aprobados: R5900, R5900OpcodeImpl, Achievements, vtlb,
DebugInterface, Memory, Patch y PINE en ON/OFF, con los comandos del build fijado
(Apple Clang 21, x86_64, C++20, ThinLTO y SDK explícito). OFF no referencia avisos.
Los consumidores que ya delegaban siguen sin referenciarlos directamente.
Achievements macOS no compila la rama opcional RAIntegration.

El [fixture propio](../../tests/fixtures/pcsx2-host-probe/README.md) utiliza
**14 fragmentos exactos privados**, incluidos el layout real de tabla y wrappers
del depurador e idempotencia. Se ejecutan **85 escenarios por modalidad**:

- Siete del parser de argumentos, cinco del segundo hook y ocho del primero.
- Quince de Deci2, siete del callback RAIntegration y cuatro de descarga TLB.
- Treinta de tamaños/alias/destino ajeno/rechazo en depurador y hoja RAM, más
  nueve de bloques, cruce de página, fallo parcial e idempotencia.

ON, OFF, ON con ASan/UBSan y la copia anterior con OFF pasan. Las cuatro producen
el resumen FNV-1a `aabd6f87f29e497c`; también se comprueban bytes, retornos,
registros, mapas y avisos anteriores al efecto. El resumen facilita comparar
estos escenarios; no es una prueba exhaustiva de equivalencia del emulador.

Los dobles de VMManager, disco, mapa, logger y entrada DMA están declarados en el
fixture. No se ejecutan parser/socket PINE, aplicación PCSX2 completa, bloques PS2
generados ni consola. La rama extra-memory del arranque continúa haciendo sus
remapeos sin un aviso de época; el test conserva explícitamente esa limitación.

## Custodia y pipeline

Se verifican las copias baseline, observador, VTLB, DMA, JIT/caché y la nueva copia
host, junto con los inputs públicos históricos. Parche y fragmentos del proveedor
permanecen privados. El repositorio contiene requisitos, datos propios y metadatos.

Las dos auditorías son idénticas: **22.928 bytes**, SHA-256
`8335ee0608fa01c93522160e5c15f0beb5ccf45ddf66722bad195d41fab459c6`.
Verifican manifiestos completos, parche, inputs históricos, fragmentos de ambas
copias, objetos, binarios, logs, recibos y símbolos. La evidencia final fija
también los scripts operativos y artefactos de regresión mediante SHA-256.

Preparación reversible → dieciséis compilaciones → extracción exacta → cuatro
modalidades → dos auditorías → regresión host/Python. Se mantienen supervisión,
suelo de 10 GiB, etapa máxima de 1 GiB, límites de 180 s de compilación y 30 s
por harness y cierre verificado de grupos. No hubo fallos de compilación ni del
harness. La primera regresión Python detectó el enlace a la evidencia pública
antes de terminar de generarla: se conserva ese resultado y se repite la
regresión después de completar el archivo. La CI pública no ejecuta estos
fragmentos privados.

La regresión final aprueba **67 CTest por configuración** (Debug, Release y
ASan/UBSan) y **3.096 pruebas Python**, sin fallos ni omisiones. Cobertura Python:
5.303/5.348 líneas (**99,16 %**) y 1.449/1.482 ramas (**97,77 %**), superando el
gate del 80 %. Ruff, formato (137 archivos), verificación del repositorio y
`git diff --check` pasan. El resultado inicial con un enlace pendiente se conserva
por separado de esta ejecución final.

No se ejecutan CI remota, nueva cobertura C++ (núcleo/puente sin cambios),
configure/enlace completo del proveedor, build 3DS ni sesión nueva de PCSX2.

## Siguiente unidad

HW-T1–T4 cubren este lote. Las tareas amplias HW-1–HW-4 mantienen pendiente el
inventario exhaustivo y la exclusión verificable de escritores/configuraciones
no cubiertos. No se habilita armado por haber cerrado los tests de funciones.

La siguiente unidad es **LG-I2 / ciclo de vida**: inventariar reset/restauración,
remapeo/cambio de modo y shutdown; invalidar antes del primer efecto; mantener
época host no restaurable; probar éxito, fallo parcial y memoria final idéntica.
La admisión exige después demostrar CPU y trabajos detenidos, ausencia de JIT
activo/GS pendiente, exclusión del hilo PINE y resto de escritores, y vincular
extremos/transporte en LG-I3–I4. F02.07/Q05/G02 y captura LP-D siguen abiertos.
