# Identidad nativa de nacimiento — NB01–NB08

Subunidad IP-NATIVE1 de [IP01–IP09](process-diagnostic-v1.md). Identifica una
instancia del proveedor; no acredita todavía artefactos, mappings ni peers.

## Requisitos EARS

- **NB01:** WHEN se consulta la identidad propia THEN el adaptador SHALL obtener
  PID y nacimiento del sistema operativo, sin aceptar PID, timestamp o nonce del
  cliente; SHALL exigir respuesta completa, PID coincidente y campos válidos.
- **NB02:** WHEN se inicia una instancia THEN SHALL generar una sola vez un nonce
  de 128 bits con la fuente de entropía del sistema; IF falla o entrega ceros THEN
  SHALL rechazar sin recurrir a reloj, PID, PRNG o valor del cliente.
- **NB03:** WHEN se crea o revalida la identidad THEN SHALL observar nacimiento
  antes y después, comprobar estabilidad y convertir segundos/microsegundos a
  nanosegundos sin overflow. SHALL conservar la resolución real de microsegundos.
- **NB04:** IF falta una lectura, cambia nacimiento/PID o se pierde la identidad
  THEN SHALL borrar la clave expuesta y fallar permanentemente, preservando la
  primera causa. Volver a valores anteriores SHALL NOT recuperar la instancia.
- **NB05:** WHEN se hereda una instancia mediante fork THEN SHALL rechazar la
  identidad heredada en el hijo; el padre SHALL conservar su identidad. WHEN se
  inicia otro proceso mediante exec THEN SHALL obtener otro nonce del sistema.
- **NB06:** WHEN se entrega una clave THEN SHALL distinguirla del manifiesto del
  artefacto y la identidad del peer. SHALL NOT construir una Observation completa
  de IP, satisfacer hechos AP, armar la guardia ni leer RAM del juego.
- **NB07:** WHEN se prueba el núcleo THEN SHALL cubrir PID reutilizado simulado,
  lecturas parciales/fallidas, nonce ausente, tiempos inválidos, overflow,
  inestabilidad, pérdida explícita y terminales, distinguiendo dobles y procesos.
- **NB08:** WHEN se entrega la unidad THEN SHALL compilar en Debug, Release y
  ASan/UBSan, comprobar cobertura del núcleo, conservar SDK/fuentes/recibos y
  añadir ejecución al pipeline host. SHALL NOT declarar ejecutado CI remoto.

## Diseño

El núcleo `ProcessBirth` consume dos puertos estrechos: `BirthSource` para PID y
tiempo, `NonceSource` para entropía. Es de un solo propietario, no copiable ni
movible y no asigna memoria. No mantiene recursos del sistema entre llamadas.
La integración futura debe poseer **una instancia por vida del proveedor** y
serializar su uso; crear instancias por solicitud generaría identidades nuevas
incorrectamente. No hay singleton ni socket incorporado en esta unidad.

`MacOSBirthSource` usa getpid y proc_pidinfo(PROC_PIDTBSDINFO), exige el tamaño
exacto de proc_bsdinfo, valida pbi_pid y vuelve a comprobar getpid. Los campos
pbi_start_tvsec/pbi_start_tvusec se convierten con aritmética comprobada. La
representación birth_ns no implica precisión nanosegundo. `MacOSNonceSource`
usa getentropy sobre dieciséis bytes; no reintenta ni acepta salida parcial.
Los adaptadores borran sus salidas antes de intentar y ante error.

El núcleo sigue `empty → ready → failed` o `empty → failed`. Cada sample devuelve
un valor y una causa; toda salida fallida contiene clave cero. `lose()` permite
al propietario invalidar explícitamente una identidad perdida. No representa
detección de corrupción arbitraria de memoria ni autenticación criptográfica.
La primera lectura rodea la creación del nonce con dos lecturas de nacimiento;
las siguientes comparan ambas contra la clave inicial. fork cambia el PID aunque
herede nonce/estado; exec crea una instancia nueva. La reutilización real de PID
no se fuerza: se prueba mediante un doble y se identifica como tal.

Un proyecto CMake host independiente en tools/observer/native compila la librería
y tests, sin alterar el CMake histórico del candidato SRC88. Linux prueba el
núcleo con dobles; macOS añade los adaptadores y pruebas nativas. Ningún target
Nintendo ni fuente privada de PCSX2 incorpora aún esta librería.

## Tareas y pruebas

1. **NB-T1 / NB01–04,07:** implementar puertos, clave y máquina de estados; tests
   independientes de plataforma y límites numéricos, sin flags de compilación que
   desactiven aserciones en Release.
2. **NB-T2 / NB01–05,07:** adaptadores macOS; comprobar estabilidad en el proceso
   propio, dos hijos iniciados con exec y contraste externo del nacimiento
   mientras siguen vivos; comprobar fork heredado y errores de API con dobles.
3. **NB-T3 / NB06,08:** builds acotados, sanitizadores/cobertura, pipeline,
   evidencia reproducible y custodia. Dejar IP-NATIVE2/3 y admisión abiertos.
