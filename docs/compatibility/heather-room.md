# HM-T5 — Aceptación física de Heather en hp34

Estado: **funcionamiento general de `c3aae59d1a70` confirmado por el usuario
en consola; HM-T5 parcial**. El 2026-10-30 comunicó «prueba realizada, funciona
correctamente» después de instalar la entrega con materiales originales.
No aportó nuevas mediciones ni resultados por caso del protocolo.

**Decisión posterior del usuario, 2026-10-30:** las mediciones y pruebas
adicionales de HM-T5 quedan aplazadas. Se continúa con
[F06.02/heather-turns](../specs/sh3-3ds/heather-turns.md), conservando esta
confirmación funcional y los casos pendientes sin ejecutarlos ahora.

HG-T5 prepara el build `0188790baedd` con cinco acciones y su
[protocolo específico de giros](heather-turns.md). Su copia a SD quedó verificada,
con respaldo de `c3aae59d1a70` y expulsión segura. La
[prueba funcional física HG](heather-turns-results.md) fue confirmada por
el usuario; conserva sus límites y no reabre los casos HM-T5 de esta guía.

Historial: el usuario reportó
carga de unos 20 s y Heather aparentemente inmóvil en `ad84b65cd58d`.
A alternaba pausa; el aviso de liberación desaparecía y `Error: none`.
R no produjo un cambio percibido. En `217e1ace6571` la carga bajó a 7492 ms
y funcionaron caminar/girar, pero el usuario confirmó que Step y `R presses`
aumentaban sin tocar botones mientras se mostraba PAUSED. La repetición con
el filtro de R en `de58ea2bb966`
confirmó pausa, R/L y retorno funcional de HOME/tapa por separado. El usuario confirmó que el build
diagnóstico `161090bc9fd5` funciona bien. La entrega HM-T4c.3.3 incorpora
los materiales originales verificados. El build `c3aae59d1a70` quedó instalado
en SD el 2026-10-30: 29 archivos releídos y verificados, respaldo de la entrega
anterior conservado y expulsión segura confirmada. La confirmación funcional
posterior se registra con este ID; la aceptación completa de HM-T5 sigue pendiente.
El build concreto y su SHA-256
se indican en el informe de entrega; el LEEME empaquetado añade el mismo ID
que aparece en la pantalla inferior. Registrar ese ID antes de probar.

## Instalación y arranque

1. Extraer `sd-card.zip` en la raíz de la SD. Debe quedar
   `/3ds/sh3_heather_room/sh3_heather_room.3dsx` junto a `scene.srr`, `map.srm`,
   `heather.sri`, `glass.rgba`, las trece `texture-00.rgba` a `texture-12.rgba`,
   las nueve `room-texture-00.rgba` a `room-texture-08.rgba`,
   `sh3_heather_room.smdh` y `LEEME.txt` (29 archivos). `SHA256SUMS` queda en
   la raíz del ZIP para verificar los bytes antes de copiar.
2. Mantener completa la carpeta; no abrir solo el `.3dsx` desde otra ruta.
   El directorio es distinto de `sh3_heather_probe`; conservar ese visor.
   Si ya existe una entrega de habitación, conservarla antes de reemplazarla.
3. Abrir **SH3 Heather room** desde Homebrew Launcher y soltar los botones.
   Anotar ID, modelo de consola y versión del entorno de arranque.
4. Esperar a que termine la carga. Comprobar Heather con atuendo original,
   habitación y vidrio; no debe aparecer Error. Anotar si el fallo ocurre
   antes de dibujar o después. Fotografiar ambas pantallas si hay un defecto.

Recursos privados: conservar el ZIP, sus archivos y capturas fuera de git,
CI y servicios públicos. Las dos copias A/B son idénticas; basta instalar una.

## Controles

| Entrada | Acción |
| --- | --- |
| Arriba | Caminar hacia donde mira Heather |
| Arriba+B | Solicitar carrera, pasando por caminar |
| Izquierda/derecha | Girar; puede combinarse con avance |
| Abajo | No añade marcha atrás en este perfil |
| A | Pausar/reanudar; soltar todos los botones al cambiar de estado |
| R, en pausa | Mantener unos 0.2 s y soltar otros 0.2 s: una actualización fija con la dirección/B que se mantenga |
| L | Volver al spawn, espera y Step=0; conserva pausa/running |
| START | Salir |

Giro y avance se refieren a Heather, no a la cámara. X/Y/SELECT/ZL/ZR no
cambian cámara ni clips. Mantener un botón al entrar, reiniciar o volver de
suspensión exige soltarlo antes de aceptar nueva entrada.

R requiere 80 ms continuos suelto para armarse y 80 ms continuos pulsado
para aceptar un único paso. Mantenerlo no repite; pulsaciones demasiado
breves se descartan. Pausa/reanudación, L, suspensión y discontinuidades de
reloj cancelan cualquier pulsación pendiente. Si el render es lento, mantener
R hasta ver el paso y después soltarlo. No se debe avanzar sin entrada válida.

## Recorrido repetible de 100 pasos

Este guion corresponde al replay integrado host, no al recorrido PS2.

1. Pulsar A para pausar, soltar; pulsar L y soltar. Debe decir PAUSED,
   Step=0 y Clip=101. Mantener la pausa durante todo el guion.
2. Sin dirección, pulsar y soltar R 25 veces: Step=25.
3. Mantener Arriba y pulsar/soltar R 25 veces: Step=50. Soltar todo.
4. Mantener Arriba+B y pulsar/soltar R 25 veces: Step=75. Soltar todo.
5. Mantener Arriba+Izquierda y pulsar/soltar R 25 veces: Step=100. Soltar todo.
6. Registrar postura, ubicación visible, clip/Q12 y Error. Repetir desde L:
   debe llegar al mismo resultado visible y contador, sin atravesar barreras.

Los pasos bloqueados siguen contando y la animación continúa. No exigir
traslación en todos los pasos: el perfil rechaza la traslación completa ante
una barrera. Los 25 pasos de cada bloque equivalen a un segundo de simulación,
independientemente del tiempo que tarde la pulsación manual. No son 25 FPS.

Después, reanudar con A y recorrer libremente durante 60 s, incluyendo
caminar, carrera, giro sobre el sitio, acercarse a las barreras y L. Comprobar
que no hay saltos verticales, penetraciones, pose rota ni reinicios inesperados.
La ruta geométrica de cinco tramos HR es evidencia analítica separada; este
guion de controles no afirma reproducir exactamente sus coordenadas.

## Pausa, suspensión y salida

- En marcha, A debe congelar posición/pose/Step. Esperar diez segundos:
  no debe avanzar. R debe añadir exactamente un paso y conservar PAUSED.
- L en pausa debe volver al spawn y Step=0 sin reanudar. L en marcha debe
  reiniciar; solo vuelve a aceptar movimiento después de soltar botones.
- Probar HOME y retorno, primero en marcha y luego en pausa. Repetir con
  cierre de tapa durante diez segundos. Se debe conservar el estado previo,
  descartar el tiempo ausente y exigir liberación de entrada, sin acelerón.
- Si el entorno permite HOME seguido de cierre de tapa, probar esa combinación
  y el retorno completo. No debe avanzar mientras quede suspendido por alguno.
  Si no se puede observar el retorno parcial, anotarlo como no comprobado.
- START debe regresar al lanzador. Abrir y salir diez veces; registrar cuelgue,
  pantalla negra, error de carga o degradación observable. Esto no mide fugas.

## Recuperación de errores

El HUD distingue error de spawn, movimiento/animación y gráficos. Ante un
error, registrar el mensaje, soltar todo y pulsar L; si se recupera, permanece
en pausa y A permite continuar. Si persiste, salir con START y conservar la
evidencia. `busy` gráfico puede omitir una presentación sin convertirse en error.

Para comprobar un error de carga de forma reversible: con la aplicación
cerrada y la SD expulsada de forma segura de la consola, conservar una copia
completa verificada y renombrar `scene.srr` a `scene.srr.saved`. Arrancar:
debe mostrar el error, permitir L sin bloqueo y START para salir. Restaurar
el nombre original con la aplicación cerrada, verificar su hash y repetir
el arranque normal. Nunca retirar la SD mientras la aplicación la utiliza.
No hace falta alterar mallas, texturas o CRC para esta prueba.

## Alcance y mediciones pendientes

**CAMARA FIJA PROPIA / MATERIALES ORIGINALES / LUZ FIJA**: las 29 formas
internas tienen asignaciones originales verificadas. Se dibujan 26 y se omiten
tres, como en la captura original. Se conserva su orden incluso para mezcla
alfa. Las nueve combinaciones de textura/paleta se cargan una sola vez.
Heather y los dos vidrios mantienen sus recursos anteriores. RGB y niebla
son los de la captura, fijados por vértice; no hay iluminación dinámica PS2
ni equivalencia exacta por píxel. La visibilidad corresponde al estado
capturado. La cámara, la inserción de Heather y la ordenación vidrio/pelo
siguen siendo del perfil de inspección.

La entrada es propia, el suelo es plano y las 32 cajas son conservadoras.
No hay deslizamiento, movimiento vertical, actores dinámicos, puertas,
combate ni cámara original PS2. Comprobar que se distinguen suelo, paredes,
muebles y Heather; anotar superficies ausentes, colores extraños, parpadeo
u objetos que atraviesan visualmente a Heather.

`Accounted: 49.33 / 64 MiB` muestra un **presupuesto**, no memoria medida.
El build de corrección muestra `Load`, `FPS submit`, intervalo `Frame`,
`Prep` (skin y orden CPU), `Submit` (envío y espera), `GPU previous`,
`Slow frames`, pasos de la última llamada y máscaras HID. `R presses (raw)`
cuenta flancos brutos del SDK y `R steps` cuenta los pasos aceptados en pausa;
ambos persisten al pulsar L. Si llegan pulsos cortos o repetidos, el primero
puede aumentar mientras `R steps` y Step permanecen fijos. Registrar ambos
antes/después, junto con Held y Down. El filtro no identifica el origen físico
de la señal ni distingue una señal falsa sostenida de una pulsación real.
La CPU indica `New fast` si se solicitó el modo rápido; no mide su frecuencia.
Las cifras de GPU y envío pueden solaparse. La aceptación de rendimiento
requiere muestras físicas de al menos 60 s por condición; el pico de memoria
y el tiempo CPU de simulación todavía no están instrumentados. No inferirlos del contador Step,
de la cadencia fija, del emulador o de la compilación ARM. El objetivo de
30 presentaciones/s sigue sujeto a medición; no está acreditado.

Registrar por separado: (a) presupuesto teórico, (b) pico observado de heap/
memoria lineal con instrumentación, (c) tiempo CPU de simulación/skin/orden,
(d) submit+espera y GPU, identificando que pueden solaparse, (e) FPS de
presentaciones. Anotar encuadre, condición, duración y estadísticos. La
validación funcional por sí sola no cierra esos campos ni HM-T5 completo.

Los fotogramas de 120 ms a 1 s ejecutan como máximo tres pasos fijos
y descartan la deuda sobrante; no congelan indefinidamente la simulación.
Un salto mayor de 1 s, reloj hacia atrás o evento de ciclo de vida limpia el
tiempo acumulado. R solo avanza en PAUSED y sigue haciendo exactamente un paso.

## Registro de resultados

Último reporte: `c3aae59d1a70`, 2026-10-30, «prueba realizada, funciona
correctamente». Recibo: `reports/local/heather-room-physical-c3aae59d1a70.json`.
La consola de la sesión es New Nintendo 2DS XL; no se ha aportado una nueva
versión del entorno. Los casos sin desglose siguen abiertos.

| Campo | Resultado registrado |
| --- | --- |
| Build / SHA-256 / consola / entorno | `c3aae59d1a70`; hash en el informe de entrega; New Nintendo 2DS XL por contexto; versión del entorno pendiente |
| Instalación completa y arranque | 29 archivos verificados en SD; prueba funcional general satisfactoria según el usuario |
| Heather, habitación, vidrio y materiales originales | Funcionamiento general confirmado; sin desglose visual por elemento |
| Replay de 100 pasos y repetición | Pendiente |
| Caminar/correr/girar/bloqueo/Y | Pendiente |
| Pausa/R/L/entrada retenida | Pendiente |
| HOME, tapa y combinación | Pendiente |
| Error de carga, reintento y restauración | Pendiente |
| START y diez aperturas/salidas | Pendiente |
| Pico de memoria / CPU / GPU / FPS | No medidos |

Conservar capturas y observaciones con el ID de build. Un fallo conserva su
resultado y exige repetición identificada tras corregirlo; no se extrapola
la aceptación física del visor anterior a esta habitación.
