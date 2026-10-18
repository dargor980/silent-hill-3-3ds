# RY v1 — RapidYAML para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-rapidyaml`.
Hereda [DB01–DB08](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **RY01 — Procedencia.** CUANDO prepare RapidYAML 0.12.1, el procedimiento
  DEBERÁ verificar el archivo de la receta fijada de PCSX2, conservar sus
  componentes incorporados y avisos, y comparar las fuentes con el archivo.
- **RY02 — Build.** CUANDO compile, el procedimiento DEBERÁ producir una
  biblioteca compartida Release x86_64 con c4core incorporado, aislar las
  búsquedas de dependencias y conservar argumentos, logs e intentos. DEBERÁ
  mantener las opciones de callbacks de la receta sin modificar al proveedor.
- **RY03 — Lectura.** CUANDO ejecute los fixtures propios, estos DEBERÁN comprobar
  mapas, secuencias, escalares vacíos, texto UTF-8 y conversiones numéricas con
  expectativas explícitas. DEBERÁN distinguir propiedad del texto en arena
  y lectura in-place sin acceder a memoria cuya vida haya terminado.
- **RY04 — Escritura.** CUANDO emita un árbol modificado, el fixture DEBERÁ
  verificar su semántica al volver a leerlo. SI el búfer de salida es pequeño,
  DEBERÁ verificar el tamaño requerido y puntero nulo documentados, además
  de guardas intactas; con capacidad suficiente DEBERÁ verificar el resultado.
- **RY05 — Errores.** CUANDO reciba YAML mal formado, el fixture DEBERÁ capturar
  el callback de error de parseo con ubicación, sin aceptar otro tipo de error,
  y comprobar una lectura válida posterior. AL terminar el ámbito de prueba,
  DEBERÁ restaurar los callbacks anteriores, incluso ante una excepción.
- **RY06 — Aceptación.** CUANDO instale, el procedimiento DEBERÁ repetir los
  fixtures usando el paquete CMake de versión exacta y el target exportado,
  rechazar un paquete explícito ausente, e inspeccionar arquitectura, enlaces
  y manifiesto. DEBERÁ ejecutar los dos quickstarts originales del proveedor
  y distinguirlos de la suite completa que requiere descargas adicionales.
- **RY07 — Continuidad.** CUANDO pasen las comprobaciones, el procedimiento
  DEBERÁ repetir CMake de PCSX2 en un directorio nuevo y reevaluar IB. F02.07,
  mapa efectivo y build completo DEBERÁN permanecer pendientes mientras no
  satisfagan sus propios criterios.

## Diseño y tareas

CMake resuelve targets y versiones; el fixture prueba únicamente el contrato
de API con YAML propio. Un guard RAII limita el cambio de callbacks a un proceso
de prueba. Cada caso tiene una responsabilidad y expectativas independientes
de la implementación del proveedor. El coordinador local registra pasos y
evidencias; no se añade una capa YAML al runtime 3DS ni se modifica el gate IB.

1. Verificar release, c4core incorporado, API y licencias (RY01).
2. Definir cinco casos propios y dos programas originales en CTest; aislar
   el directorio de trabajo de los quickstarts que escriben archivos (RY03–RY06).
3. Compilar biblioteca sin habilitar descargas de la suite completa; ejecutar
   casos contra el target exportado del build antes de instalar (RY02/RY06).
4. Instalar y repetir casos desde un proyecto consumidor nuevo; verificar
   rechazo de paquete ausente, carga efectiva y bibliotecas previas (RY06).
5. Comparar fuentes, registrar hashes/manifiesto, repetir CMake/gate y publicar
   resultados y siguiente dependencia observada (RY01/RY07).

Aceptación: siete casos antes y después de instalar, biblioteca x86_64 y
CMake de PCSX2 que supera `find_package(ryml)`. Esto no demuestra conformidad
completa YAML, seguridad frente a entradas arbitrarias, rendimiento ni el port.
