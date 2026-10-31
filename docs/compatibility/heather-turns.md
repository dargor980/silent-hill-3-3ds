# HG-T5 — Prueba de giros en consola

Build **0188790baedd**, perfil 2: espera 101, caminar 109, correr 113,
giro derecho 107 y giro izquierdo 108. Preparación del paquete: 2026-10-30.
**Prueba física pendiente.** Anotar resultados solo después de observarlos.

Este protocolo comprueba los giros nuevos, sus transiciones y conservación
de pose. Las mediciones y pruebas adicionales de HM-T5 siguen aplazadas:
no solicita FPS, pico de memoria, recorrido de contactos, pared 60, errores
de carga provocados ni diez aperturas/salidas. HOME/tapa se comprueban aquí
solo para conservar una mezcla de giro HG.

## Instalación e identificación

1. Usar una de las copias A/B verificadas de `sd-card.zip`; ambas contienen
   los mismos bytes. Conservar la carpeta anterior antes de reemplazarla.
2. Extraer en la raíz de la SD. Deben quedar **29 archivos** en
   `/3ds/sh3_heather_room/`: ejecutable `.3dsx`, `.smdh`, `LEEME.txt`,
   `scene.srr`, `map.srm`, `heather.sri`, `glass.rgba`, trece `texture-*.rgba`
   y nueve `room-texture-*.rgba`. `SHA256SUMS` queda en la raíz del ZIP.
   Verificar los hashes antes de instalar; no mezclar archivos de otros builds.
3. Abrir **SH3 Heather room** desde Homebrew Launcher y soltar los botones.
   Comprobar **Build: 0188790baedd**, habitación y Heather visibles,
   `MATERIALES ORIGINALES / LUZ FIJA` y **Error: none**.
   `Accounted: 49.42 / 64 MiB` es presupuesto, no memoria medida.
4. Anotar modelo de consola y versión del entorno si se conoce. Las copias
   y sus capturas contienen recursos privados; conservarlas fuera de git/CI
   y servicios públicos. Esta preparación no instala automáticamente la SD.

## Controles y datos que anotar

| Entrada | Acción |
| --- | --- |
| Derecha / izquierda, sin Arriba | Giro 107 / 108 sobre el sitio |
| Arriba / Arriba+B | Caminar 109 / correr 113, con sus transiciones |
| Arriba + dirección lateral | Avanzar girando, con animación de marcha |
| A | Pausa/reanuda; después soltar todos los botones |
| R, en PAUSED | Un paso con los botones de dirección/B mantenidos |
| L | Reinicia Step, pose y posición; conserva PAUSED/RUNNING |
| START | Sale al lanzador |

Para cada pulsación de R, mantenerlo unos **0,2–0,5 s**, soltarlo al menos
0,2 s y esperar que el HUD refleje el paso. Mantener R no debe repetir.
Puede mantenerse la dirección mientras se suelta R, excepto cuando aparece
`Release all buttons`: entonces hay que soltar también la dirección.
Si un toque no se acepta, contar el incremento de **Step**, no el toque.

Anotar **PAUSED/RUNNING, Step, Clip, Q12, R presses (raw), R steps y Error**
en los puntos de las tablas. Registrar además si la pose cambia suavemente,
si gira en el sentido esperado y si aparece desplazamiento inesperado.
En caso de fallo añadir `Held`, `Down` y el aviso de liberación.

`Clip` es el destino de la animación: puede cambiar antes de terminar la
mezcla. **Q12=0 durante la mezcla es normal**; el contador mostrado es la
próxima fase, no la pose que se está dibujando. El HUD no muestra beta/modo.
`R presses (raw)` cuenta flancos brutos, mientras `R steps` cuenta pasos
aceptados; **L no reinicia esos dos contadores**. Tomar una base después de
cada L y usar diferencias. En un guion solo con R, ΔR steps debe igualar Step.
Una señal bruta adicional no acredita un paso adicional: registrar ambos.

## HG-C0 — Punto de partida para cada caso

Si dice RUNNING, pulsar A una vez. Soltar todo y esperar a que desaparezca
`Release all buttons`. Pulsar L, soltar todo y esperar de nuevo.
Debe quedar **PAUSED, Step 0, Clip 101, Q12 0, Error none**.
Anotar la base de R raw y R steps. No pulsar A durante los casos con R.

## HG-C1/C2 — Ciclo derecho e izquierdo y retorno a espera

Hacer el guion completo primero con **Derecha (107)** y después, desde
HG-C0, con **Izquierda (108)**. No mantener Arriba ni B.

1. Mantener la dirección elegida y avanzar con R hasta Step 3. Soltar todo
   y esperar diez segundos: Step, Clip, Q12, R steps y pose deben conservarse.
2. Volver a mantener la misma dirección. Para llegar a Step 4, mantener R
   **dos segundos** y soltarlo: debe añadir exactamente un paso.
3. Continuar con esa dirección y pulsaciones individuales hasta Step 24.
   Observar la entrada de espera a giro y un ciclo completo, incluido su wrap.
4. Soltar la dirección. Dar nueve pasos con R sin dirección, hasta Step 33:
   Heather vuelve suavemente a espera y deja de cambiar su orientación mundial.

| Step | Clip esperado | Q12 esperado | Comprobación |
| ---: | ---: | ---: | --- |
| 0 | 101 | 0 | Reinicio |
| 1 | 107 / 108 | 0 | Comienza la mezcla |
| 3, antes y después de diez segundos | 107 / 108 | 0 | Pausa conserva la mezcla |
| 4, tras mantener R dos segundos | 107 / 108 | 0 | Un solo paso |
| 5 | 107 / 108 | 0 | Último paso de mezcla |
| 6 | 107 / 108 | 2304 | Giro estable |
| 22 | 107 / 108 | 39168 | Próxima fase cerca del final |
| 23 | 107 / 108 | 512 | Contador envuelto |
| 24 | 107 / 108 | 2816 | Continúa el ciclo |
| 25 | 101 | 0 | Comienza retorno a espera |
| 32 | 101 | 0 | Último paso de retorno |
| 33 | 101 | 614 | Espera estable |

En todos estos puntos: PAUSED, Error none y ΔR steps=Step. El giro sobre
el sitio puede mover pies/cuerpo por animación; no debe trasladar la posición
mundial por el suelo. Comprobar que Heather no desaparezca ni se deforme.

## HG-C3 — Cambiar de sentido pasa por espera

Desde HG-C0, dar seis pasos con Derecha. Sin reiniciar, cambiar a Izquierda
y dar quince pasos más. Mantener solo la dirección correspondiente durante R.

| Step | Clip | Q12 |
| ---: | ---: | ---: |
| 6 | 107 | 2304 |
| 7–14 | 101 | 0 |
| 15 | 101 | 614 |
| 16–20 | 108 | 0 |
| 21 | 108 | 2304 |

Repetir desde HG-C0 intercambiando Izquierda y Derecha: 108→101→107, con
los mismos Step/Q12. La orientación mundial sigue la dirección actual desde
el primer paso; la animación termina sus mezclas antes de llegar al otro giro.
Esa diferencia temporal está prevista por el contrato de inspección.

## HG-C4 — Una intención cancelada no reaparece

Desde HG-C0: un paso con Derecha, un paso con Izquierda y luego trece pasos
sin dirección. La entrada derecha termina antes de volver a espera; el giro
izquierdo cancelado **no debe llegar a Clip 108**.

| Step | Clip | Q12 |
| ---: | ---: | ---: |
| 1–5 | 107 | 0 |
| 6 | 107 | 2304 |
| 7–14 | 101 | 0 |
| 15 | 101 | 614 |

## HG-C5 — Conservar la mezcla HG al volver de HOME/tapa

1. Desde HG-C0, dar tres pasos con Derecha y soltar todo:
   PAUSED, Step 3, Clip 107, Q12 0. Anotar R steps y pose.
2. Pulsar HOME, esperar diez segundos y volver. Soltar todo; deben conservarse
   esos datos, la pose y Error none. Con Derecha+R dar un paso: Step 4.
3. Soltar todo, cerrar la tapa diez segundos y abrir. Debe conservar Step 4,
   Clip 107, Q12 0, PAUSED y la pose. Soltar todo si lo solicita.
4. Dar dos pasos con Derecha+R: Step 5/Q12 0 y Step 6/Q12 2304.
   No debe reiniciar la mezcla ni recuperar el tiempo transcurrido fuera.
5. Pulsar L y soltar: Step 0, Clip 101, Q12 0, PAUSED, Error none.

Si HOME no permite salir y volver en ese entorno, anotarlo como no comprobado.
No se solicita HOME+tapa combinado ni revalidar aquí todo el protocolo HM-T5.

## HG-C6 — Cinco acciones en reproducción normal y salida

Desde HG-C0, pulsar A y soltar todo. En RUNNING, mantener Derecha un par de
segundos, soltar un segundo y repetir con Izquierda. Debe alternar espera
101 con giro 107/108, con Step aumentando y sin Error.
Probar brevemente Arriba (109), Arriba+B (113, pasando por caminar) y
Arriba+Derecha (animación de marcha 109 cuando termina su transición).
Al soltar, vuelve a 101 después de la mezcla. Pausar y anotar el último
Step/Clip/Q12 y cualquier defecto visual; no se exige un Step final exacto.
Un contacto puede impedir avanzar mientras la animación continúa.
Terminar con START y registrar si vuelve al lanzador.

## Hoja de resultados

Build: __________  Consola: __________  Entorno: __________  Fecha: __________

| Caso / momento | Estado | Step | Clip | Q12 | R raw | R steps | Error / observación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0 / base | | | | | | | |
| C1 / derecha, punto de tabla | | | | | | | |
| C2 / izquierda, punto de tabla | | | | | | | |
| C3 / inversión, punto de tabla | | | | | | | |
| C4 / cancelación | | | | | | | |
| C5 / antes y después de HOME | | | | | | | |
| C5 / antes y después de tapa | | | | | | | |
| C6 / reproducción y START | | | | | | | |

Añadir filas para los puntos comprobados y marcar cada caso como correcto,
fallo o no comprobado. Si aparece un error o un contador inesperado, detener
ese caso y conservar los datos antes de L; una repetición no borra el fallo
anterior. El éxito de estos casos acredita esta entrega HG, no la aceptación
global de HM-T5, rendimiento, fidelidad completa PS2 ni campaña.
