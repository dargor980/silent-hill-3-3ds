# Vinculación runtime revocable — RB v1

Historia: como investigador, necesito que una observación nativa deje de ser
utilizable cuando el coordinador retire su alcance runtime, sin esperar IO desde
CPU ni convertir un snapshot de configuración en permiso de captura.

## Requisitos EARS

- **RB01:** CUANDO CPU active un alcance, DEBERÁ aportar ID propio no reutilizable,
  deadline local futuro de hasta 5 s, épocas host/PINE/VU/GS válidas y hechos AP
  tomados bajo sus guardias. CPU, frontera, pausa y retenciones PINE/VU/GS DEBERÁN
  estar satisfechas; hechos restantes podrán ser desconocidos o violados.
- **RB02:** CUANDO falte el alcance o cualquier precondición estructural, DEBERÁ
  rechazar sin crear una observación vinculada. Valores AP inválidos DEBERÁN
  normalizarse a desconocido, sin promoverlos a satisfecho.
- **RB03:** MIENTRAS el alcance esté activo, DEBERÁ conservar ID, deadline,
  épocas y hechos por valor. CPU DEBERÁ revalidarlos; un cambio observado,
  incluso seguido de regreso, DEBERÁ revocar permanentemente la instancia.
- **RB04:** CUANDO CPU vaya a retirar guardias o cambiar/destruir VM, DEBERÁ
  revocar antes del efecto. Revocar DEBERÁ señalar sin cerrar recursos, esperar
  al trabajador, hacer IO ni ejecutar callbacks. Una copia histórica SHALL NOT
  mantener autorización ni acceso a la VM.
- **RB05:** CUANDO DW compruebe su presupuesto, retire o confirme una entrega,
  DEBERÁ comprobar también la validez del alcance. Un alcance revocado o vencido
  DEBERÁ rechazar antes de publicar, conservando primera causa observada.
  Durante esperas internas, incluso sin solicitud pendiente, DEBERÁ consultar
  cada 20 ms nominales sin depender del polling del dueño. Esto SHALL NOT
  prometer latencia del SO ni interrumpir forzosamente un hijo bloqueado.
- **RB06:** CUANDO el trabajador componga inventario y runtime, DEBERÁ leer la
  misma vinculación antes/después, verificar presupuesto y no aceptar un hijo
  que ya aportase épocas o hechos runtime. Preparación, muestreo y limpieza del
  hijo DEBERÁN permanecer en el trabajador; no habrá referencias prestadas a VM.
- **RB07:** CUANDO se cierre, DEBERÁ separar revocación, finalización del trabajo,
  unión y cierre del canal. Un hijo bloqueado conservará limpieza pendiente;
  CPU SHALL NOT llamar a unión/destructor bloqueante ni esperar entrega de IO.
- **RB08:** CUANDO se valide, DEBERÁ cubrir cada gate/época, fronteras de plazo,
  cambio/regreso, cancelación por fase y entrega parcial, con hilos y trabajo DW
  reales. Las pruebas con snapshots locales SHALL NOT acreditar el adaptador
  PCSX2, las guardias de todos los escritores ni una VM en ejecución.

## Diseño

`DiagnosticValidity` es un puerto de consulta rápida sin espera, IO ni reentrada,
usado por DW junto con su presupuesto. `RuntimeDiagnosticBinding` conserva un
snapshot inmutable publicado por el dueño CPU; su causa de revocación es atómica.
El deadline del alcance también limita la sesión, incluso entre solicitudes.
Las consultas del trabajador no llaman al coordinador ni leen configuración VM.
La instancia es de un solo alcance; reactivarla es un error terminal. La no
reutilización de IDs entre instancias pertenece al contador del coordinador.

`RuntimeDiagnosticWorkFactory` decora una fábrica nativa: crea/prepara/muestrea/
cierra el hijo en el trabajador y añade exclusivamente una copia runtime validada.
El decorador es privado. Una función de composición pasa la misma vinculación a la fábrica y a DW, evitando
que validador y datos usen alcances distintos. El modo DW sin validador se conserva.

La fuente privada fijada completa/retira actualmente el drenaje al observar held
en `VMManager::Internal::PollObserverPineDrain`. RB-T2 deberá sustituir ese tramo
para el intento diagnóstico y revocar antes de `StopObserverPineDrain`/lifecycle.
No basta con leer generaciones dos veces: los hooks deben cubrir cambios entre
lecturas. El núcleo RB no prueba esa cobertura ni convierte bools en atestación.

## Tareas detalladas

- [x] **RB-T1 / DW-T3a** (SRC112): implementar validador revocable, snapshot y composición
  DW; verificar cada precondición y estado AP, plazos acumulados y revocación
  durante fábrica/preparación/muestreo/entrega; limpieza retenida, sanitizadores,
  cobertura y regresiones; incorporar los tests al pipeline nativo.
- [ ] **RB-T2 / DW-T3b:** adaptar el coordinador privado para conservar el intento
  mientras DW trabaja y entrega; muestrear hechos/épocas bajo CPU/PINE/VU/GS,
  mantener desconocidas rutas no acreditadas y revocar antes de cada retiro o
  transición. Probar cuerpos reales ON/OFF y generaciones/cambio/regreso.
- [ ] **RB-T3 / DW-T3c:** enlazar copia privada con hooks, contrastar con VM y
  callbacks tardíos, cierre y cada gate ausente; verificar cobertura de escritores
  y custodia. Solo esta evidencia podrá cerrar DW-T3; captura se evalúa aparte.

## Estado posterior: SRC113

- [x] **RB-T2 / DW-T3b:** completado por [RC01–RC08](runtime-coordinator-v1.md) y
  [SRC113](../docs/execution/f02-07-runtime-coordinator.md). El plan anterior queda
  como registro de SRC112. La copia nueva conserva la frontera y guardias durante
  el ticket, usa épocas/sampler privados y revoca antes de las transiciones cubiertas.
- [ ] **RB-T3 / DW-T3c:** enlace y conexión IO–CPU–DW, VM, callbacks tardíos,
  cobertura de escritores y custodia. DW-T3 y captura siguen pendientes.

## Desglose posterior de RB-T3: SRC114

- [x] **RB-T3a:** [RH01–RH08](runtime-handoff-v1.md) conecta despacho IO–CPU, ticket
  y cierre de DW con confirmación CPU de retirada. [SRC114](../docs/execution/f02-07-runtime-handoff.md)
  verifica cuerpos privados con dependencias declaradas y unidades ON/OFF.
- [ ] **RB-T3b / DW-T3c:** integrar socket/inventario nativo con el frontend,
  enlazar bajo IB02 y validar con VM lifecycle, callbacks tardíos y escritores.
  **RB-T3 y DW-T3 permanecen abiertos**, al igual que la admisión de captura.
