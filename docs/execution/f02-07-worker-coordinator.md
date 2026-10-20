# F02.07 — Coordinador conjunto VU/GS (SRC83)

Fecha: 2026-10-18. Implementa IW-COORD1–3 con el alcance de integración privada
y pruebas de cuerpos exactos descrito aquí. La admisión global sigue vacía y no
se habilita captura. El contrato es [WCJ01–WCJ10](../../schemas/worker-coordinator-v1.md).

## Cambio y propiedad

WorkerDrain implementa EffectDrainPort y depende de dos WorkerPort. RetainedDrain
mantiene CPU/PINE/épocas; el coordinador fija ambas generaciones y solicita VU.
Solo después del acuse VU solicita GS. Cada consulta revalida vida/estado/plazo;
un fallo conserva los tokens hasta que el propietario los retire GS → VU antes
de reabrir PINE. La liberación también cubre una sola solicitud aceptada.

Los IDs globales de 64 bits no se truncan: se asignan tickets de 29 bits con
presupuesto monotónico, sin reiniciarlo por sesión. Un worker offline no se omite.
Un token de diagnóstico que choque provoca rechazo; no se sustituye al propietario.

Una nueva copia privada conserva las diecisiete anteriores. Cambia VMManager,
su cabecera, CMake y el bloque de despacho QtHost; añade núcleo/cabecera y dos
adaptadores propios. No modifica WorkerControl ni los adaptadores VU/GS previos.
StopObserverPineDrain retira primero el propietario global y después cualquier
token diagnóstico independiente. BeforeObserverProducer conserva ese orden.

Durante la fase PINE se conserva el bombeo Qt anterior. Tras comenzar efectos,
CPU espera un intervalo nominal de 1 ms sin despachar aplicación y vuelve a
consultar el plazo. La API interna mantiene el máximo de cinco segundos. No se
añade una espera síncrona desde UI. La planificación del SO y rutas UI/CPU ajenas
no tienen una garantía nueva de latencia. Los avisos de cada worker siguen siendo
pistas coalescidas; este coordinador consulta periódicamente y no los consume.

## Validación

- 154 CTest por preset Debug, Release y ASan/UBSan: 462 resultados correctos.
  Incluyen 16 escenarios nuevos del núcleo y el resto del repositorio.
- Los 16 escenarios del núcleo también pasan con TSan. Cubren IDs grandes,
  agotamiento, cambios de generación/época, token perdido, rechazo parcial,
  cancelación concurrente con acuse y dependencia de una cola sintética llena.
- 20 escenarios conjuntos × normal/ASan-UBSan/TSan: 60 ejecuciones correctas.
  Ejecutan ambos bucles del proveedor y 64 fragmentos exactos, con los límites
  de [la fixture](../../tests/fixtures/pcsx2-worker-coordinator/README.md).
- Ocho objetos ON/OFF: MTVU, MTGS, VMManager y QtHost; moc regenerado por modo.
  El núcleo nuevo también se compila/enlaza en los tests y el probe conjunto.
- Seis controles negativos detectan orden de release, fuga parcial, cambio de
  generación seguido indebidamente, truncamiento del ID, solicitud GS temprana
  y regreso prematuro al despacho Qt.

El ringbuffer GS lleno se consume por MainLoop real mientras VU depende de él.
FinishGSPacketMTVU y los efectos renderer son dobles. Los casos Qt ejecutan el
bloque exacto del bucle con QEventLoop y entrega real a otro QObject, sin el
EmuThread completo. PINE usa CooperativeGate real con una fuente doble, sin
servidor/socket. Los semáforos WorkSema/Mach son reales; UserspaceSemaphore y el
wrapper de hilo son dobles. No hay VM conjunta ni ejecución de SH3 en Nintendo.

El pipeline host existente descubre los 16 tests nuevos en CMake. No se ejecutó
CI remoto, suite Python completa ni otra compilación Nintendo en esta unidad.

## Custodia y correcciones de preparación

La evidencia SRC82 se reproduce con su hash histórico. Se conservan dieciocho
copias privadas, parches, objetos, snapshots del fixture, logs y recibos.
La primera extracción falló por omitir el prefijo inline de WaitOnSize; la segunda
fija la firma completa. La primera compilación del probe detectó una ruta de
inclusión privada ausente; la segunda pasa. El primer mutante de generación
alteraba también la preparación inicial: se limitó la mutación al poll y se
repitió la serie en directorios nuevos. Los intentos anteriores siguen intactos.
El mutante de despacho falla en la aserción esperada; su salida atraviesa el
destructor de un worker deliberadamente bloqueado y requiere la terminación
del grupo por el supervisor. Se verificó la limpieza del grupo. Los cinco
negativos del núcleo terminan con error de aserción sin vencer su plazo.
Un script auxiliar de TSan falló antes de compilar por una variable ausente;
la ejecución corregida se guardó en otra etapa y los 16 escenarios pasaron.

## Continuación

IW-COORD cierra el puente CPU/VU/GS probado con cuerpos y dependencias controladas.
B3-C/B4 y CQ3-C/D conservan trabajo de frontend completo, escritores restantes y
rutas síncronas. La prueba de cola llena no cubre todas las entradas ReserveSpace.
El siguiente trabajo es verificar las dependencias UI ↔ CPU ↔ GS con despacho
real y cancelación antes de callbacks que puedan producir, y preparar el enlace
del frontend completo conservando la política de rechazo.
