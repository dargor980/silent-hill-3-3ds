# CF-T9c: escritores de Y en las colas residuales

Estado: las dos colas de la fase intermedia y la llamada anterior de fila 1/
buffer 0 están reproducidas y enlazadas con la evidencia original. La cola
de fila 2/buffer 1 ya estaba enlazada con una copia del recorrido original.
La unicidad de la última llamada entre capturas permanece sin demostrar.
Requisitos CF04/CF09–CF11/CF13 y RF02.04/RF02.05. Continúa la
[investigación de ciclo de vida](f03-04-collision-runtime.md) y la tarea
[CF-T9c](../specs/sh3-3ds/collision-shapes-research.md).

## Contrato de observación

- **CF-Y01:** WHEN se restaure un estado para localizar un escritor THEN la
  adquisición SHALL declarar restauración, perfil propio y origen fijado,
  sin incorporarla a la continuidad original.
- **CF-Y02:** WHEN se atribuya una escritura a `SQC2` THEN el verificador SHALL
  enlazar PC anterior/posterior, opcode, dirección efectiva, VF4 guardado,
  ciclos, GPR y todos los bytes de RAM fuera del vector de destino.
- **CF-Y03:** WHEN se compare la cola con capturas posteriores THEN la auditoría
  SHALL comparar todos sus bytes, incluidos Y, y conservar por separado la
  procedencia observada y las coincidencias que no identifican una llamada.
- **CF-Y04:** IF faltan capturas de un escritor THEN el informe SHALL mantener
  esa atribución pendiente aunque una traslación candidata reproduzca los bytes.
- **CF-Y05:** IF la suma binary32 del host difiere de VU THEN la auditoría SHALL
  registrar la discrepancia sin ampliar tolerancias ni habilitar respuesta física.

## Inventario de las cuatro colas

Cada fila tiene dos buffers de `0x2D0` bytes, stride de fila `0x5A0` y registros
de 80 bytes. Después del cambio de fase, la fila 1 copia cinco registros y
deja tres anteriores; la fila 2 copia uno y deja siete. Hay **20 registros
residuales, 80 componentes Y**, considerando ambos buffers.

| Fila / buffer | Dirección inicial de la cola | Registros | Evidencia de procedencia |
|---|---|---:|---|
| 1 / 0 | `0x01EEA760` | 3 | Copia anterior observada desde estado 24 intacto: llamador `0x01EE2178`, actor `0x0044B3D0`, instancia `0x03F5`, Y = −25. Cola idéntica a los estados originales 25/29/54. |
| 1 / 1 | `0x01EEAA30` | 3 | Copia de fase 5 observada en esta repetición. Actor `0x0044B3D0`, instancia `0x03F5`, Y = −298,89453125. |
| 2 / 0 | `0x01EEABC0` | 7 | Copia de fase 5 observada en esta repetición. Actor `0x0044B6F0`, instancia `0x03F6`, Y = −324,99517822265625. |
| 2 / 1 | `0x01EEAE90` | 7 | Coincide con la copia real anterior 21→22, traslación Y = 48,205078125, y con los extremos posteriores. No se excluyen reescrituras idénticas entre capturas. |

Los dos actores de fase 5 son de tipo `0x020C`. El llamador `0x01EE26B8`
selecciona fuente y destino, entrega el vector en `sp+0x140` y retorna a
`0x01EE26C0`. La palabra Y del vector coincide bit a bit con `actor+0x24`.
El código del overlay localiza el productor de posición en `0x01EE2644` y
la entrega de Y al vector en `0x01EE268C`; esas dos instrucciones no están
individualmente delimitadas por las nuevas capturas.

## Repetición sin cambios de PC ni RAM

Perfil privado `f03-04-collision-y-writer-v1`, PID 17679, una restauración de
una copia **idéntica del archivo completo** del estado 25. SHA de origen/copia:
`79c6183de32a6b0a339c0e578f7ae819ecb6fe185b2e029f0b060d7684e307f6`.
El estado inicial vuelve a PC `0x001A0CD0`, ciclo 192.193.237.299, con toda
la RAM EE y los GPR low32 idénticos al original. No se fuerza ningún PC ni
se parchea memoria. BIOS y tarjetas se copian al perfil y se preservan los
originales. El ejecutable instrumentado fijado se reutiliza sin recompilar.

Los filtros buscan la última iteración de fase 5: temporizador de juego en
`0x01CFB960` mayor que 8, filas 1/2 y retorno `0x01EE26C0`. La muestra acepta
8,039992332458496. Las instrucciones de salida comprueban ese temporizador,
preparan estado 6 y abandonan la fase. Los breakpoints no modifican esos datos.

La fase 5 alterna el buffer después de **cada fila**. En esta ejecución la
fila 0 empieza en buffer 0, la fila 1 usa 1 y la fila 2 usa 0; las doce filas
dejan el selector listo para repetir el mismo patrón. Esto explica la
distinta procedencia de las dos colas de cada fila. No se confunde ese selector
con el selector de los bancos de mundo.

| Capturas nuevas | Operación | Resultado |
|---|---|---|
| 1 | Restauración inicial | Archivo de origen y RAM/ciclo/PC enlazados. |
| 2→11 | Copia de fila 1, buffer 1 | Ocho registros desde `0x01EE3CD0` a `0x01EEA8A0`, 479 ciclos. |
| 3→4, 5→6, 7→8, 9→10 | Cuatro stores del primer registro residual de fila 1 | Cada par ejecuta una sola SQC2; escritura exacta de VF4 y RAM restante intacta. |
| 12→21 | Copia de fila 2, buffer 0 | Ocho registros desde `0x01EE5620` a `0x01EEAB70`, 479 ciclos. |
| 13→14, 15→16, 17→18, 19→20 | Cuatro stores del primer registro residual de fila 2 | Misma comprobación de instrucción, dirección, VF4 y RAM completa. |
| 22 | `0x01EE2730`, antes de almacenar estado 6 | Última iteración de fase 5 terminada, `v0=6`. |
| 23 | `0x01EE28C8`, fase posterior | Las cuatro colas coinciden completas con las capturas originales 29 y 54. |

Los escritores inmediatos son:

| PC | Instrucción | Destino dentro del registro |
|---|---|---|
| `0x001A0D18` | `sqc2 vf4, 0(t0)` | `+0x10`, vértice 0 |
| `0x001A0D30` | `sqc2 vf4, 0(a3)` | `+0x20`, vértice 1 |
| `0x001A0D48` | `sqc2 vf4, 0(a3)` | `+0x30`, vértice 2 |
| `0x001A0D60` | `sqc2 vf4, 0(a3)` | `+0x40`, vértice 3 |

Cada store guarda XYZ/W, incluido Y, en dos ciclos observados. VF4 se lee
del estado nativo fijado: tag único `vuMicroRegs` en offset 14.030, ACC de
16 bytes y array VF de vectores de 16 bytes. La auditoría fija `VUmicroMem.cpp`,
`VU.h` y `SaveState.cpp`, valida ese layout y compara la escritura byte a byte.
No obtiene VF4 ajustando un resultado esperado a la salida.

Y del primer registro residual escrito:

- Fila 1/buffer 1: −1636,39453125; −2465,74462890625;
  −2465,74462890625; −1636,39453125.
- Fila 2/buffer 0: −556,69512939453125; −1662,4951171875;
  −1662,4951171875; −556,69512939453125.

Los ocho stores están delimitados directamente. Los demás vértices se enlazan
por la copia completa de ocho registros, sus entradas y el bucle fijado; no
se declara una captura individual de las 80 componentes residuales.
Las dos colas actualizadas suman 40 componentes Y. Sus bytes de salida coinciden
con 22, 23 y los estados originales 29/54. Las otras dos colas coinciden con
los extremos 1 y 23 de la repetición. Estas coincidencias no constituyen una
traza exhaustiva de todas las escrituras ni excluyen reescrituras idénticas.

El PC final coincide con el original 29, pero el ciclo es 203.022.344.035,
**110 ciclos después** del original. Se registra la diferencia; no se atribuye
sin más a una causa ni se declara historia de CPU idéntica entre sesiones.

## Pruebas, auditoría y límites

El oráculo de stores exige opcode, PC+4, dos ciclos, mismo PID/sesión/GPR,
dirección alineada, VF4 exacto y ausencia de cambios fuera de 16 bytes en toda
la RAM. El selector valida etapa, temporizador, actor, tabla, banco y vector.
La procedencia restaurada tiene esquema propio y es rechazada por el validador
normal incluso si se cambia su etiqueta. Se conserva la separación entre
adquisición, validadores puros y auditoría de archivos.

62 pruebas nuevas; **424 auxiliares aprobadas** en modo normal y con `-O`
(aviso esperado de pytest). Se cubren los cuatro stores, escrituras ajenas,
PC/ciclo/sesión incorrectos, VF4 erróneo, layout ausente/duplicado/truncado,
tabla/banco/actor/traslación inválidos y clasificación engañosa de restauración.

Cada copia completa presenta ocho componentes distintos del cálculo binary32
host; la auditoría conserva ambos diagnósticos. No se cambia la tolerancia de
investigación previa `0,001` ni se afirma equivalencia PS2/VU. La escritura de
VF4 a memoria sí es exacta en los pares observados.

Se reprodujeron los informes previos y reverificaron **4.430 entradas**.
Recibos privados idénticos byte a byte, 1.043.452 bytes:

- `reports/local/f03-04-collision-y-writer-v1.json`
- `reports/local/f03-04-collision-y-writer-repeat-v1.json`
- SHA-256: `a81b732291a1c4c45a6787ccef99bf95407bbc9795cb37ec1a5b3c50ddb1bb7a`.

La sesión terminó con código 0, socket retirado y baselines intactos. Sus 23
capturas se cuentan aparte de las 57 originales y las dos del reset forzado.
Los estados y auxiliares permanecen privados; no se añaden a CI ni se publica
un build de consola por esta investigación.

```sh
rtk proxy .venv/bin/python -m pytest -q build/collision-runtime build/collision-y-writer
rtk proxy .venv/bin/python -O -m pytest -q build/collision-runtime build/collision-y-writer
rtk proxy .venv/bin/python build/collision-y-writer/audit.py --output /tmp/cf-t9-y-writer-new.json
```

## Llamada anterior de fila 1/buffer 0 capturada

Se completó otro perfil, `f03-04-collision-y-origin-v1`, con copia completa e intacta del estado
24 (SHA `540649afec5c9451ae3fa90e9e64274afdcef6ae1655adf74d20c7ed0a9562b7`).
Su captura inicial verifica PC `0x01EE2224`, ciclo 149.596.595.425.

Once breakpoints se limitan al llamador `ra==0x1ee2180`, fila `s4==1`, destino
`a1==0x1eea5d0`, cuatro stores antes/después en el registro `0x01EEA760` y
entrada de fase 5. La primera tentativa de adquisición se rechazó porque la
restauración aún no estaba pausada; la captura se hizo después de comprobar
el PC esperado. No hubo guardado aceptado con la VM ejecutándose.

El usuario continuó el acertijo con su teclado y avisó que PCSX2 se detuvo.
Se verificó PC `0x001A0CD0`, ciclo 257.062.635.232, PID 21731. A partir de
esa pausa se adquirieron la entrada, cuatro pares SQC2, salida, retorno y
actualización del selector. La sesión tiene **13 capturas propias**, una
restauración declarada y ningún cambio de PC o RAM por herramientas.
No se suma a la continuidad original.

| Capturas | Comprobación | Resultado |
|---|---|---|
| 1 | Restauración completa | RAM EE, GPR, PC y ciclo iniciales coinciden con el estado 24. |
| 2→11 | Copia previa, fila 1/buffer 0 | Ocho registros, 640 bytes, de `0x01EE3CD0` a `0x01EEA5D0`; 479 ciclos. Resto de RAM EE intacto. |
| 3→4, 5→6, 7→8, 9→10 | Cuatro SQC2 del registro `0x01EEA760` | Cada par escribe exactamente VF4 en 16 bytes, dura dos ciclos y conserva toda la RAM exterior. |
| 11→12 | Retorno a `0x01EE2180` | Registro de la lista en banco de mundo 1, contador 1→2, 26 ciclos; región del overlay conservada. |
| 12→13 | Actualización hasta `0x01EE2224` | Selector de buffer 0→1, 15 ciclos; máscara de fila 1 aplicada a bits `0x60`, que permanecen `0x60` porque ese bit ya estaba limpio. |

El llamador es `0x01EE2178`, con retorno `0x01EE2180`. Selecciona actor
`0x0044B3D0`, tipo `0x020C`, instancia `0x03F5`, fila `s4=1`; el vector en
`sp+0x140` contiene `(0, −25, 0, 0)` y su Y coincide bit a bit con `actor+0x24`.
El overlay fijado sitúa el productor de posición en `0x01EE2144` y la copia
al vector en `0x01EE2148`; estas dos SWC1 no se capturaron por separado.

Los Y del primer registro residual quedan en −1362,5; −2191,85009765625;
−2191,85009765625; −1362,5. La cola completa comprende tres registros,
240 bytes y 12 componentes Y. Era cero tanto en la captura 1 como en la
entrada 2. Después de la copia coincide **byte a byte** con los estados
originales 25, 29 y 54 y con el informe de la repetición de fase 5:

`db5ce72e09c79790250042f3fd3f290d7afc0edd9966a18d7fcbc1abfa8fc5d5`.

La cola admite comparación binary32 exacta; la copia completa presenta ocho
componentes distintos del cálculo host, todos fuera de esa cola, con diferencia
de un ULP (`0,000030517578125`). La primera tentativa de exigir exactitud a
toda la copia fue rechazada por el oráculo: se conserva la discrepancia y se
limita la afirmación exacta a la cola y a las escrituras VF4 observadas.
No se amplía la tolerancia previa ni se afirma equivalencia general de VU.

La adquisición, el adaptador de procedencia, la selección pura y la auditoría
permanecen separados. El adaptador admite únicamente el esquema de origen y
reutiliza el contrato de repetición fijado; no cambia campos de procedencia
ni muta el recibo. Los oráculos anteriores de copia, registro, selector y
SQC2 se reutilizan sin modificarlos. Se añaden 43 casos sintéticos para
procedencia, escena/actor/banco/vector inválidos y extremos históricos distintos:
**467 pruebas auxiliares aprobadas**, en modo normal y con `-O` (aviso
esperado de pytest). La igualdad de extremos devuelve
explícitamente `unique_last_invocation_verified=false`.

Dos auditorías reproducen los informes previos, reverifican **5.079 entradas**
y producen recibos idénticos de 1.184.092 bytes:

- `reports/local/f03-04-collision-y-origin-v1.json`
- `reports/local/f03-04-collision-y-origin-repeat-v1.json`
- SHA-256: `23625603a87ad2534f2fecdb27196c470373fa5487340a6fff5cc5eb344e01a3`.

Después de preservar la captura 13 se cerró el perfil de diagnóstico. El
lanzador confirmó código 0, socket retirado y todos los baselines intactos.
Su `closure.json` privado tiene 76 bytes y SHA
`67bc32d30070ff8afea17e3ed1dfc4f0c9dd4408042258727b79a7341d08787d`.
Los auxiliares y estados siguen fuera de CI; esta entrega no modifica el
decoder, el formato intermedio ni el visor de 2DS XL.

```sh
rtk proxy .venv/bin/python -m pytest -q build/collision-runtime build/collision-y-writer build/collision-y-origin
rtk proxy .venv/bin/python -O -m pytest -q build/collision-runtime build/collision-y-writer build/collision-y-origin
rtk proxy .venv/bin/python build/collision-y-origin/audit_origin.py --output /tmp/cf-t9-y-origin-new.json
```

La atribución de esta llamada deja de estar pendiente. **CF-T9c permanece
abierta por la unicidad del último escritor entre extremos** y los escritores
no delimitados del cambio de sala; una repetición desde estado 24 no reemplaza
la historia de CPU del recorrido original. El reset ocupado natural sigue
sin observar. CF-T9d conserva equivalencia numérica, contacto poligonal
aceptado, retorno exterior y respuesta física. El siguiente trabajo es acotar
posibles reescrituras y documentar el límite de atribución antes de cerrar CF-T9c.
