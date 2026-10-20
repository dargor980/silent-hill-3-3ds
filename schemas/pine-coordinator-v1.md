# Coordinación PINE v1 — PC01–PC09

CQ2-A/B y pruebas acotadas de CQ2-C/D. Una operación interna prueba el drenaje
de PINE. Su resultado no autoriza leer memoria ni armar continuidad.

- **PC01:** WHEN el CPU recibe una solicitud interna válida THEN SHALL dejarla
  pendiente, con ID creciente, plazo monotónico y épocas VM/servidor no nulas.
  IF hay otra operación, ID repetido o plazo inválido THEN SHALL rechazarla.
- **PC02:** WHEN el bucle exterior admite la solicitud THEN SHALL exigir frontera
  válida, pausa y las mismas épocas antes de cerrar PINE. Encolar no es admitir.
- **PC03:** WHILE hay reservas PINE anteriores THEN SHALL conservar el cierre
  entre iteraciones, ceder a eventos y SHALL NOT ejecutar Execute para drenarlas.
- **PC04:** WHEN termina un despacho THEN SHALL revalidar desde una frontera
  nueva. Los callbacks inline y encolados SHALL revocar la frontera antes de correr.
- **PC05:** WHEN cambia una época, se pierde pausa/frontera o vence el plazo THEN
  SHALL invalidar el intento y mantener el cierre hasta retirar la operación.
- **PC06:** WHEN se cancela o cierra el CPU THEN SHALL invalidar antes de liberar
  el cierre. Una cancelación con ID ajeno SHALL NOT cancelar la operación actual.
- **PC07:** WHEN no quedan reservas y las condiciones siguen válidas THEN SHALL
  informar exclusivamente drenaje PINE; SHALL NOT acreditar GS/VU/otros escritores.
- **PC08:** WHILE no hay operación THEN SHALL conservar el flujo normal ON/OFF.
  El bucle pausado SHALL poder despertar por solicitud, cancelación y plazo sin
  esperar síncronamente trabajos que necesitan el propio CPU.
- **PC09:** WHEN se detiene/reinicia PINE THEN SHALL cambiar una generación host
  no restaurable antes de efectos; SHALL NOT confundir IsInitialized con drenaje.

## Diseño

PineDrain es un controlador por hilo; BarrierSource solo abre un cierre RAII.
Una optional de Lease almacena el cierre no movible sin asignación. Sus estados
son idle, queued, draining, held y terminales completed/cancelled/timed_out/
invalidated/rejected. submit solo guarda datos; step exige CpuBoundary válida y
hechos actuales. Complete revalida, y retire invalida estado antes de destruir
el cierre. Los terminales no liberan recursos por su cuenta. No invoca callbacks.

VMManager traduce época host, generación PINE y estado VM, con rechazo de otros
hilos. El resultado permanece interno. Qt sale del exec pausado al recibir una
solicitud y, mientras drena, usa un timer local de 1 ms y exec; el timer se destruye
al salir incluso si otro evento hizo quit. No hay sondeo ocupado ni espera de
Completion. El camino Running vuelve al bucle antes de Execute si se encoló una
operación durante processEvents. Ningún lock de contabilidad cruza un despacho.

Las solicitudes pueden encolarse en callbacks; no adquieren frontera ni cierre
allí. Las épocas fijadas se verifican al admitir y en cada paso. La pausa perdida
invalida; no se fuerza una pausa ni se descarta la intención posterior de continuar.
Tras cancelar/retirar, el flujo normal puede aplicar esa intención. No se bloquean
los demás productores: CQ-3/CQ-4 deben cubrirlos antes de conservar PINE para GS/VU.

## Tareas

1. **PC-T1 / PC01–09:** implementar controlador y contrato de estados/propiedad.
2. **PC-T2 / PC02–09:** integrar VMManager/PINE/Qt en otra copia privada, sin
   comando de red ni botón de armado; conservar fuentes/evidencias anteriores.
3. **PC-T3 / PC01–09:** comprobar colas, descarte, timeout, cancelación, épocas,
   reentrada y bypass de Execute; diferenciar dobles de event loop real.
4. **PC-T4 / PC07–09:** compilar ON/OFF, sanitizar, medir cobertura y auditar;
   mantener pendientes ciclo completo de socket, escritores y VM real.
