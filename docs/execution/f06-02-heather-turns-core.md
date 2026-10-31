# F06.02/heather-turns — HG-T4.1: perfil y núcleo de giros

2026-10-30. **HG-T4.1 completada**: el núcleo C++ admite el perfil 2 de
cinco clips y las cuatro transiciones espera↔giro de
[HG-T3](../../schemas/heather-turns-native-v1.md). Estado de la entrega:
**núcleo validado en host, pendiente de recursos e integración en la escena**.
Las pruebas adicionales de HM-T5 permanecen aplazadas y se conserva la
entrega de consola `c3aae59d1a70`.

## Implementación y compatibilidad

`LocomotionProfile` separa capacidad cinco de cantidad activa tres/cinco.
`heather_turns_profile` fija ID 2, recursos 522/525, 78 muestras, ticks 2 y
orden 101,109,113,107,108. ID 1 conserva su prefijo y 58 muestras. La
validación compara todos los campos, incluidos los dos registros inactivos
cero del perfil 1. Buscar un clip recorre solo registros activos: ID 0 no
puede confundirse con una ranura vacía. La vista acotada usa C++17.

El reloj acepta exactamente los nueve arcos del contrato. Las siete mezclas
con caché usan una tabla por origen/destino; los dos arcos caminar↔correr
conservan modo 5. Los giros entran con 768/768 y salen hacia espera con
1024/410; caminar/correr→espera mantiene 1280/360. El contador se envuelve
dentro del clip, y la salida de modo 3 avanza una sola vez. La salida de
modo 5 conserva sus dos avances. No hay interrupción ni puente implícito
en el dominio; mismo destino/solicitud vacía continúa la mezcla.

El evaluador valida ventanas y planes con su identidad de perfil. La
inicialización y el reinicio propagan esa identidad, incluida la validación
del clip antes de leer muestras. La caché conserva la pose local interpolada
de ambos canales y se invalida al finalizar. Se reutilizan NLERP corto,
jerarquía y publicación transaccional. Se fijan expresamente
`-fno-fast-math -ffp-contract=off` para la unidad de poses.

Adaptaciones necesarias para preservar HL al crecer el arreglo:

- El lector legado decodifica exactamente sus tres descriptores y registra
  `clip_count=3`; los dos nuevos registros quedan cero.
- El lector de muestras recorre la cantidad activa y el visor HL usa esa
  cantidad para seleccionar anterior/siguiente.
- El validador de rig y el lector SRI2 continúan rechazando el perfil 2.
  El transporte de 78 muestras corresponde a HG-T4.2; la capacidad del rig
  sigue en 64 y SRI1 no cambia.
- Una prueba de perfil desconocido usaba el número 2: ahora usa 99, mientras
  se añaden rechazos explícitos de perfil 2 bajo la interfaz legado.

Archivos principales: [reloj](../../engine/domain/locomotion_clock.cpp),
[perfil](../../engine/domain/include/sh3/domain/locomotion_clock.hpp),
[poses](../../engine/domain/locomotion_pose.cpp) y
[publicación](../../engine/domain/locomotion_update.cpp).

## Validación nativa y errores

[Harness C++](../../tests/cpp/test_heather_turns.cpp) y
[adaptador independiente](../../tests/heather_turns_oracle.py), registrados
en CTest. El adaptador consume los literales HG-T3 fijados antes del código;
no importa pipeline ni recursos privados. La composición de referencia
reutiliza el oráculo HL de productos de cuaterniones sobre vectores base.
Se conserva el JSON sin modificaciones, SHA-256
`433811f29a1687bb5bd357d73234f7290a0cbef407df18a6dba1575c62c833ae`.

**405 resultados nativos** coinciden: bordes Q12, dos ciclos, cuatro arcos
completos, matriz de selección, continuaciones, errores, dos replays y poses
con origen fraccionario. Incluyen el hemisferio antipodal. Diferencia máxima
local `5.18185564e-08` frente a `1e-6`; modelo `8.50714789e-07` frente a `4e-6`.
Los replays verifican la secuencia de animación solicitada; la elección de
esas solicitudes desde botones y su cola siguen perteneciendo a HG-T4.3.

El harness añade **1402 rechazos** y **1303 pasos correctos/reintentos**:
perfiles mal formados, registros inactivos, planes incoherentes, lectura
faltante/pose inválida en cada lectura de entrada, continuación y salida de
los cuatro arcos, ciclos estables e inicialización de 73 huesos. Ante error,
compara los bytes de la instantánea previa; los callbacks observan siempre
esa instantánea. Tras reparar el lector, reintenta con el mismo estado y
workspace y compara reloj, cachés y matrices con una ejecución sin fallo.
Las pruebas se ejecutan con `new/new[]` prohibidos, incluidas asignaciones
alineadas. No se añade almacenamiento dinámico al núcleo.

No se atribuyen a esta unidad fallos de contactos, archivos/texturas,
HOME/tapa o publicación de movimiento junto con animación del perfil 2.
Son validaciones posteriores; las regresiones HM existentes se conservan.

## Regresiones, cobertura y memoria

**16 casos CTest pasan** en cada entorno: Clang Debug, Clang ASan/UBSan y GCC
con cobertura. Incluyen los tres oráculos HL de reloj/pose/publicación,
el oráculo de transporte SRI2 legado, lector, visor, actor, controlador,
bucle de habitación y dobles SDK relacionados. También pasan **745 pruebas
Python** de contratos HG/HL y productor/reconstrucción SRI2 legado.
Los dos tests nativos nuevos forman parte de CTest en CI; el adaptador Python
se incorpora a sus controles de Ruff. No se ejecutó GitHub Actions remoto.

Gates GCC independientes, mínimo 80 % de líneas y ramas:

| Unidad | Líneas | Ramas |
|---|---:|---:|
| reloj | 111/111 — 100 % | 138/138 — 100 % |
| poses | 180/183 — 98,4 % | 197/220 — 89,5 % |
| publicación | 45/45 — 100 % | 42/42 — 100 % |
| visor HL | 123/146 — 84,2 % | 103/119 — 86,6 % |
| rig/lector de muestras | 28/28 — 100 % | 40/40 — 100 % |
| lector SRI2 | 189/189 — 100 % | 164/166 — 98,8 % |

La recolección usa exclusivamente `build/heather-turns-core/coverage`;
no mezcla contadores antiguos de `build/host-coverage`. Se reutilizó la
imagen Docker local, sin red ni reiniciar servicios, digest
`sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.

Medidas `sizeof` en host: perfil **184 bytes**; estado **9168** y workspace
**8872**, suma **18040/32768**. Solo crece el perfil: 68 bytes respecto a
sus tres descriptores; no se crean cachés por clip. Esto no mide el pico
del proceso, las 78 muestras decodificadas ni memoria ARM. Esas mediciones
se completarán con HG-T4.2/.4.

Ruff/formato, control del repositorio y `git diff --check` pasan. Evidencia
local en `build/heather-turns-core/`: JUnit host/sanitizers/GCC/Python, JSON
de los seis gates y scripts de cobertura. Resumen y hashes:
`reports/local/heather-turns-core-v1.json`.

```sh
rtk proxy cmake --build --preset host-debug --parallel 4
rtk proxy ctest --preset host-debug -R 'heather_turns|locomotion|inspection_actor|movement_controller|room_loop' --output-on-failure
rtk proxy .venv/bin/python tests/heather_turns_oracle.py build/host-debug/test_heather_turns
rtk proxy .venv/bin/python -m pytest -q tests/python/test_heather_turns_contract.py tests/python/test_heather_locomotion_contract.py tests/python/test_locomotion_inspection.py tests/python/test_produce_heather_locomotion.py tests/python/test_locomotion_rig_reconstruction.py
```

## Siguiente unidad

**HG-T4.2:** separar capacidad y límites SRI1/SRI2, preparar productor/lector
del perfil 2 y sus 78 muestras desde A/B, cotejando las 70 referencias HG-T2.
Después, HG-T4.3 integra acciones/controles/puentes y publicación conjunta con
HM; HG-T4.4 cierra memoria y ARM. No se genera ni copia un nuevo build de
consola en HG-T4.1. HM-T5 adicional y navegación de pared 60 siguen aplazadas;
F06.02 global y G04/G05 permanecen abiertos.
