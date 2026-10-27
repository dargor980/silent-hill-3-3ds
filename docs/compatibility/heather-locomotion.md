# Heather: prueba de locomoción en New Nintendo 2DS XL

Build ARM: **`7250f427ffb9`**. **Aceptación funcional física confirmada.**
Queda por precisar duración por clip/encuadre y cobertura de los cinco arcos.
Paquete privado: `heather-locomotion-3ds-v2/sd-card.zip`, dentro de
`/Users/germancontreras/sh3-private-data/`. La guía se incluye como `LEEME.txt`.

El build `4707dacec7d1` falló con `Heather failed: open` en la consola.
Sus 17 archivos se verificaron intactos en la SD. Esta corrección evita
la barra duplicada al construir las rutas de SRI2/texturas. El usuario confirmó
que ahora carga Heather y funcionan espera, caminar, correr, controles, START,
tapa y HOME. La evidencia nueva figura al final; el LEEME del ZIP v2 conserva
la revisión previa a esta prueba, sin reescribir el paquete publicado.

## Instalación y resultado esperado

Usar el ZIP privado de la entrega HL-T4d.2 y extraerlo en la raíz de la SD.
Conservar la carpeta `3ds/sh3_heather_probe/` completa: ejecutable, SMDH,
`heather.sri` SRI2 y las 13 texturas. No basta con cambiar el `.3dsx` del visor
anterior. Abrir **SH3 Heather original** desde Homebrew Launcher; no requiere CIA.

Debe aparecer el atuendo original: chaleco blanco, falda y botas, con texturas.
El visor muestra 36 huesos, 6.943 vértices y 5.522 triángulos. Heather anima
en el mismo lugar; la cruceta controla la cámara. Los clips son:

| ID decimal | Acción | Selección desde espera |
| --- | --- | --- |
| 101 (`0x65`) | Espera | Estado inicial |
| 109 (`0x6D`) | Caminar | ZR |
| 113 (`0x71`) | Correr | ZR desde caminar estable |

ZR recorre 101 → 109 → 113 → 101; ZL recorre el orden inverso. Esperar a
que el HUD muestre `Mode: 1` antes de solicitar otro destino. `Mode: 3/5`
identifica una mezcla. Los números Q12 y Blend sirven para comprobar avance.

## Controles y avisos

- **A:** pausa/reanuda. La cámara permanece disponible.
- **R:** un paso completo mientras está pausado; conserva la pausa.
- **L:** primer fotograma del destino actual, cancela mezcla y conserva pausa.
- **SELECT:** cuerpo/cara; **X/Y:** acercar/alejar; **cruceta:** cámara;
  **B:** restablecer cuerpo y cámara; **START:** volver al launcher.
- ZL desde espera pide correr directamente: `unsupported_transition` es el
  rechazo esperado. Primero pasar por caminar. `transition_busy` significa
  que la mezcla aún no terminó; esperar `Mode: 1` y pulsar otra vez.
- La selección pausada se rechaza con `paused`; A permite reanudar.
  ZL+ZR simultáneos se rechazan. Los avisos pueden permanecer hasta otra acción.

## Secuencia HL-T5

1. Comprobar ID de build y atuendo. Dejar **60 segundos por clip** en cuerpo:
   espera → ZR → caminar → ZR → correr. En cada paso comprobar textura,
   animación continua, avance de Q12 y ausencia de bloqueos/corrupción.
2. Probar los cinco cambios en sesiones de **60 segundos por transición**,
   repitiendo el cambio y regresando por los arcos permitidos. Esperar siempre
   `Mode: 1` antes del siguiente cambio. Registrar continuidad y problemas
   visibles de brazos, piernas, rostro o cabello.

   | Transición comprobada | Tecla | Cómo preparar el origen |
   | --- | --- | --- |
   | Espera → caminar | ZR | Arranque o ZR desde correr estable |
   | Caminar → espera | ZL | ZR desde espera |
   | Caminar → correr | ZR | ZR desde espera |
   | Correr → caminar | ZL | ZR desde caminar |
   | Correr → espera | ZR | ZR desde caminar |

3. A en cada clip: comprobar que Q12/pose no avanzan; R hace un paso y L
   vuelve a Q12 cero. En el primer paso tras L la pose puede seguir en el
   primer fotograma: se evalúa antes de avanzar el reloj. La cámara debe
   responder durante la pausa. Repetir A y L durante una mezcla si es posible.
4. Comprobar SELECT, cruceta, X/Y y B; mantener **60 segundos en primer plano**
   en cada clip. El zoom mínimo es 0,45. Confirmar rostro y cabello sin corrupción.
5. Cerrar/abrir la tapa y usar HOME/regresar, tanto reproduciendo como en pausa.
   Al volver, soltar todos los controles; no debe haber saltos por el tiempo
   dormido ni acciones por botones retenidos. La pausa debe conservarse.
6. START debe volver a Homebrew Launcher. Reabrir una vez debe iniciar en
   espera, sin conservar una selección o mezcla de la ejecución anterior.
7. Anotar las lecturas aproximadas siguientes después de cada intervalo. Si
   no se midieron, marcar «sin medir» y registrar la aceptación funcional aparte.

| Clip/encuadre | Duración | FPS submit | CPU solicitada | Skin+sort CPU | Submit+wait | GPU previous | Resultado visual |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Espera/cuerpo | pendiente | | | | | | |
| Caminar/cuerpo | pendiente | | | | | | |
| Correr/cuerpo | pendiente | | | | | | |
| Espera/cara | pendiente | | | | | | |
| Caminar/cara | pendiente | | | | | | |
| Correr/cara | pendiente | | | | | | |

`New fast` indica una solicitud al SDK, no MHz medidos. FPS submit mide
presentaciones, separado de las 25 actualizaciones/s de inspección. No sumar
tiempos CPU/submit/GPU para inferir FPS; pueden corresponder a cuadros distintos.
Skin+sort no incluye el coste del evaluador de locomoción. Tras HOME/tapa,
la métrica FPS necesita una ventana nueva.

## Límites y fallos

Esta entrega acredita un visor de locomoción, con iluminación neutra y sin
desplazamiento por una habitación, colisión, combate, morphs/expresiones ni
equivalencia de raster con GS. La selección directa espera→correr no forma
parte de los cinco arcos observados. La validación host, ARM o emulada no
sustituye esta prueba física.

Ante `sample_unavailable`, `invalid_pose` o un error de carga, registrar el
mensaje y el ID de build y salir con START. No dar HL-T5 por aprobada ante
bloqueo, deformación corrupta o pérdida de los controles de salida/regreso.


## Resultado comunicado — 2026-10-26

El usuario probó `7250f427ffb9` en New Nintendo 2DS XL: carga Heather y
funcionan espera, caminar, correr, controles, START, tapa y HOME. Se acepta
este alcance funcional y la corrección del fallo `open` anterior. No se
atribuye a observación directa del agente.

| Métrica | Valor aproximado comunicado |
| --- | ---: |
| FPS submit | 29,9 FPS |
| Skin+sort CPU | 10,08 ms |
| Submit+wait | 23,3 ms |
| GPU previous | 4,32 ms |

Lectura global: no se especificaron clip, cuerpo/cara, duración ni intervalo
por transición. No llenar las seis filas del protocolo con esta misma medida.
HL-T5a funcional y HL-T5b registro de métricas completadas; HL-T5c duración y
cinco arcos por encuadre quedan pendientes de precisión. Esta separación permite
avanzar con [HM-T1](../specs/sh3-3ds/heather-movement.md), sin convertir la
aceptación en una prueba de habitación, colisión o treinta minutos de juego.
