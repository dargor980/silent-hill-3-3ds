# F02.07 — Peer y sesión de diagnóstico (SRC106)

Se completa **PT-T5b / PD-T4** mediante [PS01–PS09](../../schemas/diagnostic-peer-v1.md):
identidad nativa del interlocutor, canal Unix propio y sesión terminal ligada a
PD v1/PT v2. El presupuesto completo y la cancelación asíncrona siguen en PT-T5c;
captura y admisión permanecen deshabilitadas.

## Implementación y alcance

El lector C++ comprueba conexión Unix stream, PID, credenciales, token de auditoría
y nacimiento del proceso en dos lecturas. Contrasta el token con el proceso vivo
mediante `proc_pidpath_audittoken`; descarta la ruta obtenida. No usa nombres de
archivo, PID aislado o afirmaciones del mensaje como autenticación. Ante un error
o diferencia devuelve ausencia de identidad y limpia la salida.

La API valida PID/version del token; el socket puede devolver un token consultado
del proceso en ese momento. Por ello se relee y compara en cada frontera, sin
asumir que sea una credencial congelada desde la conexión. Se contrastaron los
headers del SDK local y la semántica publicada de [sockets XNU](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c),
[libproc](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c)
y [consulta de procesos](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c).
Las referencias a `main` no identifican el binario del kernel instalado: las
pruebas locales son la evidencia de comportamiento en este equipo.

`NativePeerReader` adapta el bridge local de 56 bytes; `UnixDiagnosticChannel`
posee un socket y maneja IO acotado; `PlatformDiagnosticSession` mantiene política,
correlación y línea base. La política, PID/nacimiento/UID esperados y helper se
eligen localmente. El proveedor remoto no puede seleccionar otro perfil o lector.

La sesión genera desafío aleatorio y secuencias consecutivas, comprueba el peer
antes/después de cada respuesta y enlaza PID/nacimiento PD con el kernel. Después
fija nonce, hashes, revisión, conteos y épocas. Replay, cambio, rechazo, error,
reentrada, fork, otro hilo o cierre borran la última observación y conservan la
primera causa. No reconecta ni acepta volver a la identidad anterior.

Un `PeerBoundDiagnostic` es una observación histórica del canal y de las cabeceras
de aplicación, con plataforma asumida. No equivale a integridad de toda la memoria,
snapshot atómico, exclusión de ABA ni permiso vigente. El SO y el adaptador del
proveedor siguen siendo parte de la base de confianza. La sesión no pretende
resistir un proveedor malicioso ni detectar cambios no observados entre lecturas.

## Validación

| Validación | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan, cobertura x86_64 | 339 escenarios por modalidad; 1356 ejecuciones correctas |
| Escenarios C++ nuevos / anteriores | 7 / 332 |
| Lector nativo C++ | 70/70 líneas; 83/100 ramas |
| Python: sesión, canal, PD, IP y supervisor | 335 pruebas correctas; 105 nuevas |
| Sesión Python | 125/125 sentencias; 32/32 ramas |
| Canal/bridge Python, incluyendo oráculo nativo | 85/85 sentencias; 26/26 ramas |
| Regresiones deliberadas | Cuatro detectadas: nacimiento estable, token vigente, tamaño exacto y limpieza |

Las pruebas reales incluyen dos procesos, cierre del peer y `exec`: PID y nacimiento
se mantienen, el token/version cambian y consultar con el token anterior falla.
Reuso de PID, cambios transitorios, metadatos imposibles y errores de APIs se
ensayan mediante dobles; no se forzó reuso real de PID. Los tests de sesión cubren
identidad en ambas fronteras, cada campo de la línea base, replay, épocas, cierres,
reentrada y callbacks síncronos después de cancelar/cerrar. Estos callbacks no
constituyen la cancelación asíncrona productiva pendiente.

El oráculo Python carga y ejecuta el helper arm64 contra sockets locales, incluida
la limpieza ante desconexión y doce entradas negativas. Se incorpora al pipeline
macOS sin sanitizadores; la suite nativa cubre el helper con sanitizadores en su
propio ejecutable. No se ejecutó CI remoto ni Linux. El port Nintendo no cambia.
La cobertura global conserva el aviso anterior de quince definiciones inline;
el objeto nuevo exporta cobertura de forma aislada sin avisos.

## PCSX2 privado y controles

Una nueva copia de 200 archivos ejecuta nueve perfiles `-testconfig`, sin BIOS,
ISO ni VM. El manifiesto fija 26 archivos, incluido el observador, antes de lanzar.
Los hashes del candidato y del manifiesto permanecen iguales tras cada ejecución.
La política referencia el snapshot PS previo a marcar tareas completas.

El lanzador escucha en un directorio temporal privado. El candidato se conecta
y contrasta PID/nacimiento/token del lanzador; el consumidor contrasta el proceso
recién lanzado antes/después de cada mensaje. La ejecución positiva acepta tres
muestras de una misma sesión, con nacimiento/nonce/token, inventarios y revisión
estables. Los hechos runtime siguen desconocidos, sin épocas observadas.

| Caso | Muestras aceptadas antes del terminal | Causa |
| --- | ---: | --- |
| Positivo, cierre explícito | 3 | closed |
| Replay | 1 | message_invalid |
| Nonce cambiado | 1 | identity_changed |
| Perfil v1 | 1 | message_invalid |
| Evidencia alterada | 1 | message_invalid |
| Desafío alterado | 1 | message_invalid |
| PID alterado en PD | 1 | process_mismatch |
| Desconexión deliberada | 1 | channel_unavailable |
| Expectativa de otro peer | 0 | peer_mismatch |

Los mensajes alterados son controles propios de la sonda, aplicados tras adquirir
el inventario. No se atribuyen esos cambios al estado real de PCSX2. La prueba de
peer incorrecto usa una expectativa local deliberadamente distinta. Todos los
procesos terminan con código cero; el auditor evalúa las causas internas, no usa
ese código como prueba de admisión. La instancia terminal no vuelve a consultar.

## Custodia y siguiente tarea

La [evidencia](../compatibility/diagnostic-peer-evidence.json) conserva resultados,
hashes, controles y recibos. Se verifican los 98 inputs anteriores, 89 archivos de
compilación y 132 binarios finales x86_64; el helper arm64 de la sonda se registra
aparte. Reserva/piso 10 GiB, máximo 512 MiB por etapa y procesos supervisados.
No se recompiló PCSX2 ni se modificó la aplicación instalada o las copias anteriores.
La primera auditoría esperaba 36 comandos supervisados; el registro contiene 35
(14 de build/cobertura, ocho de mutaciones y trece de la sonda). Se conserva ese
auditor y se corrige su expectativa en una nueva versión, sin cambiar los recibos.

Sigue **PT-T5c / PS-T4**: mover la integración fuera del hilo CPU, imponer 5 s
iniciales incluyendo preparación y 2 s por revalidación, verificar cancelación,
callback tardío y cierre completo, y unir los gates del emulador. El canal actual
solo limita espera de IO por intercambio; eso no acredita el presupuesto total.
JIT, DMA, escritores, exclusión y ciclo de vida siguen siendo requisitos para captura.
