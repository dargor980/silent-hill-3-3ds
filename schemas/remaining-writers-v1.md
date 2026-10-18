# Escrituras restantes — RW01–RW08

F02.07/origin/remaining-writers. Extiende WR, AC y MP; no define un formato
de recurso ni introduce un intérprete en el runtime Nintendo.

## Requisitos EARS

- **RW01:** CUANDO prepare el plan, el analizador DEBERÁ fijar por hash una
  ventana privada de código de hasta 4 KiB, alineada, con retorno JR RA/NOP
  final. DEBERÁ rechazar llamadas, instrucciones desconocidas, saltos fuera
  de la ventana y entradas de control en delay slots. DEBERÁ explorar ambos
  sucesores de condiciones no resueltas sin afirmar cuál se ejecutó.
- **RW02:** CUANDO catalogue escrituras, DEBERÁ aceptar solo SW directa o
  BEQ+SW en delay slot; DEBERÁ producir puntos privados de pausa anteriores
  al efecto y publicar únicamente cantidades y hashes. Otros stores o slots
  con efectos no soportados DEBERÁN impedir aceptar el plan.
- **RW03:** CUANDO reimporte la traza, DEBERÁ verificar hash de cada estado,
  A/B/C, PC/ciclo/RAM, PID/CRC y código fijado. DEBERÁ exigir entrada, uno o
  más pares pre/post y retorno, secuencias consecutivas, slots únicos e
  identidad/rango/mapa iguales entre todas las pausas. GPR4 inicial DEBERÁ
  fijar la base; GPR31 inicial DEBERÁ fijar el retorno.
- **RW04:** CUANDO valide un par, DEBERÁ reutilizar WR04/05 para calcular
  destino, valor y siguiente PC, verificar código y preservar GPR bajos de
  64 bits. DEBERÁ admitir sobrescrituras, solapes y stores sin cambio, sin
  confundir el ancho escrito con la cantidad de bytes distintos.
- **RW05:** CUANDO concilie, DEBERÁ exigir que cada preestado sea igual al
  resultado reconstruido de la entrada y pares anteriores, y que el retorno
  completo sea igual al resultado final. Un gap, par incompleto, retorno
  prematuro o efecto no soportado DEBERÁ rechazar la conciliación. Igualdad
  final por sí sola SHALL NOT atribuir bytes a una escritura.
- **RW06:** MIENTRAS adquiera, DEBERÁ acotar a 256 hits, 60 segundos de avance
  activo emulado (ciclos EE, 294.912.000 por segundo) y un supervisor de sesión
  para el tiempo de pared, incluidas pausas humanas. El adaptador actual DEBERÁ detenerse antes
  de agotar los 99 slots únicos: máximo 48 pares y 98 estados en una traza.
  El importador DEBERÁ consumir estados incrementalmente, sin retenerlos todos.
- **RW07:** CUANDO reporte, DEBERÁ separar conciliación de efectos observados,
  adquisición real y autenticación. DEBERÁ declarar que cambios transitorios
  revertidos entre pausas pueden escapar a la observación. La traducción de
  datos SHALL NOT atribuirse a páginas de código sin su propia evidencia.
- **RW08:** CUANDO publique, DEBERÁ cerrar lectores y conservar originales,
  estados, código y paquetes en custodia privada. DEBERÁ emitir solo hashes,
  cantidades y diferencias relativas, con dos reimportaciones deterministas;
  carga, semántica, F02.07/Q05/G02 DEBERÁN permanecer abiertos.

## Diseño y aceptación

`writer_sites` examina el flujo estático y produce puntos privados. Reusa el
decodificador conservador existente; no calcula decisiones de coma flotante.
`writer_trace` consume puntos AC de un iterable acotado, importa una pausa
cada vez, valida pares con `store_pair` y reconstruye exclusivamente sus
efectos. La raíz privada, el transporte, UI, reloj y publicación pertenecen
al adaptador operativo. Ninguno de estos módulos puros controla PCSX2.

Se permite restaurar una copia de entrada SRC53, verificada por hash, antes
de la primera adquisición en el perfil nuevo. Durante la serie no se permite
cargar estados. Esto es repetición desde un punto fijado, no un arranque nuevo
del juego ni evidencia adicional de cómo se cargó originalmente el recurso.

El código se contrasta con la ventana física fijada de cada estado. Esta
consistencia y la visualización del depurador no demuestran por sí mismas
la traducción de sus páginas. La ventana de datos sí exige observador MP.

- [x] Plan de puntos y contrato acotados, con ramas/slots adversos (RW01/02).
- [x] Conciliador incremental y pruebas sintéticas de gaps, sobrescrituras,
  ciclos, identidad, mapa, código y límites (RW03–07).
- [x] Captura nueva focalizada y dos reimportaciones (RW06/08).
- [x] Regresión, cobertura 80/80, Ruff, trazabilidad y próximo seguimiento.

Aceptación: [SRC54](../docs/execution/f02-07-remaining-writers.md). El primer
intento agotó 1.800 segundos de pared y permanece rechazado como incompleto.
El segundo usa 3.600 segundos de pared y conserva los límites activos y de
capturas. Se restauró la entrada antes de adquirir, nunca dentro de la serie.
