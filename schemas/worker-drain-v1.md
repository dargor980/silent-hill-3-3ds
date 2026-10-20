# Exclusión de productores y drenaje VU→GS v1 — WD01–WD12

CQ3-A fija el contrato y el inventario; CQ3-B/C implementarán estas obligaciones.
No describe capacidades ya habilitadas. Referencias: [AP](admission-profile-v1.md),
[CB](cpu-boundary-v1.md), [PC](pine-coordinator-v1.md).

Como responsable de la captura necesito distinguir trabajo terminado de ausencia
de escritores, para que una lectura no compita con CPU, VU, GS o callbacks host.

- **WD01:** WHEN se evalúa la exclusión THEN el coordinador SHALL exigir la
  identidad de las fuentes revisadas y cobertura de cada familia de productores.
  IF aparece una ruta no cubierta THEN SHALL rechazar el intento.
- **WD02:** WHILE PINE conserva reservas anteriores THEN SHALL permitir su
  progreso sin Execute. WHEN termina ese drenaje THEN SHALL conservar el cierre
  hasta que el intento completo termine o se invalide.
- **WD03:** WHEN se inicia el drenaje de trabajadores THEN SHALL excluir nuevas
  operaciones productoras antes de su primer efecto, incluida la preparación de
  paquetes, cambios de contadores y escrituras que evitan la cola.
- **WD04:** IF una solicitud tardía necesita producir trabajo THEN SHALL
  invalidar y liberar las retenciones de trabajadores antes de ejecutar sus
  efectos, o diferir la solicitud conservando su propiedad y semántica.
  SHALL NOT descartar silenciosamente una operación del juego que retorna void.
- **WD05:** WHILE drena VU THEN SHALL permitir que GS consuma paquetes y libere
  espacio. WHEN VU confirma fin de efectos previos THEN SHALL solicitar el cierre
  final de GS, incluyendo AsyncCall y presentación ociosa.
- **WD06:** WHEN un trabajador confirma retención THEN SHALL publicar un acuse
  asociado al ID y generación vigentes después de sus últimos efectos, y SHALL
  permanecer sin efectos hasta liberar ese acuse. Una cola vacía no es un acuse.
- **WD07:** WHEN el coordinador consulta el progreso THEN SHALL distinguir
  pendiente, retenido, cancelado y fallido sin bloquear en una espera sin plazo.
  IF el trabajador termina, reinicia o cambia de generación THEN SHALL invalidar.
- **WD08:** WHILE espera progreso THEN SHALL NOT mantener mutex de ringbuffer,
  configuración, logros, lista de juegos ni otros locks necesarios por los
  trabajadores. SHALL NOT esperar CPU/UI desde un hilo cuyo progreso se requiere.
- **WD09:** WHEN vence el plazo, se cancela, cambia una época o se pierde la
  frontera THEN SHALL invalidar antes de liberar; SHALL reactivar GS antes de
  permitir nuevo trabajo VU. Un acuse tardío SHALL NOT completar otro intento.
- **WD10:** WHEN se completa la retención THEN SHALL revalidar frontera, pausa,
  identidades y perfil. SHALL NOT promover RDebug, VIF dinámico, otros escritores
  o modos sin pruebas a condiciones satisfechas.
- **WD11:** WHEN se valida la implementación THEN SHALL ensayar productor tardío,
  callback reentrante, cola llena, dependencia VU↔GS, presentación ociosa, muerte,
  timeout, cancelación, reinicio y liberación. SHALL distinguir dobles, cuerpos
  reales aislados y aplicación completa en los resultados.
- **WD12:** WHEN se publica evidencia THEN SHALL incluir hashes, alcance y límites,
  sin originales del juego ni rutas privadas. Las fuentes históricas SHALL
  conservarse y la CI pública SHALL poder funcionar sin datos privados.

## Diseño y decisiones

Separa tres responsabilidades: el propietario CPU administra el intento y PINE;
la exclusión de productores protege entradas antes de efectos; cada trabajador
publica y conserva su propio acuse. Los puertos de trabajador expondrán
solicitar/consultar/liberar con resultado explícito, sin filtrar semáforos del
proveedor al controlador. No se modifica WorkSema para atribuirle exclusión.

El orden es cierre y drenaje PINE → exclusión de productores → VU retenido con
GS aún progresando → GS retenido → revalidación. La liberación invalida primero,
reactiva GS y VU, y solo después permite nuevos productores y retira PINE.
Un trabajador cerrado no se interpreta como una operación completada.

La entrega CPU de SRC74 todavía puede ejecutar cualquier callback Qt. Antes de
retener trabajadores, CQ3-B debe cubrir esos callbacks y las entradas directas
de UI. Revocar CpuBoundary al entrar en exec no cancela por sí solo la operación
ni libera trabajadores. Si el driver no puede hacer avanzar las dependencias
sin abrir productores, el intento se rechaza; no se sustituye por WaitVU/WaitGS.

El canal de control necesita progreso sin reservar espacio en un ringbuffer
lleno. En CQ3-B se elegirá y probará su integración, incluida la intervención
antes del primer efecto de un callback tardío. Un AsyncCall usado como marcador
solo prueba trabajo anterior a ese marcador; no impide trabajo posterior, ni
detiene el camino de presentación ociosa. No basta como barrera final.

Alcance inicial: frontend Qt y perfil de intérpretes de AP. VIF dinámico continúa
rechazado. Tener MTVU desactivado en configuración no demuestra ausencia de un
hilo o trabajo residual: también se necesita evidencia de ciclo de vida.
GSRunner, renderizadores y otros escritores sin cobertura siguen no admitidos.

## Entregables y aceptación

1. **WD-T1 / WD01,03,05–08,12 — CQ3-A:** inventario por productor/hilo/efecto,
   dependencias y locks; hashes de archivos y referencias de código revisadas.
   Probe de WorkSema y WaitVU con resultados separados del proveedor completo.
2. **WD-T2 / WD02–04,08–09 — CQ3-B:** copia privada nueva; prolongar PINE,
   interceptar productores antes de efectos y resolver entrada UI directa;
   canal de control que progrese sin locks ni colas de datos bloqueadas.
   Aceptación: trabajo previo progresa, trabajo tardío aborta o se conserva,
   ninguna operación void se pierde y no se concede una captura.
3. **WD-T3 / WD05–10 — CQ3-C:** acuses de VU/GS por ID/generación, presentación
   ociosa cubierta, resultado explícito, cancelación y liberación ordenada.
   Aceptación: tests adversarios y objetos ON/OFF; perfil conservador.
4. **WD-T4 / WD01–12 — CQ3-D/CQ-4:** ejecutar servidor PINE y frontend completo,
   reentrada/cierre/fallos, medir coste y auditar antes de conectar AD-3.

Las pruebas de WD-T1 justifican el diseño. No sustituyen las pruebas de WD-T2–T4.
