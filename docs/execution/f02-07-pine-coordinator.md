# F02.07 / LP-C — Coordinación de drenaje PINE

Fecha: 2026-10-18. Fuente: SRC74. Contrato [PC01–PC09](../../schemas/pine-coordinator-v1.md).
Evidencia: [metadatos públicos](../compatibility/pine-coordinator-evidence.json).

## Resultado

Se conecta BeginObserverExclusion a un coordinador del hilo CPU. La solicitud
queda pendiente hasta una frontera exterior válida, con pausa y épocas VM/PINE
coincidentes. Durante el drenaje se conserva el cierre y se procesan eventos;
el bucle Qt no llama Execute para avanzar callbacks. La rama Running también
vuelve al bucle si se encoló un request durante processEvents.

El resultado interno solo declara drenaje PINE. No se añade un comando de red,
botón ni caller del request dentro de la aplicación: los requests se activan en
las pruebas. La ruta compilada sí contiene el caller del cierre y su conducción
desde el bucle. No se ha enlazado ni ejecutado una nueva aplicación PCSX2.

## Propiedad, estados y SOLID

PineDrain administra request, identidad, plazo y estado. BarrierSource aporta una
única operación de cierre; el adaptador del proveedor la traduce a PINE. Una Lease
no movible dentro de optional conserva el cierre sin asignación dinámica propia.
El controlador pertenece al CPU, no toma locks adicionales ni invoca callbacks.
La puerta conserva su mutex breve de contabilidad; nunca cruza un despacho Qt.

| Estado/evento | Efecto |
| --- | --- |
| submit válido | Guarda ID creciente, épocas no nulas y plazo; todavía no cierra PINE |
| queued en frontera válida/pausada | Adquiere cierre; pasa a draining o held |
| draining | Conserva cierre, rechaza entradas nuevas y cede a eventos |
| held | Revalida; termina como completed, exclusivamente para PINE |
| Epoch cambiada, frontera o pausa perdida | Invalida sin reabrir automáticamente |
| Plazo vencido/cancelación | Terminal retenido hasta retire |
| retire/destrucción/cierre CPU | Invalida antes de destruir Lease y reabrir |

VMManager rechaza llamadas de otros hilos y limita el timeout del request a
1–5.000 ms. IDs no crecientes y solicitudes simultáneas se rechazan; el contador
de IDs no se reinicia con la VM. El resultado conserva ID y estado del último
intento retirado, por lo que debe correlacionarse por ID. Encolar desde un callback
no concede frontera; admitir y completar siempre requieren otra comprobación.

Qt usa un timer local de 1 ms para despertar el exec pausado mientras quedan
reservas. El timer se destruye al salir, también si otro evento hizo quit. No se
bombea desde una frontera válida ni se espera Completion síncronamente. El slot
runOnCPUThread y el fast path inline revocan antes de ejecutar el callback.
Un callback que bloquee puede retrasar la consulta del plazo: no es un límite
duro de tiempo de ejecución ni una prueba universal de ausencia de deadlocks.

PINE incrementa una generación host no restaurable al entrar en Initialize y
Deinitialize, incluso en intentos fallidos. Cambiarla invalida el intento en el
próximo paso; IsInitialized no se usa como prueba de join o cola vacía. Los hooks
se compilan/auditan y la invalidación se prueba con generaciones controladas;
el ciclo completo del socket/servidor sigue pendiente.

## Validación

Nueva copia privada del proveedor fijado
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`: 2.955 archivos, siete archivos del
proveedor modificados y dos propios añadidos. Se conservan las diez copias previas
y el snapshot del CMake público SRC73. No hay contenido del juego en el reporte.

Compilan **seis objetos reales ON/OFF**: VMManager, PINE y QtHost, con Apple Clang
21, x86_64, C++20, ThinLTO y SDK explícito. moc_QtHost se regenera en ambos modos.
Los símbolos del coordinador/generación están ausentes en OFF. Se reutiliza el
compile database fijado, adaptando rutas y flags; no es una configuración nueva
ni un enlace completo. La integración se limita al frontend Qt; GSRunner no tiene
implementado el nuevo wake y queda fuera del target soportado por este lote.

El [harness del proveedor](../../tests/fixtures/pcsx2-pine-coordinator/README.md)
pasa **45 casos comunes** con efectos `df4cc8cbdcf04c69` iguales en cuatro modos,
y **16 adicionales** ON/ASan-UBSan. El bucle y dispatcher seleccionados son cuerpos
reales con dobles; no se afirma ejecución de una VM o Qt real en ese harness.

El probe separado con **QtCore 6.11.1 real** pasa cuatro escenarios en normal y
cuatro con ASan/UBSan sobre el código propio. En cada corrida observó 30 vueltas,
34.595/34.695 microsegundos totales, incluyendo un timeout intencional de 30 ms.
Es una medida del ensayo, no del coste de PCSX2 ni del rendimiento del juego.

Los diez tests portables nuevos llevan la regresión a **110 CTest por preset**
(Debug, Release y ASan/UBSan), sin fallos ni omisiones. LLVM mide 100 % de líneas
y 60/60 ramas instrumentadas en pine_drain.cpp y 100 % de líneas en su cabecera
(sin ramas). El gate conserva 80 %. El job host/cobertura existente recoge los
tests nuevos; CI remota/GCC y build 3DS no se ejecutan aquí. La suite Python
completa no se repite porque no cambia su código; su último resultado es SRC72.

Dos auditorías idénticas verifican las once copias, snapshots, parche, scopes,
objetos, moc, fragmentos, ejecutables, recibos y QtCore del probe: **22.800 bytes**,
SHA-256 `ac4fd51ef450c136235c917a0015f1c964bbbbc49e9c492da086904654323c07`.

## Siguiente unidad

PC-T1–T4 completan la coordinación interna acotada. CQ2-A/B están implementadas;
CQ2-C/D siguen parciales por servidor real, enlace y coste de la aplicación.
El cierre se retira al concluir el diagnóstico PINE; CQ-3 deberá conservarlo
durante exclusión de productores y drenaje VU→GS, con cancelación y revalidación.

Siguen sin acreditar RDebug, GS/VU y otros escritores. VIF dinámico permanece
incompatible. La admisión no cambia, no se arman extremos ni se captura memoria.
CQ-4, AD-3/AD-4, LG-I3–I4, LP-D y F02.07/Q05/G02 continúan pendientes.
