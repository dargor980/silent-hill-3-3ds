# SA-T5d — Vuelta continua y recuperación del combate

2026-10-20. **Vuelta continua del clip `0x1449` verificada** en el actor
`0x0209`, instancia `0x018E`. La selección inicial de IA y su aplicación
también se observaron. Las transiciones de daño `0x144A` y muerte `0x144B`
siguen pendientes; SA-T5d no está cerrado.

**Corrección de la prueba de daño:** el usuario confirma que los caballos
recibían daño durante el acertijo ya completado. Las capturas 02/03 permiten
comprobar vida agotada en los once actores `0x020C` del acertijo, distintos de
los tres `0x0209` del recurso estudiado. La [auditoría de colisión posterior](f03-02-carousel-collision.md)
confirma que ninguno figura como propietario de colisión de personaje en
ambos bancos de las 28 muestras 08–35 ni en el diagnóstico 36. El overlay
sí registra su geometría de escenario, y sus flags `0x2002` los excluyen
del filtro de objetivos analizado. No corresponde repetir golpes en esa
configuración; las transiciones pendientes requieren otra ruta demostrada.
La [revisión posterior de alternativas](f03-02-carousel-alternative-routes.md)
no encuentra esa ruta entre las examinadas; SC-T3b.2 mantiene evidencia
negativa y no justifica pedir otra acción manual por ahora.

Continúa la [preparación de la partida europea](f03-02-carousel-save.md)
y aplica [SC01–SC06](../../schemas/ps2-animation-continuity-v1.md).

## Escena e inicio natural

El mismo proceso 26887 alcanzó escenario `0x23`, sala `0xEB`, con el overlay
`amusement_02` contrastado y la bandera de activación en 1. La captura 03
contiene las tres instancias `0x018E–0x0190` activas. Los hashes completos de
MDL/ANM coinciden con la pareja `en_mry` identificada previamente.

Las capturas 04–06 detienen el selector original `0x002E1230`: cada instancia
solicita `0x1449`, modo 1, desde el retorno `0x002E0F4C`. Entre 04 y 05,
una sola reanudación registrada aplica al actor `0x018E` el descriptor
`0x003DC52C`, restablece el contador a cero y cambia el modo a 4. El ajuste
PAL convierte el desplazamiento solicitado de −512 a −614; el código
responsable se contrasta contra el ELF europeo.

## Segmento admitido

Las capturas 08–35 constituyen el segmento medido; el hueco posterior a 06
y anterior a 08 queda excluido. El filtro del breakpoint se corrigió a
`>>0x10`: el parser de PCSX2 interpreta el literal `16` como hexadecimal.

| Comprobación | Resultado |
|---|---|
| Retorno del consumidor | `0x001DD444` |
| Actor / instancia / dirección | `0x0209` / `0x018E` / `0x0044D630` |
| Capturas / avances adyacentes | 28 / 27 |
| Ciclos EE inicial / final | 559.725.532.003 / 560.044.394.783 |
| Velocidad / desplazamiento / ticks | 2457 / −614 / 2 |
| Incremento por evaluación | 3686 unidades Q12 |
| Avance acumulado / vuelta requerida | 99.522 / 98.304 unidades Q12 |
| Wraps observados | 1 |
| Error máximo de rotación | 0,000000554987285; límite 0,00001 |
| Error máximo de traslación | 0,000288555025; límite 0,001 |

Las 27 poses y pasos del reloj coinciden con el oráculo independiente.
El registro de 27 reanudaciones/paradas acompaña a las capturas y sus hashes;
el reconciliador no reemplaza esa procedencia. Ocho controles negativos
rechazan huecos, duplicados y alteraciones de identidad, reloj o registro.
La regresión del reconciliador, oráculo y decoder aprobó 140 pruebas.

Informe local `reports/local/f03-02-animation-continuity-v1.json`, SHA-256
`ea78b9d400712f07616794b0382da196bf5a9bb57b55d53c9002109a9914163c`.
Reproducción privada:

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/reconcile_carousel.py
```

El resultado certifica el segmento observado en espacio del modelo.
No verifica transformación al mundo, skinning, rendimiento ni ejecución 3DS.
La historia previa de la tarjeta importada sigue siendo desconocida.

## Restauración posterior solicitada por el usuario

Después de completar el segmento anterior, el usuario informó que murió
y pidió retroceder al inicio de la pelea. Se cargó la ranura 04 mediante
**Sistema → Cargar estado → Cargar Ranura 4**. La interfaz confirmó la carga.
SHA-256 del estado restaurado:
`5d8bcd0418f3a44e97e569b9e88082e4ab5147c3570a5c219e860e65bc29dad3`.

Se avanzaron las dos selecciones iniciales restantes y se reanudó el juego.
PINE confirmó el mismo PID, sala `0xEB` y las direcciones originales de las
tres instancias. El breakpoint del selector de IA sigue habilitado; el de
retorno de pose permanece deshabilitado. La conexión con la interfaz dejó
de responder al preparar la entrega: **la pausa final no quedó verificada**;
la última consulta PINE indicó ejecución.

La restauración inicia una reproducción diagnóstica. Sus futuras capturas
no satisfacen SC01 y no se concatenarán al segmento 08–35. Este último
conserva su evidencia anterior a la restauración: se verificaron nuevamente
los hashes de sus 28 estados. El capturador local consulta ahora el recibo
`recovery-boundary-v1.json` y etiqueta los siguientes estados como
`diagnostic_replay=true`, `state_restores=1`, `fresh_boot=false`.

Estados y recibo permanecen en
`/Users/germancontreras/sh3-private-data/f03-02-skeleton-continuity-v5/`.
La reproducción puede ayudar a localizar las transiciones restantes, pero
su validación bajo SC01 requiere un nuevo ensayo sin restauraciones.

## Comprobación del intento de golpe

El usuario confirmó haber golpeado caballos sin una parada automática.
La captura 36 corresponde a una pausa normal en `0x00081FC0`, ciclo
634.040.124.403, SHA-256
`cda4b8682bdcd7b6ac2c1f6ab992c5b69143ba46c81bf58170472f17cbd3ca62`.
Los tres actores siguen en `0x1449`, con vida igual al máximo y daño
pendiente cero. La instancia `0x018E` queda a 320,56 unidades XZ de Heather.
La captura no demuestra que ningún golpe anterior llegara: el código
`0x002E0B80–0x002E0BF4` contempla recuperación de vida en estado de IA cero.

Se contrasta en RAM contra el ELF la ruta de recepción
`0x001E06F0–0x001E08FC`. El punto `0x001E07A8` corresponde a un evento de
tipo 4, antes de la llamada de cálculo de daño `0x001DEF00`. Un evento en
esta ruta aún puede descartarse; alcanzarla no demuestra por sí solo daño
positivo ni transición de animación.

El usuario añadió una parada de ejecución en `0x001E07A8` con condición
`([s2+0xc]&0xffff)==0x209`. Se verificaron dirección, condición y activación
en la interfaz, junto con el selector `0x002E1230` habilitado y el retorno
de pose deshabilitado. Se reanudó el emulador para un nuevo intento normal.
No se alteraron posiciones, vida ni estado de IA.

El auditor diagnóstico `build/f03-02-skeleton-continuity/audit_hit_probe.py`
verifica recibo, hash, CRC, código, lista de actores y recursos completos.
Informe de la captura 36: `reports/local/f03-02-carousel-hit-probe-v1.json`,
SHA-256 `88a42c387b847bb63d4c4acce750409158fa44c12d29c56d26135b683f2b08f0`.
No contiene un impacto ni una selección observados.

El auditor original ahora rechaza explícitamente recibos restaurados.
El control negativo con la captura 36 fue rechazado sin modificar su
informe anterior; la reconciliación 08–35 conserva el mismo hash publicado.

La siguiente parada automática, captura 37, corresponde otra vez a la
selección inicial `0x1449`, modo 1, retorno `0x002E0F4C`, para la instancia
`0x0190`, ahora en `0x0044AD90`. Ciclo 681.493.650.124; SHA-256
`35d5e260b7798f4a40928025875fd9231b8e83e81a85880952c947806263bb85`.
Los tres actores tienen nuevas direcciones de objeto/IA/huesos respecto de 36
y el desplazamiento del reloj vuelve a cero antes de aplicar la selección.
La causa exacta de esa recreación no quedó atestiguada; se excluye cualquier
inferencia de continuidad entre ambas capturas.

El informe diagnóstico con 36 y 37 tiene SHA-256
`a66c6be19fda62709aaf8c0120536969ffcd51ea6f4d32d06a45efd9deae6c84`.
No prueba impacto ni transición de daño. Después se filtró `0x002E1230`
con `a1==0x144a || a1==0x144b`, se verificó el filtro en pantalla y se
reanudó. `0x001E07A8` sigue activo para todos los actores de tipo `0x0209`;
`0x001DD444` conserva su filtro original y sigue desactivado.

## Corrección de fase y destinatario del daño

El usuario aclara que los caballos sí recibían daño durante el acertijo y
ofrece volver a esa fase. Se compararon las capturas privadas existentes
02 y 03, sin interactuar con PCSX2 ni restaurar otro estado:

| Comprobación | Antes, captura 02 | Después, captura 03 |
|---|---|---|
| Sala / bandera | `0xEA` / 0 | `0xEB` / 1 |
| Actores `0x020C` | 11, vida completa y positiva | 11, vida menor o igual a cero |
| Identidad de esos registros | IDs `0x03F4–0x03FF` salvo `0x03F8` | Mismos IDs, direcciones y máximos de vida |
| Actores `0x0209` | Ninguno | Tres, recursos MDL/ANM completos contrastados |

Ambos grupos **coexisten** en la captura posterior: no se observa una
conversión de `0x020C` a `0x0209`. Los extremos concuerdan con el daño y
la resolución del acertijo que relata el usuario; no registran los impactos
individuales ni demuestran una vida de objeto ininterrumpida entre capturas.

El contraste del código europeo separa también sus rutas. La inicialización
`0x00313AD0` instala la actualización de IA `0x00313D10`; esta llama a
`0x00313D60`, que recoge eventos mediante `0x001E06F0` y contiene resta y
escritura de vida en `0x00313E04` y `0x00313E14`. La devolución inmediata en
`0x00313BE0` es un callback separado y no implica que el actor carezca de IA.
Estas instrucciones se contrastaron contra el ELF en ambas capturas;
no equivalen a un breakpoint alcanzado durante un golpe.

En los once `0x020C`, los campos habituales MDL/ANM permanecen nulos en ambas
capturas. Esto impide asignarles el par `en_mry` por esos campos, pero no
demuestra que carezcan de representación visual. Su recurso de dibujo exacto
sigue sin identificarse. La posibilidad de dañar `0x0209` por juego normal
en `0xEB` tampoco queda resuelta: tener código de daño y vida inicial no la
demuestra ni prueba invulnerabilidad.

La indicación anterior de golpear caballos tras la transformación fue
prematura. El filtro `kind == 0x0209` no captura impactos de `0x020C`, y la
selección inicial de la captura 37 no era un impacto. Antes de solicitar otra
prueba manual se debe verificar colisión, destinatario y condiciones de la
ruta `0x0209`. Volver al acertijo solo serviría para investigar `0x020C` y no
satisface por sí mismo SC-T3b/c del recurso actual.

Auditoría reproducible de esta comparación:

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/audit_carousel_phases.py
```

Informe local `reports/local/f03-02-carousel-phase-v1.json`, SHA-256
`91c6efb43e41c0ea68a34eee9b957db35d61a99d04a0f9a185b7a8bc250dc5f8`.
Verifica hashes/recibos, CPU/ciclos, overlay, ventanas del ELF, lista enlazada,
identidades, vida y recursos de `0x0209`. Mantiene `observed_impact=false` y
`transition_verified=false`; no modifica el segmento continuo 08–35.
