# Observación de una escritura durante A

F02.07/camera-resource-link-eu/origin/runtime-writer · WR01–WR08.

## Requisitos EARS

- **WR01:** CUANDO se restaure entrada A, la observación DEBERÁ usar sesión y perfil
  privados nuevos, fijar estado/plan/SRC27 por hash y comprobar PC/GPR de entrada.
  Los estados históricos y la configuración habitual DEBERÁN conservarse intactos.
- **WR02:** CUANDO se capture una parada, DEBERÁ comprobar pausa antes/después de
  guardar, esperar estabilidad, importar estado/CRC/versión y conservar archivo único.
  Una respuesta PINE de guardado DEBERÁ tratarse como solicitud asíncrona.
- **WR03:** CUANDO se investigue un hit, DEBERÁ conservar estado previo, instrucción
  leída virtualmente y rango completo, avanzar un paso y conservar el estado posterior.
  Cada par DEBERÁ declarar sesión, entorno y operación; no mezclar restauraciones.
- **WR04:** SI el paso no es SW directa o BEQ seguida de SW en su delay slot,
  el par DEBERÁ quedar no soportado. Ambos extremos DEBERÁN estar fuera de delay
  slot. El validador DEBERÁ calcular dirección efectiva con desplazamiento signado
  y suma de 32 bits, exigir store alineada y completa dentro del candidato, y los
  cuatro bytes esperados desde GPR fuente previo. Para SW directa DEBERÁ exigir
  PC+4. Para BEQ+SW DEBERÁ comparar los 64 bits bajos de sus operandos y exigir
  destino de salto o PC+8 según condición; rechazar destino dentro del propio par,
  overflow de PC y cambios en los 64 bits bajos de cualquier GPR.
- **WR05:** CUANDO valide el par, DEBERÁ exigir igualdad de código antes/después y de
  bytes fuera del store. Para declarar modificación DEBERÁ haber una diferencia real
  dentro del store; una escritura del mismo valor DEBERÁ quedar `consistent_no_change`.
  Escrituras fuera del rango, memoria incompleta, orden/sesión/entorno incorrectos
  DEBERÁN rechazarse.
- **WR06:** MIENTRAS no se demuestre el mapa efectivo, DEBERÁ declarar traducción
  pendiente incluso si la lectura virtual coincide con el rango físico hipotético.
  El recibo DEBERÁ separar coherencia del par, identidad física y origen de carga.
- **WR07:** CUANDO publique, DEBERÁ emitir solo metadatos, hashes y offsets relativos;
  omitir bytes, instrucciones, GPR, direcciones y nombres originales. Fallos de hash,
  archivo o cierre DEBERÁN impedir publicación; `resource_links`/`capabilities` vacíos.
- **WR08:** CUANDO ejecute, DEBERÁ detenerse al retorno de A, 256 hits o 60 segundos
  de ejecución. Para un estudio inicial de un par se permite cierre parcial explícito;
  no afirmar cobertura de todas las escrituras ni cargador demostrado. Al terminar
  DEBERÁ cerrar el emulador y desactivar el IPC temporal.

## Diseño y tareas

1. Preparar perfil independiente, copia de restauración, IPC Unix bajo directorio
   0700 y un watchpoint de escritura sobre el rango completo de 1536 bytes. Pausar
   en entrada y contrastar con el estado fijado antes de reanudar.
2. Capturar un par antes/después de una escritura soportada, con lecturas virtuales
   y archivos de estado externos. No modificar registros, instrucciones ni memoria.
3. Implementar validador puro del store y coordinador de evidencia fijada, reutilizando
   el lector de estados y custodia existentes. Fixtures propios: desplazamiento
   negativo, alias/límites, delay slot, store no soportado, fuera del rango, corrupción
   fuera/dentro, secuencia/sesión/entorno mezclados y fallos tardíos.
4. Producir recibos repetibles, ejecutar regresión/cobertura/Ruff/contratos existentes
   y documentar qué mapa, escritores o carga siguen sin observar. El perfil habitual
   no se modifica; configuración, copias y capturas nuevas quedan en raíz privada.

## Contrato de la importación parcial

`camera_writer` importa plan/SRC27 por hash sin repetir la extracción ni el análisis
histórico. Contrasta el estado de restauración con el hash fijado y PC/GPR de la
primera parada; verifica además que el rango completo de entrada tiene el hash del
recurso de SRC27. Conserva esta dependencia histórica explícita en el recibo.

El documento privado `capture.json` declara una sesión nueva, CRC, entorno, estado
fuente, frames consecutivos (1–513), hasta 256 pares disjuntos y cierre parcial.
Cada frame fija estado `.p2s`, rango virtual completo y pausa antes/después. Cada par
fija sus dos secuencias consecutivas, operación `step_into`, posición virtual de
código y hashes de lecturas antes/después (4 u 8 bytes). El lector importa los
estados desde `sstates`, conserva la base de GPR4 de entrada y contrasta lecturas
virtuales con el rango físico hipotético. No infiere traducción de esta igualdad.

`WriterState` añade lectura acotada de los 64 bits bajos sin modificar el contrato
histórico de `EEState`. `store_pair` valida efecto y flujo sin I/O; `camera_writer`
coordina custodia y publicación. Toda salida usa listas cerradas de campos; los
estados originales, instrucciones, direcciones y registros no se publican.

El cierre exigido en esta versión es parcial, sin captura de retorno. Declaraciones
de pausa, sesión, operación y cierre no son autenticación independiente de ejecución.
Dos recibos iguales prueban repetibilidad del análisis de la misma captura; no dos
ejecuciones del juego. Los pares sin segunda lectura del código quedan auxiliares.
