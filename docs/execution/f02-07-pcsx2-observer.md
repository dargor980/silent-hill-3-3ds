# F02.07 — Contrato y parche del observador interno

Unidad: `origin/effective-mapping/instrumented-build/observer-contract-and-patch`.
Fecha: 2026-10-18. Estado: **productor implementado y siete unidades compiladas**.
Contrato [OB01–OB10](../../schemas/pcsx2-observer-v1.md),
[evidencia SRC50](../compatibility/pcsx2-observer-evidence.json).
El enlace del emulador instrumentado y la adquisición real quedan pendientes.

## Decisiones sustentadas en la revisión fijada

Se inspeccionó el checkout PCSX2 v2.8.2,
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. El recibo registra hashes de diez
archivos originales. `PINE.cpp` ejecuta las lecturas normales desde su hilo,
pero encola el guardado al hilo CPU. `VMManager::DoSaveState` descarga memoria
antes de crear el hilo que comprime/escribe; la respuesta PINE y el callback
`OnSaveStateSaved` no garantizan que el archivo esté escrito.

`QtHost.cpp` permite encolar callbacks al hilo CPU, cuyo bucle procesa eventos
estando pausado. La transición a pausa completa las esperas de VU/GS antes
de devolver el control. El nuevo lector se ejecuta allí y exige pausa, PC
esperado y cola de guardados vacía. La consulta de cola usa el mutex original;
no espera mediante join. Cola vacía tampoco garantiza éxito del archivo.

Una llamada bloqueante de PINE al hilo CPU podría entrar en conflicto con
`PINEServer::Deinitialize`, que hace join del servidor. Se usa encolado sin
bloqueo, propiedad compartida y espera máxima de dos segundos en PINE. Un
callback cancelado antes de empezar no lee; si ya empezó, su resultado tardío
se descarta. Este plazo no limita todas las operaciones del transporte original.

La primera aserción ABI detectó que `cpuRegs.cycle` es **u64**. Se conserva el
parche rechazado y se prepara otra copia con ciclo de 64 bits, sin truncarlo.
El protocolo mantiene snapshots de 88 bytes reduciendo su reserva final a
u32. Se prueban ciclos superiores a 2^32. El CRC exportado es `GetDiscCRC()`.

## Implementación y principios SOLID

| Componente propio | Responsabilidad |
|---|---|
| [Reader y dominio](../../tools/observer/include/sh3_observer/capture.hpp) | Puerto inyectable, validación y resolución de dos páginas como máximo; lectura doble y comparación |
| [Códec C++](../../tools/observer/wire.cpp) | Little endian explícito, framing y eliminación de datos parciales al fallar |
| [Completion](../../tools/observer/include/sh3_observer/completion.hpp) | Propiedad y cancelación entre productor y callback, sin referencias a buffers de la pila PINE |
| [Adaptador](../../tools/observer/pcsx2/adapter.cpp) | Globals y ABI reales, lectura de RAM por offset validado y despacho CPU |
| [Lector Python](../../tools/inspectors/observer_capture.py) | Validación estricta del paquete, identidad suministrada y reutilización del dominio MP |

El dominio no conoce PCSX2, sockets, filesystem ni Nintendo. `Reader` tiene
solo dos operaciones; los dobles y el adaptador satisfacen el mismo puerto.
El códec y la coordinación se pueden verificar sin el emulador. El adaptador
usa miembros de las estructuras reales; no aplica offsets ABI externos.
El cliente no proporciona una dirección host que se desreferencie.

La suma de bias y dirección virtual usa aritmética módulo 2^64. Se rechazan
handlers, segmentos fuera de los 32 MiB y respaldo no contiguo. Un alias
válido conserva su offset y `matches_expected_backing=false`. Los errores
eliminan snapshots y bytes parciales del reply. Python no publica direcciones capturadas,
PID, PC, CRC ni datos en `repr` o `metadata()`.

El productor no escribe archivos. El coordinador que vincula captura A,
guardado nuevo, captura B, estado y PINE implementará OB07–OB08 en una unidad
posterior, incluyendo fallos de I/O/cierre/publicación. Los hashes de contexto
suministrados al lector todavía no prueban ese vínculo; los metadatos mantienen
`state_binding_verified=false` y `live_acquisition_verified=false`.

## Parche y compilación privada

Se conservan dos copias privadas, sus parches y los fallos de la primera.
El parche final modifica **cuatro archivos**: CMake, PINE y VMManager `.cpp/.h`;
añade **siete archivos propios**. SHA-256 del diff completo:

`3320dbaf751af225aa872069ae154b074fb1a1029c076bb49871fac6e06f590a`

Los **2.934 archivos** del baseline, sus tests, su ejecutable validado y los
**5.228 archivos/70 enlaces** del prefijo se verifican de nuevo sin cambios.
Las siete copias propias coinciden con el código público. Los originales,
diff, objetos y logs completos permanecen fuera del repositorio.

CMake sin opción explícita conserva `SH3_ENABLE_OBSERVER=OFF`: **811 entradas**,
ninguna del observador. Con ON hay **814 entradas**, exactamente tres nuevas.
La opción limita esta integración a macOS x86_64; configuración Qt habilitada.

Se compilan **siete objetos** usando las órdenes generadas por esas
configuraciones: PINE/VMManager con OFF, PINE/VMManager con ON y los tres
archivos propios. Apple Clang 21, SDK macOS 26.5, x86_64, mínimo macOS 11 y
ThinLTO. Pasan las aserciones reales de puntero, vmap, tamaño de página,
layout de RAM y PC/ciclo. Esto no incluye enlace ni ejecución del adaptador.
`BuildVersion.h` es la declaración original; sus valores se resolverán al
construir y enlazar el emulador completo.

Nueve procesos finales aceptados y grupos cerrados, 31,432 s acumulados.
Copia/configuración/objetos usan presupuesto acotado de 1 GiB por versión,
suelo de 10 GiB y 180 s por proceso; máximo final medido **171,08 MiB**.
La reserva IB02 para el build completo sigue en 20 GiB. Al cierre: **20,03 GiB**,
medición que debe repetirse antes de iniciar esa compilación.

## Pruebas y pipeline

- **107 pruebas Python nuevas; 2.027 totales aprobadas.** Lector nuevo con
  100 % de líneas y ramas. Total: 98,83 % de líneas y 97,39 % de ramas;
  gate independiente 80/80 aprobado.
- **49/49 CTest Release y 49/49 con ASan/UBSan**, incluidos dos nuevos tests.
  El último caso adicional de frontera se verifica repitiendo ambos tests
  del observador en las dos configuraciones.
- **12.289 combinaciones de frontera** C++ más negativos de rangos, mapas,
  identidades, pausa, guardado, lectura y contenido. Oráculo Python separado
  compara el paquete C++ completo byte por byte, incluyendo el ciclo alto.
- Cancelación antes del callback, callback después de destruir al solicitante,
  timeout con captura ya iniciada, ejecución duplicada y finalización normal
  desde otro hilo. Sin esperas fijas para coordinar los tests de carrera.
- Cobertura Apple LLVM propia: dominio y códec **100 % líneas/ramas**;
  Completion **92 % líneas/100 % ramas**. La métrica GCC se incorpora al
  filtro existente de CI; no se presenta la medida LLVM como ejecución GCC.

Los targets host existentes ejecutarán estos tests en CI; Python entra en el
job de calidad, el oráculo se añade a Ruff y `tools/observer` al filtro de
cobertura C++. No se añade dependencia de observador al build Nintendo.
CI remota y pruebas originales con el binario instrumentado no se ejecutaron.

Fallos conservados: tipado inicial del test C++, comprobaciones de excepción
ajustadas a `ProfileError.code`, aserción ABI del ciclo, fixture del oráculo
actualizada al ciclo alto y seis tests de procesos impedidos por el sandbox.
La regresión completa posterior con acceso a `ps` pasa. El primer CMake se
abortó al desaparecer un temporal durante la medición: se verificó cierre y
se corrigió el muestreo antes de usar directorios nuevos.

## Continuidad

Sigue **`instrumented-build/build-and-validate`**, detallada en
[F02](../specs/sh3-3ds/tasks/F02.md): revalidar hashes/capacidad, construir en
otra etapa, repetir los 113 tests originales, empaquetar y verificar el
binario exacto; después probar transporte privado, errores y cierre.

Tras ello: coordinador OB07–OB08 y nueva sesión de cuatro paradas MP08.
No se arrancó BIOS ni juego en esta unidad, no hay mapa efectivo real nuevo,
relación de carga demostrada ni prueba de Nintendo. F02.07, Q05/G02 y las dos
salas conectadas permanecen abiertos. Dos muestras iguales no autentican
la ejecución ni excluyen modificaciones intermedias.
