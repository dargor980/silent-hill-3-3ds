# F03.02 — Primera pareja MDL/ANM decodificada

2026-10-20. **SA-T1–SA-T4 completadas** según
[SA01–SA08](../../schemas/ps2-skeleton-animation-v1.md). La pareja PS2 con
identificador `0x0209` produce **3 huesos, 2 raíces, 76 muestras y 228 registros
de transformación**. Dos aperturas independientes de la ISO producen bundles
idénticos. La lectura independiente confirma todos los registros y reconstruye
los 3.500 bytes del ANM exactamente.

Este informe corresponde a la decodificación de datos almacenados. La
[verificación posterior SA-T5a/b/c](f03-02-skeleton-runtime.md) ya confirma
selección inicial, tres clips, reloj Q12 e interpolación/composición modelo
en PCSX2. La CLI conserva muestras sin asignarles FPS. SA-T5d, GC-T4 y los
gates globales de F03 permanecen abiertos.

## Identificación y contenedor

El catálogo anterior de 61 MFA contiene escenarios, sin nombres `.mdl`/`.anm`.
La nueva lectura de `XBG0.MFA` verifica su hash completo y recorre **33 bloques,
1.488 entradas**, sin solapamientos. Hay 401 nombres ASCII terminados en `.mdl`
y 116 en `.anm`; son candidatos por sufijo, no una declaración de soporte.
Un nombre contiene bytes no ASCII: se conservan sin elegir Shift-JIS/CP932.

El parser MFA incorpora una opción explícita `opaque_bytes`, con los mismos
límites de estructura y cadena completa. En esa modalidad el nombre es
metadato binario y no una ruta; entradas con el mismo nombre mantienen
identidades distintas por bloque/índice. La política predeterminada conserva
ASCII, rutas seguras y rechazos de colisiones. El catálogo F02.04 original y
su rechazo de XBG0 se mantienen sin reescribir ni promover capacidades.

La pareja se eligió por tamaño pequeño, jerarquía no trivial y receta explícita
de animación en la referencia. Se fijaron ordinales, tamaños y hashes antes
de exportar. La coincidencia de IDs se verifica entre las dos cabeceras; no
sustituye una asociación observada en el juego.

| Entrada | Tamaño | SHA-256 |
|---|---:|---|
| ISO europea SLES-51434/PAL 1.02 | 3.586.785.280 | `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` |
| Contenedor XBG0 | 544.569.344 | `6b6dcef3243e62ce36c59bf3ae01a1acf88027d0b3e7b1fee980f95c8798a25d` |
| MDL, ordinal 142 | 833.712 | `120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672` |
| ANM, ordinal 140 | 3.500 | `cfb30d96574c34a0da2ab6f3be425e8c4d043f03a6ebf826418a89dbf07c8400` |

Los nombres originales en hex, localizaciones y procedencia quedan en el
manifiesto privado. Selección local:
`reports/local/f03-02-skeleton-selection-v1.json`, SHA-256
`bc81ec9fb2191c5cb434db886e0a6bf1d3c080329d53315e482292257cc264e8`.
El sondeo inicial se conserva en `reports/local/f03-02-skeleton-triage-v1.json`.

## Referencia primaria fijada

Murugo/Misc-Game-Research, commit
`c088e878544f25d45ea7cf4215613fb5f9638dd4`, licencia MIT.
Se consultó el código; no se instaló ni ejecutó Blender o el plugin.
Los parsers propios no dependen de ese código.

| Referencia | SHA-256 de la copia consultada |
|---|---|
| [import_mdl.py](https://github.com/murugo/Misc-Game-Research/blob/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3/import_mdl.py) | `66191680f7bc46602ab7dd4d2f7f912b3a01c95742681d1ddce026b6e9c70963` |
| [import_anm.py](https://github.com/murugo/Misc-Game-Research/blob/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3/import_anm.py) | `52f03bfab55f63e0719c91e1e61ceb3fc1e6557612a884e7c16ba7c7f4a38374` |
| [readutil.py](https://github.com/murugo/Misc-Game-Research/blob/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Common/readutil/readutil.py) | `b37ba3621fe37d30ccec7621499ed673826267e9fd612781be3dc271677233ed` |
| [LICENSE](https://github.com/murugo/Misc-Game-Research/blob/c088e878544f25d45ea7cf4215613fb5f9638dd4/LICENSE) | `282aef12fe79c159cda7d95f2977b8fb6c97ad132faff63fef1acd900657a413` |

Copias de investigación en `build/f03-02-skeleton/reference/`, ignoradas por Git.
La tabla del importador identifica el modelo `0x0209` con 46 bytes por muestra.
El lector confirma IEEE float16 para traslaciones de hijos. Los flags y
cuaterniones se interpretan según esa referencia, con conservación exacta de
los originales y límites adicionales del contrato propio.

## Datos conservados y límites

MDL versión PS2 3, modelo en offset 96, tres matrices por columnas de 64 bytes
y padres `[-1,-1,1]`. Se conservan floats y palabras uint32 originales,
incluido cero con signo. No se transforma el esqueleto a la base del visor
estático ni se decide aún si las matrices representan pose global o bind.
Mallas, helpers, pesos, morphs y texturas del MDL quedan sin decodificar.

La igualdad `3500 = 4 + 76 × 46` se confirma consumiendo cada registro.
En cada muestra hay flags `0x9AA`: dos raíces con XYZ float32 y rotación,
y un hijo con rotación sin traslación almacenada. El bit alto de cada nibble
se conserva opaco; no se le atribuye interpolación o activación.
Las rotaciones XYZ i16/32768 y W reconstruido se conservan por índice de
muestra. No se rellena una traslación ausente con cero ni con el valor anterior.

La auditoría independiente usa posiciones fijas de campos de esta muestra,
sin invocar los decoders de producción. Compara las tres matrices/padres y
los 228 registros; reconstruye el ANM completo desde sus palabras exportadas.
Calcula W con una expresión independiente en enteros antes de la raíz:
error observado **cero**. Detecta 1/73/73 rotaciones distintas por hueso;
no interpreta ese movimiento como una acción concreta.

## Implementación y pruebas

- `ps2_skeleton.py`: estructuras inmutables, rangos, padres, ciclos, matrices
  y reconstrucción; sin filesystem, host gráfico o SDK.
- `ps2_animation.py`: receta acotada, flags, traslaciones, cuaterniones,
  ausencia explícita de pistas y reconstrucción exacta.
- `decode_skeleton_animation.py`: selección fijada, puerto de identidad/rangos,
  lectura ≤4096 bytes, coordinación y CLI.
- Writer privado compartido: conjunto cerrado `skeleton.json`/`animation.json`,
  sin sobrescritura, verificación de escritura y manifiesto después de cerrar ISO.

**836/836 pruebas aprobadas**, incluidas **77 nuevas**. Cubren signos W,
traslaciones float32/float16, raíces múltiples, padres posteriores/ciclos,
grupos de flags dispersos, huesos ausentes, corrupción, truncamiento, límites,
identidad incorrecta, lectura corta y modificación de ISO antes del cierre.
Las regresiones incluyen MFA/variantes/mutaciones, catálogo, extracción,
interrupciones, writer, texturas, geometría, material y custodia del repositorio.

Cobertura de los cinco módulos afectados: **426/429 líneas (99,30 %) y
159/162 ramas (98,15 %)**. MFA y writer: 100 % de líneas/ramas. Las tres
líneas restantes son los rechazos defensivos de reconstrucción y el
despachador `__main__`, ejecutado en las dos conversiones reales.
Reportes: `build/f03-02-skeleton/regression.xml` y `coverage.json`.
Ruff, formato, gate independiente y contratos del repositorio: aprobados.

El job Python existente de CI descubre los casos nuevos con fixtures propios.
No se añade dependencia ni contenido original a CI. No se ha ejecutado CI
remota ni compilado otro build ARM: no cambió el motor de consola.

Manifiesto de 23 fuentes propias, pruebas y contrato:
`build/f03-02-skeleton/source-manifest.json`, 3.884 bytes, SHA-256
`fe3a903972c6da34eccb926707a249a67cb02f6f778742aa7d84008db356a0c3`.
Incluye dependencias Python locales transitivas del coordinador y excluye
datos privados, código externo y este informe para evitar autorreferencia.

## Entregas y reproducción

Raíz privada autorizada: `/Users/germancontreras/sh3-private-data/`.
Sesiones nuevas `f03-02-skeleton-a-v1/` y `f03-02-skeleton-b-v1/`.
Cada una verifica la ISO y el contenedor completos desde una apertura
independiente; no usa el corpus F02.05, que no incluía este contenedor.
Los tres archivos finales coinciden byte a byte:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| skeleton.json | 2.157 | `7e674347110fc35143a41371a552e27254783e587c6db99d7461165b15e41498` |
| animation.json | 133.955 | `b34f8ae4c257b8dba49c2abec1dd99074805cde8faca1a4215d819c71396abf9` |
| manifest.json | 10.226 | `4a53411124334fbcd7379a549f3ed0876b644a1b6a7910cb40c1077113405536` |

```sh
rtk proxy .venv/bin/python -m tools.pipeline.decode_skeleton_animation \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --selection reports/local/f03-02-skeleton-selection-v1.json \
  --selection-sha256 bc81ec9fb2191c5cb434db886e0a6bf1d3c080329d53315e482292257cc264e8 \
  --private-root /raiz/privada --run-id nueva-pareja
```

Repetir con otra sesión; las existentes se rechazan. Auditoría local propia:
`build/f03-02-skeleton/audit_pair.py`. Informe determinista
`reports/local/f03-02-skeleton-audit-v1.json`, SHA-256
`6fa0ce1de5e20f75128ef5236238df4f3fd4697dbc187bee40eb5fffaa947e2d`.
No se exportan matrices ni muestras a ese informe compartible.

## Continuación

[SA-T5a/b/c](f03-02-skeleton-runtime.md) localizan y contrastan el consumidor
europeo, selección inicial, clips, reloj y composición modelo. SA-T5d debe
medir una secuencia continua sin restauraciones y registrar selección por IA.
GC-T4 mantiene pendientes mundo, base 3DS y skinning; no extrapola
`(x,-y,-z)` de la geometría estática ni la interpolación de Blender.
