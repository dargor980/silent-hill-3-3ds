# HM-T2b: perfiles, reloj y contactos de Heather

**Estado: en curso.** HM-T2b.1–4 verifican un alcance acotado: caminar,
parada, giro derecho, reloj PAL de 2 ticks y consulta de suelo/registro de
formas. Se añadió una cadena de contacto poligonal hasta posición y matriz,
y se verificaron el plano y las conversiones a punto fijo de cuatro llamadas.
Se aislaron además dos sumas no nulas al centro y el origen del microajuste X
en una actualización con cuatro retornos de corrección cero. Quedan abiertas
otras clases de contacto, diferencias de ciclos, otros giros y autoridad
general del movimiento. **No se integra todavía la
habitación ni se modifica el visor.** Requisitos
[HM03–HM04 y tareas HM-T2b](../specs/sh3-3ds/heather-movement.md).

## Procedencia y continuidad

- Heather original, actor `0x004481D0`, tipo `0x0100`, MDL522/ANM525 y callback
  `0x001986C0`. Recursos, PC, registros bajos, RAM, ordinal y canales se
  revalidan desde los estados completos; no se confía solo en los recibos.
- Misma instancia privada de HM-T2a, PID observado 18885; ejecutable SHA-256
  `54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
- **187 estados nuevos, slots 16–202**, exclusivos. Directorio de recibos:
  `/Users/germancontreras/sh3-private-data/heather-movement-v2`.
  Los estados siguen en `heather-movement-v1/states`, según el perfil activo.
  Capturas y recursos permanecen privados; solo se publica metadata local.
- Slots 16–45 continúan desde el 15 de HM-T2a, sin restaurar entre ellos.
  Grabación `normal-controls-v2.p2m2`, SHA-256
  `23b065767544703b785d43570aa9a4de5c224a3efb061034f11cf1a9e67d17c0`.
- Slot 46 verifica una **nueva frontera de restauración** para reproducir
  `direct-run-idle-v2.p2m2`, SHA-256
  `6b38fd88089bcaa929cb9c639912d23e676775b00ffa5ab9abcaf29ea44f8f30`.
  Ancla SHA-256
  `78ec5c47ba9e06e59dded0be03569b0f36113b78bedbf826e5f162f05badb65c`;
  RAM, CPU y ciclo coinciden exactamente con la copia inicial. Es la tercera
  restauración del proceso, contando las dos iniciales de HM-T2a. Slots 47–202
  continúan sin nuevas restauraciones.
- Ambas grabaciones contienen controles normales grabados por el usuario.
  No se escribe PC, RAM ni entrada artificial para obtener estos resultados.
  Se mantienen las comprobaciones de originales y la reserva de 512 MiB.
- El usuario cargó once juegos de filtros desde ajustes. Los puntos antiguos
  conservan condición `0`; no se presume que omitirlos los elimine internamente.

## Caminar y detenerse

Cada cadena incluye entrada del escritor `0x001DCCE0`, antes/después de SQC2,
salida del callback `0x001987A4`, entrada/salida del constructor y consumidor
`0x001DD434`. El llamador real sigue siendo `ra=0x001481FC`.

| Slots | Ordinal | Entrada | Perfil observado | Delta X/Z del escritor |
| --- | ---: | --- | --- | --- |
| 16–22 | 81959 | `0x1000` | Caminar, descriptor 109 | +28 / 0 |
| 23–29 | 82000 | 0 | Mezcla a espera, descriptor 101 | 0 / 0 |
| 30–36 | 82006 | 0 | Espera estable | 0 / 0 |

Los tres pares de SQC2 pasan la comparación de **32 MiB completos de RAM**:
solo el destino de 16 bytes puede diferir, coincide con VF4 y transcurren dos
ciclos. Una escritura idempotente también se verifica; no exige que cambien
todos los bytes. Las correcciones posteriores y el consumidor conservan la
posición en estas tres muestras. La traslación de matriz coincide en bytes.

En la muestra de parada, la mezcla de ambos canales avanza de 1640 a 2000
mientras la posición permanece fija. Esto separa pose y traslación en el caso
observado; **no prueba autoridad exclusiva** para todas las animaciones.

El prefijo espacial de caminar coincide con la referencia HL de HM-T1, pero
el consumidor difiere en **+54 ciclos EE**. Se conserva junto con los +87
de HM-T2a; no se declara equivalencia temporal entre ejecuciones.

## Reloj PAL

Slots 37–45 capturan la copia local del intervalo, la entrada del productor,
sus escrituras y el siguiente consumidor:

| Punto | PC | Evidencia |
| --- | --- | --- |
| Copia a intervalo de movimiento | `0x001380F8 → 0x001380FC` | FPR0 a `0x01CFB1F8`, una instrucción |
| Entrada del productor | `0x0019AB10` | Argumento `a0=2` |
| Publicación de ticks | `0x0019ABB4 → 0x0019ABB8` | `s0=2` a `0x01CFB990`, una instrucción |
| División PAL | `0x0019ABF8 → 0x0019AC00` | Operandos 2 y 50; resultados 0,0399999991 y 25 |
| Publicación del intervalo | `0x0019AC00 → 0x0019AC04` | FPR1 a `0x01CFB970`, una instrucción |

Las tres escrituras escalares mantienen GPR/FPR y el resto de RAM idénticos,
con un ciclo entre extremos. La copia local observada precede al siguiente
productor: **no se invierte ese orden** para presentarlos como una sola llamada.
El consumidor siguiente conserva el mismo intervalo publicado.

El productor aparece con ordinal 82008/fotograma nativo 20370; la copia local
anterior con 82008/20369; el consumidor siguiente con 82009/20371. En las
ventanas espaciales el fotograma crece dos unidades por ordinal respecto al
ancla. **La fase importa:** esa fórmula no se aplica indiscriminadamente al
interior del productor. Son contadores de la reproducción, no una medición
de tiempo de pared ni de rendimiento de la 2DS XL.

Se verificaron mediante `static_assert` y compilación de sintaxis x86_64 los
tamaños de los headers fijados de PCSX2: CPU=1160, IOP=952, FPU=264, FPR=4.
El bloque FPR empieza en offset 2466 en estos estados. No es un decoder
universal de otras versiones. Solo está probada dinámicamente la rama PAL
con 2 ticks; 0/1/3 ticks y otros modos permanecen fuera de este alcance.

## Giro derecho y parada

| Ordinal | Entrada | Descriptor | Yaw antes | Yaw después |
| ---: | --- | ---: | ---: | ---: |
| 82145 | `0x4000` | 107 | 2,1867957115 | 2,2747955322 |
| 82160 | `0x4000` | 107 | −2,7763915062 | −2,6883914471 |
| 82175 | 0 | 101 | −1,8083909750 | −1,8083909750 |

El vector de posición es cero: gira sobre el sitio. En 82145 se capturan
además los operandos del producto angular, retorno de normalización y el par
**`0x00148224 → 0x00148228`**, `SWC1 f0,0x34(s0)`. Solo pueden cambiar los
cuatro bytes de yaw; coinciden con FPR0, sin otros cambios de RAM ni registros
en ese ciclo. Velocidad angular observada: aproximadamente 2,2; intervalo:
aproximadamente 0,04. El resultado coincide exactamente con producto y suma
f32 truncados para estos operandos y este recorrido con pasos de depurador.

Las dos matrices de giro y la de parada publican la posición exacta y
corresponden al yaw observado con error máximo **2,171413e−7**, inferior al
límite previo de 1e−6. La liberación conserva el ángulo. Hay pequeños cambios
Y posteriores al escritor, separados del giro. No se capturó exactamente el
cruce de ±pi entre las dos muestras ni se probó izquierda o giro en marcha.

## Suelo y formas dinámicas

Dos cadenas, ordinales 82177 (espera) y 82530 (carrera), enlazan:

1. Entrada `0x001A6200`, salida `0x00136D10`, destino `0x01CFB4F0`, máscara
   `0x108`, segmento vertical derivado de posición Y−150 / Y+6000.
2. Resultado **tipo 1**, normal inicial no unitaria y normalizada posteriormente
   a `(0,−1,0)`, conservando el signo de cero observado. El registro `v0` vale
   cero en el retorno: **no es el indicador de éxito de este contrato**.
   El código fijado limpia el tipo de salida al entrar en la consulta.
3. Corrector `0x001372D0 → 0x001378D4`: cambia Y, conserva X/Z y copia el
   objetivo a `actor+0x130`. En ambos casos se acerca al objetivo sin alcanzarlo:
   `0,1152954102 → 0,1153076142`, objetivo `0,1153106689`, y
   `−0,5670471191 → −0,5670349002`, objetivo `−0,5670318604`.
   La captura delimita la rutina, no su almacenamiento escalar concreto.
4. Registro `0x001A0120 → 0x00137824`: incrementa el contador 0→1, escribe
   propietario Heather y callback `0x001372C0` en el banco seleccionado.
   Se observan banco 1 y banco 0; la segunda forma de 48 bytes coincide
   exactamente y se comprueban los segmentos sin transformación de la primera.
   La posición del actor permanece idéntica. El callback fijado retorna sin
   operaciones. La traslación final de matriz vuelve a coincidir en bytes.

La etiqueta inicial de adquisición `contact-query` se conserva como historial,
pero su interpretación queda corregida: esa rutina es **registro de personajes**,
coherente con la investigación previa de [SC](f03-02-carousel-collision.md).
No equivale a una respuesta contra paredes, ni al registro de geometría del
escenario. Falta seguir el consumidor físico y atribuir una corrección X/Z a
una forma aceptada por juego normal.

## Discrepancia de redondeo conservada

El primer auditor rechazó el extremo superior del segmento de carrera al
exigir truncamiento: predijo **5999,4326171875**, frente a **5999,43310546875**
capturado. Este último coincide exactamente con f32 al más cercano para los
operandos guardados. No se amplió la tolerancia: el informe conserva el rechazo,
el contraste exacto y la aritmética como **pendiente de atribución**.

La configuración declara FPU.Roundmode=3, FPUDiv.Roundmode=0 y VU0.Roundmode=3.
La suma angular con pasos y el segmento obtenido por continuación no bastan
para afirmar que ambos modos usan la misma aritmética. HM-T2b.5 exige repetir
la misma operación y operandos en ambos recorridos antes del contrato del
controlador. Tampoco se atribuyen automáticamente a esto los +87/+54 ciclos.

La revisión posterior de la fuente fijada de PCSX2 aporta una explicación
candidata más precisa. `pcsx2/x86/iFPU.cpp` activa `FPU_CORRECT_ADD_SUB=1`;
`FPU_ADD_SUB` enmascara bits del operando con menor exponente antes de sumar.
Con Y=`−0,567047119140625` y 6000, la diferencia de exponentes es −13:
el primer operando pasa a `−0,56689453125` y la suma truncada produce
**5999,43310546875**, exactamente lo capturado. La misma regla coincide con
el segmento en espera y el giro observado. Por tanto, coincidir con el
redondeo al más cercano **no prueba que ese sea el modo usado**.

Además, `DebuggerWindow::onStepInto` coloca un breakpoint temporal y reanuda
la CPU; esa función no demuestra un cambio al intérprete. No se atribuye la
discrepancia a un cambio de modo. El informe candidato reabre los estados,
verifica sus hashes y conserva tres comparaciones exactas, pero falta observar
directamente el par de operandos/resultado de `ADD.S` en `0x00136D00` en ese
primer informe. La captura posterior se describe a continuación; la hipótesis
no constituye un oráculo general de la FPU PS2.

`filters/rounding-v1.json`, con 27 filas, quedó cargado y produjo ocho estados,
slots 88–95, **sin otra restauración**:

| Slots | Ordinal | Recorrido | Y de entrada | Extremo superior |
| --- | ---: | --- | ---: | ---: |
| 88–89 | 82532 | Continuar → consulta → consumidor | −0,5670202374458313 | 5999,43310546875 |
| 90–93 | 82534 | Antes de ADD.S → un paso → consulta → consumidor | −0,567034900188446 | 5999,43310546875 |
| 94–95 | 82536 | Continuar → consulta → consumidor | −0,567047119140625 | 5999,43310546875 |

El par 90/91 verifica `0x00136D00 → 0x00136D04`, opcode `0x46000800`,
`ADD.S f0,f1,f0`, y **un ciclo**. Antes, f0=6000 y f1 coincide con Y;
después, f0=5999,43310546875. Los 32 MiB de RAM, GPR bajos, VF4 y los otros 31 FPR
son idénticos. La consulta 92 conserva los FPR y publica f0 como extremo
superior. Las tres consultas coinciden con la suma enmascarada y sus
consumidores conservan X/Z y la traslación exacta de matriz.

Las tres Y originales difieren; tras el enmascarado todas valen
−0,56689453125. Esto **no es una comparación entre modos con los mismos
operandos originales**, ni prueba qué instrucciones host ejecutó el JIT.
No se observó una divergencia de resultado entre los recorridos medidos.
Se mantiene la diferencia frente a la suma IEEE truncada, sin relajar
tolerancias, y no se deduce causalidad para los +87/+54 ciclos anteriores.

## Ruta horizontal localizada

Se cotejaron otras seis ventanas ELF/RAM del estado 95 para preparar HM-T2b.6.
La preparación fue estática; las capturas posteriores se distinguen abajo:

- El llamador `0x00194D28` invoca `0x0019FCF0`, que llama al procesador
  `0x001A0D90`. Este recorre las entradas de personajes y llama a
  `0x001A1580`; se distinguen las formas del mapa y las listas dinámicas.
- `0x001A24D0` recibe destino de resultado, forma y entrada del personaje.
  Los retornos `0x001A1B5C` y `0x001A1D2C` permiten filtrar el tipo no cero
  y el propietario Heather en las rutas estática y dinámica respectivamente.
  Un candidato aceptado no acredita por sí solo una corrección física.
- `0x0019FE7C` y `0x0019FEAC` almacenan X/Z en el propietario; `0x0019FEDC`
  y `0x0019FF0C` almacenan también X/Z de la traslación de matriz. Sus sumas
  usan el delta preparado en la pila. El callback de Heather `0x001372C0`
  sigue siendo vacío; estas escrituras pertenecen a la rutina exterior.

Se respaldaron los filtros anteriores y se preparó `filters/horizontal-v1.json`
con **38 filas**, SHA-256
`62ac60afc4da5bcd0ea4d92ad0c0ea8621a5206f0de93ecf47efd4774c50af57`.
El plan `horizontal-plan-v1.json` limita la continuación a ordinales
82536–82640 y un máximo de 16 estados exclusivos, slots 96–111, manteniendo
512 MiB de reserva. Incluye otra consulta en 82540 y una parada final antes
de agotar la grabación. Las escrituras se filtran por propietario y delta X/Z
no nulo, ignorando el signo de cero. No se contabilizan como evidencia ni se
presume contacto porque se haya preparado el filtro.

El usuario cargó el filtro. El primer guardado, slot 96, quedó rotulado
`horizontal-physics-entry`, pero se detuvo realmente en `0x001A6200`, ordinal
82540. El capturador rechazó la expectativa 82536/`0x0019FCF0` **después de
preservar el estado**. El recibo y la discrepancia permanecen intactos: es la
consulta adicional prevista, no una entrada física observada.

### Comparación adicional con los mismos operandos

Slots 96–97 repiten por continuación el Y original de 90/91/92:
**−0,567034900188446**, bits `0xbf112933`. FPR1, posición Y y el operando
guardado antes de `ADD.S` coinciden en bytes; la constante es 6000 y el
resultado vuelve a ser **5999,43310546875**. Queda acreditada la coincidencia
de esta operación con los mismos operandos originales entre los dos recorridos.
El informe de 88–95 conserva su alcance histórico, que no incluía esta muestra.
No se demuestra una regla general del hardware ni qué instrucciones host
ejecutó el JIT; los +87/+54 ciclos siguen sin atribución.

### Microajuste sin contacto registrado

Slots 98–105, ordinal 82569, capturan cuatro pares de una instrucción:
posición X/Z y traslación X/Z de matriz. Cada par compara los **32 MiB de RAM**,
GPR bajos y FPR; solo puede cambiar el destino de cuatro bytes y pasa un ciclo.
El delta de pila es `(0,001953125, −0,00004196167, 0, 1)`; el estado de contacto
`entrada+0xe4` y la corrección `entrada+0xd0` son cero. X cambia un ULP y Z se
reescribe sin variar. Este caso **no se clasifica como respuesta a una pared**.
La procedencia quedaba pendiente en esa ventana; la sección posterior
contrasta una explicación con estas muestras y captura el recorrido X en
otra actualización, sin reescribir la evidencia histórica.

### Contacto aceptado y publicación física

El filtro reducido `horizontal-accepted-v1.json`, 38 filas, SHA-256
`b4b469f2a936c86a72a12b44725a0759b1d5f904fe68daf202381fc0909b4bb8`,
eliminó las paradas repetitivas de escritura y conservó aceptación y límite.
Al continuar se obtuvo el slot 106, antes del límite final:

| Slots | Punto observado | Resultado |
| --- | --- | --- |
| 106 | `0x001A1B5C`, ordinal 82592 | Candidato estático tipo 1 para Heather; aún no modifica posición |
| 107 | Retorno `0x001A1740` | Contador 0→1; copia tipo, forma y vector a la lista de candidatos |
| 108–109 | `0x001A1E30 → 0x001A1924` | Un candidato; publica `(0,15427941, 0, −0,52378708, 1)` y estado 1 |
| 110–111 | Segunda llamada del mismo ordinal | Un candidato de la misma forma; vector residual `(0,008657215, 0, −0,029391166, 1)` |
| 112–119 | Cuatro pares SWC1 | Delta aplicado `(0,126953125, 0, −0,5, 1)` a posición y traslación de matriz |
| 120–121 | Callback `0x001372C0` | Cuatro ciclos; RAM completa idéntica |
| 122 | Retorno exterior `0x00194D30` | Posición y matriz conservan el resultado |
| 123 | Consumidor del siguiente ordinal | `posición_anterior` coincide con la salida 122; nueva posición y matriz coinciden entre sí |

El seguimiento usó `contact-follow-v1.json`, **43 filas**, SHA-256
`2a9aeff90585fad91aae44a4ae8c482dceb94dc514a9dc9f8be8e53178e250a3`.
Se amplió el presupuesto de forma explícita a slots 108–135, máximo 28 estados
adicionales y la misma reserva de 512 MiB; solo se necesitaron 108–123.
No hubo restauraciones ni escrituras de PC/RAM/entrada. Las dos llamadas al
corrector son pasadas del mismo contacto, no dos contactos independientes.

La forma seleccionada está en **`tpf1.cld`**, grupo 3 (`+0x16c`), celda 0,
índice 134, stride 80, dirección `0x01848860`. El recurso completo, 37.360 bytes,
coincide con ambas extracciones privadas A/B y el catálogo fijado:
SHA-256 `8263496d10c74c085a01a480d089c9fc5912b071a4f4f1d39c88ed31269461b6`.
No es solo una coincidencia de los 80 bytes de la forma. Su grupo 4 contiene
**ocho formas activas de 48 bytes**: el decoder poligonal y el oráculo mantienen
`CP_NONPOLYGON_UNSUPPORTED`. Esta evidencia no amplía ese contrato ni acredita
una reconstrucción del recurso completo desde su formato intermedio.

El corrector conserva la posición del actor mientras publica su salida en la
entrada del personaje. La rutina exterior aplica el desplazamiento del centro
respecto a la base: X pasa de −17983,400390625 a −17983,2734375 y Z de
21481,78125 a 21481,28125; Y se conserva. Los cuatro pares SWC1 vuelven a pasar
el control de RAM completa y un ciclo. La matriz publica esos valores exactos.
Esta ventana todavía no atribuía la normal del polígono ni la transformación
del vector candidato al delta final; **no son numéricamente el mismo vector**.
La ventana posterior verifica el plano y las conversiones con otros operandos.

Esta ventana terminó pausada en slot **123**, PC `0x001DD434`, ordinal **82593**,
fotograma nativo 21539, ciclo **126929537352**. El movimiento del siguiente
fotograma ya avanzó; se verifica su posición anterior, sin presentarlo como
una conservación de la posición actual del fotograma 82592.

### Normal y punto fijo: captura y contraste

El cotejo estático de los opcodes con las tablas fijadas de PCSX2 identifica
`0x001A19E4` como **VFTOI4 vf5,vf4** y `0x001A19E8` como **VITOF4 vf4,vf5**.
La fuente `VUops.cpp` convierte multiplicando/dividiendo por 16, con conversión
entera hacia cero para los valores finitos acotados de estas muestras.
La predicción sobre el vector 109 es `(0,125, 0, −0,5, 1)`; sobre 111 es
`(0, 0, 0, 1)`. Esto explica de forma candidata la reducción observada, pero
**no constituye una captura de las conversiones de 109/111**. El desplazamiento
final X incluye además la diferencia previa entre centro y base.

`contact-arithmetic-plan-v1.json` fijó la siguiente ventana en ordinal 82594,
normal `0x0019EAA0 → 0x001A251C`, conversiones, suma al centro y consumidor
82595; conserva una parada de respaldo antes del fin de la grabación.
Máximo 32 estados exclusivos, slots 124–155, reserva 512 MiB y ninguna nueva
restauración. Filtro `contact-arithmetic-v1.json`, **52 filas**, SHA-256
`f0755eb694433ca86992fe57dc4adcfe8c02ebd53c7744de97bf3cb713b66e94`.
El usuario cargó las 52 filas y se verificaron antes de continuar. Al observar
la segunda iteración exterior se registró `contact-arithmetic-budget-v2.json`:
ancla 143, slots restantes 144–163, máximo 20 estados y 1.509 MiB libres en
ese momento, manteniendo la reserva. Los planes originales quedan intactos.
Se obtuvieron **39 estados, 124–162**, sin nuevas restauraciones ni escrituras
de PC/RAM/entrada.

| Slots | Iteración exterior | Cadena |
| --- | ---: | --- |
| 124–131 | 0 | Plano, candidato aceptado, corrector, dos conversiones y escritura |
| 132–139 | 0 | Segunda llamada con corrección residual; misma cadena |
| 140–142 | 0 | Suma residual al centro y escritura |
| 143–150 | 1 | Tercera llamada; misma cadena completa |
| 151–158 | 1 | Cuarta llamada con corrección residual |
| 159–161 | 1 | Segunda suma residual y escritura |
| 162 | Siguiente ordinal | Posición anterior y matriz del consumidor |

Son cuatro llamadas dentro de un ordinal y dos iteraciones exteriores,
**no cuatro contactos independientes**. Cada llamada conserva un candidato
tipo 1 de la forma `0x01848860` y propietario Heather. El recurso completo
sigue coincidiendo con las fuentes fijadas en los 39 estados.

El slot **132** conserva la etiqueta de adquisición `before-center-add` y
el rechazo de la expectativa `0x001A1374`: su PC real es `0x0019EAA0`, entrada
de la segunda llamada. El retorno guardado de la primera llamada es
`0x001A1020`, cuya suma/escritura está en `0x001A1060/0x001A1064`; la segunda
retorna a `0x001A1334` y usa `0x001A1374/0x001A1378`. El filtro observaba solo
el segundo sitio. La captura y su recibo no se renombran ni se descartan.

**Plano observado.** Los cuatro pares `0x0019EAA0 → 0x001A251C` producen
`(280632.9375, 0, -952743.8125, 25686636544)` en `0x01FFF920`, idéntico a VF6.
En cada par transcurren 20 ciclos y los 32 MiB de RAM solo pueden cambiar en
ese destino de 16 bytes. La referencia geométrica independiente usa
`(p2-p0) × (p1-p0)` y su coeficiente de plano: error relativo máximo por
componente **1,840386e−7**, inferior al límite explícito de 1e−6.
Es un **plano sin normalizar**; W es su cuarto coeficiente, no la componente
homogénea de un punto ni una normal unitaria.

**Conversión observada.** Cuatro pares VFTOI4/VITOF4 verifican ocho instrucciones,
cada una con un ciclo, RAM completa, GPR bajos, FPR y los otros 31 registros
VF idénticos. Para estos operandos finitos acotados se aplica
`trunc(valor * 16) / 16`:

| Llamada | X/Z antes | Enteros X/Z | X/Z después |
| --- | --- | --- | --- |
| 1 | 5.403743267 / −18.346221924 | 86 / −293 | 5.375 / −18.3125 |
| 2 | 0.011618899 / −0.039446875 | 0 / 0 | 0 / 0 |
| 3 | 5.404334068 / −18.347988129 | 86 / −293 | 5.375 / −18.3125 |
| 4 | 0.012145005 / −0.041232556 | 0 / 0 | 0 / 0 |

Y=0 y W=1 pasan por enteros 0/16 y regresan a 0/1. La salida cruda del
corrector coincide con el candidato y con VF4 antes de convertir. Los cuatro
SQC2 posteriores escriben exactamente VF4 en `entrada+0xd0`, en dos ciclos,
sin cambiar el resto de RAM, GPR, FPR o VF. No se generaliza a desbordamientos,
NaN, denormales ni a toda la aritmética VU.

**Suma al centro y publicación.** Los pares 140/141 y 159/160 observan VADD
con residuo XYZ cero: conservan XYZ y cambian W de 1→2 y 3→4, respectivamente.
Solo VF4 cambia en un ciclo; la RAM permanece idéntica. Sus SQC2 posteriores
escriben exclusivamente los 16 bytes de `entrada+0x10`, en dos ciclos.
Las sumas no nulas del primer sitio quedan delimitadas por 131→132 y 150→151:
el cambio es exactamente `(5.375, 0, -18.3125, 1)`, pero esos intervalos
**no aíslan una sola instrucción**. La siguiente ventana captura ese sitio
en otro ordinal; los intervalos originales conservan este límite.

En 162, la posición anterior es
`(-18095.90625, -0.5670318603515625, 21448.1171875, 1)`: X/Z coinciden con el
centro final 161, Y conserva la del actor y W es 1, aunque el centro tenía W=4.
La posición actual ya avanzó a
`(-18152.22265625, -0.5670318603515625, 21431.53515625, 1)` y coincide en bytes
con la traslación de matriz. Esta ventana terminó **pausada en 162**, PC
`0x001DD434`, ordinal **82595**, fotograma nativo **21543**, ciclo
**126953189354**.

### Suma no nula y origen del microajuste X

Se añadieron **40 estados, 163–202**, sin restauraciones ni escrituras de
PC/RAM/entrada. Tres planes privados fijaron las ventanas y preservaron sus
filtros anteriores:

| Plan/filtro | Filas | Alcance | SHA-256 del filtro |
| --- | ---: | --- | --- |
| `center-follow-v1` | 58 | Ancla 162; slots 163–178, máximo 16; suma en 82596 y búsqueda hasta 82640 | `02ad6655e992ebb6091f953b683f299baa267a421a19234d736f3dba539595d7` |
| `micro-small-v1` | 58 | Ancla 172; seis slots restantes 173–178; refina la búsqueda | `96a51abbb01196fd54e82890c696904ecb5f6cd87175ba9fe8ebbaf76fde7b5a` |
| `micro-origin-v1` | 72 | Ancla 177; slots 178–205, máximo 28; ordinal 82600 | `8689cabe0865710e73f2c5a70d1a4f6aa14e8053f5d85f7f407600b35e87b5da` |

El último presupuesto registró 1.068 MiB libres, con reserva de 512 MiB; se
necesitaron 25 estados de sus 28 previstos. Las 40 capturas vuelven a enlazar
actor, recursos, reproducción, ordinal, código ELF/RAM y `tpf1.cld` completo.

**Suma no nula aislada.** Slots 163–165 y 166–168, ordinal 82596, capturan
`0x001A1060 → 0x001A1064 → 0x001A1068` en las dos iteraciones exteriores.
VADD aplica `(5.375, 0, -18.3125, 1)`; el resultado es exactamente representable
en f32. Cambia solo VF4 en un ciclo, con RAM completa, GPR bajos, FPR y los
otros VF idénticos. SQC2 escribe solo `entrada+0x10` en dos ciclos.

| Iteración | Centro X/Z antes | Centro X/Z después |
| ---: | --- | --- |
| 0 | −18185.755859375 / 21441.556640625 | −18180.380859375 / 21423.244140625 |
| 1 | −18213.9140625 / 21433.265625 | −18208.5390625 / 21414.953125 |

Y se conserva; W cambia 0→1 y 2→3. El comprobador usa fracciones exactas y
rechaza sumas que necesiten redondeo: esta prueba no fija una ley general VU.
La posición anterior de 169 enlaza X/Z con el segundo centro publicado.

**Caso descartado de la búsqueda.** El slot 169 esperaba el consumidor, pero
se detuvo antes en `0x0019FE38`, ordinal 82597. Se conserva la etiqueta
`center-follow-consumer`, el recibo y el rechazo de la expectativa. El estado
final de contacto es cero, pero la resta centro−base produce
`(5.126953125, 0, -33.875, 1)` y el centro intermedio conserva W=2. No es el
microajuste histórico: demuestra que **estado final cero por sí solo no
excluye correcciones de una pasada anterior**. Slots 169–171 aíslan VSUB y su
SQC2; 172 confirma la posición y matriz resultantes. El filtro refinado añade
proximidad de un ULP en X/Z y W intermedio cero; sigue siendo un filtro de
búsqueda, no una prueba general de ausencia de contacto.

**Repetición del residuo pequeño.** Slots 173–177, ordinal 82599, capturan
centro−base = `(0.001953125, 0, 0, 1)`, su escritura en la pila y el par SWC1
`0x0019FE7C → 0x0019FE80`. X del actor cambia
−18406.240234375→−18406.23828125; solo esos cuatro bytes cambian en un ciclo.
Mitad, punto intermedio y centro final coinciden con la reconstrucción por
dos sumas truncadas. Esta ventana aún no contenía sus instrucciones iniciales.

**Origen capturado.** Slots 178–202 siguen toda la actualización 82600:

| Slots | Punto | Resultado |
| --- | --- | --- |
| 178–180 | VSUB posición−posición anterior y SQC2 | Desplazamiento `(-67.068359375, 0, 20.04296875, 0)` |
| 181–183 | VSUB base−desplazamiento y SQC2 | Centro inicial X=−18406.23828125 |
| 184–186 | VMULx por 0.5 y SQC2 | Mitad `(-33.5341796875, 0, 10.021484375, 0)` |
| 187–189 | Primer ADD.S X y rama con SWC1 en delay slot | Centro X=−18439.771484375 |
| 190–191 | Dos retornos del corrector | Estado y vector de corrección cero |
| 192–194 | Segundo ADD.S X y rama con SWC1 | Centro X=−18473.3046875 |
| 195–196 | Otros dos retornos del corrector | Estado y vector de corrección cero |
| 197–199 | VSUB centro−base y SQC2 | Residuo X=+0.001953125, Z=0 |
| 200–201 | SWC1 de publicación X | Actor X=−18473.3046875 |
| 202 | Consumidor | Posición y traslación de matriz idénticas |

Las operaciones VU de esta tabla tienen resultados exactamente representables;
cada par verifica un ciclo y el resto de RAM/registros preservado. Los SQC2
comparan toda la RAM y dos ciclos. Cada ADD.S cambia solo FPR0 en un ciclo;
el primer resultado distingue truncamiento de redondeo al más cercano
(−18439.7734375). Ambos coinciden también con la suma enmascarada de la fuente
fijada de PCSX2: estos operandos no distinguen ambas reglas entre sí.
Los pares 188→189 y 193→194 abarcan **la rama y su SWC1 en delay slot**, tres
ciclos y un único destino de cuatro bytes, no una sola instrucción.

El centro inicial, las dos mitades conservadas, cada operando FPR y el centro
final están enlazados en bytes. Las cuatro llamadas al corrector conservan
estado/vector cero y un solo personaje registrado; las dos iteraciones son
0/1. La posición del actor permanece idéntica hasta publicar X. El consumidor
202 conserva Y/Z/W y publica la traslación exacta. Así queda atribuido el
microajuste X de **esta actualización** al redondeo al recomponer el movimiento
en dos mitades, sin una corrección de contacto en los cuatro retornos observados.

La reconstrucción del caso histórico 98 produce el mismo residuo X=+1/512;
la alternativa al más cercano produce −1/512. Esa comparación conserva su
carácter de explicación candidata del recorrido histórico: no se restauró
82569 para capturar sus instrucciones. Z coincide en los extremos, pero no
se aislaron sus sumas escalares; el residuo Y histórico sigue fuera de esta
atribución. Tampoco se generaliza a todas las consultas o modos aritméticos.

La sesión queda **pausada en 202**, PC `0x001DD434`, ordinal **82600**, fotograma
nativo **21553**, ciclo **127012140056**. Posición final:
`(-18473.3046875, -0.5670318603515625, 21452.0625, 1)`.

### Preparación de pared/esquina y giros restantes

Se reabrió 202 y se cotejó íntegramente `tpf1.cld` contra ambas extracciones.
El inventario diagnóstico delimita seis cuadriláteros verticales del grupo 3,
índices **133–138**, presentes una vez cada uno en la lista de la celda 0.
Sus aristas verticales compartidas y planos no paralelos forman estas seis
parejas: **133/137, 133/138, 134/135, 134/138, 135/136 y 136/137**. Son
referencias geométricas para la captura; no prueban contactos simultáneos,
accesibilidad de la esquina ni respuesta del corrector. El recurso completo
sigue rechazado como `CP_NONPOLYGON_UNSUPPORTED` tanto por decoder como por
oráculo: no se cambia el contrato por sus ocho formas activas de 48 bytes.

El comprobador puro local `wall_references.py` exige un registro inmutable de
80 bytes, cabecera de cuadrilátero, coordenadas finitas acotadas, W=1,
coplanaridad y perímetro vertical rectangular. Calcula la normal y las aristas
con racionales exactos. Distingue una arista compartida de un único vértice,
paredes paralelas, alturas diferentes y duplicación de punteros. No llama
«esquina física» a una pareja geométrica ni cuenta dos pasadas como dos
contactos distintos. Las **38 pruebas** pasan; cobertura individual de
**50/50 sentencias y 10/10 ramas**. Se cotejan otras cinco ventanas ELF/RAM
para el recolector de candidatos y el escritor de giro/movimiento.

La grabación existente no contiene giro izquierdo ni giro en marcha. Se
detuvo su reproducción mediante la interfaz mientras PCSX2 seguía pausado;
observaciones anteriores/posteriores conservan exactamente PC, ciclo y 512
bytes del actor de 202. **No se reanudó ni restauró.** Se preparó el directorio
exclusivo `heather-movement-profiles-v3` y el diálogo para
`recordings/left-moving-v1.p2m2`. Sus controles
previstos son izquierda sobre el sitio/liberación y caminar+izquierda,
caminar recto/liberación. El archivo de 72 filtros se conserva: las 20
condiciones activas están limitadas al ordinal 82600; las otras son `0`.
Una eventual reproducción nueva deberá declarar su frontera diagnóstica.

El usuario realizó el clic físico Al encender → Guardar estado. Se verificó
el aviso de compatibilidad y se confirmó el diálogo. La grabación está
iniciada desde estado; la semilla tiene SHA-256
`07355c5d7a56f91d23de9338bd98f716e34ed45a83804df3001fd44f41bc433c`
y tamaño 15.336.864 bytes. Sus **32 MiB de RAM, estructura EE completa de
1160 bytes, FPR, PC y ciclo coinciden con 202**. Dos observaciones PINE
posteriores cotejan el actor y el ordinal, con pausa comprobada antes/después.
Se conserva ordinal 82600/fotograma 21553/ciclo 127012140056; **cero
restauraciones adicionales**. El archivo de controles todavía tenía tamaño
cero al verificar la semilla por el buffer de escritura; su cabecera y
segmentos se auditarán después de detener la grabación.

**Pendiente de interacción:** se pidió al usuario izquierda 1 s → liberar
1 s → arriba+izquierda 2 s → solo arriba 1 s → liberar 1 s → pausar, sin J,
restauraciones ni reinicios. La interfaz queda sin intervención automatizada
durante la maniobra. Preparado `audit_profile_input.py` para el archivo cerrado;
todavía no se ejecuta ni atribuye movimiento a los controles. Al verificar
la semilla quedaban 664 MiB, con reserva de 512 MiB; sigue pendiente liberar
2 GiB para la batería nueva. No hay giros/contactos nuevos verificados.

## Verificación y artefactos

- **258 pruebas sintéticas**: 52 del comprobador SQC2, 34 de SW/SWC1, 47 del
  comprobador VU, 35 de suma exacta/candidato de dos mitades, 52 de origen
  y 38 de referencias geométricas de paredes.
  Offset negativo, fuente GPR/FPR/VF, escritura
  idempotente, límites, identidad de sesión, PC, ciclo, registros, opcode,
  mutaciones de RAM y rechazo de operandos fuera del alcance. Los seis módulos
  tienen cobertura individual de líneas y ramas del **100 %**; el comprobador
  VU cubre 65/65 sentencias y 2/2 ramas; los dos nuevos cubren 30/30 y 53/53
  sentencias, sin ramas contadas por coverage. El comprobador VU anterior
  mantiene su restricción de suma XYZ cero; la suma no nula usa otro comprobador.
- Los comprobadores son puros; adquisición PINE, comparación de archivos y
  presentación de resultados se mantienen separadas. No se introduce un solver
  ni se trasladan direcciones PS2 al núcleo del visor.
- Auditores normal y con Python `-O`: informes byte por byte iguales. Nueve
  ventanas ELF/RAM en caminar/parada y doce en reloj/giro/suelo. El fallo de
  redondeo inicial sigue explícito. No se ha ejecutado un pipeline remoto.
- `tools.qa.check_repository`: PASS, cero errores; `git diff --check`: PASS.
- `reports/local/heather-movement-walk-stop-v1.json`, SHA-256
  `47407f79952684cf3ee758b4e321fe1a006c72e28d824cf0a3546b85b5ed8b5e`.
- `reports/local/heather-movement-clock-turn-ground-v1.json`, SHA-256
  `b6f7f7a3ecfa876abd7e7cc98f1106cbf7dde672a7cd687d960d5f02352f91b9`.
- `reports/local/heather-movement-rounding-candidate-v1.json`, SHA-256
  `9073a935d69b44dc202d4a419ff69158ad18d4141b3073f85551740a4309dc7a`.
  Tres muestras existentes y fuentes de PCSX2 identificadas por hash;
  salida normal/`-O` idéntica, sin nuevas capturas ni afirmación de causalidad.
- `reports/local/heather-movement-rounding-capture-v1.json`, SHA-256
  `49c888e6e0bce34f4232628990c7f66c3f5e433457e4cc3d2f7f4e011d6bb037`.
  Ocho estados nuevos reabiertos, par ADD.S y tres consultas/consumidores;
  salida normal/`-O` idéntica. El alcance y los operandos distintos quedan
  explícitos en el informe.
- `reports/local/heather-movement-horizontal-capture-v1.json`, SHA-256
  `e28b637ebabf4acb765cbe9502a8a67e6eb64c4893e34501edf0816a5af1d877`.
  28 estados nuevos, ocho pares SWC1, comparación de operandos originales,
  microajuste separado del contacto aceptado, lista/forma y recurso A/B.
  Normal/`-O` idénticos; discrepancia de adquisición 96 preservada. Al cerrar
  esa ventana había seis pares SQC2 y doce pares escalares SW/SWC1.
- `reports/local/heather-movement-contact-arithmetic-v1.json`, SHA-256
  `396f90c80710e01ba6b99c01b7eaad5a02e1b6a3d68e3a8677e8569d36f35709`.
  39 estados reabiertos, cuatro planos, ocho conversiones, seis SQC2 y dos
  VADD residuales; normal/`-O` idénticos. Preserva la discrepancia 132 y las
  sumas no nulas delimitadas. Al cerrar esa ventana había doce pares SQC2 y
  doce SW/SWC1; las conversiones y sumas se contabilizan aparte.
- `reports/local/heather-movement-microadjustment-candidate-v1.json`, SHA-256
  `573656d352c343341a934873307b3ac97f2567e8a439a0b8df45c4831c6a16ff`.
  Caso histórico 98, dos ejes y cuatro publicaciones ya existentes;
  reconstrucción candidata y alternativa al más cercano. Normal/`-O` iguales.
- `reports/local/heather-movement-center-origin-v1.json`, SHA-256
  `3fa5d9631b18be5c8a5b18ab210700b03f3d3d164e9969b3fd8c4c8442785e67`.
  40 capturas nuevas: dos sumas no nulas, cinco VSUB, un VMULx, ocho SQC2,
  dos ADD.S, dos ramas con SWC1 y dos SWC1 de posición; cuatro retornos de
  corrección cero y matriz final. Normal/`-O` iguales. HM-T2b suma veinte
  pares SQC2 y catorce SW/SWC1 de una instrucción; las dos ramas con delay
  slot se cuentan aparte. Se conserva la discrepancia de adquisición 169.
- `reports/local/heather-movement-wall-reference-inventory-v1.json`, SHA-256
  `bb383b3bc6465ad2d6e8f6b56c65240c9c6c98e95e1db8a72ba2c7919a6ced1d`.
  Seis paredes y seis aristas compartidas no paralelas; A/B/RAM completos,
  listas y cinco ventanas de código. Normal/`-O` idénticos. Preparación
  geométrica, sin nueva observación de esquina ni giros.
- `reports/local/heather-movement-profile-seed-v1.json`, SHA-256
  `1c87d3c693c4d904973d23d26095f6b5c10032d8d6dc9af0afa59299b8ca5fb6`.
  Origen de la nueva grabación verificado contra 202 y la sesión pausada;
  no acredita todavía los controles ni el movimiento posterior.
- Herramientas locales en `build/heather-movement`: `capture_b.py`,
  `peek_b.py`, `audit_b.py`, `audit_extra.py`, `scalar_evidence.py`,
  `vu_evidence.py`, `audit_contact_arithmetic.py`, `center_evidence.py`,
  `origin_evidence.py`, `audit_micro_candidate.py`, `audit_center_origin.py`,
  `wall_references.py`, `audit_wall_inventory.py`, `prepare_profile_recording.py`,
  `verify_profile_seed.py` y `audit_profile_input.py`
  y sus pruebas. Los informes
  contienen metadata; los payloads permanecen privados.

```sh
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_store_evidence.py build/heather-movement/test_scalar_evidence.py build/heather-movement/test_vu_evidence.py build/heather-movement/test_center_evidence.py build/heather-movement/test_origin_evidence.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_b.py /tmp/hm-walk-stop.json
rtk proxy .venv/bin/python build/heather-movement/audit_extra.py /tmp/hm-clock-turn-ground.json
rtk proxy .venv/bin/python build/heather-movement/audit_rounding_candidate.py /tmp/hm-rounding-candidate.json
rtk proxy .venv/bin/python build/heather-movement/audit_rounding_capture.py /tmp/hm-rounding-capture.json
rtk proxy .venv/bin/python build/heather-movement/audit_horizontal_capture.py /tmp/hm-horizontal.json
rtk proxy .venv/bin/python build/heather-movement/audit_contact_arithmetic.py /tmp/hm-contact-arithmetic.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_contact_arithmetic.py /tmp/hm-contact-arithmetic-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_micro_candidate.py /tmp/hm-micro-candidate.json
rtk proxy .venv/bin/python build/heather-movement/audit_center_origin.py /tmp/hm-center-origin.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_center_origin.py /tmp/hm-center-origin-optimized.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_wall_references.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_wall_inventory.py /tmp/hm-wall-reference-inventory.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

**Siguiente: HM-T2b.6**, completar y auditar los controles de la grabación
iniciada de giro izquierdo y giro en marcha; ampliar pared/esquina usando las seis referencias
geométricas y capturar su respuesta física. La suma no nula y el origen del
microajuste X quedan verificados en el alcance descrito; el residuo Y histórico
queda separado. El plano y las conversiones conservan su alcance de cuatro
llamadas, sin cerrar el solver general. La comparación
acotada de operandos de HM-T2b.5 queda verificada; sus diferencias de ciclos,
la autoridad y el contrato
siguen pendientes; HM-T2, HM-T3 y F06.01 siguen abiertos.
El build físico aceptado `7250f427ffb9` permanece sin cambios.
