# HR01–HR12 — Primera habitación con Heather

2026-10-29. Contrato **HM-T4a**, perfil `heather-hp34-inspection-v1`.
La [selección legible por herramientas](heather-room-profile-v1.json) contiene
identidades y parámetros propios; no contiene mallas, texturas ni formas CLD.
Su estado `specified_not_integrated` no autoriza interpretar la escena como
un build disponible. Continúa [HMN v1](heather-movement-native-v1.md) y
[HM05–06](../docs/specs/sh3-3ds/heather-movement.md).

## Objetivo y decisión

Como usuario, quiero mover a Heather original dentro de una habitación
acotada, para comprobar escala compartida, suelo y barreras antes de añadir
puertas, eventos o combate. Se selecciona **`hp34.map` + `hp34.cld`**, con
`hp34TR.tex` para los dos paneles cuyo material ya está verificado.
La selección es una composición nativa explícita: compartir nombre y origen
espacial no acredita que PCSX2 use ese CLD en la misma fase del mapa.

`hp34` es el candidato menor de los cuatro examinados: 31 formas, 15.882
vértices, 9.300 triángulos y 34 polígonos CLD, sin cilindros. La matriz de
traslación del MAP y el material de las formas 448/928 tienen evidencia
previa. `tp1d` y `tp1e` necesitan ampliar el perfil de transformaciones;
`tpf1` contiene formas de 48 bytes rechazadas por el decoder poligonal.
La [auditoría de selección](../docs/execution/f06-01-heather-room-profile.md)
separa estas observaciones de una validación física.

La primera entrega compuesta usará Heather texturada, los dos paneles con
su material comprobado y **material neutro de diagnóstico en las otras 29
formas**, identificado en pantalla. Se conserva toda la geometría; resolver
sus materiales originales será una tarea separada. No se oculta esta
limitación bajo una afirmación de habitación íntegramente texturada.

## Requisitos EARS

- **HR01** WHEN prepara la habitación THEN el preparador SHALL exigir los
  tres recursos fijados por ID, tamaño y SHA-256, catálogo y recibo de
  extracción; SHALL cotejar las copias A/B sin usar el nombre como identidad.
  IF falta o cambia una fuente THEN SHALL rechazar el paquete completo.
- **HR02** WHEN incorpora a Heather THEN SHALL conservar el atuendo original
  MDL522/ANM525, los clips 101/109/113 y el mapa de huesos/canales SRI2 fijado;
  SHALL NOT sustituirlo por el modelo de juego extra ni por la antigua ANM526.
- **HR03** WHEN transforma un punto THEN SHALL usar unidades originales,
  el modelo del MAP por columnas y una única base/origen/escala de escena;
  SHALL aplicar la matriz de instancia a Heather una sola vez y conservar W.
  IF un recurso necesita una transformación no admitida THEN SHALL fallar
  antes de publicar, sin normalizar cada recurso por separado.
- **HR04** WHEN inicia o reinicia THEN SHALL validar el spawn especificado
  contra suelo y todos los bloqueadores, inicializar espera con ordinal cero
  y exigir liberación de botones. IF el spawn no es válido THEN SHALL
  conservar la escena anterior o mostrar error recuperable con START.
- **HR05** WHEN importa colisión THEN SHALL conservar el CLD completo y
  verificar sus 34 registros referenciados, grupo 4 vacío y celda 0; SHALL
  clasificar explícitamente un suelo, un techo y 32 bloqueadores del perfil.
  SHALL conservar los filtros originales como procedencia sin atribuirles
  semántica de gameplay; ningún registro se omitirá silenciosamente.
- **HR06** WHEN comprueba una traslación THEN SHALL probar todo el segmento
  contra las cajas expandidas y el suelo erosionado, con frontera cerrada;
  IF el barrido toca una barrera THEN SHALL aceptar la posición anterior
  completa, sin avanzar parcialmente ni deslizar. El giro y la animación
  seguirán el contrato HMN. Esta respuesta nativa SHALL NOT presentarse como
  el solver de PS2 ni como una cápsula física original.
- **HR07** IF una consulta tiene estado inicial inválido, Y distinta del
  suelo, datos no finitos, ámbito no soportado o presupuesto excedido THEN
  el adaptador SHALL devolver error explícito sin escribir salida parcial;
  el coordinador SHALL conservar su transacción y pausar según HM-T3d.
- **HR08** WHILE ejecuta el visor THEN SHALL mantener el tiempo fijo,
  prioridades y suspensión HMN13–19; el renderer SHALL observar la última
  instantánea completa sin modificar movimiento, contactos ni reloj HL.
- **HR09** WHEN presenta la escena THEN SHALL identificar la cámara y los
  materiales de diagnóstico, conservar la geometría seleccionada y probar
  el orden de opacos/transparencia con Heather; SHALL NOT inferir materiales
  internos a partir de un índice o reutilizar el único material de vidrio
  para toda la habitación.
- **HR10** WHEN reserva recursos THEN SHALL comprobar los límites del perfil
  antes de reservar, reutilizar buffers y evitar asignaciones por paso;
  IF no cabe una textura o lote THEN SHALL abortar limpiamente, sin eliminar
  superficies, reducir resolución o continuar con datos parciales.
- **HR11** WHEN acepta código de contactos o escena THEN la batería SHALL
  contrastar un oráculo independiente, límites/fallos y replay con fixtures
  propios y exigir ≥80 % de líneas y ramas por módulo nuevo; SHALL separar
  validación host, compilación ARM, cotejo privado y prueba física.
- **HR12** WHEN entrega el build THEN SHALL publicar identidad, custodia A/B,
  recorrido y protocolo de controles/suspensión, y mantener pendientes las
  puertas, eventos, enemigos, audio, cámara PS2 y materiales no verificados.

Trazabilidad: HR01–03/05/09 → RF02.04/RF02.05/RF03.01 y HM05; HR04/06–08 →
RF04.01–04 y HMN; HR10–12 → RNF06.01, RNF07.06–09 y RNF08.01. Los requisitos
de esta instancia refinan esas familias; no cierran sus gates globales.

## Coordenadas, entrada y cámara

Origen compartido **O = (100000, 0, 140000)**. El modelo MAP observado es
`T(O)`; sus posiciones locales no reciben otra traslación. CLD ya contiene
coordenadas de mundo: **no se le suma su campo origin_xz**. La simulación
usa mundo; el adaptador puede restar O para realizar consultas locales.

Entrada elegida: **P = (100275, 0, 140000), yaw = 0**, con avance hacia +Z.
En coordenadas de habitación es `(275,0,0)`. Es un punto creado para esta
inspección, **no una puerta ni un punto de aparición original acreditado**.
Su selección no escribe posiciones en PCSX2 ni requiere una partida allí.

Para render, `B = diag(1,-1,-1)`, escala común `s=0.002`:

```text
mapa:    q = s · B · ((T(O) · p_local).xyz − O · p_local.w)
Heather: q = s · B · ((T(P) · Ry(yaw) · p_skin).xyz − O · p_skin.w)
W final = W de entrada; no dividir ni reemplazar por 1.
```

La rotación alrededor de Z y el centrado/escala individual que usa el visor
SRI aislado **no se reutilizan** para la escena. Las coordenadas del suelo,
instancia y cámara deben pasar por la misma base. No se establece una
conversión de estas unidades a metros.

Cámara inicial propia y fija: ojo local `(275,-1000,-700)`, objetivo
`(275,-550,100)`, FOV vertical 70°, near/far 0,02/12 en unidades de render.
Se transforma con la misma base; el vector arriba mundial es `(0,-1,0)`.
No seguirá ni modificará la pose. HM-T4c verificará encuadre, oclusión y
clipping antes de publicar; estos parámetros no certifican todavía que la
cámara vea toda la ruta. La primera entrega usa esta vista fija y reserva
la cruceta al actor; no mezcla los controles antiguos de cámara con los de
movimiento. Cambiar a cámara móvil necesitará su propia aceptación.

**Refinamiento HM-T4c.1:** el encuadre inicial recorta algunas poses.
Se mantiene este JSON fijado por hash y se añade el
[perfil de render](heather-room-render-v1.json): mismo ojo, objetivo
`(275,-300,100)` y FOV80. [Evidencia](../docs/execution/f06-01-heather-room-scene.md)
conserva el fallo inicial y valida el nuevo encuadre; sigue siendo cámara propia.

## Colisiones admitidas: `static-xz-aabb-stop-v1`

Perfil deliberadamente conservador y plano, distinto de la respuesta PS2:

| Datos seleccionados | Regla nativa |
| --- | --- |
| Grupo 0, registro 0 | Único suelo horizontal, Y=0; contener la huella completa. |
| Grupo 2, registro 4 | Techo horizontal; conservado pero no consultado porque no existe movimiento vertical. |
| Grupo 1, registros 0–3 | Cuatro paredes; proyección X/Z como caja cerrada. |
| Grupo 2, registros 0–25 salvo 4 | 25 bloqueadores: caja envolvente X/Z de los puntos activos. |
| Grupo 3, registros 0–2 | Tres barreras adicionales, también bloqueadoras, sin interpretar `filter_word=4096`. |
| Grupo 4 | Debe estar vacío; formas activas de 48 bytes no soportadas. |

Las 80 listas se validan con CP; en esta fuente solo la celda 0 contiene
referencias, una por registro. El contrato fija selección 0 y variantes 1
con cuatro puntos. Campos cambiados o cantidades/listas discordantes no
se admiten bajo este perfil fijado por hash.

La huella del actor es un **cuadrado alineado X/Z de semiextensión 175**,
independiente del yaw, con guarda adicional de 1 unidad: **R efectivo=176**.
No es el contorno de la malla ni una inferencia sobre el radio universal de
Heather. Cada bloqueador se expande R por cada lado; el suelo se contrae R.
El suelo original y el techo son las únicas excepciones enumeradas. Las
superficies altas y oblicuas restantes bloquean conservadoramente por su caja
proyectada, aunque ello reduzca el área accesible respecto del juego.

Para una consulta válida, probar el segmento `from.xz → requested.xz` contra
las 32 cajas expandidas, incluyendo ambos extremos y tangencias. Un segmento
nulo sirve para validar spawn/estado; no se divide por cero. Suelo convexo
erosionado: ambos extremos deben permanecer estrictamente dentro, con la
misma guarda. Si toca/atraviesa una caja o sale del suelo, `accepted=from`;
si todo queda libre, `accepted=requested` con Y del suelo. El resultado
bloqueado es éxito del puerto, por lo que la animación puede seguir caminando
contra la pared. Un estado inicial ya penetrado es un error, no un permiso
para salir atravesando obstáculos. No hay gravedad, escalones, rampas,
empuje, deslizamiento, depenetración ni selección dinámica de listas.

La comparación analítica de HM-T4a usa fracciones exactas de los f32 fuente.
[HRC v1](heather-room-contacts-v1.md), cerrado en HM-T4b.1, fija predicados
exactos sobre binary32, límites, errores y vectores antes del núcleo C++.
La guarda no se usa como tolerancia para aceptar penetración.

Recorrido propio de comprobación en X/Z local:
`(230,-150) → (320,-150) → (320,400) → (230,400) → (230,-150)`, más la unión
desde el spawn al primer punto. Se certifica el barrido completo, no solo
sus extremos. Es una ruta geométrica disponible bajo este modelo; no una
grabación de controles ni una ruta de juego normal verificada.

## Geometría, materiales y presupuesto

Se conservarán las 31 formas, 15.882 vértices originales y 9.300 triángulos,
incluidos los fondos exteriores a la zona caminable. Los dos paneles usan
la receta MR/MI ya comprobada. Las otras formas empiezan con material neutro
de diagnóstico de dos caras; sus UV/atributos originales se preservan para
el trabajo posterior. No se elimina el techo para facilitar el encuadre.
Los campos de modo observados 1/2 no son índices directos de matrices.

Hay siete bloques internos de 512×512 y uno externo de 256×256. Sus CLUT
declaradas implican **41 MiB** si se expandieran todas las variantes RGBA8;
eso no equivale a texturas activas. Con los 17,25 MiB de Heather serían
58,25 MiB: **no se permite cargarlas todas**. La fase de diagnóstico necesita
las texturas de Heather y la paleta 0 externa (17,5 MiB), más un material
neutro sin textura. El enlace interno posterior debe determinar y deduplicar
solo las variantes efectivamente necesarias antes de preparar el paquete.

Límites de ingeniería de esta entrega, no capacidades oficiales de consola:

| Recurso | Límite / estimación |
| --- | --- |
| Memoria runtime contabilizada | ≤64 MiB, incluyendo recursos GPU/CPU, staging y render targets; medir antes de aceptar. |
| Texturas residentes combinadas | ≤32 MiB; fase diagnóstica prevista 17,5 MiB. |
| Staging de textura | ≤2 MiB, un upload a la vez. |
| Geometría estática preparada | ≤2 MiB; 27.900 vértices expandidos ×36 bytes = 1.004.400 bytes como estimación del VBO. |
| Contactos preparados + scratch | ≤4 KiB, 32 cajas sin asignaciones durante consulta. |
| Controlador y controles | ≤32 KiB según HM-T3d. |
| Simulación | 40 ms/paso, máximo tres pasos por muestra; objetivo de presentación 30 Hz sujeto a medida. |

No se deduce rendimiento de los conteos ni se suma «Submit+wait» a CPU como
si fueran etapas independientes. HM-T5 medirá tiempos y estabilidad durante
60 segundos, diferenciando cada métrica.

## Diseño SOLID y aceptación posterior

El preparador host verifica fuentes y convierte a datos propios de escena;
el módulo geométrico puro resuelve consultas acotadas; un adaptador implementa
`IMovementContacts` sin acceder al renderer. `MovementController` conserva
el reloj, lifecycle y la transacción HM-T3c/d. El adaptador Citro3D presenta
mapa y pose con una sola transformación compartida. El paquete conserva
procedencia y exclusiones; ni dominio ni controlador leen archivos privados.

HM-T4b.1 fija [vectores sintéticos](../tests/fixtures/synthetic/heather-room-contacts-v1.json):
avance libre, bloqueo recto/oblicuo, esquina, tangencia, cruce con extremos
libres, cajas degeneradas, consulta nula, origen trasladado, subnormales,
Y/NaN/Inf, presupuestos y reglas de salida intacta. El oráculo independiente
usa intersección con lados y no importa el solver.
[HM-T4b.2](../docs/execution/f06-01-heather-room-contacts.md) implementa el
núcleo/puerto y verifica atomicidad, memoria, cobertura y ARM.
[HM-T4b.3](../docs/execution/f06-01-heather-room-preparation.md) prepara las
32 cajas/suelo A/B, preserva el CLD y coteja recorrido y negativos con el
oráculo y C++; [formato privado](heather-room-contacts-package-v1.md).
Para integración se compararán replay a
varias cadencias y pausa/reinicio/HOME/tapa, raíz aplicada una sola vez,
contacto bloqueado con animación y fallo de lector/contactos sin estado mixto.

Secuencia detallada en [HM-T4b–d](../docs/specs/sh3-3ds/heather-movement.md).
HM-T4a acepta selección y contrato. HM-T4b acepta el adaptador de contactos;
HM-T4c integra y verifica escena/cámara; HM-T4d empaqueta; HM-T5 requiere
la prueba física. La investigación pospuesta de pared 60 no se reactiva.
