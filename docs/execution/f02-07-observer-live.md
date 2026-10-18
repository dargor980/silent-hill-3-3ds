# F02.07 — Adquisición real y continuidad del mapa

Unidad: `origin/effective-mapping/observer-acquisition-live-session`.
Fecha: 2026-10-18. Estado: **completada para una invocación de A**.
Contratos [AC01–AC11](../../schemas/observer-acquisition-v1.md),
[OS01–OS06](../../schemas/observer-series-v1.md) y
[MP08](../../schemas/effective-mapping-v1.md).
[Evidencia SRC53](../compatibility/observer-live-evidence.json).

## Resultado

Se capturaron entrada, pre-SW, post-SW y retorno de una partida nueva desde
la ISO europea. Las cuatro adquisiciones comprueban identidad, pausa, mapa,
RAM, PC y ciclo contra un estado nuevo y lecturas PINE. La base EE, tabla
vmap, entrada de página y respaldo resuelto coinciden entre las cuatro pausas.
El respaldo coincide con el offset esperado; no fue necesario normalizar alias.

| Comparación sobre 1.536 bytes | Resultado |
|---|---|
| Entrada contra hash del recurso candidato | Iguales |
| Entrada → pre-SW | 0 bytes distintos |
| Pre-SW → post-SW | 3 bytes distintos, intervalo relativo [85, 88) |
| Entrada → retorno | 40 bytes distintos en 16 intervalos |
| Post-SW y retorno contra hashes históricos SRC29 | Iguales |

El validador SW existente confirma el salto BEQ con escritura en su delay
slot, destino relativo 84 y ancho 4. El par de instrucciones extraído del
estado coincide con el hash histórico; también se observó en el depurador.
La traducción medida corresponde a la ventana de datos, no a todas las páginas
de código. Los otros cambios hasta el retorno aún no tienen pares individuales.

Dos reimportaciones independientes de los archivos guardados generan SHA-256
`23d84cb2f558f6b9359fe158891ef1ac47f04aef17e78b67b51453c276b459b5`.
Son dos análisis de una captura real, no dos ejecuciones independientes del juego.
La comparación histórica usa informes fijados por hash; no reejecuta SRC29.

## Sesión y custodia

Se verificaron la ISO completa, BIOS, 2.934 archivos del baseline, 2.941 de la
fuente instrumentada y 5.228 archivos/70 enlaces del prefijo. Se utilizó el
candidato exacto SRC51, sin recompilar ni cambiar su parche. Se creó un perfil
privado, con copias de BIOS/tarjetas, directorio de estados y TMPDIR exclusivos,
permisos 0700 y umask 077. Los originales del perfil permanecen intactos.

Qt normalizó únicamente `GameListTableView/HeaderState` al inicializarse.
La diferencia se inspeccionó antes de fijar el hash de perfil; el guard no se
relajó. El usuario confirmó el inicio de Nueva partida con el perfil solicitado
de textos españoles y ambas dificultades Normal. Esa confirmación es la
evidencia de selección; no se verificaron visualmente todos los menús.

La automatización pulsó controles del depurador. El usuario inició la partida
y añadió dos breakpoints porque teclado/menú contextual no respondían a la
automatización. Se verificaron activados antes de continuar. No se cargaron
estados históricos ni se editó memoria entre las capturas. Se avanzó por las
interrupciones intermedias de la función hasta el retorno previsto.

El control de arranque aceptado se mantiene separado de MP08. Después se
guardaron las cuatro paradas aceptadas en slots nuevos, secuencias consecutivas
y una misma sesión. Cada adquisición conservó tres paquetes privados A/B/C
coherentes; las latencias individuales fueron inferiores a medio segundo.

PCSX2 terminó desde la UI con código cero, grupo cerrado y socket eliminado.
El supervisor registró 911,103 segundos de sesión, incluido trabajo humano y
pausas; no es tiempo de ejecución del juego ni una medida de rendimiento.
Se aplicaron 1.800 segundos de plazo, 8 GiB de presupuesto de etapa y 10 GiB
de suelo libre. El ejecutable y perfil original permanecen sin cambios.
Los lectores anclados se cierran antes de publicar cada informe de reimportación.

## Corrección encontrada durante la captura

El primer estado en la entrada se rechazó con `STATE_BUDGET`: el miembro de
estructuras internas tenía **2.597.162 bytes**, por encima del límite anterior
de 1 MiB. El estado y rechazo se conservan; no se emitió recibo aceptado ni
paquetes para ese intento. Se inspeccionaron `FreezeInternals` y `gifPathFreeze`
de la revisión fijada: después de cpuRegs hay subsistemas y buffers variables.

AC11 fija un presupuesto local de **4 MiB** para este miembro en la extensión
de adquisición. Se valida el CRC ZIP de todo el miembro y solo se interpreta
el prefijo conocido; un tamaño superior se rechaza antes de abrirlo. El archivo
total sigue limitado a 64 MiB. Esto no afirma un máximo universal de PCSX2.
El lector PS histórico conserva su límite de 1 MiB.

Antes de repetir la entrada se aprobaron 147 pruebas afectadas. La nueva
captura utilizó otro slot sin reanudar ni cambiar el esperado: CPU importada,
ciclo y ventana de datos coinciden con el intento rechazado. Los archivos ZIP
completos tienen hashes distintos y no se presentan como idénticos.

## Diseño y validación

[observer_series](../../tools/inspectors/observer_series.py) es puro y reusa
los validadores AC/OB/MP y la comparación de rangos. La adquisición, custodia,
UI y publicación permanecen separadas. Exige orden, identidad, secuencias,
slots distintos, hashes, tres muestras por parada y ciclos u64 crecientes.
La base se toma de GPR4 de entrada; el PC de retorno debe coincidir con GPR31
de entrada. GPR4 de retorno puede cambiar, como ocurre aquí.

Se añadieron **37 casos**: seis para AC11 y 31 para la serie, incluidos alias,
mezclas de sesiones/proceso, cambios de mapa, ciclos, retorno y datos. La
regresión pasa **2.233 pruebas en 24,15 segundos**.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| observer_state | 23/23 | Sin ramas |
| observer_series | 43/43 | 4/4 |
| Total herramientas | 4.261/4.306 (98,95 %) | 1.261/1.294 (97,45 %) |

Ruff, formato de 109 archivos, gate independiente 80/80, contratos y enlaces
del repositorio pasan. El job Python existente descubre las pruebas nuevas
sin originales del juego. No se ejecutó CI remota ni se repitieron suites
C++/proveedor: no cambiaron sus fuentes ni el binario SRC51.

## Alcance y siguiente tarea

MP08 queda satisfecho **para estas cuatro pausas de esta invocación**. Los
recibos puros conservan `live_acquisition_verified=false` y autenticación no
provista; la evidencia externa de lanzamiento, interacción, adquisición y cierre
se registra en SRC53. No se convierte coherencia de entradas en autenticación
frente a un proceso host adversario. Extremos iguales tampoco prueban que no
hubiera cambios de mapa entre observaciones.

Sigue **`origin/remaining-writers`**, detallada en el
[ticket F02](../specs/sh3-3ds/tasks/F02.md): explicar los cambios restantes con
pares de escritura y un modelo acotado verificable. Después corresponde
`origin/load-provenance`, para vincular la lectura del archivo con el destino.
Semántica, doce categorías, dos salas conectadas, F02.07/Q05/G02 y validación
física en New Nintendo 2DS XL permanecen pendientes.
