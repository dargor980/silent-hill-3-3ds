# Descriptor de archivo y adquisición multirrango — DA01–DA09

Unidad de LP-C posterior a [LF01–LF08](load-frontier-v1.md). Separa consistencia
de un descriptor, adquisición de rangos y atribución del archivo. Un descriptor
coherente no sustituye la observación de apertura/resolución del catálogo.

Estado: interpretación y coordinación implementadas con fixtures propios;
[SRC57](../docs/execution/f02-07-descriptor-acquisition.md) registra la
investigación estática y los límites. Vínculo de archivo y captura real pendientes.

## Requisitos EARS

- **DA01:** CUANDO examine asignación, codificación, comprobación y liberación
  de descriptores, DEBERÁ fijar ventanas ELF/estado y registrar explícitamente
  cómo cambia la generación. Las estructuras residuales SHALL NOT acreditar
  una apertura activa ni la identidad del archivo.
- **DA02:** CUANDO interprete un descriptor, DEBERÁ usar rangos con mapas LF
  comprobados para configuración de tabla y fila. DEBERÁ exigir longitudes
  exactas, capacidad entre 2 y 256, índice dentro de capacidad, dirección de
  fila derivada de tabla/token, generación positiva, token sin desbordamiento
  y descriptor subyacente no negativo. Reservado/cerrado DEBERÁN rechazarse.
- **DA03:** CUANDO concilie el rango, DEBERÁ comprobar offset y tamaño exactos
  contra el candidato fijado, sin aceptar sentinelas, tamaños nulos ni rangos
  fuera de los enteros positivos soportados. La igualdad de rango SHALL NOT
  identificar por sí sola el contenedor o nombre del archivo.
- **DA04:** CUANDO compare dos observaciones del descriptor, DEBERÁ exigir
  identidad, mapas, tabla y fila conservados, slots distintos, secuencia
  consecutiva y ciclos crecientes dentro del presupuesto LP. Un descriptor
  reciclado DEBERÁ rechazarse aunque use el mismo índice de tabla.
- **DA05:** CUANDO adquiera varios rangos, el coordinador DEBERÁ validar antes
  del I/O uno a ocho planes con etiquetas únicas, proceso/sesión/entorno,
  PC y slot comunes, y secuencias consecutivas ≤256. DEBERÁ guardar el estado
  una sola vez y usar ese mismo estado para todos los rangos.
- **DA06:** CUANDO adquiera, DEBERÁ observar cada rango antes y después del
  guardado y al final, contrastar PINE/estado/mapas y revalidar identidad y
  custodia. Solo el estado «guardado pendiente» podrá reintentarse, hasta
  256 sondeos y 30 segundos de presupuesto cooperativo, sin repetir el guardado.
- **DA07:** SI falla cualquier rango, el estado, las guardias, el plazo o el
  cierre, el coordinador DEBERÁ rechazar el resultado sin publicar aceptación.
  DEBERÁ conservar artefactos ya escritos y publicar solo tras cerrar lectores
  y socket; una publicación fallida SHALL NOT reintentarse automáticamente.
- **DA08:** CUANDO informe, DEBERÁ publicar solo metadatos y declarar pendientes
  apertura/archivo, ruta seleccionada, caché/disco y autenticación de ejecución.
  Ninguno de estos adaptadores DEBERÁ producir eventos `Read` por sí solo.
- **DA09:** CUANDO cierre la unidad, DEBERÁ verificar fixtures de asignación,
  generación, reciclado, rangos, adquisición parcial y cierre; gate 80/80,
  regresión completa sin publicaciones concurrentes y dos análisis estáticos
  iguales. Código y estados del juego DEBERÁN permanecer privados.

## Diseño y tareas

`archive_descriptor` interpreta únicamente tabla/fila suministradas y compara
dos pausas LF. La capacidad determina la menor potencia de dos que la cubre
para separar índice y generación; una vuelta completa del token queda fuera
del contrato. La identidad real del archivo requiere la apertura y resolución
del catálogo observadas y no se infiere del rango.

`observer_multirange` coordina los puertos existentes de canal, guardia,
custodia y publicación, reutilizando AC/MP/LF. Mantiene un estado y tres
paquetes por rango. El supervisor de proceso conserva el límite externo de
sesión; el presupuesto cooperativo se comprueba entre operaciones y antes de
publicar, sin prometer interrumpir una llamada de puerto bloqueada.

1. Fijar asignador/generación/cierre y resolución de nombre/rango.
2. Implementar y probar consistencia del descriptor y adquisición multirrango.
3. Vincular apertura y resolución de catálogo a un descriptor activo y a su
   posición; observar despacho/caché y después preparar la captura LP-D.
