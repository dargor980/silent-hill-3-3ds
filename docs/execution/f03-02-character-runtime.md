# F03.02 — Deformación de la malla de 0x0209 en PCSX2

2026-10-20. **CM-T4a–CM-T4d completadas para la muestra representativa**:
125 vértices de dos de las 15 submallas, en cuatro poses de `0x1449`.
Se contrastaron 500 muestras con las posiciones y normales producidas por VU1,
y el orden de 152 comandos de vértice con 38 paquetes consumidos por GS.
La evidencia abarca las rutas de una, dos y tres influencias y los tres helpers
del recurso. No extiende la validación a las otras 13 submallas ni a otros modelos.

[Requisitos y diseño CM/CMR](../../schemas/ps2-character-mesh-v1.md).
[Extracción estructural CM-T1–CM-T3](f03-02-character-mesh.md).
El siguiente paso es **CM-T5: integrar la malla animada al visor**. El build
`a1629eeace22` probado en New 2DS XL sigue mostrando ejes; esta tarea no produjo
un nuevo build ARM ni una prueba física de malla.

## Sesión e identidad

La sesión previa del usuario se pausó y conservó en una ranura nueva, `99`,
de `f03-02-skeleton-continuity-v5/states/`, bajo la raíz privada
`/Users/germancontreras/sh3-private-data`. SHA-256:
`4bf72e2a646afa5949105239b1f95cea17ab23d81f5033021bf9d8a82dafad5d`.
La reproducción diagnóstica utiliza el estado previo `35`, cuyo hash es
`9c325fa3f5e7ca6e6888d818a6e87fb16bc6659036930e5837c86927143b0dcd`.

Las cuatro parejas de capturas pertenecen a `f03-02-character-runtime-v2`:
una restauración al arrancar, ninguna entre muestras y ninguna escritura
directa en la memoria del juego. Guardar estados y detener/avanzar el depurador
son intervenciones diagnósticas: **no constituyen otra prueba de continuidad
por juego normal**. La evidencia anterior de SA/SC permanece separada.

Al terminar, PCSX2 quedó pausado en `0x001D39BC`, ciclo `565810801476`.
Se conservó otra captura en la ranura `11` de la reproducción v2, SHA-256
`d7b396be9aa6aad14acaaff8fb7fb1e19265863702cca4c4400bef364254df0b`.
Esta captura final no se cuenta entre las cuatro poses del contraste.

| Identidad | Valor verificado |
|---|---|
| Edición / CRC | SLES-51434 / `5088CCDB` |
| ELF SHA-256 | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| Ejecutable PCSX2 SHA-256 | `54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49` |
| Revisión fuente del observador | `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3` |
| Actor / instancia / dirección | `0x0209` / `0x018F` / `0x0044D950` |
| Clip | `0x1449`, 24 cuadros, intervalo 0–23 |
| MDL SHA-256 | `120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672` |
| ANM SHA-256 | `cfb30d96574c34a0da2ab6f3be425e8c4d043f03a6ebf826418a89dbf07c8400` |
| JSON de malla SHA-256 | `f9f4cd9b635c6d776b7dd479dce1f2696363a272a48dfa43b8dd2e01db34f8f7` |

El auditor verifica el MDL y ANM completos en cada captura de entrada y las
ventanas de código ejecutadas contra el ELF europeo. La instancia observada
tiene el bit de estado `0x2000` desactivado; la rama de reflejo no queda validada.
Se conserva el perfil de redondeo FPU/VU en modo 3, hacia cero, sin VU en hilo.

## Cadena observada y algoritmo

La entrada de dibujo `0x001D3920` enlaza el actor con la cabecera del modelo
`0x009A2060` y el área de trabajo `0x01DEDA40`. El puntero de pose en `work+8`
apunta a `0x01DEDA70`; la matriz de instancia reside en `actor+0x40`.
`0x001D3FC0` prepara los huesos y `0x001D4130` los helpers. El buffer señalado
por `0x01E5B910` es `0x01E30540`: tres matrices de hueso desde su inicio y tres
matrices auxiliares desde `+0x2000`.

Con vectores columna y matrices almacenadas por columnas, la ruta observada es:

```text
C   = View × Instance
C'  = C con la fila W sustituida por la fila Z
P_b = C' × Pose_b
H_h = P_target(h) × StoredHelper_h

p_local = (position_q4 / 16, 1)
n_local = normal_q12 / 4096
w_i     = stored_weight_i / 4096

p_view4 = suma_i w_i × M_i × p_local
n_view3 = suma_i w_i × linear3(M_i) × n_local
```

La primera influencia usa `P_primary`; las siguientes usan `H_h` de la paleta
del grupo. Los pares `(base,target)` son `(0,1)`, `(0,2)` y `(1,2)`.
La vista procede de `0x01E54F00`; la composición vista/instancia utiliza
`0x00120E18`. La fila W preparada permite obtener W=Z para la proyección.

Cada helper almacenado se aproxima a
`inverse(Rest_target) × Rest_base`: los errores máximos por componente son
`0,000181845`, `0,000535501` y `0,000474919`. Esto explica el cambio de base;
**el visor debe usar las matrices almacenadas como autoridad**, sin sustituirlas
por inversas recalculadas que pierden la precisión original.

Los pesos se usan **sin normalización**. Las normales se multiplican por las
tres columnas lineales, sin traslación, inversa transpuesta ni normalización
en esta etapa de skinning. No se atribuye ese comportamiento a etapas posteriores
de iluminación o materiales.

Al separar la deformación en espacio modelo de la transformación de presentación,
la componente homogénea resultante es `W = suma_i(w_i)`, que puede ser menor
que uno. Debe conservarse durante instancia/vista/proyección, o emplearse una
compensación algebraicamente equivalente. Forzar W=1 altera la contribución de
las traslaciones. Normalizar todos los pesos puede mantener X/Z e Y/Z, pero
cambia Q, profundidad, niebla y normales: una comparación solo visual de XY
no basta para detectar ese error.

## Evidencia VU y precisión

Las entradas se guardaron en `0x001D39BC`, después de preparar matrices; las
salidas en `0x001D3A28`, después de enviar el dibujo mediante la ruta
`0x001D8FA0` → `0x001D8DA0` y la función de paquetes `0x001D8AB0`.
La llamada DMA en `0x001D8F5C` utiliza `0x0019BF90` para D1.
Al capturar ese retorno, VU conserva las submallas **4 y 5, índices desde cero**;
no implica que el dibujo del actor completo haya finalizado.

La cadena MPG en el ELF, dirección `0x0042AC80`, contiene 10.976 bytes de
microprograma en seis cargas. Todos los intervalos cargados coinciden con
`vu1MicroMem.bin` de las capturas. Los índices de instrucción VU (ocho bytes
por instrucción) `0x55–0x67`, `0x68–0x86` y `0x87–0xAE` ejecutan las rutas
de una, dos y tres influencias: conversiones ITOF4/ITOF12 y productos/sumas.
Se desensamblaron con las tablas de la revisión fijada de PCSX2; no fue
necesario recompilar ni instrumentar el emulador.

Las paletas se contrastan palabra por palabra entre EE y VU. Una excepción
observada se excluye explícitamente de esa comparación: después de deformar,
`ISW.z vi5,3(vi5)` en `0x4B` reutiliza la traslación Z de la primera matriz
como enlace. El oráculo utiliza la copia EE original, no esa palabra sobrescrita.
Las matrices auxiliares, cabeceras VIF y comandos de tira coinciden completos.

| Capturas entrada/salida | Contador Q12 | Cuadro del clip |
|---|---:|---:|
| 03 / 04 | 67.438 | 16,46435546875 |
| 05 / 06 | 81.990 | 20,01708984375 |
| 07 / 08 | 85.676 | 20,9169921875 |
| 09 / 10 | 89.362 | 21,81689453125 |

Hay 108 vértices en la submalla 4 y 17 en la 5. Las cuatro poses suman
344 muestras rígidas, 144 de dos influencias y 12 de tres. Las poses y paletas
EE permanecen idénticas entre cada entrada y salida; los ciclos avanzan y los
cuatro contadores son distintos.

| Comparación | Error absoluto máximo por componente | Límite del auditor |
|---|---:|---:|
| Matrices de hueso, producto float32 hacia cero | 0,0000610352 | 0,001 |
| Helpers, producto de referencia en doble precisión | 0,000205392 | 0,001 |
| Posición, cuatro componentes | 0,000831400 | 0,001 |
| Normal, tres componentes | 0,000000213630 | 0,00001 |

La multiplicación acotada float32 hacia cero se usa al reconstruir las matrices
de hueso: una multiplicación directa en doble precisión cambia la cancelación
de coordenadas grandes. El oráculo de vértices trabaja en doble precisión sobre
las paletas capturadas. Ninguno pretende emular todas las particularidades
numéricas de PS2. Los límites se fijaron tras la exploración y antes de la
auditoría reproducible final; no son tolerancias prerregistradas ni una prueba
con muestras independientes de esa exploración.

Los controles negativos exceden el límite de posición de manera inequívoca:

| Variante incorrecta | Muestras detectadas | Error máximo |
|---|---:|---:|
| Normalizar pesos | 128 | 1,06965 |
| Omitir helpers | 156 | 330,561 |
| Invertir el orden del producto helper | 156 | 500.555,641 |
| Aplicar dos veces el helper | 156 | 347,135 |

## Orden de tira y consumo GS

El volcado GS sin comprimir, versión 9, contiene 7.448 transferencias,
cuatro VSync y 9.092 paquetes GIF completos. Termina en VSync. En el intervalo
de VSync 1 se identificaron de forma única 38 paquetes de ruta 3, cada uno con
cuatro vértices y registros STQ/RGBA/XYZF (`0x412`). PRIM=`0x3C`: tira de
triángulos, Gouraud, textura y niebla, sin alpha blending en esta muestra.

Cada grupo coincide, en orden, con STQ calculado a partir de la posición VU y
las UV Q12 del MDL, sin invertir V. Error máximo `8,54285e−11`, con tolerancia
`1e−8 + 2e−6 × abs(referencia)`. Además, la etiqueta de 16 bytes y los 192 bytes
del último paquete residente en VU coinciden **exactamente** con el volcado GS.

| Submalla | Paquetes / comandos | Supresión de origen | Triángulos candidatos | Caras posteriores suprimidas | Emitidos |
|---|---:|---:|---:|---:|---:|
| 4 | 32 / 128 | 78 | 50 | 21 | 29 |
| 5 | 6 / 24 | 18 | 6 | 0 | 6 |

Los 152 bits de supresión ADC quedan explicados: se conservan los conectores
del origen y se añade descarte por orientación. No hay vértices fuera de los
planos de recorte en esta muestra. El área firmada en XY/Z, corregida por la
paridad de la tira, es positiva en los candidatos suprimidos y negativa en
los emitidos. La ruta VU `0x29F–0x302` contiene el test de signo correspondiente.
El menor valor absoluto del área es `1,36355e−6`, sin ambigüedad de área cero.
El orden de índices candidatos coincide con el decoder existente.

Esto verifica tiras y descarte de estas dos submallas. No valida todas las
texturas, iluminación ni equivalencia de píxeles, y no fija automáticamente la
cara frontal de Citro3D: la conversión de base y proyección del visor deberá
comprobarse por separado en CM-T5.

## Implementación, pruebas y reproducción

`tools/qa/character_skinning_oracle.py` contiene únicamente el producto 4×4 y
la mezcla de posiciones/normales, con resultados inmutables y validación de
componentes finitos, vectores, influencias y pesos. No importa el decoder,
PCSX2, I/O ni render. La captura, identidad y comparación permanecen en el
auditor local. Esta separación mantiene responsabilidades distintas y permite
contrastar la futura implementación C++ sin compartir su código.

- **34 pruebas analíticas nuevas**: traslación separada de normal, rotación
  asimétrica, helpers, tres pesos, orden de productos, déficit Q12, W=Z,
  normales sin normalizar y rechazo de entradas inválidas/desbordamiento.
- **229 pruebas aprobadas** en la ejecución final conjunta de malla,
  esqueleto/animación, oráculo de pose y nuevo oráculo de deformación.
- Nuevo oráculo: **100 % de líneas y ramas**; Ruff aprobado. Los nuevos casos
  entran en el job Python existente por descubrimiento, con fixtures propios
  y sin datos del juego. No se afirma ejecución remota de CI.
- Contratos de arquitectura, custodia y especificación: **PASS, cero errores**.
  Formato Ruff y `git diff --check` aprobados.
- La auditoría privada verifica hashes, código, entradas/salidas y controles
  negativos; una repetición debe producir el mismo reporte byte por byte.
  La repetición final lo confirmó con el hash registrado abajo.

Comandos de reproducción desde el checkout, con los artefactos privados presentes:

```sh
rtk proxy .venv/bin/python build/f03-02-character-runtime/audit.py
rtk proxy .venv/bin/python -m pytest tests/python/test_character_skinning_oracle.py tests/python/test_character_mesh.py tests/python/test_animation_pose_oracle.py tests/python/test_skeleton_animation.py --cov=tools.qa.character_skinning_oracle --cov-branch --cov-report=term-missing --cov-report=json:build/f03-02-character-runtime/coverage.json --junitxml=build/f03-02-character-runtime/pytest.xml -q
rtk proxy .venv/bin/ruff check tools/qa/character_skinning_oracle.py tests/python/test_character_skinning_oracle.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

El auditor local depende de `research.py` y `gs_read.py` de los directorios
de investigación anteriores bajo `build/`. Las capturas y el volcado no se
incluyen en el repositorio ni en CI. Se conservan en la raíz privada; el
reporte de metadatos está en `reports/local/f03-02-character-runtime-v1.json`.

| Artefacto | SHA-256 |
|---|---|
| Reporte reproducible | `a4b6c2cc8fdd08fced7fc679a9aaf6e9d41ec0a1bd998a2a2b688e9ae992fbe0` |
| Auditor local `build/f03-02-character-runtime/audit.py` | `b1fa361ae7f0e02cfa291d8cf311d58efd8db542d2d289e428675752548a6698` |
| Oráculo Python | `29c707553970485e01049651ed85c2185c3ac41af5149d1595806765a0514d79` |
| Cadena DMA del microprograma | `544b625d5284e65e28913cfd345a884c8ae76f464dd187a161814a47971df9d2` |
| Microprograma con relleno cero hasta 16 KiB | `c54740333d5ef3137b8a43634a5c87d323083a0dd2ee9886b1e23141675febe0` |
| Volcado GS, 19.627.887 bytes | `d563ea1b7b9ceab6c99f89a96a0d8f83cf755dc0e0b4d7c9936127223a91a8e9` |

Nombre del volcado dentro de `f03-02-character-runtime-v2/profile/PCSX2/snaps/`:
`Silent Hill 3_SLES-51434_20261020190450.gs`. El reporte conserva los hashes
de cada captura, ciclos, ventanas de código y errores por pose/submalla.
JUnit y cobertura: `build/f03-02-character-runtime/pytest.xml` y `coverage.json`.

## Límites y siguiente tarea

CM-T5 debe implementar la deformación como operación de dominio pura, mantener
W y las matrices auxiliares verificadas, añadir un paquete de inspección
acotado y medir el coste por cuadro. Debe separar lectura, control de animación
y adaptador de dibujo; contrastar C++ con casos analíticos y estas referencias;
verificar base, normales y cara frontal; compilar con el SDK fijado y pasar
Azahar antes de preparar otra prueba física. Un material de inspección propio
debe identificarse como tal hasta verificar las texturas/materiales del MDL.

Permanecen pendientes la rama de reflejo, otras variantes de malla, transiciones
de daño `0x144A` y muerte `0x144B`, la base definitiva del port y la equivalencia
de materiales/iluminación. No se cierran SC-T3b/c, F03.02/F03.03 globales ni G02/G03.
