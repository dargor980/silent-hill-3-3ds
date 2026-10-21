# MR01–MR07 — Metadatos de rutas de dibujo y matriz base

2026-10-20. Investigación acotada de MP-T4/MG-T4, F03.02.
RF02.04/RF02.05/RF02.08, RNF06.01, RNF08.01.

Como desarrollador del port, necesito separar los grupos que consume cada
ruta de dibujo y localizar la matriz base sin convertir campos desconocidos
en índices de textura o transformación por su nombre en un importador.

## Requisitos EARS

- **MR01** WHEN se solicita el sondeo de render THEN el inspector SHALL volver
  a validar la jerarquía MP y leer solo cabeceras, un registro de transformación
  base y sus límites; SHALL NOT leer vértices ni exportar matrices originales.
- **MR02** WHEN interpreta los contadores del prefijo THEN SHALL delimitar cada
  raíz por su contador, conservar por separado la cola de enlaces estructurales
  y rechazar una partición incompleta, duplicada o con cuentas incompatibles.
- **MR03** WHEN localiza la transformación base THEN SHALL seguir el offset
  del área +24 y el desplazamiento relativo del registro +4; SHALL rechazar
  rangos fuera del prefijo, solapamiento, desalineación y registros encadenados
  no soportados por esta instancia.
- **MR04** WHEN inspecciona matriz y límites THEN SHALL rechazar NaN/infinito,
  conservar sus hashes y describir la prueba de matriz afín por columnas;
  SHALL NOT aplicar esa matriz ni declarar equivalencia de coordenadas PS2/3DS.
- **MR05** WHEN registra la palabra de forma +20 THEN SHALL llamarla `mode_word_20`
  y conservar +24 por separado; SHALL NOT tratar el valor como un índice de
  matriz. Los campos antiguos `transform_index_unverified` se conservan solo
  para compatibilidad, con su carácter no verificado explícito.
- **MR06** WHEN ejecuta sobre datos privados THEN SHALL reconciliar
  catálogo/recibo fijados, verificar el conjunto antes/después y publicar
  exclusivamente metadatos después de cerrar el lector.
- **MR07** WHEN informa evidencia THEN SHALL separar observación binaria,
  interpretación estática del ejecutable europeo y captura en ejecución.
  Material, alpha, fidelidad de matriz y comparación PS2 SHALL seguir pendientes
  hasta demostrar sus recorridos completos.

## Diseño y alcance

`map_render_probe.py` es un parser puro sobre el mismo puerto de lectura que MP.
`map_survey.py` lo activa mediante `--render-metadata`; su resultado es aditivo
y no cambia los informes sin esa opción. Se reutilizan catálogo, lector privado
y publicación exclusiva. No hay nueva dependencia de runtime o CI.

Subconjunto: área de 48 bytes, descriptor posterior de 32 bytes, un registro
base con cabecera de 32 bytes, matriz de 64 bytes y ocho vectores de límites
(128 bytes). El registro debe terminar antes del primer grupo. La cabecera
del registro permite hueco alineado antes de la matriz, pero el payload de esta
variante tiene exactamente 192 bytes; una variante distinta se rechaza.
Presupuestos de MP; lecturas individuales máximas de 192 bytes adicionales.

Los cuatro u16 de +64 son total y cuentas en orden de campos +66/+68/+70.
Su correspondencia con las raíces +28/+32/+36 es **+66/+70/+68**.
Cada cuenta tiene que caber en la cadena estructural, y sus prefijos deben
formar una partición exacta de los grupos únicos. No se infiere que una cola
compartida implique que todos sus grupos pertenezcan a ambas rutas.

La matriz se clasifica interpretando sus cuatro vectores consecutivos como
columnas: fila homogénea `(0,0,0,1)`, identidad de la parte 3×3 y traslación
nula/no nula. Es una clasificación de datos; no demuestra todavía la
ejecución de instrucciones VU ni la transformación final.

La nueva lectura de +20 tiene dos pistas estáticas: selección de matriz en una
ruta y codificación de información de visibilidad en otra. No se le asigna una
semántica única, ni se implementan modos adicionales por extrapolación.

## Tareas detalladas

- [x] **MR-T1:** fijar los rangos del ejecutable europeo y documentar qué
  instrucciones vinculan contadores, registro base y palabras de forma.
  Guardar SHA-256 de ventanas y disassembly privado; no usar direcciones
  estadounidenses como direcciones europeas. Requisitos MR05/MR07.
- [x] **MR-T2:** implementar parser puro y opción del coordinador. Probar
  cola compartida, cuentas incorrectas, grupos duplicados/faltantes, registro
  truncado/encadenado, huecos, no finitos, clasificación y lectura corta.
  Requisitos MR01–MR06.
- [x] **MR-T3:** ejecutar sobre copy-a y copy-b; comprobar igualdad de informes,
  límites de exportación y regresión de los contratos MP/MG/TI/GI. Registrar
  comandos, hashes y cobertura local. Requisitos MR06/MR07.
- [x] **MR-T4:** identificar el recurso que llega al banco externo en ejecución,
  comprobar TEX0/CLUT/alpha y transformación del dibujo de estas dos formas.
  Solo entonces adaptar el material y la matriz usados por el visor.
  Requisitos MR04/MR07. MR-T4b–d completan el recorrido de estas dos formas;
  MI-T1–MI-T4 completan la adaptación y confirmación física del visor.
  MP-T4/MG-T4 cerradas para esta instancia, sin generalizar a otras formas.
- [x] **MR-T4a:** preparar sesión aislada y control de la escena disponible.
  Capturar PC/ciclo, área/contador del banco y contexto MAP; identificar el MAP
  completo por hash y comprobar las ventanas de código contra el ELF europeo.
  Registrar restauración de estado y duplicados sin atribuirles avance.
  [Control ejecutado](../docs/execution/f03-02-map-runtime-bank.md): banco vacío,
  MAP distinto y salida sin entrar al bucle. Requisito MR07.
- [x] **MR-T4b:** obtener acceso al MAP objetivo sin depender de una partida
  avanzada, que el usuario no tiene. Identificar solicitud y selección de escena
  en la edición europea; validar recursos y precondiciones antes de ensayar
  una carga en copia privada. Mantenerla identificada como experimento.
  No sustituir la selección del juego por inyección de una textura. Requisito MR07.
  [Carga controlada ejecutada](../docs/execution/f03-02-map-runtime-binding.md):
  montaje por el juego, callbacks y hashes completos; no acredita partida normal.
- [x] **MR-T4c:** con ese MAP cargado, capturar el payload de `0027B770`, comprobar
  tamaño/hash y seguir registro, ordinal, gestor y contexto de formas.
  Capturar descriptor y argumentos CLUT/modo en `001B1350`, retorno de
  `001B5F20` y TEX0 efectivo; rechazar asociaciones ambiguas. Requisito MR07.
  Ambas formas usan el gestor del banco recibido y CLUT 0; argumentos,
  retornos y paquete preparado verificados en la misma sesión controlada.
- [x] **MR-T4d:** vincular el paquete a su consumo GS/VU y contrastar alpha,
  visibilidad y transformación de ambas formas. Registrar evidencia reproducible
  antes de cambiar material/matriz del visor. Requisitos MR04/MR07.
- [x] **MR-T4d.1:** identificar VIF/VU y los buffers usados; comprobar la copia
  de la matriz base, su producto con cámara/proyección y la salida XYZ/STQ de
  los 56 vértices mediante un oráculo independiente con tolerancia fijada.
  [Evidencia](../docs/execution/f03-02-map-draw-state.md): VU0, error XYZ cero
  en las capturas contrastadas; no demuestra equivalencia numérica universal.
- [x] **MR-T4d.2:** distinguir recorte/orientación de ausencia de textura;
  registrar posiciones ensayadas y cualquier intervención de cámara. Describir
  PRIM/ALPHA/TEST y alpha de vértice como estados preparados mientras no exista
  evidencia GS. Ambas formas: 16 candidatos por forma pasan con cámara de
  inspección; d.3 acredita después los estados consumidos.
- [x] **MR-T4d.3:** capturar la emisión de ambas formas y su consumo GIF/GS;
  correlacionar lotes, TEX0/CLUT, mezcla, profundidad y niebla. Volcado v6
  completo: 64 paquetes en dos cuadros; sus vértices coinciden byte a byte
  con la salida VU0 y se verifican los estados efectivos del material.
- [x] **MR-T4d.4:** contrastar píxeles y UV de ambas formas frente al resultado
  original, documentar diferencias y cerrar el requisito antes de adaptar el
  visor. No usar el alpha de un PNG normalizado como prueba de equivalencia GS.
  Reproducción software del volcado original: 16.380 píxeles interiores,
  alpha exacto, error RGB máximo de 1/255; controles opaco, sin niebla y V
  invertida detectados. [Integración MI preparada](../docs/execution/f03-02-material-inspection.md);
  comparación en 2DS XL pendiente.

[Ejecución y evidencia](../docs/execution/f03-02-map-render-metadata.md):
398 pruebas, dos informes idénticos y 15 ventanas del ejecutable europeo.
