# HM-T1 — Inventario espacial de Heather original

2026-10-26. **HM-T1a/b/c completadas** para MDL522/ANM525, actor `0x0100`,
edición PAL SLES-51434. [Requisitos HM01–HM06 y tareas](../specs/sh3-3ds/heather-movement.md).
Prepara F06.01/F06.02 y una escena compartida. No acredita aún controlador,
root motion, resolución física ni habitación jugable.

La prueba física HL-T5a/b de `7250f427ffb9` quedó registrada en
[el informe HL](f03-02-heather-locomotion.md): carga, tres clips, controles,
START/tapa/HOME; 29,9 FPS submit, 10,08 ms Skin+sort, 23,3 ms Submit+wait y
4,32 ms GPU aproximados. HL-T5c mantiene pendiente la duración y el desglose
por clip/encuadre/arco. No se modifica el build aceptado ni el paquete privado.

## Inspector y responsabilidad

[actor_spatial.py](../../tools/inspectors/actor_spatial.py) recibe exactamente
128 bytes inmutables y un tipo esperado uint16 no cero. Lee el prefijo sin
seguir punteros, sin I/O y sin direcciones del juego en el módulo. Conserva
el bloque original, incluidos campos desconocidos, en una estructura inmutable.
Tipo, tamaño, entrada mutable y componentes NaN/inf se rechazan antes de
publicar un resultado. Escala, W, giro X/Z, fila afín y traslación discrepantes
se anotan; no se reparan. La comparación de traslación conserva cero con signo.
No deduce una matriz del giro ni considera rígida toda matriz sin observaciones.

| Campo relativo al actor | Lectura del perfil |
| --- | --- |
| `+0x0c` | Tipo uint16, `0x0100` en la auditoría privada |
| `+0x14/18/1c` | Escala3; unitaria en las 81 capturas |
| `+0x20` | Posición4, W=1 |
| `+0x30` | Giro4; X/Z/W cero en las ventanas observadas |
| `+0x40` | Matriz por columnas; traslación en `+0x70` |

El contrato conserva coordenadas en unidades originales. No interpreta el
factor de presentación del visor como conversión a metros, ni aplica por
segunda vez la traslación mundial a la pose local.

## Cotejo de fuentes conservadas

Se releyeron 56 capturas de `heather-normal-input-v1/replay-v1` y 25 de
`direct-run-idle-replay-v1`, con estados resueltos por sus recibos. Se verifican
SHA-256 de estados contra informes HL fijados, hash de recibo, PC `0x001DD434`,
retorno sin delay slot, `s0=0x004481D0`, ciclo EE, entrada y ordinal. Además,
recursos completos MDL522/ANM525, ambos canales, callback `0x001986C0`, etapa
33 y ocho ventanas ELF/RAM coinciden. El informe de cierre HL actúa como
ancla: `403a586353d64cde11d79b38235032cdb157c7defdbd718a2a267c09fa3ce8e9`.
Los recibos no se modifican y la continuidad anterior no se reinterpreta.

Los tres intervalos se mantienen separados; no se calcula una velocidad
cruzando el hueco entre carrera y caminata ni entre sesiones. Cada par usado
tiene ordinal consecutivo, ciclo creciente y ticks=2. Son **81 capturas / 78
pares**, leídos sin operar PCSX2 ni producir restauraciones nuevas.

| Ventana | Ordinales | Capturas / pares | Avance XZ por actualización |
| --- | --- | ---: | ---: |
| Carrera sostenida | 81848–81875 | 28 / 27 | 70 unidades, todos los pares |
| Caminata sostenida | 81958–81985 | 28 / 27 | 28 unidades, todos los pares |
| Carrera → espera | 82610–82634 | 25 / 24 | ≈69,99731 en los primeros cuatro pares; luego 0 |

Las primeras ventanas acumulan X=1890 y X=756 respectivamente, con Z
constante. Dividir por los dos ticks observados da 35 y 14 unidades/tick;
son mediciones de esas ventanas, no constantes generales del controlador.
La parada diagonal tiene yaw `−1,2803906202`, distinto del `1,5707963705`
de las ventanas rectas. En la muestra 6 cambia a espera y X/Z dejan de
variar; Y continúa ajustándose. Durante carrera, Y abarca aproximadamente
−0,567047 a 0,115311; en la caminata observada permanece en 0,115311.
No se descarta Y como ruido ni se atribuye todavía a una función de suelo.

La posición4 coincide bit a bit con la columna de traslación en **81/81**.
Todas las matrices pasan el contrato matemático rígido existente. Para el
perfil unitario con giro solo Y, `T(p)*Ry(yaw)` coincide con máximo
**4,69137e-8**, por debajo del límite fijado `1e-6`. Esto comprueba esas
observaciones del jugador, sin generalizar orden Euler ni precisión EE/VU.

## Ruta estática y captura siguiente

El callback `0x001986C0` despacha mediante `0x003D5180` y `0x003D5188`,
con una fase de actualización en `0x00198470` entre ambas tablas. El segundo
par contiene `0x001480D0` y `0x001452A0`. Su ejecución concreta en el tramo
ha de acreditarse con pares dinámicos; no se infiere de que el código esté
presente en RAM.

En `0x001480D0` se leen yaw `actor+0x34`, un componente en `+0x110`, un
escalar en `+0x108` y `0x01CFB1F8`; se escriben componentes en `+0xF0/F8`.
La ruta multiplica el vector por 500 antes de llamar a `0x001DCCE0` desde
`0x001481F4`. El llamador alternativo `0x001452A0` tiene selección por estado
y también desemboca en operaciones de posición; su caso concreto queda
pendiente de traza. No se fija semántica completa a esos escalares todavía.

En los snapshots de carrera `+0x108=3,5`, en caminata ≈1,4 y en espera 0;
`0x01CFB1F8≈0,04`. Los campos `+0xF0/F8` son compatibles con los avances
horizontales medidos tras el factor 500 y redondeo. Esa compatibilidad no
prueba aceleración, orden de colisión, unidad temporal general ni autoría
exclusiva del movimiento. Y cambia aun con `+0xF4=0` en esos retornos.

`0x001DCCE0` carga la posición de `actor+0x20` y el vector recibido, ejecuta
una operación VU, almacena en `0x001DCCF0` y fija W=1 en `0x001DCCFC`.
Es un escritor candidato concreto para HM-T2. El constructor común
`0x001DCBA0` toma giro y posición, escribe la traslación en `+0x70/74/78`,
W=1 y escala las tres columnas. La llamada desde `0x001DCB14` usa
`a1=actor+0x30` y `a2=actor+0x20`.

### Protocolo HM-T2a propuesto

1. Crear una sesión diagnóstica separada con un ancla preservada; registrar
   cualquier restauración como frontera y presupuestar solo el primer par.
   Mantener explícitamente anulados los breakpoints antiguos del protocolo HL.
2. Detener `0x001DCCE0` con `a0==0x4481d0`; registrar `ra`, ambos vectores,
   ticks, entrada, selección, contexto/escala y los escalares candidatos.
3. Capturar antes/después de `0x001DCCF0`, y el retorno exacto de esa llamada
   (derivado de `ra`, sin presumir un llamador). Cotejar escrituras y operaciones.
4. Capturar el constructor `0x001DCBA0` con `a0==0x4481d0` y su salida.
   Comparar la posición entre escritor, callback y matriz para localizar
   modificaciones adicionales, especialmente Y; no atribuirlas a colisión
   hasta seguir su productor.
5. Repetir mediante entrada normal en caminar, correr, parada y giro,
   distinguiendo tramo despejado/contacto. No cambiar PC/RAM para acreditar
   juego normal. Hacer pruebas sintéticas independientes antes de publicar
   una ley o modificar el visor.

Al cerrar HM-T1 este protocolo estaba preparado, sin cargar ni ejecutar.
Su primera cadena se ejecutó después en [HM-T2a](f06-01-heather-movement-capture.md),
en otra sesión diagnóstica. HM-T2 permanece abierta.

## Pruebas y comprobantes

- **243 pruebas nuevas**, 322 relacionadas aprobadas. Vectores propios y
  literales asimétricos, todas las longitudes truncadas, tipos, NaN/inf en
  los 27 campos, errores combinados, inmutabilidad, valores extremos y cero
  con signo. Las pruebas no contienen recursos o estados del juego.
- Módulo: **31/31 líneas y 20/20 ramas**, gate individual 80/80 integrado
  en el job `quality`; descubrimiento automático de pytest ya existente.
- Ruff, formato y trazabilidad del repositorio verificados localmente.
  CI remoto no ejecutado; no hay cambios de engine ni nuevo build ARM.
- Auditoría privada repetida con Python `-O`, resultado byte a byte idéntico.
  El auditor usa rechazos explícitos en su validación propia; reutiliza el
  cargador local ELF fijado. Los datos completos permanecen privados.

Informe local: `reports/local/heather-spatial-inventory-v1.json`, SHA-256
`057071b53dc2997a37f6c2e53c22e970034dcc7cfe08fac81b40e5d8353dc5c7`.
Script y listado estático: `build/heather-movement/audit.py` y
`candidate-code.txt`; XML/coverage: `build/heather-movement-pytest.xml` y
`build/heather-movement-coverage.json`. Las ocho ventanas cotejadas:

| Dirección | Bytes | SHA-256 |
| --- | ---: | --- |
| `0x001986C0` | 244 | `de1be29ca3db91b5fd731953aef9f4be4f8be9adabac254650e891b20a5ed79a` |
| `0x00198470` | 136 | `3cb0116804b188c8a06827dac6041a334968b7e90b7b7e48ecc830ca512d0015` |
| `0x001DCAF0` | 336 | `6e2f4bf433ea37b4a6b6159127a4303d9af7d295cfbd2c3202c1db697d04a91c` |
| `0x001480D0` | 368 | `1321d8df2ff32fb993d4d97e0f9055fd47c2c07711640a4b3af7ed09e8ab47e7` |
| `0x001452A0` | 992 | `0d03fc46626ea342bfc0acbc96f916adc090adf2ab60d6a672d8005923f6e5b8` |
| `0x001DCCE0` | 32 | `4f51d5f4d2e9fae01ea380a04dc1ade3f461627673b448cf034458e0ab8ccb4c` |
| `0x001DD3B0` | 144 | `d93fdbf082712dff263bd91651e2e8902814fce966c148a1f0dac422555a75ae` |
| `0x003D5180` | 16 | `be3ef3e865af04941cb0ee6eaeaddbe4536eefc22e111ba1e432490e4154861b` |


```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_actor_spatial.py tests/python/test_character_space.py tests/python/test_animation_descriptors.py --cov=tools.inspectors.actor_spatial --cov-branch --cov-report=json:build/heather-movement-coverage.json -q
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-movement-coverage.json --files tools/inspectors/actor_spatial.py
rtk proxy .venv/bin/python build/heather-movement/audit.py /tmp/heather-spatial-new.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Continuación ejecutada: [HM-T2a](f06-01-heather-movement-capture.md), entrada,
escritura, retorno, corrección Y y matriz en una actualización de carrera.
Sigue HM-T2b para ampliar perfiles, contactos y base temporal.
