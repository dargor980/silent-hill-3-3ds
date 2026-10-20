# F02.07 / LP-C — Frontera CPU fuera de actividad

Fecha: 2026-10-18. Fuente: SRC73. Contrato [CB01–CB08](../../schemas/cpu-boundary-v1.md).
Evidencia: [metadatos públicos](../compatibility/cpu-boundary-evidence.json).

## Resultado

El diagnóstico exige ahora una frontera explícita del bucle CPU exterior. La
condición anterior, estar fuera de Execute, también podía cumplirse durante una
carga/reset/configuración y no bastaba para acreditar ese punto de control.

`CpuBoundary` administra una frontera léxica y ámbitos de actividad. Entrar en
actividad, reentrar en la frontera o cambiar el estado online la revoca. Terminar
un callback no la rehabilita; hay que salir del ámbito exterior y comenzar otro.
No asigna memoria, espera ni toma locks. Pertenece al hilo CPU mediante un objeto
thread_local; sus ámbitos no son copiables ni movibles y se destruyen en orden
léxico. La responsabilidad de muestreo permanece separada de esta contabilidad.

La nueva copia privada abre la frontera al comenzar cada iteración exterior de
EmuThread::run y la revoca antes de exec/processEvents. También instrumenta
PumpMessagesOnCPUThread, que puede ejecutarse desde dentro de Execute. El sampler
rechaza una frontera ausente/revocada antes de leer configuración o punteros CPU.

| Entrada VMManager protegida | Alcance de este lote |
| --- | --- |
| Execute | Cuerpo ejecutado con dependencias dobladas, incluyendo reentrada y excepción |
| DoLoadState | Cuerpo ejecutado: replay rechazado, fallo de unzip, éxito, grabación y excepción |
| SetState, Initialize, Shutdown, Reset | Entrada auditada y unidad compilada ON/OFF |
| ApplySettings, ApplyCoreSettings | Entrada auditada antes de callbacks y cambios de configuración |
| DoSaveState, LoadState, LoadStateFromSlot, SaveState, SaveStateToSlot | Entrada auditada y unidad compilada ON/OFF |
| Internal::ClearCPUExecutionCaches | Entrada auditada y unidad compilada ON/OFF |

Son catorce ámbitos VM más tres ámbitos de despacho Qt. CPUThreadInitialize
activa el objeto solo al terminar correctamente; CPUThreadShutdown lo desactiva
antes de efectos. No cambia los avisos de época/continuidad de los lotes previos.

## Coordinación que sigue pendiente

La frontera no impide escrituras de otros hilos ni cierra PINE. No se ha conectado
un caller del cierre de SRC72. Tampoco se ha introducido un request de captura.
PINE, GS/VU, RDebug y otros escritores conservan sus condiciones sin acreditar;
VIF dinámico continúa incumpliendo el perfil. Ningún modo obtiene admisión global.

El contrato fija el orden futuro: frontera CPU, cierre PINE, consultas, exclusión
de productores, drenaje VU, drenaje GS y revalidación. Si queda un callback CPU
anterior, se debe ceder al bucle exterior y perder la frontera actual. El cierre
PINE podrá conservarse entre iteraciones, pero no el permiso de frontera. Falta
implementar el despertar estando pausado y evitar Execute durante ese drenaje.
También falta cubrir el fast path de RunOnCPUThread(block=true): puede invocar
un callback directamente sin pasar por los tres pumps instrumentados. Se requiere
revocar antes de ese callback cuando se conecte la operación coordinada.
WaitVU/WaitGS bloquean y no cierran productores; no se conectan como atajo.

## Validación y custodia

Proveedor fijado: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Se conservan las
nueve copias privadas anteriores y se añade otra con 2.953 archivos. El parche
cambia VMManager.cpp/.h, QtHost.cpp, las dos listas CMake y añade los dos archivos
propios. El CMake público anterior tiene snapshot; los hashes históricos se
verifican contra sus versiones correspondientes.

Compilan cuatro objetos reales: VMManager y QtHost en ON/OFF, con Apple Clang 21,
x86_64, C++20, ThinLTO y SDK explícito. Los símbolos de frontera están ausentes
en OFF. Se regeneran los dos moc_QtHost con el moc instalado para la copia nueva.
No se ha reconfigurado/enlazado la aplicación completa ni ejecutado Qt real.

Se conserva un primer intento de preparación rechazado antes de copiar fuentes
por una coincidencia no suficientemente específica. También se conserva el fallo
inicial de QtHost: el moc histórico incluía la cabecera de la copia anterior y
producía definiciones duplicadas. Regenerar moc corrigió ese insumo; no se
modificaron las cabeceras históricas ni se desactivaron diagnósticos del compilador.

El [harness](../../tests/fixtures/pcsx2-cpu-boundary/README.md) pasa 45 casos
comunes en ON, OFF, ASan/UBSan y funciones anteriores OFF, con resumen de efectos
`df4cc8cbdcf04c69`. ON y sanitizadores pasan otros cinco casos de frontera.
Incluye cuerpos reales seleccionados y dependencias dobladas; Reset/destroyVM
en el bucle Qt son dobles. No equivale a cargar un estado ni ejecutar una VM.

Los nueve escenarios portables nuevos se integran en los presets y en el job de
cobertura existente. Pasan **100 pruebas CTest por configuración**: Debug,
Release y ASan/UBSan, sin fallos ni omisiones. LLVM mide **100 % de líneas y
ramas instrumentadas** de cpu_boundary.cpp y su cabecera (10 y 4 ramas).
El gate sigue en 80 %. No se repite la suite Python completa porque no cambia su
código; su último resultado pertenece a SRC72. CI remota/GCC y build 3DS no se
han ejecutado en este lote.

Dos auditorías iguales verifican fuentes, scopes, snapshots, objetos, moc,
fragmentos, ejecutables y recibos: **18.258 bytes**, SHA-256
`26a111fd8386161895c13fbd21f981b6dce04bb06fcac93ae695e250d741df09`.

CB-T1–T4 completan la frontera léxica de CQ-1. CQ-1 sigue parcial respecto al
coordinador operativo; CQ-2 deberá consumir el cierre PINE sin bloquear su cola
CPU ni permitir Execute durante el drenaje. CQ-3/CQ-4, AD-3/AD-4, LG-I3–I4,
LP-D y F02.07/Q05/G02 permanecen abiertos. No se ha validado ejecución en consola.
