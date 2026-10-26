# HL-T4a — Reproducción multiclips de Heather original

2026-10-26. Contrato **HLC01–HLC16**, perfil `heather-original-pal-525-v1`.
Depende del [cierre acotado HL-T3](../docs/execution/f03-02-heather-locomotion.md)
y desarrolla HL05 de [la especificación HL](../docs/specs/sh3-3ds/heather-locomotion.md).
Estado: contrato y vectores sintéticos; núcleo, conversión e integración pendientes.

Como implementador necesito reproducir espera, caminar y correr con las
transiciones contrastadas, sin confundir animación local con desplazamiento
jugable. Esta versión no define velocidad mundial, root motion, colisiones,
arma visible, expresiones, iluminación PS2 ni una habitación.

## Requisitos EARS

- **HLC01:** CUANDO se prepara el perfil privado, el convertidor DEBERÁ
  verificar MDL522 y ANM525 fijados, atuendo original, mapa de huesos y los
  tres descriptores PAL de este contrato; una discrepancia DEBERÁ impedir
  publicar el conjunto. Los bytes completos seguirán en el intermedio fuente.
- **HLC02:** CUANDO se compactan los clips, el convertidor DEBERÁ conservar
  sus índices originales y distinguirlos de los índices empaquetados; el
  wrap DEBERÁ volver al inicio del mismo clip, sin pasar al siguiente rango.
- **HLC03:** MIENTRAS reproduce el perfil, el núcleo DEBERÁ usar ticks `2`,
  velocidades PAL ya convertidas y fase Q12; DEBERÁ separar fase de pose y
  contador devuelto. Un tick distinto DEBERÁ dar error sin avance parcial.
- **HLC04:** CUANDO evalúa modo estable, el núcleo DEBERÁ evaluar la fase
  anterior al avance y devolver el contador avanzado una vez módulo período.
- **HLC05:** CUANDO selecciona caminar↔correr desde modo estable, el núcleo
  DEBERÁ conservar fase relativa y mezclar primero los extremos de ambos
  clips, después el tiempo; al cerrar modo 5 DEBERÁ aplicar los dos avances
  y evaluar en la fase intermedia, sin emitir una mezcla con beta ≥4096.
- **HLC06:** CUANDO selecciona espera→caminar, caminar→espera o correr→espera
  desde modo estable, el núcleo DEBERÁ conservar la última pose **local**
  evaluada y mezclarla con el primer frame del destino; DEBERÁ mantener su
  contador en cero durante modo 3 y avanzar una vez en su salida.
- **HLC07:** CUANDO recibe una selección no acreditada o una interrupción
  de mezcla, el núcleo DEBERÁ devolver un error explícito y conservar el
  estado y la salida previos; no DEBERÁ encadenar otras transiciones para
  atribuirle equivalencia con PS2. Repetir el destino actual será un no-op
  de selección y permitirá la actualización ordinaria.
- **HLC08:** CUANDO publica una pose, el núcleo DEBERÁ completar ambos
  canales en la misma actualización, conservar sus máscaras disjuntas y
  componer cada padre antes del hijo; un fallo en cualquier lectura DEBERÁ
  impedir publicar estado, caché o matrices parciales.
- **HLC09:** MIENTRAS evalúa, el núcleo DEBERÁ usar NLERP por hemisferio corto
  para rotaciones locales y LERP para traslaciones, sin interpolar matrices
  modelo; DEBERÁ rechazar números no finitos o poses fuera de contrato.
- **HLC10:** CUANDO está pausado, el presentador DEBERÁ conservar reloj,
  mezcla y caché; R DEBERÁ ejecutar exactamente una actualización completa
  con ticks 2. La cámara podrá cambiar sin avanzar la animación.
- **HLC11:** CUANDO reinicia el clip desde el visor, el presentador DEBERÁ
  cancelar la mezcla y mostrar el primer frame del destino actual en modo
  estable. CUANDO retorna de tapa/HOME DEBERÁ conservar la pose, descartar
  tiempo dormido y solicitudes pendientes, y exigir soltar los controles.
- **HLC12:** MIENTRAS se presenta la escena, la aplicación DEBERÁ separar
  las 25 actualizaciones de animación/s de FPS submit; DEBERÁ limitar el
  tiempo recuperable por llamada a 0,1 s y ejecutar cada actualización en
  orden, sin multiplicar un incremento para saltar mezclas o cachés.
- **HLC13:** CUANDO lee el formato SRI2, el lector DEBERÁ comprobar versión,
  límites, longitudes, CRC, reservados y relaciones antes de publicar; DEBERÁ
  rechazar truncamientos y bytes sobrantes. SRI1 conservará su interpretación.
- **HLC14:** MIENTRAS ejecuta el núcleo, DEBERÁ depender de vistas/lectores
  inmutables suministrados y memoria de capacidad fija, sin archivos, reloj
  de pared, SDK, PCSX2, GPU ni asignaciones por actualización.
- **HLC15:** CUANDO verifica fidelidad privada, el auditor DEBERÁ comparar
  A/B y reconstrucción de los datos seleccionados, extremos crudos ≤1e-7
  y matrices modelo ≤0,001 frente a las referencias fijadas. La tolerancia
  de extremos crudos no DEBERÁ aplicarse a cuaterniones ya interpolados.
- **HLC16:** CUANDO valida o entrega, DEBERÁ separar consistencia sintética,
  fidelidad privada, build y ejecución física; CI DEBERÁ funcionar sin ISO,
  BIOS, estados ni recursos originales, con gates de los módulos nuevos.

## Perfil fijado y dos canales

Modelo original `0x100`, recurso MDL522, máscara de submallas `0x3021`,
esqueleto fuente de 73 huesos y 36 activos. ANM525 contiene 1763 muestras
de 264 bytes. Solo se seleccionan las siguientes 58 muestras:

| Acción / ID | Descriptor PAL `<HHhHHBB>` | Rango fuente | Primer índice empaquetado | Incremento con ticks 2 | Período Q12 |
|---|---|---|---:|---:|---:|
| espera / 101 (`0x65`) | `101,10,307,0,9,1,0` | 0–9 | 0 | 614 | 40960 |
| caminar / 109 (`0x6d`) | `109,24,1996,80,103,1,0` | 80–103 | 10 | 3992 | 98304 |
| correr / 113 (`0x71`) | `113,24,2227,176,199,1,0` | 176–199 | 34 | 4454 | 98304 |

Los descriptores ya contienen velocidad PAL: no volver a aplicar la conversión
del ELF. Offset de velocidad acreditado: cero. Se conservan todos sus doce
bytes, sin deducir velocidad del número de muestras ni de los FPS del visor.

Fuentes privadas fijadas (SHA256, nunca publicadas por CI):

- MDL522: `1aa81b56c0a079c8d98e57f17537e91b2ce20f1e46a1cc6d9816561cad03d2e9`.
- ANM525: `a0ad870863df5c495c453acdc2230dc8bb762394687599329f5a97a975d75181`.

Máscaras en **índices del esqueleto fuente**, antes de compactar:

| Canal lógico | Referencia de adquisición | Huesos |
|---|---|---|
| 2 | actor +0x260 | 1,3,5,7,8,10,12,13,14,16,17,21,27,33,35 |
| 1 | actor +0x1d0 | 0,2,4,6,9,11,15,24,25,26,30,31,32,34,36,37,38,39,40,41,42 |

La unión ordenada define el mapa compacto. Cada padre de un hueso activo
debe estar en la unión o ser raíz; se conserva su correspondencia, no se
reparenta. Los dos canales comparten selección, fase y blend en los retornos
acreditados. El núcleo usa un reloj común y vistas de máscara distintas,
publicadas juntas; no reproduce estados transitorios entre llamadas del EE.
Otro banco con canales divergentes necesita otro perfil.

En la adquisición, `+40` es el descriptor de origen retenido y `+44` el
destino. El campo histórico `requested` de recibos significa `+40`.
Las direcciones EE son procedencia y no se serializan como punteros runtime.

## Estado y transiciones

`counter` siempre significa **la próxima fase a consumir** en modo estable
o 5, equivalente al contador devuelto por la última actualización. La salida
incluye `pose_phase` separado. Estado acotado:

- `source_id`, `target_id`, `mode` (1,3,5), `counter`, `blend` Q12.
- `last_local[36]`: última pose local completa, incluida la mezcla temporal.
- `saved_local[36]`: origen congelado para modo 3; válido solo en ese modo.
- Identidad del perfil y validez de inicialización. No almacena matrices de
  RAM ni reinterpreta matrices modelo como cuaterniones locales.

Inicialización de inspección: espera, contador/blend cero, ambas IDs 101 y
`last_local` igual al frame 0. Produce una pose sin consumir una actualización.
Esta política y el reinicio L son controles del visor, no eventos del juego.
El dominio no acepta estados arbitrarios deserializados; un estado corrupto
se rechaza. El consumidor llamará `update(request opcional, ticks=2)`.

Invariantes al entrar: modo 1 tiene IDs iguales, blend cero y contador menor
que el período; modo 5 tiene las dos IDs 109/113 distintas, contador menor
que 98304 y blend en {384,768,…,3840}; modo 3 tiene un arco de su tabla,
contador cero, blend en la secuencia correspondiente y caché válida.
Fuera de modo 3 la caché congelada está invalidada. `last_local` siempre es
válida. Los valores beta iniciales se crean dentro de la actualización; no
se expone un estado intermedio con beta cero y modo 3/5.

### Modo 1

Para clip de N muestras, inicio S y primer índice empaquetado K:

```text
P = N * 4096
j, r = divmod(counter, 4096)
frame_fuente = S+j; siguiente_fuente = S+(j+1)%N
frame_paquete = K+j; siguiente_paquete = K+(j+1)%N
pose_phase = counter
pose = mix(frame_paquete, siguiente_paquete, r/4096)
counter_salida = (counter + incremento_destino) % P
```

`mix` opera en poses locales; después se compone `parent * local`.
Una solicitud del mismo destino no reinicia ni consume un avance adicional.
Enteros intermedios al menos uint64; entrada fuera de rango se rechaza antes
de sumar. No saturar silenciosamente fase/blend ni usar overflow como wrap.

### Modo 5: caminar↔correr

Solo desde modo 1 y con ambos rangos de 24 muestras. Se conserva `counter`,
se retiene el clip anterior como origen y se elige el destino solicitado.
La primera actualización usa beta 384; las siguientes suman 384.
Las diez poses mezcladas usan 384,768,…,3840. En cada una:

```text
a = mix(origen[j], destino[j], beta/4096)
b = mix(origen[(j+1)%24], destino[(j+1)%24], beta/4096)
last_local = mix(a, b, r/4096)
pose_phase = counter
counter_salida = (counter + incremento_destino) % 98304
```

Las rotaciones se normalizan en **cada** `mix`. Interpolar antes cada clip
en el tiempo y luego mezclar clips no es equivalente. Al superar el límite
en la siguiente suma de beta (3840+384=4224), la salida recursiva observada:

1. Avanza una vez con el incremento del destino, módulo 98304.
2. Evalúa únicamente el destino en esa fase intermedia.
3. Avanza otra vez; publica modo 1, origen=destino y blend=0.

No se emite beta 4096 ni 4224; tampoco se omite el segundo avance. El wrap
se aplica en ambos avances y en el índice siguiente de ambos clips.

### Preludio 4 y modo 3: mezcla con origen congelado

El preludio 4 se representa como una operación atómica de caché, no como
un cuarto modo público. Copia `last_local` a `saved_local` para ambos canales
**antes** de sustituir IDs o contador. No vuelve a evaluar usando el contador
ya avanzado; no conserva solo el frame entero ni matrices compuestas.

| Selección desde estable | Primer beta | Sumas posteriores | Poses mezcladas | Salida |
|---|---:|---:|---:|---|
| 101→109 | 768 | 768 | 5: 768…3840 | modo 1, fase pose 0, contador 3992 |
| 109→101 | 1280 | 360 | 8: 1280…3800 | modo 1, fase pose 0, contador 614 |
| 113→101 | 1280 | 360 | 8: 1280…3800 | modo 1, fase pose 0, contador 614 |

Durante todas las poses mezcladas, `counter=0` y
`last_local=mix(saved_local,destino[0],beta/4096)`. La fuente congelada no se
reescribe con el resultado de cada mezcla. Se conserva la ID de origen.
La siguiente suma que alcance/supere 4096 evalúa destino[0], avanza una sola
vez y publica modo 1, origen=destino, blend=0; invalida `saved_local`.
El `pose_phase` del destino es cero, sin afirmar que toda la pose sea su frame 0.

La adquisición observó incremento de blend 1280 al entrar y 360 después
(base 640, ticks 2, offset posterior -460). Ese offset puede permanecer en
espera estable; no es un motivo para rechazar las capturas. El núcleo usa
la tabla acreditada y no expone modificación libre de offsets.

### Selecciones fuera de perfil

Los cinco arcos anteriores son los únicos habilitados desde estable.
101→113 devuelve `unsupported_transition`. Un ID distinto de 101/109/113
devuelve `unknown_clip`. En modos 3/5, pedir un destino distinto del actual
devuelve `transition_busy`, incluidos retornos al origen. No hay cola en
el dominio ni conversión automática espera→caminar→correr.

HL-T3c.4 observó la primera pose de una interrupción específica: primera
mezcla 101→109 con beta 768, luego mezcla hacia 101 con beta 1280 usando
aquella pose mezclada como caché. El vector sintético conserva esta fórmula
como **diagnóstico**, pero no habilita su secuencia completa en el visor.
Una futura ampliación necesita observar la continuación y fijar su contrato.

## Componentes, errores y ciclo de vida

| Responsabilidad | Entrada/salida prevista | Ubicación |
|---|---|---|
| Validar perfil y plan de reloj | Estado + solicitud → plan, sin leer huesos | dominio, HL-T4b.1 |
| Leer muestra local | Clip + índice relativo + hueso → TR o error | vista inmutable inyectada, HL-T4b.2 |
| Evaluar y cachear | Plan + lector + scratch → estado/pose completos | dominio, HL-T4b.2–3 |
| Preparar SRI2 | Intermedios fijados → bytes deterministas | pipeline, HL-T4c.1 |
| Cargar y validar | Archivo → modelo publicado al completar | plataforma, HL-T4c.2 |
| Cadencia y controles | Eventos/tiempo → actualizaciones; pose → renderer | aplicación, HL-T4d |

El núcleo recibe referencias de capacidad fija; no importa plataformas ni
el lector de archivos. Se reutilizan paleta, skinning y ordenación a través
de la pose modelo. `evaluate_rig` de SRI1 no se aplicará al bloque concatenado:
su wrap sobre `sample_count` mezclaría clips diferentes. Se conserva el camino
SRI1 para regresión. Esta separación permite lectores sintéticos que fallen
en un hueso del segundo canal, sin simular archivos o GPU.

Error de núcleo, en orden de precedencia: `invalid_profile`, `invalid_state`,
`invalid_ticks`, `unknown_clip`, `transition_busy`, `unsupported_transition`,
`sample_unavailable`, `invalid_pose`. Los primeros cinco se validan antes de
leer muestras; no hay mutación al fallar. Error de carga se mapea a los errores
de archivo existentes (lectura/datos/verificación), con diagnóstico del campo.
Un error de solicitud se muestra en el visor; la siguiente actualización sin
solicitud puede continuar. Un error de recurso conserva la última pose y pausa.

Memoria: máximo estructural 73 huesos, 64 muestras totales, 3 clips; perfil
privado exactamente 36/58/3. No duplicar la malla por clip. Muestras máximas:
130816 bytes (73*64*28); selección real: 58464. El estado más scratch adicional
de locomoción tendrá límite de 32 KiB, excluidos rig, render y texturas ya
existentes. Buffers persistentes propiedad del presentador, fuera de su pila;
HL-T4b medirá `sizeof` y comprobará ausencia de asignación por actualización.

Cada TR tiene traslación finita de magnitud por componente ≤100000 y
quaternion finito, componentes ≤1,001 y norma cuadrada a ≤0,001 de uno,
como SRI1. NLERP usa signo negativo solo si dot<0 (dot=0 conserva signo),
normaliza su resultado y rechaza norma cero/no finita. Las matrices resultantes
también deben ser finitas. Los límites no permiten sustituir datos inválidos
por pose identidad ni publicar una mezcla parcial.

Políticas de aplicación (no pruebas de comportamiento PS2):

- Prioridad: START/suspensión > pausa > reinicio L > paso R > selección > tiempo.
  Un evento de mayor prioridad consume esa llamada y descarta los inferiores.
- Pausa A limpia resto temporal y solicitud pendiente; R solo actúa pausado.
  Seleccionar pausado se rechaza con diagnóstico de aplicación `paused`.
- Una selección aceptada por la UI queda pendiente hasta la próxima
  actualización fija; máximo una. Una segunda solicitud antes de consumirla
  se rechaza; no reemplaza la primera. Suspensión/reinicio/pausa la eliminan.
- 25 Hz es la cadencia de inspección conservada, ticks 2 es el paso acreditado;
  no se deduce de ello un FPS físico de PS2. Resto temporal en [0,1), tiempo
  finito positivo limitado a 0,1 s: como máximo tres actualizaciones por llamada.
  Un tiempo negativo/no finito no avanza ni altera el resto. Cada update evalúa
  la pose aunque solo se presente el último resultado.
- Redibujar por cámara, frame ocupado o HUD no consume una actualización.
  La devolución de GPU no modifica el reloj. Se preservan New fast, cuerpo/cara,
  texturas, controles de cámara y espera de GPU antes de liberar sus buffers.

## SRI2: transporte de inspección

Decisión: una versión nueva de [SRI](rig-inspection-v1.md), con geometría,
materiales y texturas compartidos. Se descartan tres SRI1 completos por duplicar
geometría y porque no representan fase/caché entre clips. No es SH3P ni reemplaza
los intermedios completos. Esta sección fija bytes para HL-T4c, no un lector
ya implementado. SRI1 no se reinterpretará ni rellenará con 58 muestras.

Little endian; cabecera de 96 bytes, `<8s22I>`, sin padding implícito:

| Offset | Campo | Regla |
|---:|---|---|
| 0 | magic, 8 bytes | `S3RIv2\0\0` |
| 8,12,16,20,24,28 | B,F,H,V,I,M | Límites SRI1; F cuenta muestras totales |
| 32 | clips | 3 |
| 36 | ticks | 2 |
| 40 | frecuencia de inspección | 25 |
| 44 | perfil | 1 = heather-original-pal-525-v1 |
| 48,52 | recursos modelo/animación | 522,525 |
| 56 | bytes payload | fórmula inferior |
| 60 | CRC32 IEEE del payload | No autentica procedencia |
| 64–95 | reservados | ocho uint32 cero |

Payload, en este orden:

1. Centro/escala y padres como SRI1: `16+4B` bytes.
2. B vínculos `<HBB>`: índice de hueso fuente 0..72, canal 1/2, reservado cero.
   Índices únicos ascendentes; mapa y canales exactamente los fijados arriba.
3. Tres descriptores `<HHhHHBBII>` (20 bytes cada uno): doce bytes PAL,
   primer índice empaquetado y uint32 reservado cero. Orden 101,109,113;
   primeros 0,10,34; sin huecos/solapes, suma de cantidades F=58.
4. Muestras locales TR, helpers, vértices, índices y materiales según SRI1,
   en el mismo orden y con las mismas restricciones numéricas.

Longitud exacta: `16+8B+60+28BF+68H+28V+2I+28M`; total = 96 + payload.
El perfil privado exige B=36, F=58, H=49, V=6943, I=16566, M=13;
tamaño previsto **290156 bytes** (calculado, aún no convertido).
El centro se deriva del frame inicial de espera como SRI1; la cota de radio
considerará las 58 muestras con el mismo algoritmo conservador del preparador.
Centro/escala son únicos para los tres clips, sin recentrar en cada selección.
Texturas numeradas y CRC siguen SRI1. El paquete futuro usará `heather.sri`
con magic v2, el ejecutable que acepte v2 y manifiesto de hashes propio.
No sustituir el paquete físico ya validado hasta completar HL-T4c/d.

El lector valida tamaños antes de asignar, reservados y tablas antes de
evaluar, identidad de campos antes de publicar. Los metadatos no autentican
un recurso: HL-T4c cotejará SHA de fuentes, máscara, padres, materiales y
selección de cada frame contra los intermedios privados. El recibo conservará
el mapeo completo y hashes, sin rutas/timestamps dentro de los bytes SRI2.
Se reconstruye desde SRI2 la selección TR/materiales, no todo ANM/MDL.

## Vectores, trazabilidad y aceptación

[Vectores propios](../tests/fixtures/synthetic/heather-locomotion-v1.json):
metadatos de perfil, aritmética entera y poses inventadas; no contienen malla,
texturas, bytes de ANM ni matrices capturadas. El
[validador independiente](../tests/python/test_heather_locomotion_contract.py)
comprueba literales mediante racionales y Decimal de 60 dígitos, sin importar
el futuro núcleo, encoder ni oráculos privados. Sus controles negativos
distinguen fase posterior, clamp al final, salida con un avance, caché cruda,
orden de mezcla invertido y pérdida de pose al interrumpir.

| Requisitos | Evidencia de origen / política | Vectores o casos de aceptación | Implementación |
|---|---|---|---|
| HLC01–02 | HL-T1, T3c.5, SRI1 | descriptores, mapa, límites de rangos y wire | T4c.1–3 |
| HLC03–04 | T2d, T3c.5 | `clock`, ciclos completos de 3 clips | T4b.1 |
| HLC05 | T3c.3 y wrap | `clock`, `mode5_sequences`, `pose.mode5_order` | T4b.1–3 |
| HLC06 | T3c.4/c.6/c.7 | `mode3_sequences`, `pose.cached_stop` | T4b.1–3 |
| HLC07 | Cinco arcos; interrupción parcial | tabla de errores, `pose.interrupted_diagnostic` | T4b.3 |
| HLC08–09 | Máscaras T3c.4; oráculo local/modelo | `pose.channels`, hemisferio y fallos atómicos | T4b.2–3 |
| HLC10–12 | Políticas de inspección | matriz lifecycle inferior | T4d |
| HLC13–14 | SRI1, límites de este contrato | estructura wire; memoria y fallos de lector | T4b.3/T4c.2 |
| HLC15–16 | HL06; cierre HL-T3 | A/B, referencias privadas y gates | T4c.3/T4d/T5 |

Casos pendientes de implementación, no aprobados por comprobar los vectores:

| Grupo | Batería obligatoria |
|---|---|
| Solicitudes | 101→113, ID 0/65535, cambio a otro destino en modos 3/5, mismo destino en los tres modos; comparar todos los bytes lógicos de estado/salida tras error |
| Reloj | ticks 0/1/3/máximo, counter=P/uint32 máximo, beta imposible/overflow, cada entrada/salida y wrap en ambos sentidos |
| Pose/atomicidad | lectura que falla en canal 1 después del 2, NaN/Inf, quaternion cero, máscara duplicada/incompleta, padre ausente; caché interpolada y fuente congelada invariable durante modo 3 |
| Lifecycle | pausa en mitad de modos 3/5, 100 redibujos sin avance, R único, L en cada modo, selección simultánea, suspensión con solicitud pendiente y tecla mantenida, tiempo largo/no finito, START con frame ocupado |
| Wire | magic v1/v2/desconocido, truncar cada sección, CRC corrupto, longitud falsa, reservado no cero, descriptor/rango/canal alterados, material o textura ausente, bytes sobrantes, salida sin publicar al fallar |
| Fidelidad/rendimiento | A/B con fuentes fijadas, reconstrucción independiente, matrices ≤0,001, sanitizers, cobertura ≥80 % líneas/ramas por módulo nuevo, host/ARM y 60 s por clip/transición en 2DS XL |

No se amplían las tolerancias para cerrar un caso fallido. La precisión f32
de extremos sigue HL06; el NLERP sintético tiene tolerancia 1e-12 en Decimal
convertido a double y 1e-6 para su futuro cotejo float C++. La fidelidad contra
PCSX2 conservará el umbral de matrices 0,001, comprobado aparte.
