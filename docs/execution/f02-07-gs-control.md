# F02.07 — Retención integrada de MTGS (SRC82)

Fecha: 2026-10-18. Completa **IW-GS1–3**, según
[GC01–GC08](../../schemas/gs-control-v1.md). **IW-COORD sigue pendiente**:
EffectDrainPort conserva `Progress::rejected`; esta evidencia no habilita captura.

## Implementación

La copia nueva parte de `source-vu-control-v2`, commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, y contiene 2.961 archivos. Cambian
MTGS.h/cpp y VMManager.cpp; se añade el [adaptador propio](../../tools/observer/pcsx2/gs_control.inc).
Las dieciséis copias anteriores y todo el código VU de SRC81 se conservan intactos.

ThreadEntryPoint inicia una generación **después de GSopen exitoso y antes de
notificar apertura**. El contador persiste al cerrar/reabrir, reiniciar el hilo y
resetear WorkSema. Apertura fallida o en curso y agotamiento rechazan solicitudes;
la ejecución GS normal puede continuar con control offline si se agota la identidad.

CPU solicita desde una frontera válida y pausada, con token propio y sesión
operativa. Request precede a NotifyOfWork directo, sin paquete ni SetEvent; por
ello no se modifica CopyDataTally. El servicio de MainLoop consulta antes de la
próxima rama idle/espera, adquiere el token y revalida open, cola y señales
OnRingReset/Vsync. Después de despertar se completan comandos y señales antes
de volver a esa frontera. Se cubre la publicación posterior a un vacío anterior.

El servicio **libera RingBufferBusy2 antes de acknowledge** y lo readquiere tras
release. Mientras held espera ControlWakeup, sin presentar, iniciar callbacks ni
ejecutar el epílogo. Los intervalos de 50 ms solo reconsultan estado. Un flag de
cierre directo no libera el token; CPU debe cancelarlo. Stop se resuelve sin el
mutex antes de descarte de cola/Kill y del posterior GSclose. Offline en ese
punto no certifica ausencia global de escritores durante el cierre.

BeforeObserverProducer y StopObserverPineDrain cancelan **GS→VU** antes de los
efectos/transiciones ya instrumentados. Este orden libera permisos, sin prometer
que GS haya ejecutado antes de VU. No existe aún un coordinador que solicite ambos
en orden VU→GS ni una prueba conjunta del frontend. SetRunIdle sigue siendo una
operación del worker GS dentro de sus efectos, como establece el proveedor.

WorkerControl conserva la máquina de estados, el adaptador conecta sesión/cola/
mutex y VMManager valida actor/cancelación. No cambia el core ni WorkSema, no se
añade un waiter CPU de WaitForEmpty, y el aviso al propietario sigue coalescido.

## Validación

El [probe propio](../../tests/fixtures/pcsx2-gs-control/README.md) usa 30 fragmentos
exactos privados, WorkSema/KernelSemaphore Darwin/Mach, WorkerControl y CpuBoundary
reales, std::thread y dobles de efectos. Los tipos y renderer no son la ABI ni GPU
del proveedor; UserspaceSemaphore, VU/semaXGkick y PINE son dobles.

| Comprobación final | Normal | ASan/UBSan | TSan |
|---|---:|---:|---:|
| GS, 21 escenarios | 21/21 | 21/21 | 21/21 |
| Regresión VU, 15 escenarios | 15/15 | 15/15 | 15/15 |

**108 ejecuciones finales aprobadas**, sin informes de sanitizadores: 63 GS y
45 VU. En GS, 57 ejecutan MainLoop/ThreadEntryPoint exactos y seis prueban el
servicio con intercalaciones sintéticas de cola/señales. En VU, 42 ejecutan
ExecuteRingBuffer y tres su servicio aislado. La regresión usa guardias VMManager
actualizadas y un doble de cancelación GS, sin modificar el fixture público SRC81.

Se prueban comandos/callbacks y publicaciones, señales antes del acuse, mutex
disponible, idle y datos adversos bajo held, cancelación/plazo, cierre pendiente/
retenido, apertura en curso/fallida, reapertura/reinicio, actor/identidad, agotamiento
y consumo MTVU. El caso de despertar espera STATE_SLEEPING del WorkSema nativo
antes de request, mediante acceso expuesto solo en el probe. El caso opening usa
una solicitud asíncrona propia para observar GSopen bloqueado. El timeout simula
release CPU explícito, sin probar el coordinador.

**Seis objetos ON/OFF** (MTGS, MTVU y VMManager) compilan correctamente. **Seis
negativos** detectan mutex retenido y ejecución bajo held por aserción, y omisión
de reconsulta de cola, señales, despertar y cancelación por plazo de tres segundos.
Todos verifican cierre del grupo mediante supervisor. Las aserciones de negativos
pueden abortar al destruir el std::thread global activo; no acreditan cierre limpio
del proveedor. La expectativa inicial que exigía exit 1 se corrigió en un script
nuevo, conservando su log, fragmento mutado, binario y recibos.

No se fuerza CAS retry de stop, terminación abrupta, excepción de renderer, bloqueo
Qt ni una VM conjunta. COPY_GS_PACKET_TO_MTGS=0 coincide con la fuente fijada;
las ramas de configuración 1, debug-stack y DEVBUILD no se ejercitan en este probe.
Las pruebas de unidad no convierten estas configuraciones en modos admitidos.

## Custodia, pipeline y reproducción

SRC81 se audita otra vez con hash idéntico
`b79d2d9240afbff849d19d934a2829def17378dad2d698f717115f0d627b5a61`.
Dos auditorías SRC82 verifican diecisiete copias, fragmentos, adaptadores/core,
objetos, binarios, logs, recibos y negativos; sustentan la
[evidencia pública](../compatibility/gs-control-evidence.json).

Se preservan una extracción parcial fallida por ancla de namespace ambigua,
las 60 ejecuciones GS iniciales antes de reforzar la sincronización del probe y
el primer negativo cuyo código de salida se clasificó incorrectamente. Las
correcciones afectan extracción/harness/verificador; la copia GS v1 no se reescribe.

Receta local, con destinos nuevos para preparación y reportes:

```text
rtk proxy .venv/bin/python build/f02-07-gs-control/prepare.py
rtk proxy .venv/bin/python build/f02-07-gs-control/fragments-v2.py
rtk proxy .venv/bin/python build/f02-07-gs-control/compile_private.py
rtk proxy .venv/bin/python build/f02-07-gs-control/run_probe-v2.py normal-native
rtk proxy .venv/bin/python build/f02-07-gs-control/run_probe-v2.py sanitize-native
rtk proxy .venv/bin/python build/f02-07-gs-control/run_probe-v2.py tsan-native
rtk proxy .venv/bin/python build/f02-07-gs-control/prepare_vu_regression.py
rtk proxy .venv/bin/python build/f02-07-gs-control/run_vu_regression.py normal-native
rtk proxy .venv/bin/python build/f02-07-gs-control/run_vu_regression.py sanitize-native
rtk proxy .venv/bin/python build/f02-07-gs-control/run_vu_regression.py tsan-native
rtk proxy .venv/bin/python build/f02-07-gs-control/negative_controls-v2.py
rtk proxy .venv/bin/python build/f02-07-vu-control/audit.py f02-07-vu-control-v1-src82-custody.json
rtk proxy .venv/bin/python build/f02-07-gs-control/audit.py f02-07-gs-control-v1.json
rtk proxy .venv/bin/python build/f02-07-gs-control/audit.py f02-07-gs-control-v1-repeat.json
```

Apple Clang/C++20/x86_64, piso 10 GiB libres. Objetos: 180 s/build y etapa 1 GiB.
Probes: 120 s/build, 15 s/caso y etapa 256 MiB. Negativos: 120 s/build, 3 s/caso
y etapa 1 GiB. El harness GS omite avisos de declaraciones/variables estáticas sin
uso al incluir la región original completa; no cambia opciones de los objetos del
proveedor. Scripts, fragmentos y compuestos siguen privados/locales.

Se comprueban Ruff, repositorio y whitespace. No se repiten CTest host ni suite
Python completa porque su core no cambia; se repiten los probes afectados por la
guardia compartida. No se ejecutan CI remota, build 3DS, aplicación PCSX2 completa
ni consola, y no se reemplaza la aplicación instalada.

## Siguiente tarea

**IW-COORD:** conectar EffectDrainPort con identidades de sesión y tokens sin
reciclar, solicitar VU→GS y liberar GS→VU, gestionar cancelación parcial/plazos y
despacho Qt sin bloqueos del frontend. Rechazar sesiones cerradas, abriendo o
cambiadas; offline no equivale a ausencia segura. Conservar los modos admitidos
vacíos hasta validar productores, callbacks y frontend completo. B3-B2 global,
B3-B3c/CQ3-C, AD-3 y F02.07 permanecen abiertos.
