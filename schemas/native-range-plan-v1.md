# Plan de intervalos virtuales — v1

Parte de CI-T4; entrada estructural de [NL](native-image-layout-v1.md).
El plan reduce comprobaciones duplicadas y conserva qué segmentos dependen de
cada byte. Su resultado no demuestra el origen ni la integridad de las páginas.

## Requisitos EARS

- **NR01:** CUANDO se reciban segmentos, el planificador DEBERÁ conservar cada
  propietario y producir intervalos disjuntos cuya unión sea exactamente la de
  todos los segmentos no vacíos con protección distinta de cero.
- **NR02:** CUANDO varios segmentos compartan bytes, el plan DEBERÁ conservar
  todos sus propietarios, incluso en solapamientos parciales o anidados; el
  tamaño único SHALL NOT sumar aliases varias veces.
- **NR03:** CUANDO exista una cola zero-fill declarada, el plan DEBERÁ partir el
  intervalo en su frontera exacta y conservar la clasificación por propietario.
  Esa clasificación no DEBERÁ afirmar que los bytes actuales sean cero.
- **NR04:** SI hay propietarios duplicados, datos inválidos, desbordamiento o
  agotamiento de límites/memoria, el planificador DEBERÁ fallar con salida vacía,
  sin truncar ni devolver un prefijo del plan.
- **NR05:** CUANDO haya segmentos vacíos o reservados sin permisos, el plan
  DEBERÁ conservarlos en el inventario sin programar lecturas de sus direcciones.
- **NR06:** CUANDO existan permisos o clasificaciones incompatibles sobre un
  intervalo compartido, el plan DEBERÁ señalar el conflicto y retener todas las
  dependencias; no elegirá silenciosamente un propietario.
- **NR07:** CUANDO cambie el orden de entrada, el plan DEBERÁ conservar la misma
  representación canónica. Los propietarios AOT suministrados por otro proveedor
  DEBERÁN permanecer diferenciados de las imágenes Mach-O.
- **NR08:** CUANDO se contabilicen páginas de 4/16 KiB, el plan DEBERÁ contar cada
  página virtual tocada una vez, incluidos extremos parciales y huecos dentro
  de la misma página, sin ampliar los intervalos de bytes que se verificarán.
- **NR09:** CUANDO se contraste con el censo conservado, la prueba DEBERÁ
  reconstruir la cobertura y todas las dependencias con un oráculo independiente,
  separar bytes declarados/reservados/únicos y conservar la procedencia del log.
- **NR10:** SI una página transformada no se puede asociar a su origen, el
  consumidor DEBERÁ mantener el rechazo. Ser externa/limpia, pertenecer a una
  región conocida o coincidir en número con los archivos no acredita ese origen.

## Diseño y límites

`RangeClaim` identifica dominio (Mach-O/AOT), objeto del proveedor y parte;
dirección virtual, tamaño, prefijo inicializado declarado y permisos iniciales.
Los identificadores son locales al snapshot, no identidades criptográficas ni
direcciones autorizadas desde clientes. El llamador conserva el inventario NL
completo, sus flags/offsets y la correspondencia de propietarios. AOT se acepta
como dominio de entrada; enumerarlo realmente sigue siendo una tarea distinta.

Una función portable sin I/O ordena propietarios y barre eventos de inicio,
frontera zero-fill y fin. Emite átomos disjuntos y una lista plana de dependencias
que indexa las entradas canónicas. Reserva, vacío, conflicto y clasificación se
conservan explícitamente. No modifica CacheRangeGuard ni sus requisitos de origen.
No convierte offsets de Mach-O en offsets de subcaché.

Presupuestos: 65536 entradas (1024 × 64), 196608 átomos, 1048576 dependencias y
16 GiB de unión activa. Sumas declaradas usan uint64 con comprobación de overflow;
pueden exceder 16 GiB por aliases/reservas. Las asignaciones fallidas producen
`unavailable`. El coste es O(N log N + dependencias), con memoria acotada por esos
presupuestos. No se invocará en el límite CPU hasta medir/integrar su ciclo de vida.

Dos permisos iniciales distintos se marcan como conflicto conservador, incluso
si alguno fuera compatible con permisos efectivos: el plan no lee protecciones
actuales del kernel. Un prefijo inicializado y una cola zero-fill superpuestos
también son conflicto. El plan de diagnóstico puede contenerlos; no es admisión.

## Política de transformaciones pendiente de integración

Separar: archivo original verificado, página transformada por pager, página
privada COW y memoria originalmente zero-fill. Solo la primera categoría tiene
hoy vínculo implementado mediante CacheRangeGuard. Para las demás se necesita
evidencia de origen/transformación y continuidad; ni un hash de memoria mutable
ni el bit external/clean sustituyen ese vínculo. El censo de puntos no clasifica
inequívocamente COW. No se aceptan excepciones por nombres __DATA ni rutas.

## Tareas

- [x] **NR-T1 / NR01–08:** implementar barrido portable, capacidades, conflictos,
  clasificación y contabilidad; integrar casos al pipeline host existente.
- [x] **NR-T2 / NR04,09:** probar límites, aliases parciales, colas y omisiones con
  oráculo por byte, cuatro builds y controles de regresión compilados. Reproducir
  inicio/salida de SRC97 sin ejecutar de nuevo el candidato ni leer memoria viva.
- [x] **NR-T3 / NR09–10:** documentar evidencia del pager y agrupación de los 14
  objetos; publicar hashes/resultados y precisar qué asociación sigue pendiente.

Después: enumeración AOT completa, prueba de origen de páginas transformadas y
composición de cobertura con nacimiento/revisión/manifiestos/revalidación acotada.
