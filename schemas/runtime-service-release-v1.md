# FC — Liberación del canal tras la última respuesta

Historia: como consumidor del diagnóstico, necesito validar la última respuesta
mientras el productor y su identidad siguen vivos, y cerrar después mi canal.
SRC121 acepta dos respuestas por sesión; el cierre inmediato del productor
coincide con la lectura de la tercera y activa correctamente el rechazo de EOF.

## Requisitos EARS

- **FC01:** WHEN el servicio complete su tercera entrega THEN SHALL conservar
  canal, handoff y trabajador hasta observar EOF del consumidor, cancelación,
  error o agotamiento del plazo. SHALL NOT solicitar una cuarta adquisición.
- **FC02:** WHILE espere la liberación THEN SHALL usar el menor entre el plazo
  original del handoff y dos segundos desde la última entrega, sin ampliar el
  plazo global de cinco segundos. SHALL revisar cancelación y reloj antes y
  después de IO, con esperas de sondeo de hasta 20 ms.
- **FC03:** IF llega cualquier byte adicional THEN SHALL rechazar por protocolo.
  IF cambia la identidad, falla IO o se usa otro dueño THEN SHALL rechazar.
  IF observa EOF del endpoint autenticado THEN SHALL terminar esta fase sin
  atribuirle por sí sola una confirmación de publicación en el consumidor.
- **FC04:** WHEN termine la fase THEN SHALL impedir nuevas operaciones en el
  canal y recorrer la retirada CPU y unión DW existentes antes de destruir sus
  recursos. La espera SHALL NOT ejecutarse en CPU ni en UI.
- **FC05:** WHEN se valide THEN SHALL conservar el rechazo Python de datos extra
  y EOF, probar carrera de última respuesta, EOF, bytes extra, silencio, identidad,
  dueño, cancelación y límites; SHALL repetir con el candidato y tres respuestas
  aceptadas por perfil. No habilita admisión ni los gates pendientes.

## Diseño SOLID

`MacOSDiagnosticSink` conserva la propiedad exclusiva del descriptor y añade una
operación terminal no virtual para observar liberación. El servicio decide
cuándo invocarla después de su tercer envío. El adaptador sigue siendo responsable
de identidad, socket, dueño y cierre; no conoce el inventario ni interpreta
respuestas. No cambia el layout del objeto, los frames, el codec ni el verificador
Python. El launcher de pruebas anuncia fin de solicitudes con `SHUT_WR` después
de aceptar tres frames; mantiene el descriptor y espera EOF del productor antes
del cierre físico. Esa espera de limpieza está acotada a dos segundos y no
amplía el presupuesto de ninguna muestra ni el handoff del productor.

El EOF se interpreta como fin del envío remoto únicamente en esta fase terminal;
las lecturas normales siguen rechazando EOF y los bytes incompletos. Un byte
extra no se consume como nueva solicitud. El resultado no sustituye la evidencia
independiente de aceptación/publicación del consumidor.

El lector nativo ordinario también rechaza EOF. La fase terminal usa un lector
separado que exige EOF y verifica dos veces PID, nacimiento, usuarios, versión
de PID, audit token y ruta por audit token. No se expone mediante la ABI Python
ni se usa para aceptar respuestas. El socket autenticado mantiene dueño exclusivo;
se comprueba identidad también cuando EOF aparece entre dos consultas.
Un cierre físico remoto hace que macOS retire PID/token del socket y se rechaza
por identidad no disponible. El medio cierre conserva esas credenciales hasta
que el productor confirme la liberación y cierre. Los bytes adicionales se
rechazan tanto en el productor como durante la liberación del launcher.

Las pruebas nativas se ejecutan en stages separados, con inicio/suelo de 10 GiB,
máximo 512 MiB por stage y 180 s por proceso supervisado. El presupuesto del
candidato se fija con la matriz de dependencias de SRC121: tres unidades
(`macos_peer`, `macos_diagnostic_sink`, `runtime_service`), cuyos objetos previos
suman 70.656 bytes; se conservan 467 entradas de enlace.

**FC-B:** WHEN se reconstruya este candidato THEN SHALL usar un stage nuevo con
solo las fuentes propias superpuestas a la base inmutable, sin duplicar todo
PCSX2. SHALL verificar antes/después la base y las entradas reutilizadas. Exige
11 GiB libres al inicio, suelo de 10 GiB, máximo 256 MiB de stage, sondeo cada
0,5 s, 180 s por compilación/enlace y 600 s para la secuencia completa. El bundle
previo ocupa unos 108 MiB y el enlace comparable tardó 23 s; el resto reserva
espacio para fuentes propias, objetos, temporales y perfiles. IF se excede un
límite THEN SHALL abortar y preservar el rechazo. IB02 general sigue en 20 GiB;
esta decisión no autoriza un build completo ni modificar los stages de SRC121.

## Tareas

- [x] **FC-T1:** implementar la fase terminal y la integración del servicio;
  probar los caminos normales y adversos, sanitizadores y regresiones del canal.
  Requisitos FC01–FC05.
- [x] **FC-T2:** reconstruir las unidades afectadas en un candidato separado,
  fijar manifiesto/consumidor y repetir dos perfiles con tres respuestas; conservar
  candidatos y evidencia de SRC121. Requisitos FC01–FC05.
- [x] **FC-T3:** publicar evidencia reproducible y estado de RT-T3b.3, manteniendo
  separados cierre, inventario, captura y validación de otros escritores. FC05.

Resultado: [SRC122](../docs/execution/f02-07-service-release.md). Tres de cuatro
perfiles con VM aceptan tres respuestas; los dos perfiles de confirmación pasan
consecutivamente. El otro agota el plazo global durante la tercera consulta y
se conserva como rechazo. Esta validación no garantiza margen bajo carga.
