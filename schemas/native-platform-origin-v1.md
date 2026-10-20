# Origen nativo de imágenes del perfil PT — PO v1

Detalle de PT-T3. Historia: como investigador necesito vincular cada cabecera
cargada con el catálogo de caché de dyld o con un archivo, bajo la confianza de
plataforma explícita de PT, conservando errores y límites de la observación.

## Requisitos EARS

- **PO01:** CUANDO se prepare el adaptador, DEBERÁ resolver todas las funciones
  necesarias y fijar el PID propio. SI falta una función o el PID no es válido,
  DEBERÁ fallar antes de adquirir recursos de introspección.
- **PO02:** CUANDO se adquiera un proceso o snapshot, DEBERÁ liberar cada recurso
  adquirido exactamente una vez, en orden inverso, incluso ante error. Ningún
  puntero de imagen, segmento o nombre DEBERÁ sobrevivir al callback/snapshot.
- **PO03:** CUANDO recorra la caché, DEBERÁ copiar un único inicio `__TEXT` por
  imagen, legible, no vacío y contenido en la caché. DEBERÁ rechazar UUID vacío,
  rango inválido, imágenes nulas, duplicados, catálogo vacío y exceso de capacidad
  (32768 imágenes, 256 segmentos por imagen), sin aceptar un prefijo truncado.
- **PO04:** CUANDO clasifique una dirección, DEBERÁ exigir su presencia exacta
  en el conjunto cargado y en el catálogo para declararla `platform_cache`.
  Ruta, install name, flags, proximidad o intervalo aislado SHALL NOT sustituir
  esa intersección. Una imagen externa DEBERÁ satisfacer el puerto de mapping
  regular de cabecera; no se admite una excepción para bibliotecas del sistema.
- **PO05:** CUANDO prepare el catálogo y lea un origen, DEBERÁ comprobar PID,
  revisión y conjunto cargado antes/después. Cambios, fallos o una dirección
  desconocida DEBERÁN invalidar la instancia de forma terminal y vaciar salida.
- **PO06:** CUANDO valide, DEBERÁ cubrir fallos parciales de API, limpieza de
  recursos, límites, cambios/PID/fork, desconocidos y biblioteca con nombre/flags
  imitados. DEBERÁ ejecutar el adaptador dentro del candidato con testconfig y
  documentar imágenes externas/dyld sin afirmar identidad completa ni captura.
- **PO07:** ANTES de crear proceso/snapshot de introspección, DEBERÁ rechazar
  una cabecera con flag de caché fuera del rango que informa dyld. DEBERÁ leer
  cabeceras mediante copia acotada del kernel y comparar eventos antes/después;
  el rango solo permite rechazar una contradicción, nunca acreditar membresía.

## Diseño

`MacOSPlatformOrigins` implementa `ImageOriginSource`. Recibe puertos estrechos
`ImageSnapshotSource`, `MappingSource` y una tabla `MacOSCacheCalls` inyectable.
Producción resuelve la SPI de dyld con dlsym; tests sustituyen esas llamadas.
El núcleo PT, manifiestos y adaptadores de eventos/mapping existentes no cambian.

Construcción: validar tabla/PID; adquirir proceso; crear/liberar un snapshot de
preparación de dependencias; leer ledger; adquirir snapshot definitivo; recorrer
catálogo; liberar snapshot/proceso; comprobar ledger/PID. Preparación única,
sin reintentos hasta obtener estabilidad. La instancia conserva solo valores
copiados, catálogo ordenado y conjunto/revisión canónicos. Cada lectura compara
el ledger fijado, clasifica una dirección exacta, consulta mapping si es externa
y vuelve a comprobar ledger/PID. Una carga posterior requiere nueva instancia;
no se repara una sesión invalidada.

Preflight antes de proceso y de cada snapshot: comprobar la contradicción de
PO07. La prueba de flags reveló un aborto `missingPlist` en la SPI instalada al
introducir la cabecera falsa antes del snapshot. Se conserva ese fallo. Preflight
rechaza ese caso; no promete proteger frente a cualquier corrupción concurrente
del proceso ni sustituye la confianza explícita en el código de plataforma.

El catálogo se considera inmutable durante el proceso bajo la confianza en dyld;
no se reenumera para cada cabecera. Se validan los datos disponibles, sin prometer
detectar una SPI que mienta o termine silenciosamente antes de tiempo: omisiones
solo pueden resultar externas y todavía requieren mapping/manifiesto de aplicación.
La API no expone estado final del enumerador de imágenes. Las llamadas de la SPI
son síncronas y sus callbacks no se retienen. El tiempo se limita externamente
en el supervisor; no se puede cancelar una llamada del sistema desde el adaptador.

Las pasadas no son atómicas ni excluyen ABA. dyld fuera del ledger y las páginas
AOT siguen bajo la confianza de plataforma; no se insertan imágenes ficticias
en el inventario PT. Bibliotecas externas notificadas por el loader se tratan
como aplicación y necesitarán archivos esperados en PT-T4.

## Tareas

- [x] **PO-T1 / PO01–05,07:** adaptador, resolución dinámica, recursos locales,
  catálogo acotado y fallo terminal; integrar target host en CMake/pipeline.
- [x] **PO-T2 / PO01–06:** pruebas nativas y API inyectada, cuatro modalidades,
  cobertura y controles negativos; conservar todos los resultados ejecutados.
- [x] **PO-T3 / PO06:** sonda testconfig en candidato privado con hashes previos
  y posteriores, perfil nuevo, clasificación completa y registro de cambios.
  Publicar límites y dar paso al manifiesto/coste PT-T4 solo con evidencia válida.
  SRC102 clasifica las 557 cabeceras de arranque y rechaza la salida por
  `libobjc-trampolines.dylib`: cabecera con offset 16384. Sigue parcial.
- [x] **PO-T3b / PT03,PO04:** especificar una extensión explícita para slices
  Mach-O universales antes de modificar la restricción de offset cero. Leer
  FAT32/FAT64 con endianidad, tamaños y límites comprobados; rechazar
  solapamientos, overflow, arquitecturas/subtipos ambiguos y offset no asociado
  a una cabecera thin válida. Vincular archivo completo, slice esperado y mapping
  observado, sin aceptar un offset por ruta. Probar fixtures y el archivo real;
  repetir testconfig completo y solo entonces avanzar a PT-T4.

Actualización SRC103: [MS v1 / PT v2](macho-slice-binding-v1.md) completa la
vinculación universal y las dos pasadas de arranque/salida del candidato.
PT-T3 y PO-T3/3b completas; el perfil v1 conserva offset cero y sus vectores.
Sigue PT-T4: manifiesto esperado y costes. [Evidencia de ejecución](../docs/execution/f02-07-macho-slices.md).
