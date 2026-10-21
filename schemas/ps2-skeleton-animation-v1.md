# SA01–SA08 — Primera pareja de esqueleto y animación PS2

F03.02/F03.03. RF02.04, RF02.05, RF02.08, RF04.04; RNF06.01 y RNF08.01.
Historia: obtener una jerarquía y muestras de animación conservando su
procedencia y datos desconocidos antes de definir reproducción o skinning.

## Requisitos EARS

- **SA01** WHEN selecciona una pareja THEN SHALL verificar SHA-256 de ISO,
  contenedor y ambos recursos; recorrer toda la cadena MFA antes de leer
  payloads y seleccionar por ordinal explícito, nunca por similitud de nombre.
- **SA02** WHEN el recorrido usa nombres opacos THEN SHALL conservar sus bytes
  como metadatos, sin decodificación de texto ni uso como rutas de salida.
  La política ASCII previa SHALL seguir siendo el valor predeterminado y
  producir los mismos rechazos/catálogos.
- **SA03** WHEN decodifica el esqueleto THEN SHALL validar versión PS2 3,
  rangos/alineación/no solapamiento, cantidad acotada, matrices finitas y afines,
  padres válidos y ausencia de ciclos; SHALL conservar raíces múltiples y bits
  float32 originales sin asignar nombres anatómicos.
- **SA04** WHEN decodifica ANM THEN SHALL exigir ID coincidente con MDL y una
  receta explícita de tamaño de muestra; consumir exactamente cada muestra y
  todo el recurso; rechazar flags desconocidos, huesos ausentes o datos truncados.
- **SA05** WHEN obtiene una pista THEN SHALL conservar nibble completo, palabras
  de cuaternión y bits originales de traslación; reconstruir W con el signo del
  flag y comprobar valores finitos. El bit alto del nibble SHALL permanecer
  opaco; ausencia de pista/traslación SHALL permanecer explícita.
- **SA06** WHEN publica resultados THEN SHALL comprobar reconstrucción exacta
  de matrices/padres y del ANM completo; producir JSON determinista en un
  directorio privado exclusivo y publicar manifiesto después del cierre de ISO.
- **SA07** WHEN valida la implementación THEN SHALL usar fixtures propios con
  raíces múltiples, traslación float32/float16, signo W, flags dispersos, ciclos,
  límites y errores de I/O; repetir la pareja desde dos aperturas independientes.
- **SA08** WHEN informa aceptación THEN SHALL separar estructura, interpretación
  de referencia y comprobación en ejecución. SHALL mantener pendientes la
  selección del juego, límites de clips, frecuencia, interpolación, aplicación
  de pose y skinning hasta tener evidencia independiente.

## Referencia y diseño

Referencia primaria: importadores PS2 `import_mdl.py`, `import_anm.py` y lector
`PS2/Common/readutil/readutil.py` de Murugo/Misc-Game-Research, revisión
`c088e878544f25d45ea7cf4215613fb5f9638dd4`, licencia MIT. Solo consulta del
formato; no ejecución del plugin ni dependencia de Blender. La tabla de
referencia fija 46 bytes por muestra para ID `0x0209`; ese tamaño no se deduce
del nombre ni se generaliza a otros IDs.

MFA reutiliza el parser único con opción explícita `opaque_bytes`: límites de
sector, tablas, cadena, rangos y solapamientos siguen vigentes. Los nombres
opacos no tienen semántica de path ni unicidad textual; la identidad es
contenedor/bloque/índice. No cambia los catálogos históricos ni promueve XBG0
a formato semánticamente reconocido.

MDL: cabecera de archivo de 32 bytes, ID en +4 y modelo en +20. Cabecera del
modelo de 128 bytes, magic `0xffff0003`, versión 3; +8 apunta a matrices,
+12 cantidad, +16 padres, relativos al modelo. Matrices de 64 bytes por
columnas, padres i8 (`-1` raíz). Máximo 128 huesos, archivo ≤16 MiB.
Solo se decodifican estos rangos; mallas, helpers, morphs y texturas quedan
fuera de alcance. Los valores de matriz se conservan sin llamarles pose
local, inversa o bind pose demostrada.

ANM: ID u32 LE, seguido por muestras de 46 bytes para esta receta. Máximo
4096 muestras y 512 KiB. Cada u32 de flags describe ocho índices consecutivos;
nibble bajo `0,1,2,5,6`. Cero no consume datos. Bit 1 añade XYZ en float32
para raíz o float16 IEEE para hijo; después XYZ de cuaternión i16/32768.
Bit 2 selecciona W negativo; `W=±sqrt(max(0,1-X²-Y²-Z²))`. Se rechaza norma
cuadrada >`1+3/32768` (cota conservadora de cuantización; no se renormaliza).
Bit 3 se conserva sin interpretación. No se permiten pistas fuera del
esqueleto ni bytes sobrantes dentro de una muestra. El límite de muestra
marca el final de grupos presentes; huesos posteriores sin grupo quedan ausentes.

Decoder puro en `decoders/ps2_skeleton.py` y `decoders/ps2_animation.py`,
coordinación por puerto de rangos/hash en `decode_skeleton_animation.py`,
I/O ISO existente y writer privado compartido. La CLI solo publica
`skeleton.json`, `animation.json` y manifiesto; no crea nombres desde el MFA.
No modifica el renderer ni entrega un build nuevo para consola.

## Tareas

- [x] **SA-T1:** habilitar recorrido con nombres opacos y asegurar regresión
  exacta de la política ASCII, límites y fallos tardíos. SA01/02/07.
- [x] **SA-T2:** decoder MDL acotado, jerarquía y conservación de matrices;
  probar bosque, ciclos, rangos y no finitos. SA03/06/07.
- [x] **SA-T3:** decoder ANM con receta 0x0209/46, flags y reconstrucción;
  probar signos, raíces/hijos, pistas ausentes y muestras corruptas. SA04–SA07.
- [x] **SA-T4:** coordinador/CLI, dos aperturas verificadas y bundles privados
  idénticos; auditar la muestra con lectura independiente, hashes, cobertura
  y contratos de repositorio. SA01/06–SA08.
- [ ] **SA-T5:** observar en PCSX2 la pareja y el consumidor para fijar clips,
  tiempos, interpolación y composición de pose; después continuar GC-T4.
  Parcial: SA-T5a/b/c completas; falta SA-T5d. SA08/SR01–SR06.
- [x] **SA-T5a — Asociación:** localizar las direcciones europeas del enlace,
  selector de tamaño y consumidor; capturar la entrada sin pedir cargas ni
  inyectar recursos. Cotejar hashes completos de MDL/ANM, punteros, ID, stride
  y descriptor elegido. Salida: identidad de la pareja y selección inicial
  `0x1449` observadas. SA08/SR01.
- [x] **SA-T5b — Reloj y clips:** contrastar tabla ELF/RAM, conversión PAL,
  contador Q12, límites inclusivos, loop/clamp y ajuste de velocidad.
  Registrar cada modificación controlada y distinguirla de selección por IA.
  Salida: tres clips y diez evaluaciones admitidas; no acredita cadencia
  continua. SA08/SR02/SR04/SR05.
- [x] **SA-T5c — Pose:** comparar las tres matrices de salida con un oráculo
  independiente; fijar NLERP, bosque, producto padre/hijo y offset de reposo.
  Probar alternativas erróneas y fixtures propios sin recursos del juego.
  Salida: tolerancias superadas por SLERP/omisión de padre/muestra más cercana,
  y cumplidas por la composición verificada. SA08/SR03/SR04/SR06.
- [ ] **SA-T5d — Continuidad:** resolver la espera de carga observada y obtener
  una secuencia activa sin restauraciones ni escrituras al huésped. Registrar
  ticks, ciclos, contador, matrices y descriptor del mismo actor a lo largo
  de un wrap; separar frecuencia nominal de cadencia medida. Observar
  transiciones por IA si ocurren; en su ausencia conservarlas pendientes.
  Salida: reporte con duración/cadencia y procedencia de selección, antes de
  presentar la reproducción como equivalente a una partida. SA08/SR05.

[Ejecución](../docs/execution/f03-02-skeleton-animation.md): 3 huesos,
2 raíces, 76 muestras, reconstrucción exacta y dos bundles idénticos;
836 pruebas aprobadas.
[Runtime](../docs/execution/f03-02-skeleton-runtime.md): asociación inicial,
tres clips y diez evaluaciones controladas; 108 pruebas, 31 nuevas.

## Contrato de verificación runtime SR01–SR06

- **SR01** WHEN admite una captura THEN SHALL verificar estado/CRC/PC,
  hashes completos de recursos, identidad del actor y ventanas de código
  contra el ELF fijado. SHALL distinguir una asociación espontánea de una
  selección de descriptor introducida para un control.
- **SR02** WHEN verifica los tiempos de esta pareja THEN SHALL conservar
  velocidad ELF y runtime separadas, comprobar la conversión PAL y evaluar
  el contador Q12 de entrada antes de avanzarlo. SHALL contrastar límites
  inclusivos, loop/clamp, ticks y ajuste de velocidad; no asignar FPS al ANM.
- **SR03** WHEN compara la pose THEN SHALL usar matrices por columnas,
  NLERP por hemisferio y composición `padre × hijo` en espacio modelo;
  conservar raíces independientes y recuperar del MDL el offset del hijo
  sin traslación ANM. SHALL NOT aplicar por analogía la base del visor estático.
- **SR04** WHEN admite la comparación THEN SHALL exigir error absoluto
  ≤`1e-5` en rotación/fila afín y ≤`1e-3` en traslación original, comprobar
  la fila afín y exigir que controles con interpolador/jerarquía incorrectos
  excedan el límite. SHALL conservar los ensayos rechazados con su motivo.
- **SR05** WHEN presenta resultados THEN SHALL separar reloj nominal,
  evaluaciones restauradas y cadencia continua; SHALL mantener explícitas
  las rutas no ejercitadas: transiciones por IA, traslación variable,
  producto escalar negativo runtime, mundo, skinning y base 3DS.
- **SR06** WHEN valida el oráculo THEN SHALL usar fixtures analíticos propios
  independientes del decoder, filesystem, emulador y SDK; incluirlos en el
  job Python existente sin originales. Los estados y recursos SHALL
  permanecer en la raíz privada; los informes públicos solo contienen
  identidades, magnitudes de error y metadatos.

Diseño: `tools/qa/animation_pose_oracle.py` contiene operaciones matemáticas
puras y `ClipStep` inmutable; no se integra todavía en el motor o exportador.
El arnés local de captura/restauración y el auditor coordinan PINE/estados e
identidades por separado. Su alcance es avance positivo de un único clip,
sin overflow del incremento i16 ni múltiples vueltas en una evaluación.
Los datos ANM conservados y los decoders SA-T1–SA-T4 no cambian.
