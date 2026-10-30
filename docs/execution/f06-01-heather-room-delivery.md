# HM-T4d — Entrega privada de Heather en hp34

2026-10-29. **HM-T4d completada**, build de entrega **`ad84b65cd58d`**.
Se prepararon las dos copias
privadas con ejecutable, datos mínimos, hashes y protocolo físico. La entrega
conserva el perfil diagnóstico: 31 formas, 29 con material neutro, Heather
original y vidrio texturados, cámara fija propia y contactos planos con
32 cajas. La aceptación física **HM-T5 sigue pendiente**.

## Corrección antes de entregar

La revisión de la ruta de arranque encontró una repetición del defecto de
separador que había fallado físicamente en el visor de locomoción: el entry
point pasa `sdmc:/3ds/sh3_heather_room/` y el nuevo lector de habitación
concatenaba otra barra. El host normaliza `//`, por lo que las pruebas de
archivos con rutas de host no lo detectaban.

Se añadió una regresión que verifica cada ruta literal recibida por stdio,
antes de redirigirla al fixture inventado. Falló contra el código anterior
(`path-red.log`) y pasó al corregir el separador en
[`room_runtime.cpp`](../../engine/platform/common/room_runtime.cpp).
Cubre la raíz SD con/sin barra final, directorio relativo con/sin barra y `/`,
incluidos SRR1, mapa, SRI2, texturas y vidrio. No se cambiaron los datos
privados, contactos, animación, cámara o estados de render. El build previo
`c25237edb7d9` conserva su evidencia HM-T4c.2; esta entrega usa el ID nuevo.

## Artefactos

Copias nuevas y exclusivas, con directorios 0700 y archivos 0600:

- `/Users/germancontreras/sh3-private-data/heather-room-3ds-v1-copy-a/`
- `/Users/germancontreras/sh3-private-data/heather-room-3ds-v1-copy-b/`

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| `sd-card.zip` | 19904338 | `027c5f8a6517553cafc0508591b94850be047dd734e09db893ad9f355b598e12` |
| `sh3_heather_room.3dsx` | 232100 | `7117b69148fbeaafa717d7b6217b6d358d51d82bf73705f94ba0e6fabb5cd0cf` |
| `sh3_heather_room.smdh` | 14016 | `9bc594a2cf28241507f8f0663f45d4d41d0f50e878b68bf5fcf9891cb87c44e6` |
| `LEEME.txt` | 7375 | `b3f03486dc0b9c63750585ac06149a8ef1eac3bec7d334bf1a87a7ade82fcf78` |
| `manifest.json` | 4238 | `1214da0e6b8cade42a13ec3cbb43d509152762861df3def5357fdabda293ce60` |

Cada ZIP contiene **20 archivos de aplicación** bajo `3ds/sh3_heather_room/`
y `SHA256SUMS` en la raíz. Incluye `.3dsx`, `.smdh`, `LEEME.txt` y los 17
archivos de datos usados por el runtime: SRR1, SRM1, SRI2, vidrio y trece RGBA.
Los archivos sueltos más el ZIP ocupan **39803589 bytes por copia**, sin
manifiestos. Los recursos crudos y JSON de procedencia permanecen en HRS/HRR;
no se necesitan en la SD. No se incluyen en los artefactos de CI.

El ELF de código, **2608656 bytes**, permanece en
`build/heather-room/delivery-v1/arm/sh3_heather_room.elf`, SHA-256
`4ea82c14bdeec3ea7bf460eaf080c2e64b6f675af1bd9597e9b8560a8d4843cf`.
ELF32 ARM EABI5: text=207884, data=7640 y BSS=19336 bytes. Presupuesto de
runtime **40.33 MiB/64 MiB**, sin cambio respecto a c.2; no es memoria medida.

## Construcción y publicación

[`build_heather_room.sh`](../../scripts/build_heather_room.sh) exige un destino
nuevo, compila el target `_3dsx`, registra ID, paquetes del SDK, imagen fijada
y seis hashes verificados. Se ejecutó en el contenedor devkitPro fijado,
sin red, raíz/fuentes de solo lectura, sin capacidades y con límites CPU/RAM.
El contenedor no recibió datos privados. El shader ensamblado pasó su gate.
CI incorpora este target y conserva únicamente código y metadatos.

[`prepare_heather_room_delivery`](../../tools/pipeline/prepare_heather_room_delivery.py)
autentica las fuentes HRS A/B, reconstruye SRR1 y compara cada archivo de los
paquetes HRR A/B, incluidos sus manifiestos. Comprueba el inventario de build,
hashes, ELF ARM, ID recalculado desde `engine`/CMake, ID embebido y SDK fijado.
La guía empaquetada se deriva del [protocolo HM-T5](../compatibility/heather-room.md).

El ZIP usa rutas, orden, fecha y permisos fijos. El publicador relee todos
los archivos antes de publicar cada manifiesto, vuelve a validar las fuentes
y relee las dos entregas completas al terminar. No sobrescribe destinos.
La atomicidad es por copia: si B falla, A puede permanecer completa y no se
declara éxito de pareja. No se promete transacción entre directorios ni
durabilidad frente a pérdida de alimentación.

## Validación

- **7/7 CTest Release y 7/7 ASan/UBSan**: regresión de ruta, bucle/runtime,
  controles, SRI2 y oráculos de contactos/escena relacionados.
- **4/4 CTest GCC** y seis gates de cobertura de la composición aprobados.
  El lector modificado cubre 117/120 líneas (97.5 %) y 99/114 ramas (86.8 %).
  Los demás módulos mantienen sus gates ≥80/80 de HM-T4c.2.
- **155/155 pruebas Python**, incluidas 21 nuevas de entrega. Validan ZIP,
  inventario, hashes, fuentes alteradas, enlaces, código/ID/SDK discordantes,
  exclusividad, cambios durante publicación, relectura A tras B y fallo de B.
- Preparador de entrega: **96/97 líneas (99.0 %), 13/14 ramas (92.9 %)**.
  La entrada CLI real también se ejecutó al publicar, fuera de pytest.
- Formato/lint, revisión local de custodia/publicación, comprobador del repo
  y enlaces de documentación. No se ha ejecutado CI remoto.

La auditoría final del ZIP está registrada en
`reports/local/f06-01-heather-room-delivery.json`; verifica inventario, CRC,
SHA-256, permisos, manifiestos y bytes A/B, y compara los recursos con HRR.
Extrae cada ZIP en una carpeta temporal privada y ejecuta el lector/render/
HID/APT/contactos reales con dobles SDK, en Release y ASan/UBSan. Conserva
solo metadatos/hashes de salida y elimina sus temporales.

**12 replays privados aprobados**: 25/60/143 Hz × A/B × Release/sanitizadores,
100 pasos por replay. Repetición con `python -O`: otros 12 replays y un
informe idéntico. ZIP, archivos sueltos y manifiestos A/B coinciden byte por
byte. Los datos extraídos permanecieron intactos después de las pruebas.

El protocolo incluye replay de 100 pasos (25 espera, 25 caminar, 25 carrera,
25 avanzar/girar), exploración libre, pausa/R/L, entrada retenida, HOME/tapa
y combinación, START y error de carga reversible. El guion de controles
no afirma recorrer exactamente los cinco tramos geométricos del perfil HR.

Los logs de compilación/pruebas, JUnit, cobertura, auditor, comando restringido
y metadatos de entrega están en `build/heather-room/delivery-v1/`. La evidencia
fallida de la prueba de ruta se conserva en `path-red.log`; el ajuste inicial
del formato de manifiesto queda descrito en este informe. Los resultados son los
finales aprobados. Los archivos originales y entregas anteriores no se tocaron.

## Reproducción y aceptación

```sh
rtk proxy bash scripts/build_heather_room.sh /ruta/nueva/build-arm
rtk proxy .venv/bin/python -m tools.pipeline.prepare_heather_room_delivery \
  --scene-a /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-a \
  --scene-b /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-b \
  --runtime-a /Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-a \
  --runtime-b /Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-b \
  --build "$PWD/build/heather-room/delivery-v1/arm" \
  --private-root /Users/germancontreras/sh3-private-data \
  --run-prefix heather-room-3ds-v1
```

La compilación exige el contenedor fijado. La publicación rechaza repetir un
prefijo ya existente. El auditor local se reproduce con
`rtk proxy .venv/bin/python build/heather-room/delivery-v1/audit.py`; añadir
`-O` verifica que sus decisiones no dependen de `assert`. Usa temporales dentro
de la raíz privada y no toca una tarjeta.

**Durante el empaquetado no se instaló en SD ni se ejecutó en consola o
emulador.** La instalación posterior se registra abajo; HM-T5 requiere
identificar el ID y registrar resultados físicos.
El build muestra el presupuesto, pero aún no expone métricas de FPS, CPU/GPU
o pico de heap: esas medidas permanecen pendientes de instrumentación y no
se deducen del contador Step. HM-T4c.3 conserva los 29 materiales originales
pendientes; la cámara y respuesta física general PS2 siguen fuera de alcance.

## 2026-10-29 — Instalación verificada en SD

Por solicitud del usuario, se instalaron los **20 archivos completos** del
build **`ad84b65cd58d`**, **19899251 bytes**, en
`NO NAME/3ds/sh3_heather_room/`. Se identificó la tarjeta por UUID
`2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`, FAT32, extraíble y externa,
dispositivo de esta sesión `disk12s1`.

Antes de escribir se verificaron las dos entregas privadas contra los pins
del manifiesto, ZIP y `.3dsx`, el contenido del ZIP y sus SHA-256. La copia se
preparó en una carpeta temporal de la misma tarjeta, se releyó íntegra y se
publicó en su ruta final. Después de sincronizar se comprobaron de nuevo
inventario, tamaños y SHA-256 de todos los archivos instalados.

No existía una entrega anterior de la habitación, por lo que no se reemplazó
ninguna. Los 34 archivos del visor `sh3_heather_probe`, incluidos sus auxiliares
macOS, coincidieron antes y después. La carpeta temporal vacía se retiró.
`diskutil` confirmó **`Disk disk12 ejected`** y se comprobó que la tarjeta ya
no estaba montada. Puede retirarse e insertarse en la consola.

Recibo: `reports/local/heather-room-sd-delivery-ad84b65cd58d.json`.
Instalador y comprobación previa:
`build/heather-room/sd-delivery-ad84b65cd58d/install_sd.py`.
**HM-T5 sigue pendiente:** abrir *SH3 Heather room*, confirmar el ID, soltar
los botones y seguir el [protocolo físico](../compatibility/heather-room.md).
La instalación y relectura no acreditan ejecución física ni rendimiento.

## HM-T5 — Fallo físico comunicado

El usuario probó `ad84b65cd58d`: carga de aproximadamente 20 s, Heather de
espalda y sin avance percibido. A alterna RUNNING/PAUSED; R no produce un
cambio percibido. Con todos los botones sueltos desaparece el aviso de
liberación y se mantiene `Error: none`. **HM-T5 no aceptada**. Esto confirma
entrada y HUD activos, pero no permite identificar por sí solo el origen
del fallo ni demostrar que Step permanezca fijo. Se conserva la entrega
original y el recibo de SD. Registro:
`reports/local/heather-room-physical-ad84b65cd58d.json`.

En un perfil separado de Azahar 2126.2, el mismo binario avanzó de Step 1863
a 1864 con R en pausa, caminó con Arriba de la cruceta y salió con START.
Esta diferencia no invalida el resultado físico. La corrección y su
validación se documentan en [el seguimiento](f06-01-heather-room-fault.md).

## Reentrega corregida — 2026-10-30

Build **`217e1ace6571`** instalado en `/3ds/sh3_heather_room/` de la misma SD.
Se releyeron y comprobaron los SHA-256 de los 20 archivos; el build anterior
se conservó fuera de `/3ds/` y el visor previo permaneció intacto. La tarjeta
se expulsó de forma segura. Recibo:
`reports/local/heather-room-sd-delivery-217e1ace6571.json`.
La [prueba física HM-T5](../compatibility/heather-room.md) continúa pendiente.
