# Heather: reloj nativo y selección de locomoción

Instancia HL de F03.02/F06, posterior a la prueba física HP-T4. El objetivo
es identificar espera, caminar y correr del atuendo original y su reloj,
antes de integrar desplazamiento en una habitación. La inspección actual
conserva clip `0x65`, reloj de 25 evaluaciones/s y build `8f778b6e4960`.

## Requisitos EARS

- **HL01** WHEN se inventaríen descriptores THEN el inspector SHALL fijar
  fuente, dirección, tamaño y SHA; SHALL conservar los siete campos de
  `<HHhHHBB>`, incluidos cantidades cero, discrepancias y byte final.
  IF el bloque es truncado, excesivo, sin terminador exacto o con IDs
  duplicados THEN SHALL rechazarlo sin producir un inventario parcial.
- **HL02** WHEN se compare ELF con RAM THEN el auditor SHALL distinguir
  conversión PAL de velocidad, cambios del juego y campos desconocidos;
  SHALL registrar ambos canales del jugador y no trasladar la acreditación
  del consumidor genérico del caballo al jugador.
- **HL03** WHEN se acredite el reloj THEN la captura SHALL registrar una
  vuelta completa, contador de entrada/salida, ticks, modo, descriptor,
  ciclos EE y orden de reanudaciones, sin restauraciones entre muestras.
  SHALL separar reproducción diagnóstica de arranque nuevo, y tiempo del
  juego de cadencia de presentación o tiempo detenido en el depurador.
  IF una parada de dibujo repite contador/matrices o cambia su máscara THEN
  SHALL conservar ese límite y no contabilizarla como un retorno del consumidor.
  IF el oráculo excede su tolerancia fijada THEN SHALL registrar el fallo sin
  elevar el umbral para aprobar la secuencia.
- **HL04** WHEN se nombre un clip caminar o correr THEN la evidencia SHALL
  asociar entrada normal de mando, selección de ambos canales, recurso,
  transición y pose; una referencia estática SHALL seguir siendo candidata.
- **HL05** WHEN se integre locomoción al visor THEN la implementación SHALL
  mantener lectura, reloj, selección, pose y presentación separados;
  SHALL usar memoria acotada y comprobar pausa, wrap, transición, errores,
  START, tapa/HOME y rendimiento sin reducir el modelo original.
- **HL06** WHEN se contraste precisión con el perfil fijado de PCSX2 THEN
  el oráculo numérico SHALL reconstruir los extremos desde tres palabras i16,
  con productos y sumas float32 hacia cero y raíz float32 al más cercano;
  SHALL conservar el signo de W y el clamp de su radicando. IF la entrada
  no corresponde a tres i16, signo booleano o norma cuadrada ≤1,0001 THEN
  SHALL rechazarla. SHALL mantener separados el oráculo matemático anterior,
  la referencia de precisión del emulador y cualquier afirmación sobre PS2 física.

## Diseño y límites

El inspector puro recibe un bloque ya delimitado y una capacidad de muestras.
Devuelve registros inmutables y observaciones sobre rangos; no lee archivos,
no asigna nombres de acciones, no modifica velocidades y no autoriza una
conversión. Un último registro de doce ceros termina el bloque. Los registros
previos tienen ID único distinto de cero, con máximo 512. Capacidad: 1–4096.
La reconstrucción de cada registro conserva sus doce bytes originales.

Las observaciones separan rango vacío, invertido, fuera del ANM, discrepancia
de cantidad, velocidad no positiva, loop desconocido y byte final no nulo.
La ausencia de observaciones solo significa coherencia de metadatos; no
prueba que el juego seleccione ese clip ni que esté cubierto por el visor.

La adquisición privada verifica ELF y estados fijados y compara ventanas
de código. Cada sesión nueva tiene perfil y recibo propios; nunca se
sobrescriben capturas anteriores. Los recursos permanecen en la raíz privada.
En el PCSX2 fijado, «Cargar desde ajustes» borra las filas del modelo de tabla,
pero no retira los breakpoints internos omitidos. Al cambiar de protocolo se
deben conservar sus direcciones con condición explícita `0`, cargar los ajustes
y comprobar la ejecución. La ausencia de una fila no acredita su desactivación.
Se reutilizan el oráculo Q12 y el reconciliador cuando sus precondiciones se
cumplan; el jugador puede requerir otro contrato para mezcla/canales.

La referencia de precisión es un helper puro de QA, sin dependencia del
decoder ni de RAM. Recibe palabras y signo; no modifica los bytes convertidos
ni cambia el renderer. El cotejo de extremos usa límite absoluto 1e-7 y la
pose conserva 0,001. Los resultados anteriores se conservan como diagnósticos.

La investigación de HL-T3 distingue el descriptor retenido en `+40` del
destino seleccionado en `+44`. Durante una mezcla pueden diferir; el cierre
del modo 3 copia `+44` a `+40`. El nombre histórico `requested` de los recibos
privados se refiere a `+40` y no prueba una solicitud nueva. La auditoría
conserva esos recibos y declara la interpretación corregida por offset.

En el perfil observado, ↑ selecciona `0x6D` (80–103) y ↑ + Cuadrado selecciona
`0x71` (176–199), en el banco 525 y con el modelo original 522. El modo 5
mezcla los dos clips en la misma fase relativa y luego interpola en el tiempo.
El preludio del modo 4 puede conservar una pose interpolada anterior; su
origen no se reconstruye únicamente con el índice de muestra. El
[contrato HLC01–HLC16](../../../schemas/heather-locomotion-v1.md) fija ahora
su integración acotada y los casos rechazados. No acredita respuesta física.

## Tareas

- [x] **HL-T1 — Inventario y contrato.** Implementar inspector y pruebas
  sintéticas independientes; contrastar tabla básica ELF/RAM, enlazar sus
  consumidores e inicialización PAL, registrar excepciones y puntos de captura.
  Salidas: módulo, pruebas, inventario privado y reporte reproducible. HL01–02.
  Completado: 49 descriptores, cuatro estados previos, ocho ventanas de código,
  inspector puro con cobertura individual completa; [ejecución](../../execution/f03-02-heather-locomotion.md).
- [x] **HL-T2 — Espera continua.** En sesión diagnóstica aislada, capturar
  ambos canales y una vuelta completa de `0x65`, sin restauraciones intermedias.
  Cotejar contador previo, ticks, wrap y pose; conservar controles negativos
  de huecos, canal incorrecto y contador posterior. HL02–03.
  - [x] **HL-T2a — Diagnóstico del punto de dibujo.** Conservar 49 estados,
    contrastar código/recursos, ambos contadores y 47 poses comparables; rechazar
    la serie completa al repetirse contador/matrices y cambiar máscara en 49.
  - [x] **HL-T2b — Retornos reales.** Capturar `001DD3F0`, `001DD404` y
    `001DD434`; asociar cada parada a su canal y diferenciar actualización de
    animación, postprocesamiento y presentación. Antes de una nueva serie larga,
    verificar que el actor/contexto se mantiene y presupuestar su almacenamiento.
    Seis retornos de inicialización acreditan canales y postprocesamiento;
    el cambio del banco 526 al 525 se conserva como frontera independiente.
  - [x] **HL-T2c — Precisión de pose.** Localizar los errores de las muestras
    27–35 por hueso/componente y contrastar la aritmética original. Conservar
    el fallo de 0,001082908 frente al límite 0,001 hasta resolverlo con evidencia.
    - [x] **HL-T2c.1:** fijar código y configuración de redondeo; implementar
      referencia f32 pura con vectores sintéticos sensibles al redondeo, signo,
      clamp y entradas inválidas. HL06.
    - [x] **HL-T2c.2:** cotejar extremos y poses de la serie fijada, con
      controles de doble precisión, contador posterior y modo de redondeo.
      Publicar el resultado sin reemplazar el informe fallido. HL03/HL06.
      Referencia f32: 47 poses, máximo 0,000369278; 3.384 extremos,
      máximo 5,960465e-8. Pruebas independientes y gates individuales al 100 %.
  - [x] **HL-T2d — Vuelta completa.** Con el punto de retorno acreditado,
    registrar entradas/salidas, wrap, identidad y orden; comprobar controles
    negativos y oráculo de pose antes de aceptar HL-T2.
    V3-33 y V3-100–166: 67 avances, 41.138 Q12, un wrap; ambas secuencias
    de contador pasan. Las 67 poses y 4.824 extremos pasan con máximos
    0,000399061 y 5,960465e-8. Modelo original 522 y banco 525 fijados;
    ninguna restauración entre muestras. Alcance: clip `0x65` en reproducción
    diagnóstica; no acredita mezcla, locomoción jugable ni reloj físico de PS2.
- [x] **HL-T3 — Caminar y correr.** Observar entrada de mando y transiciones
  espera→caminar→correr→espera; fijar recurso/rangos, velocidad, mezcla y
  desplazamiento del actor por separado. No forzar selecciones para acreditar
  juego normal. HL03–04.
  - [x] **HL-T3a — Protocolo de entrada.** Fijar una escena controlable,
    estado de arma, bindings y lectura de mando; conservar un ancla separada
    y asociar cada acción a una ventana de captura. No reutilizar la serie
    estática como prueba de que Heather responde al mando.
    Entrada del parque, atuendo original y banco de cuchillo 525. Capturas
    179/180 enlazan ↑ con bit `0x1000`; 181/182 enlazan ↑ + J/Cuadrado con
    `0x1800`. Se verifican conexión, fuente normal, flancos y ambos canales.
    Los intentos automatizados sin entrada y el duplicado 168 quedan excluidos.
  - [x] **HL-T3b — Selección.** Capturar espera→caminar→correr→espera mediante
    mando normal; registrar descriptores de origen/destino (`+40`/`+44`), banco completo,
    contadores, modos y ambos acumuladores de mezcla, sin forzar memoria.
    Cobertura confirmada: espera→caminar, caminar↔correr, caminar→espera y
    correr→espera directa. La última selecciona 113→101 en ambos canales al
    liberar ↑/Cuadrado, con ancla de carrera y sin descriptor 109 intermedio.
    Cierre limitado al modelo original 522, banco de cuchillo 525 y ventanas
    observadas; no acredita espera→correr directa ni otros bancos/selecciones.
  - [x] **HL-T3c — Composición.** Contrastar cada rango y los dos canales con
    una referencia independiente; separar traslación del actor, pose local,
    postprocesamiento y blend. Preservar modos aún no soportados como pendientes.
    - [x] **HL-T3c.1 — Poses estables observadas.** Reconstruir desde ANM y
      modelo las capturas 180/182/184 de caminar/correr, usando el contador
      anterior al incremento. 36 matrices por captura; máximo 0,000291.
      No acredita una vuelta completa de cada clip.
    - [x] **HL-T3c.2 — Retorno de caminar a espera.** Contrastar las ocho
      poses consecutivas 169–176, extremos 80→0 y acumulador 1280→3800.
      Máximo 0,000336; contador de clip detenido durante ese tramo de modo 3.
    - [x] **HL-T3c.3 — Mezcla entre movimientos.** Capturar ambos sentidos
      caminar↔correr, contrastar fase compartida y orden de las dos mezclas;
      completar secuencia, salida de modo 5 y wrap sin huecos. Los puntos 183
      correr→caminar y 218 caminar→correr pasan el oráculo de pose; el segundo
      incluye ambos setters 216/217 y máximo 0,000258. No cierran la secuencia continua.
      La reproducción `transitions-replay-v1`, muestras 1–15, acredita ahora
      caminar→correr completa: entrada 3, diez poses de modo 5, salida 13 y
      dos avances estables posteriores; 14 poses, máximo 0,000369 < 0,001.
      La salida avanza dos veces el contador por la llamada recursiva a modo 1.
      Se observó wrap estable en la muestra 2; no acredita wrap dentro de modo 5.
      La serie anterior termina en 19 / slot 240 al cerrarse PCSX2.
      `transitions-replay-v2` repite el registro autorizado en otro perfil:
      16 retornos consecutivos, entrada 3, diez poses modo 5, salida 13 y
      tres avances posteriores. Correr→caminar completa: 15 poses, máximo
      0,000366 < 0,001; 46 negativos de reloj rechazados. La salida también
      avanza dos veces. Las cuatro muestras comunes coinciden en toda la RAM EE,
      pero no se empalman las series. `wrap-replay-v1` añade 16 muestras,
      incluida su ancla restaurada, y 15 avances consecutivos: entrada 2,
      wrap 3, salida 12 y cuatro avances estables. Máximo 0,000369 < 0,001;
      46 negativos de reloj y cuatro negativos específicos de wrap rechazados.
      Entrada ↑/Cuadrado enlazada al registro original sin alterarlo. Alcance:
      banco 525 y los sentidos/ventanas observados, sin generalizar bancos.
    - [x] **HL-T3c.4 — Origen conservado.** Capturar antes y después del
      preludio de modo 4 para espera→movimiento y mezcla interrumpida; fijar
      fracción y pose de origen desde recursos e historia previa. Conservar
      los fallos de la hipótesis de muestra cruda, sin sustituir el origen por
      los cuaterniones finales de RAM ni aumentar el límite de aceptación.
      186–200: ambos preludios, origen 95→96 con fracción 2874/4096 y retorno
      completo a espera; nueve poses, máximo 0,000388. 201–214: inicio desde
      espera e interrupción al soltar ↑; dos poses, máximo 0,000362. Las máscaras
      de 15 y 21 huesos cubren los 36 activos. Alcance: banco 525 y casos fijados;
      no acredita una mezcla sostenida espera→caminar/correr ni generaliza bancos.
    - [x] **HL-T3c.5 — Ciclos sostenidos.** Capturar una vuelta completa por
      clip de caminar/correr con entrada normal mantenida; enlazar todas las
      evaluaciones y contrastar fase previa, ticks, wrap y matrices. Conservar
      aparte los huecos de ordinal y las pausas fuera del consumidor (como 185).
      Reproducción diagnóstica de controles normales grabados: 28 retornos y
      27 avances por clip/canal, un wrap por intervalo; carrera 120258 Q12 y
      caminata 107784 Q12, ambos ≥98304. 54 poses, máximo 0,000389 < 0,001;
      extremos ≤5,960465e-8 < 1e-7 y diez controles negativos rechazados.
      Entrada enlazada con los fotogramas nativos del registro. Una restauración
      declarada al iniciar la reproducción; ninguna dentro de los intervalos.
      El hueco entre ambos intervalos no acredita continuidad de sus transiciones.
    - [x] **HL-T3c.6 — Transiciones sostenidas con espera.** Reutilizar el
      registro normal ya preservado para capturar espera→caminar y
      caminar→espera, con anclas estables, cada actualización de mezcla y su
      salida. Verificar el origen conservado desde la historia previa y los
      recursos, los dos canales, el acumulador de mezcla y el reloj del clip;
      separar el ancla restaurada de las observaciones nuevas. No sustituir
      estas secuencias por las entradas breves/interrumpidas de HL-T3c.4.
      Capturar primero dos ventanas independientes, ordinales candidatos
      81940–81963 y 81996–82020 del registro `normal-controls-v2.p2m2`;
      confirmar sus flancos nativos y revisar cualquier modo no modelado.
      Mantener abiertas las selecciones de HL-T3b que estas ventanas no cubran.
      Cierre: 49 capturas en dos ventanas independientes, 47 poses de 36
      matrices; máximo 0,000415617 < 0,001. Espera→caminar entra en 3 y sale
      en 8; caminar→espera entra en 27 y sale en 35. Orígenes interpolados
      4→5 a 1422/4096 y 80→81 a 2992/4096, reconstruidos desde recursos.
      Se rechazan 261 controles negativos de reloj/pose. Los 49 estados
      enlazan con el registro nativo intacto; offset compatible 0 solo para
      esta traza. Restauración declarada al inicio; ninguna entre capturas.
    - [x] **HL-T3c.7 — Parada directa desde carrera.** Registrar una carrera
      estable con mando normal y retirar la dirección sin un tramo de caminata
      intermedio. Auditar primero los fotogramas nativos, preservando los intentos
      que no produzcan ese flanco. Capturar un ancla estable de carrera, la primera
      selección tras soltar, cada actualización de mezcla y su salida a espera.
      Cotejar ambos descriptores/canales, ticks, fase y origen conservado desde
      ANM525/MDL522; si aparece otro modo, documentarlo antes de ampliar el oráculo.
      Verificar pausa y final del registro, frontera de reproducción, controles
      negativos y hashes; no deducir la transición del nombre del archivo.
      La cobertura de selección corresponde a HL-T3b y el resultado de pose a
      HL-T3c. Solo una secuencia observada y contrastada permite cerrar este caso.
      Completada con direct-run-idle-replay-v1: 25 retornos consecutivos,
      entrada 6, ocho poses modo 3, salida 14 y once avances posteriores.
      24 poses de 36 matrices, máximo 0,000412184 < 0,001 y 136 negativos
      rechazados. Origen 178→179 con fracción 3906/4096; los 25 estados
      enlazan con los controles nativos. Primer intento excluido al pasar por
      caminata; segundo registro preservado intacto y reproducción detenida.
  - [x] **HL-T3d — Cierre.** Publicar informe con continuidad por tramo,
    transiciones observadas y controles negativos. Solo entonces fijar el
    contrato multiclips de HL-T4 y su perfil de pruebas sintéticas.
    Informe de cierre acotado heather-hl3-closure-v1.json: 16 evidencias
    consolidadas, cinco transiciones, vueltas completas de los tres clips y
    límites explícitos. El desplazamiento mundial se registra aparte de la
    pose local; no acredita ley de movimiento, colisiones ni habitación.
    Las restauraciones y huecos de cada serie permanecen declarados.
- [ ] **HL-T4 — Conversión y reproducción.** Definir contrato multiclips y
  de transición con las observaciones anteriores; producir conversiones A/B,
  oráculo de pose, pruebas de reloj/lifecycle y build ARM/emulador. HL01–05.
  - [x] **HL-T4a — Contrato multiclips y de transición.** Fijar perfil
    MDL522/ANM525, descriptores 101/109/113, rangos y unidades Q12/PAL;
    especificar estado de los dos canales, origen conservado, orden de
    interpolación y salidas recursivas de modos 3/5. Definir EARS para solicitudes
    no observadas, interrupciones, pausa y límites de capacidad; no inventar
    equivalencia PS2 para espera→correr directa. Publicar vectores sintéticos
    independientes y matriz de trazabilidad antes de implementar.
    Completado: HLC01–HLC16, SRI2 con 58 muestras y geometría compartida,
    cinco arcos, caché local, canales atómicos y políticas de inspección.
    Treinta comprobaciones de vectores propios mediante racionales/Decimal;
    incluyen controles negativos de fase, wrap, recursión, mezcla y caché.
    Las interrupciones siguen rechazadas en runtime: la observación parcial
    se conserva como vector diagnóstico. Núcleo, lector SRI2 y build pendientes.
  - [ ] **HL-T4b — Núcleo puro de reloj y selección.** Separar avance de fase,
    selección permitida, caché de pose y evaluación; inyectar lector de clips,
    sin I/O, GPU ni dependencias de PCSX2. Memoria acotada, sin asignación por
    fotograma; probar wrap, ticks inválidos, saturación, doble avance de modo 5
    y errores explícitos para combinaciones no soportadas.
    - [ ] **HL-T4b.1 — Planificador escalar.** Crear tipos de perfil, estado,
      solicitud, error y plan de evaluación; validar los invariantes HLC03–07
      antes de leer poses. Probar las cinco entradas, no-op, ambas salidas,
      cada beta, wrap, ticks y overflow con vectores comunes al contrato;
      rechazar combinaciones no acreditadas sin mutación. Sin SDK ni I/O.
    - [ ] **HL-T4b.2 — Evaluador local.** Inyectar acceso inmutable a muestras,
      aplicar orden de NLERP/LERP, preservar la última pose y congelar el
      origen; ensamblar las máscaras antes de componer padres. Probar los
      vectores inventados y la diferencia frente al orden incorrecto. HLC08–09.
    - [ ] **HL-T4b.3 — Transacción y límites.** Publicar estado/caché/matrices
      solo al completar ambos canales. Inyectar fallos del segundo canal,
      datos inválidos y capacidad insuficiente; comprobar salida intacta,
      sizeof del estado/scratch ≤32 KiB y cero asignaciones por update.
      Ejecutar host y sanitizers, conservando regresiones SRI1. HLC07–09/14.
  - [ ] **HL-T4c — Conversión y oráculo A/B.** Empaquetar los tres clips y sus
    descriptores, validar rangos/reconstrucción y repetir conversiones privadas
    A/B. Comparar contra el oráculo independiente con tolerancias existentes;
    rechazar cambios de banco/modelo, referencias fuera de rango y datos truncados.
    - [ ] **HL-T4c.1 — Productor SRI2.** Cotejar fuentes y descriptores PAL,
      compactar 0–9/80–103/176–199 y conservar mapa/canales. Codificar el
      layout exacto con centro/escala comunes, materiales compartidos y recibo
      de correspondencias; pruebas sintéticas sin originales. HLC01–02/13.
    - [ ] **HL-T4c.2 — Lector y reconstrucción.** Implementar lector limitado
      y oráculo independiente del productor; probar secciones truncadas,
      reservados, CRC, rangos, máscaras, tipos y cierre exacto. No publicar
      modelo parcial ni tratar SRI1 como multiclips. HLC13–14.
    - [ ] **HL-T4c.3 — Cotejo privado A/B.** Publicar en destinos exclusivos,
      comparar bytes y selección reconstruida, ejecutar referencias de pose
      con umbrales fijados y registrar datos no representados por SRI2.
      Conservar activos los paquetes físicos previos. HLC01/15–16.
  - [ ] **HL-T4d — Integración y gates permanentes.** Conectar el núcleo con
    controles de inspección y renderer conservando cámara, cuerpo/cara, pausa,
    START/tapa/HOME y modo New fast. Integrar pruebas sintéticas y cobertura
    individual en CI sin assets privados; ejecutar host y build ARM, preparar
    paquete con hashes y criterios físicos de HL-T5.
    - [ ] **HL-T4d.1 — Presentador y lifecycle.** Conectar selección explícita,
      prioridad de controles, 25 Hz y cada update completo; cubrir pausa/paso,
      reinicio, solicitudes simultáneas y recuperación sin tiempo dormido.
      No añadir desplazamiento mundial. HLC10–12.
    - [ ] **HL-T4d.2 — Gates y entrega.** Añadir cobertura individual de los
      módulos nuevos, ejecutar pipeline local pertinente y compilación ARM;
      empaquetar SRI2/texturas/build coherentes y protocolo de 60 s por clip y
      transición, con métricas y controles. La ejecución de CI remoto y la
      validación 2DS XL se registran por separado. HLC15–16.
- [ ] **HL-T5 — Prueba física.** Entregar paquete, verificar hashes y medir
  espera/caminar/correr y controles en New 2DS XL; documentar los límites de
  desplazamiento antes de integrar una habitación. HL05.

HL-T1 no necesita un build ARM ni una modificación del paquete físico.
Las pruebas sintéticas se descubren en el job Python de CI; el inspector
tendrá un gate individual de cobertura, sin requerir originales o PCSX2.
