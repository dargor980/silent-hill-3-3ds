# F02.07 — Retención integrada de MTVU (SRC81)

Fecha: 2026-10-18. Completa **IW-VU1–3**, primera unidad de B3-B2, según
[VC01–VC08](../../schemas/vu-control-v1.md). **IW-GS e IW-COORD siguen pendientes**:
el puerto EffectDrainPort conserva `Progress::rejected` y no admite captura.

## Integración y corrección

Se parte de la copia SRC78 intacta del commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Se crean dos copias nuevas, con
2.960 archivos cada una. v1 añade core WorkerControl, métodos de integración y
cinco cambios en MTVU.h/cpp, VMManager.h/cpp y CMake; v2 corrige únicamente el
servicio propio. Las catorce copias anteriores y v1 se conservan completas.

VU_Thread publica una generación al entrar al worker; Reset no la recicla.
Agotamiento mantiene el control offline y rechaza observaciones; la cola puede
seguir ejecutándose. CPU solicita desde una frontera válida y pausada; su token
es de propiedad exclusiva de ese actor. Se publica request antes de NotifyOfWork
directo, sin KickStart, reserva de paquete ni cambios en WorkSema. Las consultas
de estado y generación usan los atómicos de WorkerControl.

ExecuteRingBuffer atiende control al terminar el lote despertado, incluido un
lote vacío. Conserva el orden de Execute, FinishGSPacketMTVU, semaXGkick.Post,
ciclos y CommitReadPos. Mientras held espera ControlWakeup; un plazo local de
50 ms sirve para reconsultar el estado y no libera permisos. Stop precede a Kill,
reintenta colisiones y espera si el token permanece retenido.

**Corrección v2:** la consulta vacía del while puede preceder a una publicación
CPU seguida de request. El servicio adquiere el token y vuelve a consultar la
cola antes de acknowledge. Esa adquisición ordena las publicaciones anteriores
a request. Si hay datos, retorna sin acusar; el aviso WorkSema pendiente permite
procesarlos en la siguiente vuelta. Un caso determinista fuerza ese intervalo;
eliminar la reconsulta reproduce el bloqueo por acuse prematuro en ese caso.

BeforeObserverProducer cancela el token VU antes de los productores CPU ya
instrumentados, incluidos Open/Close/Reset. StopObserverPineDrain también lo
cancela antes de las transiciones existentes. La cancelación aislada es necesaria
mientras el coordinador global todavía no posee workers. No certifica llamadas
arbitrarias de otros hilos ni la exclusión global. El orden global release GS→VU
se integrará junto al coordinador; esta unidad retiene únicamente VU.

La separación de responsabilidades se conserva: WorkerControl gestiona estados,
el [adaptador propio](../../tools/observer/pcsx2/vu_control.inc) conecta vida/cola,
y VMManager valida el actor y cancela antes de sus efectos. Los canales y el
control sobreviven al hilo; el aviso al propietario queda coalescido, sin un
nuevo waiter CPU ni un segundo consumidor de WorkSema::WaitForEmpty.

## Validación final

El [probe propio](../../tests/fixtures/pcsx2-vu-control/README.md) ejecuta 37
fragmentos privados exactos. Usa WorkSema y KernelSemaphore Darwin/Mach reales,
WorkerControl y CpuBoundary reales, con std::thread y dobles de tipos/efectos.

| Comprobación | Resultado |
|---|---|
| Normal, quince escenarios | 15/15 |
| ASan/UBSan, quince escenarios | 15/15 |
| ThreadSanitizer, quince escenarios | 15/15 |
| MTVU, VMManager y MTGS, objetos ON/OFF | 6/6 |
| Mutaciones aisladas | 5/5 detectadas |

**45 ejecuciones finales**, 42 del bucle real y tres del servicio con una frontera
sintética para publication_gap. Cubren lote con comandos, NULL_PACKET/reserva,
acuse posterior a publicaciones, cancelación/plazo, ausencia de consumo bajo
held, cierre pendiente/retenido, shutdown directo, reinicio, actor/frontera/pausa,
agotamiento y dependencia de espacio GS. No hay informes de los sanitizadores.

Los negativos detectan acuse antes del drenaje y omisión de la espera held por
aserción; omitir despertar, cancelación CPU o reconsulta de cola produce el plazo
de tres segundos y cierre del grupo verificado por supervisor. Los binarios y
fragmentos mutados están separados de las copias de referencia.

La cola MTVU y sus cuerpos son reales, pero los efectos VU/GS son dobles: la
dependencia de espacio no ejecuta MainLoop GS ni su cola. semaXGkick.Post verifica
orden mediante un doble; no se afirma haber ejecutado ese semáforo original.
El caso de intervalo vacío usa directamente el servicio en un worker propio.
El timeout reproduce cancelación CPU explícita, sin ejecutar el coordinador.
Las rutas retry del core se conservan; no se fuerza su colisión en este lote.
Terminación abrupta, callbacks UI y VM completa continúan sin verificar.

## Custodia y reproducción

SRC80 se vuelve a auditar con hash idéntico
`4a095314c1d62923b0d31f8af8d342444bb09ec3fedbd108668963c04ace2e5a`.
La auditoría SRC81 comprueba las dieciséis copias, fragmentos contra sus fuentes,
core/adaptador, objetos, logs, recibos y negativos. Dos informes idénticos
sustentan la [evidencia pública](../compatibility/vu-control-evidence.json).

Se preservan dos extracciones parciales fallidas por anclas incorrectas (enum y
calificador de WaitOnSize), un primer build del harness sin `<cassert>`, y los
resultados v1 previos a descubrir la carrera. No son resultados de la versión
final. También se conserva un negativo neutralizado por la nueva defensa: adelantar
ServiceObserverControl ya no acusa con datos pendientes. El negativo final de
acuse prematuro elude explícitamente ese servicio. Las correcciones usan scripts,
fuentes, etapas y recibos nuevos.

Receta local final; prepare-v2 parte de la copia v1 preservada y los pasos de
preparación requieren destinos inexistentes. No reconstruir v1 con el adaptador
actual, que ya incorpora la corrección:

```text
rtk proxy .venv/bin/python build/f02-07-vu-control/prepare-v2.py
rtk proxy .venv/bin/python build/f02-07-vu-control/fragments-v4.py
rtk proxy .venv/bin/python build/f02-07-vu-control/compile_private-v2.py
rtk proxy .venv/bin/python build/f02-07-vu-control/run_probe-v4.py normal-native
rtk proxy .venv/bin/python build/f02-07-vu-control/run_probe-v4.py sanitize-native
rtk proxy .venv/bin/python build/f02-07-vu-control/run_probe-v4.py tsan-native
rtk proxy .venv/bin/python build/f02-07-vu-control/negative_controls-v3.py
rtk proxy .venv/bin/python build/f02-07-worker-boundary/audit.py f02-07-worker-boundary-v1-src81-custody.json
rtk proxy .venv/bin/python build/f02-07-vu-control/audit.py f02-07-vu-control-v1.json
rtk proxy .venv/bin/python build/f02-07-vu-control/audit.py f02-07-vu-control-v1-repeat.json
```

Apple Clang, x86_64/C++20, piso libre 10 GiB. Objetos: etapa máxima 1 GiB,
180 s por compilación. Probe: 256 MiB, build 120 s y caso 15 s. Negativos: 1 GiB,
120 s/build y 3 s/caso. Scripts y recibos locales permanecen excluidos de Git.
No se recompila la aplicación completa ni se modifica la instalada. CI pública,
runtime Nintendo y sus presets no cambian; CTest host y suite Python completa
no se repiten porque su core no cambia. Ruff, validación del repositorio y
whitespace se comprueban. No se ejecutan CI remota, build 3DS ni consola física.

## Siguiente tarea

**IW-GS:** integrar una generación por apertura GS exitosa, el servicio tras
lote/señales y antes de idle, liberar RingBufferBusy2 antes de held y resolver
stop antes de epílogos. Probar MainLoop con efectos dobles, apertura/cierre/fallo,
idle/mutex y objetos ON/OFF. Después **IW-COORD** conectará VU→GS, release GS→VU,
plazos, cancelación y UI. B3-B2 global, B3-B3c/CQ3-C, AD-3 y captura siguen abiertos.
