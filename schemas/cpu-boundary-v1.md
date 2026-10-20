# CPU boundary v1 — CB01–CB08

Unidad CQ-1 de AD-2. La frontera identifica un punto del bucle CPU donde no se
está ejecutando ni despachando trabajo. No excluye escritores de otros hilos.

## Requisitos EARS

- **CB01:** WHILE el hilo CPU no ha terminado de inicializarse o ha comenzado
  su cierre THEN el diagnóstico SHALL rechazar la frontera CPU.
- **CB02:** WHEN comienza una iteración exterior del bucle CPU THEN el proveedor
  SHALL poder abrir una única frontera léxica antes de despachar eventos o ejecutar
  la VM. IF la solicitud procede de actividad anidada THEN SHALL rechazarla.
- **CB03:** WHEN empieza Execute, una transición instrumentada o el despacho de
  eventos THEN SHALL revocar la frontera antes del primer efecto o callback.
- **CB04:** WHEN termina esa actividad THEN SHALL conservar revocada la frontera
  exterior hasta terminar su ámbito; SHALL NOT rehabilitarla por restaurar un booleano.
- **CB05:** WHEN se intenta abrir otra frontera dentro de la actual THEN SHALL
  rechazar la nueva y revocar la anterior. Su destrucción SHALL NOT liberar la ajena.
- **CB06:** WHEN hay retorno temprano, excepción o ámbitos de actividad anidados
  THEN SHALL restaurar el anidamiento, sin rehabilitar una frontera revocada.
- **CB07:** WHEN se consulta admisión sin frontera válida THEN SHALL rechazar
  `cpu_boundary` antes de leer configuración o punteros de implementaciones CPU.
- **CB08:** WHILE no se ha acreditado exclusión PINE, GS/VU y otros escritores
  THEN SHALL mantener sus condiciones sin acreditar y SHALL NOT habilitar armado.

## Diseño, SOLID y orden

`CpuBoundary` solo administra ámbitos léxicos; no lee configuración, espera,
asigna memoria ni toma mutex. El proveedor posee un objeto `thread_local` y lo
activa únicamente después de CPUThreadInitialize. Sus objetos Activity y Boundary
no se copian ni mueven; deben destruirse en orden léxico en el hilo propietario,
antes que el objeto raíz. Otros hilos tienen su propia instancia inactiva.

La integración Qt abre Boundary al comienzo del while exterior. Los ámbitos de
despacho cubren tanto exec/processEvents de ese bucle como PumpMessagesOnCPUThread.
Las funciones VM instrumentadas abren Activity en su entrada, antes de validación,
efectos, avisos o diálogos. Una frontera revocada conserva su puesto hasta salir
del ámbito, por lo que terminar un callback no permite readquirirla en la misma
iteración. El sampler requiere esta prueba además de hilo CPU y pausa.

El fast path síncrono de RunOnCPUThread(block=true) invoca el callback directamente
y no atraviesa esos pumps. CQ-2 deberá revocarlo también antes de activar una
operación coordinada. Los callbacks ejecutados por otras APIs quedan fuera de
la cobertura de este lote; la frontera por sí sola no concede admisión global.

| Evento | Frontera | Continuación del coordinador futuro |
| --- | --- | --- |
| Inicio de iteración exterior, CPU online | Nueva, válida | Puede consultar PINE |
| Trabajo PINE anterior pendiente | Aún no hay exclusión | Ceder a eventos; no esperar su cola |
| Entrada en eventos/Execute/transición | Revocada | Cancelar observación; revalidar en otra iteración |
| Retorno de callback o transición | Sigue revocada | No adquirir ni reutilizar en esta iteración |
| Reentrada de frontera | Ambas rechazadas/revocadas | Abortar intento |
| Cierre/reinicio CPU | Revocada | Invalidar operación antes de liberar exclusión |

Orden previsto: frontera CPU → cierre PINE → consultas sin locks retenidos →
exclusión de productores → drenaje VU → drenaje GS → revalidación → diagnóstico.
Si se necesitan callbacks previos, hay que abandonar la frontera y volver por el
bucle exterior; no bombear eventos dentro de una frontera válida. El cierre PINE
podrá sobrevivir entre iteraciones, pero el permiso de frontera no. Una cancelación
debe invalidar la operación antes de reabrir PINE.

WaitVU/WaitGS son esperas bloqueantes y no impiden nuevos productores. IsDone y
Paused no las sustituyen. CQ-2/CQ-3 deberán resolver el despertar del bucle pausado,
la supresión de Execute mientras drena, la vida del servidor y las dependencias
inversas de trabajadores antes de conectar esas esperas. Este lote no las llama.

## Tareas y aceptación

1. **CB-T1 / CB01–08:** fijar inventario, estados y orden; delimitar qué prueba
   la frontera y qué queda pendiente del coordinador.
2. **CB-T2 / CB01–07:** implementar ámbitos portables; instrumentar una copia
   privada nueva de VMManager/QtHost, conservando copias anteriores y build OFF.
3. **CB-T3 / CB02–07:** probar anidamiento, revocación persistente, excepciones,
   inicialización/cierre, eventos, transiciones y sampler con cuerpos del proveedor.
4. **CB-T4 / CB08:** compilar ON/OFF, ejecutar CTest y sanitizadores, medir
   cobertura y auditar fuentes; mantener pendientes integración PINE y drenaje.
