# Contrato del tono sintético — F01.04

Deriva de RF08.06/RF14.01; estos criterios locales precisan la prueba diagnóstica, sin añadir formatos ni audio de SH3.

| Criterio EARS local | Aceptación verificable |
|---|---|
| C01: WHEN se crea el tono THEN el adaptador SHALL generar PCM16 mono propio de 440 Hz, 22050 muestras/s y un segundo, limitado a ±2048 | Un único bloque lineal de 44100 bytes y un buffer en bucle en canal 0; mezcla frontal L/R de 0.5 |
| C02: IF falla NDSP THEN el diagnóstico SHALL mostrar `NDSP_INIT_FAILED`, etapa y Result original sin consultar ni cerrar un servicio no adquirido | Sin asignación, cola ni lectura de contadores |
| C03: IF falla la reserva THEN el diagnóstico SHALL mostrar `PCM_ALLOC_FAILED` y Result no aplicable, y liberar NDSP | Sin inventar un código del SDK ni añadir buffers |
| C04: IF falla el flush de caché THEN el diagnóstico SHALL mostrar `CACHE_FLUSH_FAILED` y el Result original, y liberar NDSP antes del PCM | Sin configuración ni envío de cola después del fallo |
| C05: WHEN la configuración y el envío terminan THEN el diagnóstico SHALL mostrar `READY`, build y escena, sin declarar aprobada la escucha | `ndspChnWaveBufAdd` no tiene resultado; READY significa preparación local completada |
| C06: WHILE el tono está preparado THEN el diagnóstico SHALL mostrar frames NDSP, frames descartados y posición de muestra obtenidos del SDK | Valores brutos u32; pueden volver a cero, desbordar o circular; no son segundos audibles ni prueba de reproducción |
| C07: WHEN se solicita pausa, mute o suspensión THEN el adaptador SHALL aplicar la pausa al canal y evitar llamadas repetidas con el mismo valor | Mute inicial antes de encolar; reanudación respeta opciones y estado de aplicación; fallo hace pause inocuo |
| C08: WHEN se destruye el tono THEN el adaptador SHALL retirar su cola, finalizar NDSP y liberar PCM en ese orden | Descriptor y PCM vivos hasta terminar NDSP; liberación única también en fallos parciales |

## Diseño y alcance

`Tone` posee el servicio NDSP, el bloque lineal y el descriptor no copiable. Es el único propietario NDSP/canal 0 de esta aplicación diagnóstica; no admite instancias simultáneas. Genera una señal fija una sola vez, sin asignaciones por frame, callbacks de audio propios ni un mezclador anticipado. Los fallos parciales liberan inmediatamente lo adquirido y conservan su estado para la vista. La vista consulta un snapshot de diagnóstico; el dominio no recibe cabeceras ni tipos SDK.

Se conserva el orden clear → exit → free: clear solicita retirar la cola; exit espera el hilo NDSP y finaliza DSP antes de que desaparezca la memoria. Los contadores se leen individualmente, sin prometer un snapshot atómico entre ellos. Frames NDSP puede avanzar con el canal pausado y reiniciarse tras sleep; posición circula por el buffer. No se deriva duración ni progreso de esos valores.

Fuentes primarias: [cabeceras NDSP](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/ndsp/ndsp.h), [canales](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/ndsp/channel.h), [flush DSP](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/services/dsp.h) y [ciclo de vida NDSP](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/ndsp/ndsp.c), contrastadas con el SDK fijado. El contrato se limita a errores retornados por las APIs; no convierte abortos o bloqueos internos del SDK en errores recuperables.

## Verificación

La suite host compila `tone.cpp` real contra funciones SDK controladas y valida PCM, configuración, contadores, mute y propiedad. La composición tiene su propia suite para salida visible y ciclo de vida; sus dobles no acreditan el DSP. El build ARM valida las declaraciones reales del SDK. La escucha, legibilidad, suspensión y retorno requieren la consola; ni un contador positivo ni `READY` cierran esa aceptación.
