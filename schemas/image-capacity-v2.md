# LC — Capacidad presupuestada del registro, 2.048 imágenes

Historia: como investigador, necesito cubrir los 1.069 módulos observados en
[SRC119](../docs/execution/f02-07-native-census.md) sin agotar la pila del trabajador
ni producir respuestas incompatibles. Desarrolla RT-T3b.2; RT-T3b.3 conserva
el reenlace y las muestras reales como una validación posterior.

## Requisitos EARS

- **LC01:** WHEN el registro reciba hasta 2.048 direcciones válidas y distintas
  THEN SHALL conservarlas completas. IF recibe otra, un duplicado, una baja
  desconocida o revisión inválida THEN SHALL fallar de forma terminal, sin
  truncar, reiniciar ni omitir eventos. La sonda IC conserva su borde histórico.
- **LC02:** WHEN se construya un guardia de inventario válido THEN SHALL poseer
  un único espacio de trabajo fijo separado de la pila del muestreo. IF falla
  su reserva THEN SHALL devolver `storage` sin consultar puertos ni reintentar.
  WHEN se destruya el guardia THEN SHALL liberar ese espacio en su hilo dueño.
- **LC03:** WHILE muestree THEN SHALL reutilizar ese espacio sin nuevas reservas,
  conservar doble pasada, línea base, comprobaciones de cobertura y fallo terminal.
  Guardias distintos SHALL NOT compartir almacenamiento mutable.
- **LC04:** WHEN se valide en ABI de 64 bits THEN SHALL limitar el espacio propio
  estricto a 256 KiB y el de plataforma a 512 KiB, con guardias de hasta 512 bytes.
  SHALL probar borde/exceso y muestreo en un hilo con pila de 512 KiB, distinguir
  tamaños de objetos, marcos compilados y consumo dinámico observado.
- **LC05:** WHEN productor y consumidor usen 2.048 imágenes THEN SHALL emplear
  [PD v2](platform-diagnostic-v2.md), rechazar v1 y comprobar total sin overflow.
  SHALL conservar identidad, correlación, evidencia, rechazo sin payload y
  condición diagnóstica sin admisión. El cliente SHALL NOT elegir capacidad.
- **LC06:** WHILE el trabajador prepare/muestree/envíe THEN SHALL conservar el
  plazo total existente de 5 s inicial/2 s de revalidación, cancelación y cierre.
  SHALL probar el límite con dobles acotados y controles de plazo; un benchmark
  sintético SHALL NOT acreditar el plazo de PCSX2, del SO o de todas las partidas.
- **LC07:** WHEN cambie el tamaño de `ImageSnapshot` THEN SHALL reconstruir todos
  sus consumidores con las mismas cabeceras. SHALL conservar candidatos previos
  y no reutilizar objetos con el ABI anterior en el candidato siguiente.
- **LC08:** WHEN se publique THEN SHALL distinguir tests, prueba nativa aislada
  y candidato con VM; SHALL mantener RT-T3b.3 y captura abiertos hasta su evidencia.

## Diseño y SOLID

`ImageLedger` conserva el algoritmo y sus causas de rechazo. Cada guardia posee
un `Scratch` privado mediante `unique_ptr`; su constructor reserva con `nothrow`,
su destructor se define donde el tipo es completo. El guardia sigue componiendo
puertos de nacimiento/manifiesto/origen/hash; la reserva no añade dependencia
del SO ni cambia la responsabilidad de esos puertos. No hay reserva en `sample`.

Los dos snapshots, el array de mappings/orígenes y los índices pasan a `Scratch`.
Los resultados y las copias del manifiesto mantienen su forma. El dueño nativo
ya crea `Inventory` en heap dentro de DW y lo destruye antes de confirmar cierre.
El catálogo de 32.768 entradas no cambia. 2.048 deja 979 entradas respecto del
pico observado; sigue siendo una política acotada, no una capacidad universal.

PD v2 mantiene tamaños/offsets pero cambia ambos magics y el límite; los vectores
v1 permanecen como evidencia histórica y controles de incompatibilidad. Python
centraliza los magics para que el canal no mantenga una copia literal distinta.

## Tareas y aceptación

- [x] **LC-T1:** reserva propia, fallo terminal de reserva, borde/exceso y
  aislamiento; medir tamaños, marcos y pila acotada. LC01–04.
- [x] **LC-T2:** transición C++/Python/canal y vectores comunes v2, negativos
  v1 y combinaciones de conteos. LC05.
- [x] **LC-T3 / RT-T3b.2:** regresiones, sanitizadores y mediciones del límite;
  verificar plazos/cancelación existentes, publicar inputs y matriz de objetos
  afectados para el reenlace posterior. LC06–08.

Esta etapa usa builds de pruebas separados. No extiende IC-L ni inicia un
reenlace PCSX2. El presupuesto de ese reenlace se fijará con su lista de objetos.

Validación y límites: [SRC120](../docs/execution/f02-07-image-capacity.md).
