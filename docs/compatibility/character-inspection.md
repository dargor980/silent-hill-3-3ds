# Prueba física — SH3 character inspection

Estado: **CM-T5e.1 funcional aprobada por el usuario; CM-T5e.2 medición pendiente**,
New 2DS XL y Homebrew Launcher.
Build esperado **`757b48fd1746`**, preparado el 2026-10-20.
[Resultados previos de host, ARM y Azahar](../execution/f03-02-character-inspection.md).
La aprobación anterior del visor de ejes no sustituye esta prueba de malla.

## Instalación

Extraer el ZIP privado
`/Users/germancontreras/sh3-private-data/f03-02-3ds-character-v2/sd-card.zip`
en la raíz de la SD. Deben quedar cinco archivos en
`/3ds/sh3_character_probe/`: `animation.san`, `character.scm`,
`sh3_character_probe.3dsx`, `sh3_character_probe.smdh` y `LEEME.txt`.
Conservar los otros visores y expulsar la SD de forma segura. Esta entrega
usa Homebrew Launcher; no requiere CIA/FBI.

**Entrega copiada a la SD «NO NAME»** tras conectarla el usuario: build
`757b48fd1746`, cinco archivos y 335.832 bytes en
`/3ds/sh3_character_probe/`. Tamaños y SHA-256 verificados mediante lectura
posterior desde la SD; otros visores conservados. Solo se retiraron los
auxiliares `._` generados para esta copia. La SD se expulsó correctamente.
Comprobante privado: `f03-02-character-native-check-v1/sd-copy.json`, SHA-256
`a5ff3e59eddae83addfa7c9d4b0e66d4f8d192df54dc398913b6154ee775cf02`.
Confirmación posterior del usuario: «Lo probé en la 2DS XL: se ve la malla
del caballo animada y funcionan A, R, L, la cámara, START, tapa y HOME».
Se vincula la prueba al build entregado `757b48fd1746`; el usuario no
transcribió el identificador. No comunicó duración,
valores Q12, X/Y/B por separado o pruebas en cada estado de pausa. Se conserva
ese límite: la aceptación funcional permite continuar la investigación de
materiales, pero no acredita la medición de CI06 ni el protocolo exhaustivo.
En respuesta posterior comunicó lecturas aproximadas de **Skin CPU 14 ms,
Submit+wait 12 ms y GPU previous 1,1 ms**. Son observaciones físicas del usuario,
sin distribución, número de muestras ni duración confirmada. Submit+wait
incluye sincronización; no se suman las tres cifras para inferir FPS.

## Comprobaciones

1. Abrir **SH3 character inspection** y comprobar build `757b48fd1746`,
   1.455 vértices y 1.113 triángulos. Debe aparecer la malla del caballo con
   su poste, derecha y con sombreado dorado propio; todavía sin textura
   original. Rotar la cámara para observarla de lado si el encuadre inicial
   muestra su extremo.
2. Dejar reproducir al menos **60 segundos**, observando el movimiento sutil
   de la malla y el contador Q12. Registrar si aparecen vértices disparados,
   parpadeos, cortes de la figura, bloqueos o mensaje de error. El reloj del
   preview usa 25 evaluaciones/s; esto no es una medición del juego PS2.
3. A debe congelar movimiento y contador. L lleva Q12 a cero conservando
   la pausa. Cada pulsación independiente de R suma 3686, módulo 98304.
   A reanuda; R durante reproducción no debe forzar un paso adicional.
4. Cruceta gira la cámara; X/Y acerca/aleja; B restaura el encuadre. Probar
   también con la animación pausada: el contador debe permanecer fijo.
5. Cerrar/abrir la tapa y usar HOME tanto reproduciendo como en pausa.
   Al regresar, soltar todos los controles; conservar la pausa y evitar
   recuperar de golpe el tiempo suspendido. Comprobar nuevamente A y cámara.
6. START debe volver al Homebrew Launcher, también después de reanudar.
7. Anotar varias lecturas aproximadas de `Skin CPU`, `Submit+wait` y
   `GPU previous` durante la reproducción de 60 segundos. La segunda incluye
   espera de cuadro/GPU, no solo subida; las tres cifras no se suman para
   inferir FPS. No se ha definido un umbral de rendimiento para este visor.

| Dato a comunicar | Resultado |
|---|---|
| Build mostrado | Vinculado a la entrega; no transcrito por el usuario |
| Malla y movimiento | Caballo animado confirmado; duración/orientación detallada sin registrar |
| A / R / L | Funcionan según el usuario; Q12 no transcrito |
| Cámara / X / Y / B | Cámara confirmada; X/Y/B no desglosados |
| START | Funciona según el usuario |
| Tapa y HOME | Funcionan según el usuario; estados de pausa no desglosados |
| Lecturas Skin CPU / Submit+wait / GPU previous | ≈14 ms / ≈12 ms / 1,1 ms según el usuario |
| Errores o defectos visibles | No comunicados; no equivale a una inspección exhaustiva |

Esta prueba valida la integración de inspección. Materiales originales,
transformación mundial, equivalencia visual PS2/3DS y transiciones de daño
y muerte mantienen su aceptación independiente.
