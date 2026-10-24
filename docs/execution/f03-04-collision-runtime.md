# F03.04 / CF-T9 — Consultas y ciclo de vida en PCSX2

2026-10-23. **CF-T9a–b completadas para la observación básica de consultas;
CF-T9c–d abiertas.** Hay dos consultas rechazadas y un par completo aceptado,
además de dos comprobaciones del llamador que conservan un resultado previo
más cercano. La misma sesión enlaza 54 capturas: transición al carrusel
posterior, traslaciones Y no nulas, 12 listas registradas en cada banco,
avance que vacía un contador ocupado y consulta de una forma residual que
devuelve rechazo. Se conserva la discrepancia numérica frente a binary32 host.
[Requisitos y tareas](../specs/sh3-3ds/collision-shapes-research.md).

## Capturas iniciales y custodia

La sesión `cf090001000000000000000000000001` se inició desde arranque nuevo,
con un perfil privado separado y una copia de la tarjeta europea existente.
El usuario cargó «16. Fortuneteller» desde el juego. No se cargaron estados
ni se escribieron argumentos o memoria del juego mediante PINE. Guardar
un estado nuevo para inspección no equivale a restaurarlo.

PCSX2 observer, SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
PID observado: `50191`. ELF europeo:
`cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`.
Los archivos quedan en el directorio privado `f03-04-collision-runtime-v1`.
No se añaden RAM, BIOS, estados, tarjetas, capturas binarias ni recursos al repositorio.

| Slot | Punto | PC | Ciclo EE | Observación |
|---:|---|---|---:|---|
| 01 | Entrada del ejecutable | `0x00100008` | 531.029.955 | Región dinámica objetivo cero; etapa/sala 0/0. |
| 02 | Entrada al reset | `0x0019FB30` | 3.871.200.770 | Ambos contadores ya estaban en cero. |
| 03 | Retorno del reset | `0x0019FBF0` | 3.871.200.856 | Registro completo de bancos sin cambios. |
| 04 | Cilindro, índice 0: entrada | `0x0019F2C0` | 36.284.719.354 | Recurso íntegro enlazado; celda 0. |
| 05 | Cilindro, índice 0: retorno | `0x001A6E34` | 36.284.719.388 | `v0=0`, indicador de salida 0. |
| 06 | Cilindro, índice 1: entrada | `0x0019F2C0` | 36.284.719.409 | Segundo índice de la misma lista. |
| 07 | Cilindro, índice 1: retorno | `0x001A6E34` | 36.284.719.443 | `v0=0`, indicador de salida 0. |

El slot 99 es un diagnóstico de localización del PC inicial, previo a 01;
carece del enlace completo de observador y **no integra las siete evidencias**.
Las primeras tentativas de abrir el depurador seleccionaron instancias
adicionales con el asistente de configuración. Se cerraron esas instancias;
todos los recibos aceptados pertenecen al PID fijado, no a esos procesos.

## Contrato de adquisición y verificación

El proveedor local, el verificador puro y el coordinador de archivos están
separados. Son auxiliares de investigación bajo `build/collision-runtime`,
no un decoder público ni código del visor. Aplican CF03/CF06/CF11–CF13:

1. Exigir proceso, ejecutable y sesión fijados; PINE debe informar pausa.
   Cada lectura del observador fija PC, ciclo, CRC europeo y traducción de RAM.
2. Leer por bloques de hasta 4.096 bytes, con un máximo de quince regiones.
   Las regiones básicas incluyen registro de bancos, tabla de recursos y
   los 17.280 bytes de la región dinámica y el byte inmediatamente posterior.
   Este byte adicional se observa, pero no se presume un terminador permanente.
   Las consultas añaden el CLD completo, la pila de argumentos y la salida
   del llamador. No se interpreta una lectura parcial como recurso completo.
3. Guardar un slot nuevo sin sobrescribir; leer los miembros acotados de su
   ZIP y cotejar CPU, ciclo y todas las regiones con el observador. Repetir
   las lecturas después de guardar y exigir igualdad. Los recibos y paquetes
   se escriben exclusivamente, con `fsync` y lectura de verificación.
4. Rechazar identidad, PC, ciclo, argumentos, índice, región, contenido o
   metadatos incoherentes. Para un par de consulta exigir entrada/retorno,
   orden de ciclos y conservación de los argumentos y de las entradas.
   Un rechazo no permite interpretar el punto de salida, que puede ser residual.
5. Reverificar archivos de entrada y originales al terminar. La continuidad
   se sustenta en la historia controlada de esta sesión y sus ciclos; los
   recibos no constituyen autenticación criptográfica de toda la ejecución.

La versión inicial de secuencia `slot*16+región` permite slots **1–15** con
el contrato del observador. No se deben planificar más capturas con esa fórmula
sin versionar el proveedor y su verificador. El SHA de configuración se
comprobó al adquirir cada muestra, pero los INI históricos no se archivaron.
Las muestras 01–03 y 04–07 tienen hashes de configuración distintos; esta
auditoría no afirma equivalencia byte a byte de esos INI. La siguiente versión
de adquisición deberá conservar también su copia exacta.

## Recurso activo y consultas rechazadas

Se identifica `tp21.cld` por sus **7.984 bytes completos**, comparados con
las dos extracciones A/B, el catálogo y el recibo de extracción:

- ID: `asset:d64829f38cf0ea01ada11d1de01360ad6e5faa5347bb79c43882d89383e5b4f9`.
- SHA-256: `af6ac94e5f4f9fc74a0e2d21322a75ad1e5068a479391a657513224dc4c8368e`.
- RAM: `0x0163FA00`, registrada desde `0x01D0A800`; habilitación,
  slots restantes, puntero/tamaño del cargador y selección de consulta comprobados.
- Grupo 4: offset `0x1EA0`, 144 bytes, dos registros de 48 bytes y terminador.
  La base pasada en `s1` y el cálculo `base+índice*48+16` coinciden.
- `s0` apunta a la lista de **celda 0** del recurso: primero índice 0 y luego 1.
  No se infiere el uso de la forma a partir de su nombre o presencia en archivo.
- Las capturas 04–07 están en etapa `0x22`, sala `0xE5`; no son el carrusel
  transformado de etapa `0x23` y sala `0xEB` de la investigación anterior.

Ambos extremos de la consulta están en **Y = −760**. En los dos cilindros,
esa altura es menor que su límite Y numéricamente menor. Cada llamada retorna
rechazo después de 34 ciclos EE; `v0` coincide con el indicador de salida.
Los puntos, parámetros del cilindro y selección de índice permanecen iguales
entre entrada y retorno. Las tres ventanas de código usadas para interpretar
consulta, llamador y reset coinciden con el ELF en las siete muestras.

Este lote inicial corrobora dos rechazos reales con Y fuera del cilindro,
compatibles con CF-T8. Por sí solo no verifica un impacto aceptado ni sustitución del mejor resultado,
tangencia, extremos del cilindro, segmento interno o degenerado, normal,
propietario ni respuesta física. El punto residual tras rechazo se excluye
expresamente del análisis.

## Inicialización y transición: alcance pendiente

Los 17.281 bytes de `0x01EEA030` a `0x01EEE3B0` inclusive son cero en las
siete muestras. Hash:
`e3d1a86a5d2f4d350fccb14f85b2b9e31556bc741ba7307d2ab68d9fc4b2dd0c`.
El par 02–03 dura 86 ciclos y empieza con ambos bancos vacíos; el registro
permanece igual. **No demuestra borrar una lista ocupada**, ni identifica
al escritor que inicializa la región cuando se carga el overlay del carrusel.

Al cerrar el lote inicial faltaban muestras de reset con ocupación,
avance, inicializador del overlay y consulta. Los lotes posteriores de este
informe verifican avance y una consulta residual, pero no capturan todos
los escritores del cambio de fase.
Cada copia debe conservar su
fuente y vector de traslación de entrada, cotejar los dieciséis componentes
por forma —incluido Y— y comprobar que no se copió el terminador ni se borró
la cola. El control sintético usa redondeo f32 host y tolerancia absoluta
`0,001`; no acredita aún equivalencia VU0 sobre esas escrituras reales.

## Verificación ejecutada

- **38 pruebas sintéticas propias** del verificador: enlace de paquetes que
  cruza página; identidades, ciclos, PC, delay slot y procedencia incorrectos;
  paquetes modificados y rehechos sus hashes; argumentos e índices distintos;
  punto residual no finito en un rechazo; copias de 0/1/5/8/13 formas;
  Y erróneo, borrado de cola, truncado a nueve, cabecera alterada, no finitos
  y ausencia de terminador. También ejecutadas bajo Python `-O`.
- **Siete capturas y dos pares de consulta auditados**, con 166 archivos de
  entrada reverificados al cierre. Repetición de solo lectura idéntica.
- Verificación final del repositorio: **PASS, cero errores**; `git diff --check`
  sin incidencias. La primera comprobación coincidió con la escritura del
  recibo repetido y lo rechazó aún incompleto; al terminar la publicación,
  se comprobó igualdad byte a byte y se repitió el chequeo satisfactoriamente.
- Recibos locales ignorados por Git:
  `reports/local/f03-04-collision-runtime-partial-v1.json` y
  `reports/local/f03-04-collision-runtime-partial-repeat-v1.json`.
  Ambos: 49.219 bytes, SHA-256
  `138b1d7c2125c612304cbdff8ca61121eff0a3d969dc2ef440fb3f2a6587b67b`.

Reproducción local, sin ejecutar ni modificar el emulador, usando una ruta
de salida nueva porque el auditor rechaza sobrescrituras:

```sh
rtk proxy .venv/bin/python -m pytest -q build/collision-runtime/test_evidence.py
rtk proxy .venv/bin/python build/collision-runtime/audit_runtime.py --output /tmp/cf-t9-audit-new.json
```

Los auxiliares y fuentes privados requieren el workspace de investigación;
no forman parte del job público de CI. No se repitió la batería global de
8.829 pruebas como parte de esta captura ni se preparó un nuevo build 3DS.
CP/CPI y sus capacidades permanecen iguales. CF-T9c–d, F03.04 y los gates
globales siguen abiertos.

## Contacto aceptado y selección del llamador

El usuario aplicó los filtros solicitados en el depurador. La automatización
movió a Heather por la habitación y alcanzó un retorno aceptado junto al
punto de guardado. Se reanudó después hasta una nueva entrada filtrada,
sin restaurar estados. Continúan el mismo PID y sesión.

| Slot | Punto | PC | Ciclo EE |
|---:|---|---|---:|
| 08 | Primer retorno aceptado | `0x001A6E34` | 75.083.248.110 |
| 09 | Mismo retorno, ampliando región observada de salida | `0x001A6E34` | 75.083.248.110 |
| 10 | Comparación terminada; resultado previo conservado | `0x001A6EAC` | 75.083.248.131 |
| 11 | Entrada de la consulta siguiente filtrada | `0x0019F2C0` | 75.095.044.094 |
| 12 | Retorno aceptado de esa consulta | `0x001A6E34` | 75.095.044.262 |
| 13 | Comparación terminada; resultado previo conservado | `0x001A6EAC` | 75.095.044.283 |

Son **13 capturas en 12 puntos de ejecución distintos**: 08/09 tienen CPU,
ciclo y RAM idénticos, y no cuentan como dos contactos. El slot 09 añade la
salida real del llamador `0x01CFB430` a las regiones cotejadas por el observador;
el slot 08 había cubierto otra salida próxima. Los análisis de selección usan 09.

El par **11→12** acredita la misma entrada y retorno, con `v0=1`, indicador
de salida 1 y **168 ciclos EE**. Ambos contactos corresponden al índice 0 de
la celda 0 del mismo `tp21.cld` íntegro. Puntos, parámetros y selección quedan
fijados; se comprueba W=0 y la posición Y dentro de los límites del cilindro.

La comprobación geométrica usa las entradas, no parámetros ajustados al punto
observado. Evalúa pertenencia al segmento y distancia radial, con una cota
espacial de una ULP f32 de la mayor coordenada suministrada (`0,00390625` en
estas muestras). Es una comprobación de consistencia del punto observado,
no una tolerancia nueva de clasificación de contactos ni un solver equivalente a VU0.

| Comprobación | Primer contacto, 09→10 | Par completo, 11→12→13 |
|---|---:|---:|
| Parámetro del segmento | 0,686369871 | 0,596851063 |
| Error máximo de pertenencia al segmento | 0,000713459 | 0,001803918 |
| Error absoluto de radio | 0,001011253 | 0,003574081 |
| Distancia al cuadrado calculada por el juego | 147.220,046875 | 111.322,453125 |
| Mejor distancia anterior | 89.639,828125 | 79.762,453125 |
| Tipo de resultado antes/después | 1 / 1 | 1 / 1 |

En ambas llamadas, el contacto del cilindro está más lejos. Se observan los
21 ciclos desde el retorno hasta la rama `0x001A6EAC`, y permanecen idénticos
los 64 bytes del resultado previo y su mejor distancia. El cálculo f32 host
siguiendo suma X+Z y luego Y difiere del juego en una ULP del resultado en
el primer caso (`0,015625`), y coincide en el segundo. Esa diferencia se
conserva explícita; no se afirma equivalencia numérica exacta del emulador.

Quedan sin observar la sustitución del mejor resultado por un cilindro de
tipo 2, tangencia, tapas, segmentos degenerados, enlaces con actor, normal
y respuesta física. El contacto aceptado no acredita que Heather choque
físicamente con ese cilindro ni que esta consulta sea su solver de movimiento.

### Auditoría ampliada

- Se reproducen primero las siete capturas iniciales y después las seis nuevas.
  Código, recurso, registro, celda/índice, CPU/ciclo, paquetes del observador,
  estados y pares de comparación se verifican de nuevo.
- **315 archivos reverificados**; dos ejecuciones producen el mismo recibo:
  `reports/local/f03-04-collision-runtime-hits-v1.json` y
  `reports/local/f03-04-collision-runtime-hits-repeat-v1.json`, 77.518 bytes,
  SHA-256 `e582e36dac38d78d7389100b9f115204b15d19176f588a08596add04ce8bc15e`.
- **24 pruebas nuevas** de consistencia del contacto y selección; detectaron
  y permitieron corregir el cálculo de ULP para cero antes de aceptar la auditoría.
  Los datos geométricos de los tests son propios, sin recursos del juego.
- Se conserva un INI privado de 13.590 bytes, idéntico al hash de configuración
  registrado en los slots 08–13:
  `42d396e01bb448db7823593afe0c8f1685b10bcb9039a3a78d4314b66d306ca5`.
  Esto no reconstruye los INI antiguos ni implica que el INI contenga los
  breakpoints, que PCSX2 guarda por separado.

### Preparación de la siguiente adquisición

El auxiliar `capture_v2.py` conserva los originales fijados y prepara slots
1–99 con contexto de protocolo derivado de sesión/slot, secuencias locales
1–128 y hasta 128 bloques de 4.096 bytes. Guarda el INI exacto junto al recibo.
`evidence_v2.py` comprueba ese contrato sin acceder al emulador.
**14 pruebas propias** cubren los límites, slots posteriores al 15, archivo
de configuración y rechazo de paquetes procedentes de otro slot.

Las 38 pruebas originales, 24 de contactos y 14 de versión 2 suman **76**,
aprobadas en modo normal y con `-O`. Las capturas 14–17 verificadas abajo
ejercitan la versión 2 real, incluidos slots posteriores al 15.

## Llegada al carrusel y corrección del filtro

El usuario llegó por juego normal al carrusel de caballos. El slot **14**
verifica etapa `0x23`, sala `0xEA`, PC `0x00081FC0`, ciclo
118.162.359.283, mediante 18 regiones y 36 paquetes del observador. El slot
98, usado previamente para localizar el PC de la pausa, es diagnóstico y
no se cuenta como evidencia enlazada. No se restauraron esos estados.

Los dos bancos del mundo tienen contador 1 y apuntan al mismo buffer
`0x01EEB6B0`: fila 4, banco de buffer 0. Sus ocho registros coinciden
íntegramente con `0x01EE3FA0`, elegido por el índice 9 de la tabla anterior.
El resto de los 216 registros está a cero. Esto identifica contenido
almacenado; **no captura su primera escritura** ni acredita que todas las
filas hayan sido inicializadas de la misma forma.

Se detectó un error del filtro preparado por el agente: el parser local de
PCSX2 llama a `parseNumber(...,16,...)`. Por tanto `&255` significa `&0x255`,
no `&0xff`. En el estado 14 produce 1 en vez de `0x23`, ocultando las pausas
de esa etapa. Se conserva el fallo; no se interpreta la ausencia de pausas
como ausencia de llamadas. Se respaldó el archivo de breakpoints y se cambió
la máscara de los cuatro filtros a `0xff`; el usuario aplicó «Cargar desde
ajustes» y se comprobaron las cuatro condiciones en la tabla, sin reiniciar.
SHA del archivo corregido: `03ee9d194dae58fdbbb4be8baf2621f8233af66372583d3a651c6e1815943d13`.

La comprobación inicial del modelo rechazó un byte: `0x01EEE3B0` vale `0xef`
en esta fase, aunque los 17.280 bytes anteriores sí coinciden. No pertenece
a esos 216 registros. La palabra que empieza allí vale `0x00000fef`; el
código del overlay la pone a cero en `0x01EE1B74` y opera sobre sus bits en
`0x01EE1BDC` / `0x01EE21B4`. Se registra como estado por bits, sin presumir
un terminador inmutable. La comparación corregida delimita los registros y
conserva por separado el byte posterior; no altera la captura ni el decoder.

El auditor reproduce primero las 13 capturas anteriores y luego verifica
14, el código, ambas tablas y las 24 fuentes del overlay. **361 entradas**
reverificadas. Dos recibos idénticos de 84.433 bytes:
`reports/local/f03-04-collision-runtime-arrival-v1.json` y
`reports/local/f03-04-collision-runtime-arrival-repeat-v1.json`, SHA-256
`b69ed0af6ef0c8765998f3c12363bd74f10f626f5bb6aef51d1247f4c7f11828`.

## Primera copia y registro observados

Con la máscara corregida, el juego alcanzó el copiador. Se conserva entrada,
salida y retorno después del registro, sin avanzar por restauraciones:

| Slot | PC | Ciclo EE | Contadores de mundo |
|---:|---|---:|---|
| 15 | `0x001A0CD0` | 132.939.222.685 | 1 / 0 |
| 16 | `0x001A0D7C` | 132.939.223.180 | 1 / 0 |
| 17 | `0x01EE1E08` | 132.939.223.201 | 1 / 1 |

Las tres muestras añaden pila y pool a las regiones observadas: 26 regiones,
52 paquetes por muestra, con INI archivado y enlace independiente de CPU/RAM.
La llamada procede de `0x01EE1E00`, selecciona fila 4 de la tabla anterior
`0x01EE9C40`, fuente `0x01EE3FA0` y destino `0x01EEB6B0`.

El vector de entrada en `0x01FFFAC0` (`sp+0x140`) es `(0,0,0,0)`. Los
**128 componentes de ocho formas**, incluidos los 32 valores Y, coinciden
exactamente con fuente más vector; se conservan las cabeceras. El copiador
avanza fuente y cursor de destino 640 bytes y tarda **495 ciclos EE**.
No copia el terminador fuente ni modifica la cola. Esta llamada reescribe
bytes que ya eran iguales: no demuestra su inicialización ni una traslación
no nula. El límite de `0,001` del verificador sigue siendo de investigación;
en esta muestra el error observado es cero.

Después del salto final y 21 ciclos, el registro escribe el puntero en el banco
de mundo 1 y cambia su contador de 0 a 1. Ese puntero ya estaba almacenado;
la única diferencia en los 144 bytes del registro es el contador en
`0x01D045A4`. Se conservan el selector, el otro banco y las formas.
El banco de mundo 1 y el banco de buffer 0 son
selecciones diferentes y no deben confundirse.

**36 pruebas propias nuevas** verifican límites de capacidad, banco/puntero,
escrituras ajenas, metadatos de llamada, argumentos, registros y entradas
modificadas. El fixture propio de copia incluye traslación Y no nula; ese
test no sustituye su observación real. Total: **112 aprobadas**, en modo
normal y con `-O`. El auditor de archivos requiere modo normal por los
loaders históricos; sus verificadores puros usan comprobaciones explícitas.

La auditoría del lote reproduce los recibos previos y reverifica **530
entradas**. Los recibos `reports/local/f03-04-collision-runtime-bank-copy-v1.json`
y `reports/local/f03-04-collision-runtime-bank-copy-repeat-v1.json` son idénticos:
123.870 bytes, SHA-256
`7d9bb5427803c9dc733bc15991a307cac5d2bcace605044157d57e6d3e508053`.
Los scripts quedan fijados por el recibo y no deben editarse para capturas
posteriores; se debe versionar cualquier ampliación.
La comprobación del repositorio termina en **PASS, cero errores** y
`git diff --check` no encuentra incidencias. No se repite la batería global
ni se compila un visor nuevo: los cambios son auxiliares privados y documentación.

Al cerrar ese lote había 17 capturas enlazadas en 16 pausas distintas.
CF-T9c seguía abierta: faltaban otras filas y bancos, traslación no nula, reset/avance con
ocupación, escritor de inicialización, consumo de consulta y cambio de fase.
Se preparó un filtro adicional `ra!=0x1ee1e08` para omitir únicamente la
llamada repetitiva ya medida y permitir que el usuario avance el acertijo.

## Copia condicional tras disparar a un caballo

El usuario informó una pausa al disparar. Se verificó en la tabla el filtro
`ra!=0x1ee1e08`. El observador identificó la salida `0x001A0D7C`, aunque
el desensamblador visible mostraba un PC antiguo; la captura exige el PC real
y no acepta la imagen de la interfaz como sustituto del enlace CPU/RAM.
**La entrada de la primera llamada no se capturó**. Se conservó su salida
18 y se adquirió un par completo en la siguiente llamada, slots 21–22.

Fila 2 de la tabla anterior, actor `0x0044B6F0`, tipo `0x020c`, instancia
`0x03f6`. Fuente `0x01EE5620`, ocho formas. El vector en `sp+0x140`
contiene Y = **48,205078125**, idéntico a `actor+0x24`.
La salida 18 corresponde al buffer 0 (`0x01EEAB70`); el par 21–22 al
buffer 1 (`0x01EEAE40`). Sus 128 componentes coinciden exactamente con el
oráculo escalar binary32 independiente, incluidos 32 valores Y. El par
completo tarda 495 ciclos; cambia 470 bytes del destino, preserva entradas,
cabeceras, cola y registro de bancos hasta el salto final.

| Slots | Operación | Resultado |
|---|---|---|
| 18→19 | Registro tras la primera salida | Banco de mundo 0: contador 0→1, 21 ciclos. |
| 19→20 | Retorno y actualización de estado | Selector de buffer 0→1; bits `0xfef`→`0xfeb`, 15 ciclos. |
| 21→22 | Copia completa siguiente | Mismo actor y vector, buffer 1, 495 ciclos. |
| 22→23 | Registro | Banco de mundo 1: contador 0→1, 21 ciclos. |
| 23→24 | Actualización de estado | Selector de buffer 1→0; bits permanecen `0xfeb`, 15 ciclos. |

Se coteja todo el dominio `0x01EE9F00..0x01EEE3B4` exclusivo al verificar
las actualizaciones: únicamente cambian selector y bit esperado. El registro
del mundo se conserva durante ellas. El cambio del selector del mundo entre
20 y 21 tiene extremos observados, pero todavía no su escritor. Esta muestra
relaciona actor y formas; no captura la consulta del disparo ni calcula daño.

45 pruebas nuevas, 157 acumuladas en ese lote. Auditoría de 920 entradas,
dos recibos idénticos de 217.376 bytes:
`reports/local/f03-04-collision-runtime-conditional-copy-v1.json` y
`reports/local/f03-04-collision-runtime-conditional-copy-repeat-v1.json`, SHA
`718dcc72cc05afedd84899c1b3c553e82b36bc231cab27e2805ad2de635cd790`.

## Etapa intermedia y llegada continua a la fase posterior

Tras cargar el siguiente filtro, el usuario continuó el acertijo. La ruta
alcanzada en 25–28 aún está en sala `0xEA`, pero la palabra de estado del
overlay `0x01EE9F00` vale **5**. La copia viene de `0x01EE26B8`, una ruta
distinta de `0x01EE2178`: fila 0, actor tipo `0x020c`, instancia `0x03f4`,
fuente `0x01EE5BC0`, vector Y = **−125,80799102783203**, ocho formas.
Entrada/salida: ciclos 192.193.237.299→192.193.237.794. El retorno registra
el buffer en el banco de mundo 0; luego, en siete ciclos, cambia únicamente
el selector de buffer 0→1, sin limpiar un bit de fila.

Se omitieron las copias repetitivas de esa etapa mediante filtros respaldados.
La captura **29**, PC `0x01EE28C8`, ciclo **203.022.343.925**, alcanza sala
**`0xEB`**, estado de overlay 1 y contadores de mundo 0/0. Es la misma sesión
PID 50191, sin reinicio ni restauración. Se verifica continuidad entre los
extremos 28/29; **no se capturó la instrucción que cambia la sala ni el reset
que deja ambos contadores a cero**. No se atribuyen esos escritores por
inferencia a partir de sus valores finales.

| Slots entrada/salida/retorno | Fila | Fuente | Formas | Y de entrada | Ciclos de copia |
|---|---:|---|---:|---:|---:|
| 30/31/32 | 0, objeto del escenario | `0x01EE5E90` | 13 | −17,997865676879883 | 800 |
| 33/34/35 | 1, actor `0x0209` | `0x01EE69D0` | 5 | 159,06759643554688 | 312 |
| 36/37/38 | 2, actor `0x0209` | `0x01EE6F70` | 1 | 167,06546020507812 | 68 |

Las tres copias usan buffer 0; cada retorno añade su puntero al banco de
mundo 1, cuyo contador avanza 0→1→2→3. Se comprueba fuente, tabla, selección
de objeto/actor, Y del actor o temporal del objeto, pila, argumentos,
cabeceras y todos los componentes. El registro tarda 21 ciclos por llamada.
La tentativa de adquirir 35 con el retorno de objeto fue rechazada por PC
antes de guardar; el recibo aceptado usa el retorno de actor fijado en 33.

Las filas 1 y 2 conservan, respectivamente, **3 y 7 registros de cola**:
240 y 560 bytes idénticos desde 29, antes y después de sus copias. Sus
cabeceras/X/Z/W coinciden con las fuentes de la fase previa. No se copia
el terminador ni se limpian esas colas. El último escritor y la procedencia
numérica de sus Y siguen sin capturar. Al cerrar el lote 38 aún no se había
observado que una consulta recorriera esos registros; el lote 48–54 documentado
más abajo verifica uno de ellos.

### Discrepancia numérica conservada

El oráculo escalar binary32 estricto **rechaza** la copia de etapa 5 y las
filas posteriores 0 y 2. Hay 16, 12 y 4 componentes Y distintos,
respectivamente, cada uno a **1 ULP** del resultado host; diferencia absoluta
máxima **0,000244140625**. La fila posterior 1 sí coincide bit a bit con ese
oráculo. El comparador previo de investigación acepta los cuatro pares con
su tolerancia ya existente de `0,001`; no se modifica para ocultar el rechazo.
El informe guarda ambos resultados y todos los componentes discrepantes.
Esto no acredita equivalencia general de redondeo PS2/VU ni habilita física.

Los verificadores de selección, colas y diagnóstico numérico añaden 37
pruebas propias: **194 pruebas acumuladas aprobadas**, normales y con `-O`.
El modo optimizado muestra el aviso esperado de pytest; los verificadores
usan comprobaciones explícitas. El auditor de archivos se ejecuta sin `-O`.
Se reverifican **1.699 entradas**, reproduciendo los lotes anteriores.
Recibos idénticos de 416.929 bytes:
`reports/local/f03-04-collision-runtime-transition-v1.json` y
`reports/local/f03-04-collision-runtime-transition-repeat-v1.json`, SHA
`4b404ecb0f91c40fa314f2d2ff86cc18dea862f8db8decfac3df22cab44ffc9f`.

Al cerrar ese lote había **38 capturas enlazadas en 37 pausas distintas**;
la sesión quedó en `0x01EE29A0`, ciclo 203.022.346.303. CF-T9c–d permanecieron
abiertas. Los lotes siguientes amplían la cobertura sin modificar capacidades
de los decoders o del visor.

Se preparó para el siguiente lote, todavía sin confirmar su carga en la tabla, el filtro
de ciclo de vida: copia de fila 11; fin de bucle antes/después del selector
`0x01EE2A8C` / `0x01EE2AA8`; avance con ocupación `0x0019FC00` /
`0x0019FCE0`; entrada de consulta con banco lector ocupado `0x001A49D0`
y lectura de registro dinámico `0x001A4A74`. Se conservan filtros de etapa
y sala y se usa `0xb` para la fila 11. Archivo de 14 breakpoints respaldado,
SHA `40761a640f8236a87742f489db117e6b15b23f512de4fde7435775c0140144b3`.
La automatización opera Ejecutar/Paso, pero la tabla requiere que el usuario
seleccione «Cargar desde ajustes». Preparar el archivo no demuestra que
PCSX2 ya lo haya aplicado.

## Doce listas por banco y avance con ocupación

Los slots 39–47 continúan en etapa `0x23`, sala `0xEB`, estado de overlay 1.
La captura 39 observa una salida de avance, pero no su entrada; no se emplea
para atribuir todas sus escrituras. La captura 40 alcanza el bucle posterior
con selector de buffer 1 y contadores de mundo 0/12.

| Slots | Operación | Evidencia |
|---|---|---|
| 41→42 | Copia de fila 11, tercer actor `0x0209` | Nueve formas, 144 componentes, fuente `0x01EE6430`, destino `0x01EEE0E0`; Y = −190,6426544189453, 556 ciclos. |
| 42→43 | Registro y fin del bucle | Banco de mundo 0: 11→12; ambos bancos contienen 12 listas, 33 ciclos. |
| 43→44 | Alternancia del buffer | Selector 1→0 en nueve ciclos; registro de mundo y formas intactos. |
| 45→46 | Avance `0x0019FC00`→`0x0019FCE0` | Selector del mundo 0→1; contadores 12/12→12/0, 71 ciclos. |
| 45→47 | Retorno a `0x00194B6C` | 73 ciclos, incluida la instrucción de la ranura de retardo. |

Los doce punteros de mundo 0 señalan el buffer 1; los de mundo 1, el buffer 0.
Se verifica su fórmula completa para las doce filas, sin confundir ambos
selectores. El avance conserva el almacenamiento de punteros y formas:
vaciar el contador no borra los registros. El oráculo verifica todas las
escrituras del dominio `0x01D03540..0x01D05FA4` y el contador auxiliar.
Las pruebas con valores propios no nulos distinguen salida y retorno; en la
muestra real la palabra de la ranura de retardo ya era cero.

El modelo de cabecera/X/Z/W concuerda con 216 posiciones: **192 actuales,
20 anteriores y cuatro cero**. Esa concordancia no acredita el orden de todas
las escrituras ni el origen numérico de Y. La copia de fila 11 presenta 36
componentes Y a 1 ULP del oráculo host, máximo `0,000244140625`; se conserva
el rechazo estricto y la tolerancia de investigación previa `0,001`.

La primera auditoría detectó una dirección auxiliar incorrecta: se había
observado `0x01D1A7E0` en vez de `0x01D0A7E0`, por interpretar mal el inmediato
con signo del código MIPS. Se corrigió el análisis antes de publicar el recibo.
Para 45–47 esos 16 bytes proceden de RAM guardada enlazada con la CPU, **sin
lectura directa del observador en esa dirección**. El registro principal sí
está observado. Desde 48 se incluye la dirección auxiliar correcta. El informe
mantiene explícita esta diferencia de cobertura; no se recapturan ni sobrescriben
estados históricos.

24 pruebas nuevas, **218 acumuladas** en ese lote, normales y con `-O`.
Los informes `reports/local/f03-04-collision-runtime-lifecycle-v1.json` y
`reports/local/f03-04-collision-runtime-lifecycle-repeat-v1.json` son idénticos:
545.437 bytes, 2.274 entradas, SHA
`84f500d5023efd3045558e0454e800324680bc09ea7387718f465f939fb212c0`.

## Carga de breakpoints: discrepancia entre tabla y ejecución

Tras cargar un archivo con filas desmarcadas, PCSX2 siguió parándose en
`0x01EE28C8` y `0x001A0CD0`. El código local explica la discrepancia:
`DebuggerSettingsManager` carga filas sin vaciar previamente la colección;
`BreakpointModel` inserta su estado visual y llama a `AddBreakPoint`;
si la dirección ya existe, esta última conserva o activa el breakpoint sin
aplicar el estado desactivado solicitado. Una casilla desmarcada no acredita
que se haya desactivado en la CPU.

Se fijan los tres archivos fuente en el recibo, respectivamente:

- `DebuggerSettingsManager.cpp`: `0e1386cd4d00d2d34e34488ad892590ae722297534d4acffb27ec0a64c11d85d`.
- `BreakpointModel.cpp`: `a01e2e927fbacfb1af4e71e84546ccd90cf31d9b31df0dd373ac3ad0620dc8df`.
- `Breakpoints.cpp`: `160277fe2025ccf348359bb030e9157521e5cc5ffad21c3625d72bfadb7d9dcc`.

La solución aplicada deja las 14 filas marcadas y asigna condición literal
`0` a doce. Solo `0x001A49D0` y `0x001A4A74` conservan condiciones reales,
limitadas a etapa/sala y banco lector ocupado o fila 1/registro 5. El usuario
cargó ese archivo y ejecutó; la captura 48 confirmó la pausa en la consulta.
Snapshot privado `breakpoints-query-false-filter.json`, SHA
`7b28dfa5ef1dc5389a581abcb8defa92e5014a9bae399c8f62ef6b3808c78e46`.
No se modificó ni recompiló PCSX2. La edición de la tabla sigue requiriendo
intervención manual; Ejecutar, pasos y salida de función sí respondieron.

## Consumo real de una forma residual

| Slot | PC | Ciclo EE | Resultado observado |
|---:|---|---:|---|
| 48 | `0x001A49D0` | 203.199.782.172 | Entrada de consulta; selector de mundo 0, contadores 12/12. |
| 49 | `0x001A4A74` | 203.199.786.321 | Banco lector 1, fila 1, índice 5; forma `0x01EEA760`. |
| 50 | `0x001A4A84` | 203.199.786.325 | Flags `0x80` no excluidos por máscara `0x1000`. |
| 51 | `0x001A4A8C` | 203.199.786.340 | Filtro `0x001A7C80`, modo 0, devuelve 0: permite continuar. |
| 52 | `0x0019EEA0` | 203.199.786.367 | Tipo 1: entrega los cuatro vértices a la consulta poligonal. |
| 53 | `0x001A4B18` | 203.199.786.408 | Retorno después de 41 ciclos: `v0=0`, indicador temporal 0. |
| 54 | `0x001A4BE8` | 203.199.786.410 | Rama sin contacto; distancia y resultado exterior conservados. |

La lista base `0x01EEA5D0` pertenece al buffer 0. Su fuente actual contiene
cinco registros y terminador; el índice 5 está en la cola residual. La forma
coincide en cabecera/X/Z/W con la fuente previa `0x01EE3E60`. Esto acredita
su lectura y despacho real, sin atribuir el último escritor de Y.

Se verifican selección de banco opuesto, puntero de lista, stride 80, ausencia
de terminador anterior, argumentos guardados, ambos filtros y cuatro punteros
de vértice. Se comparan los 52 bytes del resultado exterior, incluida su palabra
de puntero en `+0x30`, y la distancia antes/después. Registro de bancos, formas
y extremos de consulta permanecen iguales durante 48–54. Los extremos son
`(0,−250,−0,1)` y `(0,1500,−0,1)`; no se atribuye esta consulta a un disparo.

El rechazo no permite interpretar el punto temporal residual. Tampoco demuestra
contacto aceptado, normal, daño, respuesta física o equivalencia numérica VU.
Se capturó el retorno de la consulta **poligonal individual**; el retorno de
la consulta exterior `0x001A49D0` sigue fuera de este lote.

62 pruebas nuevas: controles de bancos/buffers, identidad y orden, registros,
filtros, terminadores, procedencia, entradas no finitas, truncamiento, resultado
y puntos residuales. **280 pruebas auxiliares aprobadas** en modo normal y con
`-O` (aviso esperado de pytest); los verificadores no dependen de `assert`.
La adquisición, el verificador puro y la auditoría de archivos siguen separados.
Se reproducen los informes previos y se reverifican **2.920 entradas**.
Recibos de 678.464 bytes:
`reports/local/f03-04-collision-runtime-query-v1.json` y
`reports/local/f03-04-collision-runtime-query-repeat-v1.json`, SHA
`10254cb307834e1deaaa05874c2dc3885e8e37b41574277343a35defec136091`.
Se comprobó igualdad byte a byte de ambos recibos. La comprobación final del
repositorio termina en **PASS, cero errores** y `git diff --check` está limpio.
No se repite la batería global ni se añaden estos auxiliares privados a CI.

Reproducción del lote completo con una salida nueva:

```sh
rtk proxy .venv/bin/python -m pytest -q build/collision-runtime
rtk proxy .venv/bin/python -O -m pytest -q build/collision-runtime
rtk proxy .venv/bin/python build/collision-runtime/audit_query.py --output /tmp/cf-t9-query-audit-new.json
```

Estado al cierre del lote 54: **54 capturas en 53 pausas distintas**, mismo PID, sin restaurar
estados ni escribir memoria del juego. Sesión pausada en `0x001A4BE8`, ciclo
203.199.786.410. CF-T9c–d siguen abiertas por inicialización, reset con bancos
ocupados, último escritor de Y residual y equivalencia numérica; quedan además
contacto poligonal aceptado y retorno exterior sin observar. Para la próxima
captura de inicialización se debe identificar explícitamente el nuevo recorrido
de entrada al escenario. Volver al menú y cargar desde el propio juego puede
mantener el proceso actual; no equivale a restaurar un estado de PCSX2, pero
tampoco se presentará como avance continuo del acertijo ya completado. No hay
build nuevo ni cambios de capacidad.

## Preparación de inicialización y reset ocupado

La revisión del ELF localiza una operación más temprana que el inicio de la
fase en `0x01EE1B4C`: `0x001EC9E0` recibe la cabecera del overlay, suma
`base + 0x40 + tamaño_texto + tamaño_datos` y llama a `0x00110668` con valor
cero y tamaño BSS. Para el overlay europeo `0x23`, la cabecera fija
`0x01EE9F00..0x01EEE400` exclusivo: **17.664 bytes**, incluidos los buffers
de colisión. El retorno de esa llamada es `0x001ECA0C`. Esta preparación era
evidencia estática; el lote 55–57 descrito debajo añade la observación real.

El reset `0x0019FB30` procede del llamador `0x0012DCB0`, retorno `0x0012DCB8`.
Su oráculo compara el dominio completo `0x01D020F0..0x01D05FA4` y el auxiliar
`0x01D0A7E0..0x01D0A840`. Exige al menos un contador ocupado, capacidad máxima
16, ambos contadores finales en cero y conservación de punteros y selector
de mundo. La conservación de las formas se verificará por separado en las
capturas, sin atribuir al reset una limpieza que su código no realiza.

El oráculo de BSS compara la región completa más guardas de 16 bytes antes y
después; exige cabecera, destino, valor, tamaño y retorno correctos. Registra
cuántos bytes eran distintos de cero: una entrada ya vacía no demuestra una
limpieza de datos ocupados ni el primer escritor de toda la vida del proceso.
**56 pruebas propias nuevas** pasan en normal y con `-O`, incluidas escrituras
faltantes/ajenas, reset vacío, capacidad inválida, cabeceras/argumentos erróneos,
truncamiento y conservación de guardas. No habilitan física ni un decoder nuevo.

Se respaldaron y prepararon 17 breakpoints, seis con condición real; los demás
usan `0` para evitar el fallo de carga previamente documentado. Snapshot
`breakpoints-initialization-filter.json`, SHA
`833fb9b1f52a74a4fe938b7352fb84ffe8d12a9219b3e782dc60d60a0090b97c`.
El usuario confirmó su carga. La tabla muestra las tres nuevas entradas y
los filtros del overlay; el emulador fue reanudado conservando PID 50191.
Se solicitó volver al menú desde el propio juego para provocar la siguiente
llamada, sin reiniciar PCSX2 ni cargar estados. En ese momento todavía no
había un nuevo par capturado y el total aceptado era de 54 capturas.

Plan privado `reports/local/f03-04-collision-initialization-plan-v1.json`,
2.099 bytes, SHA
`b3c95a2549670526f59f764238ed40e88894e60053bd4193b9db8ab66bf4c7af`.
Fija fuentes, ventanas de código y auxiliares; su estado es
`prepared_not_observed` y no sustituye los recibos de adquisición.

## CF-T9c: reinicialización real, capturas 55–57

El usuario volvió al menú mediante la muerte de Heather y eligió «Continue»
desde el propio juego. Se conserva PID 50191, sin reiniciar PCSX2, restaurar
estados ni escribir memoria mediante herramientas. Este es un segmento de
carga de partida tras la muerte; no se presenta como avance ininterrumpido
del acertijo anterior. Etapa `0x23`, sala `0xEB`, selector de mundo 1 y
contadores 12/0 en las tres capturas.

| Slot | PC | Ciclo EE | Evidencia |
|---:|---|---:|---|
| 55 | `0x001EC9E0` | 256.453.082.185 | Entrada del inicializador; cabecera `0x01EE0E80`, formas aún ocupadas. |
| 56 | `0x00110668` | 256.453.082.199 | Entrada de `memset`: destino `0x01EE9F00`, valor 0, tamaño `0x4500`, retorno `0x001ECA0C`. |
| 57 | `0x001ECA0C` | 256.453.087.196 | Retorno: los 17.664 bytes están en cero; transcurrieron 4.997 ciclos. |

La región BSS y sus guardas de 16 bytes permanecen idénticas entre 55 y 56.
Entre 56 y 57 cambian a cero **12.442 bytes previamente no nulos**, sin tocar
las guardas. El subdominio de formas pasa de 12.380 bytes no nulos a cero.
El registro de listas y el dominio auxiliar siguen idénticos: la limpieza
del overlay **no vacía los contadores 12/0**. Se verifican cabecera completa,
argumentos, retorno, pila, registros conservados y código del ELF/overlay.
La observación acredita esta reinicialización, sin identificar el primer
escritor de toda la vida del proceso ni el último escritor de Y residual.

Los INI de 55–57 son idénticos. Respecto de 54 solo cambia
`Debugger/UserInterface.WindowGeometry`, tras cerrar y abrir el depurador;
la auditoría compara todas las claves y rechaza otra diferencia.

| Slot | SHA-256 del estado privado |
|---:|---|
| 55 | `2aded1672752d2af924cfdda83fc0aa39250b6d77d37a4dea37c24a17710e30d` |
| 56 | `71d21d52c4d04376eeb3cf8510269df9c524fcde1808e3ca0e8ae70da16009a5` |
| 57 | `81e8b93a80c04d0889d92a04a99eb4847f063c904ff506f6db53af594c021f63` |

`audit_initialization.py` reproduce los lotes anteriores, enlaza estados con
observaciones antes/después y reverifica **3.152 entradas**. Recibos privados
`reports/local/f03-04-collision-runtime-initialization-v1.json` y
`reports/local/f03-04-collision-runtime-initialization-repeat-v1.json`,
730.534 bytes, idénticos byte a byte, SHA
`71e695c591102ef68b619b52036c782a22e5dc8254c7fae8a057d49c7e695fd3`.

El reset `0x0019FB30` no se alcanzó durante la muerte, el menú ni «Continue».
La ruta directa localizada en el ELF es `0x0012CB74` → `0x0012DC90` →
`0x0012DCB0` → reset. El bucle principal vuelve de `0x0012CD38` a
`0x0012CB80`, después de esa llamada de arranque. Esto explica la ruta
identificada; no demuestra que todo llamador indirecto posible sea inexistente.
La sesión real se cerró limpiamente, con originales intactos. Sus 57 capturas
en 56 pausas distintas quedan preservadas.

## CF-T9c: diagnóstico separado del reset ocupado

El usuario eligió explícitamente «Diagnóstico separado». Se fijaron estos
criterios para esta prueba:

- WHEN se prepare el diagnóstico THEN la copia SHALL conservar todos los
  miembros descomprimidos salvo el campo PC del estado interno.
- WHEN se restaure la copia THEN la adquisición SHALL identificar restauración,
  PC forzado, nuevo perfil y sesión; SHALL rechazar su clasificación como captura
  de juego normal.
- WHEN el reset alcance `0x0019FBF0` THEN el diagnóstico SHALL detenerse antes
  de ejecutar `jr ra` y comparar contadores, punteros, formas y RAM restante.
- IF la copia o la adquisición altera datos fuera del contrato THEN la auditoría
  SHALL rechazar el resultado sin modificar los originales.

Perfil independiente `f03-04-collision-reset-diagnostic-v1`, PID 11054,
tarjetas copiadas y socket propio `cf09d/pcsx2.sock`. Se reutiliza el ejecutable
instrumentado fijado; no se recompila PCSX2. La copia del estado 55 cambia solo
PC de `0x001EC9E0` a `0x0019FB30`; RA permanece `0x001ECA68`. SHA de la copia:
`620e5b363e0a48724ac790befcb95a43334ce1258a42bae212644c0a8987f66a`.
Se comparan todos los miembros, incluidos RAM y estructuras internas completas.
La envoltura ZIP se recomprime a Deflate; su identidad de bytes comprimidos
no se exige. El primer intento preservaba la etiqueta Zstandard del productor
y fue rechazado por la versión ZIP antes de crear el perfil o lanzar la VM;
se corrigió la recomprensión explícita sin relajar el lector.

Se inicia pausado mediante `-statefile`, con una restauración declarada y solo
dos breakpoints de ejecución, entrada y salida, sin condiciones. La captura
de entrada comprueba RAM EE completa, los 32 GPR low32 y ciclo idénticos al
estado 55. Volver a guardar tras la restauración nativa cambia metadatos
internos/GS/SPU2 y omite la miniatura; no se exige identidad de esa nueva
serialización con el archivo de entrada. La copia entregada a PCSX2 sí cumple
la comparación completa de miembros y cambio exclusivo del PC.

| Captura de diagnóstico | PC | Ciclo EE | Contadores |
|---:|---|---:|---|
| 1 | `0x0019FB30` | 256.453.082.185 | 12/0 |
| 2 | `0x0019FBF0` | 256.453.082.271 | 0/0 |

El reset ejecutado tarda **86 ciclos EE**. El oráculo comprueba su conjunto
exacto de escrituras sobre ambos dominios, y una comparación adicional de
los 32 MiB de RAM descarta cambios fuera de ellos. Solo cuatro bytes cambian
de valor en esta muestra: otros destinos ya contenían su valor final. No se
infieren escrituras individuales a partir de bytes que ya eran cero.
Selector de mundo 1, punteros, BSS del overlay y formas permanecen intactos,
incluidos sus 12.380 bytes no nulos. Los registros conservados y RA tampoco
cambian. Esto verifica el efecto de la función con ocupación; **no demuestra
una invocación por juego normal** con esos bancos ocupados.

La primera comprobación de salida rechazó PC incorrecto antes de guardar:
la VM seguía en la entrada con el mismo ciclo. Tras continuar hasta el
breakpoint de salida, se obtuvo la captura 2 y se cerró el diagnóstico sin
ejecutar el retorno al llamador. Cierre 0, socket retirado y baselines intactos;
`closure.json` privado, 76 bytes, SHA
`67bc32d30070ff8afea17e3ed1dfc4f0c9dd4408042258727b79a7341d08787d`.

| Captura de diagnóstico | SHA-256 del estado privado |
|---:|---|
| 1 | `73acb60a43c7db19b15cd36dbcf89897cb52d9e62fa58973776ca3e9101c541b` |
| 2 | `b613e7c7f959472e8314737d67c2f19fc1cfe059a49aec8238fee606165a8294` |

Separación de responsabilidades: `diagnostic_state.py` prepara y compara la
copia; `launch_diagnostic.py` administra perfil y proceso;
`capture_diagnostic.py` adquiere observaciones y estados nuevos;
`diagnostic_binding.py` exige procedencia de diagnóstico; el oráculo puro de
reset compara dominios y `audit_reset_diagnostic.py` enlaza archivos/fuentes.
Los validadores normales rechazan las capturas restauradas incluso cambiando
su etiqueta de esquema; el validador de diagnóstico rechaza procedencia normal.

26 pruebas nuevas de copia, cambios ajenos, entrada incorrecta y procedencia,
sumadas a las 56 de inicialización/reset: **362 auxiliares aprobadas** en modo
normal y con `-O` (aviso esperado de pytest). Los validadores usan comprobaciones
explícitas. Dos auditorías idénticas reverifican **3.288 entradas**:
`reports/local/f03-04-collision-reset-diagnostic-v1.json` y
`reports/local/f03-04-collision-reset-diagnostic-repeat-v1.json`, 766.005 bytes,
SHA `0a37e349fc50643009c25a1bac137447b01b46a4247679ca2b8c5bd52a5c9a01`.
Las dos capturas de diagnóstico se registran aparte de las 57 reales.

Reproducción de las auditorías conservadas, sin abrir ni alterar PCSX2:

```sh
rtk proxy .venv/bin/python -m pytest -q build/collision-runtime
rtk proxy .venv/bin/python -O -m pytest -q build/collision-runtime
rtk proxy .venv/bin/python build/collision-runtime/audit_initialization.py --output /tmp/cf-t9-initialization-new.json
rtk proxy .venv/bin/python build/collision-runtime/audit_reset_diagnostic.py --output /tmp/cf-t9-reset-diagnostic-new.json
```

Al cerrar este lote, CF-T9c seguía abierta por el último escritor de Y residual; la invocación natural
del reset ocupado continúa sin observar. El siguiente paso es localizar ese
escritor desde la limpieza ya demostrada, declarando cualquier nuevo segmento,
sesión o restauración. CF-T9d mantiene pendientes equivalencia numérica,
contacto poligonal aceptado y retorno de la consulta exterior. Este lote no
habilita respuesta física, cambia perfiles CP/CPI ni genera un build de 3DS.

La [continuación de CF-T9c sobre escritores Y](f03-04-collision-y-writer.md)
añade 23 capturas de una repetición desde estado 25 intacto: cuatro instrucciones
SQC2 observadas y dos colas de fase 5 reproducidas. Las cuatro colas finales
coinciden con los originales 29/54. Otra repetición desde estado 24 intacto
añade 13 capturas de la llamada anterior de fila 1/buffer 0: traslación Y=−25,
cuatro stores, copia completa, registro y actualización del selector. Su cola
coincide con los originales 25/29/54; ya no queda como candidato sin llamada.
467 auxiliares aprobadas y 5.079 entradas auditadas. Estas capturas restauradas
no se añaden al contador de evidencia continua original. La unicidad del último
escritor entre extremos y los escritores del cambio de sala siguen pendientes.
