# Servidor PINE y coordinador conjuntos — PJ01–PJ10

- **PJ01:** WHEN se valida el transporte THEN SHALL ejecutar Initialize,
  AcceptClient, MainLoop, ClientLoop, ParseCommand y Deinitialize del proveedor
  fijado, con sockets locales y thread real. Un parser aislado SHALL NOT acreditar
  el ciclo de vida del servidor.
- **PJ02:** WHEN se ejecuta una fixture THEN SHALL utilizar un directorio/socket
  único de prueba y memoria sintética, sin alcanzar el socket del usuario, BIOS,
  ISO, cuentas ni VM existente. SHALL limitar tiempo, memoria/disco y procesos.
- **PJ03:** WHEN una solicitud conserva Work anterior al cierre THEN PINE SHALL
  permanecer draining y CPU SHALL poder terminar el trabajo encolado antes de
  solicitar retenciones VU/GS. WHEN llegue trabajo nuevo con entrada cerrada
  THEN SHALL rechazarlo antes del primer efecto.
- **PJ04:** WHEN Completion vence mientras su callback sigue encolado THEN
  SHALL conservar Work hasta ejecución o descarte. El vencimiento del cliente
  SHALL NOT contarse como ausencia de escritores.
- **PJ05:** WHEN servidor detiene/reinicia THEN SHALL cambiar generación,
  despertar accept/lectura y terminar el thread; SHALL invalidar intentos con
  identidad anterior. No se cerrará un descriptor reutilizado por otro hilo.
- **PJ06:** WHEN mensajes llegan fragmentados o cliente desconecta THEN SHALL
  terminar/rechazar de forma acotada y permitir recuperación según el protocolo.
  Buffers y reservas SHALL conservar límites/vida sin acceder fuera de rango.
- **PJ07:** IF sanitizadores detectan alineación, vida o carreras THEN SHALL
  preservar el fallo y corregirlo en copia nueva antes de acreditar esa ruta.
  SHALL NOT silenciar alineación ni reemplazar el cuerpo defectuoso por un doble
  en la prueba que declara transporte real.
- **PJ08:** WHEN se integra con workers THEN SHALL conservar orden VU→GS y
  retiro GS→VU→PINE, callback único y ausencia de retención durante productores.
- **PJ09:** WHEN se modifica fuente privada THEN SHALL preservar copias previas,
  probar objetos ON/OFF, sanitizadores y controles negativos. Un enlace completo
  SHALL respetar IB02 y no reemplazar automáticamente la aplicación instalada.
- **PJ10:** WHILE backend/locks, RDebug, perfil o VM sigan sin demostrar THEN
  SHALL mantener admisión vacía y no producir una captura aceptada del juego.

## Diseño y tareas

Primero se ejecuta el servidor exacto con tipos/efectos de VM sintéticos. Esto
permite observar defectos propios de transporte antes de acoplar workers. Luego
se sustituye exclusivamente el doble PINE del soporte conjunto por ese servidor,
con CPU/Qt y los bucles VU/GS ya fijados. Se conserva el despacho Completion real;
el lector sintético rechaza captura y no toca RAM del juego.

Un socket efímero corto evita truncamiento de sockaddr_un. Solo el fixture crea
su directorio y el supervisor limita cada ejecución; no se reutiliza TMPDIR del
emulador instalado. Las esperas se coordinan con señales, no con sleeps que den
por probado el orden. Los estados terminales y generaciones son los oráculos.

- **PJ-T1 / IW-PINE-JOINT1:** fuente/fragmentos y casos base de servidor real,
  cliente conectado/parcial/desconectado, lectura/escritura sintéticas y sanitizadores.
- **PJ-T2 / IW-PINE-JOINT2:** Work anterior, entrada tardía, callback CPU, timeout
  y descarte con el coordinador y workers juntos.
- **PJ-T3 / IW-PINE-JOINT3:** generaciones/parada/reinicio, negativos, objetos,
  custodia y enlace cuando corresponda. Separar alcance probado y pendiente.

## Reparación del transporte tras la prueba base

UBSan confirmó lectura desalineada de comandos y TSan confirmó acceso concurrente
al descriptor de cliente durante Deinitialize. Se conservarán esas ejecuciones.
La nueva copia leerá primitivas mediante memcpy; el hilo del servidor será dueño
del cierre del cliente. Un mutex protegerá su publicación/retiro y el shutdown
del controlador, sin abarcar accept, recv ni dispatch. El listener conservará su
descriptor hasta terminar join. Initialize/Deinitialize seguirán serializados por
el propietario CPU; esto no acredita llamadas de lifecycle concurrentes.

La recepción leerá exactamente el encabezado y luego su cuerpo, sin consumir
bytes de la siguiente solicitud; las pruebas incluirán mensajes consecutivos
en una sola escritura, desconexiones y reinicios. Los efectos del juego seguirán
sustituidos por datos propios.

La primera reparación mostró una espera intermitente en AcceptClient durante
join, confirmada con una pila del proceso. La segunda copia añade listener no
bloqueante y poll acotado a 100 ms; el socket aceptado se configura bloqueante.
La publicación revalida stopping bajo el mutex. La espera de disponibilidad y
accept no conservan ese lock. Se mantiene serializado el dueño del lifecycle.
Las pruebas y objetos de esta unidad son macOS x86_64; las ramas Windows/Linux
no se acreditan por compilación ni ejecución aquí.
