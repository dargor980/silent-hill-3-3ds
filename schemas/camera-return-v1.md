# Repetición del escritor y retorno de A

F02.07/camera-resource-link-eu/origin/runtime-writer/repeat-return · RR01–RR07.

## Requisitos EARS

- **RR01:** CUANDO repita SRC28, la observación DEBERÁ fijar plan, SRC27, SRC28 y
  ambas capturas por hash; usar sesión distinta de SRC28 y de la captura histórica;
  validar de nuevo estado de entrada, CRC, PC/GPR y rango completo.
- **RR02:** CUANDO prepare el perfil, DEBERÁ configurar watchpoint `[84,88)` y
  breakpoint de retorno antes de abrir el emulador. La cobertura DEBERÁ declararse
  limitada a ese subrango; no inferir ausencia de otras escrituras.
- **RR03:** CUANDO observe la escritura, DEBERÁ conservar par consecutivo con
  código antes/después y satisfacer WR03–WR07. Para comparar con SRC28 DEBERÁ
  reproducir su recibo desde la captura privada y contrastar clase, flujo, hash de
  código, offset/ancho y comparación completa; excluir números de secuencia de la
  comparación entre sesiones. Una diferencia DEBERÁ registrarse, no ocultarse.
- **RR04:** CUANDO declare retorno, DEBERÁ ser la última parada y posterior a todos
  los pares, estar fuera de delay slot y tener PC igual a GPR31 de entrada y al PC
  del estado histórico de retorno fijado por SRC27. El rango DEBERÁ conservar la
  base de entrada, incluso si GPR4 cambia al retornar.
- **RR05:** CUANDO contraste el retorno, DEBERÁ releer el estado histórico fijado,
  verificar su hash de rango contra SRC27 y comparar todos los bytes con la captura
  nueva. Diferencias DEBERÁN quedar explícitas; no invalidar el recibo solo porque
  difieren dos ejecuciones. Mapeo y cargador DEBERÁN seguir pendientes.
- **RR06:** CUANDO termine, DEBERÁ cerrar PCSX2, desactivar IPC y comprobar hashes
  del perfil habitual. Fallos de captura, identidad o cierre DEBERÁN impedir un
  recibo de retorno observado. Los estados y recibos históricos no se sobrescriben.
- **RR07:** CUANDO publique, DEBERÁ limitar la salida a hashes, conteos, offsets y
  estados explícitos. Dos análisis idénticos DEBERÁN distinguirse de dos sesiones de
  emulación. Tests/CI DEBERÁN usar únicamente fixtures propios.

## Diseño y tareas

1. Preparar sesión/perfil privados, copia de entrada y copia histórica de retorno.
   Capturar entrada, antes/después de SW y retorno, con guardado estable y pausa.
   Preservar cualquier hit adicional; máximo 256 hits o 60 s de ejecución.
2. Extender el lector compartido con una política explícita para captura de retorno,
   preservando exactamente la salida del modo parcial. No transformar un documento
   de retorno en una captura parcial ficticia. Revalidar estados antes de publicar.
3. Añadir coordinador de repetición: reproducir SRC28, validar captura nueva,
   comparar pares y retorno. Lectores privados poseen I/O; comparación pura produce
   metadatos. No cambiar semántica de `store_pair` ni `EEState`.
4. Fixtures: misma sesión, retorno temprano/equivocado/en delay slot, base de retorno
   cambiada, referencia alterada, discrepancia de pares/retorno, código cambiante,
   captura parcial y fallos tardíos. Regresión, cobertura y custodia antes de entrega.

## Documento privado adicional

El modo `sh3-return-writer-capture` conserva los campos WR y añade
`return_sequence` y `return_reference` (`name`, `sha256`). La secuencia debe ser la
última; la referencia vive en la raíz privada y su hash procede de la comparación
de SRC27 en `stop_at_historical_event_sequence`. El cierre exige `return_observed`
y `return_captured: true`. Se permite un frame extra de retorno, hasta 514 frames.

El recibo conserva `execution_authentication: not_provided` y cierre declarado:
sesión, pausa y acciones proceden de la captura aportada; el validador no autentica
por sí solo un proceso externo. Coincidencia virtual/física de contenido sigue sin
demostrar el mapa efectivo. La repetición del par no prueba los otros escritores.
