# HM: colocación y movimiento de Heather original

Instancia preparatoria de F06.01/F06.02 y F05.02, posterior a la aceptación
funcional de HL-T5 en `7250f427ffb9`. No cierra G04/G05/F06: primero fija
los datos observables de movimiento, después su ley y finalmente una escena.
El atuendo sigue siendo el original, MDL522 y ANM525 de la edición PAL fijada.

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
No se introduce un controlador provisional con velocidades inferidas.

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
      verificados. Izquierda, giro en marcha y cruce exacto de ±pi pendientes.
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
      **Siguientes unidades:** (1) grabar izquierda/liberación y
      caminar+izquierda/recto/liberación desde 202, verificar semilla y
      controles nativos; (2) capturar escritura de yaw, desplazamiento y
      matriz de cada perfil; (3) observar candidatos distintos en pared y
      esquina, enlazarlos a listas/normal/corrección y publicación del mismo
      ordinal. No contar punteros repetidos ni pasadas como nuevos contactos.
      La grabación está iniciada: semilla con RAM/CPU/ciclo idénticos a 202,
      sin restauración. Pendientes controles del usuario, auditoría posterior
      y espacio para las capturas.
    - [ ] **HM-T2b.7 — Autoridad y contrato.** Seguir los productores de
      velocidad, separar pose local, movimiento del actor y correcciones,
      fijar unidades y aritmética del alcance aceptado. Enumerar exclusiones
      antes de autorizar HM-T3; las muestras actuales no prueban autoridad
      exclusiva del movimiento raíz.
- [ ] **HM-T3 — Contrato y núcleo de movimiento.** Con evidencia HM-T2, fijar
  estado, intención, tick, errores, tolerancias y vectores sintéticos antes
  del controlador C++ puro. Comprobar cadencias distintas, raíz aplicada una
  vez y publicación íntegra ante error. HM05–06; el contacto queda en un puerto
  separado con alcance declarado, sin inventar comportamiento PS2.
- [ ] **HM-T4 — Primera escena compartida.** Seleccionar mapa con geometría,
  materiales, colisión y entrada comprobables; fijar dependencias y presupuesto.
  Integrar Heather en la misma base, cámara de inspección identificada y
  movimiento del perfil aceptado. Probar host/ARM y publicar paquete A/B.
  La habitación completa requiere su propia referencia visual y de navegación.
- [ ] **HM-T5 — Aceptación física.** Entregar build identificado, verificar
  recorrido y límites del perfil, controles/suspensión/salida y medir CPU/GPU.
  Mantener pendientes las clases de contacto, cámaras y eventos no probadas.


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
187 estados nuevos; caminar/parada, giro derecho/liberación, reloj PAL de
2 ticks, suelo/registro y una cadena de contacto poligonal auditados.
Veinte pares SQC2 y catorce pares SW/SWC1 de una instrucción comparados contra
RAM completa; dos ramas con SWC1 en delay slot se cuentan aparte. Cuatro
planos, ocho conversiones a punto fijo, dos sumas residuales XYZ cero y dos
sumas no nulas aisladas. El origen del microajuste X está capturado en una
actualización sin corrección de contacto en sus cuatro retornos; posición y
matriz verificadas. 258 pruebas sintéticas con cobertura individual completa
de seis comprobadores, incluido el inventario geométrico preparatorio de
paredes/esquinas; todavía sin giros nuevos ni contacto de esquina observado.
La aritmética conserva el alcance finito acotado;
no fija una ley universal de PS2. Se conserva
la discrepancia de +54 ciclos frente a HL y el rechazo inicial de la predicción
del extremo de consulta con truncamiento. Misma suma y operandos originales
coinciden entre continuación y paso en la muestra adicional. HM-T2b.5–7
mantienen abiertos ciclos, contactos/giros restantes y
autoridad general; no autorizan todavía HM-T3.
