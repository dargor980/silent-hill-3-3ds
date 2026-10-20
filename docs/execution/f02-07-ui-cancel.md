# F02.07 — Cancelación desde la interfaz

Fecha: 2026-10-19. Contrato [UC01–UC05](../../schemas/runtime-ui-cancel-v1.md).
Evidencia [SRC124](../compatibility/ui-cancel-evidence.json).

**UC-T1–UC-T4 y RT-T3c.1b.UI completos.** Salir y cerrar la ventana señalan la
cancelación antes de entrar en el apagado de VM. La interfaz conserva su bucle
de eventos; al terminar IO, el timer existente retorna al epílogo, une IO y
después detiene CPU. Pasan doce perfiles con fases observadas, dos comprobaciones
en la interfaz visible sin sonda y un control de funcionamiento normal.

## Hallazgo y corrección

Dos perfiles del candidato base, con la acción Qt Salir durante inventario,
terminan limpiamente pero registran `reason=8` (lifecycle). La señal de
cancelación aparece después de destruir los recursos IO. Esto no se presenta
como bloqueo o corrupción: demuestra que esa ruta cambia el ciclo de vida antes
de pedir la cancelación explícita requerida.

El puerto propio `cancel_runtime_service_from_ui()` reclama la salida únicamente
si el servicio arrancó correctamente. Señala cancelación sin unir hilos ni
esperar CPU. Conserva esa propiedad incluso si IO ya terminó, para que una
petición tardía siga pasando por el epílogo. Si el servicio no está activo, la
interfaz conserva su comportamiento habitual. Las llamadas repetidas no abren
otra sesión ni provocan otro despacho.

La [integración](../../tests/fixtures/runtime-service/ui_cancel_integration.py)
inserta llamadas tempranas en `MainWindow::closeEvent`, `requestExit` y `quit`
de la copia privada fijada. El evento de cierre se ignora mientras el timer
gestiona la salida. La lógica de transporte e inventario permanece separada de
Qt. No se modifica el layout de clases ni los frames PD v2.

## Pruebas con el frontend real

| Fase observada | Cierre de ventana | Acción Qt Salir | Frames previos aceptados por perfil |
| --- | ---: | ---: | ---: |
| Espera inicial sin VM | 2 perfiles | 2 perfiles | 0 |
| Inventario con VM pausada | 2 perfiles | 2 perfiles | 0 |
| Liberación final con VM pausada | 2 perfiles | 2 perfiles | 3 |

Los doce resultados registran `reason=6`, `clean=1`, `admitted=0` y salida cero.
Las trazas verifican acción en UI → señal de cancelación → destrucción de recursos
IO → unión IO → parada CPU. UI retorna sin esperar esa unión. El máximo observado
del retorno del manejador fue 2,31 ms y desde la acción hasta unir IO, 518,09 ms;
son mediciones de esta tanda, no garantías de latencia del sistema operativo.
`inventory=4` al interrumpir el inventario indica que la comprobación de manifiesto
no completó; la causa terminal del servicio es cancelación, no inventario válido.

La sonda privada publica fases con atómicos y un timer UI de 2 ms ejecuta los
eventos Qt reales. No retiene fases ni amplía los plazos. En liberación, un
archivo local fijado de antemano acredita que el consumidor ya validó los tres
frames antes de activar la acción. Esa coordinación no añade mensajes al canal.
Estas ejecuciones programáticas no se presentan como clics físicos.

Además, mediante CUA se pulsaron **el botón de cierre** y **PCSX2 → Salir de
PCSX2** en dos perfiles del candidato **sin sonda**, esperando sin VM. Ambos
registran cancelación, cierre limpio y salida cero. La herramienta observó la
salida de la aplicación y el supervisor confirmó el resultado del proceso.
El orden interno detallado procede de las pruebas con sonda; estas dos acciones
externas no tienen esas trazas.

La primera selección de la aplicación mediante CUA abrió el asistente del perfil
por defecto; se canceló sin cambiar opciones. No cuenta como validación. Los
dos casos supervisados posteriores usaron sus perfiles privados, igual que las
otras pruebas. No se configuró ese asistente ni se cargaron partidas del usuario.

El control sin cancelación del candidato limpio acepta tres respuestas en
1,623/1,428/1,424 s, registra `reason=0` y termina con código cero. Los 15 frames
aceptados entre las pruebas con sonda y este control se decodifican con sus
expectativas locales: 30 imágenes por archivo, 1.040 de caché, revisión 1.071 y
épocas `[53, 3, 1, 1]`. No se modifica el rechazo por plazo de SRC122.

## Compilación y regresiones

La matriz verifica todos los objetos del enlace y las dependencias de 390
miembros de 19 archivos estáticos. La cabecera afecta a QtHost y al servicio;
MainWindow es un consumidor nuevo. El candidato limpio reconstruye esas tres
unidades y reutiliza 467 entradas. La variante observada añade la unidad de
trabajo nativo para marcar la fase de inventario: cuatro reconstruidas, 466
reutilizadas. Los MOC de QtHost/MainWindow conservan los bytes fijados de SRC121.

Los tres bundles verifican firma ad hoc y resolución de frameworks. MainWindow
compila con el observador activado y desactivado; el candidato limpio pasa
`testconfig`. Se preservan dos fallos preparatorios por seleccionar el MOC de
otra copia de fuentes, y un error auxiliar de auditoría que confundía el hash de
`link.txt` con el del archivo estático. Ninguno se presenta como prueba aprobada.

Ejecutable limpio SHA-256:
`b82eb998e2f7d83522d1777a79b77329ea1c9db1e0d35eec10f184f11ceeca3f`.

| Suite | Aprobadas |
| --- | ---: |
| Debug x86_64 | 112 |
| Release x86_64 | 112 |
| ASan/UBSan x86_64 | 112 |
| TSan arm64 | 109 |
| Repositorio y supervisor | 58 |

Total: **445 ejecuciones nativas**. Los tres casos nuevos cubren cancelación
durante espera, sesión activa y llamada después de finalizar; también comprueban
inactividad y repetición. Se registran en CTest y en la batería que ejecuta el
pipeline existente. ASan conserva `detect_leaks=0`; TSan excluye los tres casos
fork/exec ya declarados. Ruff y formato pasan. Las 304 pruebas del consumidor de
SRC122 son evidencia previa de código Python sin cambios, no nuevas ejecuciones.

UC-B mantiene inicio ≥11 GiB, suelo 10 GiB, máximo combinado 512 MiB y 180 s por
comando de build. Los builds completos de esta etapa tardan 42,47/68,76/68,19 s;
la tanda programática restante tras el primer caso dura 84,93 s. El mínimo
observado es 11,24 GiB libres. No se reconstruyen dependencias de terceros ni se
modifican los candidatos anteriores. IB02 general sigue en 20 GiB.

## Límites y siguiente tarea

Faltan cancelación durante **entrega parcial**, el botón **Apagar VM** y callbacks
tardíos/duplicados en Host real. Se mantienen RT-T3c.1b parcial, RT-T3c.1c,
RT-T3c.2 y RT-T3c.3. Esta validación de salida UI no satisface por sí sola los
gates JIT/caché/DMA/lifecycle ni habilita captura. No se ejecutó CI remota, Linux,
build 3DS o captura de RAM del juego.
