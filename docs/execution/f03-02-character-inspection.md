# F03.02 — Malla animada integrada en el visor

2026-10-20. **CM-T5a–d completadas; CM-T5e.1 funcional aprobada por el usuario;
CM-T5e.2 medición pendiente.**
Build **`757b48fd1746`**, aplicación **SH3 character inspection**.
Se dibujan las 15 submallas de `0x0209` con el clip `0x1449`: 1.455 vértices
únicos y 1.113 triángulos. [EARS, diseño y tareas](../specs/sh3-3ds/character-inspection.md)
y [protocolo para New 2DS XL](../compatibility/character-inspection.md).

El sombreado dorado es propio de inspección, con dibujo de dos caras. Los
materiales/texturas originales, colocación mundial y transiciones de daño
`0x144A` y muerte `0x144B` permanecen pendientes. La comparación directa con
VU/GS de [CM-T4](f03-02-character-runtime.md) cubre las submallas 4/5;
el contraste host de las otras trece no amplía esa evidencia de PCSX2.

## Implementación y presupuesto

- `character_inspection.py` convierte a SCM1 sin perder enteros, UV, pesos,
  helpers ni índices. `prepare_character_probe.py` comprueba SHA-256 de fuente,
  continuidad, CM-T4 y build; las preparaciones A/B producen la misma entrega.
- `inspection_character.cpp` valida cabecera, tamaño exacto, CRC, contadores,
  matrices afines, límites y referencias; publica el modelo solo al completar
  lectura y cierre. La carga usa memoria acotada fuera de la pila de 3DS.
- `character_skinning.cpp` mantiene el cálculo puro: paletas
  `Pose_target × StoredHelper`, mezcla Q4/Q12 sin normalizar pesos, normales
  lineales y posición homogénea. Las traslaciones de presentación multiplican W.
- `IPoseScene` permite reutilizar `AnimationProbe` para ejes y malla. El
  adaptador `SkeletonPresenter` conserva el visor anterior; el dominio no
  depende de archivos, Citro3D ni controles. Se mantienen reloj, A/R/L,
  cámara y ciclo de vida probados, con responsabilidades separadas.
- `CharacterRenderer` recibe posición float4 y color float3. Su shader usa W
  en la proyección; espera GPU antes de reutilizar el buffer y vacía caché
  antes de dibujar. No asigna memoria ni lee archivos por cuadro. La
  destrucción espera GPU antes de liberar recursos y finaliza antes de gfx.

Se conservan 1.455 vértices únicos durante skinning y se expanden 3.339
vértices para **un draw call**, **93.492 bytes de subida por dibujo**.
Los buffers CPU persistentes tienen capacidad de 2.048 vértices deformados
(57.344 bytes) y 4.608 vértices de dibujo (129.024 bytes). El buffer lineal GPU
usa los 93.492 bytes efectivos. Estas cifras excluyen modelo, framebuffers,
command buffer y bibliotecas; no son una medición de RAM total.

El encuadre usa una esfera conservadora para las rotaciones interpoladas.
La primera inspección en Azahar mostró el modelo invertido; la revisión v2
añade una rotación de presentación de 180° sobre X, de determinante +1,
también aplicada a la normal de sombreado. Conserva la deformación original
antes de presentar. La base mundial definitiva y el material PS2 no se deducen
de esta corrección visual. La entrega v1 queda preservada.

Se muestran tres costes: `Skin CPU` incluye deformación, expansión,
validación y sombreado, pero no evaluación de pose; `Submit+wait` incluye
validación, espera de cuadro/GPU, copia, flush y envío; `GPU previous` procede
de Citro3D. No deben sumarse como etapas independientes ni interpretarse
`Submit+wait` como tiempo puro de transferencia. La sincronización se contrastó
con el [código de renderqueue de Citro3D](https://github.com/devkitPro/citro3d/blob/master/source/renderqueue.c)
y las cabeceras del SDK fijado.

## Validación

| Capa | Resultado y alcance |
|---|---|
| Python | 486/486 de conversión, preparación, skinning y regresiones relacionadas; no es toda la suite Python del repositorio |
| Cobertura de los dos módulos nuevos | 96,83 % combinando líneas y ramas |
| C++ Release | 270/270 antes del ajuste visual; 18/18 afectados repetidos tras el ajuste |
| C++ ASan/UBSan | 270/270 antes del ajuste visual; 18/18 afectados repetidos tras el ajuste |
| Oráculo de wire independiente | 21 corrupciones, tres fallos stdio y 12 comparaciones numéricas asimétricas |
| Dobles SDK | 16 escenarios, incluidos fallos por etapa, sincronización/flush y 1.000 actualizaciones sin asignaciones del adaptador |
| Datos privados frente a oráculo independiente | 53 poses × 1.455 vértices = 77.115 comparaciones; enteros/helpers/índices preservados exactamente |
| ARM, GCC 16.1.0 | Nuevo visor compilado; los cinco visores anteriores compilan con la separación IPoseScene |
| Azahar 2126.2, Vulkan | Dibujo, reproducción, A/R/L, cámara, X/Y, B y START comprobados en build final |
| New 2DS XL | Usuario confirma caballo animado, A/R/L, cámara, START, tapa y HOME; Skin CPU ≈14 ms, Submit+wait ≈12 ms, GPU anterior 1,1 ms; duración no confirmada |

El oráculo privado compara posiciones y normales anteriores al encuadre con
una implementación Python independiente en doble precisión. Incluye extremos,
fracciones, cierre y los cuatro contadores de CM-T4. Error máximo de posición
`0,000242166971` (límite `0,001`), normal `5,4401243e-7` (límite `1e-5`),
y W serializada a texto `3,7500003e-10`. El informe es
`reports/local/f03-02-character-inspection-oracle-v1.json`; auditor SHA-256
`98356df790de0ceab19a509da418d10f70a8a3bb08edaae2b065c75e5d3e3ab7`.
El contraste final usa el C++ corregido y los datos SAN/SCM de v1, idénticos
byte a byte a los de v2.

Azahar mostró `PAUSED Q12:0`, un paso hasta `3686` y conservación del contador
al cambiar cámara/zoom. La cámara pasó de `(0.35,0.35,4.00)` a
`(0.55,0.35,3.00)`; B restauró el encuadre y Y llevó la distancia a `4.50`.
A reanudó, con contadores observados `70034` y posteriormente `26732`;
START devolvió a la lista de aplicaciones. Los envíos repetidos de teclado
que no cambiaron el visor no se contaron como entradas aceptadas.
Se observaron `5,28 ms` de Skin CPU, `8,19 ms` de Submit+wait y `0,25 ms` de
GPU anterior: **son observaciones del emulador, no rendimiento de 2DS XL ni
una distribución estadística**. Las siete capturas y comprobante quedan en
`f03-02-character-native-check-v1/character-v2-ui-receipt.json`, SHA-256
`72039baf8389e48c82c921cf1c427a5d42e1de36ee0718c4b374b63b3cc46b68`.

## Entrega privada y reproducción

Raíz autorizada: `/Users/germancontreras/sh3-private-data/`.
Entrega final: `f03-02-3ds-character-v2/sd-card.zip`.
Manifiesto SHA-256 `9a49b97e3199f5048e8bc9b37d6e99db4463eaff99c0009bf9762a411eea7ab4`.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| animation.san | 1248 | `8adbe5e59f05923c65d0813e2acfc6d88c9364db1d7e18641bdec27f6ac89381` |
| character.scm | 47670 | `3ccf6bbbce726ccedd0b481cd7667ebe95213acc1a2f1dcdf3b27c5a2f792479` |
| sh3_character_probe.3dsx | 272072 | `17f185600e02e6c45536f1abb195705f538e5ba5066e9cd88c11a7f1e9840da7` |
| sh3_character_probe.smdh | 14016 | `90b1364e3d2ee4e5b41ff31f70c52ce6a9e807c99a98a9c94e6da2f41b5eccd1` |
| sd-card.zip | 337274 | `924081e00035e59f08a31716efea1b4f921af7cc43a55078a42b34cdf714e1e2` |

El ZIP contiene cinco archivos, incluido LEEME, en `/3ds/sh3_character_probe/`.
Se comprobó la copia usada en la SD virtual de Azahar; esta ejecución no
incluye copia a SD física ni prueba en consola. No incorpora CIA ni necesita FBI.

Procedencia y hashes de fuente, continuidad, CM-T4 y artefactos del compilador:
`reports/local/f03-02-character-inspection-preparation-v2.json`.
SDK fijado: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
Build sin red desde 66 archivos de código/configuración sin originales;
`build/character-inspection/source-manifest-v2.json`, SHA-256
`bf58ad03870da2c6e6b1851b27965c7e55b0e83ed39cbff0f99f79fbd2675268`.
JUnit/cobertura están en `build/character-inspection/` y los presets host.
El índice de evidencias y sus hashes queda en
`reports/local/f03-02-character-inspection-execution-v1.json`.

`bash scripts/build_character_probe.sh` compila dentro del SDK fijado;
`python -m tools.pipeline.prepare_character_probe --help` documenta los
argumentos de preparación. CI incorpora compilación y artefactos de código
sin SAN/SCM ni originales; **no se afirma una ejecución remota del pipeline**.
El siguiente paso es CM-T5e con el protocolo físico, antes de integrar
materiales originales o ampliar el alcance del actor.

Entrega posterior: a petición del usuario se copió el build `757b48fd1746`
a la SD «NO NAME», en `/3ds/sh3_character_probe/`. Los cinco archivos
(335.832 bytes) coinciden en tamaño y SHA-256 después de leerlos desde la SD.
Se conservaron los demás visores y se retiraron solo los auxiliares `._`
generados para esta copia. `diskutil eject` confirmó la expulsión y el volumen
dejó de estar montado. Comprobante privado
`f03-02-character-native-check-v1/sd-copy.json`, SHA-256
`a5ff3e59eddae83addfa7c9d4b0e66d4f8d192df54dc398913b6154ee775cf02`.
Esta entrega no cierra CM-T5e; falta la ejecución física de la malla.

Confirmación posterior: el usuario vio la malla del caballo animada en New
2DS XL y confirmó A/R/L, cámara, START, tapa y HOME. Cierra CM-T5e.1 funcional
para el build entregado, con los límites del protocolo; CM-T5e.2 conserva
pendientes las mediciones y el detalle de controles no comunicado. Los
reportes históricos y sus hashes no se reescriben. Posteriormente comunicó
Skin CPU ≈14 ms, Submit+wait ≈12 ms y GPU anterior 1,1 ms. Son lecturas físicas
aproximadas, sin duración confirmada ni distribución de tiempos; no se infieren
FPS sumándolas. Continúa [CT-T1–T3, texturas y vínculos](f03-02-character-materials.md).
