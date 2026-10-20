# Esperas externas y cancelación CPU v1 — EW01–EW09

IW-UIWAIT continúa el hallazgo de SRC84. No acredita productores desconocidos.

- **EW01:** WHEN un hilo externo inicia una llamada bloqueante a CPU THEN SHALL
  anunciarla antes de encolarla y conservar el anuncio hasta que la llamada termine.
  Una llamada asíncrona o ejecutada inline en CPU SHALL NOT crear ese anuncio.
- **EW02:** WHILE existe al menos una espera anunciada THEN CPU SHALL rechazar
  nuevos intentos de observación. WHEN consulta el intento activo THEN SHALL
  cancelarlo y liberar GS→VU→PINE antes del siguiente despacho de aplicación.
- **EW03:** WHEN esperas se superponen o anidan THEN SHALL conservar la señal
  hasta retirar la última. SHALL NOT confundir una notificación aislada con el
  período completo durante el cual otro hilo sigue bloqueado.
- **EW04:** IF el contador no puede registrar una espera por capacidad o
  contención acotada THEN SHALL impedir admisión durante el resto de su vida.
  SHALL NOT envolver el contador, resetearlo por VM ni bloquear al llamador.
- **EW05:** WHEN termina el scope, incluso por unwind THEN SHALL retirar solo
  su propia reserva. La señal SHALL publicar efectos anteriores mediante atomics
  acquire/release y SHALL NOT liberar tokens VU/GS desde UI.
- **EW06:** WHEN se integra THEN SHALL cubrir RunOnCPUThread bloqueante y la
  conexión directa de closeInputSources conservando argumentos, destino y retorno.
  SHALL NOT convertir la operación a asíncrona ni descartar callbacks.
- **EW07:** WHEN se prueba el ciclo UI→CPU/GS→UI THEN SHALL cancelar por la señal
  antes del deadline, entregar una vez y conservar payload. SHALL probar varios
  scopes, nuevos intentos durante espera y fallo por aviso ausente o prematuro.
- **EW08:** WHEN se valida THEN SHALL usar QtCore instrumentado con TSan,
  sanitizadores del núcleo, objetos ON/OFF y custodia de fuentes anteriores.
  El enlace completo SHALL respetar IB02 y quedar pendiente si falta capacidad.
- **EW09:** WHILE falten escritores, llamadores con locks o VM completa THEN
  SHALL mantener admisión vacía. La señal no garantiza que el propio callback CPU
  sea no bloqueante ni resuelve ciclos preexistentes ajenos a la retención.

## Diseño

ExternalWaits es un contador atómico con reservas RAII sin asignación dinámica,
callbacks ni dependencia de Qt. Cuenta scopes, no solicitudes de captura. Cada
adquisición usa hasta 32 CAS; capacidad/contención no resoluble activa un rechazo
persistente. Un scope no registrado no decrementa el contador.

VMManager posee una instancia compartida, separada de sus controladores thread_local.
Solo CPU consulta la señal para cancelar/retirar el intento. El scope externo
rodea la llamada Qt bloqueante; permanece vivo durante la ejecución del callback.
BeforeObserverProducer también cancela si ve una espera durante la fase PINE.

La espera CPU de 1 ms sigue siendo el intervalo nominal de reconsulta, sujeto a
planificación. La corrección requiere estado cancelled anterior al deadline;
no establece una garantía temporal dura ni sustituye la revisión de locks.

- **EW-T1 / IW-UIWAIT1:** núcleo y tests de scope, anidación, capacidad,
  concurrencia, publicación y unwind.
- **EW-T2 / IW-UIWAIT2:** puentes Qt/VM, cancelación del ciclo y regresión de
  retorno/payload, con negativos y QtCore instrumentado.
- **EW-T3 / IW-UIWAIT3:** copia privada nueva, objetos, custodia y enlace bajo
  reserva; conservar los estados de admisión no acreditados.
