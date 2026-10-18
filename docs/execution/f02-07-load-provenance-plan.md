# F02.07 — Origen fijado y modelo de procedencia de carga

Unidad: `origin/load-provenance`, LP-A/B. Fecha: 2026-10-18.
Estado: **anclaje, plan parcial y modelo completados; adquisición de carga pendiente**.
Contrato [LP01–LP10](../../schemas/load-provenance-v1.md).
[Evidencia SRC55](../compatibility/load-provenance-evidence.json).

## Resultado comprobado

La ISO, el catálogo, el contenedor y el candidato conservan sus hashes.
Se volvió a interpretar el índice MFA: dos bloques y 86 entradas, con rango
de contenedor y posición en ISO conciliados. Los 1.536 bytes del candidato
coinciden con ambas extracciones privadas y con la entrada guardada de SRC53,
reutilizada por SRC54. Esta igualdad sitúa el origen posible; no prueba cómo
llegaron los bytes a RAM.

Una inspección acotada de 173 filas posibles del estado encuentra 86 registros
distintos que coinciden con nombres, offsets y tamaños del catálogo de ese
contenedor. Entre ellos está el candidato completo. Una solicitud en otra
estructura conserva el mismo nombre base y tamaño. El texto del contenedor
coincide al normalizar mayúsculas y separar sus marcadores literales; no se
atribuye semántica al marcador final ni a la extensión del recurso.

Se fijaron seis ventanas de código, 1.880 bytes en total, que coinciden entre
ELF y RAM guardada. Pila, descriptor y tabla apoyan un plan de búsqueda y
entrega al consumidor. La investigación adicional fija cuatro instrucciones
de llamada y ventanas candidatas de solicitud, envoltorio y cuerpo parcial
de obtención del recurso. Son referencias estáticas; no demuestran llamadas
ejecutadas, una lectura completada ni una transferencia al destino.

El ensayo que presenta al modelo únicamente una entrega con todos los bytes
correctos se rechaza con **LINEAGE_GAP**. Así se comprueba expresamente que una
instantánea posterior a la carga no basta para aceptar procedencia.

## Modelo y responsabilidades

[load_lineage](../../tools/inspectors/load_lineage.py) recibe un origen fijado
y eventos inmutables de lectura, copia, escritura invalidante y entrega.
Mantiene una relación por byte entre RAM física y offsets del candidato:

- La lectura introduce procedencia solo para la intersección comprobada con
  el candidato; los bytes de relleno quedan sin verificar.
- La copia exige igualdad observada y traslada únicamente procedencia conocida.
  En solapes utiliza el preestado, sin afirmar que el juego usa `memmove`.
- Cada sobrescritura elimina la atribución anterior; la entrega exige bytes,
  longitud y offsets correctos para todo el candidato.
- Mezclas de identidad, secuencia/ciclo inválidos, huecos, lecturas cortas,
  transformaciones desconocidas y excesos de presupuesto se rechazan.

La función pura no lee archivos, controla PCSX2, decodifica instrucciones ni
valida mapas. ISO/MFA, custodia y publicación reusan adaptadores separados.
LP-C deberá traducir evidencia AC/MP a eventos validados; ningún campo booleano
de un recibo sustituirá esa comprobación. Esta separación mantiene el modelo
independiente del emulador y del runtime Nintendo, sin dependencias nuevas.

Límites del modelo: 256 eventos consumidos incrementalmente, candidato/evento
de hasta 4 KiB, 16 KiB de posiciones con procedencia, RAM física de 32 MiB y
60 segundos de ciclos EE. La cadena suministrada puede ser coherente sin estar
autenticada: los recibos mantienen `mapping_verified=false`,
`disk_read_verified=false`, `live_acquisition_verified=false`, vínculos y
capacidades vacíos, y carga pendiente.

## Repetibilidad y custodia

Cada análisis se ejecutó dos veces y produjo informes idénticos:

| Informe | Tamaño | SHA-256 |
|---|---:|---|
| Anclaje y plan inicial | 2.125 bytes | `e4e0d975dcf774a0a304d9826b3cc755c5d4e5c9cadeef451c4e3333aab87afb` |
| Directorio y fronteras adicionales | 1.504 bytes | `70972ab2c35e7c0ec257a32ed9a35a90482327279e44417a25204c654c834c71` |

Son dos análisis de entradas fijadas, no dos ejecuciones del juego. Los lectores
ISO se cierran antes de publicar, se verifica nuevamente el estado de origen
y los planes privados no se sobrescriben. Scripts operativos, direcciones,
nombres internos, bytes de código/datos y estado completo permanecen privados.
Se publican hashes, tamaños, recuentos y resultados. No se abrió una sesión
nueva de PCSX2 ni se modificó su build en esta unidad.

## Pruebas y pipeline

[78 casos sintéticos nuevos](../../tests/python/test_load_lineage.py) cubren
lectura directa y fragmentada, copia por bloques, relleno, solapes, escrituras
ajenas, invalidación y recuperación, orden de offsets con bytes repetidos,
mezclas de identidad, tipos inválidos, huecos, límites exactos y excesos.

La regresión final aprueba **2.365 pruebas, sin fallos ni omisiones**; JUnit
registra 28,162 segundos. La primera ejecución conserva seis fallos de pruebas
existentes del supervisor porque el sandbox denegó `/bin/ps`. La repetición
con acceso a ese comando pasa completa, sin alterar los tests para aceptarla.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| load_lineage | 89/89 (100 %) | 22/22 (100 %) |
| Total herramientas | 4.484/4.529 (99,01 %) | 1.315/1.348 (97,55 %) |

El job Python existente descubre el módulo y sus pruebas sin ISO/BIOS. Pasan
el gate independiente 80/80, Ruff/formato para los 115 archivos de su alcance,
los controles de arquitectura/custodia/trazabilidad/enlaces y `git diff --check`.
No se ejecutó CI remota ni compilación C++/3DS: esta unidad no cambia esas
fuentes. Estas pruebas validan el modelo y sus rechazos, no una carga del juego.

## Siguiente unidad: LP-C

1. Inspeccionar el cuerpo candidato y sus llamadas con ventanas privadas
   acotadas, distinguiendo búsqueda en directorio/caché de lectura completada
   y copia. Fijar operandos, rangos, retorno, tamaño solicitado y recibido.
   Aceptación: frontera observable que sustente cada tipo de evento o rechazo
   explícito si la transformación no está soportada.
2. Implementar el adaptador de evidencia, separado del modelo. Reusar identidad,
   estados, PINE y AC/MP; verificar páginas de código y datos pertinentes antes
   de normalizar direcciones físicas. Cubrir con fixtures código alterado,
   alias, mapa, identidad, rango, retorno corto y capturas discontinuas.
3. Preparar LP-D desde un punto anterior a la lectura. La entrada SRC53 está
   demasiado avanzada. Fijar perfil español/Normal/Normal, slots nuevos,
   máximo de 48 adquisiciones, 256 hits, 60 segundos activos, 3.600 de pared,
   8 GiB de etapa y 10 GiB libres mínimos antes de iniciar. Prohibir restaurar
   dentro de la serie; conservar cualquier captura incompleta o rechazo.
4. Contrastar lectura → transferencia → entrega y producir dos reimportaciones
   iguales con cierre y custodia verificados. Solo entonces evaluar el cierre
   de procedencia para esa ejecución.

LP-C/D, procedencia real, semántica de cámara, doce categorías, dos salas,
F02.07/Q05/G02 y validación física en New Nintendo 2DS XL siguen pendientes.
