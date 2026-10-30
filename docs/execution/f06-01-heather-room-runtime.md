# HM-T4c.2 — Bucle compartido, ciclo de vida y recuperación

2026-10-29. **HM-T4c.2 completada.** El ejecutable `sh3_heather_room` conecta
render de hp34/Heather, controles, tiempo fijo y contactos del perfil. Se
verificaron pausa, paso, reinicio, HOME/tapa combinados, entrada retenida,
fallos y limpieza. Las copias privadas A/B pasan el replay con Release y
ASan/UBSan. El ejecutable completo compila para ARM; **no se ha probado en
consola ni publicado un nuevo `.3dsx`/paquete SD en esta etapa**. La entrega
posterior se cerró en [HM-T4d](f06-01-heather-room-delivery.md), incluido un
ajuste de la ruta SD antes de empaquetar. Este informe conserva la evidencia c.2.

## Implementación y comportamiento

- [Contrato HRR/SRR1](../../schemas/heather-room-runtime-v1.md),
  [preparador](../../tools/pipeline/prepare_heather_room_runtime.py) y
  [lector transaccional](../../engine/platform/common/room_runtime.cpp).
- [RoomLoop](../../engine/application/room_loop.cpp) enlaza el controlador
  HM-T3d y los contactos HRC con `IRoomView`. Valida spawn antes de publicar
  y en cada reinicio. `IMovementSession` permite reutilizar HID/APT.
- [Renderer](../../engine/platform/3ds/render/room_renderer.cpp) y
  [bucle 3DS](../../engine/platform/3ds/render/room_main.cpp): reservas,
  texturas/CRC, draw plan compartido, HUD, pausa/reintento y salida RAII.

El tiempo mantiene pasos de 40 ms, dos ticks PAL y máximo tres pasos por
muestra. Descarta intervalos >120 ms y tiempo suspendido. Pausa y reinicio
exigen liberar botones. R avanza un paso estando pausado; L reinicia; START
sale. HOME y tapa mantienen bits independientes: solo se recupera el estado
previo cuando ambos motivos se liberan. Conservar la pausa previa evita un
avance accidental al volver al juego.

Contacto, reloj, pose y matriz se publican por paso completo. Un error de
simulación conserva el último paso válido, incluidos subpasos ya terminados
del mismo frame, y pausa. Un bloqueo geométrico mantiene posición/Y y deja
avanzar la animación. No se promete rollback de subpasos correctos.

Los errores quedan visibles y latentes. Tras soltar, L revalida spawn y
reinicia; A reanuda desde la pausa. Un error de render evita repetir dibujos
hasta L. `busy` es transitorio: permite continuar simulación, pero no modifica
el VBO ocupado. Una inicialización fallida libera recursos parciales antes
de ofrecer L para cargar otra vez. La sustitución de datos es todo-o-nada.

El render conserva las 31 formas, las texturas originales de Heather y el
vidrio de HM-T4c.1, la transformación única y el orden combinado de vidrio y
cabello. El HUD muestra **CAMARA FIJA PROPIA** y **29 FORMAS CON MATERIAL
NEUTRO**. La ampliación HM-T4c.3 sigue pendiente y no bloquea esta entrega
diagnóstica. No hay afirmación de equivalencia visual/física general con PS2.

## Datos privados y replay

Nuevas copias, con creación exclusiva 0700/0600:

- `/Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-a`
- `/Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-b`

**28 archivos de datos y 23556089 bytes por copia**, más manifiesto y enlace
pendiente. Mantienen sin cambios los 26 archivos de `heather-room-scene-v1`
y añaden el manifiesto padre y SRR1. Descriptor: 596 bytes,
SHA-256 `06bea16f27746c9a176ba693d384921a00253f0c98495ccf28d0264fec81fc36`.
Las fuentes y paquetes anteriores permanecen intactos. No se copiaron
geometría, texturas ni poses privadas al repositorio o al contenedor.

El [auditor](../../tests/heather_room_runtime_audit.py) desempaqueta SRR1 de
forma separada y coteja bits de las 32 cajas/suelo, spawn, CRC, manifiestos y
bytes HRS. Relee las dos copias y sus fuentes al finalizar. Ejecuta el lector,
renderer, controles, bucle y contactos **de producción**, con SDK sustituido
por dobles instrumentados. La salida capturada se reduce a hashes/estado.

**12 replays privados**: tres cadencias (25, 60 y 143 Hz) × dos copias × dos
ejecutables (Release y ASan/UBSan), con 100 pasos fijos cada uno. El guion
incluye idle/caminar/correr/girar y bloqueo real del perfil. Las cadencias
60/143 intercalan pausa, HOME+tapa, retorno parcial, tiempo prolongado y
liberación. Matriz, modelo y contador final coinciden exactamente entre
cadencias en cada ejecución; se exige bloqueo observado y Y conservada.

Se repitió la auditoría con `python -O`: otros 12 replays, **informe idéntico**.
Los cuatro stdout nativos coinciden por hash. La auditoría no usa `assert`
eliminables para sus decisiones. El oráculo independiente de geometría y
skin/orden sigue siendo el de HM-T4b.3/c.1; este nuevo replay acredita la
integración y estabilidad temporal en host, no añade un oráculo de raster GPU.

## Requisitos y pruebas

| Requisito | Evidencia |
| --- | --- |
| HR04, spawn/reinicio | Contacto nulo al construir y en L; fallo conserva instantánea; reset válido recupera |
| HR08, tiempo/ciclo de vida | Cadencias distintas, máximo tres pasos, pausa/R, botones retenidos, HOME+tapa en ambos órdenes, START/ONEXIT |
| HR09, render compartido | Código real con dobles SDK: buffers/rangos/materiales, cámara común, CRC/upload, GPU busy sin sobrescritura |
| HR10, memoria/errores | Sin asignaciones propias por frame; carga transaccional, fallos de asignación/IO/GPU, cierre/liberación, tamaños ARM |
| HR11, cotejo | Replays A/B Release/sanitizadores; regresiones de los oráculos de contactos y escena |

[`test_room_loop`](../../tests/cpp/test_room_loop.cpp) prueba contacto/lector
fallidos, último subpaso íntegro, error gráfico, reentrada, spawn inválido y
recuperación. Repite 150 pasos frente a una pared inventada a intervalos de
1/16/40/79/120 ms, con interrupciones. Prohíbe asignaciones heap durante el caso.

[`test_room_runtime`](../../tests/cpp/test_room_runtime.cpp) y sus
[dobles SDK](../../tests/cpp/room_sdk.cpp) prueban todos los open/close de la
carga, lecturas fallidas, doce mutaciones del descriptor y seis asignaciones
fallidas. Conservan el puntero anterior y verifican cierres. Inyectan 19 etapas
de inicialización SDK fallidas, tres reservas CPU, lecturas de texturas y CRC
incorrecto. Comprueban terminación de frame, sincronización antes de liberar
y ausencia de recursos vivos tras éxito, error y reintento. El `run_room` real
se ejecuta con HID/APT programados y recuperación de una creación de target fallida.

- **76/76 CTest Release**, **75/75 ASan/UBSan** de la regresión relacionada;
  la prueba de pila de contactos solo se registra sin sanitizadores.
- **4/4 CTest GCC**: bucle, runtime, controlador y controles 3DS. Usa fixtures
  inventados; CI no necesita fuentes privadas.
- **418/418 pruebas Python** de runtime, preparación, escena y contrato de
  contactos, incluidas las diez nuevas pruebas del preparador HRR.
- Lint/formato, revisión local de propiedad/errores y comprobador del repositorio.
  Gates añadidos a CI; no se ha ejecutado CI remoto.

| Módulo | Líneas | Ramas |
| --- | ---: | ---: |
| RoomLoop | 54/54 (100 %) | 63/68 (92.6 %) |
| Lector runtime | 116/119 (97.5 %) | 97/112 (86.6 %) |
| RoomRenderer | 143/144 (99.3 %) | 100/106 (94.3 %) |
| Bucle principal | 86/88 (97.7 %) | 69/83 (83.1 %) |
| Controles 3DS modificados | 63/63 (100 %) | 42/44 (95.5 %) |
| Controlador modificado | 109/110 (99.1 %) | 90/94 (95.7 %) |
| Preparador Python | 49/50 (98 %) | 5/6 (83.3 %) |

Todos los gates individuales superan 80 % de líneas y ramas. La rama Python
de `__main__` se ejecutó en la publicación CLI real, fuera de cobertura pytest.

## Memoria y ARM

Presupuesto total **42287748 bytes = 40.33 MiB / 64 MiB**, incluido el margen
de plataforma de 12 MiB. Añade 2 MiB al presupuesto HRS para la copia anterior
durante reemplazo y margen de carga/pila. Texturas residentes: 17.5 MiB.
No es un pico medido en consola ni una medida de fragmentación del heap.

Compilación ARM: RoomAssets=1395120, RoomLoop=27968, MovementControls=40,
RoomRenderer=852, RoomMovementContacts=556 bytes. Bucle+controles=28008 bytes,
bajo 32 KiB. El render/carga mantiene los arrays grandes fuera de la pila.

`sh3_heather_room.elf`, build **`c25237edb7d9`**, ELF32 ARM EABI5:
207868 bytes de text, 7640 de data y 19336 de BSS. Compilación completa,
shader validado y enlace correcto con libctru/Citro3D. Imagen fijada
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`,
sin red, raíz y fuentes en solo lectura, sin capacidades y con límites de
memoria/CPU. No se montaron datos privados. No se generó/publicó paquete SD.

Informe privado de metadatos: `reports/local/f06-01-heather-room-runtime.json`.
JUnit, cobertura, logs, tamaños, ELF, comando de contenedor y manifiesto de
validación: `build/heather-room/runtime-v1/`. Las incidencias intermedias
(firma `noexcept` del doble stdio en GCC y ajustes de inyección de fallos)
quedan en los logs; las cifras anteriores son las ejecuciones finales.

## Reproducción y siguiente entrega

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_heather_room_runtime.py
rtk proxy cmake --build build/host-release --target test_room_loop test_room_runtime test_movement_controller test_ctr_movement_controls
rtk proxy ctest --test-dir build/host-release -R '^(room_loop|room_runtime|movement_controller|movement_ctr_controls)$' --output-on-failure
rtk proxy .venv/bin/python tests/heather_room_runtime_audit.py \
  --scene-a /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-a \
  --scene-b /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-b \
  --runtime-a /Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-a \
  --runtime-b /Users/germancontreras/sh3-private-data/heather-room-runtime-v1-copy-b \
  --executable "$PWD/build/host-release/test_room_runtime" \
  --executable "$PWD/build/host-sanitize/test_room_runtime"
```

Usar `-O` después de Python repite la auditoría optimizada. La preparación
inicial usó `tools.pipeline.prepare_heather_room_runtime`, los dos `--scene-*`
anteriores, `--private-root /Users/germancontreras/sh3-private-data` y
`--run-prefix heather-room-runtime-v1`; repetir el nombre rechaza sobrescritura.

[HM-T4d](f06-01-heather-room-delivery.md) empaquetó el `.3dsx` con los datos
necesarios, releyó A/B e identificó build, recorrido, controles y limitaciones.
**HM-T5** mantiene
pendiente lectura SD, raster PICA, pausa/reinicio/HOME/tapa y salida reales,
pico de memoria y medidas CPU/GPU. La cadencia de simulación no acredita FPS.

## Corrección posterior a la entrega física

El build `ad84b65cd58d` falló la aceptación física por inmovilidad percibida
y carga de unos 20 s. El [seguimiento HM-T5](f06-01-heather-room-fault.md)
registra el cambio posterior de política de intervalos, validación estática
preparada, CRC por tabla, CPU rápida y diagnósticos. La evidencia de HM-T4c.2
conservada en este informe corresponde al comportamiento previo.
