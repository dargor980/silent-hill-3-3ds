# Enumeración del mapa virtual — v1

Parte de CI-T4, complementa [NR](native-range-plan-v1.md). Permite encontrar
mappings fuera del inventario Mach-O, incluidos candidatos AOT, sin confundir
el objeto de una región con el objeto que respalda cada una de sus páginas.

## Requisitos EARS

- **NV01:** CUANDO se enumere el mapa, el lector DEBERÁ comenzar en dirección
  cero, recorrer todas las hojas devueltas por el kernel y exigir fin explícito.
- **NV02:** SI una consulta falla, devuelve un submapa sin resolver, una región
  vacía, retrocede, desborda o supera capacidad/profundidad, el lector DEBERÁ
  fallar con salida vacía, sin aceptar un prefijo del mapa.
- **NV03:** CUANDO se adquiera un mapa, el lector DEBERÁ comparar dos recorridos
  completos de sus campos estructurales y rechazar cambios, inserciones y bajas.
  Dos pasadas iguales SHALL NOT afirmar atomicidad ni ausencia de cambios ABA.
- **NV04:** CUANDO se compare una región, el lector DEBERÁ conservar dirección,
  tamaño, offset, objeto, profundidad, protecciones, herencia, tag, flags,
  profundidad shadow, externalidad y modo de compartición; SHALL NOT usar cuentas
  volátiles de páginas/referencias como identidad estructural.
- **NV05:** CUANDO se consulte macOS, el adaptador DEBERÁ usar el task propio,
  exigir el formato completo v2, comprobar PID antes/después y rechazar el uso
  heredado tras fork. Solo KERN_INVALID_ADDRESS significará fin de recorrido.
- **NV06:** CUANDO se recorra el mapa, el núcleo DEBERÁ tener toda la memoria de
  salida reservada y preparada antes de la primera consulta, sin asignaciones
  posteriores hasta terminar ambas pasadas. SI la reserva falla, DEBERÁ devolver
  unavailable sin consultar el origen.
- **NV07:** CUANDO se investigue AOT, la sonda DEBERÁ registrar regiones omitidas
  por el loader, distinguir hints del loader/tags y puntos asociados a archivos
  retenidos, y mantener explícita la falta de verificación de páginas interiores.
- **NV08:** CUANDO se compruebe estabilidad, el consumidor DEBERÁ distinguir
  cambios entre fases de cambios dentro de una adquisición. El mapa no DEBERÁ
  asumir que sus regiones son inmutables después de retornar.
- **NV09:** CUANDO se pruebe el candidato, DEBERÁ usar la copia diagnóstica
  conservada, perfil privado nuevo y testconfig; registrar estabilidad y coste
  sin habilitar VM, admisión ni captura.
- **NV10:** CUANDO se entregue, DEBERÁ conservar etapas y resultados, ejecutar
  pruebas portables/nativas, sanitizadores y regresiones de omisión/cambio; el
  pipeline host DEBERÁ incluir estos casos.

## Diseño

`RegionSource::query(cursor, region)` es el puerto de lectura: found/end/error.
`read_region_map` es una operación sin estado. Reserva 65536 entradas y las
inicializa antes de consultar. Primera pasada: orden ascendente, hojas no vacías,
sumas comprobadas y fin explícito. Segunda: compara cada registro y la cantidad
final sin asignar memoria. Después reduce la salida al tamaño observado.
Como máximo 2 × (65536 + 1) consultas, profundidad máxima 64. Un mapa vacío con
dos fines explícitos es válido estructuralmente; la admisión requiere su contexto.

Se permiten permisos actuales/máximos de cuatro bits (incluido UEXEC de x86_64),
con actuales contenidos en máximos. Tags, flags y modos se conservan como
metadatos, no se interpretan como origen fiable. No se exige objeto no nulo en
reservas ni regiones anónimas. No se lee el contenido de las regiones.

`MacOSRegionSource` llama mach_vm_region_recurse con profundidad máxima 64 en cada
consulta; el kernel desciende hasta una hoja o el límite. El adaptador no expone
task ports ni acepta un PID ajeno. Las cuentas de residencia, suciedad y referencias
se excluyen de la comparación porque cambian sin cambiar el mapping. El ID de
región no sustituye `mach_vm_page_info` ni el vínculo con un descriptor verificado.
Si el SDK no expone flags de región, el adaptador registra `flags_available=false`;
un cero sin disponibilidad no constituye evidencia de ausencia de JIT/TPRO.
Este campo expresa disponibilidad en el SDK, no una validación independiente de
la semántica de cada versión del kernel; tampoco permite acreditar ausencia de JIT.

La reserva previa evita reasignaciones del vector durante el recorrido, pero
otros hilos pueden modificar el mapa. Cualquier diferencia produce changed; no
hay reintentos ilimitados ni una afirmación de snapshot atómico. La composición
con nacimiento/revisión y exclusión de escritores sigue pendiente de CI-T4.

## Tareas

- [x] **NV-T1 / NV01–06:** implementar núcleo y adaptador; probar orden, fin,
  capacidad, overflow, cambios por campo, fallos de API/PID y falta de asignaciones
  durante consultas; integrar al pipeline host.
- [x] **NV-T2 / NV07–09:** censar el candidato en testconfig, comprobar dos pasadas,
  listar regiones fuera de imágenes y candidatos AOT, asociar puntos a referencias
  conservadas y registrar exactamente qué parte de la cobertura permanece abierta.
- [x] **NV-T3 / NV10:** cuatro builds, negativos compilados, custodia y publicación;
  actualizar tareas sin promover estabilidad estructural a identidad completa.
