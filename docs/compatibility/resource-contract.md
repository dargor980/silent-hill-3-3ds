# Recursos y tiempos del diagnóstico — F01.06

Contrato derivado de RNF02.01/RNF02.03, RF14.02 y RNF01.05. Instrumentación sintética inicial Q13; no certifica B_app ni rendimiento del juego.

| EARS local | Aceptación |
|---|---|
| R01: WHEN se consulta un recurso THEN el diagnóstico SHALL distinguir valor disponible, error SDK, valor inválido y ausencia de medición | Cero válido no equivale a UNKNOWN; Result original conservado |
| R02: WHEN se muestran pools THEN el diagnóstico SHALL identificar capacidad de heap/lineal, libre lineal/VRAM y región APPLICATION sin sumarlos | B_app, heap libre, mayor bloque y CPU MHz permanecen sin medir |
| R03: IF falla la consulta de región o devuelve un uso negativo o superior a su capacidad THEN el diagnóstico SHALL omitir ese uso y conservar el motivo | Sin resta unsigned ni dato inicializado como éxito |
| R04: WHEN se muestra el entorno THEN el diagnóstico SHALL separar flag homebrew, familia New y límite APT de modelo exacto, launcher, versiones y reloj | Cada consulta falible conserva Result; no cambia CPU ni configura servicios |
| R05: WHEN se presenta un frame THEN el diagnóstico SHALL medir por separado espera/SDK de FrameBegin, dibujo/envío y lectura de contadores de audio | Ticks de svcGetSystemTick; no sumar intervalos ni atribuir ejecución GPU/DSP |
| R06: IF el reloj retrocede THEN el diagnóstico SHALL marcar el intervalo inválido sin producir duración unsigned enorme | Cero ticks sigue siendo válido |
| R07: WHILE se recopilan tiempos THEN el diagnóstico SHALL conservar como máximo 120 muestras tras 60 intentos de calentamiento, con rotación y rechazos visibles | Memoria fija; p95 nearest-rank sobre valores válidos, cantidad inválida y retenida explícitas |
| R08: WHEN cambia running/paused o llega suspensión/reanudación THEN el diagnóstico SHALL reiniciar la ventana y el calentamiento | Sin mezclar estados ni medir el tiempo cerrado como frame |
| R09: WHEN se pulsa SELECT THEN el diagnóstico SHALL alternar páginas sin escribir opciones ni alterar pausa | Prioridad START > SELECT > Y > X > A; limpia página anterior |
| R10: WHILE corre el diagnóstico THEN la adquisición de recursos SHALL ocurrir al primer intento de presentación y cada 60 intentos siguientes | Sin reservas exploratorias ni escritura de logs por frame; lifecycle conserva 32 eventos |

## Diseño SOLID

`ResourceProbe` adapta exclusivamente consultas SDK a `ResourceSnapshot`; no decide presupuestos ni modifica el entorno. `TimingWindow` en platform/common conserva y resume muestras con memoria fija, independiente del SDK. La composición mide fronteras conocidas y presenta dos páginas; el dominio y los puertos de juego no incorporan dependencias 3DS. Tests compilan el adaptador real contra dobles SDK y comprueban aparte la composición. ARM usa cabeceras reales.

El snapshot no es atómico: las consultas sucesivas pueden observar cambios entre ellas. Heap y lineal son reservas del proceso; APPLICATION es una región del sistema, no memoria exclusiva de esta app. VRAM libre pertenece al allocator de libctru y no describe todo el uso GPU (también hay buffers lineales). No se calcula total ni mayor bloque contiguo. Se consulta `svcGetSystemInfo` directamente para comprobar Result, porque `osGetMemRegionUsed` no lo comprueba.

Fuentes primarias contrastadas con libctru 2.7.0 del SDK fijado: [env.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/env.h), [os.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/os.h), [linear.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/allocator/linear.h), [vram.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/allocator/vram.h), [apt.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/services/apt.h). El flag homebrew no identifica Homebrew Launcher ni FBI. APT informa familia New, no modelo exacto.

## Protocolo Q13 inicial: diagnostic-v1

- Corpus fijo: dos rectángulos propios, fixture de 16 bytes y tono propio; resolución/plataforma y audio según evidencia de cada sesión. No assets originales.
- Tiempos: duración transcurrida de tres intervalos delimitados en el hilo CPU (puede incluir bloqueo o desalojo), mediante reloj monotónico en ticks; no es utilización CPU ni tiempo activo puro; `SYSCLOCK_ARM11` es frecuencia del contador definida por SDK, no una lectura del reloj CPU. Espera FrameBegin incluye bookkeeping/sincronización/refresco; dibujo/envío incluye FrameEnd; audio-poll solo lee contadores. Simulación, animación, carga/descompresión y ejecución GPU/DSP no están instrumentadas. No hay un total formado sumando subsistemas solapados.
- Sesión comparable: registrar build+hashes, toolchain, modelo, launcher y versiones, CPU conocida/desconocida, audio disponible/mute, estado running/paused y emulador frente a consola. Ventana reiniciada al cambiar estado/suspender/reanudar. No comparar ventanas de perfiles distintos.
- Calentamiento: primeros 60 intentos de presentación de cada estado/epoch. Ventana posterior: últimos 120 intentos; los rechazados cuentan y ocupan su posición, sus intervalos no ejecutados quedan sin medición. El contador de rechazos incluye calentamiento y toda la epoch. No se eliminan fallos para declarar aprobado el rendimiento.
- Estadística: p95 nearest-rank `ceil(0.95*n)`, máximo y número de intervalos válidos; sin percentil si n=0. Pantalla indica n/invalid para cada intervalo. Percentil diagnóstico local de ventana móvil, no percentil de campaña ni FPS.
- Recursos y resumen visible: primer intento y cada 60 intentos de presentación; métricas mostradas corresponden a ese refresco, no necesariamente al frame actual. No se exige equivalencia a un segundo. Se mantienen los valores hasta el siguiente refresco.
- Logs: lifecycle ring 32, timing ring 120; sobrescribe primero lo más antiguo, sin archivo de telemetría ni exportación automática. Capturar lecturas mediante pantalla o debugger con build identificado. Esto no conserva una traza completa de 30 minutos: F01.08 necesitará protocolo de evidencia prolongada.
- Criterios: esta iteración valida límites/errores/contabilidad, no impone umbral de FPS o tolerancia de refresco. No puede aprobar PERF-FRAME/MEM/TRANS ni Q08. El corpus real, tolerancia y presupuestos siguen pendientes para F09/F12.

F01.07 precisa el reinicio por cambios reales de estado: hooks repetidos o wake/restore sin suspensión no reinician la ventana. [Contrato de ciclo de vida](lifecycle-contract.md). El protocolo de muestreo/percentil diagnostic-v1 se conserva.
