# F02.07 — Diagnóstico tipado PT v2 (SRC105)

Se completa **PT-T5a** mediante [PD01–PD08](../../schemas/platform-diagnostic-v1.md):
solicitud limitada, respuesta de alcance explícito y consumidor separado del
diagnóstico IP estricto. PT-T5b (peer/sesión) y PT-T5c (deadline/cancelación y
gates del emulador) permanecen pendientes. No se habilita captura.

## Implementación

El codec C++ puro usa almacenamiento fijo: solicitud de 32 bytes y respuesta de
294, con versión PD v1 y perfil PT v2. El lanzador fija política/aplicación/
plataforma; la solicitud contiene únicamente desafío y secuencia. No permite
seleccionar perfil, archivos o política desde el cliente. Se rechazan versiones,
perfiles y evidencias cruzados sin fallback.

La respuesta conserva nacimiento/nonce, hashes, revisión y conteos, además de
`application_headers` y `platform_assumed`. Los dieciocho hechos AP se asocian
a época host y generaciones PINE/VU/GS. Sin esa observación runtime, los cuatro
campos deben ser cero y todos los hechos desconocidos. Valores internos AP no
reconocidos se normalizan a desconocido; valores wire no reconocidos se rechazan.

El consumidor Python devuelve `UnverifiedPlatformDiagnostic` o
`UnverifiedDiagnosticRejection`. Esos tipos no se convierten en `Observation` IP
ni se conectan a admisión/coordinador. Un rechazo conserva solo correlación y
causa; su payload queda vacío. Los errores del encoder limpian el buffer.

Formato, política, proveedor y futuro transporte tienen responsabilidades
separadas. El codec solo comprueba los datos suministrados: no autentica el peer,
evita replays ni acredita que los hechos se obtuvieron en una frontera CPU válida.
Incluso dieciocho hechos satisfechos producen únicamente diagnóstico no autenticado.

## Validación

| Validación local | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan y cobertura, x86_64 | 332 escenarios por modo; 1328 ejecuciones correctas |
| Escenarios C++ nuevos / anteriores | 9 / 323 |
| Codec C++ | 86/86 líneas, 106/108 ramas |
| Python: codec, IP y supervisor | 230 pruebas correctas, 120 nuevas |
| Consumidor Python | 76/76 sentencias, 6/6 ramas |
| Regresiones deliberadas | Cuatro detectadas: perfil, evidencia, época y limpieza de salida |

Un vector fijo construido con `struct` de Python verifica bytes exactos del
encoder C++, incluido endian y offsets; el consumidor comprueba sus campos
independientemente. Se ejercitan todas las truncaciones de solicitud/respuesta,
extensiones, cada byte de correlación, datos reservados, unión, cada hecho AP,
generaciones parciales, capacidades, valores extremos y rechazos sin payload.
El pipeline host recoge los targets nuevos mediante CMake; la suite Python los
recoge automáticamente. No se ejecutó CI remoto, Linux ni arm64.

Se conservan una recolección inicial fallida por usar el nombre reservado
`request` en parametrización pytest (corregida a `input_request`) y una corrida
con seis fallos del supervisor porque el sandbox denegó `/bin/ps`. La repetición
con acceso al inventario de procesos pasó, sin cambiar el supervisor. El código
del codec no produjo esos seis fallos. La cobertura nativa conserva el aviso
previo de quince definiciones inline sin perfil; el objeto nuevo se inspecciona
por separado, sin avisos propios de cobertura.

## Composición en candidato privado

Una nueva copia de PCSX2 ejecuta únicamente `-testconfig`. El manifiesto fija
26 archivos antes de lanzar e incluye el observador nuevo; los 200 archivos del
bundle coinciden con la referencia antes y después. No se ejecutan BIOS, ISO o VM.

Al arrancar se observan 23 imágenes de aplicación y 534 de plataforma; al cerrar,
26 y 621. Se serializan tres muestras por fase: seis respuestas y seis rechazos
vacíos. Python decodifica las seis y contrasta cada identidad con su muestra PT.
Todos los hechos runtime son desconocidos y las generaciones quedan sin observar.

En cada muestra, el productor rechaza perfil v1, evidencia de política alterada
y hechos runtime sin época: 18 controles. El consumidor rechaza diez variantes
por muestra, incluidas versión/perfil desconocido, tres evidencias, correlación,
alcance y hechos sin época: 60 controles. Estos negativos son perturbaciones
locales del mensaje; no equivalen a autenticación de un socket real.

Los inventarios tardaron 814–891 ms por muestra. Es una ejecución local, no una
cota de latencia. Los presupuestos 5 s inicial/2 s revalidación siguen pendientes
de cumplimiento y cancelación en el integrador. La sonda conserva el límite
externo de laboratorio de 60 s; no demuestra el deadline productivo.

## Custodia y siguiente tarea

La [evidencia](../compatibility/platform-diagnostic-evidence.json) conserva hashes,
JUnit, cobertura, controles y límites. Se preservan los 86 inputs anteriores y
una copia de 86 fuentes/fixtures de compilación. Etapas privadas separadas para
build, mutaciones y sonda; reserva/piso 10 GiB, máximo 512 MiB por etapa. No se
recompiló PCSX2 ni se modificó la aplicación instalada o la copia anterior.

Sigue **PT-T5b**: autenticar el interlocutor por el sistema operativo y vincular
el canal a nacimiento/nonce, desafío, secuencia, inventario y evidencias. Probar
reinicio, reuso de PID, replay, desconexión y cambio transitorio como fallos
terminales. Después PT-T5c deberá probar cancelación y callbacks tardíos fuera del
hilo CPU y completar gates JIT/DMA/escritores/ciclo de vida. La captura sigue cerrada.
