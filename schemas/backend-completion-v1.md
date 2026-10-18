# Backend completion v1 — BC01–BC08

Estado: consistencia de finalización suministrada, F02.07/LP-C.

Como investigador quiero distinguir una solicitud aceptada de un sector terminado
y contrastar su buffer antes de seguir la copia al recurso.

## Requisitos EARS

- **BC01:** WHEN se recibe el perfil THEN el adaptador SHALL reutilizar BS para
  validar origen y solicitud, exigir un hash canónico del sector válido y una
  llamada de consulta de estado distinta, alineada y contenida en el llamador.
- **BC02:** WHEN se reciben evidencias THEN el adaptador SHALL validar tres pausas
  de ocho rangos LF, identidad común, slots distintos, secuencias consecutivas,
  ciclos crecientes dentro de 60 segundos y mapas estables entre pausas.
- **BC03:** WHEN se valida la aceptación THEN el adaptador SHALL exigir retorno
  de un sector, backend ocupado sin progreso, posición inicial correcta, buffer
  y longitud de solicitud coherentes; SHALL rechazar retorno corto o negativo,
  cancelación y evidencia ya avanzada fuera del subconjunto admitido.
- **BC04:** WHEN se valida la finalización THEN el adaptador SHALL exigir retorno
  y estados de éxito, un sector completado, avance exacto de una unidad, stream
  con 2048 bytes completados y descriptor de disco coherente; SHALL rechazar
  error, cancelación, operación pendiente y contadores de otra solicitud.
- **BC05:** WHEN se contrasta el buffer THEN el adaptador SHALL exigir la misma
  ubicación física sin solapamiento con controles, 2048 bytes capturados y hashes
  coincidentes para todos los bytes válidos del sector y para el recurso;
  SHALL excluir del hash de archivo el padding del último sector parcial.
- **BC06:** WHEN se emite el recibo THEN el adaptador SHALL publicar solo
  metadatos y declarar si el buffer válido ya coincidía al aceptar la solicitud;
  SHALL mantener cero `Read`, vínculos y capacidades y no acreditar ejecución,
  continuidad, origen físico del llenado, copia, semántica del perfil o captura real.
- **BC07:** WHEN se fija el perfil privado THEN la investigación SHALL contrastar
  ventanas y estados con ELF, revalidar origen/sector/recurso en ISO, repetir el
  análisis con resultado idéntico y conservar fuentes sin publicar bytes originales.
- **BC08:** WHEN se verifica el cambio THEN las pruebas SHALL usar fixtures
  propios, cubrir errores y límites, y aprobar regresión, cobertura y gates del
  pipeline existente sin depender de archivos originales.

## Diseño

`backend_completion.reconcile_backend_completion(source, request, profile,
sector_sha256, stages)` es un adaptador puro. `CompletionProfile` contiene el
`BackendProfile` de BS y el sitio/objetivo de la consulta de estado. La adquisición,
custodia y lectura de ISO continúan en sus adaptadores existentes. El nuevo módulo
compone contratos sin modificar los módulos históricos ni introducir dependencias.

1. Antes de solicitar: ocho rangos BS, incluida la tabla de dispositivo.
2. Retorno de solicitud: `driver,backend,stream,file,disc,code,args,buffer`.
3. Retorno de consulta exitosa: los mismos ocho rangos que la segunda pausa.

Son 24 solicitudes regionales y tres estados, sin contar descubrimiento. El primer
rango de buffer sustituye a la tabla de dispositivo; los controles comunes mantienen
direcciones, tamaños y respaldo. La tabla no se observa entre puntos: no se acredita
su continuidad. Las pausas siguen en la misma pila y preceden al cambio de caché y
a la copia; el driver y argumentos guardados deben permanecer idénticos.

Subconjunto: archivo normal, fallo de caché de un sector, retorno de solicitud aún
sin progreso del stream ni I/O pendiente, sin cancelación, y consulta posterior en
éxito. Si el worker avanzó antes de la segunda pausa, se rechaza por estar fuera de
este perfil; no se clasifica ese rechazo como un fallo del juego. El perfil conjunto
deberá contemplar esa carrera con puntos de observación internos o un contrato nuevo.

La posición/progreso de backend y disco se mide en sectores; el contador de datos
del stream se mide en bytes. Un error también puede avanzar la posición backend:
ningún contador o estado aislado prueba éxito. Se conserva la identidad del archivo
por BS y los campos estables de disco; el tamaño mutable del stream describe solo
la solicitud. La liberación del wrapper backend no demuestra destrucción de todos
sus alias. No se dereferencia el alias del stream después de la liberación.

El hash del sector es una entrada suministrada independiente del hash del recurso.
Se valida `min(2048, file_size - sector_start)` y el recurso se extrae por su offset
dentro del sector. Un buffer preexistente coincidente es admisible como consistencia
y se declara; nunca se convierte en prueba de una escritura o lectura nueva.

## Tareas y aceptación

1. **BC-T1 / BC01–04:** trazar preparación, progreso, consulta y limpieza; fijar
   unidades, estados, alcance y ABI. Aceptación: el error con avance y la
   finalización corta se rechazan aunque el hash del recurso coincida.
2. **BC-T2 / BC02–06:** implementar composición BS/LF, estabilidad y buffer.
   Aceptación: buffer ajeno o de otro sector se rechaza, último sector parcial
   se admite sin atribuir padding al archivo, recibo mínimo con cero `Read`.
3. **BC-T3 / BC07:** crear plan privado 0700/0600 sin sobrescribir, verificar
   ventanas y hashes ISO dos veces y cerrar lectores antes de publicar informes.
   Aceptación: informes idénticos y fuentes intactas, estado posterior no usado
   como inicio de una captura nueva.
4. **BC-T4 / BC08:** negativos de estado, conteos, mapas, pila y secuencias;
   regresión completa, cobertura 80/80, lint y trazabilidad. Aceptación: pruebas
   propias reproducibles en CI y limitaciones/siguiente tarea registradas.
