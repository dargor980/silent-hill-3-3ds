# HG-T3 — Contrato nativo de giros de Heather, v1

2026-10-30. Contrato fijado en HG-T3, cuyo estado fue
**`specified_not_integrated`**. Perfil `heather-original-pal-525-turns-v1`,
ID **2**. Define la ampliación de
[HL](heather-locomotion-v1.md) y de la coordinación
[HM](heather-movement-native-v1.md).
[Secuencia HG](../docs/specs/sh3-3ds/heather-turns.md).

Actualización de implementación: [HG-T4.1](../docs/execution/f06-02-heather-turns-core.md)
completa perfil/reloj/poses/publicación; [HG-T4.2](../docs/execution/f06-02-heather-turns-sri2.md)
completa SRI2 ID 2 y recursos A/B; [HG-T4.3](../docs/execution/f06-02-heather-turns-integration.md)
integra cinco acciones, contactos y controles de escena, con ciclo de vida
verificado en host y dobles SDK. [HG-T4.4](../docs/execution/f06-02-heather-turns-resources.md)
cierra el presupuesto, inventarios ABI/pila y compilación ARM `0188790baedd`.
El contrato y el JSON HG-T3 conservan su estado histórico. HG-T4 queda completa
en su alcance local; la pila incluye una reserva externa explícita y el pico
rastreado corresponde a buffers host. [HG-T5](../docs/execution/f06-02-heather-turns-delivery.md)
prepara A/B del mismo build y el protocolo de consola. Copia a SD verificada
con respaldo y expulsión segura; [prueba funcional física aceptada según el usuario](../docs/compatibility/heather-turns-results.md),
con límites de lecturas explícitos y sin nuevas medidas de rendimiento/memoria.
Las secciones en futuro fijan obligaciones de toda HG-T4.

Como usuario del perfil de inspección, quiero que Heather use los clips
originales al girar sobre el sitio, conserve su pose al pausar y cambie entre
espera y giro sin saltar a cuadros de otro clip. El perfil conserva caminar,
correr, contactos y escena compartida. HM-T5 adicional permanece aplazada.

## Autoridad y alcance

[HG-T2](../docs/execution/f06-02-heather-turns-cycles.md) acredita dos ciclos
completos de 19 poses y cuatro arcos espera↔giro, 70 actualizaciones/2520
matrices; error máximo `0.0004684641970698067`, límite `0.001`.
Informe local `reports/local/heather-turns-cycles-v1.json`, SHA-256
`478d2c60ec9bcdc8d1f7b572847e72f9cd410a609fc61f108d4ed5fcd494567e`.
Este contrato utiliza esa evidencia sin volver a capturar el juego.

Son observados: descriptores PAL, relojes, wrap, dos canales, caché local
interpolada, pesos y terminación de esos cuatro arcos. Son **política nativa**:
prioridad de controles, cola de un único objetivo, puentes entre acciones,
rechazo de interrupciones y ciclo de vida. No se atribuyen a PS2. No hay
evidencia nueva de giro directo derecha↔izquierda, giro↔marcha, interrupciones
completas, vuelta mundial de 360°, física general ni cruce exacto de ±pi.
La navegación de pared 60 continúa pospuesta.

## Requisitos EARS

- **HGT01:** CUANDO prepara el perfil 2 DEBERÁ conservar los tres clips y
  sus índices del perfil 1 y añadir exactamente los clips 107/108, con los
  mismos recursos, topología, máscaras y materiales verificados.
- **HGT02:** CUANDO actualiza un giro estable DEBERÁ evaluar la fase de
  entrada, envolver ambos índices dentro del clip y devolver su siguiente
  contador Q12, usando exactamente dos ticks y velocidad PAL ya convertida.
- **HGT03:** CUANDO inicia espera↔giro DEBERÁ congelar la última pose local
  interpolada de ambos canales antes de cambiar el reloj; DEBERÁ mantener
  esa caché hasta la salida de la mezcla, con la secuencia propia del arco.
- **HGT04:** CUANDO recibe una selección DEBERÁ aplicar la matriz de arcos
  y precedencia de errores fijadas; mismo destino o solicitud vacía DEBERÁ
  continuar sin reiniciar. Una interrupción DEBERÁ rechazarse en el dominio.
- **HGT05:** CUANDO interpreta controles DEBERÁ priorizar avance sobre giro
  para elegir animación y aplicar el giro mundial actual independientemente
  de la animación retenida. Teclas opuestas DEBERÁN cancelarse.
- **HGT06:** CUANDO cambia el objetivo durante una mezcla DEBERÁ conservar
  solo la última acción completa, incluida su dirección; DEBERÁ finalizar
  el arco vigente y recorrer únicamente puentes permitidos en pasos futuros.
- **HGT07:** CUANDO publica un paso DEBERÁ publicar juntos movimiento,
  contacto, reloj, ambas poses de canal, jerarquía, instancia y ordinal.
  SI falla DEBERÁ conservar la última instantánea completa.
- **HGT08:** CUANDO carga SRI2 DEBERÁ aceptar únicamente las combinaciones
  exactas de perfil/tabla/muestras y validar todos los campos antes de
  publicar. El perfil 1 y el límite de aceptación de SRI1 DEBERÁN conservarse.
- **HGT09:** CUANDO evalúa poses DEBERÁ conservar NLERP corto, LERP local,
  normalización, límites numéricos, composición y tolerancias de HL.
  La transformación mundial DEBERÁ aplicarse una sola vez después de la pose.
- **HGT10:** CUANDO procesa pausa, R, reinicio, HOME/tapa o error DEBERÁ
  conservar las garantías de HM, incluyendo caché de giro y ausencia de
  recuperación del tiempo suspendido. Mantener R DEBERÁ producir un solo paso.
- **HGT11:** CUANDO ejecuta un paso DEBERÁ usar memoria acotada sin asignación
  dinámica. La ampliación de almacenamiento DEBERÁ distinguir capacidad
  física, cantidades del perfil y límites de cada formato.
- **HGT12:** CUANDO integra HG-T4 DEBERÁ ejecutar los literales sintéticos en
  C++ y cotejar las poses privadas con el oráculo independiente; resultados
  analíticos de HG-T3 NO DEBERÁN presentarse como atomicidad, ARM o consola
  ya verificados. Código nuevo DEBERÁ superar cobertura individual ≥80/80.

## Perfil, muestras y representación

ID 2, MDL522, ANM525, modelo `0x100`, máscara `0x3021`, 36 huesos activos del
esqueleto de 73. Se conservan hashes fuente de HL/HG-T2 y sus dos máscaras:
canal 2 con 15 huesos, canal 1 con 21; unión ordenada, padres completos,
sin reparentar. Las dos máscaras no representan dos relojes independientes.

| Acción / ID | Descriptor PAL `<HHhHHBB>` | Índice empaquetado | Incremento / período Q12 |
|---|---|---:|---|
| espera / 101 | `101,10,307,0,9,1,0` | 0 | 614 / 40960 |
| caminar / 109 | `109,24,1996,80,103,1,0` | 10 | 3992 / 98304 |
| correr / 113 | `113,24,2227,176,199,1,0` | 34 | 4454 / 98304 |
| giro derecho / 107 | `107,10,1152,60,69,1,0` | 58 | 2304 / 40960 |
| giro izquierdo / 108 | `108,10,1152,70,79,1,0` | 68 | 2304 / 40960 |

Orden normativo: **101,109,113,107,108**; 78 muestras sin huecos ni solapes.
Las primeras 58 y sus descriptores permanecen idénticos. No repetir la
conversión PAL ni deducir velocidad del refresco de pantalla. Ticks=2,
25 actualizaciones de inspección por segundo; incremento=velocidad×2.

El futuro `LocomotionProfile` tendrá capacidad de cinco descriptores y un
conteo activo explícito: tres para ID 1, cinco para ID 2. Los campos activos
deberán coincidir exactamente con su perfil y los registros inactivos serán
cero. No se serializa el `struct`, ni se conserva su ABI como formato.
Fábricas/validadores, inicialización y reinicio recibirán el perfil; no
podrán introducir ID 1 implícito en un estado de ID 2.

## Reloj, pose y matriz de arcos

Se conserva el estado HL: identidad de perfil, `source_id`, `target_id`, modo
1/3/5, `counter`, `blend`, `saved_local_valid`, última pose local y caché.
Modo 4 sigue siendo un preludio interno atómico, nunca un estado publicable.
Inicializar/reiniciar produce 101/101, modo 1, contador/mezcla cero, caché
inválida y pose local del frame 0, **sin consumir ticks**.

Modo 1 exige IDs iguales, beta cero, contador en `[0,N*4096)` y caché
inválida. Para `j,r=divmod(counter,4096)`, evaluar muestras `K+j` y
`K+(j+1)%N` con fracción `r/4096`, después avanzar módulo `N*4096`.
`pose_phase=counter_entrada`; `counter_salida` es la próxima fase a consumir.
No confundir contador posterior con pose visible. Usar intermedios enteros
de al menos 64 bits; rechazar entradas fuera de rango antes de sumar.

Ejemplo para ambos giros: fase `39168` interpola el último cuadro con el
primero usando fracción `2304`, devuelve `512`; la siguiente evaluación usa
fase `512`, devuelve `2816`. Diecinueve poses desde fase cero cubren 41472
unidades Q12 entre primera y última, más que el período 40960.

| Origen \ destino | 101 | 109 | 113 | 107 | 108 |
|---|---|---|---|---|---|
| 101 | continuar | caché HL | rechazar | caché HG | caché HG |
| 109 | caché HL | continuar | modo 5 HL | rechazar | rechazar |
| 113 | caché HL | modo 5 HL | continuar | rechazar | rechazar |
| 107 | caché HG | rechazar | rechazar | continuar | rechazar |
| 108 | caché HG | rechazar | rechazar | rechazar | continuar |

Nueve arcos, cinco selecciones del mismo clip y once rechazos directos.
La matriz se aplica desde modo 1; no introduce puentes dentro del dominio.
Perfil 1 conserva sus cinco arcos y rechaza 107/108 como `unknown_clip`.

### Cuatro arcos de caché nuevos

| Arco | Primer beta | Incremento posterior | Betas publicables | Salida siguiente |
|---|---:|---:|---|---|
| 101→107 / 101→108 | 768 | 768 | 768,1536,2304,3072,3840 | modo 1, fase 0, contador 2304 |
| 107→101 / 108→101 | 1024 | 410 | 1024,1434,1844,2254,2664,3074,3484,3894 | modo 1, fase 0, contador 614 |

Seleccionar desde estable copia `last_local` completa a `saved_local` antes
de reemplazar IDs/contador. La primera actualización usa el primer beta;
las restantes suman el incremento posterior. Durante la mezcla el contador
es cero y `last_local=mix(saved_local,destino[0],beta/4096)`. La caché nunca
se alimenta con la nueva pose mezclada. La interpolación temporal previa del
origen **ya está incorporada** en ella; no reconstruirla con el frame entero,
el contador posterior o una matriz modelo.

Al alcanzar/superar 4096 en la siguiente suma, evaluar exclusivamente el
frame 0 del destino, avanzar una vez, publicar IDs iguales, beta cero e
invalidar caché. No publicar beta 4096/4608/4304. Entrada tarda seis pasos
incluida salida; retorno a espera tarda nueve. Modo 3 válido exige arco
acreditado, contador cero, caché válida y beta perteneciente a su secuencia.

Las tasas se seleccionan por **par origen/destino**, nunca solo por destino:
109/113→101 siguen usando primer beta 1280 y sumas 360. 101→109 conserva
768/768. 109↔113 conserva modo 5, pesos 384…3840, interpolación primero
entre clips y después temporal, y los **dos avances** de su salida recursiva.
No aplicar ese doble avance a la salida de modo 3.

Mismo destino o solicitud vacía continúa cualquier modo; no recopia caché
ni reinicia contador/beta. Otra solicitud conocida durante modo 3/5 devuelve
`transition_busy`, aunque su arco fuera imposible desde estable. ID desconocida
se rechaza antes como `unknown_clip`. Sin cola ni interrupciones en el dominio.

### Aritmética y dos canales

Se heredan las validaciones finitas, norma mínima, topología y cotas de HL;
`float` de 32 bits sin fast-math/contracción. Para cada mezcla, cambiar el
signo del segundo cuaternión solo si el producto escalar es negativo,
interpolar linealmente y normalizar; empatar a cero no cambia el signo.
Traslaciones por LERP. Primero resolver ambos canales locales; luego
componer `parent * local` sobre la jerarquía completa, incluso si el padre
pertenece al otro canal. No transformar la raíz local en delta mundial.

Tolerancias sin ampliar: extremos reconstruidos `1e-7`; TR sintéticos C++
`1e-6`; ejemplo jerárquico sintético `4e-6`; matrices contra original `0.001`.
Los literales Decimal de HG-T3 se cotejan como double a `1e-12`, no como f32.
No se promete igualdad de trigonometría host/ARM ni fidelidad PS2 general.

## Intención y coordinación nativas

Acción tipada propuesta `InspectionAction`: `idle`, `walk`, `run`,
`turn_right`, `turn_left`. Se traduce internamente a clip 101/109/113/107/108
y movimiento `idle/walk/run/idle/idle`. El comando de aplicación separa esta
acción de `InspectionTurn`, que sigue describiendo yaw mundial. No aceptar
un par público arbitrario de clip/movimiento contradictorio.

La ruta de compatibilidad del actor para perfil 1 conserva el contrato HM
actual: movimiento idle + giro sigue usando 101. La futura escena HG usará
explícitamente perfil 2 y la nueva selección por acción. El planificador de
movimiento, resolvedor de contactos, render y materiales no cambian de función.

Prioridad para `[arriba,abajo,izquierda,derecha,B]`:

1. `arriba && !abajo`: caminar, o correr si B, con independencia del giro.
2. Sin avance: derecha exclusiva →107; izquierda exclusiva →108.
3. Sin dirección exclusiva: espera 101. B solo no produce carrera;
   abajo no crea retroceso. Arriba+abajo anula avance; izquierda+derecha anula yaw.

Yaw usa siempre los botones actuales: derecha `+0.088`, izquierda `-0.088`
radianes por paso de dos ticks. Conserva orden, normalización y traslaciones
28/70 de HM. No se deduce esa velocidad de los diez cuadros de giro.
Un giro en el sitio tiene movimiento idle y traslación solicitada cero,
pero sigue consultando el puerto de contactos y puede animarse estando bloqueado.

El controlador conserva **una sola última acción deseada**, no solo la clase
de movimiento, pues ambas direcciones de giro son idle. No usa FIFO. La
actualiza aun si el intervalo no alcanza un paso; soltar los botones es un
nuevo objetivo 101 y sustituye cualquier solicitud anterior.

Por cada paso:

1. Si hay mezcla, continuar su destino actual.
2. Si está estable y ya coincide con el objetivo, continuar.
3. Si existe arco directo, solicitarlo; en otro caso, elegir el primer
   salto de la tabla de rutas de los vectores, siempre por 101. Excepción:
   101→113 se encadena 101→109→113, como HM.
4. Ejecutar un solo paso completo. Tras la publicación, pendiente será el
   objetivo deseado si difiere del destino publicado; en otro caso, vacío.
   Un nuevo salto solo puede empezar en el **paso de simulación siguiente**.

Ejemplos: 107→108 recorre 107→101→108; 107→113 recorre
107→101→109→113; 109→108 recorre 109→101→108. Cada mezcla debe terminar
antes del siguiente arco. Si cambia la entrada, recalcular desde el destino
vigente; no ejecutar después un objetivo ya cancelado.

La traslación durante una mezcla corresponde a su destino vigente; al iniciar
un arco corresponde al nuevo destino. Una parada empieza a pedir traslación
cero cuando comienza su arco a 101. El giro mundial permanece inmediato:
al invertir derecha→izquierda durante la entrada a 107, el yaw puede ser
izquierdo mientras termina la mezcla derecha. Esta limitación explícita
mantiene los controles HM y evita inventar interrupciones originales.

## Tiempo, ciclo de vida y publicación

Se conserva la implementación HM corregida: paso fijo 40000 µs; máximo tres
por llamada. Intervalos mayores de 120000 y hasta 1000000 µs se recortan a
120000, eliminando la deuda anterior; mayores de 1000000 se descartan con
deuda/pendiente. Esta precisión prevalece aquí sobre el texto histórico de
HMN13 que indicaba descarte completo ya sobre 120 ms; no propone cambiar el
comportamiento del build verificado.

Prioridad: salida → guarda de liberación → pausa → reinicio → paso R →
reproducción. A/L/R/START dependen de flancos. R pausado publica como máximo
un paso; sostenerlo no repite. Pausa, R y reinicio consumen el intervalo.
Pausa o HOME/tapa conservan reloj, pose y caché completas; borran deuda y
pendiente. Retornar conserva RUNNING/PAUSED anterior y exige soltar todo;
la muestra neutra también descarta su tiempo. Reiniciar cancela caché y
objetivo, prepara 101/fase cero sin ticks y conserva el estado de pausa.

No cambia la jerarquía de errores del núcleo:
`invalid_profile` → `invalid_state` → `invalid_ticks` → `unknown_clip` →
`transition_busy` → `unsupported_transition` → `sample_unavailable` →
`invalid_pose`. Un perfil mal formado cuenta como `invalid_profile`, no
solo una ID desconocida. Los primeros seis no leen muestras. La falta de
una muestra requerida prevalece sobre pose/caché inválida ya detectada;
jamás se interpola una pose rechazada. No aceptar huecos de beta, IDs ajenas,
contador fuera del período, caché desincronizada ni modo 4 público.

El actor conservará el orden de HM: comprobar inicialización, proponer y
validar movimiento, prevalidar selección, resolver/validar contacto,
reconstruir instancia, evaluar ambos canales en almacenamiento provisional
y publicar toda la instantánea.
El puerto de contactos sigue sin efectos irreversibles. Callbacks ven solo
la instantánea anterior; una reentrada se rechaza y no modifica el paso exterior.
Un fallo conserva estado y salidas byte a byte, incluida caché, contador y
ordinal; reintentar con datos reparados equivale a una ejecución sin fallo.
La publicación es transaccional en un hilo, no sincronización entre hilos.

Un error pausa el controlador, limpia deuda/pendiente y exige liberación y
nueva acción explícita. Si falló el segundo/tercer paso de un lote, los pasos
completos anteriores permanecen publicados. Carga/reinicio fallidos conservan
su objeto anterior; cierre fallido del archivo también impide publicar.

## Transporte SRI2 y compatibilidad

Mismo magic `S3RIv2\0\0`, little endian, cabecera `<8s22I>` de 96 bytes,
campos/payload de HL. **Nueva identidad de perfil, no reinterpretación de ID 1.**

| Perfil | Cantidad de clips | Muestras F | Uso |
|---:|---:|---:|---|
| 1 | 3 | 58 | legado HL, exactamente sus descriptores/máscaras |
| 2 | 5 | 78 | este contrato, tabla completa anterior |

Rechazar todos los cruces entre esos valores, perfiles desconocidos, más
muestras aun si caben en memoria, descriptores/orden/reservados alterados.
El lector antiguo **rechaza** ID 2; compatibilidad significa conservar sus
archivos en el lector nuevo, no que un binario antiguo cargue el perfil nuevo.
No truncar a 58, etiquetar como ID 1 ni aplicar fallback silencioso.

Perfil 2: B=36,F=78,H=49,V=6943,I=16566,M=13; offset 32=5 clips,
36=2 ticks, 40=25 Hz, 44=2 perfil, 48/52=522/525. Reservados 64–95 cero.
Cada descriptor de 20 bytes `<HHhHHBBII>` conserva los doce bytes PAL,
primer índice empaquetado y reservado cero. Los cinco van antes de las TR.

```text
payload = 16 + 8*B + 20*C + 28*B*F + 68*H + 28*V + 2*I + 28*M
        = 310260 bytes
archivo = 96 + payload = 310356 bytes
delta respecto al perfil 1 = 40 + 20*36*28 = 20200 bytes
```

CRC32 IEEE sobre todo el payload; tamaños exactos, sin bytes finales, mismas
validaciones de textura/material, reserved, topología, finitud y procedencia
A/B de HL. No hay rutas/timestamps ni punteros EE en el archivo. El CRC no
autentica los recursos. En HG-T4 se cotejarán los extremos crudos seleccionados
y las reconstrucciones de los 78 cuadros contra ambas fuentes privadas.

Centro derivado de la espera inicial; radio conservador calculado sobre las
78 muestras y escala única para todos los clips. Esto puede cambiar el
encuadre del visor aislado. La habitación conserva la transformación compartida
HM en unidades originales: **no** aplicar el reencuadre del visor aislado a
la colocación, suelo, contactos o render de hp34. No hay geometría, texturas
ni orden de dibujo nuevos por esta ampliación de animación.

## Memoria e interfaces que deberá ampliar HG-T4

La capacidad actual de 64 muestras no alcanza para 78. Se fija capacidad
decodificada **80**, conservando 73 huesos máximos. Debe separarse:

- capacidad física de `InspectionRig`: 80;
- máximo aceptado/emitido por **SRI1: 64**, sin ampliación implícita;
- cantidades exactas SRI2: 58 para ID 1; 78 para ID 2.

No basta con sustituir una constante compartida: productor, validador SRI1,
lector SRI2 y lectores de muestras tienen responsabilidades distintas.
SRI1 conserva hashes y rechazos; SRI2 no usa `evaluate_rig` con wrap global
sobre F. Las selecciones siempre envuelven dentro de su descriptor.

TR ocupa 28 bytes. Capacidad de muestras: `73*80*28=163520`, aumento
`73*(80-64)*28=32704` bytes por rig decodificado. Datos seleccionados:
`36*78*28=78624`, frente a 58464; delta 20160. El delta de archivo es 20200.
Son **cálculos de almacenamiento**, no mediciones de pico del proceso.
HG-T4 inventariará copias persistentes/provisionales, buffers de carga,
alineamiento, pila, renderer y texturas antes de afirmar el pico host/ARM.

Reloj+estado+scratch conserva presupuesto ≤32 KiB; cada coordinador actor/
controlador completo conserva su presupuesto ≤32 KiB, excluidos recursos y
renderer como HM. Sin asignaciones por paso ni matrices grandes en la pila.
Ampliar cinco descriptores no requiere duplicar cachés por clip: solo última
pose y un origen congelado. Cargar/validar se mantiene fuera del bucle.

## Vectores y aceptación por etapas

[JSON sintético](../tests/fixtures/synthetic/heather-turns-native-v1.json),
schema `heather-turns-native-v1`. Contiene metadatos numéricos y TR ficticias;
no contiene poses, matrices ni bytes extraídos del juego. El JSON es el
artefacto normativo compartido; no generarlo desde la futura implementación
para producir sus resultados esperados.

| Grupo | Cobertura literal |
|---|---|
| `clips`, `channels` | cinco descriptores/bytes y ambas máscaras; prefijo HL idéntico |
| `clock`, `cycles` | 14 bordes Q12; dos ciclos completos de 19 filas |
| `arcs`, `poses` | cuatro secuencias; 26 poses mezcladas ficticias con caché fraccionaria |
| `direct`, `inputs`, `routes` | 25 decisiones directas, 32 combinaciones de botones, 25 rutas |
| `replays` | 36 pasos: inversión durante entrada; reemplazo, cancelación y liberación |
| `selection_ok` | 34 continuaciones sin solicitud/mismo destino en modos 1/3/5 |
| `errors` | 76 rechazos, estados inválidos, selección, compatibilidad y precedencia de fallos |
| `wire` | campos, bytes, capacidades y nueve combinaciones de aceptación/rechazo |
| `lifecycle` | nueve escenarios de pausa/R/reset/HOME/tapa/error/salida |
| `atomicity` | 19 puntos de inyección futuros, centinela y reglas de reintento |

`source_fraction` de los cuatro ejemplos es 1018/512/614/512, tomada de los
relojes observados, aplicada a cuaterniones/traslaciones **inventados**.
`translation` guarda pares numerador/denominador; los cuaterniones son
literales double. `replay_columns` nombra las nueve columnas y `initial`
usa `[source,target,mode,counter,beta,cache_valid]`. `selection_ok.output`
usa el mismo orden. `null` significa sin solicitud/pendiente.

En `errors` y `selection_ok`, `state` describe el reloj público, no una pose
binaria serializada. El harness deberá partir de perfil/topología y poses
ficticias válidos, aplicar los campos indicados y después inyectar
`read_fault`, cuando exista. `profile` elige el perfil de la llamada;
`state.profile_id` permite comprobar desacuerdos. Los valores fuera del
rango wire se inyectan en la API nativa, no se truncan para escribir uint16.
Los escenarios `lifecycle` se repetirán desde ambos giros estables y desde
el primer/último beta de los cuatro arcos; HOME y tapa son dos eventos
separados que deben satisfacer el mismo resultado conservado.

Los [tests del contrato](../tests/python/test_heather_turns_contract.py)
usan Decimal, fracciones exactas, grafo independiente y tablas de pertenencia;
no importan núcleo, pipeline ni recursos privados. Comprueban los literales,
hemisferio antipodal, padre en otro canal, raíz mundial única y controles
negativos de origen entero/caché realimentada. Las comprobaciones de ciclo
de vida y atomicidad aquí son obligaciones de harness, **no ejecución nativa**.

HG-T4 deberá alimentar esos casos al reloj/evaluador/actor/controlador C++,
inyectar fallos en cada lectura de ambos canales, entrada/continuación/salida
de cada arco y cada punto de `atomicity`, comparar estado/salidas completas
con el centinela repetido `a55ac33c96696996`, reparar y reintentar. Añadirá
perfiles mal formados, CRC/tamaños/tablas/texturas/cierre y límites 64/65,
58/78/79/80 por formato; no sustituirá esas pruebas por el test del JSON.
Comparará ambos canales y modelo contra las 70 referencias privadas de HG-T2,
conservará regresiones HL/HM, medirá memoria y compilará ARM. HG-T5 empaqueta
después una entrega identificada. Ninguna de esas etapas se acredita con HG-T3.

Reproducción pública:

```sh
rtk proxy .venv/bin/python -m pytest -q tests/python/test_heather_turns_contract.py tests/python/test_heather_locomotion_contract.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
```
