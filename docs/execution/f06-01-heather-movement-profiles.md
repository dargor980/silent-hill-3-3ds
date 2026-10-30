# HM-T2b: perfiles, reloj y contactos de Heather

**Estado: en curso.** HM-T2b.1–4 verifican un alcance acotado: caminar,
parada, giro derecho, reloj PAL de 2 ticks y consulta de suelo/registro de
formas. Se añadió una cadena de contacto poligonal hasta posición y matriz,
y se verificaron el plano y las conversiones a punto fijo de cuatro llamadas.
Se aislaron además dos sumas no nulas al centro y el origen del microajuste X
en una actualización con cuatro retornos de corrección cero. Otro recorrido
verifica la combinación de las paredes 25/26, sus pasadas intermedias y el
balance del desplazamiento hasta la publicación histórica. Quedan abiertas
otras clases de contacto, diferencias de ciclos, cruce exacto de ±pi y autoridad
general del movimiento. **No se integra todavía la
habitación ni se modifica el visor.** Requisitos
[HM03–HM04 y tareas HM-T2b](../specs/sh3-3ds/heather-movement.md).

## Procedencia y continuidad

- Heather original, actor `0x004481D0`, tipo `0x0100`, MDL522/ANM525 y callback
  `0x001986C0`. Recursos, PC, registros bajos, RAM, ordinal y canales se
  revalidan desde los estados completos; no se confía solo en los recibos.
- Slots 16–203: instancia privada de HM-T2a, PID observado 18885; ejecutable SHA-256
  `54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
- **387 estados nuevos**: 239 en slots 16–254 y 148 en C00–C148,
  excluyendo C127, que es una copia de carga y no una captura. Recibos 16–202:
  `/Users/germancontreras/sh3-private-data/heather-movement-v2`.
  Los estados siguen en `heather-movement-v1/states`, según el perfil activo.
  Capturas y recursos permanecen privados; solo se publica metadata local.
  El final manual 203 tiene recibo en `heather-movement-profiles-v3` y estado
  en `heather-movement-v1/states`. Los estados/recibos 204–254 están en
  `heather-movement-profiles-v4`, proceso nuevo PID 4124. Sus quince restauraciones
  y su continuidad interna se detallan abajo; no continúan el proceso anterior.
  C00–C148, excepto C127, tienen recibos en `heather-movement-combiner-v1/captures` y usan los
  slots físicos exclusivos 00–148 del perfil v4, salvo 127. La etiqueta C distingue
  estos estados de los slots de otras sesiones; ninguno se sobrescribe.
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
- Las grabaciones contienen controles normales grabados por el usuario.
  No se escribe PC, RAM ni entrada artificial para obtener estos resultados.
  Se mantienen las comprobaciones de originales y la reserva de 512 MiB.
- El usuario cargó los sucesivos juegos de filtros desde ajustes. Los puntos antiguos
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
cruce de ±pi entre las dos muestras. Izquierda y giro en marcha se verifican
en las ventanas posteriores descritas abajo.

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

Esta ventana terminó **pausada en 202**, PC `0x001DD434`, ordinal **82600**, fotograma
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

El usuario completó los controles y se preservó el final en **203**, antes
de detener la grabación: PC `0x00081FC0`, ordinal 82700/fotograma 21754,
ciclo 128201163763. La auditoría del archivo cerrado verifica cabecera,
202 fotogramas, cero deshacer, segundo puerto vacío y todo el payload con
paquetes literales independientes: izquierda 1–54, arriba+izquierda 55–126
y arriba 127–202. **No contiene intervalos de liberación**, aunque estaban
en la maniobra solicitada; no se declara una parada. SHA-256 del archivo:
`68bf855902146315f5eba0565af762c4f039ae4f15ea33ad0d318989a67aa960`.
La posición final es `(-18039.69921875,-0.5670318603515625,21464.6328125,1)`.
Ese extremo y los controles no prueban por sí solos los giros intermedios.

### Reproducción de izquierda, giro en marcha y referencia recta

El 28 de octubre la instancia anterior ya no estaba disponible. La selección
de reproducción solicitada en ella quedó sin ancla posterior verificada; no
se afirma que continuara. Se recuperó una copia privada en el proceso 4124:
**204** ancla la restauración de arranque y **205** la carga mediante
«Grabación de entrada → Reproducir». Ambas coinciden exactamente con la semilla
en 32 MiB de RAM, estructura EE completa, FPR, PC y ciclo. Son **dos fronteras
de restauración declaradas** en este proceso. Originales, perfil anterior y
grabación permanecen iguales. Se amplió el presupuesto al comprobar espacio,
manteniendo la reserva de 512 MiB y destinos exclusivos.

Los **18 estados 206–223** siguen desde 205 sin nuevas restauraciones ni
escrituras artificiales de PC, RAM o controles. Cada ventana captura entrada
del escritor, antes/después de SQC2, antes/después de SWC1 de yaw y consumidor:

| Slots | Ordinal / nativo | Entrada | Descriptor | Yaw antes → después | Delta X/Z del escritor |
| --- | --- | --- | ---: | --- | --- |
| 206–211 | 82610 / 21573 | `0x8000`, izquierda | 108 | −2,0723900795 → −2,1603899002 | 0 / 0 |
| 212–217 | 82640 / 21633 | `0x9000`, arriba+izquierda | 109 | 1,5707968473 → 1,4827967882 | +28 / −0,001953125 |
| 218–223 | 82680 / 21713 | `0x1000`, arriba | 109 | −0,5412034988 → mismo valor | −14,423828125 / +23,998046875 |

Los tres pares SQC2 verifican fuente VF4, dos ciclos y que ningún otro byte
de RAM cambia. Los tres pares SWC1 verifican FPR0, un ciclo, GPR bajos/FPR
conservados y exclusivamente los cuatro bytes de yaw como destino posible.
También se acepta la escritura idempotente de la caminata recta. Velocidad
angular observada: −2,2000000477 en los dos giros y cero al caminar recto;
intervalo 0,0399999991 en las tres muestras. No se generaliza el redondeo ni
se afirma haber aislado aquí el productor de la velocidad o la trigonometría.

La orientación escrita alcanza el consumidor; las tres traslaciones de matriz
coinciden en bytes con posición y sus rotaciones tienen error máximo
**1,407209e−7**, dentro del límite previo de 1e−6. En el giro sobre el sitio
la posición final no cambia. En marcha hay un ajuste posterior Z=−1/512.
En la referencia recta la corrección posterior es
**X=+7,626953125, Z=−26,001953125**, hasta
`(-17988.45703125,-0.5670318603515625,21479.76953125,1)`.
Estas correcciones quedan delimitadas entre escritor y consumidor: **no se
atribuyen todavía a una forma o esquina**. El primer registro residual de 223 contiene
un puntero al índice 134 ya conocido; su tipo no acredita el contador; esto no sustituye la
captura de su aceptación y aplicación en ese ordinal.

Las tres ventanas terminan pausadas en **223**, PC `0x001DD434`, ordinal **82680**,
fotograma **21713**, ciclo **127955860263**. La auditoría reabre todos los
estados, coteja recursos/código, recibos, reloj, canales e identidad del
proceso. Las salidas normal y `-O` son idénticas. Giro izquierdo y giro en
marcha quedan verificados en estas muestras; HM-T2b.6 sigue abierta por las
variantes de pared/esquina y las atribuciones pendientes.

### Búsqueda acotada de otro contacto

Se respaldaron 74 filtros y el usuario cargó los nuevos desde ajustes. Se
verificaron en la interfaz las tres condiciones activas: aceptación estática
con propietario Heather y puntero distinto de `0x01848860`, entrada del
corrector con un filtro inicialmente interpretado como contador y parada final.
La errata siguiente retira esa interpretación. El rango quedó limitado a
ordinales **82681–82700**, anulando los demás puntos con condición `0`.

La continuación llegó directamente al límite final, sin paradas intermedias
observadas ni nuevas restauraciones. **224** conserva PC `0x001DD434`,
ordinal **82700**, nativo **21753**, ciclo **128191881327** y posición
`(-18124.39453125,-0.5670318603515625,21439.69140625,1)`, con traslación exacta
de matriz. El recurso CLD completo coincide con A/B; el primer registro residual es de tipo 1 y apunta al índice 134. El resultado
solo acredita que no se observó otra parada con esos filtros; el filtro de
multiplicidad era incorrecto y no permite descartar varios candidatos.

Se conserva además una discrepancia: el final manual 203 tiene el mismo
ordinal, pero PC `0x00081FC0` y nativo 21754, con distinta posición/orientación.
**No son la misma fase de captura** y no se infiere la causa de la diferencia.
La equivalencia completa de trayectoria queda pendiente de comparación en
la misma fase; los pares de instrucciones y las matrices auditadas conservan
su alcance local, sin ampliar esa conclusión a toda la reproducción.

Se detuvo la reproducción por la interfaz manteniendo la pausa. Dos lecturas
del observador verifican PC/ciclo, 512 bytes del actor y ordinal contra 224.
El usuario realizó el clic físico Al encender → Guardar estado; se verificó
el aviso de compatibilidad y se inició `wall-corner-v1.p2m2` desde estado.
Su semilla de 14.925.940 bytes, SHA-256
`6aa193b97f1ba352efc87c5b42be8522f1b9052da76eb613b00370bc9f92b0c0`,
coincide exactamente con 224 en RAM, estructura EE, FPR, PC y ciclo. Dos
lecturas posteriores del observador mantienen la pausa y la coincidencia
de actor/ordinal. **Cero restauraciones adicionales al iniciar la grabación.**

### Recorrido de pared y nueva frontera diagnóstica

El usuario completó el recorrido con controles normales. El final **225**
conserva PC `0x00081FC0`, ordinal **84060**, nativo **24474**, ciclo
**144244376563** y posición `(-22424.125,-0.5670318603515625,19434.8671875,1)`.
Se cerró la grabación por la interfaz manteniendo la pausa. Su auditoría
independiente verifica cabecera, todos los paquetes literales, semilla y
extremo manual: **2722 fotogramas nativos, 74 segmentos, cero undos**. Hay
↑, ←, → y ↓, combinaciones diagonales y liberaciones; no hay J/carrera.
Un fotograma nativo no se equipara a una actualización del juego.

La copia se reprodujo con autorización del usuario, declarando otra frontera
**226**. La comparación estricta inicial **falló**: RAM completa, CPU
interpretada, PC/ciclo, FPR y VU0 VF coinciden, pero dos bytes de la estructura
EE difieren. Son parte de `cpuRegisters.nextEventCycle`, offset 1120 confirmado
por compilación contra las cabeceras fijadas: la distancia al ciclo actual
cambia de **994 a 16 ciclos**. No se alteró ni enmascaró ese campo para aprobar
el cotejo. También se conservan los ajustes del planificador de contadores;
la llamada concreta que produce el valor 16 no se trazó dinámicamente.

Esta es la tercera restauración del proceso 4124. Desde 226 no hay nuevas
restauraciones ni escrituras de RAM/PC. Las capturas posteriores acreditan
instrucciones y consultas locales; **no equivalencia temporal ni reproducción
exacta de toda la trayectoria manual**. El rechazo y los originales permanecen
conservados.

### Errata del contador y consulta de dos paredes

`0x01D055A0` contiene el **tipo del primer registro**, no el contador. Los
registros tienen **80 bytes**: tipo en `+0`, corrección en `+0x10`, puntero de
forma en `+0x20`, normal en `+0x30` y ángulo en `+0x40`. El contador se observa
en `[s3]` durante la incorporación, `[sp+0x5C]` en el llamador y `a3` a la
entrada de `0x001A1E30`. Los registros fuera del contador pueden ser residuos
de una consulta anterior.

El filtro histórico `[0x1d055a0]>1` comprobaba el tipo, por lo que se retiran
`residual_candidate_count=1` del informe de 224 y cualquier inferencia de
«sin varios candidatos» basada en ese filtro. El informe original y su hash
se conservan, acompañados de esta errata. Las cadenas anteriores con `a3=1`
y contador de incorporación observado mantienen su evidencia independiente.
El lector diagnóstico nuevo exige un contador externo explícito; 31 pruebas
comprueban tipos, paso de 80 bytes, cola residual, límites y datos inválidos.

**227** alcanza el polígono **138** en el ordinal 82705. **228** vuelve a la
aceptación estática en 82706; su etiqueta histórica
`wall-route-multiple-candidates` fue una predicción equivocada: su PC real es
`0x001A1B5C`, antes de incorporar el registro, no la entrada del corrector.
Ambas formas están enlazadas a la lista del mapa y al propietario Heather;
el CLD completo coincide con A/B. En **228→229** el contador real pasa de uno
a dos, conserva el primer registro 134 y añade el tipo 2/puntero/vector de 138.

La continuación **229–247**, sin restaurar, observa cuatro llamadas en el
mismo ordinal **82706**, nativo **21765**:

| Entrada → retorno | Candidatos | Tipos antes → después | Corrección XYZ devuelta |
| --- | ---: | --- | --- |
| 230 → 233 | 2: 134, 138 | `(1,2)` → `(1,−1)` | `(3.251024723,0,−11.037154198)` |
| 234 → 235 | 1: 134 | `1` → `1` | `(0.010403274,0,−0.035319179)` |
| 237 → 240 | 2: 134, 138 | `(1,2)` → `(1,−1)` | `(3.259673119,0,−11.066787720)` |
| 241 → 242 | 1: 134 | `1` → `1` | `(0.001840916,0,−0.006250025)` |

Las cuatro normales observadas coinciden con la referencia independiente,
error máximo **5,126710e−8**, límite previo `1e−6`. La primera tentativa de
la auditoría usó el sentido de vértices opuesto del helper geométrico y falló;
se corrigió al orden del productor ya fijado, `(p2−p0) × (p1−p0)`, sin cambiar
la tolerancia. Los planos 134/138 comparten una arista vertical y no son
paralelos. En estas llamadas dobles, sin embargo, **138 se descarta** y la
salida es idéntica a la corrección de 134. El escritor concreto de `−1` y su
rama siguen pendientes de captura.

**243→244** y **245→246** aíslan dos SWC1, un ciclo cada uno, con RAM completa
sin otros cambios. El desplazamiento publicado es X **+6,5**, Z
**−22,064453125**, Y sin cambio. **247**, PC `0x001DD434`, ciclo
**128262599652**, conserva posición y traslación de matriz idénticas:
`(-18186.98828125,-0.5670318603515625,21421.25,1)`.
Se acreditan dos candidatos simultáneos y su filtrado; no una combinación
física de ambos ni una reimplementación completa del corrector.

### Búsqueda con contador corregido

Se cargaron y verificaron filtros que usan `a3` en la entrada y `[sp+0x5C]`
en el retorno, con alcance 82707–84060. La primera parada **248**, sin otra
restauración, llega al retorno `0x001A1924`, ordinal **82709**, nativo **21771**,
ciclo **128297871374**. El contador real es 2: los registros 134/138 conservan
tipo 2 y **el mismo vector de corrección**. El propietario se comprueba desde
la entrada efectiva `s5=0x01D083E0`, cuyo `+0x60` apunta a Heather; no se infiere
solo de la condición del filtro, que refería al banco anterior.
La salida efectiva es `(2.508437872,0,−9.620161057,2)`, con bandera 2.
No se interpretan todavía estos registros como dos empujes independientes.
El usuario cargó los cinco puntos preparados. **249–253** continúan la misma
sesión y el mismo ordinal, sin restaurar. **249→250** y **251→252** aíslan
los SWC1 de X y Z, un ciclo cada uno; sus operandos y la RAM completa confirman
que solo cambian los cuatro bytes de destino. El delta publicado es
`(4.064453125,0,−17.751953125,0)`. La posición no cambia entre el retorno 248
y la pausa anterior al primer SWC1.

**253**, PC `0x001DD434`, ciclo **128297989844**, nativo **21771**, conserva
posición y traslación de matriz idénticas:
`(-18244.7578125,-0.5670318603515625,21404.08984375,1)`.
La orientación y la posición anterior del actor permanecen sin cambios.
La pila del escritor contiene el delta observado y el centro efectivo tiene
los mismos X/Z finales. En esa pausa, la corrección residual y su bandera ya
son cero; **no se atribuye el desplazamiento completo al primer vector de
248** porque las llamadas intermedias no se capturaron individualmente.

### Combinador: candidato estático y búsqueda acotada

La función `0x001A2340–0x001A24CC` tiene una primera rama que copia el vector
si el contador de aplicaciones es cero. En las siguientes, el código suma
los vectores, selecciona X y Z dentro del intervalo delimitado por los dos
operandos, publica el resultado e incrementa el contador. Esta lectura del
código fijado se conserva como **candidata**, separada del contador de
registros y de la aceptación/descarte de formas.

Se implementó una referencia matemática local, sin emular las ramas MIPS.
Su contrato diagnóstico, previo a cualquier uso en el núcleo, es:

- CUANDO reciba vectores, DEBERÁ exigir 16 bytes, componentes binary32 normales
  o cero positivo, finitas y de magnitud máxima `1e6`.
- CUANDO el contador de aplicaciones sea cero, DEBERÁ copiar el vector entrante;
  el perfil admitirá únicamente contadores enteros 0–7.
- CUANDO ya exista una aplicación, DEBERÁ exigir sumas exactamente
  representables antes de limitar X/Z al intervalo de sus operandos.
- SI una suma requiere redondeo o aparecen subnormales, cero negativo,
  infinitos, NaN o entradas fuera del perfil, DEBERÁ rechazarlas; no atribuirá
  al host una semántica general de VU.

Las **30 pruebas nuevas** incluyen vectores idénticos, signos iguales/opuestos,
ambos órdenes, copia inicial, cancelación, contador y límites numéricos.
La referencia alcanza **26/26 sentencias y 8/8 ramas**, 100 %. Su resultado
para los dos registros de 248 coincide byte por byte con la salida conservada:
XYZ no se duplica y W pasa a 2. Es una inferencia compatible con código y
retorno; faltan los operandos observados a la entrada de esa invocación.
El código estático también contiene un tipo `−2` en otra ruta de filtrado;
el lector diagnóstico actual lo rechaza y no se amplía sin evidencia propia.

Se cargaron filtros limitados al resto del recorrido (**82710–84060**) para
la segunda aplicación de dos registros tipo 2 de 134/138 con vectores
idénticos. El primer intento de adquisición fue rechazado por `not paused`:
no se creó ningún estado ni se consumió un slot. La reproducción llegó a
**254**, PC `0x001DD434`, ordinal **84060**, nativo **24473**, ciclo
**144234680037**, sin otra parada observada. **No se capturó el par de la
función**; esto no acredita ausencia de llamadas fuera de ese filtro/tramo.
El slot 255 permanece sin usar.

El extremo 254 coincide byte por byte en posición y orientación con el
manual 225: `(-22424.125,-0.5670318603515625,19434.8671875,1)`, yaw
`2.2428126335144043`. Las fases difieren: 225 está en PC `0x00081FC0`, nativo
24474, y tiene 9.696.526 ciclos más. Por ello se registra **coincidencia
espacial del extremo**, no equivalencia temporal ni de trayectoria completa.
El auditor distingue explícitamente el esquema del recibo manual, que no
incluye GPR, y vincula su estado completo mediante el hash fijado; el primer
intento asumió el esquema diagnóstico y falló con `KeyError: gpr`.
Al cerrar esa búsqueda, PCSX2 quedó pausado en 254, sin nuevas restauraciones
desde 226. La investigación siguiente declara su propia frontera.


### Entrada y retorno del combinador: copia y vectores idénticos

Se reutilizó la grabación verificada en otra copia privada, con extremo 254
preservado. El usuario cargó los filtros de entrada/retorno y autorizó esa
reproducción desde su semilla. No se reinicia el proceso ni se introduce
entrada artificial. Se reservaron C00–C15 sin reutilizar archivos existentes.

**C00** conserva PC `0x001DD434`, ordinal 82700 y ciclo 128191881327. Es la
**cuarta restauración** del proceso 4124. RAM, CPU interpretada, PC/ciclo,
FPR y VF coinciden con la semilla; vuelve a diferir `nextEventCycle` en los
mismos dos bytes, distancia **994→16 ciclos**. El cotejo estricto se mantiene
rechazado, sin modificar ni enmascarar campos. Comparado con la restauración
226, C00 sí coincide en RAM, registros, ciclo y estructura EE completa.
La continuación se limita a evidencia local de llamadas, sin equivalencia
global de trayectoria o tiempos.

**C01–C06** corresponden al ordinal **82709**, nativo **21771**, entrada
`0x9000`, y continúan desde C00 sin restauraciones. El recurso original de
Heather, canales, CLD completo A/B/RAM y código ELF se revalidan desde cada
estado. El propietario se verifica en la entrada efectiva `0x01D083E0`.

| Par | Función/retorno | Contador de aplicaciones | Resultado observado | Ciclos |
| --- | --- | --- | --- | ---: |
| C02 → C03 | `0x001A2340 → 0x001A22F8` | 0 → 1 | Copia el primer vector, W=1 | 13 |
| C04 → C05 | `0x001A2340 → 0x001A22F8` | 1 → 2 | Conserva XYZ al recibir el mismo vector, W=2 | 58 |

C01 observa `a3=2` en la entrada del corrector, tipos `(2,2)` y formas
134/138. Ese **contador de candidatos** se distingue del **contador de
aplicaciones** en `0x01D084C4`. La primera llamada recibe la corrección de
134 (`0x01D055B0`); la segunda, la de 138 (`0x01D05600`). Ambas son
`(2.5084378719329834,0,−9.620161056518555,1)`.

La copia inicial solo modifica la salida y el contador; conserva FPR, VF4 y
la pila. En la segunda llamada, VF4 contiene la suma previa a la limitación,
`(5.016875743865967,0,−19.24032211303711,2)`. La salida y los 16 bytes de
pila usados por la función contienen después
`(2.5084378719329834,0,−9.620161056518555,2)`.
La referencia independiente, restringida a sumas exactas, coincide byte por
byte en ambas llamadas. Queda verificada para **copia inicial y vectores
idénticos**; no se extrapola a operandos distintos, redondeo, subnormales o
las demás ramas del corrector.

El comprobador puro de llamadas exige mismo proceso, sesión, ordinal, PCs y
retorno, ciclos crecientes, argumentos alineados y rangos disjuntos. Contrasta
salida y contador con la referencia; valida registros preservados y la RAM
completa fuera de los destinos permitidos. Solo permite cambios de pila en
la rama de combinación y exige que coincidan con el resultado. La adquisición
PINE y la vinculación del código completo al ELF quedan fuera del comprobador.
Sus **37 pruebas sintéticas** rechazan cambios ajenos, punteros erróneos,
solapamientos, contadores, FPR/VF y metadata alterados; cobertura individual
**45/45 sentencias y 6/6 ramas, 100 %**. Son pares de llamadas de varias
instrucciones y no aumentan el total de pares SW/SWC1.

**C06** retorna a `0x001A1924`, ciclo **128297871340**, contador de aplicaciones
2 y salida idéntica a C05. El transform del actor permanece sin cambios durante
estas llamadas. Sus **32 MiB de RAM y GPR bajos coinciden exactamente con
248**, con el mismo PC, ordinal y fotograma nativo, pero el ciclo EE es **34
menor**. La diferencia se conserva sin atribuirle causa ni declarar igualdad
temporal. C06 se preservó antes de continuar la búsqueda C07–C10, sin nuevas
restauraciones; el slot 255 anterior sigue sin usarse.

La unidad solicitada de entrada/retorno queda completada en ese alcance.
La continuación C12–C15 verifica una combinación distinta. HM-T2b.6 mantiene
pendientes otras variantes de operandos, otras rutas de
selección/descarte y el tipo `−2`; HM-T2b.7 conserva la autoridad y el contrato
general antes de llevar el movimiento a la habitación.

## Descarte angular y búsqueda de operandos distintos

**C07–C09** continúan C06 sin restaurar, PID **4124**, ordinal **82709**,
fotograma nativo **21771** y entrada `0x9000`. Es otra llamada del corrector
dentro de esa actualización: sus vectores no se atribuyen a la llamada
C01–C06. Los dos candidatos conservan formas **134/138**, tipo inicial `2`
y corrección idéntica **(1,5778836011886597; 0; −8,225312232971191; 1)**.

| Captura | PC | Ciclo EE | Tipos | Aplicaciones |
| --- | --- | ---: | --- | ---: |
| C07 | `0x001A2064` | 128297927951 | 2, 2 | 0 |
| C08 | `0x001A2068` | 128297927952 | 2, −1 | 0 |
| C09 | `0x001A1924` | 128297928081 | 2, −1 | 1 |

C07→C08 aísla **SW v0,0(s2)**, opcode `0xAE420000`, destino
`0x01D055F0`: el tipo del candidato 138 cambia a `−1`. Transcurre un ciclo;
GPR/FPR y los **32 MiB completos de RAM fuera de esos cuatro bytes** son
idénticos. La salida sigue en cero después de la escritura. C09 retorna con
`v0=1`, dos candidatos de entrada y una aplicación; publica exactamente el
vector de 134, conserva los demás campos de ambos registros y no cambia la
posición, orientación ni matriz de Heather dentro de esta cadena.

El código ELF/RAM fijado compara el ángulo normalizado de FPR0 contra los
límites estrictos `−1,3089969158172607 < ángulo < 1,3089969158172607`, cuyo
umbral positivo tiene bits `0x3FA78D36`. C07 contiene FPR0 =
**1,2152938842773438**, compatible con esa ruta. La escritura sí está aislada;
las instrucciones de comparación anteriores y el cálculo de envoltura del
ángulo no se capturaron individualmente. El oráculo nuevo consume los cuatro
bytes de FPR0 y comprueba el intervalo: no emula `atan2`, el giro de ángulos ni
la aritmética general de EE. Sus 26 casos cubren los límites exactos, los
vecinos de un ULP, ceros, extremos y entradas inválidas.

Tras C09, el usuario cargó los filtros `distinct-only-v1`: las cuatro rutas
de descarte quedaron en condición `0`; permanecieron entrada/retorno del
combinador y la parada final. La búsqueda exige Heather como propietario,
dos candidatos, segunda aplicación y X o Z diferentes en los operandos.
**C10** alcanza la parada `0x001DD434`, ordinal **84060**, nativo **24473**,
ciclo **144234680037**, sin par intermedio que cumpla ese filtro. Es un
resultado negativo limitado a este tramo grabado y a esas condiciones;
**no demuestra ausencia general de combinaciones distintas**.

C10 coincide con 254 en RAM completa, GPR bajos, PC y ciclo. La posición y
orientación coinciden en bytes con el final manual 225, que tiene otra fase
y fotograma nativo. Esa coincidencia final no resuelve la diferencia previa
de −34 ciclos ni la discrepancia de `nextEventCycle` al restaurar C00. El
primer intento de guardar C10 se rechazó por `not paused` sin crear estado
ni recibo; el slot se usó únicamente al llegar a la parada final.

Se detuvo la reproducción conservando C10 pausado y se preparó una nueva
grabación de controles normales, `distinct-corner-v1.p2m2`, sin restaurar.
El usuario seleccionó físicamente **Guardar estado**; la semilla coincide
exactamente con C10 en RAM, EE, CPU decodificada, FPR, PC y ciclo. El siguiente
recorrido busca otra esquina desde un ángulo oblicuo. Su auditoría y la
preparación de la reproducción se detallan a continuación; no se presentan
como otro contacto verificado.

## Nuevo recorrido normal y búsqueda ampliada

El usuario completó el recorrido y lo dejó pausado. **C11** preserva su final
antes de detener la grabación: PC `0x00081FC0`, ordinal **84911**, fotograma
nativo **26176**, ciclo **154283181043**, entrada cero. Posición
**(−13424,958984375; 0,1153106689453125; 24575,05078125; 1)** y yaw
**1,5388057231903076**. La traslación de matriz coincide en bytes con la
posición. Siguen el actor original, MDL522/ANM525, el mismo recurso de mapa
y cuatro ventanas de código sin cambios. Esta fase de controles normales
continúa C10 sin restaurar estados ni escribir memoria del juego.

La grabación cerrada tiene **61 950 bytes**, **1 704 fotogramas**, **61 tramos**
y cero deshacer. Cada paquete de 36 bytes se reconstruye de forma literal
según el orden de campos de `PadData.cpp`: palancas centradas, sin botones de
acción/hombros, segundo puerto a cero. Inventario: ↑ 889 fotogramas, ↑+← 350,
↑+→ 344, neutral 68, ← 29, → 23 y **↑+←+→ un fotograma, el 1643**.

El primer auditor rechazó ese último paquete porque su perfil excluía
direcciones opuestas. La lectura del código fijado confirma que botones y
presiones se almacenan por separado: se añadió esa observación exacta al
inventario, fijando el archivo por hash y conservando el rechazo inicial.
**No se normaliza el paquete, ni se infiere qué prioridad aplica el juego**.
El informe normal y el de Python `-O` coinciden byte por byte. Los controles
y el extremo espacial no identifican por sí solos una nueva esquina ni
correcciones simultáneas distintas.

Se prepararon copias exclusivas en `distinct-route-replay-v1`, idénticas a
grabación y semilla. El plan reserva **C12–C31**, 20 capturas, manteniendo
512 MiB de margen; había 7 996 MiB libres al prepararlo. Las 82 filas de
breakpoints conservan los puntos antiguos con condición `0`; solo se activan:

- `0x001A2340`: propietario Heather, llamador `0x001A22F8`, de dos a ocho
  candidatos, entre una y siete aplicaciones previas y X/Z distintos entre
  los operandos efectivos `a0`/`a1`, dentro de ordinales 84060–84911.
- `0x001DD434`: parada final, propietario Heather y ordinal 84911.

Así no se restringe la búsqueda al segundo de exactamente dos candidatos
ni a direcciones fijas de sus registros. El retorno permanece desactivado
para evitar paradas de llamadas ajenas; si aparece una entrada, se preservará
y se usará **Salir / Step Out** para capturar su retorno. Antes de aceptar
una pareja se comprobarán punteros, propietario, tipos, contadores, código,
operandos, salida y RAM completa permitida. Los operandos que requieran
redondeo seguirán fuera del oráculo de suma exacta.

El usuario cargó los filtros y autorizó continuar con la reproducción. Las
dos condiciones activas se comprobaron en el depurador y se abrió la copia
exclusiva. El clic derecho automatizado seguía fallando con
`AXError.notImplemented`; esa carga manual no modifica la grabación.

## Combinación de correcciones distintas verificada

**C12** registra la **quinta restauración** del proceso, desde la semilla
derivada de C10. RAM completa, CPU decodificada, FPR, VU0 VF, PC
`0x001DD434`, ordinal 84060 y ciclo **144234680037** coinciden. La comparación
estricta de EE conserva diferencias en offsets 1120/1121: `nextEventCycle`
pasa de **1 748** a **16** ciclos de margen. El campo no se oculta ni se
reescribe; no se acredita equivalencia temporal completa de la trayectoria.
C11 y los archivos originales permanecen preservados.

La reproducción encuentra el combinador en el ordinal **84725**, fotograma
nativo **25803**, con entrada `0x9000`, PAL de 2 ticks y dos candidatos tipo
**1/1**. C13–C15 continúan sin otra restauración:

| Captura | PC | Ciclo EE | Evidencia |
| --- | --- | ---: | --- |
| C13 | `0x001A2340` | 152079601667 | Entrada, una aplicación previa y operandos X/Z distintos |
| C14 | `0x001A22F8` | 152079601732 | Retorno del combinador tras 65 ciclos, contador 2 |
| C15 | `0x001A1924` | 152079601758 | Retorno del corrector, salida intacta, `v0=1` |

Los argumentos observados son salida `a0=0x01D084B0`, entrante
`a1=0x01D05600` y contador `a2=0x01D084C4`. El propietario efectivo es
Heather; `s5=2` es el número de candidatos y `s1=1` su índice. El vector
acumulado coincide en bytes con el primer registro; el entrante pertenece al
segundo. No se deducen esos operandos de un retorno aislado:

| Vector | X | Y | Z | W |
| --- | ---: | ---: | ---: | ---: |
| Acumulado | 0 | 0 | −4,2148590087890625 | 1 |
| Entrante | −11,1777496337890625 | 0 | 0 | 1 |
| Salida C14/C15 | −11,1777496337890625 | 0 | −4,2148590087890625 | 2 |

C13→C14 pasa el mismo oráculo de sumas binarias32 **exactas**, sin ampliarlo.
La suma observada en VF4, la salida y los 16 bytes de pila temporal coinciden
con la referencia; el contador pasa 1→2. Los **32 MiB completos de RAM** se
conservan fuera de salida, contador y pila permitidos. Se comprueban los GPR
preservados y FPR3–31. La posición, orientación y matriz del actor no cambian
dentro de C13–C15. Es el **tercer par de llamada** aislado, separado de los
pares de instrucciones individuales. La política de recorte X/Z ya descrita
no cambia estos dos componentes, que proceden de ejes distintos.

Los punteros de forma `0x01846650`/`0x018466A0` se resuelven a los índices
**25/26**, grupo 3 y lista de celda 0 de `tpf1.cld`, cada uno una vez. Los
dos registros son rectángulos verticales en planos perpendiculares y comparten
la arista **X=−13250, Z=24750, Y entre −500 y 0**. El recurso completo en RAM
es idéntico a A/B. El decoder y el oráculo poligonal completo siguen rechazando
el recurso con `CP_NONPOLYGON_UNSUPPORTED`; esta inspección no añade soporte
para su grupo de formas de 48 bytes.

Esta muestra verifica una combinación real de correcciones distintas de
dos paredes, hasta el retorno del corrector. La publicación de esta
actualización se verifica por separado a continuación. No quedan verificadas
la prioridad de direcciones opuestas, operandos que requieren redondeo ni
todas las ramas de descarte. Las instrucciones previas
de aceptación de 25/26 tampoco se capturaron individualmente. El fotograma
solapado 1643 se conserva en la grabación; no se usa para explicar esta llamada
por una relación supuesta entre fotogramas nativos y ordinales.

## Publicación X/Z y matriz de la misma actualización

El usuario cargó los cinco filtros y C16–C20 continuaron desde C15 sin
restaurar. Todas las capturas conservan ordinal **84725**, fotograma nativo
**25803**, entrada `0x9000`, actor y recursos fijados.

| Par/captura | PC | Ciclos EE | Resultado |
| --- | --- | --- | --- |
| C16→C17 | `0x0019FE7C → 0x0019FE80` | 152079630412→152079630413 | SWC1 a X |
| C18→C19 | `0x0019FEAC → 0x0019FEB0` | 152079630426→152079630427 | SWC1 a Z |
| C20 | `0x001DD434` | 152079664247 | Matriz final |

Ambos pares aíslan una instrucción y un ciclo: FPR0 coincide con el valor
publicado, GPR/FPR permanecen iguales y la RAM completa fuera del destino de
cuatro bytes se conserva. La posición pasa de
**(−13402,6357421875; 0,1153106689453125; 24579,21484375; 1)** a
**(−13424,947265625; 0,1153106689453125; 24575,02734375; 1)**. El delta total
**(−22,3115234375; 0; −4,1875; 0)** coincide en XYZ con el paquete de delta
en `[sp+0x50]`; X/Z del centro efectivo coinciden con la posición final.
C20 conserva la posición de C19 y su traslación de matriz es idéntica en
bytes. La orientación y la posición anterior guardada no cambian entre
C15 y C20.

El delta total **no es la salida aislada de C15**. Entre C15 y C16 transcurren
28 654 ciclos EE; en ese corte todavía no se habían capturado todas las pasadas
intermedias. En C16/C18
la corrección residual contiene XYZ cero, **W=2 y contador de aplicaciones 2**:
no se interpreta como ausencia de contacto. La continuación siguiente atribuye
esas pasadas en esta actualización; la ley general de respuesta de esquina sigue abierta.
La combinación de operandos distintos y la publicación final de esta
actualización sí quedan verificadas en sus alcances separados.

**Estado al cerrar C16–C20:** C20 preservado y PCSX2 pausado. La reproducción sigue
cargada, sin avanzar al final del recorrido ni restaurar de nuevo. C21–C31
permanecen libres dentro del presupuesto preparado.

## Pasadas intermedias y balance del desplazamiento

**HM-T2b.6, alcance de esta actualización verificado.** Se preservaron C20 y
la grabación original y se preparó otra copia de `distinct-corner-v1.p2m2`.
El plan `heather-movement-combiner-v1/intermediate-passes-plan-v1.json` reserva
C21–C84, como máximo 64 capturas, y 512 MiB de margen. Los 20 filtros activos
entre 85 filas están limitados al actor original y al ordinal `84725`;
los restantes tienen condición `0`. SHA-256 del archivo de filtros:
`a61be325904edcc51dae4ca58b447e57fbf8f2d3f3ed0d7e7ec7ac3a6f7854e0`.
La carga manual quedó comprobada en la interfaz antes de reproducir.

C21 registra la **sexta restauración**: RAM, CPU decodificada, FPR y VF de VU0
coinciden con la semilla; la comparación estricta de EE vuelve a fallar en
`nextEventCycle`, margen **1748→16**. Se conserva esa diferencia. C22–C68
continúan sin restauraciones adicionales ni escrituras de memoria del juego:
47 paradas en el mismo ordinal `84725`, fotograma nativo `25803`, entrada
`0x9000`, banco 1 y propietario `0x4481D0`. Total de esta entrega: **48 estados**.

Se observaron dos entradas de iteración, C23 y C44, con `s7=0/1` y `fp=0`.
Cada una ejecuta dos llamadas al corrector. Sus contadores de candidatos se
leen del argumento real `a3` y se contrastan con `[sp+0x5c]` al retornar;
no se interpreta el tipo del primer registro como contador.

| Iteración / bloque | Entrada → retorno | Formas ocupadas | Corrección XYZ antes de cuantizar | Corrección XYZ aplicada | Aplicaciones |
| --- | --- | --- | --- | --- | --- |
| 0 / primero | C25→C26 | 26 | (−11,2021636962890625; 0; 0) | (−11,1875; 0; 0) | 1 |
| 0 / segundo | C35→C36 | 26 | (−0,0146636962890625; 0; 0) | (0; 0; 0) | 1 |
| 1 / primero | C46→C47 | 25, 26 | (−11,1777496337890625; 0; −4,2148590087890625) | (−11,125; 0; −4,1875) | 2 |
| 1 / segundo | C56→C57 | 25, 26 | (−0,0527496337890625; 0; ≈−0,0273590069264) | (0; 0; 0) | 2 |

Los cuatro pares `VFTOI4`/`VITOF4` y sus escrituras SQC2 se aíslan en
C27–C30, C37–C40, C48–C51 y C58–C61. En este perfil finito, la conversión
trunca a enteros tras multiplicar por 16 y vuelve a dividir por 16.
Las correcciones residuales menores que 1/16 desaparecen en XYZ, aunque
conservan W y sus aplicaciones. Las cuatro sumas y sus escrituras al centro
se aíslan en C31–C33, C41–C43, C52–C54 y C62–C64. Las dos sumas no nulas
son exactamente representables; el caso XYZ cero con W=2 usa un comprobador
puro separado, sin ampliar el antiguo perfil W=1.

El centro inicial de C23 es
**(−13424,9609375; −49,88468933105469; 24562,31640625; 0)**;
el centro de referencia guardado es
**(−13402,6357421875; −49,88468933105469; 24579,21484375; 0)**.
El operando de cada mitad del movimiento es **X=11,16259765625;
Z=8,44921875**. Los extremos C23→C24 y C44→C45 muestran en ambos casos
un avance efectivo de **X=11,1630859375; Z=8,44921875**.

| Término del balance observado | X | Z |
| --- | ---: | ---: |
| Centro inicial menos referencia | −22,3251953125 | −16,8984375 |
| Primer intervalo de movimiento | +11,1630859375 | +8,44921875 |
| Primera corrección cuantizada | −11,1875 | 0 |
| Segundo bloque de la primera iteración | 0 | 0 |
| Segundo intervalo de movimiento | +11,1630859375 | +8,44921875 |
| Corrección combinada cuantizada | −11,125 | −4,1875 |
| Último bloque residual | 0 | 0 |
| **Desplazamiento total** | **−22,3115234375** | **−4,1875** |

La suma exacta con fracciones separa **−22,3125 de corrección X** y
**+0,0009765625 = 1/1024 de residuo X** de los intervalos de movimiento.
La compensación en Z es exacta. Estos intervalos se observaron por sus
extremos; aquí no se volvieron a aislar sus ADD.S ni la preparación previa
del centro. Por tanto, el balance no constituye una prueba nueva de un modo
universal de redondeo PS2.

C64 conserva centro XYZ final con W=6. En C65 XYZ permanece igual y W ya es
1; esa normalización se delimita, sin contarla como instrucción aislada.
C65→C66 aísla `VSUB` entre centro final y referencia; C66→C67 aísla el SQC2
del paquete **(−22,3115234375; 0; −4,1875; 1)**. Su XYZ coincide con el delta
de posición de C16–C20; W del paquete no es un desplazamiento físico.

C47 frente a C15 y C68 frente a C16 coinciden en **toda la RAM, GPR bajos,
FPR y VF de VU0**, en el mismo PC. Difieren respectivamente en **−4 y −10
ciclos EE**. El intervalo C47→C68 ocupa 28 648 ciclos frente a los 28 654
históricos. Estas discrepancias se preservan, sin afirmar equivalencia
temporal ni equivalencia completa entre recorrido manual y reproducción.

Esta entrega añade **22 pares de instrucciones**, incluidos **nueve SQC2**:
ocho conversiones, cuatro VADD, una VSUB y nueve escrituras. Las cuatro
observaciones de entrada/retorno del corrector se contabilizan aparte de
los tres pares históricos del helper de combinación. El total de pares
SQC2 pasa a **32**; SW/SWC1 permanece en **24**.

**Estado final:** PCSX2 pausado en C68, PC `0x0019FE7C`, antes de publicar X,
ciclo `152079630402`; C20 permanece intacto y C69–C84 no se utilizaron.
Quedan pendientes otras variantes de ángulos/operandos, ramas de descarte,
tipo −2 y sumas inexactas. Esta evidencia cierra el balance solicitado de
esta actualización, sin cerrar HM-T2b.6 global ni implementar respuesta física.

## Variantes angulares: descarte de tipo 2 frente a tipo 1

Se prepararon cinco filtros para el tramo restante desde C68: operandos
distintos y no nulos en un eje compartido del helper, tres sitios pendientes
de descarte y parada final. El filtro de operandos usa los argumentos reales;
excluye las combinaciones ortogonales y las componentes iguales ya medidas.
La interfaz confirmó los filtros antes de reanudar. **C69** llegó directamente
a la parada final, PC `0x001DD434`, ordinal `84911`, fotograma nativo `26175`,
ciclo `154273796571`, sin paradas intermedias. Posición/orientación coinciden
en bytes con C11; el final manual tiene otro PC y un fotograma más. Esta
búsqueda negativa solo cubre el intervalo `84725–84911`, sin restaurar.

Después se preservó C69 y se preparó otra copia de los mismos controles para
revisar todo el intervalo `84060–84911`. **C70** declara la séptima
restauración: RAM, CPU decodificada, FPR y VF coinciden con la semilla;
el margen `nextEventCycle` vuelve a cambiar de **1748 a 16**. El fallo estricto
se conserva. C71–C73 continúan desde ahí sin otras restauraciones.

| Captura | PC | Ciclos EE | Resultado |
| --- | --- | ---: | --- |
| C71 | `0x001A1FF0` | 144305754677 | Rama antes del SW en delay slot |
| C72 | `0x001A2008` | 144305754680 | Primer candidato cambia 2→−1 |
| C73 | `0x001A1924` | 144305754959 | Retorno con una sola corrección publicada |

Las tres muestras conservan ordinal **84066**, fotograma **24485**, entrada
`0x9000`, dos ticks y Heather original. Aquí el banco es **0**, entrada
efectiva `0x01D05FE0`; se vuelve a comprobar su propietario. Los dos
candidatos son las formas **54/55** del grupo 3 de `tpf1.cld`, en
`0x01846F60/0x01846FB0`. El recurso completo coincide con las copias privadas
A/B. Sus tipos pasan **[2,1] → [−1,1] → [−1,1]**.

El ángulo normalizado observado en FPR0 es **0,17310869693756104** radianes.
Está dentro del intervalo estricto **(−1,5533430576324463;
1,5533430576324463)**; FPR1 contiene el límite negativo. El comprobador
aísla la rama y su SW en **tres ciclos**: GPR bajos, FPR y todos los VF se
conservan; solo cambian los cuatro bytes del tipo del primer candidato.
Se cuenta como **rama con escritura en delay slot**, no como una única
instrucción ni como un nuevo par SW aislado.

En C71/C72 el vector de salida y su contador siguen a cero. En C73, el
contador de entrada sigue siendo dos y el de aplicaciones pasa a **uno**.
Se publica exactamente el vector del segundo candidato:
**(0,1655130833387375; 0; 1,4068931341171265; 1)**. El vector descartado era
aproximadamente **(0,054899610579013824; 0; 1,770969271659851; 1)**.
La transformación de Heather no cambia dentro de esta ventana. Esta salida
precede a la cuantización; aquí no se acredita su posterior publicación en
posición/matriz.

**Contrato de las comparaciones restantes.** Se cotejaron 38 opcodes del
ELF fijado contra RAM. Las referencias puras reciben el ángulo binary32 ya
normalizado; no calculan normales, `atan2`, envoltura ni los flags del actor.

| Ruta | Límite positivo binary32 | Predicado estricto | Estado dinámico |
| --- | ---: | --- | --- |
| Tipo 2 frente a tipo 1 | `0x3FC6D3F2` / 1,5533430576324463 | `−L < ángulo < L` | C71–C73 verificado |
| Normales casi paralelas | `0x3D0EFA35` / 0,03490658476948738 | `−L < ángulo < L` | Pendiente |
| Correcciones opuestas | `0x40060A92` / 2,094395160675049 | `ángulo < −L` o `ángulo > L` | Pendiente |

La igualdad con ambos extremos queda excluida en las tres rutas. Hay **69
pruebas** de límites exactos, flotantes adyacentes, ceros, extremos del dominio
y entradas inválidas. El comprobador de rama añade **20 pruebas** de mutación
de PC, ciclo, opcode, destino, registros, tipo y RAM. Ambas coberturas
individuales son 100 %: 16 sentencias/8 ramas y 18 sentencias/sin ramas,
respectivamente. El antiguo perfil de descarte por dirección se conserva.

La ruta de opuestos está condicionada por `(actor+0x1c0)&3`. C68, C69 y C71
contienen `0x2000`; el código la excluiría con esos flags. No se afirma que
sean constantes en todo el recorrido ni que esa rama sea inaccesible en otras
situaciones. Los flags no se modificaron para forzarla. El `atan2`, la
envoltura y las comparaciones/FCR individuales siguen fuera de esta prueba.

**Continuación auditada C73→C74:** la interfaz confirmó los cuatro filtros
restantes y el descarte tipo 2 con condición `0`, SHA-256
`31aa8e12955b0547a5f7e933b45a42e30206625011a6ce48764adc499a15f44f`.
La misma reproducción alcanzó C74 sin otra parada, PC `0x001DD434`, ordinal
**84911**, fotograma nativo **26175**, ciclo **154273796516**, sin restaurar.
No coincidieron eje compartido, paralelos u opuestos bajo esos filtros;
este resultado acotado no demuestra ausencia general de las rutas.

Frente a C69, C74 conserva GPR bajos, FPR, VF, transformación de Heather y
posición anterior. Hay **−55 ciclos** y **cuatro bytes distintos de RAM**:
`0x01ECB814`, `0x01ECB817`, `0x01ECB820` y `0x01ECB830`. Su semántica queda
sin explicar; no se enmascaran ni se clasifican como inocuos. La igualdad
espacial con el final manual C11 sigue verificada, sin equivalencia completa
de trayectoria o estado. SHA-256 de C74:
`575ab64ae27129e2432624aa3a3e03ec68d3f581079b8c4f0d20e6e7723dbdd2`.

**Condiciones previas:** 28 opcodes adicionales coinciden entre ELF y RAM.
La inicialización en `0x00198A90` escribe `0x2000` en `actor+0x1c0` mediante
el puntero global `0x01CFB1F0`, que en C74 apunta a Heather. Se trata de
identificación estática, sin un nuevo par de ejecución del inicializador.
Los helpers `0x002142C0/0x002142D0` permiten OR/borrado de bits para un actor
recibido como argumento; esto no prueba que Heather los invoque ni constituye
un inventario exhaustivo de escritores.

Para distinguir una comparación que no descarta de una comparación que no
se alcanza, se preparó y verificó en la interfaz `preconditions-v1`: conserva
los cuatro filtros y añade `0x001A20E0` (ángulo normalizado de un par tipo
2/tipo 1 superviviente) y `0x001A2148` (Heather con dos o más candidatos y
`flags&3 != 0`). SHA-256
`e95415672ce9a27b3a98d5611f192ff3b480b11d962b9d6ad251923889ba5ab1`.
C74 queda preservada. C75 declara la **octava restauración diagnóstica**:
RAM, CPU decodificada, FPR y VF coinciden con la semilla; el margen del
planificador cambia otra vez de 1748 a 16 y el contraste estricto falla.
La copia de controles es idéntica al original; no se modifican flags ni PC.
C76 alcanzó nuevamente la parada final sin hits intermedios, ordinal 84911,
PC `0x001DD434`, ciclo **154273796514**. Bajo los seis filtros no se observó
la comparación de normales supervivientes ni una llamada elegible de opuestos,
tampoco una combinación nueva de eje compartido. No se concluye que los flags
sean constantes fuera del punto vigilado ni que las rutas sean inaccesibles.
Frente a C74, se revierten los mismos cuatro bytes y hay **−2 ciclos**;
frente a C69, RAM completa/GPR/FPR/VF coinciden y hay **−57 ciclos**.
La discrepancia de C74 sigue preservada y sin atribución causal.
SHA-256 de C76:
`8faf6bb0c137e0e7cc807d490b0543136e867e84a3c3c9f193c6022100f13e81`.

Se detuvo la reproducción sin reanudar ni restaurar. La grabación nueva
`oblique-contact-v1.p2m2` parte de C76: RAM, prefijo EE, FPR, PC y ciclo de
su semilla coinciden exactamente; dos observaciones del actor/ordinal lo
vinculan a la pausa real. La selección física de «Guardar estado» evitó el
fallo conocido del diálogo. El recorrido solicitado busca un obstáculo
oblicuo o curvo, con aproximación tangencial y giros alternos, sin correr.
Al primer intento con Espacio la sesión seguía pausada en ordinal 84911,
con cero fotogramas de controles grabados. Se reanudó mediante «Ejecutar»
del depurador y se comprobó avance real a ordinal 85285, sin restauración,
pasos de instrucción ni cambios de filtros. Esta diferencia de control de
pausa queda registrada; no se atribuye a la colisión del juego.
El usuario completó el recorrido. **C77** conserva su final, PC `0x00081FC0`,
ordinal **87299**, fotograma nativo **30951**, ciclo **182447277043**,
entrada cero, posición **(−17743,7734375; 0,1153106614947319; 22760,97265625)**
y orientación Y **2,4188177585601807**. SHA-256 de C77:
`3fa96ea02d4e8ba09ca6733cf838182a9cabcc8d571514e2482503583b69605e`.
La semilla conserva C76 y no hubo otra restauración durante el recorrido.

La grabación cerrada contiene **4.777 fotogramas**, **102 tramos**, cero undos,
2.433 fotogramas neutros, controles de dirección sin botones de cara, sticks
centrados y segundo puerto vacío. Los fotogramas **2390–2392** contienen
↑/↓/→ simultáneas: se reconstruyen literalmente con sus presiones, sin
normalizar ni inferir prioridad. Todos los paquetes, el final, recursos y
ventanas de código pasan el contraste normal/`-O`. SHA-256 de los controles:
`d3eb9239ac1979f5623e2ad4cdafac33ef6f00f3252f862ddb86585ff261a2a7`.
El recorrido por sí solo no demuestra que se haya alcanzado una forma oblicua
ni que se conserven dos correcciones nuevas.

**Continuación preparada:** copia `oblique-replay-v1`, seis filtros sobre
ordinales **84911–87299**, slots exclusivos **C78–C100**, con reserva de
512 MiB. SHA-256 de filtros:
`a37b8638dce87a5d8dd77a0715bc99b61bfabc9d04fb99aa0e1d8cd69dbd0886`.
La interfaz confirmó los seis filtros y se inició la copia. **C78** registra
la novena restauración diagnóstica: PC `0x001DD434`, ordinal 84911, ciclo
154273796514. RAM, CPU decodificada, FPR y VF coinciden con la semilla, pero
el margen `nextEventCycle` cambia de **624 a 16 ciclos**. El contraste estricto
falla y la diferencia se conserva. C77 y los controles originales permanecen
intactos. La continuación C79–C90 acredita el caso descrito a continuación;
HM-T2b.6 sigue abierta.

## Combinación oblicua con eje X compartido

**C79–C90 verificadas**, sin restauraciones adicionales ni escrituras del
observador en PC/RAM. Las doce muestras pertenecen al ordinal **86317**,
fotograma nativo **28987**, entrada `0x9000` y ticks 2. El propietario es
Heather original, `0x004481D0`; el banco efectivo es **1**, entrada
`0x01D083E0`, dos candidatos de tipo 1 en `0x01D055A0`. Sus formas
`0x01847690/0x018476E0` corresponden a los índices **77/78** del grupo 3.
El recurso completo coincide entre RAM y las copias A/B; ambos índices
pertenecen una vez a la lista de celda 0. La referencia racional de sus
vértices confirma una arista vertical compartida y planos no paralelos ni
ortogonales. La aceptación previa de estos candidatos no se aisló aquí.

| Valor | X | Y | Z | W |
| --- | ---: | ---: | ---: | ---: |
| Acumulado C79 | 5,7588043212890625 | 0 | 0 | 1 |
| Entrante | 3,4901297092437744 | 0 | 3,695775032043457 | 1 |
| Suma VADD C81 | 9,248933792114258 | 0 | 3,695775032043457 | 2 |
| Retorno C85/C86 | 5,7588043212890625 | 0 | 3,695775032043457 | 2 |
| Cuantización C90 | 5,75 | 0 | 3,6875 | 2 |

La llamada `0x001A2340→0x001A22F8`, C79→C85, dura **63 ciclos** y
incrementa el contador **1→2**. Se conserva toda la RAM excepto la salida
de 16 bytes, su contador y los 16 bytes de pila temporal. El retorno mantiene
los registros no volátiles comprobados y todo el bloque VF respecto a C81.
La transformación del actor permanece igual durante C79–C90; esta cadena
no acredita aún su aplicación al centro, posición o matriz final.

Los pasos aislados comprueban:

- **C80→C81:** VADD en `0x001A2364`, un ciclo, VF4 como único vector
  modificado y RAM íntegra preservada. La suma X racional exacta es
  `38792841/4194304`; la observada tiene error **−1/4194304 = −2⁻²²**.
  El valor está entre dos binary32 adyacentes y más cerca del inferior:
  tanto redondeo al más cercano como hacia cero producen lo observado.
  **No discrimina el modo general de redondeo de VU.** Y/Z/W son exactos.
- **C81→C82:** SQC2 en `0x001A2368`, dos ciclos, publica la suma en
  `0x01FFF930`; el resto de RAM y VF permanece igual.
- **C83→C84:** SWC1 en `0x001A23C0`, un ciclo, cambia solo X en esa pila
  al máximo de ambos operandos, **5,7588043212890625**, desde FPR0.
  Las comparaciones previas y el ajuste Z idempotente no se aislaron.
- **C86:** retorno del corrector en `0x001A1924`, valor 1, conserva la
  salida limitada y el contador 2.
- **C87→C88→C89→C90:** FTOI4, ITOF4 y SQC2 en
  `0x001A19E4/E8/EC`, **1/1/2 ciclos**. Enteros `(92;0;59;32)`, luego
  `(5,75;0;3,6875;2)`; escritura completa de salida verificada.

La referencia anterior de sumas exactas **sigue rechazando** estos operandos
con `inexact sum outside profile`; su SHA-256 coincide con el informe
histórico. El auditor reconstruye esta observación usando su suma capturada
y límites de componentes; no introduce una referencia general de aritmética
redondeada. El perfil poligonal completo conserva el rechazo
`CP_NONPOLYGON_UNSUPPORTED`, y el tipo −2 sigue fuera del lector aceptado.

Para continuar desde C90 se respaldaron los 87 filtros y se anuló únicamente
`HM-T2b-oblique-shared-axis-verified-OFF` mediante condición `0`.
Los cinco filtros restantes conservan paralelos, opuestos, sus condiciones
previas y la parada final en ordinal 87299. Plan privado
`oblique-remaining-plan-v1.json`, filtros SHA-256
`0dd8011dfb6eec9604afb545d9921b7343a5fd2c3d0fb23e316ba6c4bf7c3bcc`.
La interfaz confirmó la carga manual y se reanudó la misma reproducción;
no se ha registrado una décima restauración.

## Comparación de paralelismo alcanzada sin descarte

**C91–C94 verificadas**, desde C90 sin restaurar. La búsqueda se detuvo en
`0x001A20E0`, ordinal **86762**, fotograma nativo **29877**, entrada
`0x1000`, ticks 2 y banco **0**, entrada `0x01D05FE0`. El tipo 2 de la
forma **137** se compara con el tipo 1 de la forma **136**; punteros
`0x01848950/0x01848900` del mismo mapa A/B/RAM. El actor conserva flags
`0x2000`. Es la primera observación de este requisito previo en el nuevo
recorrido; las búsquedas negativas anteriores conservan su alcance histórico.

FPR0 contiene **0,1932309865951538** y el límite superior en FPR1 es
**0,03490658476948738**, bits `0x3D0EFA35`. La comparación previa coincide
con el predicado estricto ya probado: este valor no selecciona descarte.
C92→C93 aísla `BC1F` en `0x001A20F8` y su delay slot `LUI v0,0xBD0E`,
con llegada a `0x001A2128` en **dos ciclos**. Toda la RAM, FPR y VF
permanecen iguales; el único GPR modificado es v0, que pasa de
`0x3D0EFA35` a `0xBD0E0000`. Este par no es una instrucción individual
ni una escritura RAM, y se contabiliza separado de las ramas con SW.

C94 retorna en `0x001A1924` y conserva tipos `[1,2]`, contador **2** y
corrección `(0,09361335635185242;0;6,339200973510742;2)`. Su resultado
coincide con aplicar la referencia de sumas exactas a ambos candidatos,
pero las entradas/retornos de esas llamadas no se capturaron: es un cotejo
del extremo, no otro par completo del combinador. La transformación de
Heather permanece igual. No se reconstruyen `atan2`, envoltura ni FCR
general; tampoco se acredita la escritura de descarte paralelo, que no
se ejecutó en este caso.

Para continuar se preparó `parallel-discard-search-plan-v1.json` desde C94,
anulando únicamente la comparación ya observada. Filtros SHA-256
`2f356707c4a11d03ef48dcd65dfbe6d0bc15563df6ce5230ad1bb79540e0de07`:
cuatro condiciones reales, 83 condiciones `0`, slots exclusivos C95–C100,
misma reserva de 512 MiB. La carga manual quedó confirmada en la interfaz
antes de continuar desde C94, sin restaurar.

**C95 cierra esa búsqueda:** PC `0x001DD434`, ordinal **87299**, fotograma
nativo **30951**, ciclo **182443479334**, entrada cero. No se observó otra
parada desde C94: ni descarte paralelo, ni descarte opuesto, ni llamada
con el requisito previo de opuestos. El alcance queda limitado a Heather,
dos a ocho candidatos y ordinales **86762–87299**; no demuestra que esas
rutas sean inaccesibles globalmente. SHA-256 de C95:
`22e5a535394ddbf1a7a4cc9787bcb18a219d8a495c5a03f0770e965109bc2f83`.

La posición, orientación, matriz y posición anterior coinciden en bytes
con C77. Sin embargo, C77 está en PC `0x00081FC0`, otra fase de ejecución,
y tiene **3 797 709 ciclos más**. Esa diferencia no se presenta como deriva
temporal de la reproducción; tampoco se afirma igualdad de RAM/registros
completos o trayectoria. El desfase del planificador en C78 sigue explícito.

## Alcance estático de los flags y preparación del siguiente recorrido

Se cotejaron siete ventanas ELF/RAM y **44 opcodes** con C95. Seis escrituras
usan el puntero global `0x01CFB1F0`, que en la muestra apunta a Heather:

| Escritura | Efecto sobre flags | Dos bits inferiores |
| --- | --- | --- |
| `0x00137EB0` | OR `0x8` | Conservados |
| `0x00137EC4` | AND `0xFFFFFFEF` | Conservados |
| `0x0014C8BC` | OR `0x10` | Conservados |
| `0x0014C954` | AND `0xFFFFFFF7` | Conservados |
| `0x00191094` | AND `0xFFFFFFF7` | Conservados |
| `0x00198A90` | Asignación `0x2000` | Cero |

Es una atribución estática, no pares de ejecución capturados. El barrido de
palabras alineadas del segmento encuentra **21 patrones SW con offset
`0x1C0`** y 150/192 patrones JAL a los helpers OR/AND-NOT. Como el segmento
también contiene datos, esos patrones no forman un grafo de llamadas
verificado ni un inventario exhaustivo de escritores. Otros offsets,
anchos, copias, alias, overlays y llamadas indirectas quedan fuera.

La llamada `0x00216DBC` muestra un setter genérico con máscara `2`, pero
su destino viene de `[a0+4]` mediante s1, sin vínculo demostrado con Heather.
Las seis rutas globales no permiten concluir que ninguna otra active el
requisito de opuestos; otro recorrido a pie tampoco lo demostraría por sí solo.

La reproducción se detuvo desde el menú, conservando C95 pausada. Se preparó
`parallel-edge-v1.p2m2`, plan privado `parallel-edge-recording-plan-v1.json`,
con dos observaciones de PC/ciclo/RAM idénticas al ancla, sin restauraciones
ni escrituras en el juego. Los cuatro filtros previos terminan en ordinal
87299, por lo que quedan fuera de los futuros ordinales del recorrido.
Reserva de 512 MiB verificada; unos 8050 MiB libres al preparar.

La siguiente maniobra propuesta es caminar rozando una pared, pasar su borde,
regresar y pasar en sentido contrario, sin correr, durante 20–30 segundos.
Es una hipótesis para acercar el par tipo 2/tipo 1 al umbral estricto; no se
da por acreditado el contacto ni el descarte. El usuario realizó el cambio
físico «Al encender»→«Guardar estado». Se verificaron la selección y el
aviso de compatibilidad antes de pulsar OK, evitando el fallo conocido
del selector.

**Semilla de `parallel-edge-v1` verificada:** 14 927 613 bytes, SHA-256
`b78c3b3a0b3c16732521acb4521c61b55bcf4b576ed10dada906318ebf54dc42`.
Coincide con C95 en RAM completa, CPU decodificada, prefijo EE, FPR, bloque
VU0 VF, PC y ciclo. Dos observaciones del proceso 4124, actor y ordinal,
confirman la misma pausa. No hay nueva restauración ni escritura del
observador en el juego; los nueve límites diagnósticos anteriores permanecen.

Se reanudó mediante «Ejecutar» del depurador, para evitar el fallo anterior
con Espacio, y se dejó visible la ventana del juego. Una lectura posterior
confirma estado ejecutándose y ordinal **87727**, ya por encima de los
filtros antiguos. Es una comprobación de progreso, no de controles físicos.
El usuario completó la maniobra y pausó con Espacio; no se tocó la interfaz
durante el recorrido. **C96** conserva su final, PC `0x00081FC0`, ordinal
**89504**, fotograma nativo **35361**, ciclo **208458515443**, entrada cero.
Posición `(-18193,76171875;-0,5670318603515625;24875,05078125;1)`,
yaw **−1,1891814470291138**. SHA-256 de C96:
`5793445bfd29dfb782f90e1dfb2b0bf5a4002401500fc4af0b7db360673031e5`.
Se detuvo la grabación desde el menú antes de auditar el archivo completo.

La grabación tiene **159 402 bytes**, **4411 fotogramas**, **35 tramos** y
cero deshacer; SHA-256
`32ff4e1200c36ddf23fe6d0b945b43c053a811ed3b87597258a75c66120d9413`.
Los paquetes se reconstruyeron literalmente: 3043 neutros, 41 izquierda,
210 arriba+izquierda, 947 arriba, 146 arriba+derecha y 24 derecha. No hay
botones de acción/carrera ni direcciones opuestas; sticks centrados y segundo
puerto cero. Los **3017 fotogramas neutros iniciales** se conservan sin recorte
ni normalización. Recurso, código, actor y matriz del final se cotejaron;
estos controles por sí solos no acreditan un contacto o descarte paralelo.

**Décima frontera diagnóstica C97:** se preparó una copia exacta en
`parallel-edge-replay-v1` y cuatro filtros para ordinales **87299–89504**,
slots exclusivos **C97–C120**, con reserva de 512 MiB. Plan privado
`parallel-edge-replay-plan-v1.json`, filtros SHA-256
`66865276c8090f1ffa21b35fbda637eb30a4f97f5382b38ce9fb83ce970325de`.
El usuario cargó los filtros; las cuatro condiciones se comprobaron en la
interfaz antes de abrir la copia, preservando C96 y los originales.

C97 está en PC `0x001DD434`, ordinal 87299, fotograma nativo 30951 y ciclo
182443479334. RAM, CPU decodificada, FPR y VF coinciden con la semilla.
El prefijo EE difiere en offsets **1120/1121**, exclusivamente en el valor
muestreado de `nextEventCycle`: margen **1754→16 ciclos**. La comparación
estricta falla y se conserva esa diferencia; no se acredita equivalencia
temporal completa. SHA-256 de C97:
`1217b83abc50e1946b555d17193f4a19898c317a4463be1b2296e1cf7ddb6863`.
**C98 cierra la búsqueda:** PC `0x001DD434`, ordinal **89504**, fotograma
nativo **35361**, ciclo **208454715466**, entrada cero. No hubo paradas
intermedias desde C97: no se observaron los descartes paralelo/opuesto ni
la condición previa de opuestos bajo los cuatro filtros cargados. El alcance
se limita a Heather, 2–8 candidatos y ordinales 87299–89504. El punto de
comparación paralela sin descarte estaba desactivado: no se afirma ausencia
de esas comparaciones. No hay nueva restauración ni escrituras del observador.

El bloque de posición/orientación/matriz y la posición anterior coinciden
en bytes con C96. Ambos extremos tienen el mismo ordinal/fotograma, pero
C96 está en PC `0x00081FC0`, en otra fase de ejecución. La diferencia de
**−3799977 ciclos** no mide deriva de la reproducción ni demuestra equivalencia
de trayectoria, RAM completa o registros. La discrepancia del planificador
de C97 permanece explícita. La reproducción se detuvo con el juego pausado.

## Objetivo geométrico para el descarte paralelo

Se auditó el grupo 3 completo de `tpf1.cld` desde C98: **139 rectángulos
verticales**, **9591 pares distintos** y coincidencia exacta A/B/RAM. La
lista de celda 0 contiene cada índice una vez; las otras quince están vacías.
Todos tienen palabra de filtro `0x1000`. El recurso completo sigue rechazado
como `CP_NONPOLYGON_UNSUPPORTED` por sus formas activas de 48 bytes: este
inventario diagnóstico no amplía el decoder ni implementa respuesta física.

Cuatro ventanas ELF/RAM y quince opcodes vinculan forma → normal → ángulo
guardado en candidato `+0x40` → diferencia entre candidatos. Dos ángulos
reales de C91 coinciden con la referencia host `atan2(normal.z, normal.x)`
con error inferior a 1e−6. Esto no reconstruye la aritmética general PS2,
envoltura ni FCR. **La dirección de aproximación no modifica las normales
de una pareja fija**, aunque sí puede cambiar los candidatos y sus filtros
previos. Se corrige así la hipótesis de selección del recorrido anterior;
su plan y sus resultados negativos permanecen intactos.

Los 132 pares que comparten una arista vertical completa quedan fuera del
intervalo angular de paralelismo en la referencia geométrica. Hay 1452 pares
con solapamiento Y y ángulo menor al umbral; 1408 son exactamente paralelos
con igual orientación. La distancia entre cajas X/Z se usa solo como límite
inferior para ordenar candidatos, sin acreditar contacto simultáneo.

Se eligió **14/60** como objetivo: segmentos colineales en Z=19250, con
extremos próximos X=−28586,849609375 y −28703,55078125, separación exacta
**116,701171875** y Y en [−500,0]. Para este par la colinealidad hace exacto
el límite de distancia. No se infiere un radio de Heather ni se acredita
acceso, aceptación o supervivencia de ambos candidatos. Se preparó un mapa
local `build/heather-movement/parallel-target-v1.png` con C98 y el
objetivo; sus ejes no equivalen a la cámara del juego.

**Nuevo recorrido normal preparado e iniciado:** `parallel-gap-v1.p2m2`,
plan privado `parallel-gap-recording-plan-v1.json`. El usuario activó
físicamente «Guardar estado» y se comprobó el aviso antes de confirmar.
Semilla de 14 880 312 bytes, SHA-256
`c82685b4a2c10c61fc2bcaa05f2b9fdfcf712e1badcff9e049efb523e8a4586b`:
RAM, CPU decodificada, prefijo EE, FPR, VF, PC y ciclo exactos respecto de C98;
dos observaciones PINE verifican la misma pausa. No es otra restauración.
Se reanudó desde el depurador y se dejó visible el juego ejecutándose para
el recorrido manual hacia el objetivo. El usuario confirmó el recorrido
terminado y pausado; se preservó **C99**, sin restaurar entre C98 y ese final.
PC `0x00081FC0`, ordinal **102726**, fotograma nativo **61806**, ciclo
**364437472243**, entrada cero. Posición
`(−14069,5986328125;0,1153106689453125;21471,46875;1)`, yaw
**−0,48517030477523804**. SHA-256:
`ffa044aca243d95d33abe862a42fdf25689ce5ea0268a091306113028230960d`.
El extremo por sí solo no acredita que se haya alcanzado el objetivo 14/60.

Tras detener la grabación, se auditaron sus **952 662 bytes**, **26 446
fotogramas**, **136 tramos** y cero deshacer. SHA-256
`15bec7678fb29e0dde171bfad9cdfe4031d8e9a01ee3d26eda88830afcb129fc`.
Reconstrucción literal de todos los paquetes: 22144 neutros, 146 izquierda,
2721 arriba, 642 arriba+izquierda, 494 arriba+derecha y 299 derecha. No hay
carrera/acción ni direcciones opuestas; sticks centrados y puerto 2 cero.
Se conservan los **21274 fotogramas neutros iniciales**, sin recortes.
Recursos, código, actor y traslación de matriz del final quedan contrastados.

**Undécima frontera C100:** copia exacta `parallel-gap-replay-v1`, plan
`parallel-gap-replay-plan-v1.json`, slots exclusivos **C100–C123**, reserva
de 512 MiB y ordinales **89504–102726**. Se mantienen los tres filtros de
descarte/condición previa y el final; se añade `0x001A1E30`, con propietario
Heather en `a0`, 2–8 candidatos en `a3` y presencia de **ambas** formas
`0x018462E0`/`0x01847140` entre los registros ocupados. Una parada allí
acreditaría presencia antes del filtrado, no supervivencia ni descarte.
Filtros SHA-256
`3e4b55ddb90d108e1122dc7329b07b4ff06d3bcaef908a86ab31b8ed1d673db2`.
El usuario los cargó; la interfaz muestra 87 filas y cinco activas. Las
cuatro condiciones cortas coinciden por completo; de la condición larga
de presencia la interfaz accesible devuelve solo los primeros 512 caracteres.
El archivo completo queda fijado y la cola no se presenta como verificada
visualmente. El cargador fuente consulta la cadena JSON completa y la valida
antes de instalarla, sin un recorte explícito en esa ruta.

C100 está en PC `0x001DD434`, ordinal 89504, fotograma 35361 y ciclo
208454715466. RAM, CPU decodificada, FPR y VF coinciden con la semilla.
El prefijo EE difiere solo en offset **1120**: margen de `nextEventCycle`
**82→16 ciclos**. Se conserva el fallo estricto de equivalencia; no se
enmascara ni se afirma equivalencia temporal completa. SHA-256 de C100:
`264358e975233162c1dc3a82ba1933602661d835eff6f556fbc59640a1650a23`.
La copia conservó todos los paquetes originales, sin escrituras del
observador en RAM/PC ni controles artificiales.

**C101 y cierre nativo C102:** la primera reproducción no produjo paradas
intermedias; C101 alcanzó `0x001DD434`, ordinal 102726, fotograma **61805**,
ciclo **364427805766**. Los filtros del par, ambos descartes y condición
previa de opuestos no detuvieron este recorrido. Es un resultado limitado a
esos filtros y a esta trayectoria, no una prueba de inaccesibilidad.
El auditor inicial exigía el fotograma 61806 del extremo manual y rechazó
la comparación: el código y el fallo quedan preservados. La parada por
ordinal de juego no es el final nativo de la grabación.

Se reanudó una vez, sin restaurar, hasta la pausa automática **C102**:
PC `0x00081FC0`, ordinal 102726, fotograma **61806**, ciclo **364437472243**.
C101→C102 suma **9666477 ciclos**. RAM completa, CPU decodificada, FPR,
VU0 VF, PC y ciclo coinciden exactamente con C99; el prefijo EE conserva
cinco bytes distintos en offsets **840, 848, 896, 897 y 904**, aún sin
atribuir. El margen de `nextEventCycle` es 4 en ambos extremos y no explica
esos cinco bytes. No se afirma equivalencia del estado completo ni de cada
actualización intermedia. SHA-256 de C102:
`9649da63c98bb4611a3ca2a1c72594221463795048e52e2bce1e9e1186d25f29`.
El código local de `InputRecording::incFrameCounter` pausa al alcanzar el
contador total; la pausa observada es compatible con esa ruta. Se detuvo la
reproducción mediante la interfaz y se verificaron originales y copia.

**Duodécima frontera C103 y búsqueda de presencia:** nueva copia exacta
`parallel-gap-presence-replay-v1`, plan privado
`parallel-gap-presence-replay-plan-v1.json`, slots exclusivos **C103–C126**,
mismo intervalo ordinal y reserva de 512 MiB. El usuario cargó los filtros
y autorizó la reproducción. Las cinco condiciones activas son menores de
512 caracteres y se cotejaron completas en la interfaz; el archivo fija
87 filas, 82 con condición `0`. Su enumeración accesible devolvió 86 filas,
sin ocultar las cinco condiciones reales.

- `0x001A1B5C`: propietario Heather, tipo distinto de cero en `[sp+0x60]`
  y forma individual 14 o 60 en `[sp+0x90]`, antes de agregar el candidato.
  Una aceptación individual no acredita supervivencia de ambos.
- `0x001DD434`: centro de Heather en X **[−29350,−27050]** y Z
  **[18750,19750]**, o parada final. Es una caja geométrica con margen de
  500 unidades, no un radio de colisión inferido. Entrar no prueba contacto.
- Se conservan los dos descartes y la condición previa de opuestos;
  el anterior filtro largo de presencia de ambos candidatos queda en `0`.

C103 conserva PC `0x001DD434`, ordinal **89504**, fotograma **35361**, ciclo
**208454715466**. RAM/CPU decodificada/FPR/VF coinciden con la semilla; el
prefijo EE difiere únicamente en offset 1120, margen de planificador
**82→16**, con rechazo estricto conservado. SHA-256:
`83ba404abb6a9e6b0ebca43c84d42b89e6e4265be50b5b22261548b2de4964d0`.
La reproducción conservó los 21274 paquetes neutros iniciales, sin añadir
controles artificiales ni cambios de RAM/PC.

**C104, presencia positiva:** primera parada en `0x001DD434`, ordinal
**101913**, fotograma **60179**, ciclo **354837550898**, entrada `0x1000`.
Posición **(−27949,41015625;0,1153106689453125;19728,75390625;1)**,
yaw **−2,773167371749878**. Se validan el predicado numérico de la caja y
su comparación por bits IEEE754, propietario, recursos y traslación de
matriz. SHA-256 de C104:
`59fa57102ad2af82e3f06cde2751c4ea1b649c778fce63013c34f73723ac84e2`.
No hubo paradas anteriores entre C103 y C104. Esto acredita entrada en la
zona amplia; no aceptación de pared ni llegada al hueco. Su centro aún
está a 478,75390625 unidades en Z del plano Z=19250, con proyección X dentro
del segmento 14; no se convierte esa distancia en una prueba de colisión.

**Continuación desde C104:** `gap-after-region-plan-v1.json`, slots C105–C126,
22 capturas máximas, reserva de 512 MiB y ninguna restauración adicional.
Se respaldó el archivo y cambió una sola fila: `0x001DD434` queda como
`HM-T2b-gap-region-verified-final-only`, solo ordinal 102726. Las otras
cuatro condiciones permanecen idénticas. SHA-256 de filtros:
`eee951fea3bb6f7bf4d9326040b782db3a68166d210b62aaf2d2f6628b60f397`.
El clic derecho automatizado volvió a fallar con `AXError.notImplemented`;
el usuario confirmó la carga manual. La interfaz permitió cotejar completas
las cinco condiciones activas y se reanudó desde la misma pausa.



**C105–C106, pared 14 aceptada e incorporada:** C105 detiene la consulta
`0x001A1B5C` en ordinal **101925**, fotograma **60203**, ciclo **354978976735**.
Banco 1, entrada `0x01D083E0`, propietario Heather `0x004481D0`, tipo **1**
y forma **0x018462E0**. El centro de consulta es
`(−28070,39453125;−49,884674072265625;19415,30078125;0)`; la salida nativa
`(0;0;9,699234008789062;1)`. No se presenta como aritmética reconstruida.

Se siguieron 29 acciones de paso del depurador, incluidas la rama y su
delay slot, hasta C106 en `0x001A1BD4`, ciclo **354978976765**: 30 ciclos,
mismo ordinal y fotograma. Cinco escrituras fijan tipo, puntero, Y cero,
vector y contador de pila **0→1** en `0x01FFFA6C`. La RAM completa coincide
con la predicción ordenada; solo cambian siete bytes. El candidato ocupa
`0x01D055A0`. La posición y matriz del actor permanecen iguales.
Código de ambas capturas/ELF y recurso A/B/RAM contrastados. No se acredita
aún supervivencia del candidato en el corrector ni corrección final.
SHA-256 C105/C106:
`2a6c4f7db023b0af3ce847ee7250f830982ff4790b6db7f026d0351f9726e79c` /
`46f2c78534dce081d459eac66d5bf53e3927ff311ea89a3f26c1b5492154eabe`.

**Búsqueda de pared 60 desde C106:** `gap-wall60-search-plan-v1.json`,
slots C107–C126 y reserva de 512 MiB, sin restauración adicional.
`HM-T2b-gap-wall14-verified-seek60` exige ahora solo `0x01847140` y
ordinales 101925–102726; los otros cuatro filtros siguen intactos.
SHA-256 `d5b397e02f701c1348842172671288fb6d547b8d7abe1d2697ff5c88269a7ea7`.
El usuario cargó los ajustes, las cinco condiciones fueron cotejadas
completas en la interfaz y se reanudó la misma reproducción.

**C107–C108, cierre del recorrido:** desde C106 no hubo paradas por pared
60, descarte paralelo/opuesto ni condición previa de opuestos. C107 alcanza
`0x001DD434`, ordinal **102726**, fotograma **61805**, ciclo **364427805788**.
Respecto de C101 conserva RAM completa, CPU decodificada, FPR, VF, PC,
ordinal y fotograma, pero suma **22 ciclos** y difiere en doce bytes del
prefijo EE. No se atribuye ese delta a una acción concreta del depurador.

Una continuación adicional sin restaurar llega a la pausa automática C108:
`0x00081FC0`, ordinal **102726**, fotograma **61806**, ciclo **364437472243**.
RAM/CPU decodificada/FPR/VF/PC/ciclo/fotograma coinciden con C99 y C102.
Frente a C99 difieren seis bytes EE, offsets **832, 840, 848, 896, 904 y 968**;
frente a C102 son siete. El informe enumera sus valores sin ocultarlos.
No se afirma equivalencia del emulador completo ni de todo el recorrido.
La reproducción se detuvo mediante la interfaz, comprobando «Detener»
deshabilitado y juego pausado; originales y copias siguen idénticos.

El resultado positivo es entrada en la región y aceptación/incorporación
de **una** pared, la 14. La ausencia de la 60 queda acotada a esta ruta y
al retorno vigilado; no acredita inaccesibilidad global. Alcanzar el hueco,
el par simultáneo y su descarte requieren otra maniobra por juego normal.
La continuación completa C104→C108 no añadió restauraciones; se mantienen
doce en el proceso. No hay build nuevo ni implementación de respuesta física.

**Decimotercera frontera C109, copia de C104 autorizada:** el usuario pidió
expresamente recuperar una copia de C104 para investigar la pared 60 y el
hueco. `gap-targeted-route-plan-v1.json` conserva C108 y valida su pausa
con dos observaciones enlazadas. Se escribió exclusivamente
`gap-targeted-route-v1/C104-copy.p2s`, idéntica a C104. El selector nativo
mantuvo «Abrir» deshabilitado; se canceló sin cargar y se usó el comando
nativo PINE `MsgLoadState` (0x0A) con una copia exacta en la ranura libre 127.
La fuente local confirma la carga por hilo CPU y nombre de ranura. Se
registró el intento antes de enviarlo y se ejecutó una sola vez.
La ranura 127 es una **copia para carga**, no una captura adicional.

**C109** conserva `0x001DD434`, ordinal **101913**, fotograma **60179**,
ciclo **354837550898** y posición
`(−27949,41015625;0,1153106689453125;19728,75390625;1)`.
RAM completa, CPU decodificada, FPR y VF coinciden exactamente con C104.
El prefijo EE difiere en offsets **1120/1121**: margen de `nextEventCycle`
**1727→16**. La comparación estricta sigue rechazada; no se modifica ni
oculta el campo. SHA-256 C109:
`b26ed8230687223e9556588fc652d7fab029ef44affaf2a31bd2a3567151e829`.
C104 original, copia de trabajo, copia de ranura y C108 permanecen intactos.
No hubo ediciones manuales de RAM, PC, posición, flags ni controles.

**Entorno del hueco:** se cotejaron las formas 12/13/14/60 entre A/B y RAM.
12 comparte arista vertical completa con 14; 13 con 60. Ambas prolongaciones
son perpendiculares a los objetivos y tienen Y **[−500,0]**. Sus segmentos
paralelos van de Z=19250 a **20276,599609375**, longitud **1026,599609375**,
con separación exacta **59751/512 = 116,701171875**. Esto explica que una
aproximación directa deba considerar también 12/13; no demuestra por sí
solo bloqueo, inaccesibilidad o ausencia de otra ruta. El croquis local
`build/heather-movement/gap-targeted-C109.svg/.png` muestra esas cuatro
formas, posición y orientación, con ejes del mundo y límites explícitos.

**Nueva grabación, inicio verificado:** `wall60-gap-v1.p2m2`, plan
`gap-targeted-recording-plan-v1.json`. Las 87 condiciones se pusieron en
`0` y el usuario cargó los ajustes; las 87 filas fueron verificadas en la
interfaz. El usuario activó físicamente «Guardar estado» y se comprobó el
aviso antes de confirmar. El autor requirió un evento de edición real para
habilitar OK: la ruta local conecta `textEdited`, no la asignación AX.
La semilla de **14557165 bytes**, SHA-256
`64c30b92ca12401780df0a2b33910c77adc272d42ab2e93e6d15f672f56bb3df`,
coincide con C109 en RAM/CPU/prefijo EE/FPR/VF/PC/ciclo. Dos observaciones
verifican la misma pausa. Se reanudó mediante Sistema → Pausar, se comprobó
estado en ejecución y se solicitó una maniobra breve por controles normales,
sin J, restauraciones ni reinicio. Tras la confirmación del usuario se
preservó el final en C110 y se cerró la grabación mediante la interfaz,
comprobando «Detener» deshabilitado y juego pausado.

**C110 y auditoría del recorrido normal:** PC `0x00081FC0`, ordinal **107059**,
fotograma **70472**, ciclo **415551620083**, posición
`(−28446,265625;0,11532287299633026;21375,056640625;1)`, entrada 0.
SHA-256 `b2931692b29f731af696519b4d712344393158413df9ac836777a6aa2ecc77e0`.
`wall60-gap-v1.p2m2` contiene **371190 bytes**, **10294 fotogramas** y
**267 tramos**, cero undos, sin botones de acción/carrera. SHA-256
`5165cd4434a9183e1fb0925b790eb150f7773a62742b294030c0fcdd7473e143`.
El oráculo reconstruye los 36 bytes de cada paquete; sticks centrados y
segundo puerto nulo. Conserva **2371 paquetes neutros iniciales** y **16
paquetes Up+Left+Right (`0xb0`)** sin normalizar ni eliminar direcciones.
La semilla, actor original, modelo, animación, mapa y ventanas de código
permanecen fijados; el final no demuestra contacto con la pared 60.

**Decimocuarta frontera C111:** se creó una copia exclusiva en
`gap-targeted-replay-v1`, preservando originales y C110. El plan
`gap-targeted-replay-plan-v1.json` reserva **C111–C126**, 16 capturas, más
512 MiB de margen. Cinco filtros no nulos, menores de 512 caracteres,
fueron cargados por el usuario y contrastados íntegramente en la interfaz:
aceptación de 60 o 12/13 en `0x001A1B5C`, descartes paralelo/opuesto,
requisito previo de opuestos y parada final en ordinal 107059. Los demás
puntos tienen condición `0`. La pared 14 ya verificada no dispara este filtro.

El intento se registró antes de cargar la copia por «Reproducir». C111
preserva PC `0x001DD434`, ordinal **101913**, fotograma **60179** y ciclo
**354837550898**, SHA-256
`e5b4118cadae2eeb89b32e6a755cd21a88e6f76ea90f01cad4c87230a9606925`.
RAM, CPU decodificada, FPR, VF y prefijo EE completo coinciden con la semilla;
margen del planificador **16→16**. Esto no elimina la discrepancia histórica
C104→C109 de 1727→16 ni acredita equivalencia de toda la trayectoria.
Se reanudó la reproducción con los controles originales. La primera parada
fue **C112**, final de ordinal **107059** en `0x001DD434`, fotograma **70471**,
ciclo **415542245609**. No hubo paradas intermedias en los cinco filtros;
esto acota la ausencia de aceptación de 60/12/13, descartes paralelo/opuesto
y requisito previo de opuestos a esta ruta y los sitios vigilados.

Una sola reanudación alcanza **C113**, final nativo `0x00081FC0`, mismo
ordinal, fotograma **70472**, ciclo **415551620083**. Coincide con C110 en
RAM completa, CPU decodificada, FPR, VF, prefijo EE completo, PC, ciclo y
fotograma. No hay bytes EE discrepantes en esta comparación; esto no
compara todos los subsistemas del emulador ni todos los estados intermedios.
La reproducción se detuvo desde la interfaz y se comprobó «Detener»
deshabilitado. Originales y copias permanecen idénticos. Una aceptación
ausente todavía no distingue una forma no consultada de una consulta rechazada.

**Decimoquinta frontera C114 y consulta de la pared 60:** se preparó otra
copia literal en `wall60-query-replay-v1`, preservando C110/C113. El plan
`wall60-query-replay-plan-v1.json` reserva C114–C126 y 512 MiB de margen.
Las instrucciones fijadas muestran el paso de forma/entrada a `0x001A24D0`,
su conservación en `s1/s0`, la prueba lateral, la llamada a `0x0019F660` y
el retorno. Se añadieron cuatro puntos, total **91 filas**, con cinco
condiciones no nulas: entrada, rama lateral, resultado geométrico, retorno
y final. El usuario cargó los ajustes y las cinco condiciones se contrastaron
íntegramente. La carga nativa quedó precedida por un recibo de intención.
C114 coincide con la semilla en RAM/CPU/FPR/VF/prefijo EE/PC/ciclo, margen
16→16; las discrepancias históricas C104→C109 se conservan.

La primera llamada aparece en ordinal **101914**, fotograma **60181**,
entrada **0**, durante el tramo neutro inicial. Forma **60**, dirección
`0x01847140`, entrada física **`0x01D05FE0`**, banco **0**, propietario
Heather `0x004481D0`, salida en `0x01FFF9D0` y retorno `0x001A1B5C`.
El centro de consulta es
`(−27949,41015625;−49,88468933105469;19728,75390625;0)`.

| Captura | PC | Ciclo | Resultado acotado |
| --- | --- | --- | --- |
| C115 | `0x001A24D0` | 354849223093 | Entrada real con la forma 60 y propietario Heather |
| C116 | `0x001A2558` | 354849223167 | Comparación lateral: FPR1=35056564, FPR0=0; no toma el rechazo por valor negativo |
| C117 | `0x001A2574` | 354849223209 | `0x0019F660` devuelve `v0=0`; el resultado requerido es `v1=1` |
| C118 | `0x001A2730` | 354849223211 | Salto tomado y delay slot; RAM completa/FPR/VF sin cambios respecto de C117 |
| C119 | `0x001A1B5C` | 354849223217 | Retorno al llamador con tipo de salida 0 |
| C120 | `0x001A1BD4` | 354849223220 | Carga del tipo y salto que omite la incorporación |

Entre C117–C118 solo cambia `v1=sp+0xB0` por el delay slot; entre
C119–C120 solo cambia `a2=0`. C117–C120 conservan la RAM completa. El
contador `0x01FFFA6C` permanece **0→0**, los ocho registros candidatos
permanecen iguales y el bloque de Heather de 0x400 bytes, incluida posición
y matriz, tampoco cambia en C115–C120. La forma y recurso completos
coinciden con A/B; instrucciones contrastadas con el ELF fijado.

Se acredita que **la pared 60 sí se consulta y esta llamada se rechaza**.
No se ha aislado la condición VU interna que produce el 0 en `0x0019F660`;
los 42 ciclos entre C116–C117 incluyen preparación, llamada y retorno, no
una instrucción única. El producto lateral se observa, sin afirmar un
modelo general de su aritmética. El vector siguiente de la entrada se
conserva literal, sin deducir aquí un radio general. Esta llamada inicial
no representa la máxima aproximación del recorrido. PCSX2 queda pausado
en C120, dentro de la misma reproducción y sin restaurar después de C114.

## Rechazo interno de pared 60: límites separados

Se verificó la pausa viva C120 con dos observaciones enlazadas de PC/ciclo
antes de continuar. `wall60-internal-plan-v1.json` amplía el presupuesto a
C121–C146, **excluyendo C127**: la ranura física 127 contiene la copia de
C104 usada para cargar y no se convierte en evidencia nueva. Se conservan
512 MiB de reserva. No se restauró después de C114 ni se alteraron controles.

C121 es otra consulta de 60 dentro del mismo ordinal **101914** y fotograma
**60181**, entrada 0. C122 preserva la comparación lateral y cuatro pasos de
interfaz, incluidos dos delay slots, llegan a C123, entrada de `0x0019F660`.
Argumentos: salida `0x01FFF8E0`, vértices `0x01847150/0x01847170`, entrada
física `0x01D05FF0`. Propietario Heather, banco 0, forma 60.

La construcción capturada produce estos límites XYZ:

| Volumen | Mínimos | Máximos |
| --- | --- | --- |
| Consulta de Heather | (−28124,41015625; −774,8847045898438; 19553,75390625) | (−27774,41015625; −49,88468933105469; 19903,75390625) |
| Segmento vertical de pared 60 | (−28850; −500; 19250) | (−28703,55078125; 0; 19250) |

El valor horizontal **175** se obtiene del cuarto componente de esta entrada
concreta; no se eleva a radio universal. El código usa ADDw/SUBw para X/Z,
MAX/MINI para XYZ de los vértices y copia por ADD los extremos Y observados.
El oráculo reproduce los resultados binarios de estos operandos finitos.

| Captura | PC | Efecto contrastado |
| --- | --- | --- |
| C123 | `0x0019F660` | Argumentos completos del helper |
| C124 | `0x0019F69C` | Límites construidos, antes de CTC2 |
| C125 | `0x0019F6A0` | Estado VU `0x82→0x02`: limpia flags acumulados, conserva signo actual |
| C126 | `0x0019F6A4` | Primera resta: (1075,58984375; 450,11529541015625; 653,75390625); STATUS/MAC=0 |
| C128 | `0x0019F6A8` | Segunda resta: (−579,140625; 774,8847045898438; −303,75390625); STATUS=`0x82`, MAC=`0xA0` |
| C129 | `0x0019F6C0` | CFC2 lee `t0=0x82` |
| C130 | `0x0019F6C4` | ANDI deja `t0=0x80` |
| C131 | `0x0019F86C` | BNEZ y delay slot alcanzan el retorno anticipado |
| C132 | `0x001A2570` | JR y carga en delay slot devuelven `v0=0` |

Los intervalos C125→C126 y C126→C128 son de un ciclo cada uno: se compara
todo el bloque VF, incluidos componentes no escritos, sin diferencias
fuera del destino esperado. La RAM completa permanece igual desde C124
hasta C132. Lectura, máscara, salto y retorno solo cambian los registros
bajos previstos. El bloque de Heather y los ocho candidatos permanecen
intactos durante C121–C132. El orden ACC/VF/VI del estado se contrasta con
`VUmicroMem.cpp`; enums, flags y CTC2 con las fuentes fijadas de PCSX2.
La ruta nativa `recCTC2` conserva los seis bits bajos: no se afirma que
CTC2 ponga todo STATUS a cero.

**Causa acotada:** los límites no se solapan en X ni Z; las separaciones son
**579,140625** y **303,75390625**. La segunda resta activa signos nuevos y
el bit acumulado `0x80`, que conduce al retorno 0 antes de las pruebas
geométricas posteriores. El comportamiento se verifica en esta llamada
neutra de PCSX2; no demuestra inaccesibilidad del hueco ni sustituye el
solver general.

Para observar consultas durante los controles se preparó
`wall60-approach-plan-v1.json`, desde C132, sin restaurar. Las 93 filas
contienen cinco condiciones no nulas, cargadas por el usuario y leídas
íntegramente: entrada de consulta cercana con entrada grabada no nula,
resultado de límites cercano, retorno cercano, paso del rechazo de límites
independiente de la región y final en ordinal 107059. La región de búsqueda
XZ es **[−29525;−28028,55078125] × [18575;19925]**, margen geométrico 675
respecto de la pared 60; no es un radio físico ni acredita proximidad
máxima. Las condiciones de palabras IEEE invierten el orden de negativos.
La primera parada de aproximación queda preservada en C133–C135, sin
restaurar desde C132. Las tres capturas pertenecen al ordinal **103122**,
fotograma nativo **62597**, con ↑ grabada (`0x1000`). Entrada, comprobación
de límites y retorno se observan en `0x001A24D0`, `0x0019F6C4` y
`0x001A2730`, respectivamente: 111 ciclos hasta la comprobación y siete
más hasta el retorno.

El centro consultado es **(−28028,61328125; −49,88468933105469; 19523,5)**;
su X difiere ligeramente de la posición del actor (**−28028,615234375**).
El oráculo usa el operando de consulta, no la posición publicada. Las
restas son (996,38671875; 450,11529541015625; 448,5) y
(−499,9375; 774,8847045898438; −98,5), coincidentes con VF. Por tanto,
la separación cae a **499,9375 en X y 98,5 en Z**, pero STATUS/MAC
siguen en `0x82/0xA0`, la máscara en `0x80` y el retorno en cero.
No se añaden candidatos ni cambia la posición durante esa consulta;
C134–C135 conservan toda la RAM. Es la primera coincidencia con la
región elegida, no una medida de la distancia mínima del recorrido.

Desde C135, `wall60-closer-plan-v1.json` estrecha solamente las tres
condiciones de cercanía a **[−29275;−28278,55078125] × [18825;19675]**.
Conserva las condiciones independientes de paso de límites y final,
93 filas y cinco filtros activos. El margen geométrico 425 equivale, con
la extensión observada 175, a buscar aproximadamente 250 unidades más
allá del solapamiento; no redefine la física. El usuario confirma la
carga. La lectura AX permite contrastar tres filas completas y la imagen
confirma otra condición de límites, pero las columnas desplazadas impiden
una segunda lectura completa de todas las filas. Se continúa desde C135
con el archivo preparado verificado, sin restauración ni cambio de controles.

**Cierre de la búsqueda más cercana:** la siguiente parada fue C136,
`0x001DD434`, ordinal **107059**, fotograma **70471**, ciclo
**415542244133**. No se observaron paradas intermedias en la región más
estrecha ni en el paso independiente de límites desde C135; este último
tampoco había parado entre C132 y C135. La ausencia describe los filtros
y esta adquisición, no se deduce solo de los extremos. Las consultas
cercanas requieren entrada grabada no nula; el paso de límites no la exige.
No se calcula la distancia mínima del recorrido ni se declara inaccesible
la pared 60.

Una continuación llega al final nativo C137: `0x00081FC0`, ordinal
**107059**, fotograma **70472**, ciclo **415551620083**, posición
(−28446,265625; 0,11532287299633026; 21375,056640625; 1), entrada 0.
El menú «Detener» de grabación se accionó y quedó deshabilitado; PCSX2
sigue pausado. C110 y C137 coinciden en RAM completa, CPU decodificada,
FPR, VF de VU0, PC, ordinal, fotograma y ciclo. El prefijo EE completo
**no coincide**: difieren los offsets relativos 840, 841, 848, 849, 896,
897, 904 y 905; valores exactos conservados en el informe, causa pendiente.
No se acredita equivalencia temporal de todo el emulador. Las grabaciones
original y de reproducción y sus semillas conservan sus hashes.

El lote explica el rechazo geométrico y comprueba una aproximación real
sin restaurar después de C114. Quedan abiertos el contacto aceptado con
60, el par simultáneo 14/60 y sus descartes. Antes de pedir otro recorrido,
se debe definir un punto de aproximación alcanzable a partir de la geometría
adyacente y del lado que admiten las consultas observadas; la región
geométrica por sí sola no acredita acceso.

## Verificación y artefactos

- `reports/local/heather-movement-wall60-closer-closure-v1.json`, SHA-256
  `93b9963c5d93389e3721f87936ee2ea36da12bee391eeea901b6543de9af7c89`.
  C136–C137: final de búsqueda y comparación con C110, ocho diferencias
  EE conservadas, originales íntegros y normal/`-O` iguales.
- `reports/local/heather-movement-wall60-approach-v1.json`, SHA-256
  `36cd9df161a89f2310ffd3a34247146110e8cdb7651a26b1ec703f652e0b0637`.
  C133–C135, consulta con ↑ y límites aún separados; normal/`-O` iguales.
- `reports/local/heather-movement-wall60-internal-v1.json`, SHA-256
  `a3cec8e162e655bd012b677a6f949a077afc6fbc95855355952cb54eb6753e19`.
  C121–C132, excepto C127: construcción de límites, flags, salto y retorno
  cero; predicciones exactas y normal/`-O` iguales.


- `reports/local/heather-movement-gap-targeted-first-stop-v1.json`, SHA-256
  `13ee1c7d4b93b2cb8af6d7cb47d7f171609ba811b3cdcd4f35aa52eaab4fd635`.
  C112 como primera parada, final de ordinal; normal/`-O` iguales.
- `reports/local/heather-movement-gap-targeted-closure-v1.json`, SHA-256
  `ad30e89225606236876a25f24a9110921a4e900032a485e5f15cb37d9105320b`.
  C113 y comparación exacta de los dominios descritos frente a C110;
  búsqueda negativa acotada y cierre UI; normal/`-O` iguales.
- `reports/local/heather-movement-wall60-query-restore-v1.json`, SHA-256
  `5d07eac64e69db2fc090b83ef03ddc6fdf1c85886153963341518dc1ae9948dd`.
  C114, decimoquinta restauración; semilla exacta en los dominios
  contrastados, normal/`-O` iguales.
- `reports/local/heather-movement-wall60-query-v1.json`, SHA-256
  `4fe67cb90dbaabd121874f3cc8c7083b965a017c3ff3b095d669252204761bfe`.
  C115–C120, consulta y resultado 0, saltos y ausencia de incorporación;
  normal/`-O` iguales. Serialización racional de vértices exactos.


- `reports/local/heather-movement-gap-targeted-recording-v1.json`, SHA-256
  `037633e06d1c872205d5923bb9d5b2f7d4a66c91c4069d95bbb13782725ce911`.
  C110 y reconstrucción completa de los 10294 paquetes; normal/`-O` iguales.
- `reports/local/heather-movement-gap-targeted-replay-restore-v1.json`, SHA-256
  `97f2687bf1e82c7003fb17c7dab9b7b0db5f7c1cf18ca4e3ae0aac486e3843c5`.
  C111, decimocuarta frontera exacta respecto de la nueva semilla;
  normal/`-O` iguales, sin borrar las discrepancias históricas.


- `reports/local/heather-movement-gap-targeted-restore-v1.json`, SHA-256
  `14dfa7e3801e346caf4604b5eca8a893385917adcd88605744d311bcc3155225`.
  C109 y decimotercera frontera; normal/`-O` iguales, discrepancia EE explícita.
- `reports/local/heather-movement-gap-neighborhood-v1.json`, SHA-256
  `bf51f68240aa7d9436727b8e58f1b64d82771f471fea44b6f1cb3e3f56e86e71`.
  Formas 12/13/14/60 y aristas comunes; normal/`-O` iguales, sin accesibilidad inferida.
- `reports/local/heather-movement-gap-targeted-seed-v1.json`, SHA-256
  `8fa2a36b3660a9e7055fd665f1e1ca611c0e71a26cfe2206cdb2867632627d22`.
  Semilla exacta respecto de C109 y pausa viva contrastada; inicio histórico,
  controles posteriormente auditados en el informe de grabación.

- `reports/local/heather-movement-gap-presence-closure-v1.json`, SHA-256
  `b5a78e3772aa0d7d19e1fcbb8cd9ce5819817052e63a40a1242a3d65872b324d`.
  C107–C108, búsqueda acotada y cierre nativo; normal/`-O` iguales.
  Delta de +22 ciclos y diferencias EE conservados.

- `reports/local/heather-movement-gap-wall14-v1.json`, SHA-256
  `7a015f5de3b8fae04230511ed4307bbf11624e9ab8d14259b6f5fa1649d34645`.
  C105–C106, pared 14 y cinco escrituras de incorporación; normal/`-O` iguales.

- `reports/local/heather-movement-gap-presence-stop-v1.json`, SHA-256
  `874df430943aca13149f35341015427f5da475f8325647729c515f0ec15d64dd`.
  C104 entra en la caja de búsqueda; normal/`-O` iguales. Contacto pendiente.

- `reports/local/heather-movement-parallel-gap-search-v1.json`, SHA-256
  `fa4fc4bddfaf996491433f64b1eb80d8ea15c6b779c75a099a00ff56c00cd058`.
  C101/C102, rechazo inicial y cinco bytes EE conservados; normal/`-O` iguales.
- `reports/local/heather-movement-gap-presence-restore-v1.json`, SHA-256
  `00fe3d3994cd72cfff8dc9905193e81066600caccb6e545535a271173acd375a`.
  C103 y duodécima frontera; normal/`-O` iguales. La auditoría termina,
  pero la equivalencia estricta de la semilla sigue fallando.

- **496 pruebas sintéticas**: 69 de las variantes angulares y 20 de la rama con
  SW en delay slot, además de las 407 anteriores: 25 del perfil XYZ cero/W=2, 26 del criterio de descarte angular, 37 del comprobador de llamadas, 30 de la
  referencia de combinación, 31 del
  lector de candidatos y las 258 anteriores: 52 del comprobador SQC2, 34 de SW/SWC1, 47 del
  comprobador VU, 35 de suma exacta/candidato de dos mitades, 52 de origen
  y 38 de referencias geométricas de paredes.
  Offset negativo, fuente GPR/FPR/VF, escritura
  idempotente, límites, identidad de sesión, PC, ciclo, registros, opcode,
  mutaciones de RAM y rechazo de operandos fuera del alcance. Los seis módulos anteriores
  conservan su cobertura individual de líneas y ramas del **100 %**; el comprobador
  VU cubre 65/65 sentencias y 2/2 ramas; los dos nuevos cubren 30/30 y 53/53
  sentencias, sin ramas contadas por coverage. El comprobador VU anterior
  mantiene su restricción de suma XYZ cero; la suma no nula usa otro comprobador.
  El lector nuevo alcanza 24/24 sentencias y 4/4 ramas, 100 %, medido por separado.
  La primera invocación de coverage no recogió ese módulo porque el perfil general
  limita `source` a `tools`; se repitió con fuente diagnóstica explícita.
  El criterio angular alcanza 12/12 sentencias y 4/4 ramas, **100 %**,
  medido individualmente. El perfil W=2 alcanza 13/13 sentencias, sin ramas
  contadas por coverage: 100 % individual. Se ejecutaron nuevamente las
  **496 pruebas**, todas aprobadas, también tras incorporar C79–C90. Total
  actual: trece módulos puros; **34 pares SQC2**, **25 pares SW/SWC1**, tres
  ramas con escritura en delay slot y cuatro pares de llamadas, contabilizados
  por separado. La cuarta llamada usa reconstrucción observacional acotada,
  pues la referencia de sumas exactas conserva su rechazo.
  Se repitieron 196 pruebas relevantes para llamadas, referencia, candidatos,
  paredes, descarte y escrituras escalares tras añadir el caso real distinto:
  todas aprobadas.
- Los comprobadores son puros; adquisición PINE, comparación de archivos y
  presentación de resultados se mantienen separadas. No se introduce un solver
  ni se trasladan direcciones PS2 al núcleo del visor.
- Auditores normal y con Python `-O`: informes byte por byte iguales. Nueve
  ventanas ELF/RAM en caminar/parada y doce en reloj/giro/suelo. El fallo de
  redondeo inicial sigue explícito. No se ha ejecutado un pipeline remoto.
- `tools.qa.check_repository`: PASS, cero errores; `git diff --check`: PASS.
  Tras C98 se repitieron las **38 pruebas de referencias de paredes**, todas
  aprobadas. La comprobación inicial rechazó PNG/SVG dentro de `reports/local`,
  reservado para metadata; se trasladaron a `build/heather-movement` y la
  comprobación volvió a pasar, sin relajar su regla.
- `reports/local/heather-movement-shared-axis-call-v1.json`, SHA-256
  `2850fc183a1c120b5214bf7e5bcb24af9a6f266ad6a8bbc73814001308fe56db`.
  C79–C90, paredes 77/78, suma X inexacta, límite X, retorno de 63 ciclos y
  cuantización auditados. Normal/`-O` idénticos; no determina redondeo general
  ni acredita publicación en la posición.
- `reports/local/heather-movement-parallel-rejection-v1.json`, SHA-256
  `fc0e1d51613206059f18d4e0ec1c77316b03bb24f81bb7d9369249d5fa29b4ad`.
  C91–C94, requisito previo paralelo alcanzado, salto BC1F+LUI y conservación
  de candidatos/contador auditados. Normal/`-O` idénticos; descarte efectivo
  y publicación de posición pendientes.
- `reports/local/heather-movement-oblique-search-end-v1.json`, SHA-256
  `6b7f7a5fde0c69a790e1061e6025b9dba43dfb0aab58a0a18eaaa30992a666ed`.
  C94→C95 sin otros hits, final espacial igual a C77 y distinta fase de
  ejecución preservada. Normal/`-O` idénticos.
- `reports/local/heather-movement-flag-writer-scope-v1.json`, SHA-256
  `8e3ac8fcfeb3479cc52027cd257439b4b2f8a243130f402f74e91391c9aec447`.
  Seis escritores vinculados estáticamente al puntero global; 21 patrones
  SW y un setter genérico sin vínculo a Heather. Normal/`-O` idénticos;
  no acredita inventario completo ni inaccesibilidad de opuestos.
- `reports/local/heather-movement-parallel-edge-seed-v1.json`, SHA-256
  `7d3bf34dcc2506a997850c1e0c5fb82481df45b2f1dd50a12fe2c8f081c2c8ce`.
  Semilla, CPU/RAM/VF y dos observaciones de pausa exactas respecto de C95;
  grabación iniciada. El cierre/auditoría posterior se conserva en el informe
  de grabación siguiente.
- `reports/local/heather-movement-parallel-edge-recording-v1.json`, SHA-256
  `eab804bd1e6140bb5ccab37980bb861202988bb37d5ae5c3259ffcd81a66a31b`.
  C96 y los 4411 paquetes verificados, 35 tramos, sin botones de carrera
  ni direcciones opuestas. Normal/`-O` idénticos.
- `reports/local/heather-movement-parallel-edge-restore-v1.json`, SHA-256
  `5b128b001559c5bf84a8b6eb0a2e71a78b6311007444617e9523d39ca11183ef`.
  C97, décima restauración; fallo estricto limitado al margen de planificador
  1754→16, preservado. Normal/`-O` idénticos.
- `reports/local/heather-movement-parallel-edge-search-v1.json`, SHA-256
  `8a171951c641765c7d4e9bc7c84d1d28fa389117f9254f9fd21fd20e1dfd116e`.
  C98, parada final sin coincidencias intermedias, extremo espacial igual a
  C96 y distinta fase/ciclo conservados. Normal/`-O` idénticos.
- `reports/local/heather-movement-parallel-geometry-v1.json`, SHA-256
  `94909c138f3926f856af8cf2a3af545f010bdfba1e18324b774e6c296b64e096`.
  Inventario de 139 formas, listas, fuente de ángulos y objetivo 14/60.
  Normal/`-O` idénticos; preparación geométrica, sin contacto acreditado.
- `reports/local/heather-movement-parallel-gap-seed-v1.json`, SHA-256
  `dff8c28addac38c96a32d7366f0fc84ae17e89b816790a969f07781ff97b0c58`.
  Semilla y dos observaciones de pausa exactas respecto de C98; grabación
  iniciada, sin nueva restauración. Su final se audita en el informe siguiente.
- `reports/local/heather-movement-parallel-gap-recording-v1.json`, SHA-256
  `656f0bcbde541dd22b922534a59dce5ecd5e78788b019e340d0fdfad507b8234`.
  C99 y 26446 paquetes verificados; 136 tramos, sin botones de carrera
  ni direcciones opuestas. Normal/`-O` idénticos; no acredita contacto.
- `reports/local/heather-movement-parallel-gap-restore-v1.json`, SHA-256
  `1296b7c66ae040281b23621d42fee2aa7cd6d0047f87ea2e228fc1d35409e4b8`.
  C100, undécima restauración, diferencia de planificador 82→16 preservada;
  RAM/registros iguales. Normal/`-O` idénticos, fallo estricto explícito.
- `reports/local/heather-movement-oblique-route-restore-v1.json`, SHA-256
  `6288dc5e987c56393a9d2d3ff0098aab67dbdcff64845d56156175cee1e8b0a8`.
  C78, novena restauración; RAM/registros iguales, planificador 624→16.
  Normal/`-O` idénticos; fallo estricto preservado.
- `reports/local/heather-movement-oblique-route-recording-v1.json`, SHA-256
  `b2f5d89b1ea3e04739dc5af396053a54a44b32c1928fa3fe4e4ff0235104f05c`.
  C77 y 4.777 paquetes verificados, 102 tramos; tres fotogramas con botones
  opuestos preservados literalmente. Normal/`-O` idénticos; sin contacto nuevo
  atribuido todavía.
- `reports/local/heather-movement-variants-remaining-v1.json`, SHA-256
  `6c345442ebbfcf58a256adbf6665532cc4f54fd75d0676d7ce54c58d47170aff`.
  C73→C74 sin hits restantes; cuatro bytes RAM y −55 ciclos frente a C69,
  conservados sin enmascarar. Normal/`-O` idénticos.
- `reports/local/heather-movement-variant-preconditions-v1.json`, SHA-256
  `d5395c77c08003caf78c249c9f7fffa7901b90f93ec8071ad6034da39c22c764`.
  28 opcodes ELF/RAM: inicialización, helpers de flags y sitios previos a
  los descartes; identificación estática, no nuevos pares de instrucciones.
  Normal/`-O` idénticos.
- `reports/local/heather-movement-preconditions-restore-v1.json`, SHA-256
  `ac8f74748fbc3abfe42d753149df3427a31b872137e97122006f8166d175d2a8`.
  C75, octava restauración; fallo estricto del planificador preservado,
  margen 1748→16. Normal/`-O` idénticos.
- `reports/local/heather-movement-preconditions-search-v1.json`, SHA-256
  `0eddcc7a757db7fc40f227555720fcac7d44c291faf04d1ef491f2b891776e3e`.
  C75→C76: seis filtros, sin hits intermedios; diferencias frente a C69/C74
  explícitas. Normal/`-O` idénticos; alcance de propietario y 2–8 candidatos.
- `reports/local/heather-movement-oblique-route-seed-v1.json`, SHA-256
  `62844c1bc8fcba1086e7d63a06d8224f4f05c78a9c3af64fa63731ee6151743a`.
  Semilla y pausa C76 exactas, sin nueva restauración; controles auditados
  posteriormente en el informe del recorrido.
- `reports/local/heather-movement-operand-angle-tail-v1.json`, SHA-256
  `e23fd72de85153f4a9c3de335cd0f905ae5ec8247914028dfd7e604b18a26918`.
  C69 y búsqueda negativa acotada desde C68, sin restaurar.
- `reports/local/heather-movement-operand-angle-restore-v1.json`, SHA-256
  `d6fefeb93c4f443259a7ceda5deeb5ddcbd1603f2080f5fc2f2d62dd0523f3db`.
  C70 y séptima restauración; discrepancia de planificador conservada.
- `reports/local/heather-movement-discard-variants-contract-v1.json`, SHA-256
  `3d5c71cd56939383659a2e8bf3877c3140b3e9b932e94b22bc7371bb77515219`.
  Contrato estático de 38 opcodes y tres predicados; no acredita por sí solo
  que se hayan ejecutado sus ramas.
- `reports/local/heather-movement-type2-discard-v1.json`, SHA-256
  `d8b2c3ba5b8038fa70ed09c6be4040d02cc65ba0b7eaf1779b55fb34d07fabab`.
  C71–C73, rama/SW, tipo 2→−1, banco 0, formas 54/55 y salida de una aplicación.
  Los cuatro informes son idénticos en ejecución normal y `-O`.
- `reports/local/heather-movement-intermediate-passes-preparation-v1.json`, SHA-256
  `5ecd674b50aec792805f82450979de764b7a04b7e8d4ac1cb64b69843fee1857`.
  Preparación offline, fuentes/copia, filtros, código y presupuesto verificados.
- `reports/local/heather-movement-intermediate-passes-restore-v1.json`, SHA-256
  `6e3cf26975d4b0bfd4a2a408b33eac29ba49751716a14f6cba3a7fc59d353a3a`.
  Sexta restauración auditada; fallo estricto de planificador conservado.
- `reports/local/heather-movement-intermediate-passes-v1.json`, SHA-256
  `8b427301fbb224749e6a3ab8e366d3fbe247c5b4662c0544b0484bd98a7aada1`.
  C22–C68, cuatro llamadas, cuantización/sumas/escrituras, balance exacto
  y diferencias temporales C47/C15 y C68/C16. Informes normal/`-O` idénticos.
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
- `reports/local/heather-movement-profile-input-v1.json`, SHA-256
  `2840a67cd968c98e38fb44bc4169de5197cc9c718d982f848960165ff8177a47`.
  Controles cerrados y agrupados; ausencia explícita de liberaciones.
- `reports/local/heather-movement-profile-recording-verification-v1.json`, SHA-256
  `c7afa6dcb9f84a7ccbf029414150704c3c1a1c3c8ffbe5b62e1575bd0615c821`.
  Payload literal independiente, semilla/copia y extremo manual 203 reabiertos.
- `reports/local/heather-movement-left-moving-replay-v1.json`, SHA-256
  `af42193f8297a5585b9dd2a0b6321b27b858c14d95f0813b1d481dfdfe1ff32e`.
  Dos anclas y 18 capturas; tres pares SQC2, tres SWC1 y matrices finales.
  Normal/`-O` idénticos. HM-T2b suma 23 pares SQC2 y 17 pares escalares
  SW/SWC1 de una instrucción; las dos ramas con delay slot siguen separadas.
- `reports/local/heather-movement-profile-contact-search-v1.json`, SHA-256
  `192bc1385f3efc4a6712e3d624f2308a577e6cbfd42cd80704ebcd70648fc5f8`.
  Informe histórico con errata de contador descrita arriba: parada final 224,
  sin otra parada observada con sus filtros; A/B/RAM verificados y diferencia de fase/posición frente a 203 preservada.
  Normal/`-O` idénticos, sin atribución de una esquina ni equivalencia de trayectoria.
- `reports/local/heather-movement-wall-corner-seed-v1.json`, SHA-256
  `6ac74f899efa2d4477a658222825a2d3287f050ce849bdf012e1898f2c7d30a0`.
  Semilla nueva exacta respecto a 224 y dos observaciones de pausa/actor/ordinal;
  controles posteriormente auditados en el informe de grabación siguiente.
- `reports/local/heather-movement-wall-corner-recording-v1.json`, SHA-256
  `ab2912f16a141435e700790be282901470b113b1a7b20efe2d631d9e95f84d7f`.
  Final 225 y payload literal de 2722 fotogramas; normal/`-O` idénticos.
- `reports/local/heather-movement-wall-route-restore-v1.json`, SHA-256
  `2d07c42321086845b58081c2a2f8bba57dbac643fb7f12b84f662c95d205f43f`.
  Rechazo estricto de 226 conservado y acotado al planificador EE;
  normal/`-O` idénticos, sin equivalencia temporal acreditada.
- `reports/local/heather-movement-wall-pair-v1.json`, SHA-256
  `83a730ec2d9e746b21b9b1cde6aa775aefe0f2857a1fe3b8e1f6f48194865753`.
  21 estados reabiertos (227–247), contador 1→2, cuatro consultas, normales,
  descarte de 138, dos SWC1 y matriz. Normal/`-O` idénticos; incluye la errata
  de contador y la etiqueta equivocada de 228. Total HM-T2b: 23 pares SQC2
  y 19 pares SW/SWC1 de una instrucción; las ramas con delay siguen aparte.
- `reports/local/heather-movement-retained-anchor-v1.json`, SHA-256
  `3ba18f6455d0fd2d6feac21e1f04c8212122a61586772b040d18812e4052622f`.
  Retorno 248: contador real 2, tipos `(2,2)`, vectores idénticos y propietario
  del banco efectivo; normal/`-O` idénticos. La publicación se añadió después
  en el informe siguiente sin modificar este recibo histórico.
- `reports/local/heather-movement-retained-publication-v1.json`, SHA-256
  `9aa5a742e49fc9623f1bc9674e17ba52cbc2ea59fd0b4348bb1a1510c962ece7`.
  Cinco capturas nuevas, dos pares SWC1, posición/centro/matriz y límites de
  atribución; normal/`-O` idénticos. Total HM-T2b: 23 pares SQC2 y 21 pares
  SW/SWC1 de una instrucción; las ramas con delay siguen aparte.
- `reports/local/heather-movement-combiner-search-v1.json`, SHA-256
  `6e47b72e3e61c85865e5f283df240440e984705c5d59c8f6e629a3bb94653267`.
  Parada final 254, filtros y código fijados, referencia compatible con 248
  y coincidencia espacial del extremo; normal/`-O` idénticos. El par de la
  función sigue sin capturarse; el informe no declara esa verificación aprobada.
- `reports/local/heather-movement-combiner-restore-v1.json`, SHA-256
  `b27f159de61fb6aa21fc3f5251772bbb4f06beb979ca0b9571b73fa404248c32`.
  Frontera C00 y cuarta restauración declarada, diferencia estricta del
  planificador preservada; normal/`-O` idénticos.
- `reports/local/heather-movement-combiner-calls-v1.json`, SHA-256
  `334c9bcf5da415aa71de8dbc7696dbdb49fb2cb59913a81aeeee0e099c11f6d1`.
  C01–C06 reabiertos, dos llamadas, contador 0→1→2, VF4/salida/pila y RAM
  completa contrastados; normal/`-O` idénticos. Coincidencia RAM/GPR con 248
  y diferencia de −34 ciclos explícitas. Total de llamadas aisladas: dos,
  separado de los pares de instrucciones.
- `reports/local/heather-movement-discard-search-v1.json`, SHA-256
  `0c95c8e6de625ee769ffb4ba18b98fc7f3bb929f2b4616a98a2d0753cf66a4e0`.
  C07–C10 reabiertos; SW del descarte, salida/contador, fuentes A/B y parada
  final comprobados. Informe normal/`-O` idéntico; búsqueda acotada sin par
  de operandos distintos, otras rutas de descarte pendientes.
- `reports/local/heather-movement-distinct-route-seed-v1.json`, SHA-256
  `37200fc9f5a8b7b914b9890f1c3e4d66c1623faedc84306a67bf2b4d341d244c`.
  Semilla nueva SHA-256
  `850fb64966e7f4470d8c68238431ca465a614b17f75f405b188f8ba2feaa2e9f`,
  14 975 574 bytes, exacta respecto de C10 en el alcance descrito; observador
  confirma la misma pausa. La semilla por sí sola no acredita otra esquina.
- `reports/local/heather-movement-distinct-route-recording-v1.json`, SHA-256
  `4c0f7afaf23914c7c457c1967e882a98634ba4289909f767d553c9d876a5ba22`.
  Reconstrucción literal de controles, C11 reabierto y solapamiento de
  direcciones explícito; normal/`-O` idénticos. Grabación SHA-256
  `0b882900bb541ab04ffa7ac6d580423dc055f2d7d910e46ee99ca78d327e3313`.
  Plan privado `distinct-route-replay-plan-v1.json`; filtros SHA-256
  `7166651e1bcbcfe19fda7b55efee07fb2e22254289aad7d4df53be3158231e75`.
- `reports/local/heather-movement-distinct-route-restore-v1.json`, SHA-256
  `e1fc236c138760f80858196ae712ea7151d6fe6bcc3e5b93abb81068a5e4c467`.
  C12 reabierto, quinta restauración y diferencia de planificador 1748→16
  conservadas; normal/`-O` idénticos.
- `reports/local/heather-movement-distinct-combine-call-v1.json`, SHA-256
  `38c1db1e685279208ece0f4025f4f7aca4e5880b230df4ca7132811e28d78c57`.
  C13–C15, operandos distintos, 65 ciclos, salida/contador/pila/VF4 y RAM
  completa auditados; formas 25/26 y pertenencia a lista/A/B verificadas.
  Normal/`-O` idénticos. Plan privado de publicación
  `distinct-publication-plan-v1.json`, filtros SHA-256
  `012aba92ad878daecf81b8bfdeac65ed972833734ed20e37482814f4766bd7d3`.
- `reports/local/heather-movement-distinct-publication-v1.json`, SHA-256
  `59bc89dd72d166a8a5520222af370b11eb38bb8955b8d1dc70d31ebc794c0e10`.
  C16–C20 reabiertos; dos SWC1, delta de publicación y matriz final exactos.
  Residuo XYZ cero con W/contador 2 explícito; las pasadas intermedias quedan
  fuera de ese informe histórico y se atribuyen en `intermediate-passes-v1`.
  Informe normal/`-O` idéntico.
- Herramientas locales de variantes en `build/heather-movement`:
  `prepare_operand_angle_search.py`, `capture_operand_angle_search.py`,
  `operand_angle_state.py`, `audit_operand_angle_tail.py`,
  `prepare_operand_angle_replay.py`, `capture_operand_angle_replay.py`,
  `operand_angle_replay_state.py`, `audit_operand_angle_restore.py`,
  `discard_variants_reference.py`, `discard_branch_evidence.py`, sus pruebas,
  `audit_discard_variants_contract.py`, `audit_type2_discard.py` y
  `prepare_variants_remaining.py`.
- Para el cierre de `parallel-edge-v1` y el objetivo dirigido:
  `audit_parallel_edge_recording.py`, `prepare_parallel_edge_replay.py`,
  `capture_parallel_edge_replay.py`, `parallel_edge_state.py`,
  `audit_parallel_edge_restore.py`, `audit_parallel_edge_search.py`,
  `audit_parallel_geometry.py`, `prepare_parallel_gap_recording.py`,
  `verify_parallel_gap_seed.py` y `capture_parallel_gap_endpoint.py`.
  C99 quedó preservado con escritura exclusiva. La nueva copia utiliza
  `audit_parallel_gap_recording.py`, `prepare_parallel_gap_replay.py`,
  `capture_parallel_gap_replay.py`, `parallel_gap_state.py` y
  `audit_parallel_gap_restore.py` y `audit_parallel_gap_search.py`; no sobrescribe
  estados anteriores. La búsqueda de presencia usa `prepare_gap_presence_replay.py`,
  `capture_gap_presence_replay.py`, `gap_presence_state.py`,
  `audit_gap_presence_restore.py` y `audit_gap_presence_stop.py`.
- Herramientas locales añadidas para las pasadas en `build/heather-movement`:
  `prepare_intermediate_passes.py`, `capture_intermediate_passes.py`,
  `intermediate_pass_state.py`, `audit_intermediate_passes_plan.py`,
  `audit_intermediate_passes_restore.py`, `audit_intermediate_passes.py`,
  `center_w2_evidence.py` y sus pruebas sintéticas. Mantienen separados
  adquisición, reconstrucción, comprobadores puros y reporte.
- Herramientas locales anteriores en `build/heather-movement`: `capture_b.py`,
  `peek_b.py`, `audit_b.py`, `audit_extra.py`, `scalar_evidence.py`,
  `vu_evidence.py`, `audit_contact_arithmetic.py`, `center_evidence.py`,
  `origin_evidence.py`, `audit_micro_candidate.py`, `audit_center_origin.py`,
  `wall_references.py`, `audit_wall_inventory.py`, `prepare_profile_recording.py`,
  `verify_profile_seed.py`, `audit_profile_input.py`, `verify_profile_recording.py`,
  `launch_profile_recovery.py`, `capture_recovered_profile.py` y `audit_profile_replay.py`
  junto con `prepare_profile_contacts.py`, `capture_profile_contact_search.py`,
  `audit_profile_contact_search.py`, `prepare_wall_corner_recording.py`
  y `verify_wall_corner_seed.py`, `audit_wall_corner_recording.py`,
  `audit_wall_route_restore.py`, `candidate_evidence.py`, `audit_wall_pair.py`,
  `audit_retained_anchor.py`, `audit_retained_publication.py`,
  `combination_reference.py`, `audit_combiner_search.py`, `prepare_combiner_replay.py`,
  `capture_combiner_replay.py`, `audit_combiner_restore.py`, `combiner_evidence.py`
  y `audit_combiner_calls.py`, `prepare_distinct_discard_search.py`,
  `capture_distinct_discard.py`, `prepare_distinct_only.py`,
  `discard_reference.py`, `audit_discard_search.py`,
  `prepare_distinct_route_recording.py`, `verify_distinct_route_seed.py`
  y `capture_distinct_route_endpoint.py`, `audit_distinct_route_recording.py`,
  `prepare_distinct_route_replay.py`, `capture_distinct_route_replay.py`
  y `audit_distinct_route_restore.py`, `distinct_route_state.py`,
  `audit_distinct_combine_call.py`, `prepare_distinct_publication.py`,
  `audit_distinct_publication.py`
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
rtk proxy .venv/bin/python build/heather-movement/audit_profile_replay.py /tmp/hm-left-moving-replay.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_profile_replay.py /tmp/hm-left-moving-replay-optimized.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_candidate_evidence.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_wall_pair.py /tmp/hm-wall-pair.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall_pair.py /tmp/hm-wall-pair-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_retained_anchor.py /tmp/hm-retained-anchor.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_combination_reference.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_retained_publication.py /tmp/hm-retained-publication.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_retained_publication.py /tmp/hm-retained-publication-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_combiner_search.py /tmp/hm-combiner-search.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_combiner_evidence.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_combiner_calls.py /tmp/hm-combiner-calls.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_combiner_calls.py /tmp/hm-combiner-calls-optimized.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_discard_reference.py --cov=discard_reference --cov-branch --cov-config=/dev/null --cov-report=term-missing -q
rtk proxy .venv/bin/python build/heather-movement/audit_discard_search.py /tmp/hm-discard-search.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_discard_search.py /tmp/hm-discard-search-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_distinct_route_recording.py /tmp/hm-distinct-route-recording.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_distinct_route_recording.py /tmp/hm-distinct-route-recording-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_distinct_route_restore.py /tmp/hm-distinct-route-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_distinct_route_restore.py /tmp/hm-distinct-route-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_distinct_combine_call.py /tmp/hm-distinct-combine-call.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_distinct_combine_call.py /tmp/hm-distinct-combine-call-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_distinct_publication.py /tmp/hm-distinct-publication.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_distinct_publication.py /tmp/hm-distinct-publication-optimized.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_center_w2_evidence.py --cov=center_w2_evidence --cov-branch --cov-config=/dev/null --cov-report=term-missing -q
rtk proxy .venv/bin/python build/heather-movement/audit_intermediate_passes.py /tmp/hm-intermediate-passes.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_intermediate_passes.py /tmp/hm-intermediate-passes-optimized.json
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_discard_variants_reference.py --cov=discard_variants_reference --cov-branch --cov-config=/dev/null --cov-report=term-missing -q
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_discard_branch_evidence.py --cov=discard_branch_evidence --cov-branch --cov-config=/dev/null --cov-report=term-missing -q
rtk proxy .venv/bin/python build/heather-movement/audit_type2_discard.py /tmp/hm-type2-discard.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_type2_discard.py /tmp/hm-type2-discard-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_variants_remaining.py /tmp/hm-variants-remaining.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_variants_remaining.py /tmp/hm-variants-remaining-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_variant_preconditions.py /tmp/hm-variant-preconditions.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_variant_preconditions.py /tmp/hm-variant-preconditions-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_preconditions_restore.py /tmp/hm-preconditions-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_preconditions_restore.py /tmp/hm-preconditions-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_preconditions_search.py /tmp/hm-preconditions-search.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_preconditions_search.py /tmp/hm-preconditions-search-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_oblique_route_recording.py /tmp/hm-oblique-route-recording.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_oblique_route_recording.py /tmp/hm-oblique-route-recording-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_shared_axis_call.py /tmp/hm-shared-axis-call.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_shared_axis_call.py /tmp/hm-shared-axis-call-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_rejection.py /tmp/hm-parallel-rejection.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_rejection.py /tmp/hm-parallel-rejection-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_oblique_search_end.py /tmp/hm-oblique-search-end.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_oblique_search_end.py /tmp/hm-oblique-search-end-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_flag_writer_scope.py /tmp/hm-flag-writer-scope.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_flag_writer_scope.py /tmp/hm-flag-writer-scope-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_edge_recording.py /tmp/hm-parallel-edge-recording.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_edge_recording.py /tmp/hm-parallel-edge-recording-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_edge_restore.py /tmp/hm-parallel-edge-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_edge_restore.py /tmp/hm-parallel-edge-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_edge_search.py /tmp/hm-parallel-edge-search.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_edge_search.py /tmp/hm-parallel-edge-search-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_geometry.py /tmp/hm-parallel-geometry.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_geometry.py /tmp/hm-parallel-geometry-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_gap_recording.py /tmp/hm-parallel-gap-recording.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_gap_recording.py /tmp/hm-parallel-gap-recording-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_gap_restore.py /tmp/hm-parallel-gap-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_gap_restore.py /tmp/hm-parallel-gap-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_parallel_gap_search.py /tmp/hm-parallel-gap-search.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_parallel_gap_search.py /tmp/hm-parallel-gap-search-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_presence_restore.py /tmp/hm-gap-presence-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_presence_restore.py /tmp/hm-gap-presence-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_presence_stop.py /tmp/hm-gap-presence-stop.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_presence_stop.py /tmp/hm-gap-presence-stop-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_wall14.py /tmp/hm-gap-wall14.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_wall14.py /tmp/hm-gap-wall14-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_presence_closure.py /tmp/hm-gap-presence-closure.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_presence_closure.py /tmp/hm-gap-presence-closure-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_target_restore.py /tmp/hm-gap-targeted-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_target_restore.py /tmp/hm-gap-targeted-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_neighborhood.py /tmp/hm-gap-neighborhood.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_neighborhood.py /tmp/hm-gap-neighborhood-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_targeted_recording.py /tmp/hm-gap-targeted-recording.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_targeted_recording.py /tmp/hm-gap-targeted-recording-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_targeted_replay_restore.py /tmp/hm-gap-targeted-replay-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_targeted_replay_restore.py /tmp/hm-gap-targeted-replay-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_gap_targeted_closure.py /tmp/hm-gap-targeted-closure.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_gap_targeted_closure.py /tmp/hm-gap-targeted-closure-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_query_restore.py /tmp/hm-wall60-query-restore.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_query_restore.py /tmp/hm-wall60-query-restore-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_query.py /tmp/hm-wall60-query.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_query.py /tmp/hm-wall60-query-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_internal.py /tmp/hm-wall60-internal.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_internal.py /tmp/hm-wall60-internal-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_approach.py /tmp/hm-wall60-approach.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_approach.py /tmp/hm-wall60-approach-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_closer_closure.py /tmp/hm-wall60-closer.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_closer_closure.py /tmp/hm-wall60-closer-optimized.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

**Decisión 2026-10-29:** el usuario pospone HM-T2b.6 y solicita avanzar con
los datos existentes. Sigue el [núcleo nativo HMN v1](../../schemas/heather-movement-native-v1.md),
con contacto separado, sin cerrar la investigación general.
La [guía de acceso por etapas](f06-01-heather-wall60-access.md) se conserva
como evidencia; no hay otro recorrido solicitado. La referencia geométrica está definida; la llegada
y el contacto con 60 siguen pendientes. C121–C132, excepto C127, explican el
rechazo interno por límites X/Z separados; C133–C135 lo contrastan con ↑.
C136–C137 terminan la búsqueda más estrecha sin coincidencias nuevas ni
pasos del rechazo observados. El final C137 está preservado; su reproducción quedó detenida.
La navegación posterior llega hasta C148, en el primer control del regreso
desde C146. Los giros adicionales de C146 y la barrera de C144 quedan
separados. La llegada a P sigue pendiente; intentos y pausas están en el
informe de acceso. PCSX2 está pausado tras el paso posterior a C148. C137 coincide con C110 en los dominios
descritos salvo ocho bytes del prefijo EE, cuya causa sigue pendiente.
Los controles originales siguen íntegros. C114 registra la decimoquinta
frontera; no hubo nuevas restauraciones en este lote.
La pared 14 está aceptada/incorporada; siguen la 60, el par simultáneo y
su filtrado. Las prolongaciones 12/13 están inventariadas; observar su
efecto sin inferir inaccesibilidad global. Las diferencias de ciclos y
bytes EE permanecen explícitas.
C98 cierra la reproducción anterior sin los descartes vigilados;
C96 y sus controles originales están verificados. C95 cierra otra búsqueda
sin descartes restantes; las seis escrituras globales de flags no cierran
la posibilidad de otros escritores. El requisito previo paralelo ya se alcanzó y conservó ambos
candidatos en C91–C94. El caso de eje compartido queda verificado
en C79–C90 hasta cuantización; su publicación en la posición y las demás
variantes aritméticas siguen pendientes. Las dos pasadas anteriores alcanzaron
sus paradas finales sin las variantes restantes; las condiciones previas
vigiladas tampoco produjeron hits en el recorrido completo. El descarte de tipo 2 frente a tipo 1 ya está verificado
en C71–C73, sin cerrar su construcción angular general. Las
pasadas entre los equivalentes de C15 y C16 y el balance total con las formas
25/26 ya están verificados en esta actualización; se conservan los límites
de los intervalos de movimiento y las diferencias temporales. Sus escrituras
X/Z y matriz final históricas siguen verificadas. La entrada/retorno
de copia inicial, vectores idénticos y una
combinación distinta, así como una escritura de descarte angular y su efecto,
ya están verificados;
conservar como pendientes las demás ramas, el tipo `−2` y los
valores que requieren redondeo. El contador, tipos, operandos y propietario
se deben revalidar por llamada, incluidos cambios de banco.
No equiparar dos registros con dos empujes independientes. Continúan abiertas
las atribuciones de las ventanas de giro y el resto de variantes de contacto. La suma no nula y el origen del
microajuste X quedan verificados en el alcance descrito; el residuo Y histórico
queda separado. El plano y las conversiones conservan su alcance de cuatro
llamadas, sin cerrar el solver general. La comparación
acotada de operandos de HM-T2b.5 queda verificada; sus diferencias de ciclos,
la autoridad general sigue pendiente. El contrato nativo HMN v1 acota el
trabajo siguiente sin equipararlo a la ley general PS2; HM-T2 y F06.01 siguen abiertos.
El build físico aceptado `7250f427ffb9` permanece sin cambios.
