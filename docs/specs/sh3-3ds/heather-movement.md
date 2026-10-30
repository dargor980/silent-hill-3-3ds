# HM: colocación y movimiento de Heather original

Instancia preparatoria de F06.01/F06.02 y F05.02, posterior a la aceptación
funcional de HL-T5 en `7250f427ffb9`. No cierra G04/G05/F06: primero fija
los datos observables de movimiento, después su ley y finalmente una escena.
El atuendo sigue siendo el original, MDL522 y ANM525 de la edición PAL fijada.

**Decisión 2026-10-29:** a petición del usuario se pospone la navegación y
captura de pared 60/hueco 14/60, preservadas hasta C148. La investigación
general HM-T2 continúa abierta, pero deja de bloquear un perfil nativo de
inspección con exclusiones explícitas. [Contrato HMN v1](../../../schemas/heather-movement-native-v1.md).
No se requieren nuevos recorridos en PCSX2 para iniciar ese núcleo.

## Requisitos EARS

- **HM01** WHEN recibe un prefijo de actor delimitado de 128 bytes THEN el
  inspector SHALL conservar los bytes íntegros y exponer tipo, escala3 en
  `+0x14`, posición4 en `+0x20`, giro4 en `+0x30` y matriz16 en `+0x40` por
  columnas. IF la entrada no es bytes inmutables, tiene otra longitud, tipo
  distinto al esperado o componentes no finitos THEN SHALL rechazarla sin
  resultado parcial. El tipo esperado SHALL ser un entero no booleano de
  1 a 65535. Los campos desconocidos SHALL permanecer en el bloque original.
- **HM02** WHEN un campo difiere del perfil de inspección THEN el inspector
  SHALL registrar una observación sin corregir escala, W, giro ni matriz.
  SHALL detectar escala distinta de uno, W de posición distinta de uno,
  X/Z de giro distintos de cero, W de giro distinto de cero, fila afín distinta
  de `(0,0,0,1)` y traslación de matriz distinta bit a bit de posición4.
  Ausencia de observaciones SHALL NOT acreditar rigidez, orden Euler, metros,
  ley de movimiento ni ausencia de colisión.
- **HM03** WHEN audita desplazamiento desde capturas conservadas THEN el
  auditor SHALL cotejar hashes de estados/recibos/informes fijados, identidad
  de actor/recursos, PC, ciclos, ticks, entrada y ordinal. SHALL separar cada
  ventana y restauración y calcular diferencias solo entre retornos consecutivos
  de la misma ventana. SHALL conservar Y y distinguir pose local, matriz de
  instancia y traslación del actor; no usar el tiempo detenido en el depurador.
- **HM04** WHEN propone una ley de movimiento THEN la investigación SHALL
  localizar sus productores, orden de actualización, unidades temporales y
  resolución de contacto; SHALL contrastar entrada, salida y giros por juego
  normal antes de atribuir velocidades constantes al comportamiento general.
  IF solo se ha observado una trayectoria THEN SHALL marcar la ley como
  pendiente y conservar explícitamente los límites del escenario y mando.
- **HM05** WHEN integra movimiento en una escena THEN el controlador SHALL
  aplicar la traslación mundial una vez y conservar la pose local del núcleo
  HL; SHALL separar intención, integración temporal, colisión, cámara y vista.
  SHALL usar una base común para Heather y mapa, sin normalizarlos por separado.
- **HM06** WHEN integra código THEN la batería SHALL cubrir entradas válidas,
  truncamientos, errores, inmutabilidad y controles negativos independientes;
  SHALL medir al menos 80 % de líneas y ramas por módulo nuevo en CI sintético.
  Runtime futuro SHALL comprobar replay a distintas cadencias, límites de
  memoria, pausa, tapa/HOME y START, y distinguir host, ARM y consola física.

Trazabilidad: HM01–03 → RF04.01/RF04.04; HM04–05 → RF04.01–04 y RF03.01;
HM06 → RNF07.06–09 y RNF11.05–09. No se presupone que 25 Hz de inspección
sea por sí solo el contrato temporal completo F04.

## Diseño y decisiones

`tools/inspectors/actor_spatial.py` es un lector puro del bloque ya delimitado.
No accede a archivos, RAM, SDK ni direcciones fijas. Devuelve una estructura
inmutable y observaciones en orden estable. No sigue punteros ni convierte
coordenadas. El adaptador privado extrae el bloque desde estados verificados;
la auditoría compara por separado números y procedencia. Se reutilizan los
lectores de estados/ELF y `CharacterRigid` como comprobación matemática
independiente, sin trasladar la aceptación del caballo al jugador.

La primera auditoría usa las dos ventanas HL de caminar/correr y la de
correr→espera. Los informes HL previos anclan hashes, orden y recursos;
las capturas se releen para obtener escala, giro y matriz. La diferencia
entre posición y traslación de matriz se compara también como bytes, para
no ocultar cero con signo. La comparación trigonométrica se limita a yaw
cuando X/Z son cero, escala unitaria y matriz afín; tolerancia absoluta
`1e-6`, conservando el umbral anterior GC sin ampliarlo. No implica exactitud
EE/VU, soporte Euler general ni root motion acreditado.

El lector, el adaptador de fuentes y el auditor tienen motivos de cambio
separados (SRP). Sus dependencias fluyen desde adquisición hacia datos puros;
ninguna regla usa el SDK (DIP). Entradas estrechas y resultados explícitos
permiten fixtures propios como sustitutos sin cambiar el contrato (ISP/LSP).
No se atribuyen velocidades generales al juego a partir de muestras.
HMN v1 define separadamente un perfil nativo limitado, con magnitudes y
orden basados en las capturas y respuesta de contacto fuera del planificador.

## Tareas y criterios de cierre

- [x] **HM-T1 — Inventario espacial y fuentes.**
  - [x] **HM-T1a:** implementar HM01–02; probar un bloque sintético asimétrico,
    todas las longitudes truncadas, entradas mutables, NaN/inf por sección,
    discrepancias simultáneas, escala/reflexión, negativos de cero con signo
    y conservación íntegra. Gate individual y descubrimiento en CI (HM06).
  - [x] **HM-T1b:** auditar las 56 capturas de ciclos y 25 de parada directa,
    contra informes HL fijados; separar carrera, caminata y parada. Registrar
    deltas por actualización/tick, Y, orientación, matriz y fronteras (HM03).
  - [x] **HM-T1c:** cotejar ELF/RAM del constructor común y callback de Heather;
    localizar llamadas y puntos candidatos para movimiento, registrar lo
    comprobado frente a hipótesis y preparar la captura siguiente (HM04).
- [ ] **HM-T2 — Productores y respuesta observados.** Acotar la escritura de
  posición/rotación, velocidad y corrección de contacto en PCSX2. Contrastar
  pares entrada/salida de caminar, correr, parada y giro. Mando normal, sesiones
  y restauraciones declaradas; fixtures extraídos conservados solo en privado.
  No cerrar sin atribución del movimiento raíz y unidad temporal. HM03–04.
  - [x] **HM-T2a — Primera cadena de escritura y corrección.** Reproducir una
    copia privada de controles normales con sus restauraciones declaradas.
    Verificar ancla, PID, actor, recursos y ordinal; capturar entrada del
    escritor, antes/después de su almacenamiento y retorno derivado de `ra`.
    Comparar posición con salida del callback y entrada/salida del constructor
    de matriz. Atribuir cada diferencia observada al intervalo que la contiene;
    no llamar «colisión» a un cambio sin seguir su productor. Auditar la
    escritura contra RAM completa y operandos, con negativos sintéticos.
    Una muestra acotada no cierra la ley general de HM-T2.
  - [ ] **HM-T2b — Contraste de perfiles y contactos.** Repetir la cadena en
    caminar, correr, parada y giro, separando espacio despejado y contacto;
    localizar productores de velocidad, unidades temporales y contribución
    de pose. Declarar rutas no cubiertas antes de fijar el contrato HM-T3.
    - [x] **HM-T2b.1 — Caminar y parar.** Repetir escritor, SQC2,
      callback, constructor y consumidor en caminar, mezcla hacia espera y
      espera estable. Cotejar RAM completa en cada almacenamiento y publicar
      posición/matriz sin atribuir a la pose el desplazamiento del actor.
      Tres actualizaciones, ordinales 81959/82000/82006, 21 estados auditados.
    - [x] **HM-T2b.2 — Reloj PAL observado.** Capturar argumentos del productor,
      almacenamiento de ticks, división PAL y copia al intervalo de movimiento.
      Enlazar ordinal, fase y fotograma nativo; verificar la ABI de FPR contra
      los headers del ejecutable. Acreditado el caso de 2 ticks / 50; otros
      valores y modos quedan fuera del alcance, sin usar tiempo de pared.
    - [x] **HM-T2b.3 — Giro derecho y liberación.** Reproducir controles
      originales, conservar una frontera de restauración independiente y
      capturar dos ángulos y su parada. Aislar SWC1 de yaw, sus operandos y
      la matriz publicada. Descriptor 107; giro sobre el sitio y liberación
      verificados. Izquierda y giro en marcha se añaden en HM-T2b.6;
      el cruce exacto de ±pi sigue pendiente.
    - [x] **HM-T2b.4 — Suelo y registro de formas.** Seguir consulta vertical,
      resultado tipo 1, normalización, corrector y consumidor en espera y
      carrera. Distinguir el registro `0x001A0120` de la resolución física:
      propietario, contador, callback y copias de formas verificados en ambos
      bancos. No acredita contacto con paredes ni equivalencia del solver.
    - [ ] **HM-T2b.5 — Diferencias de ejecución y redondeo.** Contrastar la
      misma operación/operandos con continuación y paso, sin alterar datos
      de juego. Preservar los +87/+54 ciclos respecto a HL y el rechazo del
      oráculo de extremo superior con truncamiento. No fijar una ley general
      de f32 ni ampliar tolerancias para ocultar estas diferencias.
      La suma con enmascarado de mantisa de PCSX2 coincide con las muestras
      existentes y con el par dinámico `ADD.S` 90/91. La consulta 96 repite
      los mismos operandos originales y obtiene el mismo resultado por
      continuación. Queda pendiente acotar la diferencia de ciclos respecto
      a HL y el alcance aritmético general. No interpretar la
      coincidencia con f32 al más cercano como prueba del modo de redondeo.
    - [ ] **HM-T2b.6 — Contacto horizontal y perfiles restantes.** Identificar
      el consumidor que resuelve pared/esquina; capturar entrada, forma
      aceptada, normal y corrección X/Z por controles normales. Añadir giro
      izquierdo y giro en marcha. Mantener separados consultas sin contacto,
      registro de formas y respuesta física; conservar las fronteras de sesión.
      **Cadena acotada verificada:** `tpf1.cld`, grupo 3/celda 0/índice 134;
      aceptación, lista, dos pasadas de un candidato, cuatro pares SWC1,
      callback, retorno físico y posición anterior del siguiente fotograma.
      RAM del recurso completa idéntica a A/B; su grupo 4 activo sigue fuera
      del perfil intermedio poligonal. Otra ventana verifica cuatro planos
      sin normalizar, ocho conversiones VFTOI4/VITOF4, seis SQC2 y dos sumas
      residuales XYZ cero. Son cuatro llamadas en dos iteraciones de un mismo
      ordinal, no cuatro contactos independientes. **Suma no nula y microajuste
      X verificados:** dos VADD/SQC2 en `0x001A1060/0x001A1064` y una
      actualización completa con registro, dos mitades, cuatro retornos de
      corrección cero, residuo X=1/512 y publicación en posición/matriz.
      El caso histórico 98 conserva su explicación candidata; no se restauró.
      Z no tiene sus sumas aisladas y el residuo Y histórico queda separado.
      **Referencias preparadas:** seis paredes verticales 133–138 de
      `tpf1.cld`, seis aristas compartidas entre planos no paralelos, listas
      y A/B/RAM verificados. 38 pruebas del comprobador geométrico; no
      acreditan esquina física ni amplían el perfil CLD soportado.
      **Giros verificados:** grabación desde 202, final manual 203 y 202
      fotogramas nativos comprobados por paquetes literales. No registró
      liberaciones; no prueba parada. La sesión recuperada tiene dos anclas
      exactas y dos fronteras de restauración declaradas. Slots 206–223:
      izquierda sobre el sitio, caminar+izquierda y caminar recto; tres pares
      SQC2, tres pares SWC1 de yaw y matrices finales verificados. Descriptor
      108 al girar sobre el sitio y 109 en marcha. Ajustes posteriores de Z
      y X/Z delimitados, todavía sin atribución al contacto de esas ventanas.
      **Consulta doble verificada:** 134/138 aceptados simultáneamente, contador
      real 1→2 y cuatro llamadas 2/1/2/1; 138 pasa a tipo −1 en las dobles.
      Normales, dos SWC1 y matriz final auditados. Otra consulta conserva ambos
      con vector idéntico; dos SWC1 adicionales y la matriz final verifican su
      publicación. **Dos llamadas al combinador verificadas:** C02→C03 copia
      inicial, C04→C05 combina dos vectores idénticos; contador 0→1→2, resultado
      y suma VF4 contrastados, RAM completa preservada fuera de salida, contador
      y pila permitida. 37 pruebas del comprobador, además de las 30 de la
      referencia. El retorno C06 coincide en RAM/GPR con 248 y difiere en −34
      ciclos; la causa temporal sigue abierta. Errata del
      filtro histórico de multiplicidad y restauración con diferencia en
      `nextEventCycle` explícitas; sin equivalencia global de trayectoria.
      **Descarte angular verificado:** C07→C08 aísla un SW que cambia 138 de
      tipo 2 a −1; RAM completa fuera del destino, GPR/FPR y ciclo contrastados.
      C09 publica solo el vector de 134, con una aplicación. 26 pruebas del
      intervalo angular estricto; envoltura del ángulo no verificada.
      C10 alcanza la parada final sin operandos distintos bajo el filtro de
      dos candidatos/segunda aplicación; no acredita ausencia general.
      **Nuevo recorrido auditado:** 1.704 fotogramas/61 tramos, final C11,
      un solapamiento ↑+←+→ conservado sin normalizar. Copias y filtros para
      dos a ocho candidatos preparados y cargados. C12 declara una quinta
      restauración; `nextEventCycle` conserva la diferencia 1748→16.
      **Combinación distinta verificada:** C13→C14 combina correcciones
      ortogonales de formas 25/26 en 65 ciclos, contador 1→2 y salida exacta
      hasta C15. C16→C17/C18→C19 aíslan las escrituras X/Z y C20 verifica su
      matriz. **Pasadas intermedias verificadas:** C21 registra la sexta
      restauración; C22–C68 aíslan dos iteraciones, cuatro cuantizaciones,
      cuatro sumas al centro y la resta final. El balance exacto separa
      correcciones X=−22,3125/Z=−4,1875 y residuo de movimiento X=+1/1024.
      El residuo posterior XYZ cero conserva W y contador 2. Los extremos
      C47/C15 y C68/C16 coinciden en RAM/GPR/FPR/VF y difieren en −4/−10
      ciclos; sin equivalencia temporal. Los intervalos escalares de movimiento
      se cotejan por sus extremos, sin nuevo aislamiento de cada ADD.S.
      **Otra rama verificada:** C69 cierra sin coincidencias el tramo final
      bajo los filtros nuevos. C70 declara una séptima restauración para
      examinar todo el recorrido. C71–C73 verifican el descarte de tipo 2
      frente a tipo 1, formas 54/55 y banco 0: rama con SW en delay slot,
      tres ciclos, tipo 2→−1 y una sola corrección publicada al retorno.
      69 pruebas de umbrales y 20 del comprobador nuevo; no cierran `atan2`
      ni envoltura. El bitmask del actor que habilita opuestos se mantiene
      observado, sin forzarlo. C74 cierra el resto sin hits; C75 registra la
      octava restauración y C76 termina la búsqueda de condiciones previas
      sin hits. Cuatro bytes de RAM y diferencias de ciclos quedan explícitos.
      **Eje compartido verificado:** C79–C90 siguen las formas 77/78,
      limitación X, retorno de 63 ciclos y cuantización `(5,75;0;3,6875;2)`.
      La suma intermedia X es inexacta; la referencia de sumas exactas sigue
      rechazándola y esta muestra no discrimina el modo de redondeo.
      C91–C94 verifican la comparación de paralelismo con formas 136/137:
      0,19323 rad supera el umbral y ambos candidatos se conservan.
      C95 alcanza el final sin descartes nuevos. Seis escritores del puntero
      global preservan los bits inferiores o los inicializan a cero, sin
      probar que otros escritores no puedan activarlos.
      C96 y sus 4411 fotogramas quedan auditados; C97 declara la décima
      restauración y C98 cierra la búsqueda sin los descartes vigilados.
      El inventario geométrico de 139 paredes identifica el par colineal
      14/60 como objetivo. La dirección de aproximación puede cambiar
      candidatos/filtros previos, pero no las normales de una pareja fija.
      C99 y los 26446 fotogramas de `parallel-gap-v1` están auditados.
      C101 no detecta el par y queda un fotograma antes del final nativo C102.
      En C102 RAM/CPU decodificada/ciclo coinciden con C99; cinco bytes EE
      distintos siguen sin atribuir. C103 declara la duodécima restauración,
      con diferencia de planificador 82→16 conservada. C104 acredita entrada
      en la zona; C105–C106 verifican pared 14 tipo 1 y contador 0→1, con
      cinco escrituras y RAM completa contrastadas. **Siguiente unidad:**
      reproducir y analizar el recorrido dirigido al hueco: C107–C108 terminan sin
      aceptar la pared 60 ni activar los descartes. C109 recupera una copia
      de C104 autorizada, registra la decimotercera frontera y conserva
      el cambio de planificador 1727→16. Las paredes 12/13 comparten arista
      con 14/60; su efecto dinámico está pendiente. `wall60-gap-v1` parte
      de semilla verificada; C110 conserva su final y sus 10294 paquetes están
      auditados, incluidos 16 solapamientos izquierda/derecha. C111 verifica
      la decimocuarta restauración respecto de esa semilla, con prefijo EE
      exacto. C112–C113 terminan sin aceptar 60/12/13 y el final coincide
      con C110 en RAM/CPU/FPR/VF/prefijo EE y ciclo. C114 registra la
      decimoquinta frontera; C115–C120 verifican una consulta de 60 durante
      el tramo neutro: resultado geométrico 0 y salto que omite incorporación,
      sin cambio de contador, candidatos o actor. C121–C132, excepto C127,
      aíslan el rechazo de límites X/Z y la lectura de flags VU. C133–C135
      verifican una consulta con ↑: quedan 499,9375 de separación en X
      y 98,5 en Z. C136–C137 cierran la búsqueda más cercana sin nuevas
      coincidencias ni pasos de límites observados. Final igual a C110 en
      RAM/CPU/FPR/VF/ciclo, con ocho bytes EE distintos sin atribuir. Contacto simultáneo,
      supervivencia tras filtrado y descartes efectivos siguen pendientes.
      Mantener pendientes la publicación del nuevo caso en posición/matriz,
      la habilitación de opuestos, otras variantes redondeadas y el tipo −2. La captura
      directa de copia, vectores idénticos/distintos y un descarte queda completada;
      El [análisis de acceso](../../execution/f06-01-heather-wall60-access.md)
      define P fuera de contacto; distingue el extremo 24/60 del hueco 14/60.
      La llegada normal por etapas queda **pospuesta por el usuario** en
      C148; no es un requisito para el perfil nativo HMN v1.
      HM-T2b.6 sigue abierta para las demás variantes. No contar registros repetidos ni
      correcciones idénticas como empujes independientes.
    - [ ] **HM-T2b.7 — Autoridad y contrato.** Seguir los productores de
      velocidad, separar pose local, movimiento del actor y correcciones,
      fijar unidades y aritmética del alcance aceptado. Enumerar exclusiones
      antes de declarar equivalencia general PS2; las muestras actuales no
      prueban autoridad exclusiva del movimiento raíz.
      - [x] **HM-T2b.7a — Alcance nativo aceptado.** Fijar magnitudes, orden,
        unidades originales, tick de inspección y exclusiones en HMN v1.
        La autoridad de esta propuesta es la intención; la pose local no
        modifica la posición mundial. No cierra la autoridad general PS2.
- [x] **HM-T3 — Contrato y núcleo de movimiento.** Completado para el perfil
  nativo de inspección HMN v1, con las exclusiones HM-T2 declaradas. Fijar
  estado, intención, tick, errores, tolerancias y vectores sintéticos antes
  del controlador C++ puro. Comprobar cadencias distintas, raíz aplicada una
  vez y publicación íntegra ante error. HM05–06; el contacto queda en un puerto
  separado con alcance declarado, sin inventar comportamiento PS2.
  - [x] **HM-T3a — Contrato acotado.** HMN01–07: estado, intención, errores,
    límites, aritmética nativa y vectores independientes antes del código.
  - [x] **HM-T3b — Planificador puro.** Proponer desplazamiento antes de giro,
    preservar Y y producir matriz por columnas; publicación íntegra ante
    error, aliasing seguro y memoria constante. Probar vectores analíticos,
    ticks agrupados, límites y errores; gate individual ≥80/80 y compilación
    ARM. No consume recursos ni resuelve contactos (HMN01–04/07).
    [Entrega y pruebas](../../execution/f06-01-heather-native-movement.md):
    9/9 CTest por preset Release/sanitizadores; gate GCC 100/100; ARM compilado.
  - [x] **HM-T3c — Contacto y transacción de escena.** Definir puerto mínimo
    para aceptar posición; coordinar propuesta, resultado y pose HL sin
    avance parcial. Reconstruir matriz tras correcciones, aplicar raíz una
    vez y probar fallos de contactos y canales. Conservar exclusiones HL,
    incluido idle→run directo (HMN04–05/08–12).
    - [x] Contrato: consulta repetible sin efectos, XYZ completo y límites,
      rechazo de indisponibilidad/no soporte, reset sin ticks y reentrada.
    - [x] Coordinador: instantánea privada, copia provisional HL, matriz
      reconstruida después de contactos y publicación conjunta sin fallos.
    - [x] Verificación: fallos por lectura en ambos canales, reintentos,
      bloqueo/Y/raíz única, memoria ≤32 KiB, gate individual y ARM.
      [Evidencia](../../execution/f06-01-heather-contact-animation.md):
      12/12 CTest en Release/sanitizadores/GCC; ambos módulos 100/100.
  - [x] **HM-T3d — Presentador y tiempo.** Conectar controles al perfil,
    conservar solicitudes durante mezcla sin congelar el objetivo vigente,
    acumular pasos fijos, descartar tiempo suspendido y comprobar replay
    a distintas cadencias, pausa/paso/reinicio, tapa/HOME/START (HMN06/13–19).
    - [x] Contrato: 40 ms por paso, máximo tres por muestra, descarte de
      intervalos lentos con máximo tres pasos, discontinuidades >1 s, prioridad de
      comandos y liberación de botones. La corrección HM-T5 sustituye el
      descarte completo anterior de intervalos >120 ms.
    - [x] Controlador: última intención pendiente, puente explícito vía
      caminar, continuación durante mezcla y pausa ante errores por paso.
    - [x] Adaptador 3DS: HID, conversión ARM11 con fracción y hooks RAII;
      conserva pausa previa y descarta tiempo de tapa/HOME.
    - [x] Verificación: replay a distintas cadencias, fallos/reintentos,
      botones retenidos, hooks duplicados, reentrada, gates ≥80/80 y ARM.
      [Evidencia](../../execution/f06-01-heather-movement-controls.md):
      14/14 CTest en Release/sanitizadores/GCC; 100 % de líneas en ambos
      módulos, 98,9/88,2 % de ramas. Conexión al bucle real en HM-T4.
- [ ] **HM-T4 — Primera escena compartida.** Seleccionar mapa con geometría,
  materiales, colisión y entrada comprobables; fijar dependencias y presupuesto.
  Integrar Heather en la misma base, cámara de inspección identificada y
  movimiento del perfil aceptado. Probar host/ARM y publicar paquete A/B.
  La habitación completa requiere su propia referencia visual y de navegación.
  - [x] **HM-T4a — Perfil de habitación.** Inventariar recursos y evidencias;
    seleccionar mapa, punto de entrada, unidades, formas soportadas y límites
    de navegación. Fijar cámara y presupuesto antes de integrar.
    [HR01–HR12](../../../schemas/heather-room-profile-v1.md) selecciona hp34,
    spawn propio validado geométricamente, suelo plano y 32 cajas bloqueadoras
    conservadoras; Heather original y vidrio texturados, otras 29 formas con
    material neutro identificado. [Evidencia](../../execution/f06-01-heather-room-profile.md):
    fuentes A/B, oráculo CLD, cinco tramos continuos libres, 340 regresiones y
    auditoría normal/`-O` idéntica. Cámara/runtime/física original no acreditados.
  - [x] **HM-T4b — Contactos de escena.** Implementar el puerto con el perfil
    geométrico seleccionado; verificar suelo, paredes, bloqueo y rechazo de
    formas no soportadas con oráculo independiente y fuentes privadas A/B.
    - [x] **HM-T4b.1 — Contrato numérico y vectores.** Fijar evaluación del
      barrido contra cajas expandidas, límites, errores y atomicidad. Casos
      propios de cruce con extremos libres, tangencia, caja degenerada,
      esquina, consulta nula, origen grande, Y inválida y presupuestos.
      No usar la guarda para tolerar penetración. HR05–07/11.
      [HRC v1](../../../schemas/heather-room-contacts-v1.md): predicados
      exactos binary32, enteros acotados, errores ordenados, copia de bits y
      presupuesto conjunto de 4096 bytes. 96 consultas y 30 preparaciones
      sintéticas contrastadas con oráculo racional por lados, independiente
      del barrido previsto. [Entrega](../../execution/f06-01-heather-room-contacts-contract.md).
      Núcleo, atomicidad runtime, cobertura y ARM se verifican en HM-T4b.2.
    - [x] **HM-T4b.2 — Núcleo y puerto.** Implementar consulta pura acotada,
      respuesta todo-o-nada y adaptador `IMovementContacts`; validar spawn,
      conservar animación al bloquear y pausar sin estado mixto ante error.
      Sin heap por paso, ni SDK/archivos en el núcleo. HR04–08/10.
      [Entrega](../../execution/f06-01-heather-room-contacts.md): 894 casos
      exactos de núcleo/puerto, aliasing y publicación íntegra; 16/16 CTest
      en Release/sanitizadores/GCC, gate de pila adicional, 100/96,4 y 100/100
      de cobertura. Reserva conjunta 3136 bytes; compilación ARM verificada.
    - [x] **HM-T4b.3 — Preparación y cotejo.** Convertir las 32 cajas y suelo
      desde recursos fijados, preservar CLD/procedencia y techo excluido,
      rechazar perfiles discordantes y contrastar A/B con oráculo separado.
      Probar recorrido, negativos y gate ≥80/80; compilar ARM. HR01/05/11.
      [Entrega](../../execution/f06-01-heather-room-preparation.md): paquetes
      privados A/B idénticos y releídos, 34 registros íntegros y 32 cajas,
      spawn/cinco tramos en ambos sentidos, 400 cotejos nativos/oráculo,
      4023 pruebas Python y gates por archivo aprobados; ARM recompilado.
      Datos y render de HM-T4c.1 completados abajo; aceptación física pendiente.
  - [ ] **HM-T4c — Bucle compartido.** Conectar controles/tiempo/suspensión,
    Heather y mapa al renderer; aplicar colocación una vez, preservar pose
    ante errores y comprobar cámara, pausa/reinicio y uso de memoria.
    Perfil diagnóstico c.1/c.2 completado; c.3 permanece como ampliación
    posterior y no bloquea HM-T4d.
    - [x] **HM-T4c.1 — Datos y render compartidos.** Preparar las 31 formas,
      SRI2 original y materiales del perfil diagnóstico; base común y W,
      orden opaco/vidrio/cabello, encuadre y memoria. Identificar las 29 formas
      con material neutro sin sustituirlas por vidrio ni omitirlas. HR02–03/09–10.
      [Evidencia](../../execution/f06-01-heather-room-scene.md): paquetes A/B
      de 26 archivos; 472 cotejos privados y repetición `-O` idéntica;
      encuadre refinado sin recorte en 232 poses muestreadas; presupuesto
      38.33 MiB, gates por módulo y ARM; ampliado por c.2 abajo.
    - [x] **HM-T4c.2 — Bucle y ciclo de vida.** Conectar HM-T3d y contactos,
      cámara fija y entrada; comprobar reset, límites, errores, suspensión,
      entrada retenida y replay. Gates host/sanitizadores/ARM. HR04/08/11.
      [Evidencia](../../execution/f06-01-heather-room-runtime.md): composición
      Citro3D/HID/APT, carga transaccional, HOME+tapa combinados y recuperación;
      12 replays privados a 25/60/143 Hz más repetición `-O`, 76/75 CTest en
      Release/sanitizadores, 418 pruebas Python, gates ≥80/80 y ejecutable ARM.
      Presupuesto 40.33 MiB; empaquetado y medición física pendientes.
    - [x] **HM-T4c.3 — Materiales originales del perfil de inspección.**
      Verificar selección interna, paletas y estados antes de sustituir el
      material neutro; deduplicar sin exceder el presupuesto. Este subperfil
      no bloquea la entrega diagnóstica identificada de HM-T4d. Se integra con
      luz fija y visibilidad del estado capturado, sin fidelidad PS2 completa. HR09–10/12.
      - [x] **HM-T4c.3.1 — Inventario y presupuesto candidatos.** Raíces por
        contador, nueve combinaciones internas y una externa, selectores CSM1,
        deduplicación exacta y auditoría A/B con oráculo GS independiente.
        [Entrega](../../execution/f06-01-heather-room-material-candidates.md):
        44 variantes por copia, 21 495 808 píxeles cotejados, 26.5 MiB de
        texturas con Heather; 353 regresiones, 28 tests propios finales y
        cobertura 100/100. La asociación se verificó después en HM-T4c.3.2.
      - [x] **HM-T4c.3.2 — Selección y estados originales.**
        [Entrega](../../execution/f06-01-heather-room-material-binding.md):
        29 asignaciones preparadas; 26 formas enviadas y tres omitidas por DMA.
        31 780 registros de vértices y 28 cargas de índices/CLUT cotejados;
        estados de alfa, profundidad, wrap, color/niebla y orden documentados.
        90 tests propios, cobertura 100/100 e informe normal/`-O` idéntico.
        Fidelidad de píxeles e integración 3DS pendientes de la siguiente fase.
      - [x] **HM-T4c.3.3 — Integración y entrega.**
        [Entrega](../../execution/f06-01-heather-room-materials.md): SRM2, nueve
        materiales originales, 26 formas visibles y tres omitidas; orden
        interno conservado, mezcla con escritura de profundidad y luz fija.
        49.33/64 MiB; host/sanitizadores/GCC, cobertura ≥80/80 y ARM aprobados.
        A/B idénticos, 16 frames auditados y 12 replays del paquete. Build
        `c3aae59d1a70`, observado en Azahar e instalado en SD: 29 archivos
        releídos y verificados, respaldo conservado y expulsión segura.
        El usuario confirma funcionamiento correcto en consola; HM-T5 parcial,
        sin nuevas métricas ni resultados por caso. Descarte VU por triángulo y fidelidad
        dinámica/píxel completa fuera del perfil.
  - [x] **HM-T4d — Entrega.** Verificar host/ARM, empaquetar A/B y publicar
    build identificado con recorrido, limitaciones y protocolo físico HM-T5.
    [Entrega](../../execution/f06-01-heather-room-delivery.md): build
    `ad84b65cd58d`, ruta SD literal corregida, 7/7 CTest Release/sanitizadores,
    4/4 GCC, 155 Python y gates. ZIP A/B idénticos, 12 replays del paquete
    extraído más repetición `-O`. 20 archivos de aplicación y guía física;
    Instalados y releídos en SD los 20 archivos; expulsión segura confirmada.
    Aceptación física todavía pendiente.
- [ ] **HM-T5 — Aceptación física.** Entregar build identificado, verificar
  recorrido y límites del perfil, controles/suspensión/salida y medir CPU/GPU.
  Mantener pendientes las clases de contacto, cámaras y eventos no probadas.
  Aplazada por el usuario el 2026-10-30 para continuar HM-T4c.3; después
  confirma «prueba realizada, funciona correctamente» en `c3aae59d1a70`.
  Se registra funcionamiento general satisfactorio, sin nuevas métricas ni
  resultados por caso. Se conservan la confirmación de `161090bc9fd5` y las
  observaciones detalladas anteriores, sin cierre de los casos restantes.
  Después de esa confirmación, el usuario vuelve a aplazar expresamente las
  mediciones y pruebas adicionales y solicita seguir con el proyecto.
  Se continúa con [F06.02/heather-turns](heather-turns.md), sin reabrir ahora HM-T5.
  [Protocolo](../../compatibility/heather-room.md): arranque, recorrido de
  100 pasos, pausa/R/L, HOME/tapa, error reversible y START. Medición real de
  memoria/FPS/CPU/GPU pendiente de instrumentación; no inferirla del presupuesto.


## Evidencia HM-T1

[Informe de ejecución](../../execution/f06-01-heather-spatial.md): 81 capturas,
78 pares consecutivos en tres ventanas separadas, ocho ventanas ELF/RAM
coincidentes; matrices de traslación exactas y yaw con máximo 4,69137e-8
(límite 1e-6). Caminar/correr avanzan 28/70 unidades por actualización en
los tramos observados; Y se conserva y aún requiere atribución. 243 pruebas
nuevas, 322 relacionadas; 31/31 líneas y 20/20 ramas, gate en CI.
Al cerrar HM-T1 se localizaron el escritor candidato `0x001DCCE0` y el
constructor `0x001DCBA0` y quedó preparado HM-T2a. La ejecución posterior
se registra a continuación; HM-T1 no modificó el visor.

## Evidencia HM-T2a

[Captura de la primera cadena](../../execution/f06-01-heather-movement-capture.md):
16 estados (dos anclas y 14 paradas de una actualización de carrera), 12
observaciones pequeñas y 11 ventanas ELF/RAM. SQC2 acotada a un único destino
de 16 bytes; avance X=70 y corrección Y posterior dentro de `0x001372D0`.
La matriz publica la posición corregida exacta. 52 negativos/positivos
sintéticos; 26/26 líneas y 2/2 ramas del comprobador local. La publicación
espacial coincide con HL, pero difiere en +87 ciclos EE: sin equivalencia
temporal acreditada. Sigue HM-T2b; sin cambio de visor ni cierre de HM-T2.

## Evidencia HM-T2b parcial

[Contraste de perfiles](../../execution/f06-01-heather-movement-profiles.md):
387 estados nuevos; caminar/parada, giro derecho/liberación, giro izquierdo
y giro en marcha, reloj PAL de
2 ticks, suelo/registro y una cadena de contacto poligonal auditados.
Treinta y cuatro pares SQC2 y veinticinco pares SW/SWC1 comparados contra
RAM completa; tres ramas con SW en delay slot se cuentan aparte. Cuatro
planos, dieciséis conversiones a punto fijo, cuatro sumas residuales XYZ cero y cuatro
sumas no nulas aisladas. El origen del microajuste X está capturado en una
actualización sin corrección de contacto en sus cuatro retornos; posición y
matriz verificadas. 496 pruebas sintéticas con cobertura individual completa
de trece módulos puros, incluidos el lector que distingue tipo y contador,
la referencia de combinación restringida a sumas exactas y el comprobador de
entrada/retorno. Cuatro pares de llamadas se contabilizan aparte de los pares de
instrucciones: 13, 58, 65 y 63 ciclos, copia inicial, vectores iguales,
distintos y con eje compartido. La última reconstrucción observacional
conserva el rechazo de la referencia de sumas exactas.
Una escritura de descarte angular y su retorno verifican 2→−1 y una sola
aplicación. La búsqueda acotada hasta C10 no produjo operandos distintos;
otro recorrido tiene semilla exacta, controles y final C11 auditados.
Su reproducción verifica una combinación ortogonal de formas 25/26 y su
publicación X/Z/matriz. C21–C68 atribuyen las dos iteraciones y cuatro llamadas
del mismo ordinal: balance exacto XYZ (−22,3115234375; 0; −4,1875), con
cuantizaciones, sumas y resta final aisladas. Los intervalos de movimiento se
comparan por extremos. Los equivalentes de C15/C16 conservan RAM y registros,
pero difieren en −4/−10 ciclos. C71–C73 verifican un descarte tipo 2 frente
a tipo 1, formas 54/55 y banco 0: una rama con SW en delay slot y una sola
aplicación al retornar. Las referencias de los otros ángulos están probadas
en sus límites; aún falta observar las rutas de paralelos y opuestos.
C74/C76 alcanzan la parada final sin hits de las variantes restantes; C76
tampoco detecta los requisitos previos vigilados. C76 coincide en RAM y
registros con C69, con −57 ciclos. C74 conserva cuatro bytes distintos sin
explicación causal. La nueva grabación oblicua está auditada y su final C77
preservado. C79–C90 verifican un caso con eje X compartido, límite y
cuantización entre las formas 77/78; no resuelve el redondeo general ni su
publicación en posición. C91–C94 alcanzan la comparación de paralelismo
con formas 136/137 y conservan ambos tipos, 1 y 2. Falta observar el descarte
paralelo efectivo y el de opuestos.
C95 alcanza la parada final sin esos hits. La coincidencia espacial con C77
no implica equivalencia temporal, pues sus PCs y fases son distintos. El
inventario estático acotado de flags no identifica una ruta de activación de
opuestos para Heather. C96 y el recorrido desde C95 están auditados;
C97 declara la décima restauración y C98 llega al final sin los descartes
vigilados. Su extremo espacial coincide con C96, en otra fase de ejecución.
Un inventario de 139 paredes y 9591 pares identifica 14/60 como objetivo
colineal con separación de 116,701171875; no acredita contacto ni acceso.
`parallel-gap-v1` y su final C99 están auditados: 26446 fotogramas,
136 tramos, sin carrera ni direcciones opuestas. C101 llega a la parada
ordinal sin detectar el par; C102 alcanza el final nativo y coincide con
C99 en RAM, CPU decodificada y ciclo, con cinco bytes EE distintos sin
atribuir. C103 declara la duodécima restauración. C104 verifica entrada en la zona
y C105–C106 aceptan e incorporan la pared 14 (tipo 1, contador 0→1).
C107–C108 cierran el recorrido sin aceptar la 60 ni activar los descartes.
Siguen un recorrido dirigido al hueco, contacto simultáneo y supervivencia
tras filtrado; las diferencias EE y de ciclos se mantienen explícitas.
C109 registra la restauración autorizada desde copia de C104, con cambio
1727→16 del planificador. `wall60-gap-v1` tiene semilla exacta respecto de
C109; C110 preserva el final y la auditoría reconstruye todos los controles.
C111 verifica otra restauración, decimocuarta del proceso, con prefijo EE
exacto respecto de la nueva semilla. La geometría adyacente 12/13 está
contrastada. C112–C113 terminan sin aceptar 60/12/13 y el final coincide
con C110 en los dominios comparados. C114 inicia la decimoquinta restauración;
C115–C120 verifican consulta de 60, resultado geométrico 0 y salto sin
incorporación durante el tramo neutro. C121–C132, excepto C127,
aíslan la construcción de límites, los signos X/Z, la máscara y el retorno
0. C133–C135 verifican la aproximación con ↑: 499,9375 de separación en
X y 98,5 en Z; aún no hay solapamiento. C136–C137 cierran la región más
estrecha sin coincidencias adicionales ni pasos del rechazo de límites
observados. Final igual a C110 en RAM/CPU/FPR/VF/ciclo y ocho bytes EE
distintos sin atribuir. No hubo restauración desde C114. El ángulo de aproximación no modifica
las normales de una pareja fija; puede afectar a candidatos y filtros previos.
Dos paredes no paralelas con arista compartida aparecen en la misma consulta;
una se descarta. Otro retorno conserva dos vectores iguales y su publicación
está auditada; la ley general de respuesta de esquina sigue pendiente. Las tres ventanas
de giro izquierdo, giro en marcha y referencia recta tienen matrices auditadas;
la sesión recuperada declara quince restauraciones. C111/C114 coinciden con
su semilla en los dominios contrastados; C109 conserva la discrepancia del
planificador EE frente a C104. No se acredita equivalencia temporal completa.
La aritmética conserva el alcance finito acotado;
no fija una ley universal de PS2. Se conserva
la discrepancia de +54 ciclos frente a HL y el rechazo inicial de la predicción
del extremo de consulta con truncamiento. Misma suma y operandos originales
coinciden entre continuación y paso en la muestra adicional. HM-T2b.5–7
mantienen abiertos ciclos, variantes de contacto, cruce exacto de ±pi y
autoridad general. Desde la decisión del 2026-10-29 no bloquean HM-T3 para
el perfil nativo HMN v1; sí bloquean afirmar equivalencia general con PS2.
