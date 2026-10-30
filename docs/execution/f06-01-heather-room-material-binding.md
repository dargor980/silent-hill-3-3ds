# HM-T4c.3.2 — Asignaciones y estados originales de hp34

2026-10-30. **HM-T4c.3.2 completada** según
[HRB01–HRB06](../../schemas/heather-room-material-binding-v1.md).
Las **29 formas internas** tienen banco, selector de paleta y material
preparado verificados contra el consumidor europeo y dos capturas originales.
**26 se envían al GS** en los dos cuadros del volcado; las otras **tres están
omitidas por sus etiquetas DMA** en ese estado. Esa distinción forma parte
del resultado, no se convierte en una afirmación de visibilidad de las 29.

La auditoría reutiliza evidencia privada existente, sin arrancar otra VM.
El build funcional `161090bc9fd5` continúa instalado; integrar los materiales
y generar otro build corresponde a **HM-T4c.3.3**. HM-T5 sigue aplazado.

## Evidencia y alcance

- Fuentes A/B y oráculo de índices/paletas de
  [HM-T4c.3.1](f06-01-heather-room-material-candidates.md), anclados por el
  informe `959ea2a0861120936b135a30416c57649c23c4d4844b294f1e12ee2e53ff7719`.
  Se releen sus cuarenta entradas de custodia, incluidos los recursos A/B.
- Estado v3, slot 12, PC `001B2440`, y v5, slot 06, PC `001B175C`.
  Conservan los mismos bytes completos de hp34 y las mismas nueve
  asignaciones internas. Sus hashes se contrastan con la evidencia histórica
  de [banco/selección](f03-02-map-runtime-binding.md) y
  [consumo GS](f03-02-map-draw-state.md).
- ELF europeo `SLES_514.34`, SHA-256
  `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`:
  doce ventanas coinciden byte a byte con la RAM de ambas capturas.
- Volcado GS original v6, SHA-256
  `4ce2e101e325e92ef68ac521bd6329fcd12cdf68ea09275aeab3d2e68ab2c801`.
  Reproducción diagnóstica con cámara controlada, recursos/código sin parches;
  no acredita una partida normal de hospital.

Se verifican 28 transferencias internas: índices y CLUT de siete bloques,
en dos cuadros. Los bytes completos coinciden con las fuentes privadas.
El seguimiento conserva el orden temporal y descarta asociaciones anteriores
cuando otra transferencia sobrescribe la misma zona. Esto importa porque
los bloques 0/5 y 1/6 reutilizan direcciones GS: TEX0 por sí solo no identifica
el recurso.

Por cuadro se cotejan **239 paquetes**, **15.890 registros de vértices** y
**4.912 triángulos con emisión habilitada**. Los 31.780 registros de ambos
cuadros coinciden con la secuencia completa de rangos DMA, incluidos los dos
vértices repetidos entre lotes. La selección de forma utiliza XYZ/STQ antes
de comprobar su material. El límite prefijado es dos unidades fijas GS;
el error máximo observado es **una**. UV se contrasta en unidades fuente
Q15 con límite 0,25; no se introduce inversión V en el cotejo GS.

Esto comprueba asignación, envío y estados. No es una nueva auditoría de
píxeles interiores de las 29 formas, ni reproduce toda la iluminación del
juego, ni valida estos materiales en la consola.

## Recorrido del consumidor europeo

`001AE9F0` prepara el contexto, registra la sección interna mediante
`001ABD90` y llama a `001AE3F0` para los grupos de la raíz interna. Este
último mantiene el **ordinal del recorrido** en `fp`; en `001AE4D0` lee el
selector de la malla +16 y llama a `001ABCC0`. Ese getter toma el gestor en
`banco + 0x44 + ordinal*16` y llama a `001B5F20` en modo 1, que devuelve
`gestor + 0x80 + selector*48`.

La correlación anterior `group.word20 - 1` da el mismo resultado en hp34,
pero **el índice consumido lo determina el recorrido**, no una lectura de
ese word como identificador de textura. Los IDs TEX `-1` tampoco intervienen.

Se comprueban el puntero de cabecera de cada entrada, el mismo puntero en
gestor +`0x20`, las cuatro referencias TEX0 del setup y el descriptor asociado
a cada malla. Cada cadena de forma termina en el retorno correcto y cubre
todos sus vértices, sin saltos ni referencias fuera de rango.
`001B0720` devuelve descriptor +`0x60` para sus parámetros.

`001AC5A0` interpreta **mesh +22**: modo 0 escribe TEST `5800C`, modo 3
escribe TEST `5800D`, modo 1 escribe ALPHA `44`. `001ACA20` prepara PRIM
`3C` o `7C` según la mezcla. Los halfwords +18/+20 conservan su condición
no interpretada; este resultado no les asigna semántica adicional.

## Correspondencia completa

Los offsets son relativos al MAP. «Omitida» significa setup y cadena
verificados, sin envío en los cuadros observados.

| Forma | Bloque interno | Selector CLUT | Material | Estado observado |
|---:|---:|---:|---|---|
| 1616 | 0 | 0 | Opaco | GS |
| 11408 | 0 | 0 | Opaco | GS |
| 34208 | 0 | 0 | Opaco | GS |
| 74144 | 0 | 0 | Opaco | GS |
| 130368 | 1 | 0 | Opaco | GS |
| 131248 | 1 | 0 | Opaco | GS |
| 145856 | 1 | 0 | Opaco | GS |
| 149376 | 1 | 0 | Opaco | GS |
| 149504 | 1 | 0 | Opaco | Omitida |
| 150816 | 1 | 1 | Descarte alfa >0 | GS |
| 154976 | 1 | 1 | Descarte alfa >0 | GS |
| 159280 | 2 | 0 | Opaco | GS |
| 169008 | 2 | 0 | Opaco | GS |
| 181920 | 2 | 0 | Opaco | GS |
| 206816 | 2 | 0 | Opaco | GS |
| 222736 | 2 | 0 | Opaco | Omitida |
| 226464 | 3 | 0 | Opaco | GS |
| 229600 | 3 | 0 | Opaco | GS |
| 232784 | 4 | 0 | Opaco | GS |
| 234704 | 4 | 0 | Opaco | GS |
| 238704 | 4 | 0 | Opaco | GS |
| 243280 | 4 | 0 | Opaco | GS |
| 245648 | 4 | 0 | Opaco | Omitida |
| 246928 | 4 | 14 | Mezcla alfa | GS |
| 247248 | 4 | 14 | Mezcla alfa | GS |
| 247840 | 5 | 0 | Opaco | GS |
| 250272 | 5 | 0 | Opaco | GS |
| 253936 | 6 | 0 | Opaco | GS |
| 255568 | 6 | 0 | Opaco | GS |

Las tres omisiones corresponden a palabras de forma +20/+24 `(2,0)`,
`(2,1)`, `(2,0)`, codificadas como `10000`, `10001`, `10000`.
Sus llamadas contienen `11000000` (CNT, QWC cero), que no sigue el puntero
de la cadena; las 26 llamadas habilitadas contienen NEXT `20000000`.
No se interpreta todavía el significado jugable de esos dos índices ni
se afirma que las formas permanezcan ocultas en otros estados.

## Estados efectivos

Las nueve combinaciones usan PSMT8 **512×512**, paleta PSMCT32/CSM1,
TCC=RGBA, TFX=MODULATE y CLD=1. El selector desplaza CBP cuatro bloques
GS de 256 bytes por unidad. Se conservan las paletas y alfa originales;
el informe incluye sus hashes y los RGBA resultantes del oráculo anterior.

| Campo | 25 opacas | 2 con descarte | 2 con mezcla |
|---|---|---|---|
| Mesh +22 | 0 | 3 | 1 |
| PRIM | `3C` | `3C` | `7C` |
| TEST | `5800C` | `5800D` | `5800C` |
| Prueba de alfa | Desactivada | GREATER, referencia 0 | Desactivada |
| Mezcla | Desactivada | Desactivada | `(Cs−Cd)*As/128 + Cd` |
| ALPHA | `44`, inactivo | `44`, inactivo | `44`, activo |
| ZBUF | `3A0001C0` | `3A0001C0` | `3A0001C0` |
| Escritura de profundidad | Sí | Sí, si pasa alfa | Sí |
| Alfa de vértice observado | 0 | 127 | 127 |
| Rango RGB de vértice observado | 1–129 | 17–109 | 17–89 |
| Rango de niebla observado | 95–248 | 222 | 187–215 |

Los rangos proceden de las formas enviadas: no se atribuyen colores ni niebla
observados a las tres omitidas. PRIM habilita interpolación, textura y niebla;
el color de niebla es negro. ZTE está activo, ZTST=GEQUAL y el formato de
profundidad es PSMZ16S. No hay prueba de alfa de destino, PABE ni dithering.
La modulación utiliza color de vértice y alfa PS2; no equivale a mostrar
la textura con blanco plano. No se ha identificado aquí toda la función
dinámica que genera esos colores y valores de niebla.

TEX1=`60`: filtrado lineal, MXL=0. **CLAMP=`0`: repetición U/V**, distinto
del vidrio externo ya integrado. TEXA=`8000000040`; no hay escritura TEX2
intermedia que invalide los TEX0 examinados. El framebuffer alterna entre
`80100` y `80000`, sin máscara de canales.

Orden de mallas observado en ambos cuadros:
`1520 → 130272 → 150720 → 159184 → 226368 → 232688 → 246832 → 247744 → 253840`.
La malla con mezcla aparece antes de las dos últimas opacas. La futura
integración debe conservar este orden; ordenar todas las transparentes al
final cambiaría la secuencia original. Tampoco puede heredar del vidrio
externo su clamp ni su máscara de profundidad.

## Reproducción y validación

Herramienta pura: `tools/inspectors/map_material_binding.py`.
Auditor privado: `tests/heather_room_material_binding_audit.py`.
Los fixtures públicos inventan RAM, DMA, geometría y transferencias;
ningún payload del juego se publica en Git.

```sh
rtk proxy .venv/bin/python tests/heather_room_material_binding_audit.py \
  --private /Users/germancontreras/sh3-private-data \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --output reports/local/heather-room-material-binding-recheck.json
```

El destino debe ser nuevo. Informe final:
`reports/local/heather-room-material-binding-v4.json`, **164.786 bytes**,
SHA-256 `5ebe66786a34543c058451b7e9637b0e528ed50b3a07109c850cde1078ac5073`.
La repetición `-O` produce bytes idénticos. Registra 46 entradas de custodia,
doce ventanas de código, 29 cadenas por captura, hashes de paletas/RGBA,
28 transferencias y estados/color/niebla por forma y cuadro.
Los informes v1–v3 se conservan como iteraciones locales anteriores; v4
comprueba la secuencia completa de vértices y rechaza intercalaciones de
paquetes entre formas.

**90 pruebas propias pasan**, con **100% de líneas y ramas** del inspector
(146 sentencias, 46 ramas). Cubren referencias, límites, visibilidad,
secuencias omitidas/repetidas, XYZ/STQ ambiguos, cambios TEX2, filtros,
alpha/profundidad, cargas partidas, CLUT incorrecta y sobrescritura de
direcciones. **592 pruebas de regresión pasan**, incluidas las 90 propias. Ruff, formato,
comprobaciones de repositorio y `git diff --check` pasan. Los resultados quedan registrados en `build/heather-room/material-binding-v1/`.

## Siguiente paso

HM-T4c.3.3 puede consumir estas nueve asignaciones internas verificadas.
Debe preservar la visibilidad documentada, el descarte alfa, la mezcla con
escritura de profundidad, el wrap y el orden; declarar cualquier aproximación
de iluminación/niebla y comprobar su imagen. El presupuesto candidato sigue
siendo **26,5 MiB de texturas con Heather**, con tres formas preparadas
pero omitidas por estado; la carga final y memoria total deben recalcularse
en esa integración. No se ha generado un nuevo build en HM-T4c.3.2.
