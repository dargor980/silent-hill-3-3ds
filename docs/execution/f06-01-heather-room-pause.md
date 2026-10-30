# HM-T5 — Pasos involuntarios en pausa

2026-10-30. Build preparado: **`de58ea2bb966`**. Sustituye para esta prueba a
`217e1ace6571`; **HM-T5 continúa sin aceptación física**.

## Evidencia y causa delimitada

El usuario confirmó que tanto Step como `R presses` aumentaban sin tocar
botones mientras el HUD mostraba PAUSED. El contador bruto se incrementa
exclusivamente al recibir `hidKeysDown() & KEY_R`; el adaptador anterior
convertía cada uno de esos flancos inmediatamente en un paso en pausa.
La pausa permite R por contrato y no protegía ese comando frente a una
señal inestable. Esa es la vía de avance identificada, no un avance por
tiempo acumulado en el controlador.

En [libctru 2.7.0](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/services/hid.c),
`hidKeysDown` deriva de cambios en la máscara de botones; no es la función
de autorrepetición. No hay evidencia suficiente para atribuir la señal a
un botón defectuoso, a libctru, al entorno de arranque o a otro componente.
No se afirma haber reproducido el origen físico.

La prueba nueva inyecta R alto durante 20 ms y bajo durante 20 ms, con
flancos coherentes, durante diez segundos. El adaptador anterior falla al
primer pulso porque incrementa Step. Se conserva esa regresión roja en
`build/heather-room/pause-v1/noisy-R-red.log`. Sin ruido, el binario anterior
permanece en pausa en Azahar y las trazas host también conservan Step/Q12.

## Corrección

El puerto 3DS exige R continuamente suelto durante 80 ms para armar el
comando y una pulsación continuamente mantenida durante 80 ms para aceptar
un único paso. Mantenerlo no repite. Una liberación breve no lo rearma;
una pulsación breve, un flanco incoherente o una pulsación pendiente al
cambiar de estado no producen pasos. L, A, suspensión, retroceso del reloj
y saltos superiores a un segundo descartan la calificación pendiente.
Se conservan el movimiento direccional, B y el núcleo temporal/contactos.

La interfaz indica mantener R unos 0.2 s y soltarlo. `R presses (raw)` sigue
mostrando los eventos originales; `R steps` cuenta los pasos aceptados en
pausa. Ambos persisten al reiniciar con L. Así no se oculta una señal ruidosa
aunque se impida que sus pulsos breves avancen la simulación.

El filtro no puede distinguir una señal falsa sostenida que cumpla ambos
intervalos de una pulsación real. Su eficacia sobre el síntoma de la consola
requiere repetir allí la prueba. No se añade una copia del snapshot ni
asignación dinámica por fotograma; la reserva existente del controlador
y adaptador sigue comprobada mediante `static_assert` en host y ARM.

## Validación local

- 4/4 CTest relacionados pasan en Release y 4/4 con ASan/UBSan.
- 8/8 CTest GCC pasan, junto a las siete puertas de cobertura existentes.
  El adaptador alcanza 100% de líneas y 97.6% de ramas; el entry point,
  97.6% y 85.6%, respectivamente.
- Las trazas del bucle real con SDK simulado verifican diez segundos en
  pausa, pulsos breves de R con Arriba retenido, Q12, reinicio y un único
  paso al mantener R, a 25/60/143 Hz. Comparan el HUD publicado con los
  contadores brutos y aceptados; la prueba no se limita a compilar.
- El adaptador cubre el umbral exacto en ticks, flancos repetidos, liberación
  breve, flanco sin Held, pulsación sin flanco, reinicio, pausa/reanudación,
  suspensión y discontinuidades del reloj durante una pulsación pendiente.
- ARM compila con el SDK fijado y sus seis hashes son correctos.
- ZIP A/B idénticos: 20 archivos de aplicación, 21 entradas, 19908589 bytes.
  Los paquetes extraídos pasan los 12 replays privados de 100 pasos con
  Release/ASan-UBSan a 25/60/143 Hz. Conservan los recursos anteriores.

En Azahar 2126.2, Vulkan/New3DS, el ARM del ZIP muestra el ID correcto.
A pausa y L reinicia a Step/Q12=0; permanecen en cero más de tres minutos
sin botones (observaciones entre 12:44:29 y 12:47:48 UTC). Un pulso aislado
de R solicitado durante 30 ms incrementa el contador bruto 2→3 y conserva
Step=0 y R steps=1. Mantener R dos segundos produce Step 0→1, Q12=614 y
R steps 1→2; soltarlo y pulsarlo 0.2 s produce Step=2, Q12=1228 y R steps=3.
START regresa a la lista del emulador; Error permanece en none.

Se conserva también un intento previo de ocho pulsos UI seguidos de 30 ms:
el juego observó solo dos flancos y aceptó un paso. La duración de cada
llamada UI no demuestra qué niveles y liberaciones muestreó el ARM, por lo
que ese lote no acredita rechazo de ocho pulsos cortos. La prueba temporal
determinista se obtiene con el SDK simulado y el reloj controlado; la prueba
UI aislada confirma el rechazo de un evento bruto en el ejecutable ARM.
Estos resultados no reproducen ni resuelven por sí solos el origen físico.
Registro: `reports/local/heather-room-emulator-de58ea2bb966.json`.

ZIP SHA-256:
`311951bd9766cd84a7b2f6a3cb147395e114dbd8620ac7e6023a88f351c3d20d`.
3DSX: 234456 bytes, SHA-256
`ba2c4350903cc598f1d1b816ed98838e4d4f404b82a043332a8fdc95369bc8c5`.

Copias privadas: `/Users/germancontreras/sh3-private-data/heather-room-3ds-pause-v1-copy-a`
y `heather-room-3ds-pause-v1-copy-b`. Informes:
`reports/local/heather-room-pause-followup-217e1ace6571.json` y
`reports/local/heather-room-fix-de58ea2bb966.json`. Evidencia de build/pruebas:
`build/heather-room/pause-v1/`.

## Instalación SD verificada

El 2026-10-30 se instaló **`de58ea2bb966`** en
`/3ds/sh3_heather_room/` de la SD FAT32 `NO NAME`, con UUID
`2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`. Se cotejaron los manifiestos,
los hashes fijados, las copias A/B y los 21 elementos del ZIP. Los 20
archivos de aplicación (19903502 bytes) se escribieron en staging y se
releyeron antes y después de sustituir la carpeta activa. La verificación
final SHA-256 pasó tras sincronizar la tarjeta.

El build anterior `217e1ace6571` se conservó y verificó en
`/sh3-room-install-de58ea2bb966-20261030T161020Z/previous-217e1ace6571/`,
fuera de `3ds/`. El visor `sh3_heather_probe` permanece intacto. La SD
se expulsó de forma segura; en ese momento la prueba de consola seguía pendiente.

Recibo: `reports/local/heather-room-sd-delivery-de58ea2bb966.json`.
Instalador: `build/heather-room/sd-delivery-de58ea2bb966/install_sd.py`.

## Repetición física comunicada: pausa y R

El usuario comunicó esta secuencia el 2026-10-30, siguiendo el protocolo
de pausa del build instalado:

| Momento | Step | Q12 | R presses (raw) | R steps |
| --- | ---: | ---: | ---: | ---: |
| Después de L y soltar todo | 391 | 35274 | 0 | 0 |
| Después de 10 s sin botones | 391 | 35274 | 0 | 0 |
| Después de R medio segundo | 392 | 35888 | 1 | 1 |
| Después de R mantenido 2 s | 393 | 36502 | 2 | 2 |
| Después de otros 10 s sin botones | 393 | 36502 | 2 | 2 |

Los dos intervalos sin botones conservan todos los contadores. Cada R suma
exactamente un paso y 614 unidades Q12; mantener R dos segundos no repite.
La estabilidad en pausa y el paso único pasan en esta secuencia comunicada.
No hubo incremento bruto de R sin pulsación en esos intervalos, por lo que
esta muestra no prueba el filtrado de ruido físico ni identifica su origen.

**L confirmado en la repetición aislada:** tras solicitar L durante un
segundo en PAUSED, después de desaparecer el aviso de liberación, el usuario
comunicó **Step=0, Clip=101, Q12=0 y Error=none**. La lectura inicial
Step=391/Q12=35274 se conserva arriba; no se atribuye su causa sin evidencia.
La tabla no transcribe el ID visible, el estado ni Error; la asociación
al build procede de la instalación verificada y la prueba solicitada.

**Tapa en pausa confirmada:** el usuario cerró la tapa durante diez
segundos y, al abrirla, comunicó **PAUSED, Step=0, Q12=0 y Error=none**.
La imagen volvió normalmente. Esta observación valida el retorno en pausa.

**HOME en pausa confirmado:** después de pulsar HOME, esperar diez segundos
y volver, el usuario comunicó **PAUSED, Step=0, Q12=0 y Error=none**, con
imagen recuperada normalmente.

**Tapa en marcha: retorno funcional confirmado.** El usuario comunicó
Step **1 antes de cerrar, 87 al abrir y 300 en la lectura posterior**.
Confirmó que seguía RUNNING, sin error y con retorno normal de la imagen.
La espera entre 87 y 300 fue **aproximada**, no cinco segundos cronometrados.
Se conserva la diferencia de 213 pasos, pero no se convierte en una tasa:
sin marcas temporales no permite diagnosticar aceleración ni validar el
descarte de deuda temporal. Se valida el retorno funcional.

**HOME en marcha: retorno funcional confirmado.** Tras pulsar HOME,
esperar diez segundos y volver, el usuario comunicó **RUNNING, Error=none,
Step en aumento e imagen normal sin saltos visibles**. No aportó una traza
temporal para medir cadencia o deuda. Quedan pendientes la medición temporal
y la combinación HOME/tapa.

## Apariencia de la habitación aclarada durante HM-T5

El usuario comunica que no distingue objetos de la habitación y solo ve a
Heather. No aporta una captura física en esta observación. Se revisaron el
conversor, el renderer y la lámina privada software de HM-T4c.1: las 31
formas se conservan y se envían al render, pero 29 usan el mismo color plano
`NEUTRAL_RGB=(0.55,0.58,0.62)`, sin textura ni diferenciación de superficies.
En las cuatro vistas de esa referencia, Heather destaca sobre un campo
prácticamente uniforme. Esta limitación del perfil explica la apariencia
descrita; no demuestra que cada forma sea visible en la consola.

El color neutro y la cámara de inspección no representan una habitación
visualmente terminada. Las pruebas de controles y suspensión siguen siendo
evidencia válida de esas funciones; no acreditan legibilidad del escenario,
materiales originales de las 29 formas ni aceptación visual completa. La
combinación HOME/tapa solicitada sigue pendiente de respuesta.

Registro: `reports/local/heather-room-physical-de58ea2bb966.json`.
**Pausa, paso único R, ausencia de repetición al mantener R, reinicio L,
tapa y HOME en pausa, y retorno funcional de ambos en marcha validados en esta
secuencia comunicada. HM-T5 continúa con aceptación
parcial:** falta completar el resto del [protocolo físico](../compatibility/heather-room.md).

## Continuación visual

El build [161090bc9fd5](f06-01-heather-room-diagnostic.md) añade color y luz
de diagnóstico a las 29 formas neutras. Conserva el filtro de R y las
observaciones físicas anteriores; su aceptación en consola es independiente.
