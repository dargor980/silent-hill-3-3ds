# Perfil PS2 de Heather original, versión 1

Contrato de HI01–HI04. Los nombres identifican candidatos; la selección fija
ISO/MFA/ordinal/tamaño/SHA. `model_id=0x100` por sí solo no distingue atuendos.
El conjunto observado corresponde a `data/chr/pl/chhaa.mdl` y
`chhaa_basic1_none.anm`. Las capturas de carrusel con `chhcc.mdl` no acreditan
el atuendo original.

## Esqueleto y ANM

`sh3-ps2-anm-0100-264-v1` exige 73 padres, modelo `0x100`, cabecera de cuatro
bytes y muestras completas de 264 bytes. Límite: 512 KiB/4.096 muestras. Los
nibbles conservan bandera y signo de W; las traslaciones conservan palabras
float32 para raíces y float16 para hijos. Se rechazan referencias fuera de la
jerarquía, ciclos, valores no finitos, truncamientos y norma imposible. La
reconstrucción usa palabras originales, nunca floats derivados.

El archivo base observado contiene 1.763 muestras y 36 pistas por muestra.
El descriptor en RAM `(101,10,307,0,9,1)` identifica un segmento 0–9. Cuatro
capturas prueban un incremento de 614 y la evaluación anterior a dicho
incremento. No prueban todavía el wrap ni la frecuencia nativa completa.

## Morphs y malla

`sh3-ps2-mdl-morph-position-normal-v1` conserva ambas bases de int16×3,
alineadas a 16, y los objetivos dispersos de int16×4. El cuarto componente
es un índice, validado por separado en posiciones y normales. Los dos
listados pueden tener orden distinto. Máximos: 4.096 vértices base,
128 objetivos y 64 referencias por submalla. Los índices son únicos por
listado; se rechazan solapamientos, truncamientos y cuentas fuera de rango.

Cada referencia es `(índice_origen, dirección_VU, cantidad)`, uint16×3.
La cantidad es 1–256. El destino debe coincidir con la posición de un
vértice VIF, con paso de cuatro quadwords, dentro de la submalla, sin
solapar otra referencia. Se conservan deltas y referencias; no se evalúan
expresiones. El lector anterior de malla sigue rechazando morphs.

La máscara observada `0x3021` selecciona grupos 0, 5, 12 y 13 del campo
alto de `header_words[16]`: 79 submallas, 6.943 vértices y 5.522 triángulos.
Estas submallas no tienen referencias morph y usan 36 huesos/49 helpers.
Las 233 submallas y los 25 objetivos permanecen en la conversión completa.

## Índices y paletas GS

`sh3-ps2-indexed-csm1-selectors-v1` separa carga PSMCT32, índices PSMT8/PSMT4
y selección CSM1. Las dimensiones deben satisfacer el perfil de carga
existente; PSMT4 requiere páginas completas, altura ≥128. La paleta se
selecciona por desplazamiento real CBP, no por una supuesta columna de CLUT.

| Unidades cargadas | Bytes CLUT | Selectores válidos |
|---|---:|---|
| 4 | 4.096 | 0, 1, 4, 5 |
| 8 | 8.192 | 0–7 |
| 16 | 16.384 | 0–15 |

Se rechazan selectores que alcanzan memoria no cargada. PSMT4 usa 16 colores;
PSMT8 usa 256. Se conserva RGBA PS2; solo el PNG de inspección transforma
alfa mediante `min(255, 2*a)`. No hay inversión de filas. El oráculo externo
simula direcciones con las tablas fijadas de PCSX2 y comprueba 16 tamaños y
28 paletas. Su referencia privada no se incorpora a los fixtures de CI.

## Materiales y salida privada

El lector exige tabla de imágenes consecutiva, sectores no solapados con
geometría/morphs, bpp/bit_shift compatibles, ≤16 imágenes y ≤8 Mpíxeles.
Cada descriptor de textura debe seleccionar una paleta cargada. El conjunto
original tiene cuatro imágenes y 15 descriptores, 13 usados por la máscara.

`decode_morph_character` verifica de nuevo ISO, MFA y recursos. Escribe
geometría, materiales, índices, paletas, RGBA y PNG mediante el escritor
privado exclusivo. No sobrescribe destinos; exige el conjunto exacto de
archivos y conserva el límite existente de 40 MiB por paquete. Dos
conversiones desde la ISO deben producir archivos y manifiestos idénticos.

La prueba GS asocia 1.932 paquetes opacos y 240 triángulos de cabello con
las submallas seleccionadas. El cabello usa `(Cs-Cd)*As+Cd`, alfa `>50`
en escala PS2, profundidad GEQUAL con escritura habilitada y filtro lineal.
El opaco usa alfa `>0`, sin mezcla. UV, profundidad, pose, paletas y estados
se verifican por separado; ello no acredita equivalencia completa de raster,
iluminación, físicas ni ejecución en 2DS XL.
