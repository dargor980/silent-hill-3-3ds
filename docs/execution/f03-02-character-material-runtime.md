# F03.02 — Material del caballo contrastado en PCSX2

2026-10-22. **CT-T4a–d completadas para la instancia y pasada capturadas.**
Se enlazan las 15 submallas del actor `0x0209` con las tres texturas y CLUT 0,
los estados GS efectivos y sus píxeles en una reproducción software de PCSX2.
La pasada usa **color opaco con modulación**, aunque las imágenes 0/1 contienen
alfa: mezcla y prueba de alfa están desactivadas. No debe añadirse recorte ni
mezcla por el aspecto del PNG. [Contrato CT01–CT08](../../schemas/ps2-character-materials-v1.md).

Al cerrar CT-T4, CT-T5 seguía pendiente y el build `757b48fd1746` no se modificó.
Posteriormente, [CT-T5e.1 funcional](../compatibility/character-material-inspection.md)
quedó aprobada por el usuario con `ced27c955e41`; tiempos CT-T5e.2 pendientes.
[LI-T1–T3](f03-02-character-lighting.md) verifican después las ecuaciones de
iluminación de esta captura, aún sin integrarlas al visor. La base mundial
definitiva y las transiciones de daño/muerte no quedan resueltas por esta prueba.

## Identidad y atribución de los draws

Se reutiliza el dump inalterado de [CM-T4](f03-02-character-runtime.md), con
SLES-51434 / CRC `5088CCDB`, actor `0x44D950`, instancia `0x018F`, clip `0x1449`,
contador `89362`. Es una reproducción diagnóstica; no una nueva sesión continua
de juego normal. Las capturas de entrada/salida 9/10 conservan los hashes de
CM-T4, el MDL completo en RAM y las matrices de la pose.

Los vértices decodificados, sus matrices/huesos/helpers y pesos predicen
`S=(u/4096)/z`, `T=(v/4096)/z`, `Q=1/z`. Los **428 paquetes GIF**, de cuatro
comandos cada uno, tienen coincidencia única y ordenada en el intervalo de
VSync 1: **1.712 comandos, todas las submallas**, error STQ máximo
`1,680e-10` (límite previo `1e-8 + 2e-6*abs(valor)`). Se comprueba path 3,
PRMODECONT=1, contexto 0 y ausencia de TEX2 posterior al TEX0 seleccionado.

| Imagen / descriptor | Submallas | Paquetes | TEX0 | TBP0 / CBP | Triángulos SW |
|---|---|---:|---|---|---:|
| 0 | 0–5 | 160 | `2006D80665322800` | `0x2800 / 0x36C0` | 228 |
| 1 | 6–8 | 98 | `2006D00665322400` | `0x2400 / 0x3680` | 142 |
| 2 | 9–14 | 170 | `2006C80665322000` | `0x2000 / 0x3640` | 149 |

Las bases son unidades GS de 256 bytes. Los tres TEX0 indican PSMT8,
TBW=8, TW=TH=9, TCC=1, TFX=MODULATE, CPSM=PSMCT32, CSM=0, CSA=0 y CLD=1.
Se verifica la paleta cargada por el renderer; no basta con observar CBP.

El replay produce los draws **20, 21 y 22** del intervalo 1. Sus **519
triángulos** coinciden exactamente con los comandos atribuidos en STQ binario,
XY/Z, RGBA y niebla, admitiendo permutación de los tres vértices para comparar
el conjunto. Se contabilizan aparte seis triángulos GIF descartados por
PCSX2 al tener cajas sin centros de píxel a resolución nativa, conforme a
`GSState::VertexKick`. No se confunden con vértices ausentes o errores de UV.

## Estados efectivos

El lector parte del estado congelado GS v9 y sigue escrituras GIF; los estados
se vuelven a contrastar con los tres archivos `context.txt` del renderer.

| Estado | Valor observado | Efecto en esta pasada |
|---|---|---|
| PRIM | `0x3C` | Triangle strip, Gouraud, textura y niebla; ABE=0, AA1=0, FST=0, FIX=0 |
| TEST | `0x50002` | ATE=0, DATE=0, ZTE=1, ZTST=GEQUAL |
| ALPHA | `0x44` | Fórmula `(Cs-Cd)*As/128+Cd` almacenada, inactiva porque ABE=0 |
| TEX1 | `0x61` | LCM=1, K=0, MXL=0; bilineal min/mag, sin mipmaps |
| CLAMP | `0x000007FC007FC00A` | REGION_CLAMP U/V, límites 0–511 |
| FRAME | `0x80000` | PSMCT32, FBW=8, sin máscara de escritura |
| ZBUF | `0x3A0001C0` | Z16S, escritura activa, base `0x3800` en bloques GS |
| FBA / PABE / DTHE / SCANMSK | 0 | Sin forzar bit alfa, mezcla por píxel, dither ni máscara de líneas |
| COLCLAMP | 1 | Saturación de color |
| TEXA | `0x8000000080` | TA0=TA1=128, AEM=0; alfa procede de CLUT32 |
| FOGCOL | 0 | Niebla negra; F=255 en los vértices de estos tres draws |

La modulación usa la escala PS2 **128**, no 255: `texture * vertex / 128`,
con saturación antes de la niebla. El alfa también se modula y se escribe en
el framebuffer, pero no decide mezcla ni descarte aquí. El color interpolado
de vértice procede del juego; no se deduce del MDL ni equivale al sombreado
dorado del visor actual. Los vértices de la muestra tienen alfa 124–125.

## Texturas consumidas y caché parcial

Se comparan **786.432 índices de VRAM** y **768 colores de CLUT** contra los
archivos privados de CT-T3. La reconstrucción RGBA de las tres texturas es
idéntica byte a byte; sus hashes son los mismos del
[informe de adquisición](f03-02-character-materials.md#procedencia-y-entrega-privada).
Selector cero queda confirmado para las tres imágenes; otras selecciones
siguen fuera del perfil.

El PNG `itex0` del renderer software contiene toda la caché, pero PCSX2 solo
actualiza los bloques tocados por el draw (`SharedData::UpdateSource`). Por eso
las imágenes 1/2 muestran 24.443/23.817 píxeles distintos fuera de la región
usada: no son diferencias de los índices ni de la paleta en VRAM. Se comprueba
exactamente la caché en toda la huella de UV, ampliada para los cuatro taps
bilineales: imagen 0 `[2,14]–[509,510]`, imagen 1 `[1,0]–[456,506]`, imagen 2
`[16,17]–[480,500]`. Fuera de ella se usa la evidencia completa `itexraw` + CLUT,
no se confunden bloques no actualizados con datos originales.

## Píxeles y controles negativos

El oráculo selecciona la superficie visible por geometría y profundidad antes
de consultar el color de salida. Usa centros enteros XY, margen baricéntrico
0,05, STQ con perspectiva, fracciones bilineales de cuatro bits, modulación y
niebla negra. El límite fijado antes de comparar es RGB ≤2/255, alfa ≤1/255 y
profundidad ≤2 unidades; no se amplió ante fallos. Los bordes no se auditan.

| Imagen | Píxeles interiores | Triángulos con muestras | Rechazados por Z | RGB máx. | Alfa máx. |
|---|---:|---:|---:|---:|---:|
| 0 | 8.220 | 216 | 0 | 1 | 1 |
| 1 | 5.494 | 114 | 86 | 1 | 1 |
| 2 | 1.398 | 63 | 463 | 1 | 1 |
| Total | **15.112** | **393** | **549** | **1** | **1** |

14.776 muestras cambian el color previo. 15.063 colores RGB coinciden
exactamente y 49 difieren en una unidad; el alfa coincide en 14.207 muestras
y difiere en una unidad en 905. Profundidad: error máximo una unidad. Los
549 interiores rechazados por Z conservan su color anterior.

Controles erróneos detectados fuera de la tolerancia RGB: añadir mezcla
(845 muestras), invertir V (13.347), sustituir textura (13.935) y omitir la
modulación (12.395). Hay **186 muestras con alfa fuente calculado cero**;
descartarlas indebidamente cambia 178 resultados. La textura 2 no contiene
alfa cero, por lo que ese control solo se exige a las imágenes 0/1.

Esto demuestra el material de los draws observados. No demuestra iluminación
dinámica completa, niebla variable (aquí F=255), rasterización de bordes,
postprocesado posterior ni igualdad de píxel en PICA200.

## Implementación, pruebas y custodia

`tools/inspectors/pcsx2_gs_dump.py` incorpora el lector local de MR-T4 como
módulo probado: framing GIF por path, continuación entre transferencias,
reglist/image, validación de límites y rechazo de versiones o estados iniciales
activos no soportados. No ejecuta el dump. `tools/qa/gs_material_oracle.py`
separa decodificación de registros, validación de perfil, muestreo y semántica
de color; no accede al disco ni depende de recursos del juego.

**427 pruebas relacionadas aprobadas**, incluidas **64 pruebas GS** ahora
descubiertas por la CI host; cobertura de los dos módulos de CT-T4: **100 %
de líneas y ramas**. Ruff, formato y contratos del repositorio pasan.
No se modifican dependencias ni workflow: pytest ya descubre estos casos.
No se ejecuta pipeline remoto, compilación ARM ni prueba física en esta tarea.

Evidencia local ignorada:

- `build/character-materials/runtime-tests.xml`, `runtime-related-tests.xml`
  y `runtime-coverage.json`.
- Auditor `build/character-materials/audit_runtime.py`, SHA-256
  `30b6168d1a85943a94a0274101d1b84b475c3b92eab1642a5c86e62300aedec6`.
- Informe final `reports/local/f03-02-character-material-runtime-v2.json`,
  SHA-256 `108d8b1ba958ef2d7d70b16c698daf97a18a387959dc1a7801adc3dc9634d0dc`.
  Incluye hashes del auditor, dependencias locales y los 50 archivos del replay.
  El informe exploratorio v1 se conserva sin sustituirlo.

Raíz privada `/Users/germancontreras/sh3-private-data/`:

- Entrada `f03-02-character-runtime-v2/profile/PCSX2/snaps/`:
  `Silent Hill 3_SLES-51434_20261020190450.gs`, 19.627.887 bytes, SHA-256
  `d563ea1b7b9ceab6c99f89a96a0d8f83cf755dc0e0b4d7c9936127223a91a8e9`.
- `f03-02-character-gs-sw-info-v1/`: 1.224 archivos de diagnóstico,
  9.300.726 bytes; `f03-02-character-gs-sw-alpha-v1/`: 50 archivos,
  4.330.092 bytes. Perfiles nuevos, originales intactos, ambos procesos
  terminaron con código 0 al alcanzar su límite de 35 segundos.
- PCSX2, revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, ejecutable SHA-256
  `54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.

No se enviaron escrituras ni restauraciones a la sesión de juego original;
solo se terminaron los procesos hijos del replay. La comprobación final de
su estado vivo no pudo confirmarse: la primera consulta quedó sin ejecutar
por un límite del sistema de aprobación y el reintento autorizado del 22 de
octubre devolvió `TRANSPORT_IO`. No se afirma que siga abierta o pausada;
el cierre de CT-T4 se apoya en las capturas inmutables y los replays terminados.

Reproducción local con el corpus privado conservado:
`.venv/bin/python build/character-materials/audit_runtime.py`.
El auditor verifica las identidades, exige los límites y no reemplaza un
informe final existente con contenido diferente. Los datos del juego no
forman parte de fixtures, repositorio ni CI.

Referencias primarias de la revisión fijada, consultadas en el checkout local:
[registros GS](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSRegs.h),
[estado y descarte de primitivas](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSState.cpp),
[caché del renderer software](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/Renderers/SW/GSRendererSW.cpp),
[muestreo y color](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/Renderers/SW/GSDrawScanline.cpp).

## Receta acotada para CT-T5

Conservar UV y los tres grupos, textura/paleta verificadas, bilineal sin mipmaps,
clamp 0–511, modulación PS2 y profundidad con escritura. Desactivar mezcla y
prueba alfa para esta pasada; conservar alfa en los datos. La comparación Z
debe traducirse junto con la convención de proyección del visor, no copiarse
como una constante sin comprobar su sentido.

El visor debe declarar qué colores e iluminación usa: neutros o diagnósticos
si no se implementa aún la iluminación del juego. No convertir una muestra de
color de esta pose en una solución de iluminación dinámica. CT-T5 requiere
formato versionado, pruebas de materiales/UV y límites, build ARM, Azahar y
confirmación física independiente con tiempos de CPU/envío/GPU.
