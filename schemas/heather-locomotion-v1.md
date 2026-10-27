# HL-T4a — Reproducción multiclips de Heather original

2026-10-26. Contrato **HLC01–HLC16**, perfil `heather-original-pal-525-v1`.
Depende del [cierre acotado HL-T3](../docs/execution/f03-02-heather-locomotion.md)
y desarrolla HL05 de [la especificación HL](../docs/specs/sh3-3ds/heather-locomotion.md).
Estado: contrato, vectores, núcleo HL-T4b.1–3, productor/lector SRI2 y cotejo
privado A/B HL-T4c.1–3, presentador y entrega HL-T4d.1–2 completados.
Build ARM corregido `7250f427ffb9`: HL-T5a/b funcional y métricas reportadas;
HL-T5c duración/cobertura detallada pendiente. Sigue HM, movimiento en escena.

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
`sample_unavailable`, `invalid_pose`. Los primeros seis se validan antes de
leer muestras; no hay mutación al fallar. Error de carga se mapea a los errores
de archivo existentes (lectura/datos/verificación), con diagnóstico del campo.
Un error de solicitud se muestra en el visor; la siguiente actualización sin
solicitud puede continuar. Un error de recurso conserva la última pose y pausa.
La falta de una muestra prevalece también si una lectura anterior o la caché
contenían una pose inválida. Se completan las lecturas necesarias hasta detectar
una falta; nunca se interpola un transform rechazado ni se publica su resultado.

### API escalar implementada en HL-T4b.1

[locomotion_clock.hpp](../engine/domain/include/sh3/domain/locomotion_clock.hpp)
y [su implementación](../engine/domain/locomotion_clock.cpp) definen:

- `LocomotionProfile`: identidad y tabla de tres descriptores. La comparación
  con `heather_locomotion_profile` valida solo metadatos escalares; no sustituye
  el cotejo de recursos, padres o máscaras del preparador.
- `LocomotionClock`: perfil, IDs de origen/destino, modo, contador, blend y
  bandera de caché. Su fábrica inicial solo inicializa el reloj; el evaluador
  HL-T4b.2 inicializa y valida las poses correspondientes antes de usarlo.
- `plan_locomotion_update(profile,current,request,ticks,out)`: devuelve un
  error y conserva `out` byte por byte si falla. Una solicitud opcional vacía
  continúa; ID 0 es `unknown_clip`. La entrada se recibe por referencia const.
- `LocomotionPlan`: candidato `next`, tipo de evaluación (clip, mezcla de
  fase o mezcla con caché), fase/fracción/beta Q12, ventanas de origen/destino
  y acción de caché (`none`, `capture_last`, `discard`). Cada ventana distingue
  índices relativos, originales ANM y empaquetados. Solo modo 5 usa la ventana
  de origen; en los demás queda a cero. La mezcla con caché usa únicamente
  el primer frame de destino, aunque la ventana incluya su siguiente índice.

El evaluador ejecuta la acción de caché en scratch y produce ambos canales;
HL-T4b.3 publica `next` y la pose **solo entonces**. El planificador
no afirma que la bandera de caché valide su contenido. No realiza NLERP,
lectura de muestras, movimiento mundial ni llamadas al renderer.

El [adaptador de pruebas nativas](../tests/locomotion_clock_oracle.py) consume
los mismos literales JSON que preceden a la implementación y coteja 173
actualizaciones con el ejecutable C++; no importa código Python productivo.
CTest integra batería escalar y oráculo en host/sanitizers. El gate individual
[gcovr-locomotion-clock.cfg](../gcovr-locomotion-clock.cfg) exige 80 % de líneas
y ramas en CI. La medición local LLVM dio 123/123 líneas y 136/136 ramas;
no constituye ejecución remota del gate GCC. Estado+plan: 132 bytes en host,
con prohibición de asignaciones durante las pruebas escalares. El presupuesto
completo de estado/scratch está medido en la sección HL-T4b.3 inferior.

### Evaluador local implementado en HL-T4b.2

[locomotion_pose.hpp](../engine/domain/include/sh3/domain/locomotion_pose.hpp)
y [su implementación](../engine/domain/locomotion_pose.cpp) separan lectura,
evaluación y publicación mediante la capa HL-T4b.3:

- `LocomotionSampleReader` es una interfaz `const/noexcept`: recibe ID de
  clip, frame **relativo** y hueso compacto; devuelve TR o lectura no disponible.
  El adaptador SRI2 futuro resolverá los índices empaquetados. No hay I/O ni
  dependencia del rig con malla, de PCSX2 o del SDK en este módulo.
- `LocomotionSkeleton` contiene cantidad, padres topológicos y un propietario
  por hueso (1 o 2). Esta representación impide duplicar propietarios; 0, 3 u
  otro canal se rechazan. Valida estructura hasta 73 huesos y permite pequeños
  rigs sintéticos. **No autentica** el mapa de 36 huesos originales: esa
  comparación sigue siendo responsabilidad del preparador/lector del perfil.
- `initialize_locomotion_pose` prepara espera[0] en ambos canales sin consumir
  reloj, normaliza las rotaciones, invalida la caché congelada y compone padres.
- `LocomotionPoseCache` conserva `last_local`, `saved_local`, cantidad y
  banderas de validez. `stage_locomotion_pose` recibe un plan del planificador
  correspondiente al mismo estado y valida ventanas, ratios e invariantes
  antes de leer. La entrada debe ser distinta de `scratch.next`; el alias se
  rechaza. Un plan no sustituye el estado/reloj que lo originó.
- `LocomotionPoseScratch` contiene la próxima caché y matrices modelo.
  Captura `last_local` una sola vez, mantiene sus bytes durante modo 3 e
  invalida su bandera al salir. Los bytes congelados inactivos no se consumen.
  Evalúa canales 2 y 1 y compone matrices solo después de completar ambos.

Esta API **prepara candidatos**, no publica estado runtime: `current` siempre
queda intacto; si falla, scratch puede contener datos parciales y **debe
descartarse**. HL-T4b.3 aporta la operación completa que valida reloj/caché,
planifica, evalúa y publica conjuntamente reloj, caché y matrices. No se debe
conectar este scratch directamente al renderer ni copiarlo después de un error.

La batería nativa comprueba lectura por clip, wrap, cinco transiciones, caché
interpolada congelada, hemisferio/dot cero, composición entre canales, límites
y errores de muestras/poses. El [oráculo independiente](../tests/locomotion_pose_oracle.py)
contrasta **26 poses en nueve escenarios** con literales previos y aritmética
Decimal, incluido el orden incorrecto de mezcla como control negativo.
Tolerancia TR/cuaterniones sintéticos 1e-6; matriz del ejemplo de dos huesos
4e-6 (redondeo float). Se conserva 0,001 para el futuro cotejo privado.
Release y ASan/UBSan aprobados; ninguna asignación `new/new[]` en la batería.
Caché 4096 bytes y scratch de pose 8768 bytes en host; el estado transaccional
incluye además reloj y topología, como se detalla a continuación.

CTest y CI incluyen las dos pruebas nuevas, lint del oráculo y
[gate individual](../gcovr-locomotion-pose.cfg) de 80 % líneas/ramas.
La medición original HL-T4b.2 fue 185/192 líneas y 160/182 ramas. Tras el
ajuste de precedencia de errores en HL-T4b.3: 199/203 líneas (98,03 %),
176/196 ramas (89,80 %) y 14/14 funciones, mediante LLVM local.
La configuración GCC/CI remota sigue sin ejecutarse aquí.

### Publicación conjunta implementada en HL-T4b.3

[locomotion_update.hpp](../engine/domain/include/sh3/domain/locomotion_update.hpp)
y [su implementación](../engine/domain/locomotion_update.cpp) son la entrada
de uso del núcleo completo:

- `LocomotionState` agrupa reloj, topología propia, caché y matrices modelo.
  Solo se inicializa mediante `initialize_locomotion`; no es un formato de
  deserialización ni una API para insertar capturas de RAM. La copia de la
  topología evita que cambiar posteriormente el rig de entrada cambie la
  jerarquía de una actualización. No autentica recursos originales.
- `LocomotionWorkspace` agrupa plan y scratch de pose de capacidad fija.
  Ambos objetos serán persistentes y propiedad del presentador. El lector
  recibe muestras inmutables ajenas a ese scratch. Ningún módulo llama a
  archivos, SDK, GPU ni funciones de asignación dinámica.
- `initialize_locomotion(profile,rig,reader,state,workspace)` valida metadatos
  y estructura, prepara espera[0] y reemplaza el estado completo solo al
  terminar. Un fallo también conserva una instancia ya inicializada; éxito
  deja contador cero sin consumir la primera actualización.
- `update_locomotion(profile,reader,request,ticks,state,workspace)` valida
  perfil, topología del estado, cantidades/banderas de caché y su relación
  con el reloj; luego planifica y evalúa. Comprueba finitud y fila afín de
  las matrices vigentes antes de reemplazarlas. Si falla cualquier paso,
  **todos los bytes de `state` permanecen intactos**, incluido el reloj.
  Scratch puede variar y se descarta; el mismo estado/workspace admite un
  reintento cuando el lector vuelve a suministrar datos válidos.
- La publicación ocurre después de todos los callbacks y de las operaciones
  que pueden devolver error. Copia caché/matrices/reloj sin excepciones y
  limpia las matrices inactivas, para no publicar residuos del scratch.
  Es una garantía de todo o nada al retornar en el **hilo propietario**;
  no introduce sincronización para lectores concurrentes ni callbacks al publicar.

Capacidad insuficiente se representa por una cantidad de huesos superior a
73: `invalid_profile` al inicializar, `invalid_state` si está en el estado.
Una cantidad de caché discordante también es `invalid_state`. Los buffers son
tipos de tamaño fijo; no se aceptan punteros a salidas más pequeñas. Campos
no finitos, quaternion cero/no unitario y matrices no afines dan `invalid_pose`,
después de los errores escalares y de la prioridad de disponibilidad indicada.

La [batería transaccional](../tests/cpp/test_locomotion_update.cpp) cuenta
**3013 rechazos y 3111 actualizaciones válidas/reintentos**, incluidos los
cinco arcos, todas las betas/salidas, fallos en cada lectura y ambos canales,
inicialización con 73 huesos, estado corrupto, prioridad entre errores y
capacidad. Observa el estado anterior dentro de cada callback y compara sus
bytes después de errores. Prohíbe `new/new[]`, también alineados, en la batería.
El [oráculo completo](../tests/locomotion_update_oracle.py) coteja **410
snapshots** de reloj, pose, caché y matrices; usa Decimal y productos de
cuaterniones sobre los ejes, con las secuencias de beta ya fijadas. Máximos
local 7,4822e-8 y modelo 5,8967e-7; tolerancias 1e-6 y 4e-6, respectivamente.

Estado 9168 bytes + workspace 8872 = **18040 bytes**, frente al máximo
32768; `static_assert` impide compilar si se supera. No duplica muestras,
malla ni texturas. Las pruebas Release y ASan/UBSan pasan: **31/31 por preset**,
con 25 regresiones SRI1 además de seis pruebas de locomoción. Cobertura LLVM
local de `locomotion_update.cpp`: 48/48 líneas y 36/36 ramas (100 %).
El [gate individual CI](../gcovr-locomotion-update.cfg) exige 80 % en cada
métrica, junto a los gates separados de reloj y pose. No acredita ejecución
remota, compilación ARM ni ejecución física de esta integración pendiente.

Memoria: máximo estructural 73 huesos, 64 muestras totales, 3 clips; perfil
privado exactamente 36/58/3. No duplicar la malla por clip. Muestras máximas:
130816 bytes (73*64*28); selección real: 58464. El estado más scratch adicional
de locomoción tiene límite de 32 KiB, excluidos rig, render y texturas ya
existentes. Buffers persistentes propiedad del presentador, fuera de su pila;
HL-T4b mide `sizeof` y comprueba ausencia de asignación por actualización.

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

### Integración de aplicación HL-T4d.1

`LocomotionProbe` posee perfil, snapshot y workspace; recibe `IRigScene` y
`LocomotionSampleReader` inyectados. El lector mantiene sus datos inmutables
durante la vida del presentador. `present` entrega las matrices ya publicadas;
la cámara y el renderer no evalúan clips. `sizeof(LocomotionProbe)` queda
limitado por `static_assert` al presupuesto de 32 KiB. La instancia y los
buffers de dibujo viven fuera de la pila del bucle de 3DS.

| Entrada de inspección | Resultado |
| --- | --- |
| ZR / ZL, flanco de pulsación | Solicita siguiente/anterior en el ciclo 101 → 109 → 113 → 101; ZL recorre el orden inverso |
| ZL y ZR simultáneos | Rechazo `selection_conflict`; conserva cualquier solicitud pendiente |
| A | Alterna reproducción/pausa; limpia resto temporal y selección pendiente |
| L | Reinicia el **destino actual** estable en su primer fotograma, sin consumir ticks; conserva pausa |
| R pausado | Ejecuta exactamente una actualización completa con ticks 2 |
| R reproduciendo | Consume la llamada sin avance ni selección; conserva el resto temporal |
| SELECT / cruceta / X-Y / B | Cuerpo-cara / cámara / zoom / restablecer cámara; disponibles también en pausa |
| START | Termina incluso durante la espera de liberación o con GPU ocupada |
| Tapa/HOME y retorno | Conserva snapshot y pausa; descarta tiempo/selección; espera liberar todos los botones |

El orden de prioridad anterior se aplica a reproducción; la cámara sigue
siendo independiente. El selector solo encola arcos admitidos: espera→correr
directa (`101→113`) y otra selección durante mezcla se rechazan, sin inventar
transiciones intermedias. Al encolar no se lee ni cambia la pose; el siguiente
update fijo consume la petición. Una segunda petición rechazada conserva la
primera. La llamada de selección descarta su propio tiempo, conserva el resto
anterior y no avanza. El primer frame de liberación tras reanudar también
descarta su tiempo, incluidos intervalos largos de suspensión.

Los diagnósticos de rechazo permanecen visibles hasta otra acción explícita
o un nuevo fallo; los updates ordinarios continúan tras errores de solicitud.
`sample_unavailable`, `invalid_pose` y errores estructurales pausan y mantienen
el último snapshot completo. Si falla el segundo update de una llamada, se
conserva el primero ya publicado y se descarta el resto temporal de esa llamada.
No se presenta el scratch incompleto ni se intenta el tercer update.

`initialize_locomotion`/`initialize_locomotion_pose` aceptan un clip inicial
explícito para L; por defecto siguen siendo 101. Esta inicialización valida
ambos canales antes de publicar, borra la caché congelada y no es una nueva
transición jugable acreditada. El renderer valida el payload geométrico
compartido; la validez del reloj SRI1 o SRI2 sigue correspondiendo a su lector.
El ejecutable Heather ahora exige el paquete SRI2 completo, sin interpretar
un SRI1 como multiclips. El último build aceptado físicamente sigue siendo
`7250f427ffb9`, multiclips, según reporte funcional del usuario; el anterior
`4707dacec7d1` falló al abrir SRI2 y se conserva como intento fallido.

Pruebas: prioridad, pausa en modos 3/5, 100 redibujos sin avance, R/L,
tiempos inválidos/largos, actualizaciones secuenciales a través de mezclas,
fallo tardío y reinicio fallido, retorno sin tiempo dormido, botones retenidos,
START y GPU ocupada. El entry point real compila con dobles SDK y se prueban
sus controles, hooks APT y New fast. SRI2 sintético recorre lector → presentador
→ skin/sort durante 500 iteraciones sin asignaciones. Host: 37/37 en
Release y 37/37 ASan/UBSan; módulo Python de reconstrucción: 356 aprobadas.
HL-T4d.2 añade `gcovr-locomotion-probe.cfg`, umbral individual 80 % de líneas
y ramas, al job de cobertura y a sus artefactos. Medición GCC local del
presentador: 123/146 líneas y 103/119 ramas. La batería CTest completa pasa
364/364 en Release y 364/364 con ASan/UBSan; 608 pruebas Python relacionadas
aprobadas. ARM `4707dacec7d1` usa la imagen fijada y conserva el gate del shader.
El paquete privado reconstruido A/B incluye SRI2, trece texturas, 3DSX, SMDH
y [protocolo físico](../docs/compatibility/heather-locomotion.md). La prueba
breve en Azahar cubre arranque, los cinco cambios y controles; no acredita
los 60 s por clip/transición, tapa/HOME ni rendimiento en consola. CI remoto
y aceptación física multiclips siguen pendientes.

## SRI2: transporte de inspección

Decisión: una versión nueva de [SRI](rig-inspection-v1.md), con geometría,
materiales y texturas compartidos. Se descartan tres SRI1 completos por duplicar
geometría y porque no representan fase/caché entre clips. No es SH3P ni reemplaza
los intermedios completos. Productor y lector implementan el layout siguiente.
SRI1 no se reinterpretará ni rellenará con 58 muestras.

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
tamaño **290156 bytes**, confirmado con geometría sintética de esas cantidades;
la conversión privada A/B sigue pendiente.
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

### Productor implementado en HL-T4c.1

- [Autenticación de fuentes](../tools/pipeline/produce_heather_locomotion.py):
  `produce_heather_locomotion(model, animation, pal_descriptors)` recibe bytes
  inmutables, limita MDL/ANM a 16 MiB/512 KiB, calcula sus SHA256 y exige los
  fijados arriba. Comprueba los 36 bytes PAL antes de decodificar. Vuelve a
  obtener geometría, animación y RGBA con los decoders existentes; no acepta
  hashes declarados ni documentos editados como prueba de procedencia.
- [Reductor y encoder](../tools/pipeline/locomotion_inspection.py):
  `heather_locomotion_rig(geometry, animation, textures, descriptors)` permite
  ensayos con intermedios sintéticos y siempre declara `source_verified=false`.
  Solo la entrada anterior autentica fuentes. `encode_locomotion_rig` exige
  el mapa exacto, sus canales, B=36/F=58 y los tres registros PAL, y comparte
  las restricciones de geometría de SRI1. El reductor exige además las
  cantidades privadas, máscara, ausencia de morph activo y asociaciones.
- [Preparación compartida](../tools/pipeline/rig_inspection.py): compacta
  muestras explícitas y devuelve geometría/framing sin crear un SRI1 de 58
  frames. Centro de espera[0], radio conservador sobre las 58 muestras,
  geometría/materiales únicos. El encoder común conserva pesos, UV, alfa RGBA
  y orden opaco/transparente. SRI1 sigue seleccionando diez muestras y conserva
  los hashes de sus dos ejemplos de regresión.
- Resultado en memoria: diccionario de 14 archivos (`heather.sri` y trece
  `texture-NN.rgba`) y recibo JSON serializable determinista. El recibo registra
  cada hueso/padre/canal fuente y compacto, helper/destino, descriptor PAL,
  cada índice de muestra fuente/empaquetado, submalla/rangos de vértices e
  índices, textura/material, framing y SHA256/tamaño de cada archivo. La
  entrada autenticada añade recursos, tamaños y hashes de las fuentes.
  No hay rutas ni tiempos en SRI2 o el recibo. Los bytes completos y los datos
  excluidos permanecen en las fuentes/intermedios conservados por el llamador.
- Ninguna de estas funciones escribe archivos ni reemplaza paquetes. La
  publicación exclusiva y la comparación privada corresponden a HL-T4c.3;
  la lectura/reconstrucción independiente se describe a continuación. Los errores rechazan
  el resultado completo y no modifican los argumentos.

Pruebas propias de layout, correspondencias, límites, CRC, procedencia y
regresión en [la batería SRI2](../tests/python/test_locomotion_inspection.py) y
[la batería de fuentes](../tests/python/test_produce_heather_locomotion.py).
La simulación de autenticación reemplaza pines solo mediante `monkeypatch`
dentro de pruebas; la API productiva no ofrece parámetros para relajarlos.
El adaptador de decoders se prueba con MDL/ANM inventados reales, de otro modelo,
que el perfil Heather rechaza. Esto no acredita fidelidad privada ni hardware.

### Lector y reconstrucción implementados en HL-T4c.2

[Modelo/vista](../engine/domain/include/sh3/domain/inspection_locomotion.hpp):
`InspectionLocomotion` conserva perfil, frecuencia, mapa/canales y almacenamiento
de capacidad fija para las secciones compartidas. Reutiliza `InspectionRig`
como almacenamiento de geometría/TR, manteniendo sus dos campos de reloj
legacy en cero: `valid_rig` lo rechaza como SRI1. La pose debe venir del núcleo
de locomoción; nunca se llama a `evaluate_rig` con sus 58 muestras.
`InspectionLocomotionReader` implementa `LocomotionSampleReader` mediante una
referencia inmutable al modelo validado y devuelve la muestra relativa al clip.
Rechaza ID/hueso/frame fuera de rango sin alterar la salida. No aplica wrap
entre bloques, no asigna memoria y no realiza I/O. La topología para el núcleo
se obtiene con `locomotion_rig_skeleton`.

[Carga de plataforma](../engine/platform/common/include/sh3/platform/inspection_locomotion.hpp):

- `read_locomotion_rig(path, out, api)` comprueba exclusivamente SRI2: cabecera
  de 96 bytes, límites/fórmula antes de asignar, cierre exacto, CRC, reservados,
  identidad PAL, mapa/canales, padres, TR, helpers, vértices, índices y materiales.
  Devuelve `LocomotionLoadResult` con `FileError`, campo diagnóstico estático y
  ordinal de textura cuando corresponda.
- `read_locomotion_bundle(directory, out, api)` exige `heather.sri` y todos los
  `texture-NN.rgba` referidos. Verifica tamaño exacto y CRC incremental de cada
  textura usando un buffer de 64 KiB. No retiene/sube los píxeles ni enumera
  archivos ajenos del directorio; solo consume esos nombres fijos. La posterior
  carga GPU deberá volver a verificar los bytes que utilice.
- Ambos construyen un candidato privado y publican **solo después de todos
  los cierres exitosos**. Cualquier fallo conserva todos los bytes de `out`,
  incluso cuando ya contiene un modelo válido. La garantía es transaccional
  síncrona en el hilo propietario, no sincronización entre hilos. Un error
  anterior prevalece sobre un error de cierre posterior. Las asignaciones se
  limitan a la carga, con `nothrow`, nunca a la vista o a la evaluación por frame.
- La validación numérica/geométrica compartida reside en `rig_payload_error`;
  el reloj de SRI1 se sigue validando aparte. El productor comprueba también
  la norma de los quaternions **después de redondear a f32**, rechazando un
  valor que cruce la tolerancia 0,001 al serializar. No se relaja el umbral.
  Los ejemplos válidos de SRI1 mantienen exactamente sus hashes.

[Reconstrucción independiente](../tools/qa/locomotion_rig_oracle.py):
`reconstruct_sri2(bytes)` no importa productor ni código runtime. Recupera
campos de perfil, centro/escala, huesos fuente/padres/canales, registros PAL,
índices fuente de las 58 muestras, TR, helpers, vértices/UV/pesos originales,
índices y materiales. `reconstruct_sri2_bundle(files)` exige el conjunto exacto
SRI/texturas en memoria y coteja sus tamaños/CRC antes de devolver el resultado.
El conjunto exacto es una regla de auditoría; el lector de directorio tolera
archivos auxiliares que no consume. Ninguna API acredita por sí sola los hashes
de MDL522/ANM525 ni recupera datos no representados por SRI2.

Evidencia sintética: 59.212 cortes rechazados por el reconstructor, 329 variantes
corruptas rechazadas también por C++, 650 rechazos nativos con salida intacta,
comparación de todos los campos de un paquete producido y 500 actualizaciones
del núcleo usando la vista. 542 pruebas Python y 33/33 CTest por preset Release
y ASan/UBSan. Gates individuales al 80 % para modelo, lector y oráculo;
el cotejo privado A/B y la prueba física siguen pendientes.

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

Matriz de casos requeridos; comprobar los vectores del contrato por sí solo
no acredita las implementaciones ni la fidelidad privada:

| Grupo | Batería obligatoria |
|---|---|
| Solicitudes | 101→113, ID 0/65535, cambio a otro destino en modos 3/5, mismo destino en los tres modos; comparar todos los bytes lógicos de estado/salida tras error |
| Reloj | ticks 0/1/3/máximo, counter=P/uint32 máximo, beta imposible/overflow, cada entrada/salida y wrap en ambos sentidos |
| Pose/atomicidad | lectura que falla en canal 1 después del 2, NaN/Inf, quaternion cero, máscara duplicada/incompleta, padre ausente; caché interpolada y fuente congelada invariable durante modo 3 |
| Lifecycle | pausa en mitad de modos 3/5, 100 redibujos sin avance, R único, L en cada modo, selección simultánea, suspensión con solicitud pendiente y tecla mantenida, tiempo largo/no finito, START con frame ocupado |
| Wire | HL-T4c.2 implementado: magic v1/v2/desconocido, truncamientos, CRC, longitud, reservados, descriptor/rango/canal, material/textura, sobrantes y salida intacta ante fallos; cotejo privado en T4c.3 |
| Fidelidad/rendimiento | A/B con fuentes fijadas, reconstrucción independiente, matrices ≤0,001, sanitizers, cobertura ≥80 % líneas/ramas por módulo nuevo, host/ARM y 60 s por clip/transición en 2DS XL |

No se amplían las tolerancias para cerrar un caso fallido. La precisión f32
de extremos sigue HL06; el NLERP sintético tiene tolerancia 1e-12 en Decimal
convertido a double y 1e-6 para su futuro cotejo float C++. La fidelidad contra
PCSX2 conserva el umbral de matrices 0,001, comprobado aparte.

## HL-T4c.3: publicación y fidelidad privada

El productor autenticado aplica `pcsx2-hl06-f32-v1` a los extremos de SRI2:
XYZ conserva los enteros originales divididos por 32768; productos y sumas
se truncan a f32, el radicando negativo se limita a cero y SQRT se redondea
al f32 más cercano, conservando el signo de W. No normaliza el extremo.
El decoder ANM sin pérdidas conserva sus palabras y quaternion matemático;
SRI1 no cambia. Esta política corresponde al perfil PCSX2 fijado, no a una
emulación general de la FPU PS2 ni a una prueba en hardware PS2.

`publish_heather_locomotion` autentica las fuentes y los descriptores, genera
el paquete y exige reconstrucción antes de escribir. Reutiliza el escritor
privado anclado: directorio externo exclusivo, archivos 0600, directorio 0700,
sin sobrescribir destinos ni seguir enlaces de archivo. Relee los 14 archivos,
compara bytes y reconstrucción, y solo entonces publica `manifest.json`.
Un fallo deja evidencia parcial sin manifiesto final. El manifiesto declara
que la auditoría de poses es separada; la publicación estructural no la acredita.

`tools/qa/locomotion_source_audit.py` compara la reconstrucción con documentos
decodificados de fuentes, sin importar productor ni runtime. Conserva
exactamente enteros de geometría, vínculos, rangos, descriptores, materiales
y píxeles; compara TR, helpers y encuadre en representación f32 canónica.
Los quaternions proceden del oráculo HL06 independiente. No permite reconstruir
todos los bytes MDL/ANM: quedan fuera cabeceras/padding, flags y palabras ANM
originales, muestras/bones/submeshes no seleccionados, morphs, movimiento
mundial, arma visible e iluminación PS2. Los originales siguen conservados.

Cotejo privado cerrado: A/B idénticos, 58×36 TR, 6.943 vértices, 16.566
índices, 49 helpers y 13 materiales/texturas; lector C++ coincide en todos
los campos. 245 poses/8.820 matrices frente a estados fijados dan máximo
0,000514984130859375; 13.968 extremos crudos de quaternion dan máximo
5,960464477539063e-8. Las tolerancias siguen 0,001 y 1e-7, respectivamente.
Cada ventana reinicia el harness desde su fase estable; las poses/cachés se
calculan desde SRI2, nunca se cargan de RAM. Las nueve anclas diagnósticas
permanecen separadas. No es una nueva captura continua ni una prueba de FPS.

560 pruebas Python relacionadas y 33/33 CTest Release/ASan/UBSan por preset
aprobadas; gates individuales de cobertura integrados para publicación y
auditoría, usando solo datos inventados en CI. La integración del presentador
y el build ARM se completan después en HL-T4d; la aceptación multiclips en
2DS XL sigue en HL-T5.
[Evidencias y hashes](../docs/execution/f03-02-heather-locomotion.md#2026-10-26--hl-t4c3-publicación-privada-ab-y-fidelidad).


## Corrección de apertura en SD — 2026-10-26

El lector SRI2 debe unir el directorio y el nombre con una sola barra tanto
si el directorio termina en `/` como si no. Para la raíz usada por el visor,
la primera apertura debe recibir exactamente
`sdmc:/3ds/sh3_heather_probe/heather.sri`; se aplica igual a las texturas.
La regresión inyecta un abridor que compara las rutas literales y rechaza
una barra duplicada. Cubre las dos formas de `sdmc:/3ds/sh3_heather_probe`,
`own`, `own/` y `/`, además de los errores y límites anteriores. El build
`7250f427ffb9` corrige solo esa unión; conserva SRI2, publicación atómica,
recursos y reloj. Gate GCC del lector: 187/187 líneas y 164/166 ramas.
El éxito en host y la compilación ARM no acreditan apertura física: HL-T5
requiere repetirla después del error `open` comunicado por el usuario.


La repetición física de `7250f427ffb9` se confirmó el 2026-10-26: carga y
clips, controles, START, tapa y HOME funcionales. Métricas aproximadas: 29,9 FPS,
10,08 ms Skin+sort, 23,3 ms Submit+wait y 4,32 ms GPU, sin atribución a un
clip/encuadre ni duración. HL-T5c conserva ese detalle pendiente; el núcleo
no incorpora movimiento mundial. [Evidencia](../docs/execution/f03-02-heather-locomotion.md).
