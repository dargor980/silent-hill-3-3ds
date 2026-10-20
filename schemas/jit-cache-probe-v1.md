# JIT/cache probe v1 — JC01–JC07

Lote de cobertura conservadora de LG-I1. JIT EE no admitido para continuidad;
ningún modo de VM obtiene permiso de armado por este contrato.

## Requisitos EARS

- **JC01:** WHEN se entra por `recExecute` THEN el productor SHALL invalidar la
  observación antes del reset pendiente y antes de entrar al código compilado;
  SHALL conservar la ejecución original, exista o no conexión.
- **JC02:** WHEN ya existen bloques compilados antes de conectar el puente THEN
  el rechazo en la entrada SHALL seguir siendo dinámico; SHALL NOT depender de
  recompilar esos bloques. IF el JIT ya está ejecutándose THEN esta barrera SHALL
  NOT considerarse suficiente para autorizar armado; el armado real seguirá cerrado.
- **JC03:** WHEN se solicita un acceso de escritura a caché THEN SHALL invalidar
  por cobertura desconocida antes de buscar/expulsar una línea o marcarla sucia;
  SHALL cubrir tamaños escalares y 128 bits, entradas directas y vía VTLB.
- **JC04:** WHEN una línea sucia/válida con PFN válido se devuelve a memoria THEN
  SHALL notificar sus 64 bytes y destino host antes de la asignación; IF no hay
  escritura efectiva THEN SHALL NOT inventar un aviso de RAM. La devolución
  SHALL conservar datos y flags, aunque la observación haya fallado.
- **JC05:** WHEN se ejecuta reset de caché o la instrucción CACHE THEN SHALL
  invalidar antes de mutar datos/tags o descartar líneas. Un acceso de lectura
  normal SHALL conservar su comportamiento y observar las devoluciones que cause.
- **JC06:** WHEN VTLB delega una escritura a caché THEN SHALL producir un solo
  aviso lógico de cobertura desconocida desde la hoja común; SHALL conservar
  los avisos físicos adicionales que correspondan a una devolución real.
- **JC07:** WHEN se valida el lote THEN SHALL separar cuerpos reales con dobles,
  compilación de unidades y VM; SHALL comparar efectos ON/OFF, conservar fuentes
  anteriores y rechazos, y declarar pendientes JIT generado, admisión de modos,
  concurrencia, época, extremos y rendimiento en el emulador.

## Diseño y decisión

Se reutiliza el puente existente, sin cambiar núcleo ni transporte. Una barrera
host al comienzo de `recExecute` invalida cualquier intervalo conectado. Los
generadores de stores constantes/dinámicos/fastmem permanecen intactos; no se
declara cobertura por instrucción ni equivalencia intérprete/JIT.

La escritura lógica se rechaza desde `prepareCacheAccess<true>`. Se retiran solo
los dos avisos VTLB previos a esa delegación, evitando duplicación; los handlers
conservan su rechazo. `CacheLine::writeBackIfNeeded` observa el puntero real y
64 bytes. `resetCache` y `CACHE` invalidan conservadoramente incluso si la
operación concreta no modifica RAM. No se alteran sus ramas, datos ni retornos.

Un cambio futuro de modo debe quiescer CPU/trabajos, revisar caché existente y
establecer época antes de armar. La barrera de entrada no impide que una conexión
creada dentro de un bloque ya activo omita esa entrada. Por ello no se expone
armado PINE/VM y LG-I2–I4 permanecen pendientes. Admitir JIT requerirá una tarea
separada de emisión/ABI/fastmem, recompilación y ejecución de bloques reales.

## Tareas acotadas

1. **JC-T1 / JC01–07:** inventario fijado de JIT, caché, delegaciones, remapeos y
   bloques existentes; decisión de rechazar JIT y escrituras lógicas de caché.
2. **JC-T2 / JC01–06:** nueva copia privada, parche reversible, barrera JIT,
   hooks de caché y eliminación de avisos VTLB duplicados; sin armado.
3. **JC-T3 / JC02–07:** harness con cuerpo completo de caché, funciones VTLB y
   entrada JIT, dobles explícitos y RAM propia. Verificar tamaños, hit/miss,
   aliases, expulsión, writeback, flags, valores iguales, restauración, reset,
   instrucciones CACHE y entrada con callback preexistente. ON/OFF/sanitizadores.
4. **JC-T4 / JC07:** compilar unidades reales ON/OFF, comparar efectos, auditar
   dos veces y repetir gates. El callback preexistente del harness no representa
   un bloque PS2 recompilado; esa validación y el rendimiento quedan pendientes.
