# CF — Investigación de formas y listas de colisión

2026-10-23. Investigación posterior a IR-T7, sin cambiar su contrato de
registros ni habilitar capacidades físicas del runtime.
[CF-T1–T3 completadas y evidencias](../../execution/f03-04-collision-shapes-research.md).
[CF-T8 completada: variante de 48 bytes y colas dinámicas](../../execution/f03-04-collision-extended-research.md).
[CF-T9 parcial: consultas rechazadas y aceptadas](../../execution/f03-04-collision-runtime.md).

## Requisitos EARS

Como implementador del port, necesito distinguir los registros, las listas
y las primitivas que consume el juego para diseñar un decoder acotado.

- **CF01:** CUANDO se atribuya un campo a una forma, el informe DEBERÁ
  vincularlo con instrucciones del productor o consumidor de la edición
  europea fijada y separar interpretación demostrada de hipótesis.
- **CF02:** CUANDO se recorra una lista, el auditor DEBERÁ comprobar su límite,
  paso y terminación, conservando alias y solapamientos observados sin
  deducir la longitud de la distancia al siguiente puntero.
- **CF03:** CUANDO se relacione un recurso con el escenario, el auditor
  DEBERÁ comprobar su identidad completa y su enlace desde las tablas usadas
  por el consumidor; un nombre o sufijo no bastará.
- **CF04:** CUANDO se contraste una transformación, el informe DEBERÁ indicar
  origen, destino, selección de banco, componentes comprobados, tolerancia y
  muestras; los valores deducidos de la salida no serán una referencia independiente.
- **CF05:** SI una variante, campo o enlace carece de evidencia, el informe
  DEBERÁ mantenerlo pendiente y no convertirlo en semántica física pública.
- **CF06:** MIENTRAS se investiguen las capturas conservadas, el auditor
  DEBERÁ verificar los pins de entrada, preservar los originales y emitir
  solo metadatos; distinguirá control, continuidad y diagnóstico restaurado.
- **CF07:** CUANDO se publique el resultado, el auditor DEBERÁ incluir
  controles negativos en copias de memoria y una reproducción de solo lectura.
- **CF08:** CUANDO se interprete la variante de 48 bytes, el informe DEBERÁ
  vincular cada componente utilizado con su consumidor y contrastar los 293
  registros del corpus fijado A/B; los campos no utilizados por esa ruta
  DEBERÁN permanecer opacos y no se relajará el rechazo del perfil CP v1.
- **CF09:** CUANDO se explique una lista dinámica, el análisis DEBERÁ separar
  registro de punteros, selección del banco, escritura de formas y terminación;
  conservará los solapamientos y las colas procedentes de fases anteriores.
- **CF10:** SI un modelo reproduce una captura sin observar las escrituras
  intermedias, el informe DEBERÁ distinguir compatibilidad del modelo de
  ejecución demostrada; no cerrará inicialización, orden temporal o física.
- **CF11:** CUANDO se compare con capturas, el auditor DEBERÁ fijar código,
  estados, recibos, PC/ciclo y fase; indicará qué componentes compara exactamente
  y cuáles quedan fuera, y verificará que controles incorrectos se detecten.
- **CF12:** CUANDO se capture una consulta de 48 bytes, la evidencia DEBERÁ
  enlazar el recurso completo cargado, registro, grupo/celda/índice y llamada
  con sus argumentos y retorno; una forma presente en archivo no acreditará
  su uso en la escena ni su respuesta física.
- **CF13:** CUANDO se cierre el ciclo de vida de las listas, la evidencia
  DEBERÁ observar selectores, contadores, región de formas y escrituras antes
  y después del cambio de fase, comparar también Y y separar cualquier
  restauración del segmento continuo.
- **CF14:** SI falta la normal, el enlace con el actor o la regla de respuesta,
  la integración DEBERÁ mantener pendientes esas capacidades físicas aunque
  la consulta geométrica o el modelo de ocupación coincidan.

## Diseño y verificación

La investigación separa tres responsabilidades: lectura y custodia de fuentes,
comprobaciones estructurales puras y reconciliación de evidencias. El auxiliar
local de investigación no es un decoder de producción ni forma parte de CI.
Usará estados fijados, ELF/overlay de la ISO privada y las extracciones A/B.
Solo las conclusiones y metadatos se documentarán en el repositorio.

Primero se sigue productor → registro → consumidor. Después se contrasta
recurso completo → tabla de recursos → sublista de índices → primitiva.
Las formas dinámicas y el recurso estático se estudian por separado. No se
presupone equivalencia con la malla visual, daño, activadores o solver.

Los futuros lectores de producción deberán tener contratos propios, errores
tipados, fixtures sintéticos y verificación independiente antes de integrarse
al formato intermedio. Este trabajo conserva IR-T7 y sus paquetes existentes.

## Tareas

- [x] **CF-T1 — Productor y consumidor de listas dinámicas.** Fijar ventanas de
  código; seguir los doce enlaces del overlay, tamaños, campos y terminadores;
  examinar los dos bancos y el control de la fase anterior. CF01/CF02/CF06.
- [x] **CF-T2 — Recurso estático y listas del escenario.** Identificar por
  bytes el recurso consultado, cotejar copias A/B, tablas y referencias;
  registrar variantes y enlaces todavía no observados. CF01/CF03/CF05/CF06.
- [x] **CF-T3 — Reconciliación y límites.** Contrastar capturas, transformaciones
  demostrables y solapamientos; ejecutar controles negativos, publicar el
  comprobante de metadatos y precisar el siguiente experimento. CF02/CF04/CF07.
- [x] **CF-T4 — Contrato del primer decoder de formas.**
  [CP01–CP15](../../../schemas/ps2-cld-polygons-v1.md): perfil poligonal
  indexado, límites, API, errores, conservación opaca, diseño de oráculo y
  gate de cobertura. Dos fixtures propios y 50 vectores materializados,
  comprobados por un auditor local independiente del constructor.
  [Ejecución y límites](../../execution/f03-04-collision-polygons-contract.md).
  RF02.04/RF02.05, CF01–CF07; sin decoder de producción, respuesta física ni G02/G03.
- [x] **CF-T5a — Decoder poligonal puro.** API CP y errores explícitos;
  estructura, coordenadas, terminadores e índices validados con los 50
  vectores originales, sin I/O ni datos privados. 69 pruebas aprobadas,
  incluidas comprobaciones iniciales de tipos, presupuestos, aislamiento y
  vectores bajo `-O`; 100 % de líneas/ramas del módulo. CP01–CP09/CP12/CP13,
  con controles iniciales CP10/CP11.
  [Ejecución y alcance](../../execution/f03-04-collision-polygons-decoder.md).
- [x] **CF-T5b — Batería y oráculo público.** Oráculo stdlib independiente
  del decoder y del constructor, con f32 por signo/exponente/fracción.
  3.159 pruebas del perfil: fronteras, barridos, alias, aislamiento,
  precedencia, metamórficas y sensibilidad; 2.742 buffers y nueve tipos
  inválidos por lector/modo normal y `-O`. Decoder y vectores CF-T4 intactos.
  [Evidencia y trazabilidad](../../execution/f03-04-collision-polygons-verification.md).
  CP01–CP14; no acredita fuentes privadas ni respuesta física.
- [x] **CF-T5c — Integración de calidad.** Oráculo/constructor en Ruff/formato
  y módulo en gate individual ≥80 % líneas/ramas; conservados los gates
  global e IR-T7. Job `quality` reproducido localmente: 8.307 pruebas
  principales aprobadas, 100 % líneas/ramas del decoder, siete controles
  del gate y artefactos cotejados. Sin fuentes privadas ni ejecución de CI remoto.
  [Evidencia y límites de entorno](../../execution/f03-04-collision-polygons-ci.md).
- [x] **CF-T6 — Cotejo privado del decoder.** 285 recursos por copia:
  233 aceptados, 52 no soportados (`CP_NONPOLYGON_UNSUPPORTED`), cero otros
  rechazos; inventario íntegro y vistas/errores cotejados con el oráculo.
  Ambos CLD del carrusel coinciden con RAM y tablas en 30 capturas conservadas.
  643 fuentes reverificadas, 16 controles detectados y repetición idéntica
  normal/`-O`; sin cambios al perfil ni capacidades físicas. CP15/CF03/CF06/CF07.
  [Evidencia y registro detallado](../../execution/f03-04-collision-polygons-private.md).
- [x] **CF-T7 — Extensión intermedia de formas.** Definir primero contrato
  separado, buffer completo/vista, procedencia y reconstrucción; después
  implementar y comparar publicaciones A/B. No modificar el perfil IR-T7.
  [Contrato CPI01–CPI14 y tareas detalladas](../../../schemas/collision-polygons-intermediate-v1.md).
  **CF-T7a completada:** inventario, límites, errores e interfaces; 24 ejemplos
  propios verificados normal/`-O` sin apertura de archivos durante reconstrucción.
  Tres paquetes coherentes y 21 rechazos; controles separados de fidelidad externa.
  [Evidencia y límites](../../execution/f03-04-collision-polygons-intermediate-contract.md).
  **[CF-T7b completada](../../execution/f03-04-collision-polygons-intermediate.md):**
  tres APIs puras, 139 pruebas, cobertura 100 % de líneas/ramas y 3.416
  regresiones aprobadas; ejemplos intactos y reconstrucción sin I/O normal/`-O`.
  **[CF-T7c completada](../../execution/f03-04-collision-polygons-preparation.md):**
  preparador de entradas fijadas, custodia, writer exclusivo y lector de
  directorio; 104 pruebas propias. A/B preparado solo en memoria: 519 archivos
  y manifiestos iguales, 233/52/0.
  **[CF-T7d completada](../../execution/f03-04-collision-polygons-intermediate-verification.md):**
  oráculo independiente, fidelidad externa, 279 pruebas nuevas y gates
  permanentes de los cinco módulos CPI; 8.829 pruebas y gates aprobados
  localmente.
  **[CF-T7e completada](../../execution/f03-04-collision-polygons-publication.md):**
  A/B publicados; 519 archivos y manifiestos idénticos, ocho reconstrucciones
  sin fuentes y cotejo externo íntegro. 233/52/0 y 30 enlaces históricos
  reproducidos; 575 entradas intactas. Cierra el perfil estructural CPI;
  variante de 48 bytes, listas dinámicas y respuesta física siguen pendientes.

- [x] **CF-T8a — Consumidor y campos de 48 bytes.** Seguir la selección del
  grupo 4, argumentos, accesos, cálculo radial/vertical y estructura de salida;
  contrastar dimensiones, componentes opacos, índices y terminadores de las
  copias fijadas. Registrar por separado las otras rutas que llaman al mismo
  consumidor. CF01/CF03/CF05/CF06/CF08.
  Resultado: cilindro vertical finito sustentado por código; 293 registros
  en 52 recursos A/B con dimensiones coherentes. Componentes sin uso y cabecera
  conservados opacos; CP sigue 233/52/0. Sin llamada real de grupo 4 capturada.
- [x] **CF-T8b — Ciclo de bancos y procedencia de las colas.** Localizar reset,
  alternancia, registro y consulta; reconstruir un modelo de ocupación desde
  las dos tablas del overlay y comparar cabeceras/X/Z/W en 28 muestras continuas
  y el diagnóstico separado. Probar hipótesis de limpieza, truncado y ausencia
  de fuentes anteriores. No usar la salida observada para construir la entrada
  esperada ni atribuir al modelo una cronología capturada. CF02/CF04/CF09–CF11.
  Resultado: 216 registros por captura, 192 de fuentes actuales, 20 de las
  anteriores y cuatro cero; 400.896 bytes de cabecera/X/Z/W idénticos en
  29 capturas. Doce recorridos por banco reproducidos, sin truncar a nueve.
- [x] **CF-T8c — Auditoría y siguiente experimento.** Conservar solo metadatos,
  repetir con resultado idéntico, reverificar entradas e inventariar las
  limitaciones. Definir los puntos de captura necesarios para la consulta de
  48 bytes y el cambio de fase antes de un decoder nuevo o solver. CF05–CF11.
  Resultado: 647 entradas reverificadas, 12 controles negativos detectados,
  repetición idéntica y comprobante local. Alcance y siguiente experimento en
  el [informe CF-T8](../../execution/f03-04-collision-extended-research.md).
- [x] **CF-T9a — Preparar captura y seleccionar recurso activo.** Definir
  recibo de adquisición, límites de lectura, correlación llamada/retorno y
  controles de rechazo con fixtures propios; localizar por identidad completa
  un CLD de los 52 candidatos cargado y registrado con grupo 4 no vacío.
  Rechazar selección por nombre y los CLD actuales del carrusel con grupo vacío.
  Separar el proveedor de captura del verificador puro. CF03/CF06/CF11/CF12.
  Resultado: contrato y 38 pruebas sintéticas; siete capturas enlazadas al
  observador/estado. `tp21.cld` completo coincide con A/B y las tablas activas;
  grupo 4 con dos formas, índices 0/1 de celda 0. Auditoría repetida idéntica,
  166 entradas reverificadas. Límite de secuencia e INI no archivados explícitos
  en el [informe parcial](../../execution/f03-04-collision-runtime.md).
- [x] **CF-T9b — Observar consulta de 48 bytes.** Capturar entrada a
  `0x0019F2C0` desde el llamador indexado y retorno `0x001A6E34`, incluyendo
  puntos, parámetro, índice, estado de mejor resultado e indicación/punto de
  impacto. Contrastar éxitos y rechazos del juego sin alterar argumentos;
  inventariar bordes sin cobertura, normal y enlace con actor. CF01/CF08/CF12/CF14.
  Resultado: dos pares rechazados en 34 ciclos con Y fuera de límites y un
  par aceptado en 168 ciclos; dos comprobaciones del llamador conservan un
  resultado previo más cercano. Trece capturas, doce pausas distintas;
  315 entradas reverificadas y auditoría repetida idéntica. No se interpreta
  el punto residual de rechazo. Sustitución por tipo 2, tangencias, tapas,
  degenerados, normal, actor y respuesta física quedan sin cobertura.
- [ ] **CF-T9c — Observar transición y vida de los bancos.** Registrar antes/
  después de reset, avance, copia y consulta durante el cambio de fase;
  identificar inicialización y últimas escrituras de las colas. Contrastar
  todos los componentes, incluidos Y, con entradas independientes. Separar
  continuidad de diagnósticos restaurados. CF04/CF09–CF11/CF13.
  Parcial: reset inicial capturado con contadores ya vacíos; región objetivo
  cero hasta la captura 13. La captura 14 llega por juego normal a etapa
  `0x23`, sala `0xEA`, con una lista registrada por banco. El filtro inicial
  usó `255`, interpretado como hexadecimal por PCSX2; se debe usar `0xff`.
  No se capturó el escritor de inicialización durante ese recorrido.
  La nueva adquisición v2 archiva el INI y valida contextos por slot.
  El filtro corregido permitió los slots 15–17: copia de ocho formas de fila
  4/banco de buffer 0, vector cero, 128 componentes exactos, cola conservada
  y registro en el banco de mundo 1 (contador 0→1). Los slots 18–24 añaden
  fila 2 con Y no nula, ambos bancos y actualización de selector/bits.
  Los slots 25–38 alcanzan una etapa intermedia y la sala posterior sin
  restaurar: tres copias posteriores, colas de 3/7 registros conservadas
  y discrepancias de 1 ULP frente a binary32 host documentadas.
  Los slots 39–47 añaden la fila 11, 12 listas registradas por banco,
  alternancia del buffer y avance que vacía un contador ocupado (12→0),
  conservando punteros y formas. Los slots 48–54 verifican una consulta
  sobre el registro residual 5 de la fila 1: supera ambos filtros, entrega
  cuatro vértices y devuelve rechazo; resultado previo intacto.
  Los slots 55–57 capturan la reinicialización real del overlay tras morir y
  elegir «Continue» en el propio juego: mismo proceso, sin restauraciones,
  segmento distinto del acertijo. Se ponen en cero 17.664 bytes de BSS,
  12.442 antes no nulos, conservando guardas y contadores 12/0.
  El diagnóstico separado autorizado copia el estado 55 y modifica solo
  PC a `0x0019FB30`; conserva todos los demás miembros descomprimidos.
  Dos capturas propias verifican reset 12/0→0/0 en 86 ciclos, selector,
  punteros y formas intactos. No se incorporan a las 57 capturas normales
  ni prueban que el juego invoque naturalmente el reset con ocupación.
  362 pruebas sintéticas y 3.288 entradas auditadas. Escritor de Y residual,
  contacto poligonal aceptado y equivalencia numérica siguen pendientes;
  también la invocación natural del reset ocupado. Los escritores del cambio de
  sala no se deducen de los extremos observados. La carga de ajustes puede
  conservar breakpoints activos pese a mostrarlos desmarcados: los ajenos
  a la consulta se neutralizaron con condición `0`, sin recompilar PCSX2.
  [Escritores Y](../../execution/f03-04-collision-y-writer.md): 23 capturas de
  repetición desde estado 25 intacto. Las SQC2 en `0x001A0D18/30/48/60`
  escriben VF4; ocho pares delimitan un vector por instrucción en dos registros.
  Las copias de fase 5, llamador `0x01EE26B8`, generan las colas de fila 1/
  buffer 1 y fila 2/buffer 0; las cuatro colas finales coinciden con 29/54.
  Fila 2/buffer 1 coincide también con la copia real 21→22. La repetición
  desde estado 24 intacto añade 13 capturas y verifica la llamada previa de
  fila 1/buffer 0, Y=−25: cuatro SQC2, copia de ocho registros, registro de
  lista y selector. Sus tres registros residuales coinciden con 25/29/54.
  467 pruebas auxiliares y 5.079 entradas auditadas. La llamada queda
  identificada; siguiente paso: acotar reescrituras posteriores y escritores
  del cambio de sala. No declarar unicidad del último escritor solo por
  coincidencia de valores entre extremos.
  Desglose del cierre pendiente:
  - [x] **CF-T9c.1 — Atribuir la cola anterior de fila 1/buffer 0.** Capturar
    selección, stores, salida, registro y selector; cotejar los 240 bytes con
    los extremos originales y declarar la restauración. Cumplido con las
    13 capturas de origen, 467 pruebas y dos auditorías idénticas.
  - [ ] **CF-T9c.2 — Acotar reescrituras de las colas anteriores.** Inventariar
    los sitios que pueden escribir sus rangos y las condiciones que los
    habilitan; definir un intervalo de observación y filtros de todas esas
    rutas. Registrar cada llamada o declarar huecos de cobertura. Aceptación:
    una atribución de última escritura debe estar respaldada por cobertura
    de ese intervalo, no solo por igualdad en sus extremos. Una máscara
    aplicada a un bit ya limpio no prueba que la copia quede deshabilitada.
  - [ ] **CF-T9c.3 — Reconciliar el alcance del ciclo de vida.** Enlazar las
    escrituras delimitadas del cambio de sala con la limpieza ya capturada,
    separar reset natural y forzado y trasladar a CF-T9d los límites que
    deban conservarse en el contrato. No cerrar el ticket matriz con rutas
    pendientes ni habilitar respuesta física por coincidencia de bytes.
- [ ] **CF-T9d — Decidir contrato y capacidades siguientes.** Reconciliar
  captura con CF-T8, declarar discrepancias y bordes abiertos; definir contrato
  y oráculo sintético del nuevo perfil antes de su implementación. Mantener
  consulta, almacenamiento y respuesta física como responsabilidades distintas.
  No habilitar normal, deslizamiento, gravedad o daño sin su evidencia. CF05/CF14.
