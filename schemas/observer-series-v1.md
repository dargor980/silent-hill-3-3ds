# Serie de cuatro paradas — OS01–OS06

Complemento de AC y MP08. El analizador es puro: interpreta entradas privadas
suministradas; la evidencia de ejecución/PINE proviene del coordinador y de
la sesión supervisada, no de este analizador.

- **OS01:** WHEN compare una serie THEN SHALL exigir exactamente entrada,
  pre-SW, post-SW y retorno, en ese orden, con secuencias consecutivas, slots
  distintos y una misma sesión/proceso/perfil/CRC/rango esperado.
- **OS02:** WHEN reimporte cada parada THEN SHALL comprobar el hash del estado,
  tres paquetes A/B/C idénticos semánticamente, su PID/CRC y RAM/PC/ciclo
  contra el estado; SHALL rechazar una captura parcial o mezclada.
- **OS03:** WHEN contraste continuidad THEN SHALL exigir iguales base EE,
  tabla vmap, entradas de página, tamaño y offset resuelto en las cuatro
  paradas. Un alias uniforme SHALL conservarse como distinto del esperado;
  una reasignación SHALL impedir aceptar continuidad.
- **OS04:** WHEN contraste orden THEN SHALL exigir ciclos u64 estrictamente
  crecientes, base virtual igual a GPR4 de entrada y PC de retorno igual a
  GPR31 de entrada; SHALL NOT usar GPR4 de retorno como nueva base.
- **OS05:** WHEN reporte THEN SHALL publicar hashes, etiquetas, tamaños y
  diferencias relativas, omitiendo registros, CRC, direcciones y bytes.
  El resultado SHALL ser determinista y no declarar autenticación o captura
  real a partir de entradas suministradas.
- **OS06:** WHEN documente la sesión real THEN SHALL asociar recibos AC,
  supervisor, controles UI y hashes privados. Un control de arranque SHALL
  mantenerse separado de las cuatro paradas MP08. El origen de carga y la
  semántica del recurso SHALL permanecer pendientes.

`observer_series` reusa AC/OB para reimportar y `origin_compare` para medir
diferencias; no abre archivos ni controla el emulador. El script de operación
posee la lectura anclada y publica después del cierre. Las pruebas usan
estados y paquetes propios, incluida continuidad con alias y ruptura del mapa.

Los PCs esperados pertenecen al plan privado de adquisición; el analizador
exige su coincidencia, pero no descubre por sí mismo qué instrucciones
representan. Tampoco conserva ni reejecuta el transporte PINE: su comparación
real está en los recibos del coordinador AC.

## Aceptación

- [x] OS01/02: identidad, orden, secuencias, slots, hashes y tres paquetes.
- [x] OS03/04: continuidad, alias, ciclos u64, base de entrada y retorno.
- [x] OS05: resultado determinista sin bytes ni direcciones.
- [x] OS06: sesión real, cierre y dos reimportaciones iguales en
  [SRC53](../docs/execution/f02-07-observer-live.md).

31 casos sintéticos cubren aceptación y rechazo. MP08 queda completado para
la invocación documentada; no implica continuidad durante todos los instantes
intermedios ni procedencia de carga demostrada.
