# F06.03 / HS-T2 — contrato de paletas y vectores

2026-10-30. **HS-T2 completada en su alcance de contrato y SDK.**
[HSN v1](../../schemas/heather-skinning-native-v1.md) fija paletas de 30
matrices afines, atributos, remapeo, orden, tolerancias y fallos del
prototipo híbrido. **Sigue HS-T3**, implementación y ensayo host.
`0188790baedd` continúa siendo el build de consola; no se generó una nueva
aplicación ni se copió a SD. HM-T5 adicional y pared 60 siguen aplazadas.

## SDK comprobado

Imagen local autenticada por digest:
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
Image ID: `23e9c452eafb9bd85c7a5fbf1f6ebb05f22f086f5f14cc73fcc6dbcd5a32a71c`.
Paquetes: citro3d 1.7.1-2, libctru 2.7.0-1, picasso 2.7.2-3,
devkitARM r68-1. Contenedores temporales sin red, memoria máxima 512 MiB;
sin reiniciar Docker ni interrumpir servicios.

| Verificación | Observado |
| --- | --- |
| Uniformes flotantes Citro3D | 96; 4 enteros |
| Atributos/buffers Citro3D | 12; guardas `cmp #12` en biblioteca ARM |
| ABI C3D_FVec | 16 bytes; W/Z/Y/X a offsets 0/4/8/12 |
| ABI del vértice propuesto | 64 bytes, campos a 0/16/32/48, alineación 4 |
| Sonda skinning | 28 instrucciones, 12 descriptores, 12 componentes de salida escritos una vez |
| Paleta/vista/constante | c0..89 / c90..93 / c95; c94 libre |
| Frontera del ensamblador | 96 fvec aceptados; 97 rechazados; 96 + constante rechazados |
| 31 matrices × 3 filas + vista + constante | Rechazado por falta de uniformes |
| Registros probados | v11/v12/v14, r15 y c95 aceptados; v15/v16, r16 y c96 rechazados |
| Dos entradas distintas en MUL | Rechazado |

**16 comprobaciones de Picasso** y objeto de aserciones estáticas ARM
aprobados. Los resultados son del SDK instalado. El manual general describe
v0..v15, pero esta versión rechaza v15; no se extrapola ese texto a una
capacidad aceptada por el compilador. La sonda usa solo v0..v3.
El `WritePtr` de uniformes carece de comprobación de rango: el contrato
exige validarla en el adaptador antes de escribir.

Fuentes primarias de contraste:
[manual de Picasso 2.7.2](https://github.com/devkitPro/picasso/blob/v2.7.2/Manual.md),
[asignación y registros del ensamblador](https://github.com/devkitPro/picasso/blob/v2.7.2/source/picasso_assembler.cpp),
[atributos Citro3D 1.7.1](https://github.com/devkitPro/citro3d/blob/v1.7.1/source/attribs.c),
[envío de uniformes](https://github.com/devkitPro/citro3d/blob/v1.7.1/source/uniforms.c),
[vectores y orden de componentes](https://github.com/devkitPro/citro3d/blob/v1.7.1/include/c3d/maths.h),
[carga del shader en libctru 2.7.0](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/gpu/shaderProgram.c).
Esta última limita la carga vertex a 512 instrucciones; el contrato rechaza
una salida fuera del perfil exacto antes de llegar a esa truncación.
Las cabeceras y las bibliotecas instaladas quedan identificadas por hash.

## Resultado sobre A/B y memoria estructural

Relectura autenticada del SRI2 A/B fijado en HS-T1, con contenido y padres
verificados: capacidad 30 da **15 lotes opacos**, 200 matrices sumadas entre
lotes y **6558 vértices** si se duplican por lote, frente a los 6553 únicos
opacos. Los 15846 índices conservan el orden original. El cabello conserva
371 vértices/720 índices en CPU y se ordena con vidrio.

El formato propuesto requiere 419712 bytes de vértices y 31692 de índices:
**451404 bytes GPU estáticos activos**. Si staging y GPU coexisten son al
menos 902808 bytes, más planes, paletas y overhead. No se descuentan todavía
buffers del baseline ni se presenta esto como pico real, presupuesto
aprobado o mejora de rendimiento. HS-T3 verificará coexistencia y liberación
contra la reserva vigente de HG, incluido el coste de validación de opacos.

## Vectores y evidencia local

El fixture congela 54 casos numéricos, 6 particiones, 14 rechazos, 4 casos
de proyección y un orden transparente con empates. Incluye 15 ventanas
de los cinco clips y las 26 poses esperadas sintéticas de los cuatro arcos
HG. Se conserva el fixture HG original por SHA-256. El contrato no duplica
ni altera las reglas del reloj: recibe la pose final de cada caso.

El oráculo racional calcula primero la deformación y luego instancia/base;
otro recorrido prepara filas y atributos y evalúa las instrucciones del
SHBIN ensamblado. Compara bytes, remapeos, XYZ/W, UV/color y proyección.
Ese evaluador usa binary32 host: **no es un emulador PICA ni evidencia GPU**.
Las tolerancias de GPU y 0,25 píxel se fijan antes de ejecutarlo en consola.
Máximos observados host: `6.867048796266317e-8` unidades de habitación y
`1.3178607272124054e-5` píxeles. W intermedio coincide exactamente en los
54 casos. El [contrato](../../schemas/heather-skinning-native-v1.md) publica
los hashes congelados del fixture y del SHBIN; cambiarlos requiere versión
y evidencia nuevas.

**365 pruebas aprobadas**, incluidas 99 nuevas y las regresiones HS-T1/HG.
Oráculo: 100 % líneas / 98,33 % ramas; generador: 93,55 % / 91,67 %;
HS-T1: 100 % / 100 %. Los tres gates individuales pasan. Ruff/formato,
contratos del repositorio (0 errores) y revisión de whitespace aprobados.
Python host 3.14.6, pytest 9.1.1. CI incorpora el gate de los oráculos y
repite la sonda con el SDK fijado, sin recursos privados.

Evidencia en `build/heather-skinning-contract/` y el informe agregado
`reports/local/heather-skinning-contract-v1.json`: JUnit, cobertura,
sonda SDK, cabeceras, objeto ARM, SHBIN, particiones privadas sin payload
original y hashes de fuentes/fixtures. El SDK se puede repetir con:

```sh
rtk proxy docker run --rm --memory=512m --network none \
  --mount type=bind,source=/Users/germancontreras/silent-hill-3-3ds,target=/work \
  devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
  python3 /work/tests/heather_skinning_sdk.py
rtk proxy .venv/bin/python -m pytest tests/python/test_heather_skinning_contract.py tests/python/test_skinning_workload.py tests/python/test_heather_turns_contract.py
```

No se ha implementado todavía el renderer híbrido, probado su precisión
GPU, validado su pico real ni elegido la alternativa por rendimiento.
F06.03 global continúa abierta.
