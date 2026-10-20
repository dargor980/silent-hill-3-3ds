# F02.07 — Identidad y perfil de diagnóstico (SRC90)

Fecha: 2026-10-18. Contrato [IP01–IP09](../../schemas/process-diagnostic-v1.md).
Continúa [SRC89](f02-07-rdebug-artifact.md) y distingue inventario estático,
consumidor probado con dobles e integración nativa todavía pendiente.

## Identidades encontradas y decisión IP-1

| Identidad | Evidencia actual | Límite |
|---|---|---|
| Artefacto | SRC88 fija el candidato; SRC89 examina 42 Mach-O | El hash del archivo no demuestra qué mapping ejecuta un proceso |
| Versión mostrada | El svnrev.h generado tiene GitRev Unknown y GitHash vacío | Ni siquiera identifica el commit; tampoco describiría los cambios privados |
| PID | El lector OBS1 obtiene getpid | Puede reutilizarse tras terminar el proceso |
| Sesión OBS1 | Request.session llega por la solicitud | Correlación del cliente, no nonce del proveedor |
| Época VM | HostEpoch empieza en 1, avanza antes de lifecycle y agota a 0 | Es local al proceso; no identifica un arranque nuevo ni sincroniza RAM |
| Generación PINE | Época propia, avanza en Initialize/Deinitialize | Distingue el servidor dentro del proceso, no otro ejecutable |
| Generaciones VU/GS | WorkerControl conserva generación y estado online | Lifecycle de workers; no sustituye tokens retenidos o exclusión global |
| Anclas RAM/vmap | Snapshot valida punteros y rango | Direcciones reutilizables; no identidad de objeto a lo largo del tiempo |
| CRC del juego | Snapshot incluye game_crc | Identifica contenido de forma auxiliar, no proceso, build o continuidad |
| Guardia AC02 | Hash de disco/perfil, ps con hora de inicio, lsof con ruta txt | Inicio textual con segundos, sin nonce ni identidad de mappings/dependencias |

La decisión es conservar AC02 como guardia de su flujo exploratorio y construir
un puerto separado para el diagnóstico nuevo. El consumidor no interpreta JSON
del cliente como evidencia. El adaptador nativo debe obtener PID/nacimiento,
nonce propio, identidades de archivos, inventario real del cargador y sus cambios,
además de las generaciones; debe comprobar la identidad del peer. Está pendiente.

Reemplazar el ejecutable con los mismos bytes cambia el objeto de archivo y debe
descartar el intervalo. Reemplazarlo mientras corre no modifica necesariamente
el mapping ya cargado: una nueva lectura de la ruta no basta. Reiniciar exige
otro nonce incluso si coinciden PID, época y generaciones. Una dependencia
desconocida o una carga/descarga también invalida; las bibliotecas del sistema
requieren evidencia separada del manifiesto de 42 imágenes empaquetadas.

## Matriz IP-2

No se llamó al sampler en una VM durante esta unidad. Por tanto, los dieciocho
hechos runtime permanecen **desconocidos** en esta evidencia. La columna de
restricción estática describe lo que el código exige o impediría satisfacer;
no se publica como si se hubiera observado bajo exclusión.

| Hecho AP | Restricción estática / evidencia disponible | Runtime |
|---|---|---|
| cpu_thread | El sampler rechaza otros hilos antes de leer estado no atómico | Desconocido |
| cpu_boundary | Exige alcance CpuBoundary, antes de seguir leyendo | Desconocido |
| paused | Exige VMState Paused; no prueba ausencia de writers | Desconocido |
| implementations_settled | Exige ausencia de transición de implementación | Desconocido |
| ee_interpreter | Configuración y puntero de intérprete, sin GS replay | Desconocido |
| iop_interpreter | Configuración y puntero de intérprete | Desconocido |
| vu0_interpreter | Configuración y puntero de intérprete | Desconocido |
| vu1_interpreter | Configuración y puntero de intérprete | Desconocido |
| ee_cache_disabled | Debe desactivar EE cache | Desconocido |
| fastmem_disabled | Debe desactivar fastmem | Desconocido |
| mtvu_disabled | Debe desactivar MTVU | Desconocido |
| vif_dynarec_disabled | **Violada por el build fijado:** newVifDynaRec es true | Desconocido; si llega a esa comprobación, el sampler dará violado |
| raintegration_disabled | Exige RAIntegration inactiva | Desconocido |
| pine_excluded | PINE configurado o inicializado produce violado; parado deja desconocido | Desconocido |
| rdebug_excluded | SRC89 satisface ausencia en el artefacto examinado; sin vínculo runtime | Desconocido |
| gs_drained | Hay control/coordinador probado; el sampler aún no lo promueve | Desconocido |
| vu_drained | Hay control/coordinador probado; el sampler aún no lo promueve | Desconocido |
| other_writers_excluded | Locks, backend y compuesto completo siguen sin cobertura | Desconocido |

El sampler productivo permanece intacto y no concede admisión. Desactivar VIF
dinámico exigiría otro candidato y validación específica; este informe no cambia
la constante para hacer pasar el perfil.

## Consumidor IP-3

El módulo propio `process_diagnostic` separa datos inmutables, puerto de lectura
y evaluación. Solo admite un intervalo. Una lectura ausente, cambio de identidad,
manifestación inválida, perfil incompleto o error del puerto descarta el resultado
y conserva la primera causa. Volver al valor anterior no revive la instancia.
Los informes completos son históricos y diagnósticos; no incluyen capacidades.

Las 87 pruebas nuevas cubren cada campo de identidad, PID reutilizado mediante
cambio de nacimiento/nonce, sustitución por otro objeto de archivo, dependencias,
revisión del cargador, épocas/generaciones, pérdida del puerto, desconocidos,
agotamiento, datos malformados, cancelación y terminales. Contrasta los dieciocho
nombres AP con el enum C++. Todas usan un doble del puerto: **no prueban aún
la identidad de un proceso PCSX2 real ni el transporte del proveedor**.

La suite se integra por el descubrimiento pytest existente y los comandos Ruff
de CI. El primer intento de regresión conserva seis fallos del supervisor por
denegación de `/bin/ps` en el entorno restringido; los 87 tests nuevos pasan y
cubren 109 líneas y 36 ramas, ambas al 100 %. Se repite la suite con acceso a la
tabla de procesos y se conservan ambos recibos. No modifica CMake, código del
proveedor, instalación o candidato. La segunda ejecución solo falló en el gate
documental por dos enlaces añadidos antes de publicar la evidencia; se corrige
ese orden y se conserva una tercera ejecución completa: **3.183 tests aprobados**,
Ruff y gate de cobertura correctos. La
custodia comprueba la fuente privada actual, el historial SRC88, los 42 binarios
y los insumos congelados de SRC89; dos publicaciones iguales fijan el resultado.

## Continuación necesaria

IP-1–3 cierra inventario, decisión, matriz y consumidor diagnóstico con dobles.
**IP-NATIVE** sigue abierto: prueba de nacimiento/nonce, archivos y mappings
en un proceso propio; notificaciones de carga/descarga; vinculación del canal;
integración en una nueva copia privada de PCSX2 y muestreo dentro del coordinador.
La integración deberá rechazar las imágenes externas no acreditadas y los
intentos de usar valores del cliente como prueba del proveedor. Después siguen
VIF/escritores, frontend/VM y AD-3. No hubo VM, captura ni Read del juego.
