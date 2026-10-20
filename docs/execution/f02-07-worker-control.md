# F02.07 — Canal independiente CPU↔worker (SRC79)

Fecha: 2026-10-18. Completa **B3-B1 y el núcleo portable de B3-B2** según
[WC01–WC10](../../schemas/worker-control-v1.md). WorkerControl separa identidad y
retención de la cola de datos; ControlWakeup comunica cambios sin AsyncCall ni
despacho Qt. **La integración B3-B2 y B3-B3/CQ3-C sigue pendiente:** este núcleo
no detiene trabajadores PCSX2 ni habilita capturas por sí solo.

## Implementación y responsabilidades

Código propio en tools/observer, compilado solo con BUILD_TESTING en host.
WorkerControl mantiene una instantánea atómica de generación, ID y fase;
ControlWakeup administra únicamente los avisos. No conocen VM, Qt, PINE ni
ringbuffers. La composición futura debe respetar el puerto EffectDrainPort y
sus dependencias, sin incorporar este tooling al runtime Nintendo.

Un actor CPU solicita/libera y un actor worker inicia/acusa/detiene. El acuse
publica efectos anteriores y obliga al worker a permanecer sin producir hasta
que CPU libere el token. Un stop con held devuelve retained; una carrera de CAS
devuelve retry. Ambos impiden salir del worker. stop tiene nodiscard para exigir
que el caller atienda el resultado. Destrucción y fallos del hilo requieren
coordinación externa; no hay un destructor que finja liberar otra autoridad.

Generación de 32 bits e ID de 29 bits positivos, sin reutilización ni wrap.
Se exige atomic de 64 bits sin locks en el host. Las operaciones usan CAS fuertes
y trabajo acotado: release hace como máximo dos intentos para resolver la carrera
requested→held. IDs antiguos no pueden retirar una solicitud nueva ni restaurar
held después de una cancelación. El reinicio exige offline y generación mayor.

El aviso usa un semáforo binario y flag atómico. Los notificadores agrupan avisos;
el consumidor único adquiere también los avisos agrupados al limpiar el flag con
exchange(acq_rel). Una señal no significa held: siempre se vuelve a consultar
el estado. Las esperas aceptan un plazo y no ejecutan callbacks. Una espera puede
fallar espuriamente; el caller repite la consulta hasta cumplir el predicado o
agotar el plazo. No se usa el semáforo como contador de solicitudes.

Esto separa responsabilidades y conserva interfaces pequeñas. No se añade una
abstracción de proveedor a la máquina de estados ni una política de VM al aviso.
El coordinador posterior establecerá el orden VU→GS y liberación GS→VU.

## Validación ejecutada

**18 CTest nuevos**, incorporados a la batería host existente: 17 escenarios y
un proceso de control de asignaciones. **138/138 pasan en Debug, Release y
ASan/UBSan**; las comprobaciones permanecen activas con NDEBUG. Timeout CTest de
15 s; esperas del harness con plazos de 5 s, sin exigir latencias precisas.

| Requisitos | Evidencia del núcleo |
|---|---|
| WC01,05,06 | Inicio/offline, token ajeno, duplicado, ID creciente, reinicio, límite de ID y generación, estados coherentes |
| WC02–04 | Cancelación antes/después de acuse, acuse tardío, held estable ante stop, liberación del propietario |
| WC04,08 | 3.000 carreras release/ack, 1.500 request/stop y 1.500 stop/release, sincronizadas con barreras |
| WC07 | Aviso antes de esperar, entre comprobación y espera, agrupación, consumidor no bloqueante, timeout y varios notificadores |
| WC02,07 | Payload ordinario publicado por request, ack y release; 2.000 intercambios por wake; publicación de un aviso agrupado posterior al permiso original |
| WC06,07 | Aviso CPU compartido por dos buzones sin confundir sus acuses |
| WC08 | 1.000 ciclos con operator new rechazado después de construir el núcleo; comprobación local de asignaciones escalares, no perfil global del proveedor |
| WC09 | Modelo de cola de datos de una posición llena: control llega por separado, trabajo previo termina antes del acuse y release permite detenerse |

Diez escenarios de concurrencia/avisos pasan además con **ThreadSanitizer** local.
Esto detecta carreras ejercidas por el harness; no demuestra todos los órdenes
posibles ni sustituye la integración de los workers reales.

Cobertura LLVM local del núcleo: worker_control.cpp **93/95 líneas (97,89 %)** y
**77/80 ramas (96,25 %)**; cabecera 100 % de líneas y ramas instrumentadas. El
umbral local es 80 % en ambos. No se introdujeron accesos privados o hooks de test
para cubrir retornos defensivos no alcanzables bajo el contrato de actores.

Tres mutaciones aisladas compilan y los tests detectan la aserción prevista:
permitir stop durante held, aceptar un acuse ajeno y omitir la señal de despertar.
Fuentes mutadas, logs y hashes quedan en build local; el código final se conserva.

La primera batería pasó 137 pruebas por preset. Se conservan snapshots y logs;
la batería final añade publicación agrupada, publicación request/release y
nodiscard. No hubo compilaciones ni pruebas fallidas del código final; los tres
fallos deliberados pertenecen exclusivamente a los controles negativos.

## Pipeline y reproducción

CMake exige C++20 solo para sh3_worker_control y sus consumidores. El runtime
mantiene C++17. Los nuevos tests entran automáticamente en los jobs existentes
Linux/macOS Release/ASan-UBSan y en cobertura GCC de GitHub Actions. No se ejecutó
CI remota, cobertura GCC, suite Python completa ni build 3DS en esta unidad;
ThreadSanitizer y cobertura LLVM se ejecutaron localmente con Apple Clang.

Receta pública, sin originales ni fuentes PCSX2:

```text
rtk proxy cmake --preset host-debug
rtk proxy cmake --build --preset host-debug --parallel 2
rtk proxy ctest --preset host-debug
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --parallel 2
rtk proxy ctest --preset host-release
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --parallel 2
rtk proxy ctest --preset host-sanitize
```

Los tests específicos pueden seleccionarse con `-R worker_control_`. La receta
GCC de cobertura permanece en .github/workflows/ci.yml, con umbral 80 % de líneas
y ramas. Ruff, comprobaciones de repositorio y whitespace se validan localmente.

## Custodia y siguiente tarea

Las catorce copias privadas permanecen idénticas. SRC78 se vuelve a auditar y
produce su hash histórico; no se recompila ni ejecuta el proveedor. El CMake
anterior queda en un snapshot cuyo hash coincide con el fijado por SRC76. La
evolución pública intencional se registra sin modificar informes anteriores.
Dos auditorías SRC79 iguales sustentan la
[evidencia pública](../compatibility/worker-control-evidence.json), sin rutas
personales, bytes del juego ni cuerpos PCSX2.

Siguiente unidad: **B3-B3**, concretar los puntos donde VU y GS pueden acusar y
esperar sin efectos, incluyendo idle, métricas, cierre y callbacks UI síncronos.
Eso permite completar la integración B3-B2: un wake propio todavía no despierta
un worker que duerme en WorkSema. Se debe resolver su espera combinada/control,
el progreso GS mientras VU drena y la liberación antes de despachar Qt o salir.
No basta llamar a acknowledge desde un modelo ni observar una cola vacía.

CQ3-B global, CQ3-C/D, B3-C/B4, CQ-4 y AD-3 siguen abiertos. El puerto productivo
conserva rejected, los modos admitidos permanecen vacíos y no hay captura nueva.
