# Prueba física LI-T4f — SH3 captured lighting

Estado: **LI-T4f.1 aceptada funcionalmente; LI-T4f.2 sin medir**,
New 2DS XL / Homebrew Launcher. Build entregado **`b27d16a1671e`**.
[Implementación y evidencia local](../execution/f03-02-character-lighting-inspection.md).
La aceptación del visor neutro anterior no sustituye esta prueba.

ZIP privado:
`/Users/germancontreras/sh3-private-data/f03-02-3ds-character-lighting-v1/sd-card.zip`.
Extraer en la raíz de la SD y conservar los otros visores. La carpeta
`/3ds/sh3_character_lighting_probe/` debe contener `animation.san`,
`character.scm`, `character.sct`, `character.scl`,
`sh3_character_lighting_probe.3dsx`, `sh3_character_lighting_probe.smdh`
y `LEEME.txt`. Expulsar de forma segura; abrir **SH3 captured lighting**.
No requiere CIA/FBI.

**Copiado a la SD NO NAME el 2026-10-23 a petición del usuario**: siete archivos,
3.490.852 bytes, con tamaños y SHA-256 comprobados por lectura posterior.
Los visores anteriores se conservaron y la SD se expulsó correctamente.
Se admitieron los archivos auxiliares `._` creados por macOS en FAT32;
no forman parte de los siete archivos del build.
Recibos privados en `f03-02-character-lighting-native-check-v1/`:

- `sd-copy.json`: `932884b04a0ac8f9d2d27ff492705df92d1f3ef59824304acc9fad88abe65b3f`.
- `sd-eject.json`: `c3637ef52bcb357941921f9ab3a3e25dbf43d0a4d4a2db8dd0960fb83f713c22`.
- `physical-user-confirmation.json`:
  `3868ac89e4cebee30d2bf9a2f2b45e19c3b33f624dc42ac5cc1fe0c1d76aa7bb`.

El 2026-10-23 el usuario informó: «Lo probé en la 2DS XL durante 60 segundos
en cada modo: se ve el caballo iluminado, SELECT cambia la iluminación y
funcionan los controles, START, tapa y HOME». Para las métricas respondió
«sin medir». La atribución del build corresponde a la entrega verificada;
no se recibió una nueva fotografía de la pantalla. El protocolo detallado
siguiente se conserva para repetición y para las comprobaciones no informadas.

1. Confirmar build, 1.455 vértices / 1.113 triángulos, caballo texturado y
   rótulo **Captured lights / fixed / two-sided**. La iluminación puede verse
   más oscura que la neutra: son parámetros de una captura fija.
2. Observar **≥60 segundos** en modo capturado: Q12 avanza, hay movimiento,
   no desaparece la malla ni aparecen parpadeos, vértices disparados o bloqueos.
3. A pausa; L reinicia Q12=0; R avanza 3686 módulo 98304. En pausa, SELECT
   alterna iluminación capturada/neutra sin cambiar Q12 ni cámara. Repetir
   SELECT para volver; debe recuperarse el mismo aspecto en esa pose.
4. Cruceta mueve cámara, X/Y zoom y B restaura 0,35 / 0,35 / 4,00. La cámara
   no mueve el preset de luces. A reanuda. Probar **≥60 segundos en modo neutro**
   y alternar también durante reproducción.
5. Probar tapa y HOME en ambos modos, reproduciendo y en pausa. Al regresar,
   soltar controles. Deben conservarse modo, pausa y cámara, sin recuperar
   de golpe el tiempo suspendido ni alternar SELECT mientras se mantiene pulsado.
6. START vuelve al Homebrew Launcher, también después de tapa/HOME.
7. Registrar varias lecturas de **Skin CPU**, **Light CPU**, **Submit+wait**
   y **GPU previous**, indicando el modo. Light CPU debe ser cercano a cero
   en modo neutro. Submit incluye espera; no sumar los tiempos para obtener FPS.
   No se fija todavía un umbral físico de rendimiento para este visor.

| Dato | Resultado |
|---|---|
| Build mostrado | Atribuido a la entrega b27d16a1671e; sin nueva imagen |
| Caballo e iluminación | Visibles según usuario; valores Q12 no informados |
| SELECT | Cambia iluminación; conservación exacta de pose/cámara no medida |
| A/R/L, cruceta, X/Y/B | Usuario confirma los controles en conjunto |
| ≥60 s capturado / ≥60 s neutro | Confirmado por usuario en cada modo |
| Tapa/HOME | Funcionales; casos separados pausa/reproducción no detallados |
| START | Confirmado por usuario |
| Skin / Light / Submit+wait / GPU por modo | Sin medir; LI-T4f.2 pendiente |
| Defectos o mensajes | Ninguno informado |

Es un preset de inspección recalculado por pose. No implementa selección de
luces al recorrer habitaciones, seguimiento de linterna, sombras ni daño/muerte.
