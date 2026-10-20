# F02.07 — Nacimiento nativo del proveedor (SRC91)

Fecha: 2026-10-18. Completa **IP-NATIVE1 / NB-T1–3** bajo
[NB01–NB08](../../schemas/native-process-birth-v1.md). Continúa
[SRC90](f02-07-process-diagnostic.md) con procesos propios reales, todavía sin
integrar una identidad completa en PCSX2.

## Implementación y evidencia nativa

El núcleo C++ `ProcessBirth` separa dos puertos: lectura de nacimiento y generación
del nonce. El adaptador macOS obtiene getpid, consulta
proc_pidinfo(PROC_PIDTBSDINFO), exige tamaño completo/PID coincidente y comprueba
getpid nuevamente. Usa los campos de segundos y microsegundos del SDK; el valor
birth_ns conserva esa resolución, aunque esté expresado en nanosegundos.

El nonce de dieciséis bytes procede de getentropy y se crea una sola vez por
instancia. Un fallo o salida cero descarta la identidad, sin fallback. Cada
muestreo valida dos lecturas de nacimiento, comprueba overflow y continuidad.
La pérdida explícita, un error o un cambio deja una causa permanente y una clave
cero. No permite copiar, mover o recuperar la instancia. Su propietario deberá
conservar una instancia por proceso y serializar el acceso.

Se verificó localmente con **Apple Clang 21.0.0, SDK MacOSX26.5 y ejecutables
x86_64 sobre macOS 26.5**. Se registran hashes de headers y de libSystem.tbd,
que declara las APIs usadas; no se copian esos cuerpos al repositorio.

Tres escenarios usan APIs y procesos reales:

1. El proceso propio mantiene PID, nacimiento y nonce en cien revalidaciones;
   la pérdida explícita elimina la clave y queda terminal.
2. Dos hijos nuevos, iniciados con exec mediante posix_spawn, producen claves
   y nonces distintos. El padre contrasta sus PID con los devueltos por spawn y
   consulta externamente su nacimiento mientras los hijos siguen vivos. Un
   intercambio acotado mantiene ese alcance antes de terminarlos y recogerlos.
3. Un hijo creado por fork rechaza el objeto heredado del padre. Una instancia
   nueva del hijo obtiene su propia identidad; el padre conserva la original.

El cuarto escenario macOS inyecta errores en las llamadas: funciones ausentes,
PID inválido, respuesta fallida/corta, PID devuelto distinto, cambio durante la
consulta, tiempo inválido y entropía fallida. Comprueba salidas borradas. Esos
errores son **dobles de API**, no fallos provocados en el kernel.

## Batería de pruebas y pipeline

**22 escenarios × cuatro modalidades = 88 ejecuciones finales correctas**:
18 escenarios del núcleo y cuatro del adaptador, en Debug, Release, ASan/UBSan
y cobertura. Los límites de CTest son de quince segundos por escenario y la
supervisión verifica el cierre de los grupos de procesos. Las aserciones propias
permanecen activas en Release. ASan/UBSan se ejecutó con interrupción ante error;
la detección de fugas se deshabilitó, por lo que no se afirma cobertura de leaks.

La primera etapa privada también pasó 88 ejecuciones. Se conserva completa;
la segunda refuerza el doble de cambio de PID/nacimiento para mantener el valor
nuevo durante toda la consulta. Ambas etapas conservan fuentes, binarios y logs.

Tres controles negativos compilados y ejecutados son detectados:

| Regresión introducida | Test que la detecta |
|---|---|
| No comparar con el nacimiento inicial | Reutilización simulada del mismo PID con otro nacimiento |
| Leer nuevamente después del fallo terminal | Pérdida explícita de identidad ya inicializada |
| Regenerar el nonce durante revalidación | Identidad estable y una única petición de entropía |

LLVM informa **100 % de líneas y ramas** en las dos fuentes de implementación:
41 líneas/50 ramas del núcleo y 23 líneas/20 ramas del adaptador. Esta medición
excluye librerías del sistema y no demuestra su implementación interna.

El proyecto CMake host independiente incorpora esos tests. El nuevo workflow
`native-process.yml` configura Release con y sin ASan/UBSan en Linux y macOS;
Linux ejecuta el núcleo portable y macOS añade el adaptador. Conserva JUnit como
artefacto. Se verificó la ejecución local; **CI remoto y Linux no se ejecutaron
en esta unidad**. El CMake raíz y el workflow previo permanecen intactos.

## Custodia y límites

La reserva de esta prueba pequeña es 10 GiB al iniciar y durante la ejecución,
con etapa acotada a 512 MiB; no es un build completo de PCSX2 sujeto a IB02.
Se conservan recibos de compilación, tests, cobertura y negativos, con fuentes
y hashes de ambas etapas. Dos auditorías reproducibles fijan la evidencia.
El candidato SRC88 y la fuente privada pine-transport v2 conservan sus hashes.

La reutilización real de PID no se forzó: se prueba con un doble que mantiene
el PID y cambia el nacimiento. El nonce distingue instancias; no autentica por
sí solo al emisor ni demuestra que un proceso ejecute el candidato aprobado.
No se comprueba manipulación arbitraria de memoria ni corrupción del kernel.

**IP-NATIVE2** sigue abierto: vincular ejecutable/dependencias con mappings y
cambios del cargador. **IP-NATIVE3** deberá comprobar el peer e integrar la lectura
en el coordinador de una nueva copia privada de PCSX2. No se construye una
Observation completa con esta clave parcial; no se cambia AP, se arma la guardia
ni se lee RAM. No hubo VM, ISO, BIOS o captura del juego en esta unidad.
