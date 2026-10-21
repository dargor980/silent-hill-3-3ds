# Cobertura de formatos PS2

Actualización: 2026-10-20. Instancia preparatoria de F03.01, independiente del
cierre global de G02. [Contrato TEX01–TEX07](../../schemas/ps2-texture-probe-v1.md)
y [ejecución reproducida](../execution/f03-01-texture-structure.md).

## Referencia fijada

Sparagas/Silent-Hill, commit `f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35`,
licencia MIT. Autores indicados: Laurynas Zubavičius (Sparagas) y Rodolfo Nuñez
(roocker666). Se inspeccionaron el
[plugin](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/Noesis%20-%20Python%20Plugins/tex_sh2_sh3_ps2_tex_tbn2.py)
y la
[plantilla binaria](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/010%20Editor%20-%20Binary%20Templates/sh2_sh3_ps2_tex_tbn2.bt).
El antiguo nombre `fmt_sh3_ps2_tex.py` del README indexado ya no existe en esta
revisión; la referencia vigente es `tex_sh2_sh3_ps2_tex_tbn2.py`.

| Archivo consultado | SHA-256 |
|---|---|
| Plugin, 9.034 bytes | `789b51877bede23ebe47d537efb2cfe5cd64a066167397ee09a80182e60c66d1` |
| Plantilla, 4.773 bytes | `1675ae166674c8dc92014400a96bf5aab3fed4eff0566c4bb98b4c5ddda538b3` |
| LICENSE, 1.076 bytes | `26f743052bafcf49c229e0a9f8bb694b3f0a5e22fafc099a2e8231778a059e54` |

Los archivos públicos consultados y su licencia se conservan en
`build/f03-01/reference/`. Son referencia de investigación; no dependencia
incorporada al pipeline ni código copiado al parser propio. No se instaló ni
ejecutó Noesis, por lo que no se atribuye compatibilidad a una versión de su host.

## Matriz de evidencia estructural — F03.01

| Unidad | Evidencia local | Estado / límite |
|---|---|---|
| Cabecera de área SH3 `-1`, contenido en 32 | 119/119 entradas de ambas copias | Estructura aceptada por el subconjunto v1 |
| Cabeceras indexadas 8 bpp, PSM 0/0x13 | 281 bloques | Rangos y tamaños coherentes; píxeles sin decodificar |
| Cabeceras indexadas 4 bpp, PSM 0/0x14 | 40 bloques | Subpaletas y píxeles sin decodificar |
| CLUT de 4/8/16 unidades declaradas | 228/28/65 bloques respectivamente | Tamaños 4096/8192/16384; orden y selección sin validar |
| Relleno anterior a índices | 9 discrepancias con el byte declarado | Rango calculado por `all_size - data_size - 48` |
| Datos opacos | Valores numéricos y hashes completos de headers | Sin semántica atribuida a GIFtag, offsets CLUT, flags ni materiales |
| Campos de área `lastOffset` | 84 apuntan al final y 35 al último header | Ambas formas aceptadas; no se infiere semántica adicional |
| Cabecera SH2, sin cabecera, 24 bpp, contador cero y otros CLUT | Sin ensayo de este subconjunto | Desconocidos; no soportados por el sondeo v1 |
| RGBA, alpha, orientación, UV, animación y dependencia de sala | Sin comparación de salida | Pendientes; no declarados soportados |
| Noesis / 010 Editor ejecutándose | Solo revisión de código y layout | No ejecutados; sin comparación visual del plugin |

Las dimensiones observadas son 256×256 (55 bloques), 512×512 (226) y 512×1024
(40). La extensión selecciona candidatos; la aceptación exige recorrer headers,
validar rangos y consumir el archivo exactamente. El inventario previo no se
reescribe ni se promueve: `classification.type=unknown`, `capabilities=[]`.

## Primera muestra para F03.02

Se seleccionó un recurso de un solo bloque, 8 bpp, 256×256 y cuatro unidades CLUT
declaradas. Criterio determinista: menor cantidad de píxeles, luego tamaño,
ID y ordinal. Tamaño del recurso: 69.808 bytes; índices en 128, longitud 65.536;
CLUT en 65.712, longitud 4096. ID y hashes están en el informe privado de selección,
enlazado al hash del sondeo. No se eligió una sala por el nombre del archivo.

Pasos concretos pendientes:

1. Fijar el contrato del orden de índices PS2 para este bloque de 8 bits, con
   patrón sintético asimétrico y comparación independiente del direccionamiento.
2. Separar las unidades CLUT y comprobar la permutación de colores; conservar
   paletas y alpha originales antes de cualquier conversión.
3. Producir RGBA y preview privados reproducibles; contrastar orientación,
   colores y transparencia con una segunda lectura o referencia visual.
4. Solo después integrar la imagen validada en una entrega privada para la 2DS
   XL, conservando procedencia y receta. Las variantes de 4 bits tendrán su caso.

## Actualización de píxeles — F03.02

La [instancia de 8 bits/cuatro CLUT](../execution/f03-02-indexed-texture.md) ya
produce índices, paletas, RGBA original y vistas PNG. Los pasos 1–2 y la generación
repetible del paso 3 se completaron para la muestra de 256×256. Dos conversiones
desde las extracciones privadas coinciden byte a byte, y el mapa de índices se
contrastó con tablas GS independientes. La paleta 0 muestra una superficie gris
desgastada; las otras tres son uniformes 0xCC y se conservan.

La inspección de PNG no equivale a comparar el material en el juego original.
Esa parte del paso 3 y el resto de variantes siguen pendientes. La integración
del paso 4 como visor privado se completó con
[TI-T1–TI-T5](../execution/f03-02-texture-inspection.md), incluida confirmación
física del usuario en New 2DS XL.
La CLI declara `decoded_candidate`, sin elevar capacidades del perfil ni
atribuir una sala, selección de paleta o modo de material.

## Actualización de metadatos del render — F03.02

[MR-T1–MR-T3](../execution/f03-02-map-render-metadata.md) añaden partición de
raíces por contador, localización del registro base y palabras de modo de forma.
El subconjunto probado tiene un registro base y ocho grupos; otras variantes
se rechazan. Evidencia estática europea, 398 pruebas y dos informes idénticos.
No acredita todavía textura asignada, alpha, transformación final ni captura
del material en ejecución.

## Actualización de mapa candidato — F03.02

[MP-T1–MP-T3](../execution/f03-02-map-material-candidate.md) verifican la
estructura de un MAP seleccionado por relación de nombre con la muestra:
8 grupos únicos, 10 mallas, 10 submallas, 31 formas y 15.882 vértices declarados.
Dos raíces comparten cola; no se duplica esa geometría en el conteo.
Una sección embebida distinta de la textura externa contiene siete bloques
de 8 bits/512×512. Lecturas de ambas copias idénticas y 233 tests aprobados.

El grupo pequeño de dos formas/56 vértices se
[decodificó después con MG-T1–MG-T3](../execution/f03-02-map-geometry.md):
32 triángulos, posiciones/UV locales y atributos originales conservados.
JSON/OBJ coinciden en ambas copias y se inspeccionaron en el host.
No se ha demostrado la selección de textura/CLUT, transformación o uso en PS2.
`material_binding=unverified`.

## Actualización posterior — material y convenciones estáticas

El estado `unverified` anterior corresponde a la salida histórica del sondeo.
[MR-T4b/c](../execution/f03-02-map-runtime-binding.md) identificaron después
el recurso del banco y CLUT 0; [MR-T4d](../execution/f03-02-map-draw-state.md)
contrastó modelo, UV, consumo GS y transparencia de las dos formas.
[MI-T1–MI-T4](../execution/f03-02-material-inspection.md) integran el material
y modelo; el usuario confirma paneles con transparencia, controles, START,
tapa y HOME en New 2DS XL para `764be66e7762`.

[GC-T1–GC-T3](../execution/f03-03-static-geometry.md) fijan el contrato
estático de columnas/base/UV/winding y sus controles asimétricos, con
regresión exacta de la entrega privada. No se extiende la cobertura a
otros MAP/materiales, esqueletos, animación, colisión o cámara de juego;
los informes previos y sus hashes se conservan sin promover capacidades.

## Esqueleto y animación — subconjunto SA

[SA-T1–SA-T4](../execution/f03-02-skeleton-animation.md) añaden una pareja
MDL versión PS2 3 / ANM `0x0209` de XBG0: tres huesos, dos raíces y 76 muestras.
La jerarquía, matrices almacenadas y registros de rotación/traslación se
decodifican conservando bits originales y flags opacos; reconstrucción exacta
y dos aperturas independientes coincidentes. La receta de 46 bytes por
muestra no se generaliza a otros IDs. Las variantes inválidas se rechazan.

No se decodifican malla, pesos, helpers o morphs de MDL. No se interpretan
clips, frecuencia, interpolación, pose, root motion o selección del juego.
SA-T5 y GC-T4 requieren evidencia del consumidor en ejecución. Los 401 nombres
`.mdl` y 116 `.anm` encontrados son candidatos, no recursos soportados.
