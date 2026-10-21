# SA-T5d — Partida europea para alcanzar el carrusel

2026-10-20. **Actualización:** se alcanzó `0xEB` y se verificaron la selección
inicial y una vuelta continua de `0x0209`. Tras morir, el usuario solicitó
restaurar el inicio del combate; esa reproducción se registra por separado.
Véanse [resultados y límite de continuidad](f03-02-animation-continuity.md).
Las secciones siguientes conservan el registro de preparación.

**Partida importada y cargada correctamente.** El slot 16
`Fortuneteller` permite preparar el tramo anterior al carrusel con acción
Normal y acertijos Normal. Todavía no se admite como evidencia de continuidad
del actor `0x0209`: faltan la llegada a la sala objetivo y las capturas del
consumidor y la IA.

Extiende la [localización de activación](f03-02-animation-activation.md) y
aplica [SC01–SC06](../../schemas/ps2-animation-continuity-v1.md). El usuario
solicitó buscar una partida europea y usarla para este ensayo.

## Fuente e identificación

Se seleccionó el adjunto **AR MAX Savefile for Silent Hill 3 (E).rar** del
[mensaje de Maori-Jigglypuff en el foro de PCSX2](https://forums.pcsx2.net/Thread-Post-your-PCSX2-cheats-patches-here?pid=571817#pid571817).
El autor identifica la edición `SLES-51434`, PAL, CRC `5088CCDB`, y anuncia
17 ubicaciones. [Adjunto de la partida](https://forums.pcsx2.net/attachment.php?aid=66685).
La importación confirma el directorio de tarjeta `BESLES-51434File`.

El mensaje también ofrece parches independientes. No se descargaron ni
aplicaron esos parches; el uso histórico de trucos por el autor del guardado
es **desconocido**. Esta procedencia permite estudiar la ejecución desde un
estado inicial identificado, pero no demostrar una progresión íntegra sin
trucos ni validar el balance de dificultad.

| Artefacto privado | SHA-256 |
|---|---|
| RAR descargado | `5f81e26c4f739cb8bde1e818a67a32cb440714facf1d4ce60b3c67d01361cee4` |
| `maori-eu.max`, 138.606 bytes | `d88f669ef200ef0d4a09a697d2b76e99806579a3a77b38c2867d58afbe73e7bf` |
| `maori-eu.ps2`, tarjeta importada | `bb0d8f5c9f510b7b10886105ebc51cc38d49a5fde13dbece508bb75f8630a283` |

Se leyó únicamente el miembro identificado del RAR; no se ejecutó contenido
del archivo. `mymcplusplus 3.2.0`, obtenido de PyPI, creó una tarjeta nueva e
importó el MAX. La [documentación oficial de tarjetas de PCSX2](https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/configuration/memcards.md)
referencia esa herramienta. Sus dependencias se instalaron solo en
`build/save-import-tools/`, ignorado por Git.

Antes se revisaron tres candidatos europeos de
[GameFAQs](https://gamefaqs.gamespot.com/ps2/561292-silent-hill-3/saves):
Nakian (`15828`: capilla/resultados) y BrooniE (`2711`, `2757`:
apartamento/resultados). Sus slots observados no ofrecían el punto previo
al carrusel buscado; no se usaron para medir animación. Los perfiles de esas
revisiones se cerraron normalmente con BIOS y tarjetas de origen intactas.

## Carga comprobada

En el menú del juego se observaron:

| Campo | Valor |
|---|---|
| Tarjeta | Slot físico 1, copia privada de la tarjeta importada |
| Partida | `16. Fortuneteller` |
| Tiempo | `2:13:15` |
| Acción / acertijos | Normal / Normal |
| Número de guardados | 22 |
| Fecha mostrada | `2018/06/06 01:46:25` |
| Texto observado | Inglés; no cambia el objetivo de alpha en español |

Se eligió **Load** dentro del juego y se verificó `Loading completed`.
Después apareció Heather junto al punto de guardado de la adivina; respondió
a los controles normales. No se restauró un estado de PCSX2. El slot 17
`Alessa's room`, posterior, no fue elegido.

La [guía de la zona](https://www.silenthillmemories.net/sh3/walkthrough_13_lakeside_amusement_park_en.htm)
sirve únicamente para orientar el recorrido por Marchen Travel y el camino
de la heladería. Las direcciones y comprobaciones del actor proceden del
análisis europeo, no de esa guía.

## Sesión y captura pendiente

El ensayo usa el perfil privado `f03-02-skeleton-continuity-v5`, proceso
registrado 26887, y el mismo ejecutable candidato SRC51 identificado en
SA-T5. Arranca la ISO normalmente, sin `-statefile`; conserva BIOS y tarjetas
de origen y sustituye solo la copia de la primera tarjeta en este perfil.
`EnablePatches`, `EnableCheats`, `EnableWideScreenPatches` y
`EnableNoInterlacingPatches` están desactivados.

Se prepararon estos puntos de interrupción:

| Dirección | Propósito | Filtro |
|---|---|---|
| `0x001DD444` | Retorno del consumidor de pose | Tipo `0x0209`, instancia `0x018E` desde `s0` |
| `0x002E1230` | Selector original de la IA | Sin filtro; resolver actor mediante `a0+4` |

El usuario tomó el control para recorrer el tramo hasta el carrusel después
de que la automatización no lograra superar el mobiliario de la habitación.
Se le indicó no reiniciar ni restaurar estados y dejar pausado cualquier
breakpoint. Las consultas de navegación mientras la VM corre se etiquetan
como **no coherentes** y no sirven para validar pose, identidad o continuidad.

El capturador comprueba PID y pausa, escribe un slot nuevo, decodifica CRC,
PC y ciclo EE, y vuelve a comprobar la pausa. El auditor resuelve la lista
de actores con límites y enlaces validados; deriva las direcciones actuales
de MDL, ANM y huesos, compara hashes completos y ventanas del código, y
prepara la comparación entre retornos mediante el oráculo independiente.
Una coincidencia aislada no certifica una vuelta ni ausencia de huecos:
también se requiere registrar cada reanudación/parada con el breakpoint
habilitado. La columna de ejecuciones muestra `--` para este tipo de
breakpoint; no se interpreta como un contador numérico.

### Comprobación de Swing Rocket

Tras el primer aviso de llegada, la imagen correspondía a la atracción de
sillas Swing Rocket. Se pausó mediante el depurador y se guardó el slot 01
sin restaurar estados:

| Campo | Captura 01 |
|---|---|
| SHA-256 | `6790c74b352d10f4551bf2c7507e87fffa2a5e2782c609a739f8285bfc3c9fbc` |
| PC / ciclos EE | `0x00081FC0` / 249.575.146.483 |
| Escenario / sala | `0x22` / `0xE3` |
| Overlay contrastado por código completo | `amusement_01` |
| Lista enlazada validada | 13 actores; ninguno de tipo `0x0209` |

Esta evidencia excluye esa sala como la zona objetivo de SA-T5d. La palabra
en `0x01EEE3F8` vale cero, pero no se interpreta como la bandera del carrusel
mientras esté cargado otro overlay. Se verificaron ambos breakpoints
habilitados y se reanudó la misma sesión. El usuario continúa hacia el
carrusel de caballos, pasando por Marchen Travel.

Auditoría de esta captura:
`reports/local/f03-02-carousel-observation-v1.json`, SHA-256
`d08960d4106c0a1702a9315c762bb3cb1af89b72e799a5848789a12aa4522c76`.
Su resultado mantiene `continuity_verified=false`. Al añadir capturas,
el auditor actualizará el informe; el hash anterior identifica este corte.

### Llegada a Happy Carousel: sala del acertijo

El siguiente aviso de llegada sí corresponde visualmente al carrusel de
caballos. Se conservó la pausa del propio juego, se pausó además el emulador
para capturar y se guardó el slot 02 en el mismo proceso:

| Campo | Captura 02 |
|---|---|
| SHA-256 | `3e2cd755bf2a5931ff7df57a858346b72edcc453a9e4a1877f245f46de211886` |
| PC / ciclos EE | `0x00081FC0` / 484.590.519.283 |
| Escenario / sala | `0x23` / `0xEA` |
| Overlay contrastado por código completo | `amusement_02` |
| Lista enlazada validada | 26 actores; ninguno de tipo `0x0209` |
| Actores del acertijo | 11 de tipo `0x020C`, IDs `0x03F4–0x03FF` salvo `0x03F8` |
| Bandera `0x01EEE3F8` | 0 |

Los once actores `0x020C` tienen función de actualización `0x00313BE0` y
punteros nulos en los campos MDL/ANM usados por el consumidor investigado
(+`0x308` y +`0x30C`). No se los admite como instancias del par
`en_mry.mdl` / `en_mry.anm` por su semejanza visual.

La tabla europea de inicialización distingue `0xEA` → `0x01EE1684` de
`0xEB` → `0x01EE16C0`; solo la segunda ruta establece la bandera objeto de
esta investigación. La captura corrige la orientación anterior, demasiado
amplia: **llegar al carrusel no equivale todavía a alcanzar la sala `0xEB`**.
La [guía del recorrido](https://www.silenthillmemories.net/sh3/walkthrough_13_lakeside_amusement_park_en.htm)
sitúa una transformación después del acertijo y antes del combate con
Alessa. Se pide al usuario continuar por juego normal hasta esa transición;
su correspondencia con `0xEB` aún debe observarse, no se deduce de la guía.

Se verificaron visualmente ambos breakpoints habilitados, se reanudó el
emulador y se cerró solo el depurador. La pausa del juego quedó a disposición
del usuario. No hubo restauraciones ni escrituras a memoria del huésped.
El usuario confirmó que continuará y avisará cuando se detenga.

Auditoría de los slots 01 y 02:
`reports/local/f03-02-carousel-observation-v1.json`, SHA-256
`5992f713388a56146f8af65192ca013c1add5bbcf7a5386d1032e37a8b6fe39d`.
Mantiene `continuity_verified=false`: estas dos pausas de navegación no son
retornos consecutivos del consumidor.

## Custodia, validación y continuación

- Fuente, MAX, tarjeta nueva y recibo:
  `/Users/germancontreras/sh3-private-data/f03-02-eu-save-search-v1/`.
- Sesión, perfil, log y futuros estados:
  `/Users/germancontreras/sh3-private-data/f03-02-skeleton-continuity-v5/`.
- Herramientas locales ignoradas:
  `build/f03-02-skeleton-continuity/launch_carousel.py`,
  `carousel_live.py`, `carousel_capture.py` y `audit_carousel.py`.
- Regresión del decoder y del oráculo: **108 pruebas aprobadas**.
  Esto valida las herramientas existentes, no la continuidad todavía pendiente.
- El nuevo extractor/auditor se contrastó con tres controles privados anteriores:
  reloj y pose coinciden. Rechaza además seis copias alteradas en memoria
  (ciclo en la lista de actores o puntero ANM fuera de límites), sin modificar
  los estados originales. Reproducción:
  `rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/check_carousel_audit.py`.
- Se añadió `tools/qa/animation_continuity.py`, independiente de PCSX2 y del
  filesystem, para reconciliar retornos consecutivos de un clip en loop.
  Rechaza huecos de ordinal, ciclos no crecientes, cambio de identidad, modo,
  contador, incremento o muestras incompatibles. Comprueba avance acumulado,
  no solo un wrap. **32 pruebas nuevas; 140 aprobadas** junto al decoder y
  el oráculo, cobertura de líneas y ramas del módulo nuevo del **100 %**.
  La procedencia de los ordinales y las poses se verifican por separado;
  todavía falta aplicarlo a una vuelta real.

Siguiente paso: pasar de la sala del acertijo `0xEA` a la sala objetivo
`0xEB` de `amusement_02`, identificar las
instancias `0x018E–0x0190`, registrar la selección natural del clip y capturar
una vuelta del mismo actor. SC-T1c, SC-T2, SC-T3 y SC-T4 permanecen abiertos
hasta obtener y reconciliar esa evidencia. No hay un nuevo build 3DS en
este paso de investigación.
