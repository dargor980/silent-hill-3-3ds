# F03.02 — Transformación VU0, consumo GS y transparencia

2026-10-20. **MR-T4d completada para las dos formas de hp34.map.** Se verificaron
la transformación y los STQ de sus 56 vértices, el consumo GS de 32 triángulos
por cuadro y la transparencia en una reproducción software del volcado original.
El oráculo contrastó 16.380 píxeles interiores: alpha exacto y error RGB máximo
de 1/255. La cámara de inspección es una intervención registrada; no acredita
una partida normal ni todos los materiales del juego.

Al cerrar MR-T4d aún no había nuevo build 3DS ni cambios en el renderer.
La [entrega posterior MI](f03-02-material-inspection.md) integra el material
y modelo en `764be66e7762`; el usuario confirmó después ambos paneles con
transparencia, controles, START, tapa y HOME en New 2DS XL.

## Recorrido comprobado

La ruta observada es **EE → DMA/VIF0 → VU0 → scratchpad → EE → paquetes GS**.
No corresponde a un envío de estas formas a VU1.

`001B1200` inicia el DMA D0 y consulta VIF0. `001B1F30` recoge la salida de
VU0 desde `11004000` mediante SPR1. `001B16F0` examina el bit `8000` del
cuarto componente del registro de posición, en vértices de 48 bytes. Si está
activo, salta la construcción del triángulo. Los triángulos que pasan se
preparan mediante `00139050`, SPR0 y `00139150`.

Las direcciones se contrastaron con el ELF europeo ya fijado, no con un
desplazamiento supuesto desde otra región. Las direcciones de hardware y la
serialización de registros se comprobaron en las fuentes locales de PCSX2,
revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`:
[Hw.h](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/Hw.h),
[VUmicroMem.cpp](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/VUmicroMem.cpp),
[GSState.cpp](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSState.cpp).

## Modelo, cámara y coordenadas

La matriz del MAP en su offset 112 coincide byte a byte con la copia en
`01D15360` y con los primeros 64 bytes de la memoria de VU0. `01D15360`
es objeto de render +`60`, **no contexto MAP +`60`**. El contexto +`768`
apunta al objeto y no es directamente una matriz.

En esta instancia, el modelo tiene rotación identidad y traslación
`(100000, 0, 140000)`. La matriz de pantalla y la de recorte conservan
separadamente la contribución de cámara/proyección. Sus productos por el
modelo coinciden con los registros VF1–VF4 y VF13–VF16 de VU0 dentro del
límite de redondeo de una cadena corta de operaciones de precisión simple.

El oráculo independiente calcula el producto por columnas, divide XYZ por W
y convierte a la escala fija ×16 de la salida. No pretende emular todas las
reglas numéricas de VU. Se fijó una tolerancia máxima de una unidad fija;
**el error observado fue cero en cada coordenada XYZ comprobada**.

| Captura privada | Forma | Registros contrastados | Resultado del filtro |
|---|---|---|---|
| v3, slot 09 | offset 448, 26 vértices | 26, scratch `1000` | 0 triángulos pasan |
| v3, slot 12 | offset 928, 30 vértices | lote de 28 en `1000` y de 4 en `0000`, con 2 repetidos | 0 pasan |
| v5, slot 02 | offset 448, 26 vértices | 26, scratch `1000` | 16 candidatos pasan |
| v5, slot 06 | offset 928, 30 vértices | 28 en `1000` y 4 en `0000`, con 2 repetidos | 16 candidatos pasan |

Los STQ capturados cumplen `Q≈1/W`, `S/Q≈U/32768` y `T/Q≈V/32768`.
El máximo error observado de UV normalizadas es menor que `8,74e-8`, dentro
del límite fijado `4×2^-23`. VU0 no invierte V en este recorrido y conserva
el bit de control del U original en su valor numérico. El contraste de píxeles
posterior confirma la orientación en PCSX2; la del importador/renderer 3DS
requiere su propia prueba.

## Controles de cámara y descarte

La reproducción v3 cargó el hospital pero conservó la posición anterior del
personaje. Todos los registros de salida examinados quedan fuera del volumen
de recorte. TEX0 del banco objetivo no aparece en los contextos GS guardados.
La selección de material de MR-T4c era correcta, pero no acreditaba dibujo.

En v4 se ensayaron dos posiciones del personaje mediante dos escrituras
verificadas por intento, sin modificar matrices ni recursos:
`(100000,0,140000)` y `(99000,0,138000)`. El juego actualizó la orientación
de su cámara, pero mantuvo su posición fija. En la segunda prueba hay vértices
dentro del volumen de recorte y los triángulos siguen descartados. El camino
VU incluye la prueba de orientación, además de los controles de recorte y
reinicio de tira; el bit `8000` no identifica exclusivamente un plano de recorte.

Para observar la otra cara se abrió v5 desde el slot 06 de v4. En `001B6C00`,
con `a0=01DEB3C0`, se sustituyó **la transformación padre de la cámara de
diagnóstico** en `01DEB400` por identidad con posición
`(100000,-1400,136000)`. Fueron 11 palabras efectivamente diferentes; las
16 se verificaron antes/después. La rutina original calculó vista/proyección
y el getter de cámara produjo esa posición.

Se conservaron el modelo, las dos formas, los índices, la textura y los estados
de mezcla. Los hashes completos de MAP/textura siguen coincidiendo. La primera
forma tiene 16 candidatos que pasan el filtro, coincidentes con su
decodificación geométrica previa. El slot 02 conserva la pausa antes del
primero. Los slots 03–07 registran el avance posterior: primera forma completa,
lotes de 28/4 de la segunda y siguiente entrada de cámara.

La cámara de inspección es una intervención documentada. No acredita una
partida normal de hospital, su cámara de juego ni una captura ininterrumpida.

## Estados consumidos y textura efectiva

El volcado v6 acredita los siguientes estados junto a los vértices objetivo:

| Estado | Valor e interpretación |
|---|---|
| TEX0 | `2006E00621311C00` / `2006E00621312C00`: PSMT8, CLUT 0, TCC=1, TFX=0 |
| GIF PRE / PRIM | PRE=1, PRIM=`07B`: triángulos, interpolación de color, textura, niebla y mezcla activas; STQ, contexto 0 |
| ALPHA | `0000008000000044`: A=Cs, B=Cd, C=As, D=Cd |
| TEST | `0000000000053000`: ATE=0, DATE=0, ZTE=1, ZTST=2 |
| AFAIL | 3, inactivo mientras ATE=0 |
| Alpha de vértice | 127 en todos los registros contrastados |

Los campos se contrastaron con
[GSRegs.h](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSRegs.h).
La ecuación seleccionada para RGB es
`Cd + (Cs − Cd) × As/128`, con las reglas de aritmética y saturación del GS.
FIX=128 no selecciona una opacidad constante: el selector C usa As.
La referencia de cálculo es
[GSDrawScanline.cpp](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/Renderers/SW/GSDrawScanline.cpp).

La imagen RGBA PS2 de paleta 0 se verificó por su hash
`5e18dfe5e3d46b61c23ea25fcd56994e165fbb8bb4940a8a25ff07081d24d792`.
Sus alphas usados van de 42 a 128. El RGB y el canal alpha extraídos de la
textura utilizada por el renderer software coinciden byte a byte con los
65.536 texels de esa imagen. La modulación con el alpha de vértice 127 se
contrastó después del muestreo, contra el alpha del framebuffer.

El seguimiento conserva también los estados externos al paquete: PRMODECONT=1,
XYOFFSET=(1792,1792), scissor 0–511, clamp en U/V, filtrado lineal y MXL=0.
FRAME es PSMCT32, sin máscara de escritura. ZBUF es PSMZ16S con **ZMSK=1**:
se compara profundidad pero no se escribe. FBA=0, PABE=0, DTHE=0 y COLCLAMP=1.
La niebla es negra; F=227 en los vértices contrastados.

## Transferencias GIF/GS

La sesión v6 restaura v5/07 y pausa únicamente en la función de cámara. Se
reaplica su transformación documentada antes de cada cuadro, con recibos y
comprobación de las ventanas de código. La primera reanudación alcanza el
breakpoint restaurado sin cambiar ciclo; se registra como tal, no como avance.

«Guardar volcado de un fotograma del GS» llama `queueSnapshot(1)`, pero la
revisión fijada conserva campos adicionales. El archivo completo contiene
**5.582 transferencias, 4 VSync y 5.780 paquetes GIF**. El lector valida
cabecera, estado GS versión 9, límites y continuidad independiente de cada
path. Rechaza paquetes incompletos; no busca firmas entre bytes sin encuadre.

En los intervalos VSync 1 y 3 hay 32 paquetes objetivo por cuadro, path 3,
NLOOP=1, PRE=1, PRIM=`07B`, NREG=12, registros `412412412EEE`.
Los 144 bytes STQ/RGBA/XYZF de cada triángulo coinciden **exactamente** con
las tripletas que pasan el filtro de VU0: 16 de cada forma en cada cuadro.
La comparación conserva multiplicidad y comprueba los tres A+D del material.
La ruta original de PCSX2 registra estas transferencias después de procesarlas
en `GSState::Transfer`; esta evidencia supera la mera preparación en RAM.

TEX0 alterna TBP0=`1C00`/`2C00`; FRAME alterna su buffer correspondiente.
Los restantes campos del material coinciden. Por tanto, TBP0 no debe convertirse
en identificador persistente de textura. El volcado original tiene 12.907.891
bytes, SHA-256 `4ce2e101e325e92ef68ac521bd6329fcd12cdf68ea09275aeab3d2e68ab2c801`.

## Contraste de píxeles

Se reprodujo ese mismo archivo, sin modificar paquetes, con el renderer
software de PCSX2 y perfiles aislados. El primer recorrido identifica las
llamadas 21 y 47 con el material objetivo. La llamada 21 agrupa los 32
triángulos de ambas formas; se guardan únicamente sus texturas, registros y
buffers de color/profundidad antes y después. Las formas se observan como
paneles de vidrio sobre el fondo ya dibujado.

El oráculo usa muestras XY enteras, división STQ, clamp, desplazamiento de
medio texel y filtrado bilineal con fracciones de 4 bits. Se identificó una
etapa necesaria en `GSState::CalcMask/FlushPrim`: para primitivas de Z constante,
PCSX2 redondea S/T eliminando al menos 9 bits, ajustados por diferencia de
exponentes respecto a Q, y elimina los 8 bits inferiores de Q. Los 96 STQ
resultantes coinciden exactamente con el registro del renderer. Omitir esa
etapa produjo discrepancias de muestreo; se corrigió el oráculo según la ruta
observada, sin ampliar la tolerancia.

La secuencia comprobada es modulación de textura por color de vértice con
denominador 128, niebla `floor(Cs×227/256)`, alpha
`floor(Atextura_muestreada×127/128)` y mezcla
`Cd + floor((Cs_niebla−Cd)×As/128)`, con saturación.

| Comprobación | Resultado |
|---|---|
| Píxeles interiores, margen baricéntrico fijo 0,05 | 16.380, repartidos entre los 32 triángulos |
| Alpha | 16.380 coincidencias exactas |
| RGB | 16.331 exactos; 49 difieren en 1 nivel; ninguno supera 1/255 |
| Profundidad antes/después | Idéntica, coherente con ZMSK=1 |
| Control opaco | Difiere más de 1 nivel en 16.273 muestras |
| Control sin niebla | Difiere más de 1 nivel en las 16.380 muestras |
| Control con V invertida | Difiere más de 1 nivel en 14.254 muestras |

Cada triángulo tiene muestras y detecta los tres controles incorrectos.
No se admiten bordes de rasterización como prueba de igualdad, ni se afirma
equivalencia universal del GS. Los píxeles se contrastan con PCSX2 software;
la confirmación funcional posterior de MI-T4 en New 2DS XL no constituye
una comparación cuantitativa de píxeles entre ambas plataformas.

## Evidencia reproducible

Raíz privada autorizada: `/Users/germancontreras/sh3-private-data/`.

- `f03-02-map-runtime-v4/`: seis capturas, dos recibos de cambio de posición
  y cierre normal, código 0; originales intactos y socket eliminado.
- `f03-02-map-runtime-v5/`: siete capturas y recibo de cámara. El bloqueo de
  pantalla y los clics fallidos se resolvieron avanzando por los menús del
  depurador. Cierre normal, originales intactos y socket eliminado.
- `f03-02-map-runtime-v6/`: cinco capturas, tres recibos de cámara y volcado
  GS completo. Cierre normal, originales intactos y socket eliminado.
- `f03-02-gs-sw-{info,pixels,alpha}-v1/`: tres reproducciones del mismo volcado,
  limitadas a 35 segundos y cuatro campos para exportación. Todas terminan
  con código 0; la última conserva 17 archivos, 674.197 bytes.

Informe: `reports/local/f03-02-map-draw-v2.json`, 7.301 bytes, SHA-256
`2bb5e23ed9615ab5283985d8a3ee447481170e86d16b02185e2b6be5ce2e3572`.
Contiene hashes, cuentas, errores y límites de las conclusiones; no exporta
vértices, matrices ni imágenes originales.

```sh
rtk proxy .venv/bin/python build/f03-02-map-runtime/audit_draw.py
```

El auxiliar local ignorado usa el lector acotado con CRC, comprueba identidad
de captura, PC/ciclo, ocho ventanas del ELF, hashes completos de ambos recursos,
matrices, XYZ, STQ y estados preparados. La repetición produjo el mismo informe.
Sus conclusiones se limitan a esa etapa; los informes siguientes añaden la
evidencia de consumo GS y píxeles.

Informes adicionales, deterministas al repetirlos:

- `reports/local/f03-02-map-gs-v1.json`: 6.054 bytes, SHA-256
  `aa7c2bdde2d0fed8b3bcd5743f57184ea8ee68d55ab578f8a45aebc07d696661`.
- `reports/local/f03-02-map-pixels-v1.json`: 16.235 bytes, SHA-256
  `befdcbd7fa06305310f2ba76187e6d8315556666b8d8a3d417821a16e5eed285`.

`audit_gs.py` reproduce la correlación GS y `pixel_probe.py` el contraste de
píxeles, dentro de `build/f03-02-map-runtime/`. El segundo usa Pillow del
runtime local y el intérprete del proyecto para leer ZIP-Zstandard mediante
el lector acotado. Los informes exportan hashes, estados y estadísticas;
los recursos, imágenes y vértices permanecen privados.

```sh
rtk proxy .venv/bin/python build/f03-02-map-runtime/audit_gs.py
rtk proxy /Users/germancontreras/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 build/f03-02-map-runtime/pixel_probe.py
```

Validación final: **235 pruebas aprobadas** —184 existentes de savestates,
PINE y metadatos de render, 35 de repositorio y 16 sintéticas del lector GS
local—, JUnit `build/f03-02-map-runtime/gs-pixel-tests.xml`. Las dos auditorías
se repitieron con hashes idénticos a los registrados. Estas pruebas y la
reproducción software no sustituyen la comparación pendiente en New 2DS XL.

## Siguiente paso: material en el visor

MR-T4d habilita especificar e implementar el material y la transformación de
estas dos formas en el visor. Deben conservarse responsabilidades separadas
para decodificación, modelo de material y adaptador Citro3D; cubrir escalas
PS2 de color/alpha, UV, filtrado, niebla, culling y profundidad con fixtures
sintéticos y comparación del build en New 2DS XL. F03.02 y MG-T4 siguen
abiertas hasta completar sus entregables; este cierre no modificó el visor.
La [integración posterior MI-T1–MI-T4](f03-02-material-inspection.md) ya está
implementada, compilada y confirmada funcionalmente en New 2DS XL.
MG-T4 queda cerrada para estas dos formas; F03.02 conserva sus demás instancias.
