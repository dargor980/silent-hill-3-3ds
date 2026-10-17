# Prueba física F01.04: tono y servicio de audio

Estado: **no ejecutada**. Destino: New Nintendo 2DS XL y Homebrew Launcher. [Contrato EARS](audio-contract.md) y [evidencia local](../execution/f01-04-audio.md). F01.02/hardware, F01.03/hardware y G01 permanecen abiertos.

## Preparación e identidad

Copiar `build/f01-04/artifacts/sh3_diagnostic.3dsx` y `probe.txt` a la carpeta existente `/3ds/sh3_diagnostic/` de la SD. Build visible esperado: **632a72b68533**. SHA-256 del 3DSX: `2d24c0744cb6522fdd7994113ac8171b8f0723b01f2c52df5f0ecc06f10a3f8e`. Conservar el ELF del mismo build en el ordenador. El diagnóstico no incluye componentes DSP ni audio original.

Registrar firmware, launcher/versión, fecha, operador, hash transferido y salida usada (altavoces o auriculares); los datos desconocidos siguen pendientes. Iniciar con volumen bajo y ajustarlo a un nivel cómodo. `Tone: off` puede ser una opción persistida; Y restaura/guarda on si los archivos permiten escribir. Si hay error de archivo, anotarlo y resolver la instancia de archivos antes de acreditar mute persistente.

## Casos

| Caso | Acción | Resultado esperado |
|---|---|---|
| Preparación | Abrir y esperar varias actualizaciones | Build correcto, `Audio: READY`, etapa TONE y Result de éxito; patrón gráfico y START disponibles |
| Escucha | Con State running, Tone on, Channel unpaused y volumen audible | Tono continuo propio; registrar si se escucha, interrupciones o ruido. La pantalla mantiene `Listening: NOT_VERIFIED` porque la escucha se registra externamente |
| Contadores | Anotar dos lecturas separadas por unos segundos | SDK frames cambia; anotar Dropped y Pos. Pos circula por el bucle. Valores no prueban escucha ni rendimiento del juego |
| Pausa A | Pulsar A; esperar siguiente actualización; pulsar A otra vez | Pausa silencia y reanudación recupera el tono; Channel refleja pausa solicitada. SDK frames puede seguir avanzando con el canal pausado |
| Mute X | Con sesión ejecutándose, pulsar X; salir y reabrir | Save OK, Tone off, Channel paused, sin tono desde el inicio siguiente; luego Y restaura/guarda on |
| Pausa y opciones | Pausar con A y cambiar X/Y | Las opciones no reanudan una sesión pausada; después A reanuda respetando Tone |
| Sleep activo | Con tono activo cerrar tapa y abrir | Silencio al suspender y reanudación del tono; registrar contador antes/después sin exigir monotonicidad |
| Sleep en mute/pausa | Repetir con Tone off y después con pausa A | Se conserva silencio hasta habilitar/reanudar explícitamente |
| HOME y retorno | Entrar/salir de HOME si está disponible en el launcher utilizado | Suspensión y estado conservado; si el entorno no permite HOME registrar no disponible, sin inventar un resultado |
| Salida/reapertura | START y abrir de nuevo | Retorno controlado, sin tono después de salir; nuevo arranque preparado y opción persistida aplicada |
| Error de audio natural | Solo si ocurre en el entorno real | Código `NDSP_INIT_FAILED`, `PCM_ALLOC_FAILED` o `CACHE_FLUSH_FAILED`, etapa y Result/N/A visibles; START operativo y sin declarar escucha aprobada |

No se provoca fallo retirando archivos DSP, llenando memoria o alterando el sistema de la consola. Los tres fallos de preparación se cubren por inyección host. Un fallo NDSP no identifica por sí solo firmware ausente: conservar Result original y contexto. READY acredita preparación local y envío de buffer, no que se haya reproducido.

## Registro pendiente

| Campo | Observado |
|---|---|
| Modelo, firmware, launcher/versión | New Nintendo 2DS XL; resto pendiente |
| Build/hash, operador/fecha, salida/volumen | pendiente |
| Arranque, legibilidad y escucha | no ejecutado |
| Frames/Dropped/Pos: lecturas antes/después | no ejecutado |
| A, X/Y y reapertura | no ejecutado |
| Tapa activa, mute y pausa | no ejecutado |
| HOME/retorno o motivo de no disponibilidad | no ejecutado |
| START, silencio al salir, siguiente arranque | no ejecutado |
| Errores naturales y evidencia | pendiente |

Guardar resultados fallidos como fallidos y adjuntar build/hash. Para cerrar F01.04/hardware se requiere escucha y comportamiento físico aprobados con dependencias verificadas. T11/F01.07 conserva su campaña completa; estos casos iniciales no sustituyen pruebas de estrés ni estabilidad prolongada.
