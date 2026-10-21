# Malla MDL de personaje — contrato candidato v1

2026-10-20. F03.02, después de AI-T5. Recurso seleccionado por identidad:
MDL ordinal 142 de XBG0.MFA, modelo `0x0209`, SHA-256
`120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672`.
Historia: como desarrollador del port necesito recuperar la geometría y sus
vínculos de huesos para reemplazar los ejes por una malla animada verificable.

## Requisitos EARS

- **CM01** WHEN se solicita decodificar el MDL, el pipeline SHALL verificar
  identidad de ISO, contenedor, descriptor y recurso antes de producir salida.
  Los datos originales y derivados SHALL escribirse solo en la raíz privada.
- **CM02** WHEN se interpretan secciones, el decoder SHALL validar límites,
  alineaciones, recuentos, paletas y referencias a huesos/helpers; SHALL
  conservar cabeceras y matrices auxiliares sin atribuir significado a campos
  desconocidos. IF aparece morph o una variante no soportada SHALL rechazarla.
- **CM03** WHEN se carga un paquete VIF de esta variante, el decoder SHALL
  admitir únicamente NOP, STCYCLE y UNPACK V4-32/V4-16/V3-16/V2-16 sin máscara,
  con ciclos de salto soportados y direcciones absolutas. SHALL comprobar
  tamaño, extensión signed/unsigned, RAM de 1024 quadwords y lecturas de
  componentes realmente escritos. No SHALL ejecutar microcódigo ni suplir
  datos ausentes con ceros o datos del paquete anterior.
- **CM04** WHEN se recupera un grupo de vértices, el decoder SHALL preservar
  posición, normal, UV y pesos enteros, hueso primario y helpers utilizados.
  SHALL resolver las referencias dentro de sus paletas y comprobar pesos
  entre 0 y 4096, con suma entre `4096−(influencias−1)` y 4096; no SHALL
  normalizarlos silenciosamente. Este margen conserva el déficit observado
  de 1/2 unidades con 2/3 influencias; CM-T4 confirma su uso sin normalización
  en la muestra de ejecución identificada abajo.
- **CM05** WHEN se recupera la tira, el decoder SHALL comprobar cada dirección,
  conservar las marcas de supresión y construir índices sin salir de la malla.
  SHALL distinguir triángulos emitidos de degenerados y conectores suprimidos.
- **CM06** WHEN se publica el resultado, el reporte SHALL distinguir extracción
  estructural de verificación de skinning en PCSX2 y de prueba en consola.
  La base final 3DS, materiales/texturas del MDL y
  transiciones de daño/muerte SHALL permanecer pendientes hasta tener evidencia.
  La aplicación de helpers verificada en CM-T4 no SHALL generalizarse a otras
  variantes ni presentarse como integración de malla comprobada en consola.

## Diseño y límites

Decoder puro VIF separado del decoder MDL; estructuras inmutables, sin I/O,
Blender, GPU ni dependencias de plataforma. Coordinador por puerto de lectura
ISO existente, writer privado exclusivo compartido. Se reutiliza la validación
de esqueleto y la selección MFA con nombres opacos. No se altera el visor actual.

Perfil inicial: MDL v3 sin morph, hasta 128 huesos, 128 helpers, 256 submallas,
16 MiB por recurso y 16 KiB de memoria VU por paquete. Cada submalla conserva
su partición opaca/blend y referencia de textura, sin afirmar estado GS.
CM-T4 verifica posiciones locales Q4, normales Q12 con signo, UV Q12 sin
invertir V y pesos Q12 para dos submallas del perfil. Se conservan los enteros
y helpers almacenados como autoridad. La composición observada se detalla
abajo; la integración y conversión de base del visor pertenecen a CM-T5.

Referencia primaria consultada, sin ejecutar el plugin:
[import_mdl.py y vu.py de Murugo/Misc-Game-Research](https://github.com/Murugo/Misc-Game-Research/tree/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3),
commit `c088e878544f25d45ea7cf4215613fb5f9638dd4`, licencia MIT.
El código de referencia orienta hipótesis; no sustituye validaciones de rango
ni demuestra la equivalencia con el microprograma del juego.

## Tareas detalladas

- [x] **CM-T1 — estructura y vínculos** (CM01/CM02): inventariar las secciones
  de las 15 submallas observadas; comprobar límites, helpers y paletas; añadir
  fixture propio asimétrico con varios huesos, inválidos y preservación de palabras.
- [x] **CM-T2 — paquetes y geometría** (CM03/CM04/CM05): implementar el subconjunto
  VIF observado; recuperar grupos, pesos y tiras con fixtures signed/unsigned,
  saltos, reinicios de tira, direcciones fuera de RAM y datos no inicializados.
- [x] **CM-T3 — adquisición reproducible y auditoría** (CM01/CM06): decodificar
  dos veces desde la ISO; guardar derivados en carpetas privadas independientes,
  comparar hashes; contrastar componentes con un lector independiente, registrar
  recuentos y límites, ejecutar tests, cobertura, lint y contratos de repositorio.
- [x] **CM-T4 — composición real** (CM04/CM06): contrastar en PCSX2 entradas y
  salidas de vértices representativos rígidos y mezclados; determinar matrices
  de reposo/inversas/helpers, normales y orden de tira. No cerrar por inspección
  estática ni por apariencia de un exportador. Conservar errores cuantificados.
  Cerrada para 125 vértices de las submallas 4/5, cuatro poses de `0x1449`,
  todas las rutas de 1/2/3 influencias y los tres helpers; orden de 38 paquetes
  consumidos por GS. Las demás submallas y variantes no quedan verificadas.
- [ ] **CM-T5 — integración de malla animada** (CM06): tras CM-T4, añadir datos
  acotados al visor, costes CPU/GPU, sincronización y regresiones; compilar con
  SDK fijado, verificar en emulador y preparar nueva prueba física independiente.
  **CM-T5a–d completadas**, build `757b48fd1746`: malla, skinning, lector,
  renderer, tests, CI y entrega privada; **CM-T5e.1 funcional confirmada en
  New 2DS XL**. Lecturas aproximadas CPU/envío/GPU recibidas; CM-T5e.2 mantiene
  pendiente la duración y detalles complementarios del protocolo físico.
  [Desglose EARS y aceptación](../docs/specs/sh3-3ds/character-inspection.md),
  [resultados](../docs/execution/f03-02-character-inspection.md).

Continuación: [CT-T1–T3, imágenes y vínculos del material](ps2-character-materials-v1.md)
completadas; CT-T4 verificará su uso efectivo en PCSX2 antes del visor texturado.

La CI host ya descubre `tests/python` y exige cobertura; esta tarea ampliará esa
batería sin incluir datos originales ni acceso a la ISO en CI. G02/G03 y F03.02
global no se cierran con esta instancia.

Resultados, hashes y alcance de cada comprobación:
[ejecución CM-T1–CM-T3](../docs/execution/f03-02-character-mesh.md) y
[ejecución CM-T4](../docs/execution/f03-02-character-runtime.md).

## CM-T4 — protocolo de contraste en ejecución

- **CMR01** WHEN se inicia la reproducción, el auditor SHALL identificar el
  ejecutable PCSX2, ISO/ELF, estado inicial, MDL/ANM y actor por hash/CRC e
  instancia. SHALL conservar la sesión previa en una ranura nueva. Las
  restauraciones diagnósticas SHALL quedar separadas del ensayo de continuidad.
- **CMR02** WHEN se observa la preparación de dibujo, el auditor SHALL enlazar
  actor, pose, matriz de instancia, paleta y helpers mediante punteros y
  ventanas de código verificadas contra el ELF europeo; SHALL conservar
  entradas/salidas en capturas privadas pausadas, sin sustituir matrices del juego.
- **CMR03** WHEN se contrasta la deformación, el oráculo SHALL distinguir
  vértices rígidos, de dos y de tres influencias, y conservar el déficit Q12.
  SHALL comparar también alternativas incorrectas (normalización, omitir
  helper/inversa y orden de producto) antes de declarar un algoritmo verificado.
- **CMR04** WHEN solo hay evidencia de preparación en EE, el resultado SHALL
  identificarse como tal; CM-T4 no SHALL cerrarse sin salida de vértices
  ejecutada, varias poses, normales y orden de tira comprobados.
- **CMR05** WHEN se separa la deformación modelo de instancia/vista/proyección,
  la implementación SHALL conservar `W = suma(pesos_q12)/4096` o su equivalente
  algebraico; no SHALL forzar W=1 ni normalizar los pesos implícitamente.
  SHALL distinguir la normal lineal de la posición con traslación.

- [x] **CM-T4a — identidad y cadena de matrices EE**: sesión previa preservada,
  reproducción diagnóstica separada, actor/clip/MDL/ANM y código identificados.
- [x] **CM-T4b — paletas y ejecución VU**: matrices, cabeceras y tiras enlazadas;
  salidas reales de posición/normal, microprograma idéntico al ELF en los
  intervalos cargados y orden GS comprobado para las dos submallas.
- [x] **CM-T4c — contraste independiente**: 500 muestras en cuatro poses,
  errores cuantificados y cuatro controles negativos detectados. Oráculo puro
  con 34 pruebas nuevas, 229 pruebas conjuntas aprobadas.
- [x] **CM-T4d — contrato para el visor**: composición, helpers, W, normales,
  tolerancias y límites consolidados; CM-T5 conserva su aceptación independiente.

### Composición verificada para esta muestra

Vectores columna, matrices por columnas: `C = View × Instance`; `C'` copia
la fila Z de C sobre su fila W; `P_b = C' × Pose_b`;
`H_h = P_target(h) × StoredHelper_h`. La primera influencia usa P y las demás
H según la paleta del grupo. El helper aproxima
`inverse(Rest_target) × Rest_base`, pero se utiliza su valor almacenado.
Se mezclan `(position_q4/16, 1)` y `normal_q12/4096` con pesos Q12 originales.
La normal usa solo las tres columnas lineales, sin normalización en esta etapa.

Tolerancias absolutas del contraste: posición4 `1e−3`, normal3 `1e−5` y matrices
`1e−3`; STQ `1e−8 + 2e−6 × abs(referencia)`. Se fijaron tras la exploración,
antes de la auditoría final reproducible. La reconstrucción de matrices de
hueso usa float32 hacia cero acorde al perfil; el oráculo de vértices usa doble
precisión sobre paletas capturadas y no es un emulador numérico completo de PS2.

La tira candidata del decoder coincide con GS; los ADC adicionales de esta
muestra corresponden a caras posteriores según área proyectada y paridad de
tira. La cara frontal de Citro3D, otros estados y el material completo exigen
validación separada. Los resultados no autorizan eliminar ese límite en CM-T5.
