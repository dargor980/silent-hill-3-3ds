# Control CPU↔worker v1 — WC01–WC10

Núcleo de B3-B1/B3-B2; complementa [WD](worker-drain-v1.md) y
[QD](qt-dispatch-v1.md). La conexión con workers PCSX2 sigue separada.

- **WC01:** WHEN CPU solicita retención THEN el canal SHALL aceptar solo un ID
  positivo creciente de la generación online vigente y sin otra solicitud activa.
  IDs/generaciones inválidos, agotados o reutilizados SHALL rechazarse sin wrap.
- **WC02:** WHEN el worker terminó todos los efectos anteriores y puede quedarse
  sin producir THEN SHALL poder acusar únicamente la solicitud vigente. IF CPU
  la canceló o cambió la generación THEN SHALL rechazar ese acuse.
- **WC03:** WHILE existe un acuse held THEN el worker SHALL permanecer sin
  efectos y SHALL NOT finalizar su generación hasta que CPU libere ese token.
  Un intento de stop retenido SHALL devolver retained, nunca stopped.
- **WC04:** WHEN CPU libera un token pendiente/retenido THEN SHALL invalidarlo
  sin bloquear ni reservar datos. Un acuse concurrente SHALL NOT restaurar held
  después de esa liberación; tokens ajenos SHALL NOT liberar al propietario.
- **WC05:** WHEN el worker inicia otra generación THEN SHALL hacerlo solo desde
  offline y con generación estrictamente mayor. Una consulta vieja SHALL resultar
  invalid y un nuevo inicio SHALL NOT restaurar acuses ni IDs anteriores.
- **WC06:** WHEN se consulta THEN SHALL distinguir pending, held, released,
  offline e invalid a partir de una instantánea coherente. Un despertar SHALL NOT
  interpretarse como acuse; el caller SHALL comprobar siempre el predicado.
- **WC07:** WHEN se publica control THEN SHALL despertar por un canal independiente
  de ringbuffer/AsyncCall. Avisos repetidos podrán agruparse, pero una publicación
  entre comprobación y espera SHALL NOT perderse. Las esperas tendrán plazo.
- **WC08:** WHEN se opera request/ack/release/start/stop THEN SHALL usar trabajo
  acotado sin asignación propia, espera de CPU/UI, locks del proveedor ni callbacks.
  Si stop pierde una carrera SHALL devolver retry: el worker no podrá salir aún.
- **WC09:** WHEN se valida THEN SHALL probar carreras, reinicio, IDs límite,
  publicación entre hilos, avisos antes/durante la espera y cola de datos llena
  en un modelo explícito; SHALL separar ese modelo de workers reales.
- **WC10:** WHILE los puntos de acuse y ciclo de vida PCSX2 no están conectados
  THEN SHALL conservar el puerto productivo rechazado y los modos admitidos vacíos.

## Diseño y propiedad

WorkerControl tiene dos actores: un único CPU que pide/libera y un único worker
que inicia/acusa/detiene. start/stop/ack del worker no corren entre sí; CPU no
ejecuta dos request/release simultáneos. Las consultas son atómicas. El objeto
y su ControlWakeup de CPU deben vivir hasta que ambos actores hayan terminado.
El buzón es tooling host C++20, independiente del runtime Nintendo.

Una palabra atómica de 64 bits contiene generación (32), ID (29) y fase (3).
ID máximo 536870911; generación máxima 4294967295. No se reinician dentro de la
misma generación ni se permite wrap; reiniciar exige offline y otra generación.
Las plataformas host deben ofrecer atomic<uint64_t> sin locks, comprobado al
compilar. Este requisito no se impone al runtime 3DS.

| Actor / operación | Precondición | Transición / resultado |
|---|---|---|
| worker start(g) | offline, g mayor y no cero | running(g,0), aviso CPU |
| CPU request(g,id) | running(g,anterior), id mayor y válido | requested(g,id), aviso worker |
| worker acknowledge(token) | requested del mismo token | held, aviso CPU |
| CPU release(token) | requested o held del mismo token | running conservando ID, aviso worker |
| worker stop(g) | running/requested de g | offline conservando ID, aviso CPU |
| worker stop(g) | held | retained; debe esperar liberación |
| worker stop(g) | carrera durante CAS | retry; no tiene permiso de salir |
| consulta token | coincidencia de generación/ID | estado derivado; otro token es invalid |

CAS fuertes, sin bucles de reintento abiertos. Release usa como máximo dos CAS:
si el primero pierde frente a requested→held, el segundo puede retirar held;
ningún worker puede modificar held salvo observar la liberación de CPU. Si
perdió frente a stop/reinicio, el token viejo ya no está activo. Un segundo
escritor CPU o dos workers simultáneos violan el contrato de actores.

Publicación y CAS exitosos usan release/acquire; consultas y fallos CAS adquieren
la palabra observada. Un acuse publica efectos previos del worker; el acquire de
CPU los observa. La invariancia de held requiere que el caller pare efectos y
respete stop(retained); el buzón no puede detener por sí mismo a un hilo.

ControlWakeup contiene un semáforo binario y un flag atómico de aviso pendiente.
notify hace exchange(true, acq_rel) y publica al semáforo solo al pasar de false
a true. Un consumidor único adquiere el semáforo y hace exchange(false, acq_rel):
adquiere los avisos agrupados antes de limpiar; los posteriores publican otro
permiso. Puede haber varios notificadores, pero solo un consumidor por wakeup.
Una señal antigua o espuria exige volver a consultar el predicado. Los métodos
de espera explícitos son la única parte bloqueante; no ejecutan Qt ni callbacks.

Cada WorkerControl posee el aviso del worker y recibe por referencia el aviso
CPU, que puede compartirse entre VU/GS. El coordinador decidirá solicitar VU antes
de GS y liberar GS antes de VU. No se conecta aún a EffectDrainPort ni al bucle
Qt: primero se deben integrar los puntos reales donde detener efectos, despertar
el worker dormido y tratar sus cierres/fallos sin ignorar StopResult.

## Tareas y aceptación

- **WC-T1 / WC01–08:** estados, identidad y núcleo WorkerControl/ControlWakeup;
  sin proveedor ni datos del juego. B3-B1 completo, B3-B2 núcleo portable.
- **WC-T2 / WC01–09:** CTest, carreras con barreras, modelo de cola llena,
  publicación de payload, límites y asignaciones; Debug/Release/ASan-UBSan,
  cobertura y controles negativos. CI pública independiente de datos privados.
- **WC-T3 / WC10:** auditoría y snapshots; B3-B2 integración, B3-B3/CQ3-C acuses
  reales y B3-C/B4 dependencia VU↔GS/cierre/UI permanecen pendientes.
