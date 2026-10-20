# Composición privada del diagnóstico — DC v1

Historia: como investigador, necesito comprobar consumidor, trabajador,
inventario nativo y transporte juntos antes de dar por terminada la integración
de presupuesto, manteniendo separada la admisión runtime del emulador.

## Requisitos EARS

- **DC01:** CUANDO se prepare la sonda, DEBERÁ verificar una copia privada PCSX2,
  fijar manifiesto y evidencias antes de lanzarla y conservar fuentes, registros
  y hashes de cada intento. SHALL NOT modificar el candidato ni usar ISO/BIOS/VM.
- **DC02:** CUANDO se reciba una solicitud, DEBERÁ fijar el deadline local del
  productor antes del recibo y pasarlo a `submit_until`; preparación, lectura,
  hash y entrega compartirán ese plazo. El consumidor BC DEBERÁ usar su propio
  plazo total. SHALL NOT equiparar relojes absolutos de procesos distintos.
- **DC03:** CUANDO se establezca el canal, DEBERÁ contrastar identidad nativa
  de ambos procesos con expectativas locales y conservarla en revalidaciones.
  El payload SHALL NOT seleccionar política, peer esperado ni permisos.
- **DC04:** CUANDO se acepte una muestra, DEBERÁ verificar frame completo,
  correlación, evidencia, identidad de proceso y plazo; tres muestras positivas
  DEBERÁN conservar identidad y nonce. Facts desconocidos y epochs cero SHALL
  NOT habilitar captura ni certificar guardias runtime.
- **DC05:** CUANDO se bloquee una fase o cancele cualquiera de los extremos,
  DEBERÁ impedir admisión tardía y nuevas solicitudes, conservar primera causa
  y verificar limpieza pendiente antes de atribuir un cierre confirmado.
- **DC06:** CUANDO se fragmente o frene el envío, DEBERÁ conservar la operación
  pendiente y el plazo restante. La prueba DEBERÁ distinguir backpressure real
  del socket de una demora sintética del sink y separar bytes de confirmaciones.
- **DC07:** CUANDO termine la sesión, DEBERÁ verificar unión DW, cierre del sink,
  cierre del consumidor y salida del proceso; el contraste de descriptores
  DEBERÁ declarar su rango observado. Un intento rechazado por cambio del loader
  SHALL NOT contarse como ejecución del fallo que se pretendía provocar.
- **DC08:** CUANDO pase la matriz conjunta, DEBERÁ publicar evidencia reproducible
  y cerrar NW-T3/DW-T2 solo para diagnóstico privado sin VM. Guardias runtime
  DW-T3, perfil de producción, captura y port jugable continuarán separados.

## Diseño y tareas

El launcher Python crea un socket Unix privado y conoce PID/nacimiento del hijo.
La sonda se inicia fuera de CPU en la salida de `-testconfig`; contrasta al padre
y construye DW con `MacOSDiagnosticWorkFactory`. Un dueño de IO recibe solicitudes
y compone `deliver_diagnostic` con el sink nativo. Una envoltura local de prueba
fragmenta o demora IO y publica marcadores; ninguna opción procede del payload.
El control de fallos nativo y las demoras del consumidor son exclusivos de la
sonda. Las fuentes de producto verificadas en SRC109/SRC110 se reutilizan.

- [x] **DC-T1 / NW-T3c:** congelar fuentes/configuración, componer ambos extremos
  y verificar positivo/revalidaciones con identidad de kernel e inventario real.
- [x] **DC-T2 / NW-T3c:** deadline/cancelación en preparación, lectura, hash y
  entrega; fragmentación, backpressure, peer incorrecto, manifiesto incorrecto
  y desconexión. Conservar intentos que no alcancen el punto de inyección.
- [x] **DC-T3 / NW-T3c:** auditar frames, recursos, cierres, fuente y copia;
  ejecutar controles de repositorio y publicar dos auditorías idénticas.
