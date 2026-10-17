# Diagnóstico prolongado y cierre G01 — F01.08

**Estado: pendiente; ninguna sesión física de treinta minutos registrada.** Target: New Nintendo 2DS XL con Homebrew Launcher. [Contrato de automatización](build-contract.md). Este ensayo usa solo el programa y fixture sintéticos. No acredita navegación, slice ni rendimiento del juego; PERF-EARLY exige sus sesiones por separado.

## Preparación

1. Elegir una carpeta de build completo con `artifact-check.json`. Verificar desde el checkout correspondiente mediante `python -m tools.qa.build_artifacts --directory CARPETA --probe tests/fixtures/synthetic/probe.txt --sdk-image toolchains/devkitpro-image.txt`. No usar `--record` para corregir un fallo. Conservar también el recibo y sus hashes originales.
2. Registrar ID/sha del 3DSX y ELF, imagen SDK, fecha, operador, firmware, versiones de Homebrew Launcher/Luma, mapeos, alimentación y SD utilizada. Desconocidos como `null`; no inferir CPU/reloj/B_app del emulador. Copiar solo el 3DSX, SMDH y `probe.txt` a `/3ds/sh3_diagnostic/` de la SD. Mantener símbolos/manifiestos en el host.
3. Archivar una copia de esta hoja en una carpeta nueva bajo `build/hardware-sessions/ID-DE-SESION/`. Si ya existe, usar otra. Identificar opciones iniciales y verificar lectura del fixture y audio READY. Conservar los códigos si hay fallos; no cambiar firmware ni importar recursos del juego para forzar un PASS.
4. Preparar reloj externo para medir duración, más fotografías o video con referencias a los checkpoints. El reloj del host/emulador, el ring de 120 muestras y el contador de frames no son evidencia histórica de una sesión física.

## Sesión de treinta minutos

Iniciar el cronómetro con la aplicación visible y el diagnóstico operativo. Mantener al menos **1800 segundos activos** en la misma ejecución. Registrar hora inicial/final y tiempo activo por separado. Detener el cronómetro durante tapa cerrada, HOME, pausa A u otras interrupciones, y ampliar el tiempo total para completar 1800 segundos activos. Documentar cada interrupción. No unir sesiones separadas tras una salida o reinicio.

| Minuto activo | Acción y evidencia requerida | Tiempo real / observado / captura |
|---|---|---|
| 0 | Patrón visible, build correcto, fixture válido, Load/Save, NDSP/Result y escucha real; snapshot de recursos | pendiente |
| 5 | A pausa/reanuda; comprobar imagen, controles y tono; registrar pausas y reinicio de ventana | pendiente |
| 10 | X cambia mute y guarda; salir de mute; Y restaura opciones predeterminadas. Guardar resultados de I/O | pendiente |
| 15 | Tapa desde running y paused; volver, soltar botones y comprobar estado/audio. Excluir tiempo inactivo | pendiente |
| 20 | HOME y retorno si el entorno lo permite; registrar disponible/no disponible y preservar estado; excluir interrupción | pendiente |
| 25 | SELECT: capturar recursos y p95/n/unavailable después del calentamiento; comparar pools con minuto 0 sin sumar pools | pendiente |
| 30 o más | Confirmar duración activa y comportamiento de imagen/tono/controles; capturar estado y salir con START; registrar launcher de retorno | pendiente |

Las capturas periódicas son evidencia de observación manual, no telemetría continua. Registrar inmediatamente cualquier congelamiento, salida inesperada, error de archivo o pérdida de audio, con minuto activo y último checkpoint. Conservar fallos y repetir en sesión nueva después de corregir. Un audio no disponible impide aprobar la parte de audio aunque el resto permanezca activo.

## Registro y decisión

| Campo | Valor inicial |
|---|---|
| session_id / operador / fecha | pendiente |
| execution_kind | physical_not_tested |
| build_id / 3dsx_sha256 / elf_sha256 / recibo_sha256 | pendiente |
| hardware | New Nintendo 2DS XL, confirmado por el usuario |
| launcher / versión / firmware / Luma | Homebrew Launcher / null / null / null |
| CPU clock / B_app | null / null |
| inicio / final / tiempo activo / tiempo interrumpido | null / null / null / null |
| reinicios / salidas inesperadas / defectos | pendiente; no sustituir por cero sin ejecución |
| geometría / controles / archivos / escucha / retorno | not_tested en cada categoría |
| checkpoints y archivos de evidencia | pendientes |
| error simbolizado: build, entorno, pasos, stack, fuente y evidencia | pendiente para el build de esta sesión |
| veredicto / responsable / motivo | pending / pendiente / sin ejecución física |

Aplicar además H01-H12 de [ciclo de vida](lifecycle-probe.md) y las guías de [recursos](resource-probe.md), [audio](audio-probe.md), [archivos](file-probe.md) y [depuración](debugging.md). Esas guías conservan builds históricos: reemplazar sus referencias en la hoja de sesión por el bundle elegido, sin mezclar ELF y 3DSX. Para el error simbolizado, reproducir un error recuperable previsto y conservar backtrace/archivo/línea del mismo ELF; registrar si se obtuvo en emulador o consola. No provocar corrupción de SD ni cortar energía. El caso emulado de F01.05 sigue siendo evidencia histórica, no del build nuevo.

G01 solo puede evaluarse con build limpio, ensayo físico completo, categorías aprobadas, error simbolizado vinculado, perfil/launcher y recursos registrados. Una restricción de HOME requiere resolver compatibilidad de ese entorno; `unavailable` no equivale a PASS. F01.02-F01.07 conservan sus criterios específicos. Las pruebas host/SDK doubles y la validación de artefactos nunca cambian automáticamente `hardware_execution` ni el estado de G01.
