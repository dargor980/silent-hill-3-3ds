# HM-T3a/b — Planificador nativo de movimiento

Fecha: 2026-10-29. **HM-T2b.7a, HM-T3a y HM-T3b completadas.**
El usuario solicita posponer la búsqueda de pared 60/hueco 14/60 y avanzar
con lo ya observado. C148 y las auditorías permanecen preservadas; no se
realiza navegación, captura, restauración ni reanudación de PCSX2 en esta entrega.
HM-T2b.5–7 y el solver general continúan pendientes en sus ámbitos originales.

## Contrato e implementación

[HMN01–07](../../schemas/heather-movement-native-v1.md) fija un perfil nativo
de inspección separado de cualquier afirmación de equivalencia EE/VU.
El núcleo [inspection_movement.cpp](../../engine/domain/inspection_movement.cpp)
propone espera, caminar, correr y giro: pasos de 0/28/70 unidades por
actualización de dos ticks PAL y ±0,088 radianes de giro. Calcula primero
el desplazamiento con la orientación anterior, conserva Y y genera una
matriz `T(posición)·Ry(yaw)` por columnas con escala unitaria.

La [API](../../engine/domain/include/sh3/domain/inspection_movement.hpp)
recibe estado, intención y ticks, sin archivos, SDK, cámara, pose ni
memoria de PCSX2. La propuesta no resuelve contactos y su delta expresa
el desplazamiento solicitado, antes del redondeo de posición. El estado
publicado sigue siendo responsabilidad del futuro coordinador.

Valida entradas finitas, posición acotada, yaw semiabierto, enums, ticks y
ordinal. El error conserva todos los bytes de salida; admite que la entrada
sea `out.next` y asigna solo al terminar. Estado y propuesta suman como
máximo 128 bytes; las pruebas prohíben `new`. La unidad se compila con
`-fno-fast-math -ffp-contract=off`. Son decisiones nativas documentadas,
no una reproducción del redondeo PS2 ni del microajuste sin contacto.

Separación SOLID: el dominio solo planifica; el coordinador posterior
dependerá de un puerto de contactos y del núcleo HL. Pose local, cámara,
temporizador y render no se incorporan a este módulo. No se añade un
resolvedor vacío que pueda confundirse con física funcional.

## Verificación

| Comprobación | Resultado |
| --- | --- |
| CTest seleccionado macOS Release | 9/9 aprobadas |
| Mismos casos ASan/UBSan, `halt_on_error=1` | 9/9 aprobadas |
| Oráculo geométrico independiente | 72 combinaciones yaw/movimiento/giro, doble precisión mediante rotación compleja |
| Replay por ticks | 100 actualizaciones por recorrido, mismas intenciones, cuatro cadencias de presentación: estado final idéntico en la misma plataforma |
| Errores y límites | NaN/Inf, posición, yaw, enums, ticks, ordinal, salida fuera de límites, precedencia, aliasing y conservación byte a byte |
| GCC 12.2 con configuración exacta del gate nuevo | 47/47 líneas, 40/40 ramas, 3/3 funciones |
| devkitARM GCC 16.1, Release | `sh3_domain` compilado; objeto ELF32 ARM EABI5, texto 820 bytes, datos/BSS 0 |
| Contratos del repositorio | PASS, 0 errores |
| Regresión del verificador del repositorio | 35 pruebas Python aprobadas |
| Enlaces locales del contrato/informe/spec y formato del diff | Verificados |

Las regresiones incluyen reloj, pose, publicación conjunta HL y colocación,
con sus oráculos. La prueba de replay agrupa llamadas del planificador en
un harness sintético: no acredita aún el temporizador del presentador,
HOME/tapa, recuperación tras suspensión ni igualdad bit a bit host/ARM.

El [gate individual](../../gcovr-inspection-movement.cfg) exige 80 % de
líneas y ramas en CI; se añadió su ejecución y XML a
[ci.yml](../../.github/workflows/ci.yml). El nuevo test es descubierto por
CTest y el módulo pertenece a `sh3_domain` también en la compilación ARM.
CI remota no ejecutada en esta entrega.

Comandos principales:

```sh
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_inspection_movement test_locomotion_clock test_locomotion_pose test_locomotion_update test_character_world --parallel 2
rtk proxy ctest --preset host-release -R '^(inspection_movement|locomotion_(clock|pose|update)(_oracle)?|character_world(_wire)?)$' --output-junit movement-tests.xml
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_inspection_movement test_locomotion_clock test_locomotion_pose test_locomotion_update test_character_world --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(inspection_movement|locomotion_(clock|pose|update)(_oracle)?|character_world(_wire)?)$' --output-junit movement-tests.xml
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

GCC/cobertura y ARM se ejecutaron en la imagen devkitPro fijada por el
repositorio, sin red y con fuentes montadas en solo lectura. Evidencia local
ignorada en `build/heather-movement/native-v1/`: comandos JSON, scripts,
`coverage-summary.json`, XML, biblioteca, comandos de compilación, cabecera
y tamaño ARM. El primer intento no encontró el daemon de Docker. Tras
iniciarlo, pruebas/cobertura y compilación pasaron; el recolector buscó
erróneamente `.cpp.o` en vez de `.o`. Se corrigió la ruta y se inspeccionó
el objeto de la biblioteca ya generada, sin repetir la compilación. Los
logs de ambos incidentes se conservan.

## Siguiente tarea

**Actualización:** [HM-T3c completada](f06-01-heather-contact-animation.md) y
[HM-T3d completada](f06-01-heather-movement-controls.md).
La descripción que sigue conserva el alcance previsto al cerrar HM-T3b.
La [selección HM-T4a](f06-01-heather-room-profile.md) también está completada;
[HM-T4b.1](f06-01-heather-room-contacts-contract.md) fija el contrato numérico
y vectores. [HM-T4b.2](f06-01-heather-room-contacts.md) implementa el núcleo
y puerto; sigue HM-T4b.3, preparación y cotejo A/B.

**HM-T3c:** puerto de contactos y publicación conjunta con HL. Debe validar
la posición aceptada, reconstruir la matriz final tras la corrección y
mantener posición, ordinal, reloj, caché y pose sin cambios ante cualquier
fallo. Las transiciones HL admitidas no se amplían: idle→run directo sigue
sin soportarse. Después, HM-T3d conectará controles y ciclo de vida; HM-T4
integrará una escena compartida con límites explícitos de navegación.

El build físico aceptado **`7250f427ffb9`** no se reemplaza. No se entrega
un nuevo `.3dsx` ni se afirma movimiento físico de Heather en una habitación.
