# F03.02 — Banco externo y selección de material observados

2026-10-20. **MR-T4b y MR-T4c completadas** en una reproducción controlada de
PCSX2. El cargador del juego recibió el MAP objetivo y su textura externa,
verificados por tamaño y SHA-256 de todos los bytes. Las dos formas seleccionadas
usan el gestor de ese banco, CLUT 0 y el mismo TEX0.

**Seguimiento: [MR-T4d completada](f03-02-map-draw-state.md)** para estas dos
formas. La verificación posterior contrasta las transformaciones VU0/XYZ/STQ,
el consumo GS de sus 32 triángulos por cuadro y 16.380 píxeles interiores
en una reproducción software del volcado original. Este informe conserva
el alcance de MR-T4b/c: asociación y estados preparados. La integración
del material y su comprobación funcional en New 2DS XL se completaron después
en [MI-T1–MI-T4](f03-02-material-inspection.md).

## Alcance de la prueba

Se reutilizó el ejecutable SRC51, SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`,
sin recompilar. Dos perfiles privados nuevos restauraron una copia del estado
del [control inicial](f03-02-map-runtime-bank.md). Cada perfil tiene copias de
BIOS/tarjetas, slots nuevos, PINE local, MTVU desactivado y arranque pausado.

Se modificaron campos de solicitud en la RAM de esas copias, mediante PINE,
con PID del peer, pausa y valores previos comprobados. Las escrituras y su
lectura posterior quedaron registradas. **No se modificó código, no se inyectaron
recursos y no se alteraron la ISO ni las tarjetas originales.** La recepción
de recursos y la selección de material las ejecutó el juego.

Esta prueba demuestra ese recorrido de carga/dibujo bajo una solicitud
controlada. No acredita una partida normal de hospital, su lógica de progreso,
una captura ininterrumpida ni la admisión del observador.

## Precondición encontrada y solicitudes

El ELF europeo contiene una ruta alternativa en `0027F040`: al activar
`01ED1F64`, toma el grupo de `01ED1F74` y la posición de `01ED1F78/7C/80`.
Con los controles de seguimiento y modo a cero, el grupo 14 y la posición
`(100000, 0, 140000)` seleccionan la celda `34`. La tabla en `003D36F0` y
`00280430` construyen `data/bg/hp/hp34.map` y `data/bg/hp/hp34TR.tex`.
La entrada de sufijo `TR.tex` usa el tipo 4; la tabla `00408E98` lo enlaza
con el callback `0027B770`. Estas direcciones se comprobaron contra esta
edición europea, sin trasladar direcciones de otra región.

**Control sin montaje, perfil v2:** cuatro escrituras de 32 bits activaron
grupo/posición/solicitud. Se alcanzó `0027F1B0` con `a0=14` y la posición
esperada en la pila, pero la entrada de caché `000E0034` no encontró recursos.
El juego descargó el MAP anterior y el banco siguió vacío. Este intento
identificó la necesidad de montar los archivos del hospital.

**Carga con montaje, perfil v3:** se restauró de nuevo el estado inicial y se
pausó GameMain en `00194870`. Se cambió el selector de zona de 34 a 27,
se solicitó su estado de carga 2 y se limpiaron los subestados conforme al
setter europeo `0012D020`; se mantuvo la solicitud alternativa de celda.
El registro contiene nueve escrituras efectivas: un byte y ocho palabras.
Los contadores que ya estaban a cero se comprobaron sin reescribirlos.

Se alcanzó `0012C780` con `a0=003D36B8`, que apunta a `hp`. Su tabla de
montaje enumera los archivos `hp1F`, `hp2F`, `hp3F`, `hpBF` y `hpGB`.
Después, los cargadores normales entregaron la textura y el MAP objetivo.

## Recepción, registro y contexto

| Punto capturado | Resultado |
|---|---|
| `0027B770`, slot 05 | `a2=018BF200`, `a3=69808`; textura completa coincide |
| Banco registrado, slots 06–12 | Área `018BF200`, contador 1 |
| Entrada de ordinal 0 | Bloque `018BF220`, gestor `01DCCA30` |
| `0027B320`, slot 06 | `a2=018D2200`, `a3=2134960`; MAP completo coincide |
| Contexto `01D0B3A0`, slots 07–12 | MAP `018D2200`, lista externa `01D1DAB0` |
| Otros tres contextos | MAP nulo |

MAP:
`asset:464325b2533b0e0a0702d4ad52f7050d41e9a02ba308dea7bce2a3268e83d4ae`,
SHA-256 `fe6661eeb4d7df7e3baf6cd015452e1c9d3548416a862e503e1f2370a1f289c9`.

Textura:
`asset:0af58e26e1e91e71293f018ef07da3daed14ad44fd94d4ecea6b7d4eb4d72c3b`,
SHA-256 `65173379ae86c13512b0c546edf68ae3a82b79b7267f5b011a39d8d44ccf35e4`.

Ambos recursos conservan esos hashes completos en las capturas posteriores.
La identificación no depende de similitud visual, nombre o cabecera.

## Selección de las dos formas

| Forma, offset MAP | Descriptor generado | Payload referenciado, offset MAP | Bit de visibilidad |
|---|---|---|---|
| 448 | `01D1DAB0` | 512 = forma +64 | 56 |
| 928 | `01D1DB10` | 992 = forma +64 | 63 |

En slots 07/09, el global `01DC7C10` apunta respectivamente a esos descriptores.
Sus primeros 16 bytes coinciden con los copiados al scratchpad `70002000`,
señalado por `003D57B0`. La referencia al payload de cada forma se verificó
contra el MAP identificado, sin inferirla solo del orden de las llamadas.

En ambas pausas `001B1350` recibe `a0=01DCCA30`, `a1=0`, `a2=1`: gestor
del banco, CLUT 0 y modo 1. Tras ejecutar `001B5F20`, slots 08/10 alcanzan
`001B1358` con `v0=01DCCAB0`, exactamente gestor +`80`.
El retorno de la preparación se siguió hasta `001B2084` y `001B2440`;
en este último, los registros conservan gestor, lista y contexto +`780`,
coherentes con el recorrido de `001B23B0`.

El par leído en el puntero devuelto es TEX0 `2006E00621312C00` y registro GS
`06`. La disposición de bits se contrastó con
[GSRegs.h de PCSX2, revisión fijada](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSRegs.h),
también disponible en las fuentes locales usadas por el proyecto.

| Campo TEX0 | Valor |
|---|---|
| TBP0 / TBW | 11264 / 4 |
| PSM | 19, PSMT8 |
| TW / TH | 8 / 8: 256×256 |
| TCC / TFX | 1 / 0 |
| CBP / CPSM | 14080 / 0 |
| CSM / CSA / CLD | 0 / 0 / 1 |

El slot 11 contiene el mismo TEX0 en el paquete preparado del scratchpad,
junto a ALPHA `0000008000000044` y TEST `0000000000053000`.
**Un paquete preparado no prueba por sí solo el estado final del GS ni la
fidelidad del resultado.** No se traduce aún ese ALPHA a una regla de mezcla
del renderer 3DS, ni el puntero de contexto +`768` a una matriz directamente.

## Evidencia y reproducción

Capturas y registros privados:

- `/Users/germancontreras/sh3-private-data/f03-02-map-runtime-v2/`: cuatro pausas
  del control sin montaje; la cuarta se tomó mediante pausa manual.
- `/Users/germancontreras/sh3-private-data/f03-02-map-runtime-v3/`: doce pausas
  de solicitud, montaje, callbacks, selección y retorno de dibujo.

Ambos procesos cerraron normalmente con código 0. Los sockets desaparecieron
y las BIOS/tarjetas originales conservaron sus hashes. Los archivos de juego,
RAM y scratchpad permanecen privados.

Informe local: `reports/local/f03-02-map-runtime-binding-v1.json`,
15.720 bytes, SHA-256
`e7ca63fee6277bac68fa6cbe00d616eb3c1ae9c685a7b0e6d318fdb61d7b5344`.
Registra las modificaciones, hashes de cada captura y auxiliar, y trece
ventanas del ELF verificadas en las dieciséis capturas. Distingue acceso,
asociación comprobada y consumo final pendiente.

```sh
rtk proxy .venv/bin/python build/f03-02-map-runtime/audit_binding.py
```

La auditoría usa el lector acotado existente con CRC, comprueba PC y ciclos,
hashes completos, callbacks, registro, descriptores, argumentos y retornos.
Exige igualdad exacta al repetir el informe. Los auxiliares son operativos
locales ignorados por Git; no amplían la API ni los contratos de admisión.

Validación: **184 pruebas existentes aprobadas** de savestates, transporte
PINE y metadatos de render; **35 comprobaciones de repositorio** aprobadas.
JUnit en `build/f03-02-map-runtime/binding-tests.xml` y
`binding-repository-tests.xml`. Auditoría repetida idéntica y
`git diff --check` sin errores.

Los slots 07–12 de v3 sirvieron de punto de partida para la
[verificación posterior MR-T4d](f03-02-map-draw-state.md), completada con
capturas VU0, un volcado GS y contraste de píxeles. La
[integración de material y transformación](f03-02-material-inspection.md)
se validó después funcionalmente en consola mediante confirmación del usuario.
