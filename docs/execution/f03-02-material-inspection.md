# F03.02 — Material y modelo preparados para New 2DS XL

2026-10-20. **MI-T1–MI-T4 completadas**. El build `764be66e7762` combina las
dos formas verificadas por MR-T4d, su textura de paleta 0, modelo y material
capturado. Presenta 32 triángulos sobre una cuadrícula opaca propia.
[MI-T4, prueba física](../compatibility/material-inspection.md), confirmada
por el usuario: ambos paneles con transparencia, controles, START, tapa y HOME.
No se declara una escena jugable ni equivalencia general PS2/3DS.

## Implementación

El [contrato EARS y diseño](../specs/sh3-3ds/material-inspection.md) separa:

- `material_inspection.py`: transformación pura y conversión de color/alpha.
- `prepare_material_probe.py`: identidad de recursos/referencia/build y entrega.
- Lectores SGM1/STX1 existentes: formato, límites, CRC y errores de I/O.
- `material_state.cpp`: estados de fondo y vidrio en Citro3D.
- `SceneRenderer`: propiedad RAII, copia de buffers y presentación.
- Composición `SH3_MATERIAL_INSPECTION`: carga ambos archivos antes de GPU.

El modelo afín por columnas se aplica antes del cambio de base `(x,-y,-z)`,
centrado y escala uniforme. Centro mundial después del cambio de base:
`(99999.5,1000.5,-139204)`; escala `0.0034393809114359416`;
destino `(0,0.75,-2)`. El orden de formas es 928, 448, observado en el
cuadro GS contrastado. Cada forma aporta 48 vértices de dibujo.

Los UV usan las palabras originales divididas por 32768, sin invertir V;
se conserva el bit de control en el valor de U. Los RGB de VU0, distintos
por vértice, se convierten con `/128 × 227/256`. Alpha de textura se convierte
a UNORM8 con `round(A×255/128)` y se modula con `253/255`, aproximación de
alpha de vértice `127/128`. No se usan los alphas normalizados del PNG previo.

Citro3D usa filtrado lineal, clamp, RGB `Cs×As + Cd×(1−As)`, sustitución de
alpha destino, GEQUAL sin escritura de profundidad y culling de espalda CCW.
La cuadrícula se dibuja antes con escritura de profundidad. Las posiciones
planas/cara frontal se validan antes de empaquetar, para no aplicar esta
política de inspección a una malla arbitraria.

La luz y niebla son una instantánea de la captura. No se reproducen los
truncamientos intermedios, redondeo de STQ ni filtrado de 4 bits del GS; la
prueba de 1/255 de MR-T4d corresponde al oráculo frente a PCSX2, **no a PICA**.
Los otros tres visores conservan sus modos anteriores.

## Validación

| Capa | Resultado |
|---|---|
| C++ Release | 245/245; incluye 21 escenarios nuevos de material |
| C++ ASan/UBSan | 245/245 |
| Python, suite completa | 3.969 pasan en sandbox; seis casos del supervisor requieren `ps` |
| Supervisor con permiso de procesos | 23/23, incluidos los seis casos anteriores |
| Conversión/preparación del material | 30/30; cobertura combinada de líneas/ramas 96,30 % |
| ARM | Visor nuevo y los tres visores anteriores compilan con GCC 16.1.0 |
| Azahar 2126.2, Vulkan | Ambos paneles, textura/transparencia, cruceta, zoom, reset y START |
| New 2DS XL | Confirmación del usuario: ambos paneles con transparencia, controles, START, tapa y HOME |

Los 3.975 casos Python quedan cubiertos entre la ejecución completa y la
repetición del supervisor. El fallo inicial fue `Operation not permitted`
en `/bin/ps`; no se modificó el supervisor para evitarlo.
Reportes JUnit y cobertura en `build/material-inspection/`.
Ruff y contratos del repositorio pasan. El workflow CI añade build y artefactos
de código del visor; no se afirma una ejecución remota de GitHub Actions.

En Azahar, la cámara pasa de `(0.35,0.35,7.00)` a `(0.55,0.10,4.89)`,
Y aleja hasta 6.05 y B restaura el estado inicial. START vuelve a la lista.
Se probaron además `MISSING` sin geometría y `VERIFY_FAILED` alterando un byte
de la textura, con salida mediante START. La copia de prueba se restauró y
se cotejaron sus cinco archivos con la entrega.
Tapa y HOME fueron confirmados después por el usuario en New 2DS XL.

## Entrega y procedencia

Raíz privada autorizada: `/Users/germancontreras/sh3-private-data/`.

- Referencia `f03-02-material-reference-v1/reference.json`, 5.867 bytes,
  SHA-256 `e4cdb9f7c55d17409d5b1da8b48f706dbfe51440ad0a69716351e305e41c1e37`.
  Se exportó de v5/02 y v5/06 después de repetir la auditoría GS; conserva
  hashes de captura, formas y los informes GS/píxeles.
- Entrega `f03-02-3ds-material-v1/`; manifiesto SHA-256
  `a16da2ef6965bf81868c3475eb27994fab4146a949b68597627888d4139a5b30`.
- Capturas privadas `f03-02-material-native-check-v1/`.
- Preparación desde las extracciones independientes A/B: archivos e informe
  idénticos; CRC/longitudes y hashes comprobados de nuevo.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `geometry.sgm` | 3096 | `ae67b60d1ff8349fc385d1760b42e0edc889423456aa599408751b0ec858d5f6` |
| `texture.stx` | 262168 | `55c90e160f02701a9c246c617d8d15e68284f8eaab9b95d05b9736725192b579` |
| `sh3_material_probe.3dsx` | 206196 | `6e6b8d1cea4ee68b4258ec50a1c5ea10c1db2f22745bf5ac97a38fea29fd9bb9` |
| `sh3_material_probe.smdh` | 14016 | `e469359a8ef54fec07dc330dcbe235fb5a02a87dac81777fccd3665cfcb61638` |
| `sd-card.zip` | 487586 | `a8b2e5f81725e34dd8085c45028c7193ff4f894aaaabcb84bbca02f49728acd9` |

SDK `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
El contenedor compiló sin red y con una copia de código, sin originales.
Manifiesto de 53 archivos de fuente/configuración:
`build/material-inspection/source-manifest.json`, SHA-256
`2b2c347b74ac46fcc2470b0b9bd1787f85cffabf7003c7c976b18b57c1ef8f5d`.
La copia se cotejó con el árbol usado para la entrega.

El script de build es `scripts/build_material_probe.sh`; el preparador es
`python -m tools.pipeline.prepare_material_probe --help`.
Al preparar el ZIP, la SD física «NO NAME» no estaba montada.
El 2026-10-20 se copió el build `764be66e7762` a
`/Volumes/NO NAME/3ds/sh3_material_probe/`: cinco archivos, 486.174 bytes.
Se verificaron tamaños y SHA-256 mediante lectura posterior de la SD contra
el manifiesto de entrega. Se conservaron los visores anteriores y se
retiraron únicamente los archivos auxiliares `._` creados por macOS dentro
de la carpeta nueva. Comprobante privado:
`f03-02-material-native-check-v1/sd-copy.json`, SHA-256
`2d7156eec775718eba60c62c2cb404c0772f09f80ec512e9edff13bb2308ac9e`.
La confirmación posterior del usuario cierra MI-T4 y completa MG-T4 para
estas dos formas. F03.02 sigue abierta para los demás tipos y variantes.

Índice local: `reports/local/f03-02-material-inspection-execution-v1.json`,
2.056 bytes, SHA-256
`5595d91c855f3717dd9272a66584ffeda55616fd2df62a0f2dff24ee9b04690e`.
Conserva los resultados de pruebas y hashes de las seis capturas privadas.
Ese índice previo a la prueba física se conserva sin reescribir sus hashes;
la confirmación posterior está en el protocolo físico enlazado arriba.
