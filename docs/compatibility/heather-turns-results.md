# HG-T5 — Resultados físicos de 0188790baedd

2026-10-30. **Prueba funcional acotada de HG aceptada según el usuario** en
el build `0188790baedd`. Se siguió el [protocolo de giros](heather-turns.md)
después de su instalación verificada en SD. La confirmación final acredita
Step creciente en RUNNING, ausencia de errores/saltos y retorno normal al
lanzador mediante START. HM-T5 adicional y pared 60 continúan aplazadas.

## Procedencia y alcance

El usuario confirmó en pantalla Build `0188790baedd`, PAUSED, Step 0,
Clip 101, Q12 0, R raw 0, R steps 0 y Error none antes de empezar.
El ejecutable instalado tiene SHA-256
`8c2612a3a203cb7e6a8b1995c9d0aade0a31112e43a437b49ccaa26b016d9f2d`.
La consola es New Nintendo 2DS XL por contexto previo; modelo y versión del
lanzador no se volvieron a transcribir en esta sesión.

La evidencia son lecturas y confirmaciones del usuario, incluidas respuestas
«coincide» a tablas concretas. No es una captura independiente ni una traza
instrumentada de todos los cuadros/pulsaciones. El recibo distingue lecturas
explícitas de confirmaciones de tabla; no rellena datos que no se comunicaron.

## Resultados observados

| Caso | Resultado comunicado |
| --- | --- |
| C0 — Identidad/reinicio | Build correcto; PAUSED, Step 0, Clip 101, Q12 0, R steps/raw 0/0, Error none |
| C1 — Giro derecho y espera | Entrada a 107; Step 6/Q12 2304; Step 22–24/Q12 39168→512→2816; retorno a 101 en Step 33/Q12 614/R steps 33. Heather vuelve a espera |
| C1 — Pausa/R sostenido | Step 3 permanece tras diez segundos sin botones. R mantenido dos segundos añade solo un paso: Step 4/R steps 4/R raw 4, Error none |
| C2 — Giro izquierdo y espera | Step 3/Clip 108/Q12 0/R steps 36 y pose quieta tras diez segundos. Step 6/Q12 2304/R steps 39; wrap coincidente en 22–24, sin saltos. Retorno suave: Step 33/Clip 101/Q12 614/R steps 66 |
| C3 — Derecha→espera→izquierda | Cinco puntos coincidentes y transición fluida; final Step 21/Clip 108/Q12 2304/R steps 87 |
| C3 — Izquierda→espera→derecha | Cinco puntos coincidentes y transición fluida; final Step 21/Clip 107/Q12 2304/R steps 108 |
| C4 — Cancelación | Cinco puntos coincidentes; nunca apareció Clip 108. Final Step 15/Clip 101/Q12 614/R steps 123 |
| C5 — HOME durante mezcla | Tras diez segundos y retorno: PAUSED, Step 3/Clip 107/Q12 0/R steps 126, Error none; misma pose e imagen normal |
| C5 — Tapa y continuación | Se conservaron las lecturas Step 4/Clip 107/Q12 0/R steps 127. Después, Step 5/Q12 0/R steps 128 y Step 6/Q12 2304/R steps 129; animación sin saltos |
| C5 — L | PAUSED, Step 0, Clip 101, Q12 0, R steps 129, Error none |
| C6 — RUNNING y salida | Clips 107/108/109/113 y 109 al avanzar girando coincidentes. Step aumenta; sin errores ni saltos; START vuelve normalmente al lanzador |

Los reinicios L conservaron el contador acumulado de pasos R, que terminó
en **129**. Se confirmaron PAUSED y Error none en los puntos comunicados.
Para C6 se pidió aclarar expresamente el avance en RUNNING, ausencia de
errores/saltos y salida por START; la respuesta fue «Sí, todo eso se cumplió».
No se asigna un Step/Q12 final exacto al recorrido libre.

## Detalle de las lecturas R

Se conservan las discrepancias del contador bruto: en C2/Step 6 el usuario
aclaró **R raw 36 y R steps 39**; en Step 24 indicó **R raw 75 y R steps 57**.
La primera respuesta `R raw 6` fue corregida mediante una nueva lectura a 36.
No se atribuye una causa al dispositivo, al SDK ni al filtro a partir de
estos datos. R steps y los puntos de simulación comunicados sí coinciden
con el guion. La fidelidad del contador bruto no queda acreditada.

Los pasos intermedios 4 y 5 del giro izquierdo no se transcribieron por
separado; sí se comunicó Step 6 y los puntos posteriores. R sostenido se
confirmó explícitamente durante el giro derecho. La aceptación se limita
al comportamiento funcional comunicado, sin presentar una traza completa
de cada pulsación como observada.

## Registro y límites

Recibo local: `reports/local/heather-turns-physical-0188790baedd.json`, SHA-256
`48cc8ec196f53aba792f830d40db9e42a1789d637d33ce93be4fe29218366c65`.
Vincula el recibo SD y el protocolo empaquetado por hash. Los manifiestos,
recibos de preparación/SD y la guía incluida conservan su estado histórico
anterior a la prueba; el resultado actual se registra en este documento.

No se obtuvieron nuevas medidas de FPS, CPU/GPU, pico de memoria ni pila
física. No se reabrieron recorrido/contactos de HM-T5, HOME+tapa combinado,
errores de carga provocados ni aperturas/salidas repetidas. La validación de
este perfil HG no cierra HM-T5 completo, F06.02 global, G04/G05 ni fidelidad
general del movimiento o render PS2.
