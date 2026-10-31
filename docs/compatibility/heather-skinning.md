# HS: comparación CPU / híbrida en consola

Build: **f64760613473**. Paquete específico HS-T4; pendiente de ejecución
física HS-T5. HM-T5 adicional y pared 60 siguen aplazados.

## Instalación e identidad

Las copias privadas A y B son redundantes e idénticas; ambas contienen los dos
modos en una aplicación. Instalar una sola en `3ds/sh3_heather_skinning/`.
Conservar `3ds/sh3_heather_room/` con el HG aceptado `0188790baedd`.
Comprobar los SHA-256 del ZIP y sus 29 archivos antes de retirar la SD.
No mezclar ejecutables o recursos de carpetas distintas.

Abrir **SH3 Heather CPU GPU**. Soltar todos los botones antes de elegir:
**A = CPU**, **L = HYBRID**, **START = salir**. En la escena, SELECT vuelve al
selector y libera la variante anterior; cada elección vuelve a cargar recursos.
Anotar modelo de consola, build, alimentación, CPU New fast/default y Load ms.
El modo CPU de este build es la referencia de la comparación instrumentada;
el HG conservado permite regresar a la versión aceptada.

## Comprobación funcional previa

1. Elegir CPU, soltar todo y anotar `Asked:CPU Active:CPU`, `CPU_SELECTED`,
   `PAUSED`, Step 0, Clip 101, Q12 0, R raw 0, R steps 0 y Error none.
2. Mantener R 0,2–0,5 s, soltar y esperar: debe avanzar una sola vez. Mantenerlo
   2 s en otra pulsación también avanza una sola vez. Diez segundos sin botones
   en PAUSED no cambian Step/Q12/R steps. El contador raw solo es diagnóstico.
3. L restablece Step 0, Clip 101, Q12 0 y conserva PAUSED; R steps es acumulativo
   durante esa elección de modo. Soltar todo elimina Release all buttons.
4. A alterna pausa; cruceta arriba camina, B+arriba corre, derecha/izquierda
   giran; soltar vuelve a espera. Comparar los cinco clips, entrada/salida de
   giro y contacto con los objetos sin cambiar los controles.
5. Volver con SELECT, elegir HYBRID y repetir desde la misma pose. Debe mostrar
   `Asked:HYBRID Active:HYBRID`, `HS_READY` y Error none. Si dice Active:CPU,
   anotar Status: es fallback y esa ventana no cuenta como híbrida.
6. Comparar habitación, objetos, cuerpo, cabello y vidrio: mismos materiales,
   visibilidad, encuadre y orden. Buscar vértices separados, geometría que se
   estira, agujeros, parpadeos o transparencia alterada. Usar L y pasos R iguales
   para cotejar poses; no usar una espera aproximada para igualar Step.
7. Fuera de una ventana de medición, verificar HOME y tapa durante 10 s en ambos
   modos: misma pausa/pose, o continuación RUNNING sin deuda ni salto, Error none.
   START debe volver al lanzador. Anotar cualquier diferencia antes de medir.

## Ventanas de coste del caso real

Con las comprobaciones anteriores conformes, usar una secuencia alternada
**CPU, HYBRID, CPU, HYBRID, CPU, HYBRID**. No cambiar alimentación ni condiciones
entre variantes. Para cada ventana volver al selector, elegir modo, verificar
pose inicial, pulsar A, soltar y pulsar X. Mantener a Heather en espera para
este primer caso controlado; repetir después por separado con giro derecho y
con giro izquierdo sostenidos desde antes de X. Identificar siempre el caso.

X descarta 32 cuadros de calentamiento y registra 256 llamadas al bucle; espera
la finalización GPU del último envío válido. La pantalla inferior permanece
quieta durante la captura. La simulación y la imagen superior continúan.
No pulsar Y, A, L, SELECT, HOME ni cerrar la tapa durante una ventana. Pausa,
reinicio, suspensión o salida cancelan la ventana; volver a iniciarla.

Al aparecer `Window: DONE`, pulsar A para pausar y anotar las dos páginas
(**Y** las alterna) antes de X o SELECT, que sustituyen/descartan los resultados.
Los resultados se conservan en RAM; este build no escribe registros en la SD.

| Dato | Registro por ventana |
| --- | --- |
| Identidad | Build, consola, modo solicitado/activo, Status, CPU, Load, memoria |
| Ejecución | Caso, orden de ventana, Error, Step/Clip/Q12 al terminar |
| Integridad | n=256, fail, Frames inicio..fin, GPU matched/256 |
| Página 1 | mediana/p95/máximo de Move/contact, Anim/pose, Validate, Palette, CPU deform, Sort/expand, GPU rows |
| Página 2 | mediana/p95/máximo de Own wait, Copy/flush, Submit, CPU total, Cadence, GPU queue |

Todas las duraciones son milisegundos; p95 usa rango más próximo y la mediana
promedia los dos centros. CPU total cubre la llamada al controlador; Cadence
usa 255 diferencias entre comienzos consecutivos, incluyendo esperas externas.
Las fases CPU son disjuntas; CPU total ya las incluye. GPU queue se vincula por
ID al envío que la originó, incluye transferencias y puede solaparse con CPU:
**no sumar GPU a CPU total ni sumar total a sus fases**. Submit incluye el
flush global que realiza FrameEnd. Las llamadas fallidas cuentan en fail;
GPU matched excluye envíos fallidos o ausentes. Si no hay 256 coincidencias,
registrar la incidencia y no declarar equivalencia de coste de esa ventana.
Carga se informa aparte; descompresión y audio no se ejecutan en este perfil.

## Alcance de la decisión HS-T5

La variante híbrida conserva por ahora la deformación, validación y expansión
CPU completa, además de su copia dinámica; sustituye el dibujo de los opacos
por lotes GPU. Una mejora de velocidad no está demostrada ni garantizada.

Este paquete cubre el caso real hp34. No contiene perfiles de carga creciente;
las curvas de huesos, influencias y lotes exigidas por HS-T5 requieren perfiles
controlados adicionales. Tampoco una inspección visual acredita las tolerancias
numéricas reales de PICA: siguen pendientes las mediciones GPU de HSN v1
(XYZ, W, proyección y clipping), con sus referencias independientes.
Conservar CPU como referencia hasta reunir esa evidencia. El build ARM y las
pruebas con dobles SDK no constituyen aceptación de consola ni cierre de HS-T5.
