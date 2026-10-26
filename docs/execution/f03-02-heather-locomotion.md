# HL: inventario y reloj de Heather original

Fecha: 2026-10-25. [Spec EARS HL01–HL06](../specs/sh3-3ds/heather-locomotion.md).
**HL-T1 y HL-T2 completadas.** El inventario conserva 49
descriptores básicos y distingue los dos canales del jugador. La primera
serie de dibujo no acredita una vuelta completa: al final repite contador
y matrices y cambia la máscara. Nueve poses excedían el límite con la
referencia matemática; HL-T2c identifica la precisión de los extremos como
causa y acredita una referencia f32 separada, sin elevar la tolerancia.
Una serie posterior acredita una vuelta completa de `0x65`, con 67 avances
y poses verificadas. **HL-T3 en curso:** el mando normal selecciona caminar
`0x6D` y correr `0x71`; se cotejan poses estables, retorno completo a espera,
inicio/interrupción, vueltas completas de ambos movimientos y la transición
caminar→correr sostenida, incluida su salida recursiva. Faltan la transición
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
