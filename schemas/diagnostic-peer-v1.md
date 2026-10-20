# Canal y sesión de diagnóstico — PS v1

Historia: como investigador, necesito vincular PD v1 al proceso que lancé y
descartar la sesión cuando el canal o su identidad dejen de coincidir.

## Requisitos EARS

- **PS01:** CUANDO se construya una sesión, DEBERÁ recibir del lanzador PID,
  nacimiento y UID esperados, política PD inmutable y una conexión Unix propia.
  El payload remoto SHALL NOT seleccionar proceso, política ni lector nativo.
- **PS02:** CUANDO se identifique al peer en macOS, DEBERÁ comprobar socket Unix
  conectado de tipo stream, PID y credenciales del kernel, token de auditoría y
  nacimiento mediante APIs del sistema. DEBERÁ comparar dos lecturas, validar
  que el token aún identifica el proceso y rechazar cualquier error o diferencia.
  Nombres de ruta, `ps`, datos del cliente o PID aislado SHALL NOT sustituirlo.
- **PS03:** CUANDO se intercambie una respuesta, DEBERÁ comprobar el peer antes y
  después del intercambio en el mismo descriptor retenido, y comparar PID y
  nacimiento de PD con el peer y la expectativa local. El token completo DEBERÁ
  permanecer estable; una nueva conexión requerirá una nueva sesión.
- **PS04:** CUANDO se inicie la sesión, DEBERÁ generar un desafío aleatorio de
  128 bits y secuencia inicial 1. CUANDO se solicite otra muestra, DEBERÁ avanzar
  consecutivamente sin overflow. Un mensaje repetido, anticipado o de otro
  desafío DEBERÁ invalidar permanentemente la sesión, sin reconectar ni fallback.
- **PS05:** CUANDO exista una línea base, DEBERÁ conservar nonce del proveedor,
  hashes, revisión, conteos, alcance, evidencias y épocas/generaciones. Cualquier
  cambio o lectura fallida DEBERÁ borrar la observación pendiente y conservar la
  primera causa. Volver al valor previo SHALL NOT rehabilitarla. Los hechos AP
  pueden cambiar dentro de épocas iguales; nunca constituyen permiso de captura.
- **PS06:** CUANDO haya EOF, rechazo PD, error de formato/IO, fork, llamada desde
  otro hilo, cierre o cancelación explícita, DEBERÁ hacer terminal la sesión y
  cerrar su conexión. Los errores de cierre SHALL NOT ocultar la causa original.
  Una instancia terminal SHALL NOT volver a consultar el canal.
- **PS07:** CUANDO se transporte PD, DEBERÁ limitarse a solicitudes de 32 bytes y
  respuestas de 294, manejar fragmentación, rechazar bytes adicionales disponibles
  y acotar la espera de IO. El plazo de IO SHALL NOT presentarse como cumplimiento
  del presupuesto completo de preparación/inventario pendiente en PT-T5c.
- **PS08:** CUANDO se entregue diagnóstico ligado al peer, DEBERÁ declarar que es
  histórico y de alcance application_headers con plataforma asumida. SHALL NOT
  convertirlo en IP estricto, autenticar todo el contenido de memoria, excluir
  ABA, armar guardias ni otorgar capacidades. El adaptador confiable y el SO forman
  parte de la base de confianza; no se pretende resistir un proveedor malicioso.
- **PS09:** CUANDO se valide, DEBERÁ probar procesos y sockets reales además de
  dobles: cierre, exec, otro PID, fragmentación y comparación C++/Python. Reuso de
  PID no inducible con seguridad DEBERÁ probarse con dobles y declararse como tal.
  El candidato PCSX2 DEBERÁ probarse en una copia privada sin iniciar VM.

## Diseño y SOLID

`read_macos_peer` es un lector nativo acotado y sin estado de protocolo. El dueño
del descriptor serializa llamadas y evita cerrar/sustituirlo durante la lectura.
Usa `LOCAL_PEERPID`, `LOCAL_PEERTOKEN`, `getpeereid`, `proc_pidinfo` y
`proc_pidpath_audittoken`. La última API valida PID/version del token; la ruta
devuelta se descarta y no es una evidencia de artefacto. Los campos del token se
extraen con libbsm; sus bytes opacos se conservan únicamente para comparación.
El helper de nacimiento permite fijar la expectativa al lanzar el proceso.

El bridge local serializa 56 bytes: PID, euid, ruid, pidversion (cuatro u32 LE),
nacimiento ns u64 y token opaco de 32 bytes. No es un nuevo mensaje remoto PD.
El token se consulta de nuevo en cada frontera: no se presume inmutable por estar
en un socket. Lecturas dobles son comprobaciones puntuales, no un snapshot atómico.

`NativePeerReader` carga el helper local elegido por el lanzador; `UnixDiagnosticChannel`
posee el socket conectado y solo maneja IO; `PlatformDiagnosticSession` compone
política, correlación y comparación terminal. El canal no se conecta a PINE/OBS1.
El transporte es síncrono, de propietario único y usa un plazo monotónico por
intercambio. Integración asíncrona y cancelación externa verificada quedan en PT-T5c.

Un nonce se fija con la primera respuesta del proceso ya contrastado por el kernel;
no autentica por sí solo al proveedor. El resultado `PeerBoundDiagnostic` conserva
la evidencia puntual del peer y PD. Si el dueño pierde la sesión borra su última
observación; copias históricas anteriores no son permisos vigentes ni revocables.

Fuentes de semántica: [socket Unix de XNU](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c),
[wrapper libproc](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c)
y [validación de identidad](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c),
contrastadas con los headers del SDK local. Se implementa código propio.

## Tareas detalladas

- [x] **PS-T1 / PS01–03,09:** implementar lector nativo/bridge y pruebas de API,
  socket real, nacimiento y exec. Fijar hashes de headers y conservar negativos.
- [x] **PS-T2 / PS03–08:** implementar puerto/canal y dueño de sesión Python;
  pruebas de secuencia, desafío, cada identidad, excepciones y terminales.
- [x] **PS-T3 / PS09:** integrar canal en sonda privada PCSX2, comprobar tres
  muestras estables y rechazos deliberados, pipeline, cobertura y custodia.
- [ ] **PS-T4 / PT-T5c:** ejecutar fuera del hilo CPU, cancelación verificable,
  deadline total y callbacks tardíos; unir gates runtime antes de habilitar captura.

SRC107 completa DW-T1 / PT-T5c.1, núcleo de presupuesto/cancelación/cierre en
[DW v1](diagnostic-worker-v1.md). PS-T4 permanece abierto hasta instrumentar
adaptadores nativos y unir las guardias runtime; la sesión síncrona anterior no
se presenta como integrada al ejecutor.

SRC109 añade el modo optativo `budget_clock` del [contrato BC](budgeted-diagnostic-consumer-v1.md):
plazo total del consumidor de 5 s/2 s, desde antes de consultar peer hasta publicar,
IO no bloqueante y cancelación cooperativa. Las llamadas desde otro hilo señalan
rechazo y el dueño cierra al retornar; un fork descarta su copia sin tomar el
mutex heredado. El modo anterior conserva sus pruebas y alcance. No se declara
integración con el productor DW ni se cierra PS-T4 con esta etapa.
