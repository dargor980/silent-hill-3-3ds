# Ensayo de ciclo de vida — F01.07

**Estado físico: no ejecutado.** New Nintendo 2DS XL + Homebrew Launcher confirmados por el usuario. Registrar firmware, versión de launcher/Luma y mapeos conocidos antes del ensayo; desconocidos como null. No se asume que HOME esté disponible en todo launcher. [Contrato EARS](lifecycle-contract.md) e [informe/build](../execution/f01-07-lifecycle.md).

## Preparación y registro

Usar build `7c369f7e8c79` de `build/f01-07/artifacts/` con su ELF, manifiesto y fixture propios, sin mezclar builds anteriores. Verificar mediante `python -m tools.debug.bundle verify --directory build/f01-07/artifacts --build-id 7c369f7e8c79`. Copiar `.3dsx`/`probe.txt` a `/3ds/sh3_diagnostic/`. Registrar ID y SHA-256 del bundle, modelo, launcher/versiones, audio/Result, estado inicial de opciones y cualquier combo personalizado de Rosalina. La escucha se marca pendiente si NDSP no llega a READY; no se deduce de los contadores.

Tras suspensión o combinación bloqueada, soltar todos los botones. La pantalla puede mostrar `Release all buttons to enable controls`; se acepta una nueva pulsación después de una lectura completa sin botones. START continúa como salida normal, excepto mientras espera esa liberación o forma parte de una combinación con botones ajenos al diagnóstico.

## Matriz manual sintética

| Caso | Acción | Resultado esperado / evidencia que registrar |
|---|---|---|
| H01 pausa | A, mantener y soltar; A de nuevo | Una transición por flanco; patrón ámbar/verde, paused/running, opciones conservadas |
| H02 tapa/running | Cerrar/abrir tapa con tono activado | Regresa running; espera liberación; ventana de tiempos reiniciada, sin salto por tiempo cerrado |
| H03 tapa/paused | A para pausar, cerrar/abrir tapa | Regresa paused y tono pausado; requiere otra A nueva para running |
| H04 tapa/mute | X para desactivar tono y comprobar Save OK, cerrar/abrir | Mute conservado; no se activa audio por el despertar |
| H05 HOME/running | Pulsar HOME y volver si el entorno lo permite | Estado running y opciones conservadas; si no permite HOME, registrar no disponible con entorno exacto |
| H06 HOME/paused | Repetir HOME desde paused | Sigue paused al volver; sin volver automáticamente a running |
| H07 tecla al volver | Mantener A o SELECT al abrir tapa, soltar, pulsar de nuevo | Primera tecla mantenida no pausa/cambia página; después de soltar y pulsar de nuevo sí actúa |
| H08 salida al volver | Mantener START al abrir tapa; soltar y pulsar START | No sale por tecla residual; sale por nueva pulsación y retorna al launcher |
| H09 combinación reservada | Si existe Rosalina con combo predeterminado: L+abajo+SELECT; volver y soltar todo | No cambia página/pausa/opciones del diagnóstico; la disponibilidad del menú se registra por separado |
| H10 opciones y HOME | X/Y, luego HOME o tapa; volver y comprobar Save/Load/tono | Operación síncrona previa conservada, sin guardado adicional desde hooks; no demuestra durabilidad frente a pérdida de energía |
| H11 ciclos | Repetir tapa/HOME diez veces desde running y paused | Estado anterior conservado; sin nueva reserva propia por hook ni crecimiento del ring; medir pools aparte |
| H12 salida normal | START desde running y paused | Una salida, sin congelamiento; registrar destino real del retorno |

No cambiar configuración del sistema para hacer pasar un caso. Un combo personalizado solo con A/START/SELECT/X/Y requiere revisar el perfil antes de probarlo. No extraer SD ni cortar energía como inyección de fallo; las fallas de archivos se cubren con fixtures/dobles. Este ensayo no es todavía T11 completo con juego, combate, streaming, secuencias o partidas.

## Hoja por caso

Registrar: fecha, caso, build/3dsx SHA/ELF SHA, hardware o emulador, firmware/launcher, estado/audio/opciones antes y después, pasos exactos, esperado, observado, capturas disponibles, resultado (`pass`, `fail`, `not_tested`, `unavailable`) y explicación. `unavailable` no cierra por sí solo el requisito de compatibilidad; requiere revisar el perfil objetivo. No sustituir valores desconocidos por cero.

F01.08 reúne la ejecución prolongada, error simbolizado y gates. Mientras no exista evidencia física, F01.07/G01 siguen abiertos aunque todos los tests host pasen.
