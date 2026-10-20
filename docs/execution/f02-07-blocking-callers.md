# F02.07 — Llamadores bloqueantes y dependencias (SRC86)

Fecha: 2026-10-18. Contrato [BC01–BC07](../../schemas/blocking-callers-v1.md).
Esta unidad examina la copia SRC85 sin modificarla. La cancelación prioritaria
está probada; permanece pendiente demostrar el progreso de los cuerpos concretos
que se ejecutan después de retirar las retenciones.

## Inventario fijado

La búsqueda y clasificación registra 108 referencias RunOnCPUThread: dos
corresponden a declaración/definición y 106 a llamadas. De estas, 102 omiten el
argumento block, dos pasan false y dos true. Se fijan 27 archivos, siete usos de
BlockingQueuedConnection y tres referencias closeInputSources. El inventario
abarca .cpp/.h de pcsx2 y pcsx2-qt, incluyendo ramas de otras plataformas; no es
un grafo de llamadas generado por el compilador ni prueba de alcanzabilidad.

| Ruta | Hecho comprobado en la fuente | Estado |
|---|---|---|
| SetupWizardDialog y AchievementSettingsWidget | Sus botones de logout llaman CPU con true; no conservan un lock explícito alrededor de esa llamada | Scope externo cubierto; cuerpo Logout pendiente |
| Achievements::Logout | Puede tomar el mutex recursivo de logros, borrar estado, adquirir locks de ajustes/secretos y guardar secretos | No probado como no bloqueante; no se ejecutó una cuenta real |
| ClearGameInfo | Puede encolar ClearUIState a GS mientras Logout conserva el mutex de logros | Requiere comprobar capacidad de cola y dependencias inversas |
| DrawGameOverlays / FullscreenUI | La ruta de render de logros adquiere el mismo mutex después de comprobar estado/opciones | Existe dependencia compartida; un deadlock completo no se ha reproducido aquí |
| CommitBaseSettingChanges | Desde CPU encola el guardado a UI sin true; UI programa un timer | Esta llamada particular no es una espera síncrona CPU→UI |
| MainWindow::recreate | Espera modo surfaceless bombeando eventos y después llama closeInputSources antes de reemplazar la ventana | Ruta bloqueante cubierta; recreación QWidget y backends no ejecutados |
| closeInputSources externo | Mantiene el destino anterior reloadInputDevices | La conservación del retorno no demuestra cierre real de dispositivos |
| InputManager::ReloadDevices | Invoca métodos virtuales de los backends inicializados | Dependencias de SO/dispositivo desconocidas |
| observer::dispatch | Encola CPU con false y después espera Completion hasta 2 s | Espera independiente del scope Qt; requiere analizar su reserva PINE |

## Reserva de la ruta PINE

El llamador productivo encontrado admite Work antes de interpretar comandos y
rechaza si el gate no permite entrada. Pasa esa reserva a dispatch; el callback
la captura y la conserva hasta ejecución o descarte, incluso si el llamador ya
agotó su espera Completion. Mientras exista ese Work, PINE no puede llegar a
held y el coordinador no debe iniciar la retención VU/GS. La fase PINE sigue
permitiendo despachar CPU para completar trabajo anterior.

Esto es una comprobación estática del camino concreto, apoyada en los contratos
ya probados; falta el ensayo del servidor PINE real junto al nuevo coordinador.
La API interna dispatch todavía permite una reserva vacía por defecto. No se
extrapola la cobertura del llamador encontrado a otros usos futuros de esa API.
No se elimina el parámetro ni se cambia el wire protocol en esta unidad.

## Ensayo del límite

La [fixture](../../tests/fixtures/pcsx2-blocking-callers/README.md) ejecuta un
callback libre y otro con mutex poseído por un hilo adversario: seis ejecuciones
normales/ASan-UBSan/TSan. En el segundo, CPU ya retiró VU/GS/PINE pero el cuerpo y
UI siguen pendientes hasta que el dueño del mutex lo libera. Se comprueban datos,
entrega única, retorno síncrono y nuevo intento posterior. No se acepta timeout
como éxito ni se usan supresiones TSan.

La prueba demuestra por qué el estado cancelled no acredita disponibilidad
universal de UI. No reproduce Logout, credenciales, red, backend de dispositivos
ni QWidget completo. No se inicia VM ni captura nueva. Fuente, núcleo y CMake
permanecen sin cambios; la regresión host y el candidato SRC85 no se recompilan.

## Resultado y continuación

IW-CALLERS1–3 quedan documentadas en su alcance acotado. Dos auditorías fijan
referencias, cuerpos por hash/rango, fixtures, recibos y custodia SRC85. La
admisión permanece vacía; F02.07 y sus gates generales siguen abiertos.

La siguiente unidad IW-PINE-JOINT debe ejecutar el servidor PINE real y sus
comandos en una etapa aislada: petición anterior al cierre, nueva petición
rechazada, callback encolado, timeout del llamador con trabajo todavía vivo y
parada/reinicio. Debe unir esos hechos al coordinador sin leer memoria de una VM
sin exclusión acreditada. Después se podrá decidir qué hechos concretos del
perfil dejar de marcar como desconocidos; los locks/backend y RDebug conservan
su rechazo hasta demostración propia.
