# F03.02 — Imágenes y vínculos del material del caballo

2026-10-20. **CT-T1–CT-T3 completadas** después de la confirmación funcional
de la [malla animada en New 2DS XL](../compatibility/character-inspection.md).
Se recuperaron tres imágenes de 512×512, sus cuatro unidades CLUT y las
referencias de las 15 submallas. [Contrato EARS CT01–CT05](../../schemas/ps2-character-materials-v1.md).

Al cerrar CT-T1–T3, CT-T4 y CT-T5 quedaban pendientes. **CT-T4 se completó
posteriormente para la pasada capturada** en el
[informe de material en PCSX2](f03-02-character-material-runtime.md).
[CT-T5a–d, visor texturado](f03-02-character-material-inspection.md), completadas
el 2026-10-22. Tras corregir el shader, **CT-T5e.1 funcional aprobada** con
`ced27c955e41`: usuario confirma 60 segundos, texturas, Q12 y controles.
Tiempos CT-T5e.2 pendientes; [iluminación LI-T1–T3](f03-02-character-lighting.md)
contrastada posteriormente, aún sin integrar al visor.
Esta ejecución no cambia el build `757b48fd1746` de la consola. La apariencia
de los PNG y la partición opaca del MDL no demuestran cómo aplica el juego
alpha, filtrado, clamp, iluminación o descarte de fragmentos.

## Resultado estructural y visual

| Descriptor / imagen | Submallas (índices desde cero) | Selector almacenado | Alfa PS2 usado |
|---|---|---:|---|
| 0 | 0–5 | 0 | 0–128 |
| 1 | 6–8 | 0 | 0–128 |
| 2 | 9–14 | 0 | 128 |

La tabla de imágenes es `0,1,2`; las tres parejas descriptor/selector son
`(0,0)`, `(1,0)`, `(2,0)`. Las 15 submallas pertenecen a la partición opaca.
Sus palabras de cabecera se conservan: el candidato `material_type=2` y
`display_group=0` no se convierten en estado GPU por su nombre.

El sector empieza en `0x8700`, ocupa 799.152 bytes y termina exactamente en
el final del MDL (`0xCB8B0`). Cada imagen contiene 262.144 bytes de índices
transferidos como PSMCT32 y leídos como PSMT8; cada CLUT ocupa 4.096 bytes.
La primera cabecera de imagen mide 96 bytes y las otras dos 80. Se validan
los contadores de archivo/modelo/sector, tabla, rangos y relleno, sin usar el
byte bajo del tamaño total como sustituto del tamaño completo de cabecera.

La inspección privada muestra superficies con pliegues y franjas en las
imágenes 0/1; en la 2 se distingue la cabeza, arneses y una franja del poste.
Los contornos y detalles son continuos, sin cortes evidentes entre bloques.
Esta descripción es observación visual del atlas, no prueba de UV en escena.
Los RGBA conservan alfa original; únicamente el PNG usa `min(255,2*a)`.

Se preservan las cuatro unidades CLUT, incluidas las no usadas. **Solo se
interpreta selector cero**: los índices de unidades almacenadas no se
equiparan automáticamente a selectores CBP no cero. Otras selecciones y
tablas de imágenes distintas de la identidad se rechazan explícitamente.

## Implementación y pruebas

El decoder puro `ps2_character_materials.py` compone los lectores existentes
de malla, sector e índices. Valida el presupuesto antes de decodificar y
mantiene separados estructura y píxeles. El coordinador
`decode_character_materials.py` verifica adquisición, construye metadata y
previews y delega escritura al adaptador privado exclusivo. No cambia C++,
el renderer, el shader ni los formatos SCM/SAN de la entrega probada.

**363/363 pruebas relacionadas aprobadas, 38 nuevas.** Incluyen dos imágenes
sintéticas distintas, todas las unidades CLUT, enlaces por submalla, rechazo
de selector no soportado, solapamientos, recuentos cruzados, PSMT4/CLUT fuera
del perfil, tamaño exacto, presupuesto antes de píxeles, identidades, error
de I/O, modificación de ISO al cerrar, determinismo y salida exclusiva.
La CI host descubre estos tests; no necesita originales ni red.

Cobertura de los dos módulos nuevos: **98,64 % líneas/ramas combinadas**;
decoder puro 100 %. Falta únicamente el despachador `__main__`, usado en
ejecución fuera de cobertura. Ruff y contratos del repositorio pasan.
JUnit y cobertura: `build/character-materials/pytest-final.xml` y
`coverage-final.json`. No se repitió toda la suite Python, ni se ejecutó
un pipeline remoto o una nueva compilación ARM en esta tarea.

## Contraste independiente

Un auditor separado relee el MDL y comprueba tablas, cabeceras y enlaces sin
importar los nuevos decoders. Reconstruye la memoria de subida PSMCT32 y
lectura PSMT8 mediante las tablas de páginas/bloques/columnas de
[GSTables.cpp de PCSX2, revisión fijada](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSTables.cpp).
Para CLUT usa su tabla `clutTableT32I8` sobre memoria subida, no la fórmula
compacta del decoder. No se ejecuta ni integra código externo en el pipeline.

Resultado: **786.432 índices y píxeles RGBA**, cero diferencias; **3.072 colores
de paleta** conservados exactamente. Un lector PNG independiente comprueba
chunks/CRC, descomprime filas y contrasta los píxeles normalizados. Los
controles negativos de píxel alterado, paleta incorrecta e inversión vertical
fallan como se esperaba. Este cálculo con tablas GS no es una captura de
ejecución de PCSX2 y no cierra CT-T4.

Referencia GS SHA-256 `a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8`.
Auditor local `build/character-materials/audit_materials.py`, SHA-256
`7367265dcffca04bb9ddac07e836c80524eeea9969567dfd50a1afe33a7f5219`.
Informe: `reports/local/f03-02-character-material-audit-v1.json`.
La referencia de estructura Murugo fijada en el contrato se consultó como
fuente de hipótesis; no se ejecutó su importador Blender.

## Procedencia y entrega privada

MDL: 833.712 bytes, SHA-256
`120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672`.
Selección: `reports/local/f03-02-skeleton-selection-v1.json`, SHA-256
`bc81ec9fb2191c5cb434db886e0a6bf1d3c080329d53315e482292257cc264e8`.
Se verifican ISO y XBG0.MFA completos antes de extraer el MDL por ordinal.

Raíz privada autorizada: `/Users/germancontreras/sh3-private-data/`.
Dos adquisiciones independientes finales:
`f03-02-character-material-a-v2/` y `f03-02-character-material-b-v2/`.
**22 archivos, 4.511.936 bytes por entrega**, más manifiesto; ambas son
idénticas byte a byte. Los ensayos v1 se conservan; v2 explicita la política
de selector cero, con los mismos píxeles. Manifiesto final SHA-256
`15d127ffa1534f17272454574f9bbaa70f8ebbd2007893b43b9e707831f30be9`.

| Archivo | SHA-256 |
|---|---|
| materials.json | `d0ccc22515dc2fa21784f04deeb7e0609c414611722c936ef3c64fa4e59b78ea` |
| texture-0.rgba | `84e8ef0f7bab22dad004a212bd19853b833a5e9858439aa1b899ef1d6347c4a3` |
| texture-1.rgba | `6bd431beb3e887bbb30c76809638643fcf81f3b515457aa1be5aac52181adfa3` |
| texture-2.rgba | `34c3fc2958f7b129db0c4861f07d7d20db2c47c5eb886a3fa2fb3116510e248d` |

Reproducción: `python -m tools.pipeline.decode_character_materials --help`;
usar la selección/hash anteriores, ISO autorizada y un run-id privado nuevo.
Los derivados originales y PNG no se incluyen en el repositorio ni en CI.
Índice de fuentes, resultados y confirmación física previa:
`reports/local/f03-02-character-material-execution-v1.json`.

La verificación posterior de **CT-T4** enlaza las 15 submallas, tres texturas,
428 paquetes GS y 15.112 píxeles interiores: mezcla y prueba alfa desactivadas,
modulación, bilineal, clamp y escritura de profundidad. CT-T5a–d integran
el material al visor respetando esos límites; siguiente: **CT-T5e física**.
CM-T5e.2 mantiene pendiente la duración y detalles complementarios físicos;
sí se registran las lecturas comunicadas por el usuario de ≈14/≈12/1,1 ms.
