# Prueba física — visor de textura privada

Estado: **TI-T5 completada por confirmación del usuario**, New Nintendo 2DS XL,
Homebrew Launcher, build `a6a45e73a03d`, 2026-10-20. Tras corregir la ubicación
del paquete en SD, el usuario confirma textura visible, cruceta, controles de
cámara, regreso tras cerrar la tapa y usar HOME, y salida con START.
Esta confirmación corresponde al visor de textura privada.
[Resultado local](../execution/f03-02-texture-inspection.md) y
[requisitos TI01–TI07](../specs/sh3-3ds/texture-inspection.md).

## Preparación

Usar `f03-02-3ds-texture-v2/sd-card.zip` dentro de la raíz privada autorizada.
Extraer en la raíz de la SD, conservando `3ds/sh3_texture_probe/`.
Abrir **SH3 texture inspection** en Homebrew Launcher. No requiere instalar CIA
con FBI. La carpeta de la demo sintética es distinta y se conserva.

La pantalla inferior debe indicar **build `a6a45e73a03d`**. La superior debe
mostrar una superficie gris desgastada sobre un panel, con fondo azul oscuro.
La vista usa RGB opaco: no reproduce todavía el material original.

## Registro de aceptación TI-T5

| Comprobación | Resultado |
|---|---|
| Build mostrado | Confirmado en foto: `a6a45e73a03d` |
| Carga de textura sin error | Confirmada por el usuario tras corregir la ruta; `MISSING` resuelto |
| Textura visible | Confirmada por el usuario; sin nueva captura para comparación detallada |
| Cruceta: órbita y elevación | Confirmada por el usuario |
| X/Y: acercar/alejar; B: recuperar cámara | Controles de cámara confirmados por el usuario |
| START: volver al launcher | Confirmado por respuesta explícita del usuario |
| Cerrar/abrir tapa: recuperar imagen y controles | Confirmado por el usuario |
| HOME y regreso, si el launcher lo permite | Confirmado por el usuario |
| Duración observada y anomalías | Duración no informada; sin nuevas anomalías comunicadas |

Si se informa `MISSING`, revisar la ruta de `texture.stx`. `INVALID_DATA` o
`VERIFY_FAILED` requieren verificar/reponer el archivo desde el ZIP; el visor
no presenta una textura sustituta. START permite salir.
Conservar el texto exacto del error, build y acción anterior.

Un ensayo visual correcto confirma esta carga puntual. No cierra soporte de
otras texturas, uso de paletas, transparencia, geometría o jugabilidad.

## Registro — 2026-10-20, archivo ausente

El usuario adjuntó `IMG_3340.heic`. Se leyó mediante una conversión temporal a
PNG, conservando el original fuera del repositorio. Texto observado:
`Render probe failed: MISSING`, build `a6a45e73a03d`,
`SD file: /3ds/sh3_texture_probe/texture.stx`, `START: exit`.
La foto muestra el diagnóstico de salida, pero no prueba que START se pulsara.

En este lector, `MISSING` corresponde a `fopen` con `ENOENT`, antes de adquirir
recursos GPU. Se verificó de nuevo el ZIP entregado: contiene
`3ds/sh3_texture_probe/texture.stx`, de 262168 bytes, con SHA-256
`9e102a4ca80eecaae97e33b4608c3099e87c55601db62a4658c90984472956c6`.
Coincide con el archivo suelto privado. En esta primera revisión no había SD
montada en el Mac; todavía no se había inspeccionado su disposición.

Acción indicada entonces: colocar `texture.stx` en `/3ds/sh3_texture_probe/` de la SD,
junto al 3DSX, o extraer el ZIP en la raíz sin una carpeta adicional `sd-card`.
Volver a abrir el visor y registrar el resultado.

## Registro — 2026-10-20, corrección de SD y confirmación física

Con autorización del usuario se inspeccionó la unidad `NO NAME`. El paquete
estaba en `/sd-card/3ds/sh3_texture_probe/` y
`/3ds/sd-card/3ds/sh3_texture_probe/`; faltaba `/3ds/sh3_texture_probe/`.
Se creó esta última carpeta y se copiaron el 3DSX, SMDH, `texture.stx` y
`LEEME.txt` de la entrega v2, sin borrar las copias anteriores. Se sincronizó
cada archivo y se verificó su SHA-256 tras leerlo desde la SD; los cuatro
coinciden con los originales de la entrega identificada.

El usuario confirmó después que se muestra la textura, funcionan la cruceta y
los controles de cámara, y se conserva el funcionamiento tras cerrar la tapa
o ir a HOME. Ante una comprobación específica de START, respondió:
«Sí, vuelve correctamente», en referencia a Homebrew Launcher.

Se cierra TI-T5 para este build y esta muestra. La evidencia de funcionamiento
físico es la confirmación del usuario; la foto anterior documenta únicamente
el error inicial. No hay medición de duración/FPS ni comparación visual
detallada con PS2. La identificación del material, paleta para escena,
transparencia e integración con geometría original siguen pendientes.
