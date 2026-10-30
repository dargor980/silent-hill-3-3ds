# HRR v1 — Bucle compartido y descriptor de carga

2026-10-29. HM-T4c.2 extiende [HRS v1](heather-room-scene-v1.md) con un
descriptor acotado, carga transaccional y composición Citro3D/HID/APT.
Conserva las 31 formas de hp34, SRI2 original, 32 cajas y suelo del perfil;
29 formas usan material neutro identificado y la cámara fija es propia.

## Preparación y custodia

El [preparador](../tools/pipeline/prepare_heather_room_runtime.py) recibe dos
paquetes HRS. `read_bundle` verifica inventario, manifiestos, SHA-256 de las
fuentes fijadas y reconstrucción de sus datos. Exige igualdad A/B. Cada copia
HRR contiene los **26 archivos HRS sin cambiar** y añade:

- `scene.srr`: descriptor SRR1 de 596 bytes para el lector C++.
- `source-scene-manifest.json`: manifiesto HRS canónico que conserva procedencia.

Son 28 archivos de datos, más `manifest.json` y su enlace pendiente. Publicación
exclusiva fuera del repositorio, directorios 0700 y archivos 0600. El escritor
relee los archivos y el callback vuelve a verificar ambas fuentes antes de
publicar cada manifiesto. La atomicidad es por copia; una copia completa puede
permanecer si falla la otra. No hay transacción entre directorios ni garantía
de durabilidad ante pérdida de energía. El auditor final relee A/B completas.
Este paquete de datos aún no es la entrega SD de HM-T4d ni contiene ejecutable.

## SRR1

Little endian. Enteros u32 y floats IEEE-754 binary32. Tamaño exacto 596 bytes,
sin relleno ni bytes posteriores. El CRC es CRC32/IEEE con semántica zlib.

| Offset | Tipo | Contenido |
| --- | --- | --- |
| 0 | 8 bytes | `S3RRv1\0\0` |
| 8 | u32 | Longitud del payload: 564 |
| 12 | u32 | CRC32 de los bytes 32–595 |
| 16 | u32 | CRC32 del archivo completo `map.srm` |
| 20 | u32 | CRC32 del archivo completo `heather.sri` |
| 24 | u32 | CRC32 de `glass.rgba` |
| 28 | u32 | Versión 1 |
| 32 | u32 | Número de cajas: 32 |
| 36 | 3 × f32 | Origen compartido XYZ |
| 48 | f32 | Altura del suelo |
| 52 | 4 × f32 | Suelo `(xmin,xmax,zmin,zmax)` |
| 68 | 3 × f32 | Spawn mundial XYZ del perfil HR |
| 80 | f32 | Yaw inicial del perfil HR |
| 84 | 32 × 4 × f32 | Cajas, mismo orden y campos que el suelo |

Los bits de suelo y cajas se copian de los tokens `f32:` de contactos;
no se vuelve a proyectar CLD ni a expandir el radio. El puerto HRC realiza
la expansión exacta al preparar las consultas. Origen=(100000,0,140000),
suelo Y=0. Spawn y yaw deben admitir contacto nulo y matriz rígida válidos.

## Carga y propiedad

[`read_room_runtime`](../engine/platform/common/room_runtime.cpp) carga un
`RoomAssets` candidato en heap: mapa, rig, contactos y spawn. Valida SRR1,
contactos/spawn, SRM1 con 31 formas, SRI2 con 13 materiales, texturas originales,
CRC de mapa/SRI/vidrio y presupuesto. Solo entonces intercambia el puntero de
salida. Fallos de formato, lectura, cierre, CRC o asignación conservan el
objeto anterior; los temporales y descriptores se liberan.

CRC detecta corrupción; **no autentica procedencia**. La identidad SHA-256
se exige al preparar los paquetes privados. Los lectores existentes mantienen
sus límites y validaciones. Las comprobaciones adicionales de archivos usan
bloques de 4096 bytes y límite de 2 MiB por archivo; raíz ≤450 caracteres.
El renderer vuelve a validar CRC antes de subir cada textura. Los JSON y
recursos crudos se conservan para auditoría; la consola no los interpreta.

## Bucle y comandos

[`RoomLoop`](../engine/application/room_loop.cpp) implementa `IMovementSession`
y conecta `MovementController`, `IMovementContacts` e `IRoomView`.
[`run_room`](../engine/platform/3ds/render/room_main.cpp) compone los adaptadores
reales. La entrada espera en `sdmc:/3ds/sh3_heather_room/`.

- Paso fijo de **40000 µs**, dos ticks PAL, hasta tres pasos por muestra;
  intervalos >120000 µs se descartan. Acumulación/fracción ARM11 de HMN se
  conserva; pausa, suspensión, reinicio y liberación borran tiempo pendiente.
- D-pad: avanzar/girar; B: correr. A: pausa; R: un paso estando pausado;
  L: reinicio/reintento; START: salida. Conserva prioridad de HMN y el puente
  explícito idle→walk→run. Al entrar o cambiar de estado hay que soltar botones.
- Cada actualización publica conjuntamente contacto, posición, yaw, matriz,
  reloj y pose. Un bloqueo mantiene posición y permite avanzar animación.
  Y permanece en el suelo del perfil. Render recibe esa instantánea completa.
- El spawn se consulta antes de publicar la primera escena y en cada L.
  Un fallo no reemplaza la última instantánea. Reiniciar normalmente conserva
  running/paused; tras un error conserva paused, y A reanuda después de soltar.
- HOME y tapa son **dos motivos de suspensión independientes**. RESTORE limpia
  HOME, WAKEUP limpia tapa; solo se reanuda cuando no queda ninguno. Duplicados
  son inertes. Se conserva la pausa previa; no se dibuja ni simula suspendido.
  ONEXIT/START detienen definitivamente y los hooks se desregistran por RAII.

## Errores y GPU

Fallos de spawn, contacto/animación o render quedan latentes: pausa, descarte
de tiempo y liberación de entrada. A/R no eluden el error. L revalida spawn,
reinicia el actor y permite un nuevo dibujo. Un fallo de simulación conserva
el último paso completo, incluidos los subpasos anteriores válidos del mismo
frame; no se promete revertir todo el frame. Sigue mostrándose esa pose.
Un fallo gráfico suprime reintentos automáticos hasta L. `busy` es transitorio:
no pausa ni revierte simulación y el siguiente frame puede volver a presentar.

[`RoomRenderer`](../engine/platform/3ds/render/room_renderer.cpp) reserva CPU,
VBO estático/dinámico y 14 texturas al inicializar. Usa la base, cámara, orden
global vidrio/cabello y estados HRS. Solo modifica el VBO dinámico después de
`C3D_FrameBegin(SYNCDRAW)` exitoso; cada salida posterior termina el frame.
En destrucción sincroniza mediante la eliminación del target antes de liberar
texturas, VBO, programa y shader; termina Citro3D al final.

Un fallo inicial de carga/GPU/asignación destruye recursos parciales y ofrece
L para cargar de nuevo, o START para salir. No solapa propietarios GPU.
No hay reserva de heap en el paso/render del código propio; el SDK se valida
con dobles en host y requiere comprobación física adicional.

## Memoria y alcance

El presupuesto HRS de 40190596 bytes aumenta en **2097152 bytes** para el
`RoomAssets` anterior durante reemplazo y margen de carga/pila. Total:
**42287748 bytes (40.33 MiB de 64 MiB)**, incluidos 12 MiB de reserva de
plataforma. `static_assert` exige `sizeof(RoomAssets)+65536 ≤ 2 MiB` y
bucle/controles ≤32 KiB. ARM: RoomAssets=1395120, RoomLoop=27968,
MovementControls=40 y RoomRenderer=852 bytes. Los arrays grandes viven en heap.

Es un presupuesto conservador, no una medición del pico en hardware. La
compilación ARM no acredita FPS, tiempo CPU/GPU, HOME/tapa reales ni lectura
SD. [Evidencia, gates y reproducción](../docs/execution/f06-01-heather-room-runtime.md).
HM-T4d prepara la entrega y HM-T5 conserva la aceptación física.
