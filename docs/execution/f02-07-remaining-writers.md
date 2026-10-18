# F02.07 — Conciliación de las escrituras restantes

Unidad: `origin/remaining-writers`. Fecha: 2026-10-18.
Estado: **completada para la repetición desde la entrada fijada de SRC53**.
Contrato [RW01–RW08](../../schemas/remaining-writers-v1.md).
[Evidencia SRC54](../compatibility/remaining-writers-evidence.json).

## Resultado

Se adquirieron **66 pausas**: entrada, 32 pares pre/post y retorno, con 198
paquetes A/B/C y estados nuevos. Los efectos calculados de cada SW reconstruyen
los 1.536 bytes del retorno. Los **40 bytes distintos en 16 intervalos** quedan
explicados por los pares observados; no quedan diferencias netas sin explicar.
Entrada y retorno coinciden con los hashes registrados en SRC53.

El patrón observado se repite en ocho registros separados por 128 bytes:

| Destino relativo dentro del registro | Pares por registro | Ancho por SW | Bytes distintos por par |
|---|---:|---:|---:|
| +64 | 2 | 4 | 0 |
| +84 | 1 | 4 | 3 |
| +96 | 1 | 4 | 2 |

Son 16 pares sin cambio y 16 con cambio, sobre cuatro sitios de escritura
distintos. Se escriben 128 bytes contando repeticiones; ese número no equivale
a los 40 bytes cuyo valor final cambia. Los destinos relativos no identifican
la semántica de los campos ni demuestran todavía que el recurso sea una cámara.

Dos reimportaciones independientes de los mismos archivos generan SHA-256
`fd096c782b339dee67271416dc3ba1a489e8f20b1ab2f4e6cd3fba2c9ed5e6c3`.
El bloque reconstruido tiene SHA-256
`4826f98efad530eb84f1f04b4bed7879d6143b1c4fc2ef1044244317a6656d52`.
Son dos análisis de una serie completa, no dos ejecuciones completas del juego.

## Plan y separación de responsabilidades

[writer_sites](../../tools/inspectors/writer_sites.py) examina una ventana
privada fijada de 472 bytes. Reusa el decodificador conservador y encuentra
13 sitios posibles: siete SW directas y seis pares BEQ+SW. Explora ambos
sucesores cuando no resuelve la condición; no infiere decisiones de coma
flotante. Solo cuatro sitios se observaron en esta ejecución. El catálogo
estático no demuestra ejecución ni cobertura de todas las rutas.

[writer_trace](../../tools/inspectors/writer_trace.py) consume estados uno
a uno, reusa AC/MP y el validador SW, y reconstruye exclusivamente los efectos
de los pares aceptados. Exige identidad, secuencia, slots, código, mapa y ciclos
coherentes; compara cada preestado con la reconstrucción anterior y el retorno
completo con la reconstrucción final. Sobrescrituras y pares sin cambio se
conservan. El orden o la igualdad final por sí solos no atribuyen una escritura.

Ambos módulos son puros. Adquisición, control de UI, custodia, reloj y publicación
permanecen en adaptadores separados; el runtime Nintendo no incorpora estas
herramientas ni depende de PCSX2. El límite es 48 pares/98 estados para mantener
slots únicos, dentro del presupuesto de 256 hits y 60 segundos de ciclos EE.
El valor de PS2CLK y la carga inicial pausada se contrastaron con Common.h y
QtHost.cpp de la revisión de PCSX2 fijada en SRC51.

## Captura y custodia

Se verificaron ISO/BIOS, ejecutable, parche, 2.934 archivos del baseline,
2.941 instrumentados y 5.228 archivos/70 enlaces del prefijo. Se usaron perfil,
copias de tarjetas/BIOS, estados y socket privados nuevos. Qt solo normalizó
`GameListTableView/HeaderState` antes de fijar el perfil. Los originales y el
ejecutable conservaron sus hashes.

Se restauró una copia de la entrada SRC53 **antes de la primera captura**.
Los campos de CPU interpretados, ciclo y datos de esa captura coinciden con la
copia. No se cargaron estados durante la serie. El perfil español/Normal/Normal
procede de la confirmación
del usuario en SRC53; aquí no se inició otra partida ni se verificaron los menús.

En cada pausa, AC comprueba estado, RAM, PC, ciclo, identidad y traducción de
datos. Además, la ventana completa de código se compara por PINE antes/después
de adquirir y contra cada estado: 132 comprobaciones PINE. El mapa de datos
coincide entre las 66 pausas. El avance registrado es de 616 ciclos EE, sin
interpretarlo como una medición de rendimiento del port.

Cada adquisición aceptada tardó entre 0,468 y 0,657 segundos. La sesión completa,
incluidas pausas de automatización, duró 1.156,112 segundos. PCSX2 salió desde
la UI con código cero; el supervisor verificó cierre y desaparición del socket.
Los lectores privados se cerraron antes de publicar las reimportaciones.

## Intento incompleto conservado

El primer intento alcanzó el plazo de 1.800 segundos con 56 capturas: entrada,
27 pares completos y otro preestado. El supervisor cerró el proceso y registró
`deadline`, salida cero y cierre verificado. La relectura de todos los archivos
aceptados rechaza la serie con **TRACE_INCOMPLETE**. No se publicó como traza
completa ni se mezcló con el segundo proceso.

Se preparó un segundo perfil y una sesión nueva desde la misma entrada, con
3.600 segundos de tiempo de pared para cubrir la adquisición interactiva.
Se mantuvieron el máximo de 60 segundos de avance emulado, 48 pares, 8 GiB de
etapa y 10 GiB de espacio libre mínimo. No se cambió el validador para aceptar
el intento incompleto. Ambas series y sus límites permanecen registrados.

## Validación

Se añadieron **54 casos sintéticos** sobre catálogo, ramas y delay slots,
escrituras repetidas/sin cambio, reconstrucción, identidad, mapa, ciclos,
código, límite activo, retorno prematuro, gaps y series incompletas.
La regresión pasa **2.287 pruebas, sin fallos ni omisiones**; JUnit registra
28,653 segundos.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| writer_sites | 54/54 | 24/24 |
| writer_trace | 80/80 | 8/8 |
| Total herramientas | 4.395/4.440 (98,99 %) | 1.293/1.326 (97,51 %) |

Los controles de arquitectura, custodia y enlaces pasan sin errores; también
`git diff --check`. Pasan el gate independiente 80/80 y Ruff/formato para los 113 archivos del
alcance de CI (`tools`, `tests/python`, `tests/observer_wire_oracle.py`). Un
barrido adicional de todo `tests` señaló 30 infracciones de lint y seis archivos
sin formato en fixtures previos de proveedores, fuera de ese job; no se alteraron
esos originales fijados por hash. No se ejecutó CI remota ni se repitieron
compilaciones/suites C++ o de proveedores, cuyas fuentes no cambiaron aquí.

## Alcance y siguiente tarea

Se explican los efectos observados de esta repetición. El muestreo no excluye
escrituras transitorias revertidas entre pausas, ni prueba continuidad del mapa
en todos los instantes. La traducción de datos no acredita páginas de código;
su igualdad de contenido se registra por separado. Los recibos puros mantienen
`live_acquisition_verified=false` y autenticación no provista; SRC54 documenta
por separado la adquisición real, interacción y cierre.

Sigue **`origin/load-provenance`**: vincular una lectura del archivo candidato
con el destino previo a A, distinguiendo copia, transformación y mera igualdad.
El [ticket F02](../specs/sh3-3ds/tasks/F02.md) detalla contrato, límites, pruebas,
captura y aceptación. Semántica, doce categorías, dos salas conectadas,
F02.07/Q05/G02 y validación física en New Nintendo 2DS XL siguen pendientes.
