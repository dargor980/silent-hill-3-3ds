# Coordinador runtime del diagnóstico — RC v1

Historia: como investigador, necesito conservar CPU/PINE/VU/GS durante el
diagnóstico y descartar inmediatamente un alcance retirado, sin hacer IO o unir
trabajadores desde CPU.

## Requisitos EARS

- **RC01:** CUANDO CPU encole un diagnóstico, DEBERÁ fijar deadline antes de
  adquirir guardias y crear un ticket propio, pendiente, con ID de alcance no
  reutilizable en el proceso. Un intento ajeno, concurrente o inválido SHALL NOT
  reemplazar el dueño actual. Agotamiento de IDs/generaciones será terminal.
- **RC02:** MIENTRAS PINE/VU/GS se drenen, el ticket DEBERÁ permanecer pendiente.
  CUANDO todas estén retenidas bajo CPU pausada, DEBERÁ muestrear épocas reales y
  el perfil AP, revalidar guardias y publicar una única vinculación.
- **RC03:** MIENTRAS el ticket esté listo, DEBERÁ conservar la misma frontera
  lexical CPU y guardias hasta cancelación o plazo. Una salida, actividad o
  frontera anidada DEBERÁ revocar antes de invalidar esa frontera.
- **RC04:** CUANDO cualquier hilo notifique un productor o transición cubierta,
  DEBERÁ avanzar una generación atómica antes del efecto o espera. DW DEBERÁ
  rechazar su generación anterior sin esperar a otro polling CPU. Esta señal
  SHALL NOT acreditar sincronización de memoria ni cobertura de otros escritores.
- **RC05:** CUANDO cambie una época, un hecho AP o venza el plazo, DEBERÁ revocar
  antes de retirar guardias. Cambio/regreso SHALL NOT reactivar el ticket. Un
  ticket viejo SHALL NOT cancelar un intento nuevo.
- **RC06:** CUANDO IO termine o cancele, DEBERÁ poder señalar por el ticket sin
  callback CPU. CPU retirará GS/VU/PINE y el dueño IO unirá/cerrará DW aparte.
  Un trabajo bloqueado conservará limpieza pendiente; no se esperará desde CPU.
- **RC07:** CUANDO falte evidencia de RDebug, escritores, JIT/caché/DMA u otra
  condición, DEBERÁ conservar el hecho desconocido o violado. La retención PINE
  cooperativa acreditará solo su cierre observado, no la desactivación del servidor.
- **RC08:** CUANDO se valide el adaptador, DEBERÁ ejecutar cuerpos privados
  exactos con dependencias declaradas, contrastar ON/OFF, lifecycle y regresiones,
  compilar unidades completas y conservar custodia. Esto SHALL NOT sustituir
  el candidato enlazado con VM de RB-T3 ni habilitar captura.

## Diseño y aceptación de RB-T2

El ticket separa entrega entre hilos de la vinculación inmutable y del trabajador.
CPU conserva un dueño que revoca antes de destruirse. La generación compartida
solo invalida: no se resetea ni conserva punteros a VM. El ticket se crea en CPU;
IO obtiene la vinculación cuando está listo y cancela por su propio ticket.

VMManager mantiene el drenaje mientras el ticket existe y revalida usando los
controles retenidos y el sampler AP. La frontera privada revoca en su destructor;
Qt mantiene una sola instancia durante la espera de trabajadores/diagnóstico,
sin despachar callbacks. Las esperas externas y el cierre de la aplicación
retiran ese intento. La ruta histórica de drenaje de una sola muestra se conserva.

- [x] RC-T1: ticket/generación, revocación de lifecycle y pruebas de carreras.
- [x] RC-T2: adaptar VMManager/PINE/frontera/Qt en copia privada; cuerpos ON/OFF,
  retención, muestreo, cancelación, cambio/regreso y controles negativos.
- [x] RC-T3: compilar unidades completas, regresiones nativas, sanitizadores,
  custodia, pipeline y documentación. RB-T3 permanece pendiente hasta probar VM.

Evidencia: [SRC113](../docs/execution/f02-07-runtime-coordinator.md). Las tareas RC
cierran la integración y su validación con sondas; RB-T3 requiere candidato y VM.
