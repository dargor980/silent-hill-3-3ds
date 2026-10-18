# QB v1 — Qt Base para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qtbase`.
Hereda [DB](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **QB01 — Procedencia.** CUANDO prepare Qt Base, el procedimiento DEBERÁ
  verificar el archivo 6.11.1 contra el SHA-256 de la receta PCSX2 fijada,
  conservar originales, avisos y un inventario de archivos fuera del repositorio.
  SI un archivo contiene rutas inseguras o excede el presupuesto de preparación,
  DEBERÁ detenerse antes de extraerlo.
- **QB02 — Parches.** CUANDO prepare el árbol de trabajo, el procedimiento
  DEBERÁ registrar por separado los dos parches de compatibilidad y el parche
  inline de macdeployqt, sus resultados y el diff final. SI un parche no aplica,
  DEBERÁ conservar el fallo y resolverlo explícitamente antes de configurar;
  el nombre del parche no acreditará compatibilidad.
- **QB03 — Configuración y capacidad.** CUANDO configure Qt Base, el
  procedimiento DEBERÁ conservar MinSizeRel, dylibs x86_64, destino macOS 11.0
  y las opciones de la receta; DEBERÁ distinguir dependencias privadas,
  componentes del SDK y herramientas host. ANTES del build completo de Qt Base,
  DEBERÁ comprobar los 20 GiB de IB02 y limitar el paralelismo a dos jobs.
  SI la reserva falta, DEBERÁ permitir solo preparación y diagnósticos pequeños;
  la excepción de Shaderc no se aplicará a Qt.
- **QB04 — Core y herramientas.** CUANDO pruebe Core, los fixtures DEBERÁN
  comprobar entrega diferida de una señal, cancelación de una conexión,
  finalización del bucle de eventos con timeout y conversión UTF-8/JSON válida
  e inválida. CUANDO generen código con moc/rcc/uic, DEBERÁN comprobar su
  comportamiento mediante un consumidor compilado; ejecutar `--version` no
  sustituirá ese ensayo.
- **QB05 — Recursos e imágenes.** CUANDO carguen un recurso propio incorporado
  con rcc, los fixtures DEBERÁN verificar su contenido exacto y el rechazo de
  una ruta ausente. CUANDO codifiquen y decodifiquen una imagen PNG propia,
  DEBERÁN verificar dimensiones y píxeles, y rechazar datos corruptos.
  CUANDO utilicen JPEG, DEBERÁN comprobar disponibilidad, dimensiones y colores
  con tolerancia declarada para su compresión con pérdidas.
- **QB06 — Widgets.** CUANDO ejecuten el formulario generado por uic con la
  plataforma offscreen, los fixtures DEBERÁN comprobar texto Unicode, estado
  habilitado/deshabilitado y una interacción que actualice un contador.
  DEBERÁN distinguir estas pruebas de una ventana Cocoa visible, GPU y UI PCSX2.
- **QB07 — Consumo e instalación.** CUANDO valide Qt Base, el procedimiento
  DEBERÁ ejecutar un subconjunto explícito de tests originales y los casos
  propios antes de instalar; DEBERÁ repetirlos desde un consumidor nuevo del
  prefijo instalado. DEBERÁ rechazar prefijos ausentes, verificar versiones,
  arquitectura, carga efectiva, plugins, manifiesto y hashes previos del prefijo.
  SI una suite no se ejecuta, DEBERÁ declararla pendiente u omitida.
- **QB08 — Continuidad.** CUANDO cierre una etapa, el procedimiento DEBERÁ
  publicar únicamente metadatos reproducibles y actualizar el backlog.
  CUANDO instale Qt Base, DEBERÁ repetir CMake PCSX2 y el gate IB en una salida
  nueva, conservando pendientes Qt Tools/LinguistTools y demás dependencias.
  Preparación, sintaxis y configuración no acreditarán build, tests de ejecución,
  compatibilidad macOS 11 ni finalización de F02.07.

## Diseño y tareas

El coordinador local registra descarga, extracción, parches y comandos; el
contrato define los criterios; CMake resuelve targets Qt desde una ruta explícita.
Los fixtures separan Core, recursos, codecs e interacción de widgets, comparten
únicamente comprobaciones y usan datos propios. El formulario y el QObject son
entradas reales de uic/moc; no se sustituyen por archivos generados manualmente.
La configuración de dependencias no modifica el runtime 3DS ni el checkout PCSX2.

1. Verificar archivo, tamaño y rutas; guardar inventario/licencias y hashes
   anteriores del prefijo. Preparación limitada a 1 GiB de datos lógicos para
   archivo, original, copia y configuración; medir también asignación (QB01/QB03).
2. Aplicar cada parche de receta sin fuzz, conservar offsets, originales y diff;
   comprobar exactamente qué archivos cambian (QB02).
3. Configurar con búsquedas aisladas, sin tests/examples completos ni descargas
   implícitas; inspeccionar cache y resumen de features. Identificar herramientas
   ejecutables en este host y plugins offscreen/Cocoa (QB03).
4. Implementar casos propios con oráculos declarados y seleccionar tests del
   proveedor por sus fuentes; preparar consumidor y negativo de prefijo ausente.
   Si faltan los headers públicos de reenvío, generar únicamente los de los
   módulos probados con `syncqt`: herramienta de una unidad C++ sin enlace Qt,
   dentro del presupuesto de preparación; registrar arquitectura y ejecución.
   Comprobar sintaxis donde sea posible sin fabricar moc/uic ni usar otro Qt
   (QB04–QB07).
5. Con reserva suficiente, compilar con dos jobs. Ejecutar casos propios y
   subconjunto original desde el árbol de build; instalar solo si pasan, repetir
   desde el prefijo y comprobar ABI/carga/manifiesto (QB03–QB07).
6. Registrar evidencia y límites, repetir CMake/gate tras instalación y detallar
   siguiente unidad, sin dar por disponible LinguistTools (QB08).

Aceptación final: Qt Base y sus herramientas x86_64 ejecutables en el host,
casos seleccionados aprobados antes/después y resolución por PCSX2. La fase de
preparación tiene su propio estado y mantiene esta aceptación pendiente.
