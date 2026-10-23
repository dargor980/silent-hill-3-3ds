# Prueba física — SH3 textured character

Estado: **CT-T5e.1 funcional aprobada**, New 2DS XL y Homebrew Launcher,
build **`ced27c955e41`**. Confirmación del usuario el 2026-10-22.
Los tiempos del build corregido siguen pendientes en **CT-T5e.2**.
Build anterior fallido **`3fde5682ed11`**: no repetir esa entrega.
[Resultados de implementación y verificación](../execution/f03-02-character-material-inspection.md).
La aprobación de la malla dorada anterior no sustituye esta prueba.

## Repetición con la corrección

Build nuevo **`ced27c955e41`**, validado funcionalmente en consola.
[Diagnóstico, corrección y pruebas](../execution/f03-02-character-material-gpu-fix.md).
ZIP privado: `/Users/germancontreras/sh3-private-data/f03-02-3ds-character-material-v2/sd-card.zip`.
**Copiado a la SD NO NAME a petición del usuario**: seis archivos,
3.485.367 bytes, con tamaños y SHA-256 verificados mediante lectura posterior.
Se verificaron también los 30 archivos de los otros visores, sin cambios.
La SD se expulsó correctamente. Comprobante privado:
`f03-02-character-material-native-check-v2/sd-copy.json`, SHA-256
`0178c975aee28140307143f97145486b13a773430a51aa388600b30bf031c3a1`.
El usuario confirma: «Lo probé en la 2DS XL durante 60 segundos: ahora se ve
el caballo con texturas, avanza Q12 y no se bloquea. Funcionan los controles,
START, tapa y HOME». Es evidencia física comunicada por el usuario; no una
captura instrumentada. No se recibieron lecturas de rendimiento nuevas.

| Comprobación de v2 | Resultado comunicado |
|---|---|
| Build | `ced27c955e41`, vinculado a la entrega solicitada y verificada en SD |
| Caballo y texturas | Visibles |
| Animación / Q12 | Avanza |
| Duración | 60 segundos sin bloqueo |
| Controles / cámara | Funcionan según confirmación global del usuario |
| START | Funciona |
| Tapa / HOME | Funcionan |
| Skin CPU / Submit+wait / GPU previous | Sin medir para este build; CT-T5e.2 pendiente |

La confirmación no aporta valores exactos de los pasos R ni separa las
variantes de tapa/HOME en pausa y reproducción. No se infieren esos detalles.
La tabla al final conserva el fallo de v1 como antecedente.
Recibo privado: `f03-02-character-material-native-check-v2/physical-user-confirmation.json`,
SHA-256 `6200b64c83123f603a9d260ece13364562efea5b0d45729035157f24f0edfb90`.

## Instalación original (v1, fallida)

ZIP privado: `/Users/germancontreras/sh3-private-data/f03-02-3ds-character-material-v1/sd-card.zip`.
Extraer en la raíz de la SD, conservando los otros visores. Deben quedar seis
archivos en `/3ds/sh3_character_material_probe/`: `animation.san`, `character.scm`,
`character.sct`, `sh3_character_material_probe.3dsx`,
`sh3_character_material_probe.smdh` y `LEEME.txt`.
Expulsar la SD de forma segura y abrir **SH3 textured character**.
No requiere instalación CIA/FBI.

**Entrega copiada a la SD «NO NAME»** a petición del usuario: build
`3fde5682ed11`, seis archivos y 3.485.367 bytes en
`/3ds/sh3_character_material_probe/`. Tamaños y SHA-256 verificados mediante
lectura posterior desde la SD. Los visores anteriores se conservaron y la SD
se expulsó correctamente. La prueba física posterior **CT-T5e falló**.
Comprobante privado: `f03-02-character-material-native-check-v1/sd-copy.json`,
SHA-256 `0e2f8ab78c8f87b9de1ace524b2091eab3b14b4a90db810f30c8d1ebb4598966`.

## Protocolo

1. Comprobar build nuevo `ced27c955e41`, 1.455 vértices y 1.113 triángulos. Debe
   verse el caballo con poste y sus texturas originales oscuras/rojizas,
   en lugar del sombreado dorado. La luz es neutra y se dibujan ambas caras.
2. Observar al menos **60 segundos** en reproducción. Revisar el contador
   Q12 y el movimiento sutil, texturas alineadas, sin vértices disparados,
   cuadros blancos, parpadeos, desapariciones o bloqueos. Las zonas con alfa
   cero permanecen opacas: así lo verificó CT-T4 para esta pasada.
3. A pausa; L lleva Q12 a cero sin quitar la pausa. Cada R suma 3686 módulo
   98304. A reanuda. La cámara debe seguir funcionando en pausa.
4. Cruceta mueve la cámara; X/Y acerca y aleja; B vuelve al encuadre inicial.
   El rango de cámara sigue siendo el del visor anterior.
5. Probar tapa y HOME reproduciendo y en pausa. Al regresar, soltar los
   controles; verificar que se conserva la pausa y no se recupera de golpe
   el tiempo suspendido. Volver a probar A y cámara.
6. START debe regresar al Homebrew Launcher, también tras tapa/HOME.
7. Durante los 60 segundos, anotar varias lecturas de **Skin CPU**, **Submit+wait**
   y **GPU previous**. Submit incluye espera; estas cifras no se suman para
   calcular FPS. No hay todavía un umbral de rendimiento para este visor.

| Dato | Resultado |
|---|---|
| Build mostrado | `3fde5682ed11`, confirmado en foto |
| Texturas, alineación y movimiento | No aparece el caballo; bloqueo reportado |
| A / R / L y valores Q12 | Pendiente |
| Cruceta / X / Y / B | Pendiente |
| START | Pendiente |
| Tapa / HOME reproduciendo y en pausa | Pendiente |
| Duración ≥60 s y lecturas CPU/envío/GPU | No validada; foto: 16,53 / 16,98 / 0,00 ms, Q12=0 y Sample=0 |
| Defectos o mensajes de error | Consola bloqueada, el usuario tuvo que apagarla |

La prueba no acredita iluminación dinámica PS2, descarte VU, transformación
mundial definitiva, equivalencia de filtrado a nivel de píxel ni transiciones
de daño `0x144A` y muerte `0x144B`.
