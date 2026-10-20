# F02.07 / LP-C — Propietario persistente del intento

Fecha: 2026-10-18. Fuente: SRC76. Completa **CQ3-B/B1**, tareas RD-T1–T3,
con entradas anticipadas para B3. Contrato [RD01–RD08](../../schemas/retained-drain-v1.md).
Evidencia: [metadatos](../compatibility/retained-drain-evidence.json).

## Resultado

RetainedDrain conserva el cierre PINE durante una fase posterior y hasta que
esta libera sus recursos. Vaciar PINE ya no completa el intento del proveedor.
La integración usa un puerto que rechaza la fase posterior porque aún no están
implementadas exclusión de productores y retenciones GS/VU. No concede captura
ni cambia las condiciones desconocidas o incompatibles del sampler.

Se añaden cancelación/retirada al entrar en catorce transiciones VM y una consulta
antes de los dos callbacks CPU ya instrumentados. Estos cambios preparan el
orden de liberación; **B2/B3 permanecen abiertos** por otros productores,
entradas Qt/UI y el canal de control de trabajadores.

## Estados, propiedad y SOLID

El controlador compone PineDrain sin modificar su implementación. EffectDrainPort
solo expone begin(request), poll(id), release(id), separando propiedad del intento
de la futura implementación de exclusión. Sus llamadas deben ser acotadas, sin
esperar CPU/UI, reservar colas de datos ni despachar callbacks de aplicación.
El puerto debe liberar preparaciones parciales, en orden GS antes de VU.

| Evento | Resultado |
| --- | --- |
| submit válido | Conserva ID creciente, épocas y plazo; no cierra inmediatamente |
| PINE draining | Conserva cierre, permite progreso de reservas previas; no llama begin |
| PINE held | Llama begin una sola vez; empieza a consultar la fase posterior |
| Puerto pending | Sigue draining y conserva cierre PINE |
| Puerto held | Revalida; held/completed ahora requieren ambas fases |
| Puerto rejected o valor desconocido | Terminal rejected; no sustituye barrera por éxito |
| Cambio de época/pausa/frontera o timeout | Terminal sin liberar implícitamente |
| Reentrada de step | Invalida; no libera mientras begin/poll siguen activos |
| cancel/complete | Publica terminal; conserva recursos hasta retire |
| retire/destructor | Libera fase posterior antes de retirar PINE; no admite retirada recursiva |

El ID permanece monótono a través del PineDrain compuesto. Los requests no se
reemplazan al reentrar; el puerto recibe el mismo ID para begin/poll/release.
La revalidación ocurre antes y después del puerto; completar vuelve a comprobar
las condiciones. El caller debe aportar épocas actuales: un snapshot pasado
como argumento no detecta por sí solo cambios posteriores. El driver obtiene
épocas de VM/PINE de nuevo antes de complete.

No hay asignación ni mutex propios del controlador. La puerta PINE conserva su
mutex breve. Un puerto bloqueado impediría observar puntualmente el deadline;
esta interfaz no convierte ese plazo en una interrupción forzosa.

## Integración del proveedor

Nueva copia privada a partir de SRC74: 2.957 archivos, cuatro archivos modificados
y dos propios añadidos. Parche SHA-256
`9f44b80983541574a1f9e97417c1315f8599da96271cf2bb46da818cfa05ba1c`.
Las once copias previas se conservan; el CMake público SRC74 queda en un snapshot.

VMManager reemplaza el propietario PineDrain por RetainedDrain, manteniendo los
nombres internos Queue/PollObserverPineDrain. ObserverEffectDrain devuelve
rejected; sus begin/release no retienen ningún trabajador. El bucle Qt conserva
el wake, timer y bypass de Execute. No se añade caller UI/red para el request.

Las catorce entradas VM cancelan/retiran antes de la actividad y de cualquier
statement original, incluidos retornos tempranos. El slot runOnCPUThread y el
fast path inline invocan BeforeObserverProducer antes del callback. Esa consulta
solo retira si comenzó la fase posterior: los callbacks que aún mantienen
reservas PINE pueden terminar y drenarlas. Los scopes de bombeo Qt no abortan
indiscriminadamente; hacerlo impediría avanzar el drenaje previo.

Esto no cubre todos los slots, productores de memoria ni la entrada directa UI
de LocaleChanged encontrada en SRC75. Tampoco implementa acuses, aparcamiento
de VU/GS o control de presentación ociosa. El puerto rechazado mantiene ese límite
explícito mientras B2/B3/CQ3-C están pendientes.

## Validación

- **120 CTest por preset** Debug, Release y ASan/UBSan, cero fallos/omisiones.
  Diez escenarios nuevos cubren fases, liberación, rechazo, épocas, timeout,
  cancelación, reentrada y destrucción. La fase pending/held usa un puerto propio.
- **Cuatro objetos reales ON/OFF:** VMManager y QtHost, Apple Clang 21, x86_64,
  C++20, ThinLTO y SDK explícito. Se regenera moc en ambos modos. Los símbolos
  nuevos están ausentes en OFF. Se reutiliza el compile database; no hay nueva
  configuración/enlace completo de PCSX2.
- **45 casos comunes** en ON/OFF/ASan-UBSan/anterior OFF, con digest de efectos
  `df4cc8cbdcf04c69` idéntico; **26 adicionales** en ON/sanitizadores.
  El [harness](../../tests/fixtures/pcsx2-retained-drain/README.md) ejecuta cuerpos
  reales con dobles. Solo Execute/DoLoadState se ejecutan entre las catorce
  entradas; las otras se compilan y auditan. La fase del puerto real se rechaza;
  no se ensaya pending/held de trabajadores reales.
- LLVM: retained_drain.cpp **70/73 líneas (95,89 %) y 55/58 ramas (94,83 %)**;
  cabecera 100 % de líneas, sin ramas. Supera el umbral de cobertura existente.

Las compilaciones y harness privados usan supervisión: reserva 10 GiB,
presupuesto 1 GiB, máximo 180 s por compilación y 30 s por ejecución. No hubo
intentos fallidos en este lote. No se repite la suite Python porque no cambia
su código. El CMake incorpora los tests al pipeline host/cobertura existente;
CI remota/GCC y compilación o ejecución 3DS no se realizan aquí.

La custodia SRC74 se vuelve a verificar. Sus únicos cambios de reporte son los
hashes del CMake actual en referencias históricas; no cambian fuentes privadas,
objetos ni resultados anteriores. El snapshot conserva el hash público previo.
También se verifican los inputs de SRC75. Dos auditorías SRC76 comprueban copias,
parche, scopes, fragmentos, objetos/moc, recibos, regresión y cobertura con salida
idéntica. Los reportes públicos no contienen rutas privadas ni originales del juego.

## Siguiente tarea

**CQ3-B/B2:** intervenir antes de efectos en productores, incluidos contadores
GIF y FIFO directo, y serializar la ruta UI de LocaleChanged. B3 completará
callbacks tardíos y un canal de control que progrese sin colas/locks bloqueados.
Después CQ3-C implementará los acuses VU→GS y B4/CQ3-D/CQ-4 verificarán la
integración completa. Servidor PINE real, Qt/VM completos, coste y AD-3 siguen
pendientes; no se acredita exclusión global ni se arma captura de memoria.
