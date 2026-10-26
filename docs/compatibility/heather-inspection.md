# Heather original: prueba en New Nintendo 2DS XL

**Estado: build `8f778b6e4960` confirmado funcional, con mayor fluidez reportada.**
Baseline histórico probado `f25a2d9bb316`.
Añade primer plano y corrige la orientación vertical de las texturas en PICA.
[Resultados previos](../execution/f03-02-heather-inspection.md): ARM compilado,
64 segundos continuos y controles comprobados en Azahar. Esa evidencia no
acredita rendimiento, START al launcher ni tapa/HOME en la consola.

## Preparación y resultado esperado

Paquete privado: `/Users/germancontreras/sh3-private-data/heather-3ds-v2/sd-card.zip`.
Extraer en la raíz de la SD, conservando `3ds/sh3_heather_probe/`, y abrir
**SH3 Heather original** desde Homebrew Launcher. No requiere instalar CIA.
La carpeta incluye SRI y 13 texturas; copiar solo el `.3dsx` es insuficiente.

Entrega a SD del 2026-10-24: build `f25a2d9bb316` copiado en
`NO NAME/3ds/sh3_heather_probe/`. Los 17 archivos (18.949.569 bytes)
coinciden por tamaño y SHA-256 tras releer la SD, que se expulsó de forma
segura. Recibo local: `reports/local/heather-sd-delivery-f25a2d9bb316.json`.
El usuario confirmó la prueba funcional de esta entrega el 2026-10-24.

Debe verse Heather con chaleco blanco, falda oscura y botas, texturada y con
movimiento de espera. Pantalla inferior: build correcto, clip `0x65`, 36
huesos, 10 muestras, 6.943 vértices y 5.522 triángulos. Q12 y muestra avanzan.
La luz es neutra; no hay habitación ni control jugable de Heather.

## Secuencia HI-T5b

1. Dejar animar **al menos 60 segundos** sin bloqueo ni corrupción visible.
2. A pausa/reanuda; en pausa, R avanza y L devuelve Q12 a cero. Comprobar que
   la pose responde y que la cámara funciona también con animación pausada.
3. SELECT alterna cuerpo/cara. Cruceta gira/eleva cámara, Y aleja, X acerca
   hasta 0,45 y B vuelve al cuerpo completo. Dejar animar otros 60 segundos
   en primer plano; comprobar rostro/cabello y repetir SELECT con A en pausa.
4. Cerrar/abrir tapa y usar HOME/regresar. Soltar todos los controles si se
   solicita; comprobar que la animación continúa y no hay saltos por el
   tiempo dormido. No se debe disparar A/R/L por botones retenidos al volver.
5. START vuelve a Homebrew Launcher. Reabrir una vez confirma nueva carga.
6. Anotar valores aproximados de `Skin+sort CPU`, `Submit+wait` y
   `GPU previous`, sin deducir FPS sumando esas cifras. Si no se midieron,
   registrarlos como pendientes; la prueba funcional se registra aparte.

| Dato | Resultado |
|---|---|
| Fecha y duración | 2026-10-24; 60 segundos reportados |
| Modelo y rostro texturado | Cara de Heather visible correctamente; informe del usuario |
| A/R/L | Controles confirmados de forma conjunta por el usuario |
| Cruceta/X/Y/B | Zoom y controles confirmados |
| SELECT cuerpo/cara y primer plano 60 s | Confirmados; no se atribuyen dos intervalos separados de 60 s |
| START/reapertura | START confirmado; reapertura no detallada |
| Tapa/HOME | Confirmados |
| Skin+sort CPU / Submit+wait / GPU previous | ≈60,7 / 49 / 4,36 ms; lecturas manuales |

Ante una pantalla de error, registrar el texto y usar START. Un fallo de
hardware mantiene HI-T5b abierta. La aceptación de los visores del caballo
no se traslada automáticamente a este perfil de mayor tamaño.

El usuario también informa baja fluidez. No se midieron FPS ni percentiles;
estas cifras aproximadas no se suman para obtener FPS. La aceptación
funcional HI-T5b/HI-T6c se registra separada de la mejora de rendimiento
[HP](../specs/sh3-3ds/heather-performance.md), ahora prioritaria.

## Límites conocidos

El clip usa un reloj de inspección de 25 evaluaciones/s, no una frecuencia
nativa completa acreditada. No se aplican morphs/expresiones, luces/fog PS2,
colisión ni desplazamiento de jugador. La transparencia se ordena para la
cámara del visor; no se ha medido equivalencia de raster PICA/GS.

## HP: resultado de rendimiento

Build `8f778b6e4960`, paquete privado
`/Users/germancontreras/sh3-private-data/heather-3ds-v3/sd-card.zip`.
Entrega a SD del 2026-10-24: los 17 archivos (18.950.897 bytes) se
verificaron por tamaño y SHA-256 en `NO NAME/3ds/sh3_heather_probe/`.
Se respaldaron los dos archivos sustituidos y se expulsó la SD de forma
segura. Recibo local: `reports/local/heather-sd-delivery-8f778b6e4960.json`.

Conserva el SRI y las 13 texturas del build funcional confirmado.
Solicita CPU rápida en la familia New y reduce trabajo por vértice compartido.
`CPU: New fast` significa solicitud al SDK; no es una medición de MHz.
`FPS submit` cuenta presentaciones de la aplicación por segundo transcurrido;
no son barridos físicos de pantalla ni muestras de animación.

**HP-T4 confirmada por el usuario el 2026-10-24:** 60 s en cuerpo y 60 s en
cara; Heather se ve más fluida; controles, START, tapa y HOME funcionan.
Lectura conjunta aproximada: **29,9 FPS submit**, CPU **New fast**, Skin+sort
**10,27 ms**, Submit+wait **23,1 ms**, GPU previous **6,34 ms**. No se dieron
lecturas separadas por encuadre ni se detalló reapertura. No son percentiles
ni una traza por cuadro; no se suman etapas ni se infieren FPS previos.
Tras suspensión, los FPS esperan una ventana nueva.
Recibo local: `reports/local/heather-hardware-v2.json`.
