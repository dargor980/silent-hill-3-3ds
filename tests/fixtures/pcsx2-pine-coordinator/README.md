# Pruebas de coordinación PINE

`harness.cpp` contiene dobles y oráculos propios. Trece fragmentos del proveedor
se extraen a includes privados: inicialización/cierre CPU, Execute, DoLoadState,
estado por hilo, fábricas/API/sampler, ScopedGuard, puente PINE, run/pump, slot,
dispatcher y wake de Qt. El conjunto previo OFF usa nueve fragmentos y stubs
vacíos para APIs exclusivas de ON; no se publica código PCSX2 ni datos del juego.

Pasan 45 casos comunes en ON/OFF/ASan-UBSan/anterior OFF y 16 adicionales en
ON/sanitizadores. Los adicionales contienen cinco casos de frontera heredados y
once de coordinación: rechazos de requests, dispatch inline/encolado y ocho
recorridos del bucle completo con trabajo, descarte, cancelación, timeout,
cambio de generación, cambio de época VM, cierre CPU y request durante Running.

Los cuerpos seleccionados son reales; QEventLoop, QTimer, QMetaObject, auxiliares
de EmuThread, reset/destroyVM, dependencias VM y memoria siguen siendo dobles.
Los cambios de generación se estimulan mediante HostEpoch propio. Los cuerpos
completos de Initialize/Deinitialize de PINE no se ejecutan: sus nuevos hooks se
compilan y auditan en entrada. No se verifica recepción por socket ni join real.

`qt_event_loop.cpp` es otro probe propio enlazado a QtCore real: solicitud desde
callback y wake, ejecución de trabajo retenido, timeout, cancelación y destrucción
del contexto que retiene un callback. Cuatro escenarios se ejecutan en normal y
con ASan/UBSan sobre el código propio; la biblioteca Qt instalada no se recompila
con sanitizadores. Este probe no ejecuta EmuThread ni una aplicación PCSX2.

Los diez escenarios de `tests/cpp/test_pine_drain.cpp` entran en CTest y cobertura
CI. Los dos harness de esta carpeta requieren insumos privados y no entran en CI
pública. La comparación histórica utiliza funciones anteriores con bibliotecas
propias actuales y dobles; no compara binarios completos de PCSX2.
