# SA-T5d — Localización de la activación de 0x0209

**Actualización posterior:** la [captura en la sala activa](f03-02-animation-continuity.md)
confirma las tres instancias, la selección inicial y una vuelta continua.
Las transiciones de daño y muerte siguen pendientes. Este documento conserva
la investigación estática que permitió llegar a esa captura.

2026-10-20. **Localización estática completada; continuidad e IA en ejecución
pendientes.** La ruta encontrada en la edición europea pertenece al carrusel:
overlay `amusement_02`, selector de escenario `0x23`, sala `0xEB` (235),
correspondencia de mapa `tp1d.map`. Hay tres instancias de tipo `0x0209`,
con IDs `0x018E`, `0x018F` y `0x0190`.

El usuario eligió continuar con este recurso. No se sustituye por un enemigo
de la primera zona. El nuevo arranque llega a una escena jugable, pero la
instancia `0x0209` de preparación ya ha sido eliminada. La residencia de los
archivos en RAM no demuestra la presencia de un actor activo.

Este informe amplía [SA-T5a/b/c](f03-02-skeleton-runtime.md) y aplica
[SC01–SC06](../../schemas/ps2-animation-continuity-v1.md). No cierra SA-T5d,
GC-T4, skinning ni integración del esqueleto en 3DS.

**Actualización posterior:** se encontró, importó y cargó una
[partida europea en Fortuneteller](f03-02-carousel-save.md), Normal/Normal,
para recorrer el tramo anterior al carrusel. La llegada a Happy Carousel
está comprobada en la sala `0xEA`, con once actores `0x020C` y ninguno
`0x0209`. Esa sala contiene el acertijo previo; falta observar el paso a
`0xEB` y la captura continua de las instancias objetivo.

## Arranque sin restauraciones

Se creó un perfil privado exclusivo con copias de BIOS y tarjetas del perfil
existente. Ejecutable PCSX2 candidato SRC51, SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`;
ISO europea ya fijada en SA-T4. El recibo registra `-fastboot`, sin
`-statefile`, proceso 2339 e inicio `2026-10-20T17:14:06Z`.

Se continuó desde la pausa del depurador al iniciar el ELF; después se eligió
Nueva partida, textos en español, acción Normal y acertijos Normal. Se usaron
inputs normales de teclado para los menús y omitir la introducción. PINE solo
consultó estado/lecturas y guardó dos slots nuevos; no se cargaron estados ni
se escribieron campos de memoria del huésped. Los breakpoints no sustituyeron
instrucciones del juego.

| Captura privada | Ciclos EE | Escenario / sala | Actor en `0x004484F0` |
|---|---:|---|---|
| 01, retorno `0x001DD444` | 39.906.186.363 | `0x22` / `0xE3` | Tipo `0x0209`, ID 0; preparación |
| 02, pausa en zona jugable | 75.807.097.843 | `0x21` / `0xD2` | Tipo `0x0804`; otra instancia |

La auditoría recorre la lista enlazada desde `0x0044E5D4`, valida enlaces
anteriores, límites/alineación de slots y ausencia de ciclos. La segunda
captura no contiene ningún actor `0x0209`. Compara también toda la sección de
código de cada overlay: captura 01 = `amusement_01`; captura 02 =
`amusement_00`. No se trata de deducir el overlay solo a partir del selector.

En ambas capturas los bytes completos del MDL en `0x0081A000` y del ANM en
`0x008E6000` conservan sus hashes de SA-T4. Sin embargo, el segundo actor
apunta a otro modelo y tiene ANM nulo. **La dirección del slot fue reutilizada.**
La selección inicial y las matemáticas de SA-T5a/b/c siguen siendo evidencia
válida del consumidor; no eran evidencia de IA durante juego activo.

La sesión se cerró normalmente tras preservar ambas capturas, código de
salida 0. El recibo de cierre verifica BIOS/tarjetas de origen sin cambios y
socket retirado. Los recibos y el registro de acciones documentan este ensayo;
no constituyen una auditoría universal de todas las mutaciones posibles de la VM.

## Cadena estática de activación europea

ELF `SLES_514.34`, SHA-256
`cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`.
El contenedor `B0.MFA` tiene 509.952 bytes y SHA-256
`aa1a9e1b934112c17050f5198ae900255721fec9cdd2727847e0c5459edf960d`.
Todas las direcciones siguientes son europeas.

| Recurso de B0 | Offset / tamaño | SHA-256 |
|---|---|---|
| `overlay/amusement_00.bin` | 2.048 / 22.400 | `fb145d4f10c7d9ebade143f05ee42181a191a8b8287906919365c72e5256fccf` |
| `overlay/amusement_01.bin` | 24.576 / 30.336 | `3822e3b9291ff108dcbfa500527141ce085896caa17bdf281f47045b9a3a02f3` |
| `overlay/amusement_02.bin` | 55.296 / 36.992 | `414142dad62fefc1cbd0d6684c05ba5d3331dd445949a11e5301470250683bde` |

1. La tabla de escenarios en `0x003D07E0`, índice `0x23`, devuelve
   `0x01EE99E0`. Su campo +`0x10` apunta a la lista de personajes
   `0x01EE3A00`; +`0x1C` a inicialización `0x01EE1600`; +`0x20` a actualización
   `0x01EE1930`.
2. `0x00170B20` obtiene la sala de `0x01CB5770`. La inicialización resta
   `0xE8` y despacha mediante `0x01EE9E80`. Para `0xEB`, el destino es
   `0x01EE16C0`: en `0x01EE16C8` llama al setter `0x01EE2D80` con `a0=1`
   en el delay slot. Este escribe `0x01EEE3F8`.
3. La tabla de actualización `0x01EE9EC0` despacha la misma sala a
   `0x01EE2774`. Recorre doce posiciones de una tabla distinta,
   `0x01EE9D30`, stride 16; solo tres tienen ID no nulo: 398, 399 y 400.
   Busca tipo `0x0209` + ID mediante `0x0012FDF0`, aplica posiciones/rotaciones
   del escenario y habilita los actores. Esa función es una **búsqueda**, no
   la creación de instancias.
4. La creación genérica recorre registros de **24 bytes** desde el campo
   +`0x10` del escenario. En `0x001696B4` llama `0x0016A260`; esta crea el
   actor mediante `0x0012F350` y enlaza recursos con `0x0012F5D0`.
   Antes se comprueban sala, disponibilidad y condiciones del registro.
5. La lógica `0x002E0B10` consulta el getter `0x01EE2D90`, que lee la bandera
   `0x01EEE3F8`. La selección de clips usa `0x002E1230`, separada del
   inicializador de preparación `0x002E0A00`.

La tabla de grupos `0x003D3620` asigna `0x23` al grupo 17; el prefijo de
`0x003D36F0` es `tp` y el código de sala en `0x003D3480 + 0xEB` es `0x1D`.
El catálogo F02 contiene `tp1d.map`, 2.517.040 bytes, SHA-256
`0bee15e6bb43501bcc5f9a10871c3f7c7617f8c1e5a5fa3d17dc3a6da00d0d62`.
Esta correspondencia de tablas aún debe contrastarse con la carga real del MAP.

| Registro | ID de instancia | Etiqueta de IA | Condiciones del registro |
|---|---|---|---|
| `0x01EE3AA8` | `0x018E` | `0x13` | `0xF800` |
| `0x01EE3AC0` | `0x018F` | `0x14` | `0xF800` |
| `0x01EE3AD8` | `0x0190` | `0x15` | `0xF800` |

Los tres registros comparten posición inicial `(22800, -28, -100204)`;
la actualización después aplica las transformaciones del escenario. El filtro
`0x0016B6C0` exige que la sala calculada desde la posición coincida con la actual,
que no esté marcado el bit persistente del ID en la tabla `0x01CA50B0` y que
la máscara de dificultad permita su creación. `0xF800` incluye la máscara
Normal `0x2000`; su condición inferior de 11 bits es cero. La admisión activa
también examina el bloqueo global de enemigos, bit 20 de `0x01CA4FEC`.
Estas condiciones se identificaron estáticamente; no se midieron en el carrusel.

Existe otra declaración `0x0209` en `amusement_01`: registro `0x01EE6378`,
ID `0x0179`, posición `(-60000, 0, 60000)`, flags `0xF860`.
La condición inferior `0x60` es rechazada por la ruta de admisión activa
`0x0016ADB0` → `0x0016B188` (retorno cero); el filtro previo de recursos
puede admitirla con otra condición. No se confunde esta declaración con los
tres actores activos del escenario `0x23`, ni con el ID 0 observado en carga.

## Selección de clips: puntos de observación preparados

| Ruta estática | Llamada a `0x002E1230` | Clip | Retorno esperado (`ra`) |
|---|---|---|---|
| Estado en `0x002E0F10` | `0x002E0F44` | `0x1449` | `0x002E0F4C` |
| Estado en `0x002E0FA0` | `0x002E0FE0` | `0x144A` | `0x002E0FE8` |
| Estado en `0x002E1080` | `0x002E10C0` | `0x144B` | `0x002E10C8` |

Las tres rutas solicitan un offset de velocidad `-512` mediante `0x001DDCE0`.
La captura posterior corrigió el cálculo preliminar: la ruta PAL convierte
ese argumento a `-614`; la velocidad efectiva observada es `2457 - 614 = 1843`,
con incremento 3686 para dos ticks. Véase el informe de continuidad enlazado
arriba. No se infieren FPS de esos valores.

La lógica consulta daño/vida y el fin del clip; usa además las etiquetas
`0x13/0x14/0x15` para retirar bits 1/2/4 de la máscara `0x01EEE3D0` cuando la
vida llega a cero. La inicialización de `0xEB` establece esa máscara en 7.
Esto identifica receptores y selección de clips en código, pero **no demuestra
que se puedan provocar por juego normal**. La [investigación posterior de colisión
y rutas alternativas](f03-02-carousel-alternative-routes.md) corrige la inferencia
inicial de accesibilidad: no encontró una acción admisible para esas transiciones.

## Siguiente captura y límite actual

El lugar jugable corresponde al carrusel del regreso avanzado a Lakeside
Amusement Park. Como orientación para llegar allí se consultó la
[guía de la zona](https://www.silenthillmemories.net/sh3/walkthrough_13_lakeside_amusement_park_en.htm);
no se usa esa guía para deducir direcciones, cantidades de actores o formatos.
La presencia de tres registros en esta ruta no implica que todos los caballos
visibles del carrusel sean instancias de este mismo recurso.

La investigación inicial requería progreso normal hasta esa zona o una
partida europea guardada dentro del juego. La [búsqueda posterior](f03-02-carousel-save.md)
ya proporciona esa partida y comprueba su carga normal desde tarjeta como
preparación de un nuevo ensayo. El recorrido y la secuencia medida deben
permanecer sin restauraciones de estados ni reinicios.

1. Arrancar el perfil privado y llegar por juego normal a la zona objetivo.
   Registrar por separado cualquier carga inicial de tarjeta.
2. Comprobar el hash del overlay y la sala antes de admitir un breakpoint
   en `0x01EE16C8`; esa dirección puede contener otra cosa en otro overlay.
   Confirmar después la bandera y capturar la creación/enlace de cada instancia.
3. Capturar `0x002E1230`: `a0` es la estructura de IA, `a0+4` contiene el
   actor, `a1` es el clip y `ra` identifica la ruta. Resolver el actor nuevo,
   sin reutilizar la dirección `0x004484F0` como identidad fija.
4. Capturar entradas/retornos del consumidor `0x0013F3E0` /
   `0x001DD444`, sin omitir evaluaciones del actor elegido, hasta completar
   una vuelta. Verificar reloj y pose con el oráculo existente.
5. Solo tras demostrar una ruta admisible en SC-T3b.2, aplicar una acción normal
   de combate y seguir selección → descriptor → nuevas evaluaciones. La revisión
   posterior no la ha encontrado; conservarla pendiente sin repetir golpes
   sobre la configuración descartada.

## Evidencia y reproducción

Raíz privada: `/Users/germancontreras/sh3-private-data/f03-02-skeleton-continuity-v1/`.
Se preservan perfil, recibos, log del emulador y dos estados:

- Captura 01: SHA-256 `4aaf2443c5e9b7602af903d5e80f2be58697183083ed2ff1b37992433054db42`.
- Captura 02: SHA-256 `7af73900e6c6261a4e2654e708d56fdec5f79f2f0621e8eef72279032bb8aff4`.

Herramientas locales ignoradas en `build/f03-02-skeleton-continuity/`:
`launch.py`, `capture.py`, `read_status.py`, `overlay.py`,
`audit_activation.py`. El auditor lee ISO/estados sin ejecutar código de
referencia; comprueba hashes, listas, reutilización, tablas de despacho y
ventanas del ELF/overlay. Su salida contiene metadatos, no RAM o recursos.

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/audit_activation.py
```

Salida: `reports/local/f03-02-animation-activation-v1.json`.
8.304 bytes, SHA-256
`94a2d9abbac7c50679050e792f0c97477800796e5fe8503973f9aee3ddc794c3`.
El resultado esperado es `static_activation_located_runtime_target_absent`;
`continuity_verified=false`, `ai_transition_observed=false`. Las direcciones,
hashes de ventanas, actores y recibo de cierre permiten repetir la auditoría
local. El reconciliador completo de secuencias SC-T4 sigue pendiente.

Verificación de esta entrega:

- 108 pruebas existentes del decodificador y oráculo de pose aprobadas
  (`test_skeleton_animation.py`, `test_animation_pose_oracle.py`).
- `tools.qa.check_repository`: PASS, cero errores.
- `git diff --check`: sin errores.
- Auditoría de las dos capturas y del overlay europeo: aprobada.

No se modificó código de producción ni se generó un build 3DS en esta etapa
de investigación. Estas pruebas host no acreditan continuidad de IA.

Referencia auxiliar de nombres: `amusement_02.c` de
[memory-of-alessa, revisión fijada](https://github.com/dreamingmoths/memory-of-alessa/blob/247c7f43fd619aff8d2086ea0b0af291c283ea9d/silent-hill-3/src/Event/stage/amusement_02.c),
SHA-256 `59ed67ae6f200fc9d3dc68a30498cb3bf05f0c67ba967fde4edccd93e569ab51`.
Corresponde a otra región; las conclusiones técnicas de este informe proceden
del ELF y los overlays europeos verificados.
