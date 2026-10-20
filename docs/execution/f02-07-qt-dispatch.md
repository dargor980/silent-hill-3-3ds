# F02.07 — Entradas y bombeo Qt (SRC78)

Fecha: 2026-10-18. Completa **B3-A / QD-T1–T3** del
[contrato EARS QD01–QD08](../../schemas/qt-dispatch-v1.md). Se protegen los slots
CPU restantes y se cancela la fase posterior a PINE antes de bombear Qt.
**B3 global sigue parcial:** el canal separado se ha elegido, pero B3-B todavía
no lo implementa. No hay acuses reales de retención GS/VU ni captura habilitada.

## Implementación e inventario

Nueva copia privada desde SRC77, proveedor fijado en
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Cambia únicamente
`pcsx2-qt/QtHost.cpp`; se conservan los 2.957 archivos anteriores.
Parche SHA-256 `871a6f8b1dc5cb9b7545e9de3bdd905862d6c954088c66ba02df95686ab1c65c`.

Se reutiliza BeforeObserverProducer y el propietario RetainedDrain. No se añade
otra autoridad de estado, locks o reservas de ringbuffer. En CPU, si ya empezó
la fase de efectos, el intento se cancela y retira antes de la instrucción
original. PINE sigue cerrado durante release. Durante su drenaje previo se
permite el trabajo; en otro hilo el aviso no toca el propietario CPU.

Hay **48 puntos nuevos**: 38 slots, seis ayudantes, Host::PumpMessagesOnCPUThread
y tres despachos en run. El slot RunOnCPUThread ya estaba protegido: los 39 slots
públicos/privados declarados en QtHost.h quedan inventariados por nombre y hash.
La auditoría exige una guardia al inicio de cada cuerpo, incluido el retorno
que reenvía a CPU. Las mismas entradas pueden recibir llamadas directas.

| Familia | Entradas y primeros efectos | Hilo / decisión |
|---|---|---|
| VM | startVM, resetVM, setVMPaused, shutdownVM, stopInThread; flags y salida del event loop antes de VMManager | CPU protegido; reenvío UI conserva su conexión |
| Estados | loadState, loadStateFromSlot, saveState, saveStateToSlot; diagnóstico, callbacks y señales | CPU protegido; duración original de argumentos |
| Ventana | start/stopFullscreenUI, toggle/setFullscreen, setSurfaceless, onDisplayWindowResized, redrawDisplayWindow, requestDisplaySize | CPU protegido antes de flags, ImGui y MTGS |
| Configuración y medios | loadSettings, checkForSettingChanges, applySettings, reloadGameSettings, updateEmuFolders, toggleSoftwareRendering, changeDisc, setELFOverride, changeGSDump, reloadPatches | CPU protegido; locks ya adquiridos por un llamador requieren análisis de ese recorrido |
| Input y foco | reloadInputSources/Bindings/Devices, closeInputSources, enumerateInputDevices/VibrationMotors, onApplicationStateChanged, doBackgroundControllerPoll | CPU protegido antes de input, flags de foco y señales; se conservan destinos/conexiones existentes |
| Captura GS | queueSnapshot, beginCapture, endCapture | CPU protegido antes de construir/publicar callbacks y esperar GS |
| Ayudantes | destroyVM; create/destroy/start/stopBackgroundControllerPollTimer | CPU protegido antes de campos, timers y conexiones |
| Métricas | updatePerformanceMetrics | Protección solo CPU; también llega desde GS por PerformanceMetrics::Update → Host::OnPerformanceMetricsUpdated; ese camino no está excluido |
| Despacho existente | runOnCPUThread y fast path Host::RunOnCPUThread | Guardias SRC76 preservadas; no hay cambios en su entrega |
| Bombeo | run: pending, paused/shutdown y running; Host::PumpMessagesOnCPUThread | Cancelación antes de Activity, timer y exec/processEvents; cubre receptores distintos de EmuThread y sus filtros durante estos bombeos |

Rutas revisadas que **no** se convierten en excluidas:

- AcquireRenderWindow/ReleaseRenderWindow y connectDisplaySignals llegan desde
  GS; MainWindow conecta adquisición/liberación con BlockingQueuedConnection.
  UI debe poder avanzar mientras GS la necesita. La retención requiere CQ3-C.
- Métricas GS mutan campos y encolan actualizaciones UI. Se trazó la llamada
  desde GSRenderer.cpp y PerformanceMetrics.cpp; un aviso TLS CPU es inerte allí.
- EmuThread::start/stop se ejecutan en UI; stop bombea UI mientras espera CPU.
  Constructor/destructor y cambios de afinidad requieren ciclo de vida completo.
- connectSignals pertenece al arranque; shouldRenderToMain consulta configuración;
  señales Host→UI, diálogos, filtros UI y otros QObjects fuera de los bombeos
  revisados no reciben una garantía global por esta instrumentación.
- QtProgressCallback tiene su propio QThread. Ni ese hilo, RDebug ni otros
  escritores se convierten en admitidos. Una llamada directa con efectos previos
  al cuerpo protegido necesita una frontera previa en su llamador.

Cancelar antes del bombeo es deliberadamente conservador: una fase posterior
pendiente se retira antes del timer local de 1 ms. Este recorrido **no permite
retener workers entre iteraciones de Qt**. El puerto productivo sigue devolviendo
rejected, por lo que no se finge progreso ni se habilita observación.

## Canal elegido y trabajo siguiente

B3-B usará control separado por trabajador, fuera de la cola de datos, con un
mecanismo de despertar que no publique AsyncCall. CPU solicita/libera; cada
trabajador acusa con ID y generación solo después de acabar sus efectos y poder
permanecer sin producir. El contrato detalla estados/concurrencia que todavía
hay que fijar e implementar. La espera CPU de control no bombeará Qt arbitrario
con trabajadores retenidos; si necesita hacerlo cancelará primero.

Quedan: probar publicación/acuse/cancelación concurrente y reinicio, despertar sin
pérdidas, liberación GS antes de VU y cola llena. CQ3-C integra los puntos reales
VU/GS e idle; B3-C/B4/CQ3-D/CQ-4 prueban dependencias inversas, servidor y frontend
completos, cierre y coste. Ningún estado del puerto simulado acredita esos pasos.

## Validación ejecutada

- QtHost real compila ON/OFF con moc regenerado en cada modo; Apple Clang,
  x86_64/C++20 y configuración local fijada. No se enlazó la aplicación completa.
- **112 casos por modalidad** ON, OFF, ASan/UBSan y SRC77 OFF. Digest de efectos
  idéntico `82bcb24eba918bac`; QtCore real **6.11.1** en las cuatro ejecuciones.
- 80 casos: ocho entradas × cinco fases × entrega directa/encolada. Se verifica
  release antes de flags/efectos y se conserva el comportamiento del cuerpo.
- 20 casos: receptor QObject ajeno, timer cero, contexto destruido y bombeo
  anidado. Diez casos: RunOnCPUThread inline/encolado, payload y destrucción;
  dos casos: reenvío real desde un std::thread a la afinidad CPU de Qt.
- Dos controles negativos compilan y fallan en la aserción prevista al retirar
  la guardia de setFullscreen o de PumpMessagesOnCPUThread. Mutaciones aisladas;
  la copia auditada no se modifica.

Se ejecutan **nueve entradas nuevas** (ocho métodos y Host Pump) más cinco cuerpos
previos del puente/despacho: catorce fragmentos exactos privados por copia.
Las otras 36 entradas y tres puntos del bucle se compilan y auditan. El receptor
es un QObject propio con afinidad Qt, no EmuThread completo. QtCore y los
controladores propios son reales; VM/GS/input/configuración/puerto son dobles.
No se ejecuta un socket PINE, worker, ringbuffer ni VM de PCSX2. La biblioteca
QtCore instalada no se recompiló con sanitizadores; se instrumentó el harness
compuesto y los controladores propios.

El primer script de preparación confundió sangrías de cuatro/cinco tabs y se
detuvo **antes de crear la copia**; se corrigió anclando la línea completa. El
primer harness no compiló por llamar `slots` a una función propia, colisionando
con la macro Qt. Se renombró y se guardaron fuente, script, log y recibos iniciales;
las ejecuciones finales usan v2. No se cambió el proveedor para corregir el fixture.

La CI pública y CMake no cambian. No se repitieron los 120 CTest por preset de
SRC76, la suite Python completa, CI remota ni build 3DS; el código portable no
cambió. Ruff, controles de repositorio y whitespace se ejecutaron localmente.

## Custodia y reproducción

Se verifican las catorce copias privadas, hashes de fuentes revisadas, hooks,
parche reversible, objetos, moc, fragmentos, QtCore y ejecutables. La auditoría
SRC77 se repite con su hash histórico intacto. Dos auditorías SRC78 idénticas
sustentan la [evidencia pública](../compatibility/qt-dispatch-evidence.json).
No contienen código del proveedor, rutas privadas ni originales del juego.

Receta local; preparación exige destinos nuevos y no debe sobrescribir copias:

```text
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/prepare.py
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/compile_qt.py
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/make_harness.py
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/run_harness.py on
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/run_harness.py off
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/run_harness.py sanitize
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/run_harness.py baseline
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/negative_controls.py
rtk proxy .venv/bin/python build/f02-07-producer-entry/audit.py f02-07-producer-entry-v1-src78-custody.json
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/audit.py f02-07-qt-dispatch-v1.json
rtk proxy .venv/bin/python build/f02-07-qt-dispatch/audit.py f02-07-qt-dispatch-v1-repeat.json
```

Scripts y recibos completos quedan en build/reports locales excluidos de Git;
fuentes, includes y binarios quedan privados. Compilación/probes con supervisión:
piso libre 10 GiB, etapa 1 GiB, compilador 180 s, ejecución 30 s. Esto no equivale
al presupuesto ni a una validación del build completo o del runtime Nintendo.
