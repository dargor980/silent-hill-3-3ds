# Heather original: prueba en New Nintendo 2DS XL

**Estado: pendiente de prueba física.** Build actual `f25a2d9bb316`.
Añade primer plano y corrige la orientación vertical de las texturas en PICA.
[Resultados previos](../execution/f03-02-heather-inspection.md): ARM compilado,
64 segundos continuos y controles comprobados en Azahar. Esa evidencia no
acredita rendimiento, START al launcher ni tapa/HOME en la consola.

## Preparación y resultado esperado

Paquete privado: `/Users/germancontreras/sh3-private-data/heather-3ds-v2/sd-card.zip`.
Extraer en la raíz de la SD, conservando `3ds/sh3_heather_probe/`, y abrir
**SH3 Heather original** desde Homebrew Launcher. No requiere instalar CIA.
La carpeta incluye SRI y 13 texturas; copiar solo el `.3dsx` es insuficiente.

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
| Fecha y duración | Pendiente |
| Atuendo original/texturas/animación | Pendiente |
| A/R/L | Pendiente |
| Cruceta/X/Y/B | Pendiente |
| SELECT cuerpo/cara y primer plano 60 s | Pendiente |
| START/reapertura | Pendiente |
| Tapa/HOME | Pendiente |
| Skin+sort CPU / Submit+wait / GPU previous | Pendiente |

Ante una pantalla de error, registrar el texto y usar START. Un fallo de
hardware mantiene HI-T5b abierta. La aceptación de los visores del caballo
no se traslada automáticamente a este perfil de mayor tamaño.

## Límites conocidos

El clip usa un reloj de inspección de 25 evaluaciones/s, no una frecuencia
nativa completa acreditada. No se aplican morphs/expresiones, luces/fog PS2,
colisión ni desplazamiento de jugador. La transparencia se ordena para la
cámara del visor; no se ha medido equivalencia de raster PICA/GS.
