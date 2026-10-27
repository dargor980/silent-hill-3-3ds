# HL: inventario y reloj de Heather original

Inicio: 2026-10-25. Actualizado: 2026-10-26. [Spec EARS HL01–HL06](../specs/sh3-3ds/heather-locomotion.md).
**Estado actual: HL-T1–T4 y aceptación funcional HL-T5a/b completadas.**
El usuario confirma espera/caminar/correr y lifecycle en **`7250f427ffb9`**,
tras corregir `open` de `4707dacec7d1`. Métricas aproximadas registradas;
HL-T5c conserva duración y cobertura por encuadre/arco pendientes.
Continúa [HM-T1, inventario espacial](../specs/sh3-3ds/heather-movement.md). El cotejo
privado SRI2 previo conserva 245 poses con error máximo 0,000515 ≤0,001.

Resumen histórico de la investigación inicial: El inventario conserva 49
descriptores básicos y distingue los dos canales del jugador. La primera
serie de dibujo no acredita una vuelta completa: al final repite contador
y matrices y cambia la máscara. Nueve poses excedían el límite con la
referencia matemática; HL-T2c identifica la precisión de los extremos como
causa y acredita una referencia f32 separada, sin elevar la tolerancia.
Una serie posterior acredita una vuelta completa de `0x65`, con 67 avances
y poses verificadas. En ese corte inicial de HL-T3, el mando normal selecciona caminar
`0x6D` y correr `0x71`; se cotejan poses estables, retorno completo a espera,
inicio/interrupción, vueltas completas de ambos movimientos y la transición
caminar→correr sostenida, incluida su salida recursiva. Quedaban pendientes la transición
inversa sostenida, wrap durante modo 5 y la integración al visor; la aprobación
se limita a los tramos y perfil diagnóstico fijados.

La prueba física [HP-T4](f03-02-heather-performance.md) permanece aceptada
para el build `8f778b6e4960`. Su reloj de inspección y su aceptación funcional
no equivalen a una verificación completa del reloj nativo, caminar o correr.

## HL-T1: contrato e inventario

`tools/inspectors/animation_descriptors.py` recibe bytes inmutables y capacidad
explícita; devuelve registros inmutables y observaciones. No lee archivos,
modifica velocidades ni asigna acciones a IDs. Las pruebas usan ejemplos
sintéticos propios y un vector literal de endian/signo. El gate individual
de cobertura se añade al job Python de `.github/workflows/ci.yml`.

Fuentes fijadas: ELF europeo `SLES_514.34`, 3.395.784 bytes, SHA
`cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`;
MDL original 522 y ANM básico 526 identificados en [HI](f03-02-heather-inspection.md).
El helper privado `build/heather-locomotion/audit_inventory.py` compara cuatro
estados anteriores (02/04/06/08), reconstruye los registros y verifica ocho
ventanas de código contra el ELF. Repetirlo produce el mismo informe.

| Campo | Hallazgo |
|---|---|
| Tabla básica | `0x350d70`, 49 registros `<HHhHHBB>` y terminador de 12 ceros |
| Extensión | 600 bytes; terminador en `0x350fbc`; IDs 100–148 |
| Capacidad del ANM | 1.763 muestras; no supone 1.763 clips |
| Cantidades cero | IDs 100, 125 y 128; se conservan |
| Discrepancia de cantidad | ID 145 declara 30; rango 697–736 contiene 40 |
| Byte final | Nueve registros no nulos; el selector puede escribirlo |
| Inicialización PAL | `0x135ec0` llama `0x1dea20`: velocidad ×60/50 truncada |
| Descriptor `0x65` | `0x350d7c`, diez muestras 0–9, loop 1, velocidad 256→307 |

Los 49 registros de RAM coinciden con ELF tras aplicar únicamente esa
conversión de velocidad. El byte final no se trata como padding: hay escrituras
en `0x132c18` y `0x133734`. Otras tablas de Heather siguen fuera de este inventario.
La tasa aritmética nominal de `0x65` es 15.350 Q12/s; no es una medición de FPS.

La ruta para actor `0x100` ejecuta el consumidor común `0x13f3e0` dos veces:

| Canal | Argumento de modo | Retorno |
|---|---:|---|
| actor + `0x260` | 2 | `0x1dd3f0` |
| actor + `0x1d0` | 1 | `0x1dd404` |
| Tras el postprocesamiento del jugador | — | `0x1dd434` |

El retorno `0x1dd444` del caballo se omite para Heather. Ambos canales usan
el mismo descriptor en las muestras examinadas; esto no demuestra cómo se
mezclan durante una transición. En esta ruta el siguiente índice es el
`u16` en canal + `0x2e`. El cursor en + `0x08` avanza durante la decodificación
y no debe reinterpretarse como índice de la siguiente muestra.

## HL-T2a: serie de dibujo y límites encontrados

La sesión privada `heather-clock-v2` usa el ejecutable de PCSX2 fijado en HI,
una única restauración inicial del estado original 02 y ninguna entre las
49 capturas, sin escrituras al guest. Los slots y recibos son nuevos; la
sesión preliminar `heather-clock-v1`, con dos paradas duplicadas, se conserva
separada y no se mezcla con esta serie.

En cada estado se verifican SHA, CRC, PC `0x1d39bc`, ciclos EE, identidad de
actor/recursos, MDL y ANM completos, y tres ventanas ELF/RAM. El registro
de reanudaciones cubre 3–49; el paso 1→2 quedó registrado en la interacción
de herramientas antes de habilitar ese registro. Las pausas de depuración
impiden usar el tiempo de pared para medir rendimiento.

| Resultado | Observado |
|---|---:|
| Dibujos 1–48 | Ambos contadores siguen incrementos de 614 Q12, ticks 2 |
| Avance comparado | 47 pasos, 28.858 Q12 de los 40.960 de una vuelta |
| Wraps | 0 |
| Dibujo 49 | Contador 29.472 repetido y matrices exactamente iguales a 48 |
| Máscara 48→49 | `0x3021` → `0x1b` |
| Poses comparadas | 47, correspondientes al contador anterior |
| Error máximo | 0,0010829080933021373; límite conservado: 0,001 |
| Poses fuera del límite | Slots 27–35 |
| Error máximo de componentes de rotación | 0,000015975654 |
| Control con contador posterior | Error mínimo 0,333624203979 |

El mayor error está en el slot 33, hueso 41, componente 14 de la matriz
(traslación): esperado 33,721436012805135, observado 33,72251892089844.
Ese fallo inicial se conserva; su resolución acotada figura en HL-T2c. La aceptación
HI de cuatro poses conserva su alcance original; no se extiende a esta serie.

El reconciliador rechaza la arista 48→49 en ambos canales. También rechaza
hueco, duplicación, contador alterado, identidad de canal incorrecta y ticks
alterados. Se añade una regresión sintética para un dibujo repetido con
ciclos crecientes y ticks residuales: el avance del emulador no demuestra
por sí solo otra evaluación de animación.

La posición observada del actor es `(-60000, 0, 60000)`, callback `0x1986c0`.
No se presenta como locomoción jugable. Cambiar la máscara conservando las
matrices obliga a capturar los retornos reales antes de intentar otra serie.

## HL-T2b: inicialización y retornos del jugador

Los estados V2 51–56 conservan seis retornos: `1dd3f0`, `1dd404`, `1dd434`
en dos contextos. En 51 solo terminó la inicialización del canal +`260`;
el otro sigue en modo 0. En 52 ambos están en modo 1, siguiente muestra 1,
contador cero; las 36 matrices activas coinciden exactamente entre 52 y 53.
El valor residual de incremento 614 no acredita avance durante inicialización.
La pose parcial de 51 difiere 4,708887; la completa de 52/53, 0,000819056.

En 54–56 se repite esa secuencia, pero cambia el contexto: selector de etapa
34→33, posición `(-60000,0,60000)`→`(-20000,0,19700)` y banco ANM 526→525.
El MDL original 522 sigue coincidiendo byte a byte. El ANM 525
`chhaa_basic1_knif.anm`, 465.436 bytes, SHA
`a0ad870863df5c495c453acdc2230dc8bb762394687599329f5a97a975d75181`,
es un banco de animación del mismo atuendo original. Sus primeras diez muestras
son idénticas al banco 526; el archivo completo no lo es. Las series de ambos
bancos no se unen para acreditar continuidad. Tampoco se extrapola igualdad
de matrices antes/después del postprocesamiento a otras acciones del jugador.

## HL-T2c: precisión de los extremos

La diferencia se origina al reconstruir W desde XYZ comprimidos, especialmente
cerca de W=0. Se cotejan las rutas `13e2f0`/`13e7a0`, el perfil de PCSX2
(`FPU.Roundmode=3`, `FPUDiv.Roundmode=0`, `VU0.Roundmode=3`) y la implementación
local de `recSQRT_S_xmm`, que cambia a redondeo al más cercano para la raíz.

El helper puro `tools/qa/animation_precision.py` recibe tres i16 y el signo W;
trunca productos/sumas f32 y redondea la raíz f32 al más cercano. Su entrada
proviene del ANM original, no de los extremos capturados en RAM. Estos últimos
solo son el objeto de comparación. La interpolación y composición se evalúan
desde el recurso y la jerarquía, con el contador anterior.

| Cotejo V2, estados 2–48 | Resultado |
|---|---:|
| Poses independientes | 47 |
| Error máximo de pose con referencia f32 | 0,0003692779699804305 < 0,001 |
| Extremos cotejados | 3.384 |
| Error máximo de extremo | 5,960464477539063e-8 < 1e-7 |
| Control: acumulación al más cercano | 9,868759661912918e-6; falla |
| Control: signo W invertido | 1,99917334318161; falla |
| Control: contador posterior, error mínimo de pose | 0,3336214123004808; falla |

Los 25 tests del helper incluyen un oráculo con `Fraction` y raíz Decimal
de 70 dígitos, vectores literales, W negativo/cero, clamp y entradas inválidas.
La batería integrada seleccionada suma 179 pruebas aprobadas. El inspector
de descriptores y el helper de precisión alcanzan 100 % de líneas y ramas;
sus gates individuales están incluidos en CI y comprobados localmente.
No se afirma ejecución remota de CI ni precisión de una PS2 física.

## HL-T2d: segunda serie y frontera de contexto

V3 restaura una copia fijada de V2-56 una sola vez al arrancar; no hay
restauraciones intermedias ni escrituras al guest. V2 dejó de estar disponible
antes de esta continuación y no tiene recibo de cierre limpio. V3 usa perfil,
socket y estados nuevos; conserva esa frontera explícita.

V3-1 es el ancla restaurada; V3-2 repite sus ciclos/RAM y se excluye. V3-3–22
contienen 19 avances consecutivos de 614, 11.666 Q12 y cero wraps. Las 19 poses
comparables pasan (máximo 0,0003656233980109391); extremos: 5,960464477539063e-8.
La siguiente reanudación no alcanza el breakpoint. Se pausa manualmente y
se conserva V3-23 en PC `81fc0`, ciclos 64.281.936.883: contador 12280 residual,
profundidad de contexto 1→0 y posición `(0,0,0,1)`. No se acepta una vuelta.

Tras reanudar y enviar START se alcanza V3-24: nueva inicialización, contador 0,
posición `(-16000,0,20000)`. En V3-25–32 ambos canales están en modo 3; el
acumulador +`20` avanza 768, 1230, 1692, 2154, 2616, 3078, 3540 y 4002.
El contador +`18` sigue en cero. El despacho `431320[modo+1]` lleva modo 3
a `13f6d4`: suma la velocidad de mezcla y, al alcanzar 4096, reinicia su
acumulador, cambia a modo 1 y llama recursivamente al consumidor. V3-33
observa esa salida con contador 614. Esta transición se conserva aparte;
no se afirma todavía una validación independiente de sus matrices de mezcla.

## HL-T2d: vuelta completa aceptada

El tramo aceptado empieza en V3-33 y continúa por V3-100–166. Las ranuras
100 en adelante evitan sobrescribir el archivo 90 usado como semilla; el
salto de numeración no es un salto de ejecución. El recibo de 100 enlaza
explícitamente el SHA de 33. Cada intervalo contiene una reanudación observada,
sin restauraciones, botones de juego ni escrituras de memoria. Los ordinales
del auditor son consecutivos, 0–67; las ranuras físicas quedan en el informe.

| Verificación final | Resultado |
|---|---:|
| Retornos / avances por canal | 68 / 67 |
| Avance acumulado | 41.138 Q12 ≥ 40.960 |
| Reinicios | 1; 40524→178→792 |
| Muestras actuales cubiertas | 0–9 |
| Poses completas comparadas | 67 × 36 matrices |
| Error máximo de pose | 0,0003990606330717128 < 0,001 |
| Extremos comparados | 4.824 |
| Error máximo de extremo | 5,960464477539063e-8 < 1e-7 |
| Control con contador posterior, error mínimo | 0,3336214123004808; falla |

La última pose, cuyo contador de entrada es 178, produce el máximo de error
(hueso 35, componente 13). Las dos secuencias de reloj coinciden y pasan
el reconciliador. Los controles de duplicado, hueco, contador alterado,
canal distinto y ticks incorrectos se rechazan. El primer retorno solo
ancla el contador; no se deduce la entrada de su pose.

En todos los estados se comparan los recursos completos, CRC, PC y actor,
jerarquía y ventanas de código fijadas. Se mantiene el MDL original 522 y
ANM 525; no se mezcla la evidencia del banco 526. El actor permanece cerca
de X=-16000, Y≈0,11531, Z=20000, etapa 33.
El pequeño asentamiento Y no constituye locomoción. Ese tramo terminó pausado
en V3-166, `1dd434`, con ambos contadores en 792.

Esta aceptación cubre reloj y matrices de 36 huesos activos del clip `0x65`
en la reproducción diagnóstica. No acredita entrada jugable, blend, morphs,
iluminación, materiales, colisión, rendimiento de pared o precisión de PS2 física.

## HL-T3a/b: entrada normal y selección

Se continúa V3 sin restaurar estados ni escribir memoria del juego. El usuario
opera el teclado: flechas para dirección, J/Cuadrado y Espacio para reanudar
desde pausa. La fuente de entrada normal, conexión, 28 valores, flancos y ordinal
se leen en el bloque `0x355a40`. `PAD.bin` no acredita los botones actuales.
↑ corresponde a `0x1000`; ↑ + J, a `0x1800`. Las ventanas de lectura y
selección se comparan con el ELF fijado y cada estado con sus recursos completos.

Se corrige una etiqueta de adquisición: `requested` en los recibos antiguos
representa el descriptor **retenido de origen en +`40`**; +`44` es el destino
seleccionado. El setter `1dd930` y la salida `13f768–13f77c` acreditan esta
distinción. Los recibos originales se preservan; el auditor expone ambos offsets.

| Acción observada | Clip / rango inclusivo | Velocidad PAL / incremento con ticks 2 |
|---|---|---|
| Espera | `0x65`, 0–9 | 307 / 614 Q12 |
| Caminar con ↑ | `0x6D`, 80–103 | 1996 / 3992 Q12 |
| Correr con ↑ + J | `0x71`, 176–199 | 2227 / 4454 Q12 |

Los dos canales usan el MDL original 522 y ANM 525 de cuchillo. Las capturas
179/180 conservan ↑ y la selección/inicio estable de caminar; 181/182,
↑ + J y la selección/inicio estable de correr. La 183 registra la liberación
de J conservando ↑ y el cambio directo correr→caminar. La 184 vuelve a caminar
estable. Sus ordinales tienen huecos: no acreditan un ciclo completo ni una
velocidad de desplazamiento. El actor se aproxima a una pared; el visor de
PCSX2 la muestra delante de Heather. No se infiere una regla de colisión.

Los intentos automatizados 167/168 no acreditan entrada; 168 duplica ciclo/RAM.
169 y 178 capturan la liberación de ↑, aunque la intención era mantenerla.
177 es una pausa manual. En 185 el usuario reportó parada automática, pero
el estado guarda PC `81fc0`, caminar y botones `0x1800`; falla la aserción
del breakpoint esperado. Se excluye como prueba caminar→correr y se conserva
como ancla previa para la siguiente captura. No se cambia su recibo para
convertirlo en una parada aceptada.

## HL-T3c: composición y pose conservada

El oráculo parte del ANM original, la jerarquía del MDL y escalares de fase.
Los cuaterniones finales de RAM solo se usan como objetos de comparación.
Se conserva el límite de pose `0,001` y los controles de dirección/fase erróneas.

| Tramo | Comprobación | Error máximo de pose |
|---|---|---:|
| 169–176 | Ocho evaluaciones consecutivas de caminar→espera; extremos 80→0, blend 1280→3800 | 0,000336282 |
| 180/182/184 | Tres poses estables de caminar/correr; fase anterior al incremento | 0,000290909 |
| 183 | Correr→caminar, modo 5; fase compartida y dos interpolaciones | 0,000312254 |
| 192–200 | Nueve poses: retorno desde caminar interpolado hasta salida a espera | 0,000387713 |
| 207/214 | Inicio espera→caminar e interrupción al soltar ↑ | 0,000361100 |
| 218 | Caminar→correr, ambos setters 216/217 y primera composición modo 5 | 0,000257475 |

Cada pose compara 36 matrices. El modo 5 mezcla primero origen/destino en
las muestras relativas actual y siguiente, luego interpola entre ambos
resultados por la fracción temporal. En 183 la fase de entrada es 16982 Q12,
relativa 4 + 598/4096, y blend 768/4096. Usar el contador posterior o invertir
origen/destino falla. Sigue pendiente su secuencia continua y salida/wrap.

Las hipótesis iniciales que usaban solo índices crudos para 178/179/181 fallan
y permanecen en el informe. El preludio de modo 4 conserva una pose que puede
estar interpolada o mezclada, no necesariamente un extremo del archivo.
Las capturas 186–191 fijan ambos setters y ambos preludios, antes/después,
en la misma evaluación de entrada 78633. El origen se reconstruye desde las
muestras **95 y 96 de caminar, fracción 2874/4096**, conservadas desde 185.
La primera máscara procesa 15 huesos y la segunda 21; son disjuntas y cubren
los 36 activos. Los extremos originales coinciden con máximo `5,960465e-8`.

192–200 son evaluaciones consecutivas 78633–78641: contador detenido en cero
y blend 1280, 1640, 2000, 2360, 2720, 3080, 3440, 3800; después modo 1,
blend cero, ambos descriptores de espera y contador 614. El origen crudo de
muestra 95 falla en las ocho mezclas (errores 1,566–15,609). La reconstrucción
interpolada pasa las nueve poses, incluida la salida recursiva a espera.

201–207 pertenecen a la evaluación siguiente, 78642: ↑ pulsada selecciona
caminar mediante modo 4 y produce blend 768/4096 hacia muestra 80. El origen
es la muestra 0 de espera, conocida por la salida anterior. Al soltar ↑,
208–214 registran la evaluación 78643: el nuevo preludio conserva esa mezcla
parcial y la mezcla a su vez con espera en 1280/4096. Ambas poses pasan.
La diferencia máxima observada de los cuaterniones **interpolados** conservados
es `1,035035e-7`; se publica como diagnóstico, sin reinterpretarla como extremo
crudo ni cambiar el gate `1e-7` de decodificación. La aceptación usa la pose
compuesta independiente y su límite preexistente.

El primer guardado de 206 falló por `No space left on device`. No produjo
archivo; tras liberar espacio el usuario, se guardó desde la misma pausa,
sin reanudar ni restaurar. La cadena y los ciclos se verifican hasta 214.
PCSX2 queda pausado en 214, `1dd434`. El inicio de caminar fue interrumpido
deliberadamente; no se acredita su mezcla completa ni la finalización del
segundo retorno. El retorno completo independiente es 192–200.

Validación local de esta continuación: 179 pruebas seleccionadas aprobadas,
gates individuales de líneas/ramas al 100 %, Ruff y formato aprobados,
sin errores de whitespace. Los tres informes HL-T3 se regeneran con los mismos
hashes. No se ejecuta CI remota ni se genera un nuevo build de consola.

## Evidencia y reproducción

Los estados, recursos y perfiles permanecen en la raíz privada. Los informes
y helpers locales están ignorados por Git; el repositorio contiene el contrato,
el inspector y los tests sintéticos. No se modifica el build de consola.

| Informe local | SHA-256 |
|---|---|
| `heather-locomotion-inventory-v1.json` | `90de6070575e2ef1d92af2b8ae6e7a56584cf53e5916498c2b6daa05a44d64ba` |
| `heather-draw-clock-diagnostic-v1.json` | `c224458ad0efd978b3a0bb6945a3be53572edda5ef8c587cb2a2879650f77cfb` |
| `heather-channel-initialization-v1.json` | `1a73e0e4a0995c7ae83f93bcac6ba8512502e9e4223dfd0afc189e9f84a68790` |
| `heather-endpoint-precision-v1.json` | `c76c5d0db1be75eaf16f09c3a3eab9567715fa011bcd48940d7dbe258e2d265e` |
| `heather-composed-prefix-22.json` | `e48228e653f643deb1cfe48b8de12ada75e963ac91f44e243824c5537b80546f` |
| `heather-context-boundaries-v1.json` | `e239143edb10bd9c9280459fdbbaae7f01d329c99534be4c2daaef65a1858de3` |
| `heather-composed-continuity-v1.json` | `51248b6230d5857debfb88eb1875476c6601e66958f0f7c7b20915005451f34c` |
| `heather-locomotion-observations-185.json` | `a8b3d84e04139ff1d66808306b2ff67ba126f8e1169dfcadc27bd046359828a5` |
| `heather-cached-pose-200.json` | `216282dd8135ef4a218c51f55eb504a28f680ef81aaa122c978154589f8e9e9e` |
| `heather-interrupted-pose-214.json` | `0eeb8416bfb06386fedb8791562ae7b397e9ae776d96ad35b63bd3123f0d3f7c` |
| `heather-walk-run-218.json` | `171d71fd07e08e5f24e5b6be4e908418de9029188c69f82a8a2308cf38aad09f` |
| `heather-normal-input-v2-initial.json` | `cdc5bfbdb7022502a9dff189f221271b5cc8b5537715a6b4411cf92e90161adb` |
| `heather-normal-input-v2.json` | `11086cae33412f2de2734421efa6c73c478313f2d67b4f1e86a72d9ae9f1671b` |
| `heather-input-replay-56.json` | `9892403e6eec1a40d7ef28bb0b61b06d6d4e9e39408f7046c903b5baca1c9a7d` |
| `heather-input-replay-binding-56.json` | `89de66eaaf88d45be49ecf4ac74edf9d5e8c6fed2bc46d17d9b2480c4583696f` |

El segundo informe lleva `passed: false`, `clock_passed: false`,
`pose_passed: false` y `full_loop: false`; los fallos se publican como evidencia
del diagnóstico, sin transformar el subconjunto favorable en una aprobación.
El informe final de continuidad tiene los cuatro campos en `true` y su
propia serie completa. Los informes de precisión e inicialización conservan
sus alcances parciales, sin sustituir al diagnóstico fallido.

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_inventory.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_clock.py 49
rtk proxy .venv/bin/python build/heather-locomotion/audit_initialization.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_precision.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_composed.py 22
rtk proxy .venv/bin/python build/heather-locomotion/audit_boundaries.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_steady.py 166
rtk proxy .venv/bin/python build/heather-locomotion/audit_locomotion.py 185
rtk proxy .venv/bin/python build/heather-locomotion/audit_cached_pose.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_interrupted_pose.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_walk_run.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_input_replay.py 56
rtk proxy .venv/bin/python -m pytest -q tests/python/test_animation_descriptors.py tests/python/test_animation_precision.py tests/python/test_heather_animation.py tests/python/test_animation_continuity.py tests/python/test_animation_pose_oracle.py tests/python/test_repository.py --cov=tools.inspectors.animation_descriptors --cov=tools.qa.animation_precision --cov-branch --cov-report=json:build/heather-locomotion-coverage.json --cov-report=term-missing
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-locomotion-coverage.json --files tools/inspectors/animation_descriptors.py tools/qa/animation_precision.py
```

HL-T3 permanece abierta: completar mezcla sostenida/salida de correr→caminar
y wrap durante modo 5. Las vueltas
completas de caminar/correr quedan aceptadas en la reproducción separada descrita
al final de este registro. Deben distinguirse de los puntos en ambos sentidos
caminar↔correr y del inicio
interrumpido ya observado y del desplazamiento o colisión del actor. El contrato
multiclips HL-T4 y un nuevo build físico siguen pendientes de ese cierre.

Preparado el siguiente filtro (todavía pendiente de carga manual al cerrar
esta continuación): `HL-T3-walk-to-run-setter` en `1dd930`, con origen caminar
y destino correr; `HL-T3-run-or-stop` en `1dd434`. Ajustes respaldados en
`breakpoints-before-hlt3-walk-run-v11.json`; nuevo archivo SHA
`8c548779168837ca5236b267878b8d195b24d3936b2a252a1f24469431c308d8`.
El protocolo solicita alejar a Heather de la pared caminando y añadir J sin
soltar ↑, conservando la sesión; no fuerza el clip ni la posición en RAM.

### Incidencia al cambiar los filtros

El usuario informa que el juego se pausa antes de poder alejar a Heather.
La tabla muestra solo los dos filtros v11, pero la captura 215 guarda PC
`13fa30`, uno de los puntos de caché anteriores. La pantalla previa mostraba
`13f7c0`; se conserva el fallo de esa expectativa y se usa el PC del estado
para clasificar la captura. No es un retorno compuesto ni prueba caminar→correr.

El código fijado explica el problema: `BreakpointView` llama `m_model->clear()`
al cargar ajustes, y `BreakpointModel::clear()` solo vacía `m_breakpoints`;
no elimina los puntos del núcleo. Reimportar una dirección con condición `0`
sí ejecuta `ChangeBreakPointAddCond` para anularla explícitamente. Diagnóstico
en `heather-stale-breakpoints-215.json`, SHA
`7d437353fcf921d8730993c622c500a3d0a3ff4b3cf70b3f492fd690dc319901`.

Se respalda v11 en `breakpoints-before-hlt3-neutralize-cache-v12.json` y se
preparan cuatro filas: los dos filtros actuales más `13f7c0`/`13fa30` con
condición `0`. Archivo SHA
`f550a435f720de545d6131c590145b153673a448479e65529596963d4b140ced`.
El usuario carga v12; se verifican visualmente las dos condiciones `0` y se
reanuda desde la interfaz. PINE devuelve estado de ejecución `0` en tres
lecturas separadas por un segundo, sin repetirse la parada anterior. Recibo
`heather-stale-breakpoints-resume.json`; no hubo restauración. Se deja visible
el juego ejecutándose y se solicita repetir el movimiento normal. Esta prueba
acredita la reanudación acotada, no todavía caminar→correr ni un ciclo completo.

### Caminar→correr con entrada normal, 216–218

El usuario aleja a Heather de la pared caminando y añade J sin soltar ↑.
Los tres estados conservan ordinal de entrada 81168, botones actuales `0x1800`,
anteriores `0x1000` y flanco pulsado `0x800`; fuente normal y mando conectado.
216 y 217 paran en `1dd930`, primero para el canal 2 y después para el 1:
destino `350e0c` (correr 113), argumento de modo 6, origen caminar 109.
218 retorna en `1dd434` con ambos canales en modo 5, blend 384/4096 y contador
40382 = 35928 + 4454. Las tres capturas están enlazadas, sin restauraciones
ni escrituras del huésped entre ellas. El hueco antes de 216 corresponde a
navegación normal y no se acepta como intervalo de reloj auditado.

El oráculo reconstruye 36 matrices desde MDL 522/ANM 525 originales, fase
**anterior** 35928 y blend 384. Error máximo `0,0002574741553189597`, hueso 9,
componente 13; límite `0,001`. Usar la fase posterior produce error 67,161885;
invertir origen/destino produce 131,303484. Ambos controles fallan como se espera.
El informe `heather-walk-run-218.json` acepta esta primera composición y mantiene
`hl_t3_complete: false`: no acredita mezcla sostenida, salida ni vuelta completa.

### Intento de entrada sostenida y grabación nativa

El usuario acepta mantener ↑ + J mientras se reanuda entre capturas. La
automatización de ventanas agota dos esperas de 30 segundos antes de reanudar;
se le indica soltar las teclas. El observador confirma entonces el PC y ciclo
de 218 (`1dd434`, 110119712356), sin avance. No se obtuvo otra muestra continua.

Se intenta preparar la grabación nativa de controles en
`heather-normal-input-v1/normal-controls.p2m2`. El diálogo muestra «Guardar
estado» seleccionado, pero al aceptar ejecuta la ruta de reinicio. Se detiene
la grabación desde Herramientas y se comprueba «Detener» deshabilitado.
El archivo final tiene 570 bytes, cero fotogramas y flag `fromSavestate=0`.
La captura diagnóstica 219 conserva CRC cero, PC `bfc00000` y ciclo cero:
el guard falla con `STATE_IDENTITY`, correctamente. No es evidencia de Heather.

El código local de `NewInputRecordingDlg` actualiza su tipo interno mediante
la señal `QRadioButton::clicked`; la selección visual por accesibilidad no
acredita esa señal. Esta discrepancia explica una hipótesis concreta a verificar;
no se repetirá el flujo basándose solo en el estado visual del botón.
El intento y sus archivos se preservan en
`reports/local/heather-input-recording-failed-219.json`.

La captura 218 conserva SHA
`1ae265826073d354d484373a6f923c93bc82377993fe5f9adc06232287fa2725`.
La revisión automática de permisos rechazó restaurarla porque la sesión tenía
la restricción de no cargar estados; exige confirmación específica del usuario.
Se mantiene la pausa hasta recibir esa confirmación. El usuario autoriza
expresamente recuperar 218; se restaura mediante PINE y se cotejan PC `1dd434`,
ciclo 110119712356, CRC `5088ccdb` y los 768 bytes del actor con el estado
original. Ambos canales conservan modo 5, contador 40382 y blend 384.
Recibos privados `recovery-boundary-after-recording-219.json` y
`recovery-verification-after-recording-219.json`. La VM queda pausada.
La siguiente serie deberá declarar esta frontera de recuperación separada,
sin enlazarla como ejecución continua desde 218.

Se bloquea el helper de adquisición V3 al detectar esa frontera para evitar
que una captura posterior herede `state_restores_between_samples=0` o se enlace
con 219 por numeración. Los auditores de las capturas existentes siguen siendo
reproducibles. El segundo intento, `normal-controls-v2.p2m2`, queda preparado en
el diálogo, sin aceptar ni crear archivo; se solicita al usuario seleccionar
físicamente «Al encender» y después «Guardar estado». Debe aparecer el aviso
de compatibilidad, cuya visibilidad cambia en el mismo slot que asigna el tipo
interno. Antes de reanudar se exigirán el estado inicial y el flag correcto.

El usuario realiza la selección física y aparece el aviso. Se acepta el diálogo
y esta vez se genera `normal-controls-v2.p2m2_SaveState.p2s`, SHA
`2d448f68eaeeb61f23de33c527eefce3ab55d313c7167cfc6c8ee7cc6f452fc7`.
Se cotejan CRC, PC, ciclo y bytes del actor con 218 mediante estado y observador:
coinciden y la VM sigue pausada. Informe inicial
`reports/local/heather-normal-input-v2-initial.json`; todavía no acepta entrada
ni animación. El flag del archivo se verificará al cerrarlo.

Se preparan los cuatro puntos existentes con condición `0` y nombres
`HL-T3-recording-OFF-*`, respaldo `breakpoints-before-hlt3-normal-record-v13.json`.
Perfil preparado SHA `63026aa5d19c90819bf7ab1d310a910e2f15f643f7cbdc03225ff853c7407830`;
la carga manual queda pendiente al preparar este registro. Se solicita al usuario
cargarlo, reanudar con ↑ + J, correr 3 s, caminar con ↑ 3 s y soltar 1 s antes
de pausar. La automatización no enviará teclas durante esa maniobra. El helper
local `audit_input_recording.py` comprobará el archivo cerrado, sus 36 bytes por
fotograma, origen guardado y cero regrabaciones; esta evidencia de mando no
sustituirá la comparación posterior de reloj y pose en una serie separada.

### Grabación de controles cerrada y preservada

El usuario carga los cuatro filtros v13, realiza la secuencia con el teclado y
deja PCSX2 pausado. Se guarda el final en la captura 220, SHA
`0ebb5cfd3e5e78fd40a3753e6bf306e447b9df1ca006624f6d00a86e90153fee`,
PC `81fc0`, ciclo 120733991923, ordinal 82067. Se detiene la grabación desde
la interfaz. El original `normal-controls-v2.p2m2` tiene 65.406 bytes,
1.800 fotogramas nativos, cero regrabaciones y `fromSavestate=1`; SHA
`23b065767544703b785d43570aa9a4de5c224a3efb061034f11cf1a9e67d17c0`.
El estado inicial conserva el SHA previamente fijado y su correspondencia con
218. No se alteran los botones grabados para prolongar artificialmente un tramo.

Los tramos efectivos son: 1–1328 sin entrada; 1329–1334 con ↑;
1335–1459 con ↑ + Cuadrado; 1460–1470 con ↑; 1471–1547 sin entrada;
1548–1658 con ↑; 1659–1800 sin entrada. Son fotogramas nativos de PCSX2,
no actualizaciones del juego. La caminata inmediatamente posterior a la carrera
solo dura 11 fotogramas: esta grabación no acredita la mezcla completa entre
ambas. El tramo posterior permite verificar una vuelta estable de caminar.

### Reproducción diagnóstica y ciclos completos, HL-T3c.5

Se copian el archivo de controles y su estado inicial a
`heather-normal-input-v1/replay-v1/`, manteniendo intactos los originales.
El usuario autoriza explícitamente reproducir esa copia desde el estado derivado
de 218 y carga el filtro `HL-T3-replay-cycle-windows`. La restauración inicial
es una nueva frontera diagnóstica: tercera restauración desde el lanzamiento V3,
sin continuidad declarada con las series anteriores. Se verifican PC, ciclo,
CRC y actor al iniciar. Los recibos `plan.json` y `start.json` fijan ese alcance.

El filtro en `1dd434` acepta los ordinales 81848–81875 y 81958–81985,
con actor `4481d0`; `1dd930`, `13f7c0` y `13fa30` tienen condición `0`.
SHA del perfil v14:
`0caa04657cd2cf5f9820c0f10ca2621c1539ab494b17bcdb20274d98100d2085`.
Se guardan 56 estados completos y recibos enlazados: secuencias 1–56 en
`replay-v1/capture-*.json`, slots físicos 34–89 antes libres en `heather-clock-v3`.
La numeración física no los enlaza con la antigua serie V3. No hay restauraciones
ni escrituras del huésped dentro de esta reproducción. El hueco entre las dos
ventanas no se acepta como intervalo de poses ni como transición verificada.

| Comprobación | Correr 113 | Caminar 109 |
|---|---|---|
| Retornos consecutivos / avances por canal | 28 / 27 | 28 / 27 |
| Avance acumulado Q12 | 120258 | 107784 |
| Longitud del ciclo Q12 | 98304 | 98304 |
| Wrap observado | 97988 → 4138 | 95808 → 1496 |
| Incremento por actualización | 4454 | 3992 |
| Error máximo de pose, límite 0,001 | 0,000352961833 | 0,000388989357 |

Ambos canales conservan modo 1 y blend cero. El oráculo independiente coteja
54 poses de 36 matrices usando MDL 522 y ANM 525 fijados, además de los campos
de reloj y los extremos crudos. Error máximo de estos últimos:
`5,960464477539063e-8`, menor que `1e-7`. Usar la fase posterior produce errores
mínimos 25,589093 y 26,010741, respectivamente; los 10 controles negativos de
contador, duplicación, canal, hueco y ticks fallan como corresponde.

El informe de enlace de entrada compara las 56 capturas con el contador nativo
congelado de PCSX2 y los controles del archivo. El delta nativo respecto de
18689 satisface `2 × (ordinal - 81168)` en las dos ventanas. La combinación de
botones coincide en el fotograma indicado y en sus dos vecinos: ↑ + Cuadrado
al correr, ↑ al caminar. Esto acredita entrada estable reproducida; no fija la
latencia exacta de una transición. El original y la copia mantienen su hash.

La primera adquisición guardó correctamente el slot 34, pero el helper falló
al construir el recibo por una variable local reutilizada. Se corrigió el nombre
y se recuperó el recibo desde ese mismo archivo, sin reanudar ni volver a guardar.
Los 56 estados finales y la cadena de recibos pasan la auditoría.

Se cierra **HL-T3c.5**. La sesión queda pausada en la secuencia 56 / slot 89,
PC `1dd434`, ciclo 119757335239, ordinal 81985, contador 57384 en ambos canales.
La reproducción sigue activa en esa pausa; no debe continuarse hasta el final
del archivo sin controlar el posible cambio automático a grabación.
No se acreditan todavía la mezcla sostenida/salida del modo 5, movimiento físico,
colisión, iluminación ni rendimiento de consola. HL-T3, HL-T4 y el nuevo build
multiclips permanecen pendientes en sus respectivos alcances.

### Preparación de la mezcla sostenida

Se detiene la reproducción desde Herramientas, sin reanudar, y la interfaz
confirma «Detener» deshabilitado. El observador coteja de nuevo PC, ciclo, CRC
y los 768 bytes del actor con la captura final: no hubo avance ni restauración.
Los dos archivos de controles conservan su SHA. Recibo `replay-v1/stop.json`.

Se prepara `heather-normal-input-v1/transitions-v1.p2m2` desde esa misma pausa,
sin aceptar aún el diálogo. Los filtros v14 terminan en ordinal 81985 y no
interrumpirán las actualizaciones siguientes de esta sesión. Se solicita la
selección física «Al encender» → «Guardar estado» y comprobar el aviso rojo
antes de aceptar. Después se verificará el nuevo estado inicial y se pedirá una
secuencia de caminar → correr → caminar conservando ↑ durante ambos cambios.
No se acredita todavía esa grabación ni se autoriza tácitamente una nueva
restauración para reproducirla.

Validación de esta continuación: 35 pruebas del repositorio aprobadas y
`git diff --check` sin errores; auditorías privadas de los 56 estados y del
enlace de entrada aprobadas. Se conservan los gates y resultados previos de
los decodificadores sin volver a inferir rendimiento ni validación física.

El usuario realiza la selección física y se verifica visible el aviso de
compatibilidad. Se acepta la grabación `transitions-v1.p2m2`; su estado inicial
tiene SHA `08fed63ed84f4c45d91e2e5140df0c8fd193b8036a70ec824aa471f98de4b99e`.
Se cotejan contra la secuencia 56 / slot 89 PC `1dd434`, ciclo 119757335239,
CRC, los 768 bytes del actor y el banco de entrada. Ambos canales siguen en
modo 1, caminar 109, contador 57384, blend cero; ordinal 81985 y entrada `0x1000`.
El observador confirma la misma pausa. Recibo privado
`transitions-v1-initial.json` y copia local
`reports/local/heather-transitions-v1-initial.json`: acepta solo el ancla inicial,
sin nuevos reinicios, restauraciones ni escrituras del huésped.

Se solicita caminar 3 s con ↑, añadir J durante 3 s y soltar solo J para caminar
otros 3 s, manteniendo ↑ durante los dos cambios; al final, soltar ↑, esperar
1 s y pausar. La grabación está activa y el juego queda pausado a la espera de
esa maniobra. Se validará el archivo cerrado antes de acreditar una transición.

### Recorrido de transiciones preservado, 221

El usuario completa la maniobra y pausa. Se guarda el final en el slot nuevo
221, SHA `4ddbc83b635f03cdd9f4facdb340423f359aaae96325fe4aa20f7c0356032d67`,
PC `81fc0`, ciclo 123040203763, ordinal 82263 y botones cero. Ambos canales
están en espera 101, modo 1, contador 3684 y blend cero. Recibo privado
`transitions-v1-end-221.json`; preserva el final, sin acreditar el intervalo.
Se cierra la grabación desde Herramientas y se verifica «Detener» deshabilitado.

El archivo cerrado tiene 557 fotogramas nativos, cero regrabaciones y origen
guardado; SHA `7e9bd9e9eefe0a803eb8cc09c943f964449ffd8b6f759efed0050bdff24573f8`.
El estado inicial conserva su hash. ↑ permanece pulsada de 24 a 529;
Cuadrado, de 232 a 376. Se registran también giros laterales:
64–142, 317–328, 418–433 y 458–467. Se conserva íntegra esa entrada.
El detector estricto de tres segmentos rectilíneos consecutivos no encuentra
un triple completo; no se cambia ese resultado a una aprobación. Las ventanas
locales alrededor de 232 y 377 sí permiten intentar observar las dos mezclas:
143–231 caminar recto, 232–316 correr recto; 329–376 correr recto,
377–417 caminar recto. Son ventanas candidatas, todavía sin prueba de modo o pose.
Informe `reports/local/heather-transitions-v1-input.json`.

Se prepara una copia verificada en `heather-normal-input-v1/transitions-replay-v1/`
y el plan de 31 estados en slots antes libres 222–252. Filtro v15 en `1dd434`:
ordinales 82100–82114 y 82172–82187; las otras tres direcciones conservan
condición `0`. Perfil SHA
`794e885fd8663458b88758712ea624a7865eeec6f8892b0d94f20ad60b72c369`;
respaldo `breakpoints-before-hlt3-transitions-v15.json`. La estimación basada en
los fotogramas nativos solo guía las ventanas; el capturador exigirá ordinales
consecutivos y el oráculo cotejará los campos del juego. No se acepta el hueco
entre ventanas como secuencia continua de poses.

El código fijado `13fb00–13fbbc` avanza primero el contador en modo 5; cuando
el blend alcanza 4096, limpia la mezcla, copia el descriptor destino al origen
y llama recursivamente al consumidor en modo 1. La hipótesis de reloj prevé
dos incrementos en esa actualización de salida, conservando para su pose la
fase anterior al segundo incremento. Se preparan `transition_clock.py`,
`capture_transition_replay.py` y `audit_transition_replay.py`. Se verifican
22 aristas sintéticas en ambos sentidos, incluidos wrap y salida, y se rechazan
22 contadores alterados. Esto comprueba la implementación de la hipótesis;
su aceptación real sigue pendiente de las capturas, con límite de pose `0,001`.

Al preparar esta reproducción quedan 835.706.880 bytes libres, unos 797 MiB.
Los 31 estados se presupuestan en 496 MiB y el guardado mantiene 512 MiB de
reserva; se solicita liberar 1 GiB adicional. La reproducción no se inicia:
quedan pendientes la carga manual de v15, la confirmación de su nueva frontera
de restauración y el espacio. El final 221 y las grabaciones originales están
preservados; PCSX2 permanece pausado.

### Caminar→correr sostenida, reproducción 1–15

El usuario carga v15 y autoriza reproducir la copia desde su estado inicial.
Se verifican visualmente los cuatro filtros; se abre exclusivamente la copia
`transitions-replay-v1/transitions-v1.p2m2`. El observador coteja PC, ciclo, CRC
y actor con el estado inicial. `start.json` registra la cuarta restauración
desde el lanzamiento y una nueva frontera diagnóstica, sin continuidad con la
serie anterior. No se restauran estados ni se escribe memoria del huésped
entre las muestras de esta reproducción.

Aunque el usuario informa haber liberado espacio, el sistema comunica
861.392.896 bytes libres al iniciar, por debajo de los 1.056.964.608 estimados
para ambas ventanas más reserva. Se solicita 512 MiB adicionales y se avanza
solo con la primera ventana, manteniendo el guardado mínimo de 512 MiB.

Quedan 15 capturas completas en slots nuevos 222–236, ordinales consecutivos
82100–82114. El ancla 1 tiene caminar, contador 96304; la muestra 2 conserva
caminar y hace wrap a 1992. La muestra 3 registra el flanco de Cuadrado y
caminar→correr: contador 6446, ambos canales modo 5, blend 384. Diez
composiciones consecutivas avanzan el blend en 384 hasta 3840, conservando
↑ + Cuadrado. En la muestra 13 ambos canales pasan a modo 1, blend cero y
ambos descriptores de correr. El contador cambia 46532 → 55440, exactamente
dos incrementos de 4454, como predice la llamada recursiva del código fijado.
Las muestras 14 y 15 avanzan normalmente a 59894 y 64348.

El oráculo acepta 14 poses de 36 matrices; error máximo
`0,00036807906838021154 < 0,001`. Rechaza fase posterior, inversión de mezcla
y 43 controles alterados de reloj, incluido omitir el segundo avance al salir.
Informe `heather-transition-replay-15.json`, SHA
`bcf7cbf25a789dee5ac079444f71f5f547295fd511108f43f895362301ef4871`.
El wrap observado es de modo estable antes de la transición; no se acredita
un wrap durante modo 5 ni todavía la transición inversa sostenida.

El auditor de enlace coteja el contador nativo congelado, el ordinal del juego
y los botones en las 15 capturas. El estado inicial tiene contador nativo
20323; cada captura satisface `delta = 2 × (ordinal - 81985)`. Los offsets
de fotograma `-2` y `-1` son compatibles con todos los botones observados,
incluido el flanco: se publica esa ambigüedad sin fijar latencia exacta.
Original y copia conservan su SHA. Informe `heather-transition-binding-15.json`,
SHA `2dcb9b81401bf90a8900dd826e86eedaa88cd08b7d7309c66c6f72fbe272428f`.

PCSX2 queda pausado en la muestra 15 / slot 236, PC `1dd434`, ciclo
121279080715, ordinal 82114, contador 64348 en ambos canales; estado SHA
`9f5f7eac7acadecdd3912f27408d6dd3ac9783104061832bdd55f2f16c0b7022`.
La reproducción permanece activa. Quedan unos 570 MiB libres; se espera el
espacio adicional antes de reanudar hacia la segunda ventana. El siguiente
paso es guardar la secuencia 16 / slot 237 en ordinal 82172 y continuar
consecutivamente hasta 31 / 252, sin otra restauración. HL-T3 sigue abierta.

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_replay.py 15
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_binding.py 15
```

Comprobación final de esta continuación: 35 pruebas del repositorio aprobadas
y `git diff --check` sin errores. No hay nuevo build ARM ni prueba física.

### Inicio de correr→caminar, reproducción 16–19

El usuario solicita continuar hasta donde permita el espacio. Se confirma que
la pausa anterior conserva PC y ciclo de la muestra 15, sin avances ni nuevas
restauraciones. El guardado se hace más conservador: antes de escribir exige
512 MiB de reserva más 16 MiB para la captura siguiente, tamaño previsto a
partir de los estados completos anteriores. No reduce la reserva para avanzar.

Se reanuda la misma reproducción hasta la segunda ventana y se preservan las
muestras 16–19 en slots nuevos 237–240, ordinales consecutivos 82172–82175.
16 y 17 mantienen carrera, con contadores 27768 y 32222; 18 registra la
liberación de Cuadrado mientras ↑ sigue pulsada: ambos canales pasan de
correr 113 a caminar 109, modo 5, contador 36214, blend 384. La muestra 19
mantiene esa entrada, avanza el contador a 40206 y el blend a 768.

El oráculo acepta las tres nuevas poses (avance estable y dos composiciones),
17 en total entre ambas ventanas, con máximo global
`0,00036807906838021154 < 0,001`; rechaza 52 controles alterados de reloj.
Informe `heather-transition-replay-19.json`, SHA
`2e08722370def42a3f83634580c78f3e2b3e7c852796d6d11af968dd9e1d7a07`.
La salida de correr→caminar y el wrap durante modo 5 siguen sin capturarse.

El enlace de entrada también pasa para las 19 muestras. Al incorporar el nuevo
flanco queda únicamente el offset nativo `-1` compatible con este conjunto;
es una relación observada en estas capturas, sin generalizar la latencia del
emulador. Original y copia conservan sus hashes. Informe
`heather-transition-binding-19.json`, SHA
`535acc8b242e363052dc5c9fc71a78eb3cd0da08aae3827ec4948b8d0f62329c`.

Se detiene el avance con 539.303.936 bytes libres (unos 514 MiB), por debajo
de los 553.648.128 necesarios para otra captura más reserva. Recibo privado
`space-stop-after19.json`; PINE confirma PC `1dd434`, ciclo 121998796000 y
pausa. La muestra 19 / slot 240 tiene SHA
`ef917d5416af3fe9628327afc09c91021e319afd264d3372b967954f838b336b`.
La reproducción sigue activa y no se alcanza el final del archivo. Quedan
12 capturas previstas; para retomarlas se requiere espacio y después una
reanudación hasta ordinal 82176, secuencia 20 / slot 241, sin restaurar.
La estimación restante más reserva es 704 MiB; liberar 512 MiB adicionales
ofrece margen para las fluctuaciones observadas del volumen.

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_replay.py 19
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_binding.py 19
```

Se comprueban las nuevas capturas con los dos oráculos y `git diff --check`.
No cambia código de producción; se conservan las 35 pruebas de repositorio
aprobadas en la continuación anterior, sin presentarlas como una ejecución nueva.

### Recuperación separada tras el cierre de PCSX2 — 2026-10-26

Al continuar hay 2,76 GiB libres, pero PINE devuelve `TRANSPORT_IO` y el
inventario de aplicaciones confirma PCSX2 cerrado. La pausa de 19 / slot 240
ya no existe en memoria. No se guarda una supuesta muestra 20 ni se atribuye
continuidad a una sesión reiniciada. Los dos oráculos se ejecutan de nuevo
sobre las 19 capturas: conservan exactamente los hashes y resultados anteriores.

Se prepara un perfil privado independiente `heather-transition-recovery-v2`,
con copia de BIOS, tarjetas y configuración del perfil previo; el ejecutable
sigue fijado por SHA. `transitions-replay-v2` recibe copias verificadas del
registro autorizado y su estado inicial. La nueva ventana comprende ordinales
82172–82187, 16 capturas previstas en slots 1–16 de una carpeta de estados
distinta. El plan declara que la serie anterior termina en 19 y que no existe
continuidad entre ambas. Se mantiene la reserva de 512 MiB más 16 MiB antes
de cada guardado.

La sesión nueva, PID 4114, arranca pausada desde el estado inicial: primera
restauración declarada. El observador de solo lectura coteja PC `1dd434`,
ciclo 119757335239, ordinal 81985 y los bytes de ambos canales contra ese
estado. La tabla del depurador muestra el filtro
`HL-T3-recovery-run-to-walk` y los tres puntos antiguos con condición `0`.
La reproducción nativa todavía no se ha iniciado: al cerrar el depurador,
la ventana del juego oculta los menús y los clics devuelven
`windowNotFoundAtPosition`. Se solicita al usuario dejar visible el menú
Herramientas sin reanudar. La reproducción añadirá otra restauración inicial,
que deberá verificarse y registrarse antes de capturar la nueva ventana.

Los helpers privados separados `capture_transition_recovery.py`,
`audit_transition_recovery.py`, `audit_transition_recovery_binding.py` y
`observe_transition_recovery.py` usan las nuevas rutas y el PID de lanzamiento;
no sustituyen las herramientas ni los informes originales. No cambia código
de producción ni el build físico `8f778b6e4960`.

### Correr→caminar completa en la recuperación independiente

Tras la intervención del usuario vuelve a estar disponible Herramientas.
Se abre la copia `transitions-replay-v2/transitions-v1.p2m2`; la interfaz
confirma la grabación activa y el observador vuelve a verificar el estado
inicial exacto. `start.json` declara dos restauraciones desde el lanzamiento:
una al abrir la sesión y otra al iniciar la reproducción nativa. No hay
restauraciones entre las capturas nuevas.

Se guardan 16 retornos consecutivos en ordinales 82172–82187. La entrada
es la muestra 3, al liberar Cuadrado conservando ↑: origen 113, destino 109,
modo 5 y blend 384. Las muestras 3–12 recorren diez composiciones, hasta
blend 3840; 13 vuelve a modo 1, iguala origen y destino y limpia el blend.
El contador pasa de 72142 a 80126: dos incrementos de 3992 por la salida
recursiva, como anticipa el ejecutable fijado. 14–16 mantienen caminata
estable. Ambos canales coinciden en los campos de reloj, modo y descriptores.

El oráculo independiente reconstruye 15 poses de 36 matrices a partir de
MDL 522 y ANM 525. El máximo es `0,0003650409233841856 < 0,001`, sin elevar
la tolerancia. Se rechazan 46 alteraciones de contador, incremento, siguiente
fotograma y omisión del segundo avance a la salida; también fallan las
hipótesis de fase posterior y mezclas invertidas. No hay wrap dentro de esta
ventana: esa condición de HL-T3c.3 permanece abierta.

El enlace con el registro nativo pasa en las 16 muestras. Los offsets `-1`
y `0` son compatibles con este intervalo; no se impone el `-1` único que
resultaba al combinar otros flancos en la serie anterior. Original, copia y
estado inicial conservan sus SHA. Las cuatro muestras solapadas con las
antiguas 16–19 coinciden en los 32 MiB de RAM EE, ciclos, canales y entrada.
Esta igualdad permite comprobar la reproducción, sin unir las series.

| Informe privado local | SHA-256 |
| --- | --- |
| `heather-transition-recovery-16.json` | `b1e4b94cf2cf890d8f033b6d75625af180a28ff08c6281e828b497e736745a25` |
| `heather-transition-recovery-binding-16.json` | `12643685d51c51a722003271ab3e106562c129076dde6e6e8f9537f9daf22207` |
| `heather-transition-recovery-overlap.json` | `0869f47be03dedfc668c3e9f2f7153f9e63088a91e78f8db3859ce9fdf9134fd` |

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_recovery.py 16
rtk proxy .venv/bin/python build/heather-locomotion/audit_transition_recovery_binding.py 16
```

Se detiene la reproducción desde Herramientas antes del final del registro.
El observador confirma que la pausa conserva PC `1dd434`, ciclo 122140218904
y ordinal 82187. El contador de caminata es 92102: quedan 6202 unidades Q12
antes del reinicio del clip, una ubicación útil para intentar el wrap durante
una nueva transición. Se prepara `wrap-mode5-v1.p2m2`, sin iniciar aún la
grabación. Se pide el clic físico Al encender→Guardar estado para evitar el
fallo conocido del diálogo; no se pulsa OK mientras no se compruebe el modo.
La entrada de usuario y su efecto deberán verificarse, sin dar por observado
el wrap a partir de esta previsión. HL-T3 y HL-T4 siguen abiertas.

### Wrap durante modo 5 y cierre de HL-T3c.3

El usuario activa físicamente Guardar estado y se comprueba el aviso de
compatibilidad. Se inicia `wrap-mode5-v1.p2m2` desde la pausa 16 del perfil
de recuperación, sin reinicio ni restauración. El estado creado coincide
en toda la RAM EE con esa ancla y conserva PC, ciclo, ordinal y contador 92102.
El archivo de controles permanece inicialmente vacío por el buffering del
grabador; su cabecera se valida después de cerrar, sin forzar su escritura.

El usuario mantiene ↑ + J y pausa al terminar. Se preserva su final en el
slot 17, SHA `7e4b19334d3c5d1e110622813d580d3e0a2902403cbe5548f4b1aedf2ea8758b`:
PC `81fc0`, ciclo 122810172403 y ordinal 82243. El registro cerrado contiene
114 fotogramas, cero regrabaciones y `fromSavestate=1`. ↑/Cuadrado permanecen
pulsados desde el primer fotograma; hay giros a derecha en 5–25 y a izquierda
en 45–63, que se conservan sin modificar. SHA del registro:
`a6e735f2989d2ab7a2568295cb3a8ad38b04ef3e08dd7bc722c6c5dd2fc986bb`.
SHA de su estado inicial:
`90cf828e593f4f62043c480266b05971bbbbbe952e1635b0fd4b6c892028f3f6`.

Se prepara `wrap-replay-v1`, el usuario carga `HL-T3-mode5-wrap-window` y
confirma continuar. Se reproduce una copia verificada desde su estado inicial:
tercera restauración desde el lanzamiento del perfil de recuperación y nueva
frontera diagnóstica. El observador confirma el ancla antes de reanudar.
Se preservan 16 muestras en slots nuevos 18–33, ordinales 82187–82202. La
primera es el ancla restaurada; las otras 15 son avances consecutivos sin
restauraciones ni escrituras de memoria. Los originales permanecen intactos.

| Punto | Secuencia | Contador Q12 | Modo / blend |
| --- | --- | --- | --- |
| Ancla caminando | 1 | 92102 | 1 / 0 |
| Entrada hacia correr | 2 | 96556 | 5 / 384 |
| Wrap observado | 3 | 2706 | 5 / 768 |
| Última composición | 11 | 38338 | 5 / 3840 |
| Salida recursiva | 12 | 47246 | 1 / 0 |
| Cuarto avance estable | 16 | 65062 | 1 / 0 |

El oráculo reconstruye las 15 poses de 36 matrices, máximo
`0,0003687840001020959 < 0,001`. En el wrap, la fase anterior es 96556:
extremos 103→80 para caminar y 199→176 para correr, fracción 2348/4096,
blend 768/4096. Su error concreto es `0,0002359500510920043`.
La hipótesis incorrecta de repetir el último fotograma produce error
`46,55631182301962`; también se rechazan omitir el módulo, saturar el
contador y no reiniciar el siguiente fotograma. Son cuatro controles
específicos adicionales a los 46 controles negativos de reloj de la serie.

La vinculación de entrada coteja los 15 avances contra la grabación nativa.
El ancla no se presenta como una nueva muestra de mando. El contador nativo
parte de 20727 y su delta es `2 × (ordinal − 82187)`. ↑ y Cuadrado coinciden
con offsets `-1`, `0` o `1`; no se deduce una latencia exacta. La correspondencia
adicional entre derecha nativa y bit `0x4000` observado solo admite `-1` en
esta traza, y se etiqueta como hipótesis local, no como mapa general de botones.

| Informe privado local | SHA-256 |
| --- | --- |
| `heather-wrap-initial-v1.json` | `443472ee676d4738aa929a72e4ea4aeab24250bcebf6a9884cf22e2c0165e388` |
| `heather-wrap-mode5-input-v1.json` | `1fbd7a32050fb55d253377338da1041290360f8ddcde8683396d0532a2a54b2f` |
| `heather-wrap-replay-16.json` | `49fbe8b878fd19b78e385351177de25bbe7c2658ba2ede91f986620b4ab4afc3` |
| `heather-wrap-binding-16.json` | `af9eb6ebc9a555a5c7465862e9a870cfbb1665467c26493431990130e3cf15d3` |
| `heather-wrap-boundary-v1.json` | `1c03f07d4b442c0ec9b8d78acdd3628af7b137cbda1c1cc8b7d0fc1ec8d5be0d` |

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_wrap_replay.py 16
rtk proxy .venv/bin/python build/heather-locomotion/audit_wrap_binding.py
rtk proxy .venv/bin/python build/heather-locomotion/audit_wrap_boundary.py
```

Se detiene la reproducción por la interfaz antes de su final. PINE confirma
la pausa en PC `1dd434`, ciclo 122317197315, ordinal 82202; recibo `stop.json`.
Quedan unos 1,96 GiB libres. **HL-T3c.3 queda cerrada** para banco 525:
ambos sentidos completos, salida de modo 5 y wrap contrastado. HL-T3 y HL-T4
siguen abiertas. La siguiente verificación es HL-T3c.6: las transiciones
sostenidas con espera, reutilizando el registro `normal-controls-v2.p2m2`.
No cambia el código de producción ni se genera un build físico nuevo.

### Preparación de HL-T3c.6 con los controles existentes

El registro `normal-controls-v2.p2m2` contiene 77 fotogramas sin entrada
(1471–1547), seguidos por 111 con ↑ (1548–1658) y otros 142 sin entrada
(1659–1800). Se utiliza una copia íntegra nueva en
`idle-transitions-replay-v1`, conservando el registro y su estado inicial
fijados. Estos botones permiten proponer las ventanas de observación; no
demuestran por sí solos que las mezclas completen su salida.

El plan reserva ordinales 81940–81963 y 81996–82020, 49 capturas en slots
34–82 de `heather-transition-recovery-v2`. Son dos intervalos separados:
el hueco no se presentará como continuidad de pose. La reserva estimada es
784 MiB para estados más 512 MiB libres; en la preparación hay
2.082.525.184 bytes disponibles. El guardado conserva su control individual
de 528 MiB antes de cada captura.

Se respaldan los filtros anteriores y se prepara
`HL-T3-idle-walk-windows`, SHA
`d12bb605a2a5fa50765ebe9bf4846463b60a1fdde925771ba9f695b56b2b6ec6`.
Los otros tres puntos conservan condición `0`. Los helpers privados
`observe_idle_replay.py` y `capture_idle_replay.py` separan las nuevas rutas,
slots y modos admitidos; su sintaxis se comprueba. La reproducción todavía
no se inicia: se solicita al usuario cargar los ajustes y mantener la pausa.
La restauración prevista será la cuarta desde este lanzamiento y deberá
verificarse antes de guardar nuevas observaciones. Los oráculos de pose,
reloj y entrada de HL-T3c.6 siguen pendientes de esas capturas.

Las auditorías de wrap y sus controles negativos pasan; `git diff --check`
no detecta errores. No se presenta como nueva ejecución la batería de 35
pruebas de repositorio anterior, ni como validación física estas observaciones
de PCSX2.

### HL-T3c.6 — Espera ↔ caminar sostenidas (2026-10-26)

Tras la confirmación del usuario se verifica visualmente
«HL-T3-idle-walk-windows» y las otras tres condiciones `0`. La reproducción
nativa utiliza la copia preparada de `normal-controls-v2.p2m2`. Antes de
avanzar, el observador confirma PID 4114, PC `1dd434`, ciclo 110119712356,
ordinal 81168 y los 224 bytes de ambos canales contra el estado inicial.
`start.json` registra la cuarta restauración desde el lanzamiento de esta
instancia: una al inicio de esta reproducción y ninguna entre sus capturas.
No se modifican registros, selecciones ni memoria guest.

Se guardan las **49 capturas previstas**, slots físicos 34–82 de
`heather-transition-recovery-v2`, con recibos encadenados por SHA-256.
La primera ventana contiene los ordinales 81940–81963; la segunda,
81996–82020. Cada ventana es consecutiva; los 32 ordinales intermedios no
son una traza de pose y no se presentan como tal. La primera petición de
guardado se rechazó porque la reproducción todavía no estaba pausada:
no creó estado ni recibo; se guardó al alcanzar el breakpoint previsto.

| Transición | Ancla / entrada / salida | Reloj observado | Origen conservado |
| --- | --- | --- | --- |
| Espera→caminar | 2 / 3 / 8 | Modo 3: blend 768, 1536, 2304, 3072, 3840; contador 0. Salida modo 1 con contador 3992. | Espera 4→5, fracción 1422/4096; destino muestra 80. |
| Caminar→espera | 26 / 27 / 35 | Modo 3: blend 1280, luego pasos de 360 hasta 3800; contador 0. Salida modo 1 con contador 614. | Caminar 80→81, fracción 2992/4096; destino muestra 0. |

Los valores coinciden en ambos canales. Durante modo 3 el incremento de clip
conserva el valor anterior (614 o 3992), pero no avanza el contador. Al salir,
el consumidor recursivo evalúa la primera pose del destino y realiza un
avance normal. Se verifica por separado del doble avance observado en modo 5.
En espera estable puede persistir el offset de mezcla -460; no debe exigirse
cero fuera de la mezcla. Se conserva el primer rechazo de esa hipótesis en
el registro de ejecución. En el retorno, el primer incremento de blend es
1280 y los siguientes son 360 con offset -460; la ida utiliza 768 y offset 0.

El oráculo reconstruye el origen interpolado con MDL522 y ANM525 originales
y la fase escalar del ancla anterior. Las matrices y los cuaterniones finales
de RAM no se usan como entradas del oráculo. Se cotejan recursos completos,
ocho ventanas de código contra el ELF fijado, PC, ciclos, descriptores,
contador, modo, campos de fotograma, flancos de entrada y ambos canales.

Resultado: **47 poses × 36 matrices**, con máximo absoluto
`0.000415616154214149` frente al límite `0.001`, sin elevar tolerancias.
Son 23 poses comparables en la ida y 24 en el retorno; las dos anclas no
cuentan como avances. Se rechazan **261 controles negativos**: contador,
blend, siguiente fotograma e incremento alterados; uso de fase posterior,
descarte de la fracción del origen, mezcla invertida y omisión de la mezcla.
El límite de extremos crudos 1e-7 permanece intacto; los valores conservados
durante la transición son interpolados.

La auditoría de entrada enlaza los 49 estados con la grabación nativa:
contador inicial 18689 y delta `2 × (ordinal − 81168)`. Entre los offsets
ensayados (-2, -1, 0, 1), solo 0 es compatible con todos los botones,
analógicos y presión de ↑. Es una correspondencia de esta traza, no una
medida general de latencia. El registro original, su copia y sus estados
iniciales mantienen los hashes fijados.

El Mac se bloqueó tras la muestra 47. Después del desbloqueo manual se
verificaron el mismo PC, ciclo 120146306311 y ordinal 82018 antes de continuar:
no hubo avance del guest ni restauración. Las muestras 48–49 completaron
la ventana. Se detuvo la reproducción por la interfaz antes del EOF;
«Detener» quedó desactivado y «Nueva» disponible. El observador cotejó otra
vez ordinal y canales con el estado 82, sin avance: PC `1dd434`, ciclo
120169872011 y ordinal 82020. `stop.json` conserva esa comprobación;
quedaron 1.481.592.832 bytes libres, por encima de la reserva de guardado.

| Informe local | SHA-256 |
| --- | --- |
| `heather-idle-replay-49.json` | `8e037d41c8f5705a446a1413cc615f80b4a8290144a2225d04c00c5eb32d231c` |
| `heather-idle-binding-49.json` | `606a986da52274ef9202955ffd5d821c98d441f3574f9501338e2c169bf7d74c` |

Estado final privado, slot 82:
`d4831eda82f522a2994551394558f590d684aefb76fc691925dfcd358dd559bb`.
Los informes parciales 14, 24, 28, 36 y 47 se conservan; no se sobrescriben.

```sh
rtk proxy .venv/bin/python build/heather-locomotion/audit_idle_replay.py 49
rtk proxy .venv/bin/python build/heather-locomotion/audit_idle_binding.py 49
```

**HL-T3c.6 queda cerrada para espera↔caminar, banco 525 y las ventanas
observadas.** HL-T3b/d y HL-T4 siguen abiertos. La próxima selección que
falta observar directamente es correr→espera al soltar dirección y Cuadrado:
correr→caminar→espera no la sustituye. El informe de cierre deberá fijar
explícitamente esa cobertura y cualquier caso aún no soportado antes del
contrato multiclips.

No se modifica código productivo ni CI en este paso, y no hay build nuevo
para la 2DS XL. Las auditorías privadas anteriores son la validación de esta
entrega; no se atribuye una nueva ejecución a la batería de repositorio
previa. Tampoco se deduce rendimiento físico de las pausas del depurador.

### HL-T3c.7 — Grabación de parada directa (2026-10-26)

El inventario de los tres registros anteriores no contiene un flanco directo
de carrera a reposo: normal-controls-v2 y transitions-v1 pasan por caminata;
wrap-mode5-v1 termina con carrera mantenida. Se explicita HL-T3c.7 para
verificar la selección pendiente y su composición, sin inferirlas del mando.

Se inicia direct-run-idle-v1.p2m2 desde el final de HL-T3c.6 (slot 82).
El usuario activa físicamente el modo Guardar estado y se verifica el aviso
rojo antes de aceptar. PC/ciclo, actor y banco de mando coinciden con el ancla;
no hay reinicio ni nueva restauración. El intento cerrado tiene 227 fotogramas:
↑/Cuadrado en 1–91, solo ↑ en 92–180 y reposo en 181–227.
No acredita la parada directa y se conserva completo, SHA
6fb8fcdf721d6e62102383aac4c75f7f1e88a62bc942d06b78889fa1cec2923d.
Su final se guarda en el slot 83 (PC 81fc0, ciclo 121506661363, ordinal 82133),
SHA 8d4162db37e29654126ac52c36cf1c280a315f6ed5862dbb67a55fabde29568f.

El segundo intento, direct-run-idle-v2.p2m2, empieza en esa misma pausa,
de nuevo con selección física y aviso verificados. El usuario aparta a Heather
de la pared por juego normal antes de la maniobra. La grabación cerrada contiene
1026 fotogramas y cero regrabaciones: tras esa preparación, ↑/Cuadrado en
769–962 (194 fotogramas) y directamente ningún botón en 963–1026 (64).
Los analógicos permanecen centrados. Este flanco sí es candidato a parada
directa; todavía requiere observar la animación seleccionada.

SHA del segundo registro:
6b38fd88089bcaa929cb9c639912d23e676775b00ffa5ab9abcaf29ea44f8f30.
SHA inicial:
78ec5c47ba9e06e59dded0be03569b0f36113b78bedbf826e5f162f05badb65c.
Se cotejan PC 81fc0, ciclo 121506661363, ordinal 82133, contador nativo 20619,
768 bytes de actor, 2880 bytes de entrada y MDL522/ANM525 originales.
Las dos grabaciones no añaden restauraciones: la instancia conserva cuatro.

El segundo final se preserva en slot 84, PC 81fc0, ciclo 127558255603,
ordinal 82646, ambos canales en espera y contador 14736. SHA:
a9bef09037be947b0b257e24f1271c67685661bec61341c8baf64498148e643d.
Se detiene la grabación en la interfaz, verificando Detener deshabilitado.

Se prepara una copia íntegra en direct-run-idle-replay-v1 y se respalda el
archivo de breakpoints. HL-T3-run-idle-window delimita ordinales 82610–82634
en 1dd434, con actor 4481d0; las otras tres condiciones permanecen en 0.
Se reservan 25 capturas, slots 85–109 (400 MiB estimados), manteniendo 512 MiB
libres y el guard de 528 MiB por guardado. Hay 1.470.541.824 bytes al preparar.

El usuario carga los filtros y autoriza reproducir la copia. Tras verificarlos
visualmente, se restaura y coteja el estado inicial exacto antes de avanzar.
start.json registra la quinta restauración histórica, una al inicio de esta
reproducción. No se empalman sus capturas con la sesión manual ni se cambian
selecciones o memoria del guest. HL-T3c.7 sigue pendiente del cotejo de poses.

Informes privados locales de preparación: heather-direct-run-idle-input-inventory-v1,
heather-direct-run-idle-initial-v1, heather-direct-run-idle-input-v1,
heather-direct-run-idle-initial-v2 y heather-direct-run-idle-input-v2.
El primer intento permanece excluido como prueba de parada directa.

### HL-T3c.7 — Parada directa verificada y cierre acotado de HL-T3

La copia autorizada produce 25 retornos consecutivos de 1dd434, ordinales
82610–82634 y slots 85–109. El estado restaurado inicial queda fuera de la
ventana. El archivo original y su copia se conservan intactos; no hay
restauraciones entre muestras ni escrituras a memoria guest.

Las muestras 1–5 son carrera estable 113 en ambos canales. La 2 incluye un
wrap estable del contador (97040→3190). En 6, el flanco de liberación
0x1800→0 selecciona directamente espera 101: +40 conserva origen 113 y +44
contiene destino 101, sin descriptor 109 intermedio. La mezcla modo 3 conserva
contador 0, empieza en 1280 y avanza 360 por evaluación hasta 3800 en 13.
En 14 sale a modo 1, ambos descriptores son 101 y contador 614. Las muestras
15–25 acreditan once avances estables posteriores, hasta contador 7368.

El origen reconstruido procede de la pose anterior de carrera: muestras
178→179 y fracción 3906/4096. Se usan MDL522/ANM525 y la historia escalar;
las matrices y cuaterniones finales de RAM son objetivos de comparación,
no entradas del oráculo. Se cotejan también código fijado, identidad de
recursos, ciclos, ordinales, campos de fase y ambos canales.

Pasan **24 poses × 36 matrices**. Máximo absoluto:
0.00041218335653070426 < 0.001, sin elevar tolerancias.
Se rechazan **136 controles negativos** de contador, blend, incremento,
siguiente fotograma, fase posterior, fracción omitida, mezcla invertida
y origen sin mezcla. El origen interpolado no sustituye ni relaja el
gate de extremos crudos 1e-7.

El enlace de entrada verifica los 25 estados frente al registro de 1026
fotogramas. El contador nativo inicial es 20619 y delta = 2 × (ordinal−82133).
Los offsets -1 y 0 son compatibles con todos los botones, presiones y
analógicos de la ventana; no se infiere una latencia única o general.

| Informe local | SHA-256 |
| --- | --- |
| heather-direct-run-idle-replay-25.json | 1e213643d85d9a39450abc2d2969cb265c9a429dc435d7dcc68fcbbfd88eba41 |
| heather-direct-run-idle-binding-25.json | 5e45de9d2706247ab973ee86b74e6d3d677d53fa0e4c2bbbff64f5672c25717e |
| heather-hl3-closure-v1.json | 403a586353d64cde11d79b38235032cdb157c7defdbd718a2a267c09fa3ce8e9 |

Comandos reproducibles de esta entrega:
- rtk proxy .venv/bin/python build/heather-locomotion/audit_run_idle_replay.py 25
- rtk proxy .venv/bin/python build/heather-locomotion/audit_run_idle_binding.py 25
- rtk proxy .venv/bin/python build/heather-locomotion/audit_hl3_closure.py

La reproducción se detiene antes del EOF y se verifica Detener deshabilitado.
El observador coteja ordinal y canales con slot 109 sin avance: PC 1dd434,
ciclo 127412972873, ordinal 82634. SHA del estado final:
659de44cd906bdc3ff9f4650d6eb5c0b9284554441ee8d40a42d0e07ffdbcd6c.
stop.json conserva cinco restauraciones históricas, cero entre capturas,
archivos intactos y 1.036.791.808 bytes libres. PCSX2 queda pausado.

**HL-T3b/c/d y HL-T3 quedan cerradas en el perfil observado del banco 525.**
El nuevo informe consolida 16 evidencias existentes mediante sus hashes,
umbrales, descriptores, continuidad interna y resultados de entrada. Esa
consolidación no se presenta como repetición de todas las auditorías crudas
anteriores. Los informes históricos con hl_t3_complete falso se conservan
inalterados; el cierre acotado reside en el nuevo manifiesto.

| Selección cubierta | Evidencia de secuencia |
| --- | --- |
| Espera→caminar | idle-transitions-replay-v1, entrada 3 y salida 8 |
| Caminar→espera | idle-transitions-replay-v1, entrada 27 y salida 35 |
| Caminar→correr | transitions-replay-v1, entrada 3 y salida 13 |
| Correr→caminar | transitions-replay-v2, entrada 3 y salida 13 |
| Correr→espera directa | direct-run-idle-replay-v1, entrada 6 y salida 14 |

El cierre incluye vueltas completas de espera/caminar/correr, modo 5 con wrap
y salida recursiva, y los casos fijados de origen conservado e interrupción.
Las series no se empalman como un solo recorrido continuo. La traslación
mundial se conserva por separado con posiciones iniciales/finales y delta
observado; no acredita una ley de desplazamiento, root motion ni colisiones.
Espera→correr directa, otros bancos/armas y otras interrupciones quedan fuera
del perfil aceptado y deberán tratarse explícitamente en el contrato.

Sigue **HL-T4a**, contrato multiclips y de transición, seguido por núcleo puro,
conversión A/B y gates de integración. No cambia código productivo, CI ni el
último build físico de Heather. La batería histórica del repositorio no se
presenta como ejecutada nuevamente; esta entrega valida los oráculos privados,
la consolidación y la consistencia documental.

### HL-T4a — Contrato multiclips y vectores independientes

2026-10-26. Se completa el
[contrato HLC01–HLC16](../../schemas/heather-locomotion-v1.md) antes de
implementar el núcleo. Fija MDL522/ANM525, descriptores PAL 101/109/113,
los rangos 0–9/80–103/176–199 y su correspondencia con 58 muestras compactas.
Las máscaras de 15/21 huesos se toman de los informes de preludio ya
verificados y se publican juntas; no se extrapolan canales de otros bancos.

Se separan contador devuelto y fase de pose. Modo 5 mezcla extremos de
clips antes de interpolar tiempo y sale con doble avance; modo 3 conserva
la última pose local, mantiene contador cero durante la mezcla y sale con
un avance. Espera→correr directa y nuevas selecciones durante mezcla dan
error explícito. La interrupción parcial de HL-T3c.4 sigue como diagnóstico,
sin anunciar soporte completo de interrupciones en el visor.

La nueva versión SRI2 conserva malla/materiales compartidos, añade vínculos
de canal y tres descriptores, sin reinterpretar el SRI1 físico existente.
Su tamaño previsto de 290156 bytes es un cálculo del layout, no un archivo
privado generado. Las políticas de pausa, paso, reinicio, solicitudes y
tapa/HOME son decisiones de inspección identificadas aparte de la evidencia
del juego. La planificación separa reloj, lectura, pose, publicación atómica,
conversión, oráculo y presentación; detalla HL-T4b.1–3, T4c.1–3 y T4d.1–2.

Se publican [vectores propios](../../tests/fixtures/synthetic/heather-locomotion-v1.json)
y [30 comprobaciones](../../tests/python/test_heather_locomotion_contract.py)
sin importar código productivo ni oráculos privados. Usan aritmética racional
para reloj/traslación y Decimal de 60 dígitos para rotaciones inventadas:

- Descriptores little endian, cobertura compacta y wrap dentro de cada clip.
- Doce casos de reloj, secuencias completas de ambos sentidos de modo 5,
  tres secuencias modo 3 y avances suficientes para una vuelta por clip.
- Orden de NLERP, caché interpolada, hemisferio, composición entre canales
  y diagnóstico de interrupción. El control de orden incorrecto difiere
  más de 0,03 en un componente del quaternion sintético.
- Tamaños y offsets de cabecera/descriptores SRI2, sin presentarlo como
  prueba de un encoder/lector aún no implementado.

SHA256 del fixture:
`2a1e3044555e9c3e46c7e3cbdd32657dfa98efa15d4b18f7befa3671b5c3f004`.

Validación local:

```text
rtk proxy .venv/bin/pytest -q tests/python/test_heather_locomotion_contract.py tests/python/test_animation_descriptors.py tests/python/test_animation_precision.py tests/python/test_animation_continuity.py tests/python/test_heather_animation.py tests/python/test_rig_inspection.py
190 passed in 4.39s
rtk proxy .venv/bin/ruff check tests/python/test_heather_locomotion_contract.py
All checks passed!
rtk proxy .venv/bin/ruff format --check tests/python/test_heather_locomotion_contract.py
1 file already formatted
rtk proxy .venv/bin/python -m tools.qa.check_repository
Repository checks: PASS (0 errors)
rtk proxy git diff --check
sin errores
```

El job Python existente descubre estas pruebas; no se ha ejecutado CI remoto
ni creado un gate de cobertura de un módulo inexistente. Los casos de fallos
atómicos, lifecycle, corrupción de paquetes y límites de memoria quedan
como aceptación obligatoria de las tareas de implementación, no aprobados
por esta comprobación matemática.

**HL-T4a cerrada; siguiente: HL-T4b.1, planificador escalar puro.** No se
operó PCSX2 ni se tomaron nuevas capturas. El código productivo y el último
build físico 8f778b6e4960 permanecen sin cambios en esta entrega.

### HL-T4b.1 — Planificador escalar puro implementado

2026-10-26. Se implementan
[los tipos de perfil/estado/plan](../../engine/domain/include/sh3/domain/locomotion_clock.hpp)
y [el planificador](../../engine/domain/locomotion_clock.cpp), conforme a
HLC03–07 y la separación de responsabilidades de HLC14.

El módulo valida la tabla PAL fijada antes de hacer aritmética; recibe estado,
solicitud opcional y ticks. Rechaza un perfil alterado, estados inconsistentes,
ticks distintos de 2, IDs desconocidos, nuevas selecciones durante mezcla y
espera→correr directa, en ese orden. La solicitud vacía continúa y repetir el
destino no reinicia. Usa intermedios uint64 y publica el plan solo al completar;
un error conserva byte por byte la salida anterior.

La salida distingue contador siguiente de fase evaluada, las tres clases de
evaluación y las acciones de caché. Las cinco transiciones usan sus secuencias
de beta fijadas. Modo 5 conserva fase relativa, aplica incremento del destino
y en su salida evalúa entre los dos avances. Modo 3 pide congelar la última
pose al entrar, no vuelve a congelarla al continuar y descarta la caché al
salir, con contador avanzado una sola vez. Sus ventanas separan índices
relativos, originales ANM y compactados, incluido wrap dentro del clip.

Este módulo no lee muestras ni evalúa rotaciones. La bandera de caché es una
precondición escalar; HL-T4b.2–3 deben validar su contenido y publicar el reloj
solo después de completar la pose de ambos canales. No se conecta aún al
presentador ni se interpreta SRI2 como un SRI1 de 58 frames.

Pruebas nuevas:

- [Batería C++](../../tests/cpp/test_locomotion_clock.cpp): todas las entradas
  y betas, no-op, salida de modos 3/5, límites de fase, enteros extremos,
  estados/perfiles inválidos, precedencia de errores, salida intacta y entrada
  que comparte almacenamiento con el próximo estado. Se prohíben `new/new[]`
  durante la batería escalar. Estado 28 bytes y plan 104 bytes en host;
  el presupuesto de poses/scratch completo sigue pendiente.
- [Oráculo nativo](../../tests/locomotion_clock_oracle.py): **173 updates**
  cotejados contra el fixture ya fijado: 12 casos puntuales, 22 retornos de
  modo 5, 24 de modo 3 y 115 avances de ciclos completos. Compara todos los
  campos de salida, sin importar módulos productivos o recursos privados.
- Las 30 comprobaciones matemáticas del fixture siguen aprobadas. Su SHA
  permanece `2a1e3044555e9c3e46c7e3cbdd32657dfa98efa15d4b18f7befa3671b5c3f004`.

Validación local ejecutada:

```text
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_locomotion_clock --parallel 2
rtk proxy ctest --preset host-release -R '^locomotion_clock' --output-on-failure
2/2 aprobadas
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_locomotion_clock --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^locomotion_clock' --output-on-failure
2/2 aprobadas, ASan/UBSan sin hallazgos
rtk proxy .venv/bin/pytest -q tests/python/test_heather_locomotion_contract.py
30 passed in 0.05s
rtk proxy .venv/bin/ruff check tests/locomotion_clock_oracle.py tests/python/test_heather_locomotion_contract.py
All checks passed!
rtk proxy .venv/bin/ruff format --check tests/locomotion_clock_oracle.py tests/python/test_heather_locomotion_contract.py
2 files already formatted
```

Cobertura local separada con LLVM: compilación de las dos unidades C++ con
`-fprofile-instr-generate -fcoverage-mapping`, SDK retornado por
`xcrun --show-sdk-path`, ejecución de batería/oráculo, merge de ambos perfiles
y `llvm-cov report` limitado a `engine/domain/locomotion_clock.cpp`.
**123/123 líneas, 136/136 ramas y 10/10 funciones (100 %)**. Binario y perfiles
quedan en `build/heather-locomotion/clock-coverage/`, fuera de Git.
El intento inicial de compilación directa refería un SDK eliminado; se corrigió
pasando el sysroot de Xcode sin cambiar flags de advertencias ni el módulo.

CTest incorpora las dos pruebas a las matrices existentes. CI añade lint del
adaptador y el gate individual [gcovr-locomotion-clock.cfg](../../gcovr-locomotion-clock.cfg)
con mínimos de 80 % de líneas/ramas, además del gate agregado. La medición
local es LLVM; no se afirma haber ejecutado GCC/gcovr o CI remoto en esta entrega.
No se repite aquí toda la batería histórica ni el build ARM, pues aún no hay
consumidor del planificador en el visor.

**HL-T4b.1 cerrada. Sigue HL-T4b.2: evaluar y conservar poses locales usando
el plan.** HL-T4b completa, conversión A/B, integración y validación física
siguen pendientes. No se opera PCSX2 ni se genera un paquete nuevo para SD.

## 2026-10-26 — HL-T4b.2: poses locales y origen congelado

Implementados [los tipos y el lector inmutable](../../engine/domain/include/sh3/domain/locomotion_pose.hpp)
y [el evaluador puro](../../engine/domain/locomotion_pose.cpp), conforme a
HLC05–06/08–09 y a la separación de HLC14. Se reutiliza el planificador
escalar y se mantienen sin cambios el lector y la evaluación SRI1.

El lector recibe clip, índice relativo y hueso compacto, y devuelve TR o
`sample_unavailable`. El esqueleto aporta padres topológicos y un único
canal propietario por hueso. Valida estructura y capacidad hasta 73 huesos;
el mapa original de 36 y su identidad privada se verificarán en HL-T4c.
Los rigs inventados pequeños permiten comprobar la matemática sin recursos
del juego. No hay acceso a archivos, reloj de pared, SDK ni PCSX2.

La inicialización produce espera[0] sin avance de reloj. Durante una
actualización, NLERP normaliza cada mezcla y elige el hemisferio con dot<0;
dot=0 conserva el signo. Traslaciones usan LERP. Modo 5 mezcla primero los
extremos entre clips y después el tiempo. Modo 3 captura la última pose local
ya interpolada, lee solo destino[0] y conserva el origen congelado en cada
actualización. Al salir invalida la caché; no reutiliza sus bytes inactivos.

Los dos canales se evalúan completos en orden 2/1 antes de componer matrices
`parent * local`, sin interpolarlas ni añadir desplazamiento mundial. Las
lecturas y la caché se validan por finitud, límites y norma; los valores
inválidos no se reemplazan por identidad.

**Límite de esta entrega:** `stage_locomotion_pose` produce un candidato en
scratch, nunca publica reloj/salida runtime. Conserva el estado de entrada,
pero un error puede dejar scratch parcial: debe descartarse. La entrada no
puede compartir almacenamiento con `scratch.next`. HL-T4b.3 implementará la
transacción que valida la relación reloj/caché, evalúa y publica todos sus
resultados solo al completar. El visor todavía no consume esta API.

Verificación sintética:

- [Batería nativa](../../tests/cpp/test_locomotion_pose.cpp): inicialización,
  primer frame sin avance, wrap por clip, cinco transiciones, lectura de un
  solo frame en modo 3, cacheado interpolado y congelación byte por byte,
  hemisferios opuestos/dot cero, padre del canal 1 con hijo del 2 y cambio de
  padre visible en la misma actualización. También capacidades/jerarquías,
  canales y planes inválidos, NaN/Inf/cero, caché corrupta, falta de muestras,
  alias rechazado y entrada intacta. `new/new[]` abortan durante la batería.
- [Oráculo independiente](../../tests/locomotion_pose_oracle.py): **26 poses
  en nueve escenarios**, mediante los literales del fixture previo y Decimal
  a 60 dígitos. Comprueba modo 5 frente al orden incorrecto, parada con caché,
  hemisferio, matriz del hijo, wrap de tres clips y ambas salidas de modo 5.
  Tolerancia local TR/cuaterniones 1e-6; matriz sintética del hijo 4e-6.
  No modifica el límite de fidelidad privada de matrices (0,001).
- Las **30 pruebas** matemáticas del contrato siguen aprobadas. No se habilita
  la interrupción de mezcla observada solo parcialmente ni espera→correr.
- Caché **4096 bytes**, scratch **8768 bytes** en host. El presupuesto del
  futuro estado transaccional completo y la batería exhaustiva de errores
  siguen en HL-T4b.3.

Validación local:

```text
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_locomotion_pose test_locomotion_clock --parallel 2
rtk proxy ctest --preset host-release -R '^locomotion_' --output-on-failure
4/4 aprobadas (baterías y oráculos de reloj/pose)
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_locomotion_pose test_locomotion_clock --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^locomotion_' --output-on-failure
4/4 aprobadas, ASan/UBSan sin hallazgos
rtk proxy .venv/bin/pytest -q tests/python/test_heather_locomotion_contract.py
30 aprobadas
```

Cobertura separada LLVM con instrumentación nativa y las dos pruebas de pose:
**185/192 líneas (96,35 %), 160/182 ramas (87,91 %), 14/14 funciones**.
Binario/perfiles locales: `build/heather-locomotion/pose-coverage/`, ignorados.
CTest añade batería y oráculo a los presets existentes; CI añade lint/formato
del oráculo y el [gate individual GCC](../../gcovr-locomotion-pose.cfg), con
80 % mínimo de líneas y ramas. Ruff y comprobaciones del repositorio pasan.
No se afirma ejecución remota de CI/GCC ni se compila ARM en este paso puro.

**HL-T4b.2 cerrada. Siguiente: HL-T4b.3, publicación conjunta, fallos y límites
del núcleo completo.** Conversión privada A/B, lector SRI2, integración al
visor y ensayo físico multiclips siguen pendientes. No se modifica la sesión
PCSX2 ni se crea un build nuevo para la SD.

## 2026-10-26 — HL-T4b.3: publicación conjunta, fallos y límites

Implementados [LocomotionState y LocomotionWorkspace](../../engine/domain/include/sh3/domain/locomotion_update.hpp)
y [las operaciones completas](../../engine/domain/locomotion_update.cpp) de
inicialización y actualización. HLC07–09/14: el estado publicado agrupa reloj,
topología propia, caché de poses locales y matrices modelo. Usa el planificador
y el evaluador existentes; no duplica la máquina de transiciones ni el lector.

La inicialización prepara espera[0] sin avanzar y solo reemplaza un estado
anterior si termina correctamente. La actualización valida perfil, topología,
cantidades/banderas y relación entre reloj y caché; planifica y evalúa en el
workspace. Las matrices vigentes deben ser finitas y afines. Todas las
operaciones que pueden fallar y todos los callbacks de lectura terminan
antes de copiar reloj, caché y matrices al estado. Las posiciones de matrices
inactivas se limpian para no publicar residuos de un workspace reutilizado.

Un error conserva **todos los bytes del estado**. El candidato parcial queda
solo en workspace y puede descartarse; un reintento con datos disponibles
produce el mismo resultado que una actualización sin interrupción. Esta
publicación conjunta es síncrona, en el hilo propietario; no añade exclusión
mutua ni permite observar copias intermedias desde otros hilos.

La batería ampliada hizo explícita una prioridad ya fijada por el contrato:
`sample_unavailable` debe prevalecer sobre `invalid_pose`, incluso si el valor
inválido aparece primero. Se ajustó el evaluador para continuar las lecturas
requeridas después de detectar una pose/caché inválida y rechazar la falta
posterior, sin interpolar datos rechazados. No se añaden buffers grandes ni
se vuelven a leer las muestras; los errores escalares siguen precediendo a
toda lectura. La validación escalar del perfil se comparte con la inicialización.

Pruebas nuevas y ampliadas:

- [Batería transaccional](../../tests/cpp/test_locomotion_update.cpp): **3013
  casos rechazados**, **3111 actualizaciones válidas/reintentos**. Recorre
  los cinco arcos, todas sus betas y salidas y vueltas de los tres clips.
  Inyecta ausencia o quaternion cero en cada lectura de cada paso, incluidos
  ambos canales. Cada callback comprueba que sigue visible el estado anterior;
  cada error compara todos sus bytes, y cada recuperación se coteja con una
  actualización sin fallo.
- Casos adicionales: NaN/Inf en TR y matrices, norma/componentes fuera de
  contrato, caché congelada corrupta, matriz no afín, máscaras/cantidades y
  padres inválidos, estado sin inicializar, ticks/IDs/modos y prioridades
  entre errores. Inicialización con fallos en las 73 lecturas; capacidad 0,
  74 y uint32 máximo rechazadas; actualización con 73 huesos y reinicialización
  a uno. La topología de entrada puede cambiar después de inicializar sin
  alterar la copia del estado. Scratch con matrices inactivas inválidas no
  contamina la publicación.
- [Oráculo de transacción](../../tests/locomotion_update_oracle.py): **410
  snapshots completos**, incluidos errores de selección/ticks y continuación.
  Usa las tablas PAL/beta del fixture, muestras inventadas, NLERP Decimal
  independiente y productos de cuaterniones sobre ejes para las matrices.
  Compara reloj, poses locales, origen congelado y matrices en cada retorno.
  Máximo local **7,48212291e-8**, máximo modelo **5,89661063e-7**, frente a
  tolerancias 1e-6/4e-6. El umbral privado 0,001 sigue sin cambiar.

Presupuesto medido en host:

| Almacenamiento | Bytes |
|---|---:|
| Estado: reloj + topología + caché + matrices | 9168 |
| Workspace: plan + candidato de pose | 8872 |
| Total | **18040** |
| Límite comprobado por `static_assert` | **32768** |

No se duplican muestras/malla/texturas dentro de esos objetos. El código de
dominio no asigna memoria dinámica; la batería aborta ante `new/new[]`,
incluidas sus versiones alineadas. Los objetos serán persistentes en el
presentador; las operaciones no crean copias automáticas del estado completo.

Validación local ejecutada:

```text
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_locomotion_update test_locomotion_pose test_locomotion_clock --parallel 2
rtk proxy cmake --build --preset host-release --target test_inspection_rig test_rig_draw_equivalence test_ctr_rig --parallel 2
rtk proxy ctest --preset host-release -R '^(locomotion_|inspection_rig$|rig_)' --output-on-failure
31/31 aprobadas
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_locomotion_update test_locomotion_pose test_locomotion_clock --parallel 2
rtk proxy cmake --build --preset host-sanitize --target test_inspection_rig test_rig_draw_equivalence test_ctr_rig --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(locomotion_|inspection_rig$|rig_)' --output-on-failure
31/31 aprobadas, ASan/UBSan sin hallazgos
rtk proxy .venv/bin/pytest -q tests/python/test_heather_locomotion_contract.py
30 aprobadas
```

Las 31 incluyen seis pruebas de locomoción y 25 regresiones SRI1: lector,
presentador, equivalencia de skinning/ordenación y contratos GPU contra dobles
del SDK. No acreditan uso físico del nuevo núcleo. Se mantienen los oráculos
anteriores de 173 planes y 26 poses y el fixture sintético sin modificar.

Cobertura local LLVM combinando las seis pruebas de locomoción:

| Módulo | Líneas | Ramas |
|---|---:|---:|
| `locomotion_clock.cpp` | 123/123, 100 % | 136/136, 100 % |
| `locomotion_pose.cpp` | 199/203, 98,03 % | 176/196, 89,80 % |
| `locomotion_update.cpp` | 48/48, 100 % | 36/36, 100 % |

Binarios, perfiles y `coverage.txt` en
`build/heather-locomotion/update-coverage/`, ignorados. CTest incorpora
batería/oráculo, CI añade lint/formato del adaptador y el
[gate individual transaccional](../../gcovr-locomotion-update.cfg) al 80 %,
además de los gates separados de reloj y pose. Ruff, formato, revisión de
whitespace y comprobaciones del repositorio pasan. No se afirma ejecución
remota de CI/GCC ni compilación ARM en este paso.

**HL-T4b.3 y HL-T4b cerradas. Siguiente: HL-T4c.1, productor SRI2**, para
empaquetar los tres clips y conservar mapa/canales/descriptores. Lector,
cotejo privado A/B, integración al visor y nueva prueba en 2DS XL siguen
pendientes. No se opera PCSX2 ni se entrega un nuevo build de consola aquí.

## 2026-10-26 — HL-T4c.1: productor SRI2 y correspondencias

Implementado el productor en memoria para los clips 101/109/113 del perfil
original PAL. Cumple la parte de producción de HLC01–02/13: extrae 0–9,
80–103 y 176–199 en 58 posiciones consecutivas; conserva los doce bytes de
cada descriptor PAL, sin convertir otra vez sus velocidades. El mapa ordenado
de 36 huesos y los canales 1/2 deben coincidir exactamente con el contrato.
Los padres y los destinos de los 49 helpers se remapean sin cambiar jerarquía.

Responsabilidades:

- [Entrada de fuentes](../../tools/pipeline/produce_heather_locomotion.py):
  `produce_heather_locomotion` limita tipo/tamaño, calcula hashes de los bytes
  MDL522/ANM525 y exige los pines existentes. Verifica descriptores antes de
  decodificar. Deriva de nuevo geometría, muestras y texturas con los decoders
  completos, conservando RGBA PS2 sin normalizar alfa. Los hashes declarados
  por un llamador no sirven para autenticar documentos alterados.
- [Reductor y encoder](../../tools/pipeline/locomotion_inspection.py): separa
  la reducción de intermedios y el layout binario. La entrada de intermedios
  sirve también para pruebas propias y declara `source_verified=false`;
  solamente la entrada autenticada añade `sources` y confirma su cotejo.
- [Preparación común](../../tools/pipeline/rig_inspection.py): recibe índices
  explícitos de muestra, calcula un único centro desde espera[0] y un radio
  conservador sobre todas las muestras elegidas. Comparte geometría, texturas
  y validación de secciones SRI con la versión anterior. No se genera ni se
  reinterpreta un SRI1 de 58 muestras.

El resultado contiene `heather.sri`, trece texturas numeradas y un recibo
serializable a JSON. El recibo conserva cada muestra fuente/empaquetada,
hueso/padre/canal, helper/destino, submalla/rangos de vértices e índices y
textura/material; incluye descriptores crudos en hexadecimal, centro/escala,
radio, tamaños y SHA256 de todos los archivos. La entrada autenticada añade
hashes/tamaños de ambas fuentes. No introduce rutas ni timestamps. Registra
como excluidos los datos no seleccionados, morphs, movimiento mundial, arma
visible e iluminación PS2. Las fuentes completas siguen siendo responsabilidad
del intermedio privado conservado; SRI2 no permite reconstruir todo MDL/ANM.

La cabecera de 96 bytes, el mapa `<HBB>` y los tres registros
`<HHhHHBBII>` se escriben en el orden fijado, con reservados cero y CRC32
del payload. El ejemplo sintético con B36/F58/H49/V6943/I16566/M13 ocupa
**290156 bytes**, frente a los 241536 del ejemplo SRI1. La malla y sus
materiales se escriben una sola vez; las texturas se comparten entre clips.
Ninguna función escribe en disco o publica un resultado parcial.

Validación local:

- [Pruebas SRI2](../../tests/python/test_locomotion_inspection.py): lectura
  directa de cabecera/secciones con `struct`, literales independientes de
  las tablas productivas, 2088 transformaciones locales (58×36), todos los
  vértices/índices y las correspondencias de helpers/materiales. Los extremos
  sintéticos se cotejan con error absoluto ≤1e-7. Comprueba determinismo,
  entradas intactas, centro común y radio que incluye correr. Pistas fuera
  de selección y una submalla oculta no contaminan el resultado.
- Cada uno de los 36 bytes PAL alterado se rechaza; también orden/tamaño/tipo
  de descriptores, mapas duplicados/reordenados, canales incorrectos, booleanos
  usados como índices, padre ausente/adelantado, pistas desordenadas en los
  seis extremos, NaN/Inf, quaternion inválido, pesos, helpers, materiales,
  texturas ausentes/truncadas/mutables y documentos incompatibles. Se aceptan
  límites estructurales: cero/128 helpers, 3/8192 vértices, 3/18000 índices,
  1/16 materiales, un/tres pesos y el presupuesto exacto de 8 Mpíxeles.
- [Pruebas de fuentes](../../tests/python/test_produce_heather_locomotion.py):
  tamaño/tipo/SHA y descriptores se rechazan antes de llamar al decoder. El
  adaptador real procesa una pareja MDL/ANM inventada, conserva su RGBA y su
  representación JSON; el perfil Heather rechaza ese otro modelo. La prueba
  de coordinación exitosa sustituye pines y decodificación con `monkeypatch`
  exclusivamente dentro del test, sin opción productiva para omitir hashes.
  No se presenta esa simulación como autenticación privada real.
- Regresión SRI1: los dos ejemplos anteriores mantienen exactamente sus
  SHA256 (`1d14965d…b5c9fd` y `43f1f854…c6d68a`); pasan lector nativo,
  rechazos sin publicación, poses y empaquetado existentes.

Batería ejecutada: **435 pruebas aprobadas** en 12 archivos, incluidos
contrato de locomoción, SRI1/SRI2, animación Heather, MDL/ANM, morphs,
texturas indexadas, descriptores y precisión. Ruff, formato, whitespace y
comprobaciones del repositorio pasan.

```text
rtk proxy .venv/bin/pytest -q tests/python/test_locomotion_inspection.py tests/python/test_produce_heather_locomotion.py tests/python/test_rig_inspection.py tests/python/test_heather_locomotion_contract.py tests/python/test_heather_animation.py tests/python/test_skeleton_animation.py tests/python/test_morph_character_conversion.py tests/python/test_character_morphs.py tests/python/test_morph_materials.py tests/python/test_indexed_selectors.py tests/python/test_animation_descriptors.py tests/python/test_animation_precision.py --cov=tools.pipeline.locomotion_inspection --cov=tools.pipeline.produce_heather_locomotion --cov=tools.pipeline.rig_inspection --cov-report=json:build/heather-locomotion/sri2-coverage.json --cov-report=term-missing --junitxml=build/heather-locomotion/sri2-pytest.xml
435 passed
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-locomotion/sri2-coverage.json --files tools/pipeline/locomotion_inspection.py tools/pipeline/produce_heather_locomotion.py tools/pipeline/rig_inspection.py
Line/branch coverage gate: PASS
```

| Módulo | Líneas | Ramas |
|---|---:|---:|
| `locomotion_inspection.py` | 57/57, 100 % | 12/12, 100 % |
| `produce_heather_locomotion.py` | 32/32, 100 % | 8/8, 100 % |
| `rig_inspection.py` | 150/150, 100 % | 80/80, 100 % |

CI incorpora gates individuales al 80 % para los dos módulos nuevos,
comprobados por un test de configuración. Informes locales ignorados en
`build/heather-locomotion/sri2-coverage.json` y `sri2-pytest.xml`.
No se afirma ejecución remota de CI ni nueva compilación ARM.

**HL-T4c.1 cerrada. Siguiente: HL-T4c.2, lector SRI2 y reconstrucción
independiente**, con truncamientos, CRC, reservados y publicación atómica.
El cotejo/publicación privada A/B (HL-T4c.3), la integración y la prueba
física multiclips siguen pendientes. No se modifican capturas PCSX2 ni el
paquete instalado en la SD.

## 2026-10-26 — HL-T4c.2: lector SRI2, reconstrucción y publicación atómica

Implementados el [modelo y la vista inmutable](../../engine/domain/include/sh3/domain/inspection_locomotion.hpp),
el [lector de plataforma](../../engine/platform/common/inspection_locomotion.cpp)
y el [reconstructor independiente](../../tools/qa/locomotion_rig_oracle.py).
Cubren HLC13–14 y preparan el cotejo privado de HLC15, que sigue pendiente.

`InspectionLocomotion` conserva el perfil PAL, frecuencia, mapa de huesos,
canales y secciones compartidas de capacidad fija. Reutiliza almacenamiento
`InspectionRig` con sus campos de reloj legacy en cero; no es un SRI1 válido
ni se evalúa mediante `evaluate_rig`. `InspectionLocomotionReader` entrega TR
por ID de clip, frame relativo y hueso compacto. Un índice posterior al último
frame se rechaza aunque exista físicamente el siguiente bloque: el wrap sigue
siendo responsabilidad del núcleo y permanece dentro del mismo clip.

`read_locomotion_rig` comprueba cabecera, cantidades, identidad y longitud
esperada antes de asignar el payload. Exige lectura completa, ausencia de
bytes sobrantes y CRC correcto; después valida reservados, descriptores PAL,
mapa/canales, padres, TR, helpers, vértices, pesos, índices, rangos de materiales
y presupuesto de texturas. La validación numérica y de geometría se comparte
con SRI1 mediante `rig_payload_error`; su validación de reloj se conserva aparte.

`read_locomotion_bundle` carga `heather.sri` y verifica todas las texturas
referidas con un buffer reutilizado de **64 KiB** y CRC incremental. Exige
tamaño exacto, incluida lectura de EOF, y cierre correcto de cada archivo.
No conserva ni sube los píxeles; la carga GPU posterior deberá comprobar los
bytes que use. El directorio puede contener archivos auxiliares que el lector
no abre. El auditor de paquetes en memoria exige el conjunto exacto SRI/RGBA.

Ambas APIs preparan un candidato privado y copian a la salida solo después
de terminar todas las comprobaciones y cierres. En error conservan **todos
los bytes del modelo vigente**. Los diagnósticos incluyen `FileError`, nombre
estático del campo y ordinal para texturas. Se conserva el primer error ante
un cierre posterior fallido. Es una transacción síncrona en el hilo propietario;
no constituye publicación concurrente ni cambia la sesión de PCSX2.

El modelo ocupa **389640 bytes en host**. El mayor payload admitido ocupa
333356 bytes; el staging propio máximo durante la carga SRI es, por tanto,
722996 bytes dinámicos, además del modelo vigente y los buffers internos de
stdio. Una vez leído/cerrado SRI, el payload se libera antes de comprobar RGBA.
La vista no asigna memoria por lectura. El presupuesto de 18040 bytes del
estado/workspace de HL-T4b permanece separado y sin cambios.

El oráculo Python importa solo `math`, `struct` y `zlib`; no importa productor
ni runtime. Reconstruye perfil, encuadre, topología, máscaras, registros PAL,
los 58 índices fuente, TR, helpers, enteros de vértices/UV/pesos, índices y
materiales. Compara todos los campos con un volcado nativo, incluyendo el
patrón float32 de cada número y el signo de cero. También reconstruye el
paquete generado por HL-T4c.1 con cantidades completas de Heather sintética.
CRC y metadatos no autentican MDL522/ANM525 ni reconstruyen las partes omitidas.

Las pruebas de frontera descubrieron una discrepancia del productor: para
normas al cuadrado 0,999/0,99900001/0,99900002, un quaternion válido en doble
precisión podía quedar en **0,998999964993974** al guardarse en f32. El lector
lo rechazaba correctamente. El encoder común ahora comprueba la norma del
valor serializado y devuelve `RI_ROTATION_F32` si cruza el límite. Se añadieron
tres casos rechazados y tres fronteras representables aceptadas por productor,
oráculo y C++. **No se amplió la tolerancia 0,001**, ni se alteraron los hashes
de los ejemplos válidos SRI1.

Pruebas ejecutadas:

- [Batería nativa](../../tests/cpp/test_inspection_locomotion.cpp): **650
  rechazos** conservan la salida byte por byte. Incluye cabeceras y límites
  uint32, reservados, mapa/canales/descriptores, datos numéricos, geometría,
  truncamientos de cabecera/secciones/frames, CRC y sobrantes; errores de
  apertura, lectura, EOF y cierre; fallos de las tres asignaciones; errores
  en la última textura y recuperación posterior. Los callbacks de I/O
  comprueban que todavía ven el modelo anterior. La cabecera inválida se
  rechaza antes de asignar. SRI1 rechaza SRI2 sin modificar su salida.
- La misma batería prueba acceso a extremos de los tres clips, rangos
  inválidos sin mutación, padding inactivo limpio y **500 actualizaciones**
  del núcleo con la vista nueva. No hay llamadas al evaluador SRI1 para estas
  muestras. El fallo de asignación se intercepta explícitamente en las formas
  normales y `nothrow` de `new`, también bajo ASan.
- [Reconstrucción y cotejo](../../tests/python/test_locomotion_rig_reconstruction.py):
  rechazo de los **59212 puntos de truncamiento** de un archivo sintético,
  tipos de entrada, texturas ausentes/mutables/corruptas, conjunto de archivos,
  presupuesto de píxeles, influencias ausentes y producción→reconstrucción→C++.
- [Oráculo de wire nativo](../../tests/locomotion_rig_wire_oracle.py) con
  [bytes inventados independientes](../../tests/locomotion_rig_fixtures.py):
  todos los campos coinciden; **329 variantes corruptas** son rechazadas por
  ambos lectores, incluida cada posición de los 60 bytes de descriptores.
  Comprueba también la ausencia de la última textura mediante archivos reales.
- **542 pruebas Python aprobadas** en las cinco baterías relacionadas de
  reconstrucción, productor, fuentes, SRI1 y contrato multiclips.
- **33/33 CTest en Release y 33/33 en ASan/UBSan**, sin hallazgos. Incluyen
  las ocho pruebas/oráculos de locomoción y 25 regresiones SRI1 de lector,
  presentador, skinning, ordenación y contratos GPU con dobles del SDK.

Comandos principales:

```text
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_inspection_locomotion test_inspection_rig test_rig_draw_equivalence test_ctr_rig test_locomotion_clock test_locomotion_pose test_locomotion_update --parallel 2
rtk proxy ctest --preset host-release -R '^(locomotion_|inspection_locomotion$|inspection_rig$|rig_)' --output-on-failure
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_inspection_locomotion test_inspection_rig test_rig_draw_equivalence test_ctr_rig test_locomotion_clock test_locomotion_pose test_locomotion_update --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(locomotion_|inspection_locomotion$|inspection_rig$|rig_)' --output-on-failure
rtk proxy .venv/bin/pytest -q tests/python/test_locomotion_rig_reconstruction.py tests/python/test_locomotion_inspection.py tests/python/test_produce_heather_locomotion.py tests/python/test_rig_inspection.py tests/python/test_heather_locomotion_contract.py --cov=tools.qa.locomotion_rig_oracle --cov=tools.pipeline.locomotion_inspection --cov=tools.pipeline.produce_heather_locomotion --cov=tools.pipeline.rig_inspection --cov-report=json:build/heather-locomotion/sri2-reader-python-coverage.json --cov-report=term-missing --junitxml=build/heather-locomotion/sri2-reader-pytest.xml
```

Cobertura local, Python y LLVM:

| Módulo | Líneas | Ramas |
|---|---:|---:|
| `engine/domain/inspection_locomotion.cpp` | 36/36, 100 % | 34/34, 100 % |
| `engine/platform/common/inspection_locomotion.cpp` | 212/212, 100 % | 155/158, 98,10 % |
| `tools/qa/locomotion_rig_oracle.py` | 86/86, 100 % | 18/18, 100 % |
| `tools/pipeline/rig_inspection.py` | 153/153, 100 % | 82/82, 100 % |

Los dos módulos del productor conservan 100 % de líneas/ramas. CI incorpora
CTest/oráculo, lint de los helpers y gates individuales al 80 % para
[modelo](../../gcovr-inspection-locomotion-domain.cfg),
[lector](../../gcovr-inspection-locomotion-reader.cfg) y reconstrucción Python.
Ruff, formato, whitespace y comprobaciones del repositorio pasan. Informes
ignorados en `build/heather-locomotion/sri2-reader-coverage/`,
`sri2-reader-python-coverage.json` y `sri2-reader-pytest.xml`.
No se afirma ejecución remota de CI/GCC, nuevo build ARM ni prueba física.

**HL-T4c.2 cerrada. Siguiente: HL-T4c.3, publicación/cotejo privado A/B**,
comparando reconstrucción con las fuentes fijadas y referencias de pose sin
relajar umbrales. HL-T4c no queda cerrada todavía. La integración del visor y
la nueva prueba de espera/caminar/correr en 2DS XL permanecen pendientes.

## 2026-10-26 — HL-T4c.3: publicación privada A/B y fidelidad

**HL-T4c.3 y HL-T4c cerradas en el perfil declarado.** Los paquetes A/B
son idénticos, se reconstruyen con el lector independiente y el lector C++,
y el núcleo reproduce 245 poses contra las referencias fijadas de HL-T3.
Se mantienen las tolerancias HLC15. No se generó un build de consola ni se
cambió el paquete físico `8f778b6e4960`.

### Fuentes, publicación y correspondencias

La conversión A parte de los recursos conservados en `heather-source-v1`;
B vuelve a abrir la ISO europea, verifica su hash/tamaño, verifica `XBG0.MFA`,
recorre sus entradas D8 y adquiere de nuevo los ordinales 522 y 525. Los
bytes de ambas adquisiciones coinciden antes de las conversiones separadas:

| Entrada | Bytes | SHA-256 |
|---|---:|---|
| MDL522 original | 1.639.344 | `1aa81b56c0a079c8d98e57f17537e91b2ce20f1e46a1cc6d9816561cad03d2e9` |
| ANM525 | 465.436 | `a0ad870863df5c495c453acdc2230dc8bb762394687599329f5a97a975d75181` |
| Descriptores PAL 101/109/113 | 36 | `8288f40a25c744293312fad7e868619a431ce6e5155003dedb883285051fe867` |

Los descriptores proceden de RAM del primer estado de la ventana
`idle-transitions-replay-v1`, contrastado con el manifiesto HL-T3 fijado.
No se vuelve a aplicar la conversión PAL. El manifiesto consolidado de
referencias mantiene SHA
`403a586353d64cde11d79b38235032cdb157c7defdbd718a2a267c09fa3ce8e9`;
se verifican de nuevo los hashes de sus 16 informes antes de usar referencias.

Destinos exclusivos bajo `/Users/germancontreras/sh3-private-data/`:

- `heather-locomotion-a-v1/`
- `heather-locomotion-b-v1/`
- `heather-locomotion-audit-v1/`, informe agregado y copia del helper.

Cada paquete contiene `heather.sri` de **290.156 bytes**, 13 RGBA de
**18.087.936 bytes** en conjunto y un manifiesto. Total de datos:
**18.378.092 bytes** por conversión. Los 14 archivos y ambos manifiestos
son idénticos. Se conserva `.manifest.pending.json` conforme al protocolo
del escritor compartido; el enlace final solo se publica después del cotejo.

| Artefacto | SHA-256 |
|---|---|
| `heather.sri` A y B | `2bc96e9f7fec9e52b21186d033ee02694b67808098bf101d304fd944c928fc0b` |
| `manifest.json` A y B | `0f8251b66f737b00525bb092799eff9ace799aa6fd6fbc2c96b8b590a32e7af1` |
| `heather-locomotion-audit-v1/audit.json` | `e61ad4580c74770b4c30e376ada40e5b8eced617ad8beeda3c5e8c6c9da65af7` |
| Helper de publicación/auditoría | `fbeec9d1130256ab69d63b3e0708b76fa2bf6cb753ffb6ce2c9c2c1fc342bb99` |
| Lector/harness nativo Release | `323912ff25568fa59edb908070bbe6e6e4b950025836432c903e9985f722ae34` |

El nuevo [publicador](../../tools/pipeline/publish_heather_locomotion.py)
recibe fuentes crudas y reutiliza autenticación y escritor exclusivo:
no acepta un `source_verified` indicado por el llamador. Antes de publicar
el manifiesto relee cada archivo, compara bytes y reconstruye el conjunto.
Los fallos conservan el directorio parcial sin manifiesto final y no
sobrescriben un destino anterior. La auditoría de poses se registra aparte.

El [auditor de selección](../../tools/qa/locomotion_source_audit.py) no
importa productor ni runtime. Recalcula desde documentos decodificados:
58×36 TR, padres/vínculos, 49 helpers, 6.943 vértices, 16.566 índices,
13 materiales/píxeles, descriptores y encuadre común. Compara todos los
campos seleccionados, incluidos enteros originales y representaciones f32.
El lector C++ reconstruye los mismos campos desde ambos paquetes y produce
trazas idénticas. No se reconstruyen todos los bytes MDL/ANM: cabeceras,
padding, flags/palabras ANM originales, muestras y elementos inactivos,
morphs, arma, desplazamiento mundial e iluminación PS2 quedan fuera.
Los recursos completos permanecen conservados en su ubicación privada.

### Hallazgo de precisión y corrección

El primer candidato, evaluado solo en memoria, tenía SHA SRI2
`3d5e0345f5447c3ed57c69f45b7003eccb9c33ea676119fede49aa9a760a503b`.
**414 de 2.088 quaternions** superaban 1e-7 frente al oráculo HL06;
máximo **0,00010834046406671405**. No se publicó ese candidato ni se
elevó la tolerancia. El productor usaba el quaternion matemático del decoder,
distinto del extremo f32 ya acreditado en las capturas.

El productor SRI2 reconstruye ahora W con la política acotada
`pcsx2-hl06-f32-v1`: productos/sumas truncados a f32, radicando limitado a
cero, SQRT al f32 más cercano y signo original de W. No normaliza los
extremos. Una implementación separada en QA compara 4.008 casos sintéticos;
los 2.088 extremos empaquetados coinciden exactamente con ese oráculo.
El decoder ANM sin pérdidas y la producción SRI1 permanecen sin cambios.
Esta política representa el perfil fijado de PCSX2, no toda la FPU PS2.

### Cotejo de poses con los estados preservados

Se releen **245 estados** y sus hashes fijados; se comprueban PC, S0,
ciclos EE, ticks, ambos canales, descriptores, padres, código del consumidor
y los bytes completos MDL522/ANM525 en RAM. No se controla PCSX2, no se
restaura ningún estado en el emulador y no se produce una nueva captura.

El modo `trace` del harness nativo es solo una herramienta de pruebas:
establece un ancla escalar de clip/fase estable y evalúa desde SRI2; después
solo usa `update_locomotion`. No inyecta matrices, TR ni caché de RAM.
Las ventanas con saltos de ordinal quedan como anclas separadas: **nueve**
en total. Los 245 relojes publicados coinciden exactamente en fuente,
destino, modo, contador, beta y validez de caché. Se comparan las matrices
modelo, antes de cualquier colocación mundial o cámara.

| Ventana | Poses | Matrices | Máximo absoluto |
|---|---:|---:|---:|
| Vuelta de espera | 68 | 2.448 | 0,000514984131 |
| Vueltas de correr y caminar, dos anclas | 56 | 2.016 | 0,000427246094 |
| Caminar → correr | 15 | 540 | 0,000427246094 |
| Correr → caminar | 16 | 576 | 0,000427246094 |
| Wrap durante modo 5 | 16 | 576 | 0,000427246094 |
| Espera → caminar y caminar → espera, dos anclas | 49 | 1.764 | 0,000488281250 |
| Correr → espera | 25 | 900 | 0,000427246094 |
| **Total** | **245** | **8.820** | **0,000514984131 ≤0,001** |

Se cotejan además **13.968 extremos crudos de quaternion** en retornos
estables: máximo **5,960464477539063e-8 ≤1e-7**. No se aplica ese umbral
a quaternions interpolados ni a offsets locales derivados del esqueleto;
estos últimos se comparan en f32 canónico y sus matrices resultantes con
la tolerancia 0,001. Se rechazan **236 controles** que desplazan la referencia
una actualización. A y B producen exactamente las mismas trazas nativas.

### Pruebas y límites de entrega

- **560 pruebas Python relacionadas aprobadas**, incluidas 12 alteraciones
  de fuente/selección, publicación exclusiva, fallos antes del manifiesto,
  política f32, lector y anclas/trazas nativas con caché; regresiones SRI1.
- Cobertura local **100 % líneas y ramas** de los seis módulos medidos:
  reductor SRI2, productor autenticado, publicador, payload compartido,
  reconstrucción y auditor de selección. Gates individuales ≥80 % en CI;
  las pruebas públicas usan únicamente recursos inventados.
- **33/33 CTest Release y 33/33 ASan/UBSan** aprobadas, con ocho pruebas
  de locomoción y regresiones de lector/render/lifecycle SRI1.
- Ruff/formato sobre el conjunto de CI y contratos del repositorio aprobados.
  Informes locales en `build/heather-locomotion/sri2-publication-coverage.json`
  y `sri2-publication-pytest.xml`. No se ejecutó CI remoto.

El helper queda en `build/heather-locomotion/publish_and_audit_sri2.py` y
como copia de custodia en la carpeta privada de auditoría. El modo `publish`
rechaza carpetas existentes; `audit` solo lee paquetes/capturas y crea un
informe nuevo al terminar. No debe reutilizarse un destino ya publicado.
El presupuesto de esta ejecución fue dos paquetes más 64 MiB de margen;
no se aplicó la reserva de 20 GiB propia del build PCSX2. Al finalizar la
auditoría quedaban unos 257 MiB: revisar espacio antes del próximo build.

El manifiesto del paquete físico anterior `heather-3ds-v3` sigue asociado
a `8f778b6e4960`, SHA
`e39433cdffefb27a2ceb3a772af7e9812df906b89e55f2786607415852e3a483`.
No se sustituyó ese directorio ni se escribió en la SD. Estos son paquetes
de datos para la siguiente integración; no acreditan todavía controles
multiclips, cadencia, ARM, 2DS XL ni movimiento por una habitación.

**Siguiente: HL-T4d.1, presentador y lifecycle**, conectando selección de
clips, pausa/paso, reinicio y suspensión con el núcleo ya cotejado.

## 2026-10-26 — HL-T4d.1: presentador, controles y ciclo de vida

**HL-T4d.1 cerrada en host.** `LocomotionProbe` conecta selección y tiempo de
inspección con el núcleo completo, y entrega al renderer únicamente matrices
publicadas. HLC10–12 quedan cubiertos por pruebas sintéticas; la aceptación
física multiclips continúa pendiente.

### Cambios y límites

- Aplicación separada del lector SRI2 y del renderer mediante
  `LocomotionSampleReader`/`IRigScene`. Perfil, reloj, caché y workspace tienen
  capacidad fija; no hay asignaciones en el bucle. Un `static_assert` limita
  el presentador al presupuesto de 32 KiB. El visor SRI1 conserva su lector
  y pruebas; Heather usa ahora la entrada SRI2 validada como paquete completo.
- Cadencia de inspección de 25 Hz con ticks 2, tiempo finito limitado a 0,1 s
  y máximo tres updates completos por llamada. Se ejecuta la evaluación de
  cada uno, incluso si solo se dibuja el último. No se multiplican incrementos
  para saltarse estados de mezcla o caché, ni se añade movimiento mundial.
- ZL/ZR solicitan anterior/siguiente en `101/109/113`. El selector rechaza
  espera→correr directa, cambios de destino durante mezcla, selección pausada
  y botones opuestos simultáneos. Conserva una sola petición hasta el próximo
  update y nunca reemplaza la primera por una segunda.
- Prioridad START/suspensión → A → L → R → selección → tiempo. A limpia
  resto temporal/petición. R pausado hace un update completo. L reinicia el
  destino actual en su primer fotograma estable sin consumir ticks y conserva
  la pausa. La extensión de inicialización al clip explícito mantiene el
  default 101 y la garantía de no publicar nada si falla un canal.
- Tapa/HOME conservan pose y pausa, descartan resto y petición, y exigen soltar
  todos los botones. El frame que libera los controles también descarta el
  tiempo dormido. START sigue funcionando durante esa espera. Cámara,
  SELECT cuerpo/cara, zoom, B y petición de CPU New fast se conservan.
- Fallos de muestra/pose pausan sobre el último snapshot válido; si un update
  falla dentro de una tanda, no se ejecutan los restantes. Los rechazos de
  selección muestran diagnóstico y permiten continuar luego sin solicitud.
  Cámara/HUD/GPU ocupada no vuelven a evaluar la pose al presentarla.
- El renderer valida el payload compartido, sin exigir el reloj legacy SRI1;
  los lectores siguen verificando su formato específico. El HUD muestra
  origen/destino, modo, mezcla y Q12, y separa 25 updates/s de FPS submit.

Archivos principales:
`engine/application/{include/sh3/application/locomotion_probe.hpp,locomotion_probe.cpp}`,
`engine/domain/{locomotion_pose.cpp,locomotion_update.cpp}` y
`engine/platform/3ds/render/{rig_main.cpp,rig_renderer.cpp}`.
El [contrato](../../schemas/heather-locomotion-v1.md#integración-de-aplicación-hl-t4d1)
detalla el mapeo y los descartes de eventos.

### Verificación local

| Comprobación | Resultado |
| --- | --- |
| Preset Release, selección de locomoción/SRI/render/cadencia | 37/37 |
| Misma selección con ASan/UBSan y `halt_on_error=1` | 37/37 |
| `test_locomotion_rig_reconstruction.py` | 356 aprobadas; productor/lector/oráculo y corrupciones |
| Ruff del módulo Python modificado | Lint y formato aprobados |
| Contratos de repositorio/especificaciones | PASS, 0 errores |
| `git diff --check` | Aprobado |

`test_locomotion_probe` comprueba pausa en modos 3/5, cien redibujos sin
avance, paso/reinicio, precedencia simultánea, cola de selección, tiempos
negativos/no finitos/largos, equivalencia de updates agrupados y separados,
reinicio fallido, fallo en el segundo update, suspensión durante ambas
mezclas, botones retenidos, cámara en pausa, START y frame ocupado.
Las asignaciones globales están prohibidas durante sus escenarios.

`test_ctr_locomotion_controls` compila el **entry point real** con dobles SDK
y prueba su mapeo HID, hooks de tapa/HOME/salida, restauración New fast y
liberación del hook/CPU. Esta comprobación descubrió una conversión implícita
de la frecuencia de ticks a float bajo Clang; ahora el cociente usa double
antes de convertir el intervalo a float. No es una compilación ARM ni una
prueba de hardware.

`test_inspection_locomotion` añade 500 iteraciones desde el SRI2 sintético
reconstruido, pasando por lector concreto → presentador → skin/sort, sin
asignaciones. `rig_gpu_locomotion` valida el payload sin reloj SRI1 durante
1.001 presentaciones, conservando las pruebas de fallos, espera y liberación
de recursos. Los oráculos previos de reloj, pose y publicación conjunta
siguen aprobados, al igual que las regresiones del visor SRI1.

Comandos de reproducción de esta selección:

```sh
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_locomotion_probe test_ctr_locomotion_controls test_locomotion_clock test_locomotion_pose test_locomotion_update test_inspection_locomotion test_inspection_rig test_ctr_rig test_rig_draw_equivalence test_frame_cadence --parallel 2
rtk proxy ctest --preset host-release -R '^(locomotion_|inspection_locomotion$|inspection_rig$|rig_|frame_cadence$)' --output-on-failure
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_locomotion_probe test_ctr_locomotion_controls test_locomotion_clock test_locomotion_pose test_locomotion_update test_inspection_locomotion test_inspection_rig test_ctr_rig test_rig_draw_equivalence test_frame_cadence --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(locomotion_|inspection_locomotion$|inspection_rig$|rig_|frame_cadence$)' --output-on-failure
rtk proxy .venv/bin/python -m pytest tests/python/test_locomotion_rig_reconstruction.py -q --no-cov
```

CMake registra las pruebas nuevas para los jobs host existentes; no se
ejecutó CI remoto ni se midió aún el gate individual del presentador.
No se generó build ARM ni se modificaron los paquetes privados A/B, el
build físico `8f778b6e4960`, PCSX2 o la SD. Al verificar quedaban unos
212 MiB libres: se hicieron builds incrementales host y pruebas acotadas;
revisar margen antes de la entrega ARM.

**Siguiente: HL-T4d.2**, gate individual del presentador, pipeline pertinente,
compilación ARM y paquete SRI2/texturas/build con hashes y protocolo HL-T5.

## 2026-10-26 — HL-T4d.2: cobertura individual, ARM y entrega multiclips

**Completada. Build `4707dacec7d1` preparado; HL-T5 sigue pendiente.**
Se añade [el gate individual](../../gcovr-locomotion-probe.cfg) del
presentador a `cpp-coverage`, con umbrales de 80 % de líneas y ramas y XML
incluido en los artefactos de CI. Los gates previos de reloj, pose,
transacción y lectores permanecen separados. Los jobs usan datos sintéticos;
la entrega con recursos originales se publica exclusivamente fuera del repositorio.

### Pipeline y portabilidad

| Comprobación local | Resultado |
| --- | --- |
| CTest completo macOS Release | 364/364 |
| CTest completo macOS ASan/UBSan | 364/364; `halt_on_error=1` |
| Python: publicación, reconstrucción, productor, contrato, SRI1 y scripts ARM | 608 aprobadas |
| Gate aislado del presentador, GCC 12.2/gcovr | 123/146 líneas (84,2 %), 103/119 ramas (86,6 %), 10/10 funciones |
| Medición adicional LLVM, mismo módulo | 86,31 % líneas / 87,12 % ramas |
| ARM y shader PICA | Compilación Release aprobada; 12 componentes de salida únicos |
| Ruff del test Python modificado | Lint/formato aprobados |
| Contratos del repositorio y trazabilidad | PASS, 0 errores |
| `git diff --check` | Aprobado |

La batería del script incluye ahora `build_heather_probe.sh`: SDK ausente,
destino ocupado por directorio/archivo/enlace, fallo de CMake y conservación
de la salida existente. Son 48 casos en esa batería, incluidos dentro de
las 608 pruebas anteriores.

Al ejecutar también las regresiones SRI1/SRI2 en Linux, GCC detectó que
los tres callbacks de error de archivo no conservaban `noexcept`. En glibc,
el tipo de `ferror` incluye esa especificación; en macOS no causaba el error.
Se corrigieron solo los dobles de `test_inspection_locomotion.cpp` y
`test_inspection_rig.cpp`, sin relajar flags ni cambiar el lector real.
El build ID y los bytes ARM permanecen iguales porque estos cambios son
exclusivos de pruebas.

Tras esa corrección pasan las **37/37 pruebas seleccionadas con GCC 12.2**
en Linux, incluidos los cuatro oráculos y las regresiones del renderer.
Los seis gates, usando sus configuraciones exactas de CI, quedan así:

| Módulo C++ | Líneas | Ramas |
| --- | ---: | ---: |
| Reloj | 104/104 (100 %) | 140/140 (100 %) |
| Pose | 178/181 (98,3 %) | 191/214 (89,3 %) |
| Publicación conjunta | 45/45 (100 %) | 42/42 (100 %) |
| Presentador | 123/146 (84,2 %) | 103/119 (86,6 %) |
| Modelo SRI2 | 28/28 (100 %) | 38/38 (100 %) |
| Lector SRI2 | 186/186 (100 %) | 162/164 (98,8 %) |

Todos superan 80/80; los XML y resúmenes están en `delivery-v1/gates/` y
CTest en `gcc-tests.xml`. La prueba SRI2 y su oráculo se repitieron después
del ajuste en Release y ASan/UBSan (2/2 por preset); la regresión SRI1
también se reconstruyó y comprobó por separado en ambos presets.

### Compilación ARM

Se ejecutó `scripts/build_heather_probe.sh` desde un contenedor de la imagen
fijada `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`,
con fuentes de solo lectura, sin red ni recursos privados. Los objetos se
construyeron en tmpfs; los artefactos se conservaron bajo
`build/heather-locomotion/delivery-v1/arm/`. GCC ARM informa 16.1.0.

El ELF es ARM de 32 bits, little endian, EABI5 hard-float. `size` informa
200.608 bytes de texto, 397.280 de datos y 1.172.976 de BSS; estas cifras
no son una medición del heap, de memoria GPU ni del consumo total en consola.
Se verificaron los seis hashes de `SHA256SUMS`, magic 3DSX/SMDH y el ID
recalculado desde todas las fuentes de `engine` y `CMakeLists.txt`.

El primer intento compiló y verificó el build, pero su recolector no encontró
`arm-none-eabi-readelf` en PATH. La repetición usa la ruta explícita de
`DEVKITARM` y recoge todos los artefactos. El primer ensayo de cobertura
también quedó registrado como fallido por tmpfs `noexec`; se corrigió el
montaje de esa carpeta temporal. Ninguno requirió cambiar el código de producto.

### Entrega privada y reconstrucción

Destino nuevo y exclusivo:
`/Users/germancontreras/sh3-private-data/heather-locomotion-3ds-v1/`.

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `sd-card.zip` | 19.016.374 | `c152678c3d5f13458af985f74f16e5ef20c0589c1a833387bb003044ddde8946` |
| `sh3_heather_probe.3dsx` | 614.444 | `1bf372f3cc5eaedc78ad9a57d767e4144ce2a26a8d65d0c116cae360afa71021` |
| `sh3_heather_probe.smdh` | 14.016 | `8e6b2829e0656345043d0cb4fedc1a270e1f4ac287e22c6e2f726541b8d1efdc` |
| `heather.sri` SRI2 | 290.156 | `2bc96e9f7fec9e52b21186d033ee02694b67808098bf101d304fd944c928fc0b` |
| `LEEME.txt` | 5.374 | `e87c2dd6355069bbc0f061e90ca91ea9743604264f1322e2c7eb689797a6a03a` |

El manifiesto de entrega tiene SHA-256
`8384baf0387454d7b5d422452768b08d836b0d94ab1f36841a0bc2aa3494005a`.
Recibo local: `reports/local/heather-locomotion-delivery-v1.json`.

Las entradas son los paquetes A/B de HL-T4c.3: se recalcularon los hashes
del manifiesto, sus catorce archivos y la auditoría de 245 poses antes de
empaquetar. Cada lado pasó el oráculo Python y el lector C++ completo;
sus reconstrucciones y dumps nativos coinciden. Ambos ZIP producidos en
memoria son idénticos. Se verificó el contenido de las 18 entradas del ZIP,
CRC y SHA-256, y se reconstruyó nuevamente SRI2 desde él.

El helper compartido `inspection_archive` conserva rutas y fechas fijas.
`_write_bundle` escribe exclusivamente, relee los archivos y ejecuta una
reconstrucción adicional antes de publicar `manifest.json`. El paquete
incluye 17 archivos de aplicación bajo `3ds/sh3_heather_probe/` más la lista
de hashes en la raíz del ZIP. Los archivos sueltos y el ZIP ocupan
38.028.300 bytes, sin contar el manifiesto. Se conservaron las entregas
anteriores y no se escribió en la SD física.

### Prueba breve en Azahar

Azahar 2126.2 ARM64/Vulkan ejecutó el mismo ZIP en una copia portátil privada
con configuración nueva derivada del perfil anterior. El atuendo original,
las trece texturas y los clips 101/109/113 aparecen correctamente. Se
seleccionaron los cinco arcos y se observó su llegada a modo estable; el
salto directo espera→correr mostró el rechazo esperado sin bloquear el visor.

A conserva la pose; R pasó Q12 de 31.056 a 31.670 (614), manteniendo pausa;
L volvió a cero sin reanudar. SELECT mostró el rostro, X acercó hasta 0,45,
la cruceta giró la cámara y B restauró el cuerpo. A reanudó el reloj y START
regresó a la lista de aplicaciones. El proceso usado para la prueba terminó.
Se conservaron trece capturas, `smoke.json`, `launch.log` y
`user/log/azahar_log.old.txt` en `heather-locomotion-emulator-v1/`, fuera
del repositorio. Recibo: `reports/local/heather-locomotion-emulator-v1.json`.

Es una comprobación breve de arranque y controles, sin una medición de
60 segundos por arco. El log conserva `ConfigureNew3DSCPU` no implementado:
`New fast` no acredita frecuencia física. Los FPS del emulador tampoco se
presentan como rendimiento de la 2DS XL. No se probó tapa/HOME en hardware.

### Reproducción y siguiente paso

Los scripts locales `run_host.py`, `run_container.py`, `run-arm.sh`,
`run-coverage.sh`, `run-coverage-all.sh`, `package.py` y
`launch_emulator.py`, junto con logs/XML/JSON, están en
`build/heather-locomotion/delivery-v1/`. El empaquetador rechaza el destino
si ya existe; no debe ejecutarse para sobrescribir esta entrega.

El [protocolo HL-T5](../compatibility/heather-locomotion.md), incluido en
`LEEME.txt`, pide 60 s por clip y transición, cuerpo/cara, A/R/L, cámara,
START, tapa/HOME y métricas por encuadre. La selección usa ZL/ZR y sigue
siendo una animación en el mismo lugar: no añade habitación, movimiento
mundial, respuesta física ni combate. **Siguiente: copiar el paquete completo
a la SD y ejecutar HL-T5 en New Nintendo 2DS XL.** CI remoto no ejecutado.

## 2026-10-26 — Entrega de `4707dacec7d1` a la SD

Por solicitud del usuario, se instalaron los 17 archivos completos del
paquete (19.011.926 bytes) en `NO NAME/3ds/sh3_heather_probe/`, comprobando
tamaños y SHA-256 contra el manifiesto fijado antes y después de instalarlos.
Los archivos auxiliares AppleDouble de macOS se identificaron por nombre y
cabecera; no se confundieron con recursos del visor. Se conservó el directorio
anterior completo en
`NO NAME/sh3-heather-backup-before-4707dacec7d1-20261026T205329Z/previous/`.
Después de sincronizar y verificar también el respaldo, `diskutil` confirmó
la expulsión segura de la tarjeta. Recibo local:
`reports/local/heather-locomotion-sd-delivery-4707dacec7d1.json`.
**HL-T5 sigue pendiente:** esta copia no acredita funcionamiento físico.


## 2026-10-26 — HL-T5: fallo de apertura y corrección de ruta

**Primer intento físico fallido; repetición pendiente con `7250f427ffb9`.**
El usuario comunicó `Heather failed: open`, build `4707dacec7d1`, antes de
mostrar Heather. Al reconectar la SD, los 17 archivos coincidían con el recibo
anterior en tamaño y SHA-256; `heather.sri` conservaba su cabecera SRI2.
No se observó un archivo faltante ni una copia distinta del paquete entregado.

El entry point pasa `sdmc:/3ds/sh3_heather_probe/`, pero el lector concatenaba
siempre `"%s/%s"`. La primera apertura recibía
`sdmc:/3ds/sh3_heather_probe//heather.sri`, con una barra adicional. La nueva
regresión, que coteja cada ruta literal antes de simular la apertura, falló
contra ese código y pasó después de corregir el separador en
[el lector](../../engine/platform/common/inspection_locomotion.cpp).
El resto del núcleo, renderer, SRI2 y recursos privados queda intacto.
La relación causal final con el fallo físico sigue pendiente de confirmar
en la consola; la reproducción host comprueba la construcción defectuosa.

[La batería del lector](../../tests/cpp/test_inspection_locomotion.cpp) cubre
el directorio `sdmc:` con/sin barra final, directorios relativos con/sin barra
y la raíz `/`; verifica SRI2 y ambas texturas sintéticas, con tres aperturas,
tres cierres y nueve lecturas. Conserva las pruebas de truncamiento, CRC,
reservados, límites y publicación atómica. Resultados de esta corrección:

- 37/37 CTest Release y 37/37 ASan/UBSan; cero fallos.
- 356 pruebas Python de reconstrucción SRI2; cero fallos.
- 37/37 CTest GCC y los seis gates individuales aprobados con el SDK fijado.
- ARM ELF32/3DSX/SMDH compilados, hashes verificados y gate del shader aprobado.
- Reconstrucción independiente de los ZIP A/B idéntica; lector nativo acepta
  ambos paquetes y produce el mismo resultado. Recursos cotejados con el
  manifiesto y la auditoría de 245 poses fijados en HL-T4c.3.

| Gate GCC | Líneas | Ramas |
| --- | ---: | ---: |
| Reloj | 104/104 | 140/140 |
| Pose | 178/181 | 191/214 |
| Publicación | 45/45 | 42/42 |
| Presentador | 123/146 | 103/119 |
| Dominio SRI2 | 28/28 | 38/38 |
| Lector SRI2 | 187/187 | 164/166 |

Logs, XML de pruebas/cobertura, build y scripts de entrega se conservan en
`build/heather-locomotion/path-fix-v1/`. El log
`red-path-regression.log` conserva el fallo previo a la corrección.
No se reejecutó CI remoto ni Azahar para este cambio. Las cifras de la batería
completa y la prueba emulada de HL-T4d.2 pertenecen al build anterior.

### Paquete corregido y nueva entrega a SD

Nuevo destino privado exclusivo:
`/Users/germancontreras/sh3-private-data/heather-locomotion-3ds-v2/`.
Se conservó intacto el paquete v1. El ZIP contiene los 17 archivos de la
aplicación más `SHA256SUMS`; los recursos SRI2/texturas no se modificaron.

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| `sh3_heather_probe.3dsx` | 614488 | `9160bba42baa256af18dfde44a85d5e8ce2278be5f92e590b356894836b43d4d` |
| `sh3_heather_probe.elf` | 2510688 | `b7883d009aadcdfd8f4006862cd330487e33c423216ba719ad9683d576d1c484` |
| `sd-card.zip` | 19016718 | `68688a6f775f1aa1e78a877ba732d9eec6682d1d27d065f3777edfab1d80d6e2` |

Manifiesto v2: `0671ab59b1556cf14d56c5d0e79aa5e1c96b5e15b959e8de91c3251d1a8e1447`.

Se instalaron y releyeron los 17 archivos (19,012,270 bytes) en
`NO NAME/3ds/sh3_heather_probe/`, identificando la tarjeta por UUID
`2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`. Antes de reemplazar la aplicación se verificó el
inventario anterior y se conservó completo, incluidos auxiliares de macOS, en
`/Volumes/NO NAME/sh3-heather-backup-before-7250f427ffb9-20261026T210546Z/previous`.
También se verificó el respaldo. `diskutil` confirmó `Disk disk4 ejected`;
la tarjeta quedó expulsada de forma segura. Recibos locales:
`reports/local/heather-locomotion-delivery-v2.json` y
`reports/local/heather-locomotion-sd-delivery-7250f427ffb9.json`.

**Siguiente:** repetir el arranque y la [prueba física HL-T5](../compatibility/heather-locomotion.md)
con `7250f427ffb9`. No se acepta el visor multiclips hasta observar clips,
transiciones, controles, START, tapa y HOME en New Nintendo 2DS XL.


## 2026-10-26 — HL-T5a/b: aceptación funcional y métricas físicas

El usuario confirma que `7250f427ffb9` carga Heather y que funcionan espera,
caminar, correr, los controles, START, tapa y HOME en la New Nintendo 2DS XL.
Se registra aceptación funcional y corrección de `Heather failed: open`.
El resultado proviene del reporte del usuario, no de una captura del agente.

Métricas aproximadas: **29,9 FPS submit; 10,08 ms Skin+sort CPU; 23,3 ms
Submit+wait; 4,32 ms GPU previous**. No se indicaron clip, encuadre, intervalo
ni duración por transición; se conserva esa incertidumbre. Las cifras no se
suman ni se presentan como promedio de los seis casos. El evaluador de
locomoción tampoco queda medido de forma separada por Skin+sort.

Se desglosa HL-T5: **a funcional y b registro de métricas completadas**;
**c pendiente** de confirmar 60 s por clip/transición, cuerpo/cara y los cinco
arcos. El paquete privado v2 y su LEEME permanecen inmutables. No se fabrica
un nuevo build por registrar este resultado.

**Siguiente instancia: HM-T1**, inventario y contrato de datos espaciales de
Heather original, preparatorio de F06.01/F06.02 y de la primera escena compartida.
Se reutilizan capturas ya verificadas; no se confunde pose local con ley de
movimiento, colisión ni cámara del juego. [Spec y tareas](../specs/sh3-3ds/heather-movement.md).
