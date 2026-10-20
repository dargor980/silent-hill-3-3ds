# F02.07 / LP-C — Barrera cooperativa de PINE

Fecha: 2026-10-18. Fuente: SRC72. Contrato [PE01–PE09](../../schemas/pine-exclusion-v1.md).
Evidencia: [metadatos públicos](../compatibility/pine-exclusion-evidence.json).

## Resultado y alcance

`CooperativeGate` permite cerrar la entrada de solicitudes PINE y consultar su
drenaje sin esperar trabajadores. Cada ParseCommand admitido posee una reserva
compartida hasta terminar sus efectos y destruir todos los callbacks derivados.
Las entradas posteriores reciben IPC_FAIL antes de ejecutar el paquete.

Una reserva sobrevive al retorno del parser, a respuestas tempranas y al timeout
del observador. Guardado/carga conservan la reserva en sus callbacks CPU; el
callback de error de guardado la conserva también si el trabajo ZIP lo retiene.
El adaptador propio pasa la reserva al callback de Completion. Descartar una
cola libera las reservas al destruir su última copia.

El cierre RAII es exclusivo y no copiable/movible. `poll` distingue rechazo,
drenaje, retenido, timeout y cancelación. El timeout **no reabre** por sí solo;
cancelación/destrucción reabre una vez. Un cierre competidor no libera el ajeno.
Capacidad agotada o falta de memoria al crear una reserva rechazan la entrada.

**No hay coordinador productivo de cierre ni captura real.** La API de cierre
solo se ejecuta en el harness; las reservas sí están conectadas al parser de la
nueva fuente privada. La admisión SRC71 no cambia: PINE, GS/VU y otros escritores
siguen sin una exclusión global acreditada.

## Orden, propiedad y SOLID

La puerta solo administra contabilidad, plazo y propiedad. Work es un token opaco
copiable que prolonga una operación ya admitida; no concede nuevas entradas.
Closure pertenece a un único hilo y el gate debe vivir más que todos sus tokens.
El parser/dispatch traducen esos ámbitos a operaciones del proveedor; la guardia
de continuidad, época y diagnóstico conservan su código previo.

El mutex interno se mantiene únicamente al actualizar/consultar contadores y
propiedad. Ningún callback, escritura, despacho o espera CPU/GS se ejecuta con
ese mutex retenido. La publicación de un efecto anterior se comprueba después
de observar cero reservas mediante el mismo mutex. Los trabajadores admitidos
pueden ejecutarse concurrentemente; la puerta no los serializa entre sí.

La inspección de QtHost confirma que RunOnCPUThread encola por defecto y que el
CPU procesa eventos también estando pausado. Un coordinador que bloquee ese
hilo esperando el drenaje impediría terminar trabajos que ya están en su cola.
La API nueva permite devolver el control y consultar después; no implementa
esa coordinación ni invoca PumpMessages de forma reentrante.

| Ruta | Tratamiento | Evidencia pendiente |
|---|---|---|
| PINE directo y paquete con error parcial | Reserva del ParseCommand completo | Recepción y envío por socket real |
| LoadState encolado | Copia de reserva hasta destruir callback CPU | Carga real y transiciones de VM |
| SaveState encolado | Copias en callback CPU y error retenido por ZIP | Worker ZIP real y callbacks posteriores |
| Observador con espera agotada | Callback CPU conserva reserva aunque el parser termine | Coordinación con extremos/captura real |
| PINE detenido o reiniciado | El gate no usa s_end como prueba de drenaje | Ciclo de vida completo del servidor |
| GS/VU, depurador y otros escritores | Sin cambio, permanecen desconocidos | AD-2/EX-1,3,4 |

## Fuentes y validación

Proveedor fijado: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Se crea otra copia
privada con PINE.cpp/.h, lista CMake y adaptador propio actualizados. Todas las
copias previas permanecen intactas. Se conservan snapshots del CMake público y
del adaptador anterior; no se sustituyen hashes históricos por los nuevos.

Compilan **cinco objetos reales**: PINE y VMManager en ON/OFF, más el adaptador
ON. Apple Clang 21, x86_64, C++20, ThinLTO y SDK explícito. OFF no incorpora la
barrera. No se configura ni enlaza de nuevo la aplicación PCSX2 completa.

El [harness](../../tests/fixtures/pcsx2-pine-exclusion/README.md) aprueba 44 casos
comunes en cuatro modos con resumen `38044f6443d78e6d`, y trece casos de exclusión
en ON/ASan-UBSan. Prueba las funciones seleccionadas con dobles explícitos y
hilos propios. FromSpan usa un doble con memcpy; el helper desalineado original
queda fuera de esta validación. No se ejecutan sockets, Qt ni estados del juego.

Diez pruebas portables comprueban propiedad, reservas compartidas, descarte,
contendientes, cancelación, agotamiento, timeout, unwinding, publicación entre
hilos y fallo de asignación. La última vive en un proceso separado con un
operador new de prueba; no introduce hooks de fallo en código productivo.

La regresión aprueba **91 pruebas C++ por configuración** (Debug, Release y
ASan/UBSan) y **3.096 pruebas Python**, sin fallos ni omisiones. LLVM mide 100 %
de líneas y ramas instrumentadas de cooperative_gate.cpp (16 ramas) y 100 % de
líneas de su cabecera (sin ramas). Esa medición usa los nueve escenarios del gate;
la inyección de bad_alloc se verifica adicionalmente en los tres presets. No es
cobertura de PCSX2 completo ni una prueba de todos los interleavings posibles.
Python mantiene 5.303/5.348 líneas (99,16 %) y 1.449/1.482 ramas (97,77 %).
Los gates permanecen en 80 %; Ruff, formato de 137 archivos, comprobaciones del
repositorio y `git diff --check` pasan.

Las dos auditorías son idénticas: **14.474 bytes**, SHA-256
`a95fb66ce734534dd0c42e633e85524e72eb1e4c6aeb8b86e56ecb0626edb61e`.
Comprueban copias privadas, inputs de SRC65–SRC71, el par original del adaptador,
snapshots, parche, objetos, fragmentos, ejecutables y recibos supervisados.
Los tests nuevos se integran en presets host y cobertura CI; el harness privado
no se publica en CI. Build remoto, consola y ejecución de una VM permanecen pendientes.

## Siguiente tarea: coordinador CPU y drenaje GS/VU

1. Fijar una frontera CPU fuera de Execute y de transiciones, con máquina de
   estados y cancelación; permitir progreso de los callbacks ya admitidos sin
   activar CPU o escritores nuevos durante el cierre.
2. Bloquear productores, drenar VU y luego GS sin mantener un lock que necesiten
   esos trabajadores. Rechazar rutas todavía no inventariadas, incluido VIF
   dinámico. Integrar el cierre PINE bajo este propietario; no esperar en un loop
   bloqueante ni promover por sí solo su estado retenido a admisión global.
3. Probar callbacks tardíos, cierre/reinicio PINE, timeouts y reentrada durante
   transiciones. Medir el coste de las reservas en una aplicación completa.
4. Solo después unir perfil/sesión/época/anclas y extremos en AD-3/LG-I3–I4.

PE-T1–T4 cierran este lote; AD-2/EX-2 sigue parcial hasta integrar el coordinador
y sus pruebas de servidor. EX-1,3,4, AD-3–AD-4, LP-D y F02.07/Q05/G02 siguen abiertos.
