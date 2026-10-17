# Ciclo de vida y controles del diagnóstico — F01.07

Contrato local derivado de RF12.01-RF12.03 y RF11.04; V12/T11. Se limita al diagnóstico sintético. No existe todavía simulación de juego, combate, streaming, cinemáticas ni partidas para certificar esas operaciones.

| EARS local | Criterio verificable |
|---|---|
| L01: WHEN A cambia pausa THEN el diagnóstico SHALL alternar running/paused y conservar las opciones | Ningún reloj de juego ficticio; tono pausado en paused y mute respetado |
| L02: WHEN llega suspensión HOME o sleep THEN la aplicación SHALL conservar el estado previo y dejar de consultar entrada/presentar mientras siga suspendida | Sin cambio de página, guardado ni lectura de métricas durante ese estado |
| L03: WHEN llega restore/wakeup después de suspensión THEN la aplicación SHALL recuperar running/paused previo y reiniciar la ventana diagnóstica | El tiempo suspendido no entra como frame; tono se ajusta al volver al bucle, respetando mute |
| L04: IF un hook repite un estado o llega resume sin suspensión THEN el diagnóstico SHALL evitar eventos y efectos de transición duplicados | No reiniciar métricas ni pausar otra vez por un hook redundante |
| L05: WHEN se vuelve de suspensión THEN la entrada SHALL esperar una lectura sin botones nuevos ni mantenidos antes de aceptar acciones | A/SELECT/X/Y/START durante el retorno no alteran estado/opciones/salida; requieren liberación y nueva pulsación |
| L06: IF una lectura contiene botones ajenos al conjunto diagnóstico THEN la entrada SHALL ignorar la combinación y esperar liberación completa | Cubre modificadores mantenidos, no solo recién pulsados; no consume L+abajo+SELECT como SELECT |
| L07: WHEN solo se usan botones diagnósticos THEN la entrada SHALL resolver prioridad START > SELECT > Y > X > A por flanco | Mantener un botón no repite acción; no aplica a combinaciones reservadas bloqueadas por L06 |
| L08: WHEN APT solicita salida o START aceptado termina la sesión THEN la aplicación SHALL mantener stopped terminal y liberar cada recurso una sola vez | Sin entrada/vista/archivos después de salida; hooks posteriores no reviven ni reinician métricas |
| L09: WHEN llega un hook de suspensión/salida THEN el adaptador SHALL evitar iniciar escritura o reconstrucción de recursos desde el callback | Opciones son síncronas en el bucle; finalización RAII después de desregistrar hook |
| L10: WHILE se documentan resultados THEN el proyecto SHALL separar contratos con dobles, compilación ARM y ejecución física | HOME no disponible se registra como tal, sin PASS inferido; no se prometen transacciones resistentes a corte de energía |

## Diseño y política

`Lifecycle` conserva los cuatro estados y la pausa anterior. `DiagnosticApp` bloquea poll/present si ya está suspendida y acepta eventos de plataforma mediante dispatch. El host sintético también reanuda mediante dispatch, sin depender de leer un botón desde un estado inactivo. `Input` interpreta flancos/held y posee únicamente la espera de liberación. `LifecycleHook` traduce eventos SDK y aplica efectos solo al cambiar realmente el estado. El bucle ajusta audio tras volver de APT; no lo reactiva dentro de ONRESTORE, que ocurre antes de completar la secuencia de despertar DSP. Vista/retención y puertos siguen separados.

Los hooks de HOME y sleep se tratan como pares de suspensión/reanudación serializados, según el SDK fijado. No se inventa una pila de suspensiones para servicios concurrentes inexistentes. Repeticiones son idempotentes. Un adaptador futuro con causas independientes simultáneas necesitará un contrato explícito, no debe reutilizar este par genérico sin revisarlo.

Las opciones se escriben/cerran/releen de forma síncrona fuera de callbacks y antes del siguiente bombeo APT. Una solicitud del sistema pendiente no cancela bytes a mitad de operación desde esta aplicación; se atiende cuando vuelve a APT. Esto no garantiza durabilidad SD ni cubre fallos de energía. Audio/SDK tienen sus propios hilos internos; el dominio solo se modifica desde el hilo del bucle. No se introduce concurrencia de aplicación.

### Controles reservados

El conjunto diagnóstico es A, START, SELECT, X, Y. Cualquier otro bit observado en held/down bloquea acciones hasta soltar todo. HOME y power permanecen gestionados por APT, sin remapeo ni deshabilitación desde el proyecto. Se protege el combo predeterminado de Rosalina L+abajo+SELECT; combos personalizados formados exclusivamente por botones diagnósticos requieren revisar el mapeo antes de usarlos. No se afirma conocer la configuración del usuario ni se cambia su sistema.

Fuentes primarias: [libctru 2.7.0 apt.c](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/source/services/apt.c) (`aptMainLoop`, `aptHandleSleep`, `aptJumpToHomeMenu`, `aptWaitForWakeUp`), [apt.h](https://github.com/devkitPro/libctru/blob/v2.7.0/libctru/include/3ds/services/apt.h) y [documentación oficial Rosalina](https://github.com/LumaTeam/Luma3DS/wiki/Rosalina). Verificación física según versión/launcher pendiente.

## Validación

Pruebas portables: matriz de estados, ciclos repetidos, log de cambios real, entrada que intentaría salir/pausar mientras suspendida y estado terminal. Composición real con SDK/Tone dobles: hooks por lotes dentro de una llamada APT (sleep/retorno), hooks separados como caso adverso, HOME desde running/paused, duplicados, salida entre hooks, botones mantenidos al volver y combos reservados con modificadores previos. La instrumentación cuenta render/entrada/archivo/audio y conserva orden de destrucción. Release, ASan/UBSan, GCC/cobertura y ARM son obligatorios. Hardware sigue un procedimiento manual independiente.
