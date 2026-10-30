# HM-T5 — Seguimiento de inmovilidad y carga

2026-10-29. **Aceptación física no aprobada** para `ad84b65cd58d`.
El usuario informa unos 20 s de carga, Heather de espalda e inmovilidad
aparente. A alterna RUNNING/PAUSED; R no produce un cambio percibido. El
aviso de liberación sí desaparece al soltar los botones; `Error: none`.
No hay una lectura física exacta de Step ni de tiempos de fotograma.

## Investigación

El binario exacto entregado arrancó en un perfil aislado de Azahar 2126.2
con Vulkan y New 3DS. En pausa, R cambió Step de 1863 a 1864. Arriba de la
cruceta desplazó a Heather y START salió. Por tanto, el fallo físico no se
reprodujo por completo en ese entorno. La cámara fija muestra a Heather
de espalda y el perfil conserva 29 materiales neutros: no es el escenario
texturado final. No se cambia el encuadre para ocultar el síntoma.

Se identificó un defecto de progreso: el controlador descartaba enteramente
cada intervalo >120 ms. Si todos los fotogramas superaban ese umbral,
RUNNING seguía activo pero nunca había simulación. Esto puede explicar
inmovilidad bajo carga, pero no demuestra por sí solo el caso físico de R,
que avanza sin depender del tiempo transcurrido.

El visor tampoco solicitaba CPU rápida en New 3DS. Revalidaba el mapa y
todos los datos inmutables del rig en cada presentación y calculaba CRC
bit a bit durante la carga. Los controles HID reales y la pila ARM de las
funciones inspeccionadas no mostraron un desbordamiento evidente; la mayor
reserva local inspeccionada fue 4136 bytes en la lectura CRC por bloques.
Esto no equivale a medir el máximo de pila en consola.

## Corrección

- Intervalos de más de 120 ms y hasta 1 s ejecutan tres pasos de 40 ms,
  sin conservar deuda; >1 s y retrocesos de reloj descartan el intervalo.
  Pausa, reinicio, HOME/tapa y liberación mantienen su limpieza de tiempo.
  R en pausa conserva exactamente un paso, con prioridad de comandos.
- Solicitud de CPU rápida antes de cargar en New 3DS; reposición al terminar
  la suspensión combinada HOME/tapa y desactivación al salir. Consolas
  anteriores o fallo al consultar el modelo conservan el modo predeterminado.
- `PreparedRoomScene` valida mapa/rig una vez y toma referencias prestadas
  que deben permanecer inmutables hasta destruirlo. Cada frame sigue
  validando pose, matriz y vértices resultantes. La API comprobada existente
  conserva su validación completa y atomicidad.
- CRC IEEE mediante tabla constante de 1 KiB, sin asignaciones. Se conservan
  todas las verificaciones de integridad, incluidos CRC duplicados en las
  fronteras de lectura/render; no se omiten validaciones para acelerar carga.
- Pantalla de carga y métricas de carga, FPS de presentación, intervalo,
  preparación CPU, envío/espera y GPU anterior. Máscaras HID y contador
  persistente `R presses` permiten verificar recepción de R independientemente
  de la visibilidad del paso en animación de reposo.

El presupuesto sigue siendo 40.33 MiB/64 MiB, con reservas ya existentes para
código, pila y SDK; no es una medición de pico de heap ni memoria de consola.
No se modifican recursos privados, posiciones, cajas, transformaciones,
orden de transparencia ni materiales.

## Validación

377/377 CTest Release y 53/53 CTest ASan/UBSan relacionados aprobados. Incluyen
100 fotogramas consecutivos de 160 ms sin inanición (300 pasos), límites de
120001/1000000/1000001 µs, pausa/R/reinicio/HOME/tapa, comprobación CRC contra
referencia bit a bit y lectura incremental, equivalencia del frame preparado,
atomicidad y ausencia de asignaciones durante el replay.

También pasan 109 pruebas Python de entrega, runtime y escena. La regresión
de fotogramas lentos falla con la política anterior: se conserva el resultado
rojo en `build/heather-room/fault-v1/slow-frame-red.log`.

La revisión final fuerza el intercambio de buffers de la pantalla de carga
antes de leer los recursos. Tras ese ajuste pasan 8/8 pruebas relacionadas
en Release, 8/8 con ASan/UBSan y 8/8 con GCC. Las siete puertas de cobertura
finales alcanzan 97.5–100% de líneas y 85.4–96.1% de ramas. La compilación
ARM termina con el SDK fijado y las seis comprobaciones SHA-256 correctas.
Docker se reinició con autorización del usuario; `test.postgres12` volvió
a ejecutarse después del reinicio.

Los ZIP de las fuentes privadas A/B son idénticos. Se verificaron sus 21
entradas, los 20 archivos de aplicación, CRC del ZIP, SHA-256 y coherencia
con las fuentes del build. Los paquetes extraídos pasan 12 replays de 100
pasos: A/B × Release/ASan-UBSan × 25/60/143 Hz. Estos replays usan el núcleo,
lectores y render del programa con dobles del SDK; no acreditan hardware.

En Azahar 2126.2, perfil aislado con Vulkan y New 3DS, el binario final mostró
`217e1ace6571` y `Error: none`. A pausó; R avanzó Step 1319→1320 y el contador
de pulsaciones 0→1. Arriba desplazó a Heather y Derecha la giró. L devolvió
Step y Q12 a cero, en pausa, y START regresó a la lista del emulador. El HUD
mostró 11439 ms de carga, 29.9 FPS de presentación y 33.4 ms por intervalo
en observaciones breves. Son datos del emulador, no medidas de rendimiento
en consola ni una aceptación sostenida de 60 s. No se capturó visualmente
la pantalla durante la carga.

Evidencia reproducible: `build/heather-room/fault-v1/` y
`build/heather-room/fault-v2/`. Informes locales:

- `reports/local/heather-room-physical-ad84b65cd58d.json` conserva el fallo físico.
- `reports/local/heather-room-fix-217e1ace6571.json` registra integridad y replays.
- `reports/local/heather-room-emulator-217e1ace6571.json` registra la prueba de controles.

## Entrega preparada

Build final **`217e1ace6571`**, preparado el 2026-10-30. El candidato
intermedio `d3f28ae2d627` queda conservado como evidencia; la entrega original
`ad84b65cd58d` tampoco se modifica.

Copias privadas verificadas:

- `/Users/germancontreras/sh3-private-data/heather-room-3ds-fix-v2-copy-a`
- `/Users/germancontreras/sh3-private-data/heather-room-3ds-fix-v2-copy-b`

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| ZIP | 19907045 | `e18a776a72c7262a8bda8e8f37381a2cb97f8528837c21e6b7848000c950b6c7` |
| 3DSX | 233844 | `99bd791b2d966479c5a950a281ec342be1693cf39413f7e18464e2e3a5d1624b` |

## Instalación en SD — 2026-10-30

El usuario conectó la SD y autorizó copiar `217e1ace6571`. Se comprobó la
identidad del volumen, el build anterior contra su recibo, ambos paquetes
privados y sus hashes fijados antes de escribir. Los 20 archivos nuevos
(19901958 bytes) se copiaron a `/3ds/sh3_heather_room/`; se sincronizaron y
releyeron para verificar tamaño y SHA-256. La copia anterior se conservó
íntegra fuera de `/3ds/`, en
`/sh3-room-install-217e1ace6571-20261030T030758Z/previous-ad84b65cd58d/`.
El visor `sh3_heather_probe` permaneció intacto.

Recibo: `reports/local/heather-room-sd-delivery-217e1ace6571.json`.
Instalador: `build/heather-room/sd-delivery-217e1ace6571/install_sd.py`.
La expulsión segura terminó correctamente y se confirmó que la SD ya no
estaba montada. **Lista para probar en consola; aceptación física pendiente.**
La aceptación física requiere confirmar el ID y seguir el
[protocolo HM-T5](../compatibility/heather-room.md), incluyendo la recepción
de R mediante su contador y Step. El síntoma físico de R todavía no se ha
reproducido localmente y no se declara resuelto por las pruebas anteriores.

## Repetición física comunicada — 2026-10-30

Tras instalar `217e1ace6571`, el usuario informa `CPU: NEW FAST`,
`Load: 7492 ms` y `Error: none`. Arriba permite caminar, Derecha girar y el
aviso de liberación desaparece al soltar los botones. También informa
«arriba corre», sin precisar B; la carrera con su clip queda por confirmar.
Es una muestra de carga, no una medición sostenida de rendimiento.

Después de L informa `Step: 0`, `Clip: 101`, `Q12: 40818`; tras unos diez
segundos, `Step` alcanza aproximadamente 206. A la consulta específica,
confirma que la pantalla mantuvo `PAUSED` todo el tiempo sin pulsar botones.
**La aceptación de pausa falla según esta observación y HM-T5 sigue sin
aprobarse.** No se atribuye aún la causa al controlador, HID o HUD. Faltan
los contadores `R presses`, las máscaras de entrada y una lectura conjunta
antes/después. El ID esperado procede de la instalación verificada; falta
su transcripción desde la pantalla física.

Registro: `reports/local/heather-room-physical-217e1ace6571.json`. Se conservan
el resultado físico anterior y las validaciones locales; estas no anulan
el fallo comunicado por el usuario.

El usuario aclaró después que `R presses` también aumenta sin tocar botones.
La reproducción con entradas inestables, el filtro aplicado y el nuevo build
`de58ea2bb966` se documentan en [el seguimiento de pausa](f06-01-heather-room-pause.md).
El origen físico de esos flancos sigue sin identificar; no se declara
aceptación en consola a partir de la regresión local.
