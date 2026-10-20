# Integridad de archivos y rangos de caché nativa — v1

Estado: contrato de implementación CI-T1–3, dentro de IP-NATIVE2c2-integridad.
Precedentes: [NP](native-page-binding-v1.md), [NM](native-artifact-manifest-v1.md)
y [NC](native-inventory-v1.md). No habilita captura ni admisión.

## Requisitos EARS

Como proveedor de diagnóstico necesito relacionar los archivos completos de la
caché con cada página exigida por una política explícita, sin elevar los límites
del manifiesto de aplicación.

- **CI01:** CUANDO se verifique un bundle, el sistema DEBERÁ conservar los límites
  NM de 256 MiB por archivo, 512 MiB totales y 256 entradas.
- **CI02:** CUANDO el proveedor seleccione el dominio de caché del sistema, el
  sistema DEBERÁ admitir como máximo 32 archivos, 2 GiB por archivo y 16 GiB en
  total, rechazando dominios desconocidos y cualquier exceso antes de leer bytes.
- **CI03:** CUANDO se calcule un digest, el sistema DEBERÁ leer el archivo completo
  en bloques de hasta 64 KiB desde el descriptor que respalda la referencia de
  páginas, comprobar EOF e identidad antes/después y rechazar cambios o errores.
- **CI04:** CUANDO se contraste un manifiesto esperado e inmutable del proveedor,
  el sistema DEBERÁ verificar tamaños y SHA-256 en dos pasadas y conservar el
  primer fallo terminal, borrando los resultados y sin volver a efectuar IO.
- **CI05:** SI solo existe una línea base adquirida del host durante la sonda,
  el sistema DEBERÁ declararla observación local, sin presentarla como evidencia
  independiente del fabricante ni como política aprobada para el candidato.
- **CI06:** CUANDO se solicite cubrir una lista de rangos, el sistema DEBERÁ
  rechazar listas vacías, desordenadas o solapadas, direcciones/tamaños cero,
  desbordamientos, offsets fuera del archivo y alineaciones incompatibles.
- **CI07:** CUANDO se verifique un rango válido, el sistema DEBERÁ comprobar cada
  página intersectada, incluidos comienzo y final parciales, contra el objeto y
  offset esperados en dos pasadas completas; una página ausente, COW, modificada
  o respaldada por otro objeto DEBERÁ invalidar el resultado entero.
- **CI08:** CUANDO cambie la referencia, identidad del archivo o vínculo previo,
  el sistema DEBERÁ fallar de forma terminal; restaurar la ruta o bytes no DEBERÁ
  rehabilitar la instancia.
- **CI09:** CUANDO se informe cobertura, el sistema DEBERÁ limitarla a los rangos
  explícitos recibidos. La omisión de una imagen o segmento requerido DEBERÁ
  impedir la admisión del inventario completo en la futura integración.
- **CI10:** CUANDO se publique evidencia, el sistema DEBERÁ separar pruebas
  sintéticas, archivos reales verificados, rangos realmente recorridos y gates
  pendientes, conservando scripts, snapshots y resultados fallidos.

## Diseño y decisiones

`ArtifactDomain` selecciona dos políticas cerradas del proveedor. El valor por
omisión sigue siendo `bundle`. `AnchoredDigest` y `ManifestGuard` reutilizan los
mismos algoritmos de NM; cambian únicamente sus límites al seleccionar
`system_cache`. Un request remoto no selecciona dominio ni manifiesto.
Los nuevos límites son presupuestos del proyecto, no límites oficiales de macOS.

`MacOSPageAnchor` implementa tres puertos estrechos: identidad, lectura de bytes y
referencia de página. Retiene un descriptor privado con RAII y usa ese mismo
objeto para mmap/pread. Reabrir el nombre sirve solo para comprobar continuidad.
El hash sigue siendo responsabilidad de `AnchoredDigest`; CommonCrypto implementa
el puerto criptográfico. La costura de pread es interna y permite probar errores.

`CacheRangeGuard` posee una copia inmutable de los rangos de **un archivo** y el
`FileDigest` ya verificado. Valida como máximo 4096 rangos, 16 GiB de cobertura
acumulada y páginas de 4096 o 16384 bytes. Dos pasadas completas leen referencia,
todas las páginas y referencia final; se exige offset exacto en cada consulta.
No almacena bytes ni un vector de páginas. El contador indica consultas por
pasada; dos rangos disjuntos dentro de una misma página cuentan dos consultas. Las listas deben venir ordenadas por
dirección; aliases virtuales no solapados son permitidos. La referencia debe ser
residente, externa, limpia y offset cero, con identidad igual al digest fijado.

El guard comprueba asociación con un digest obtenido anteriormente; no recalcula
SHA durante cada consulta. La futura composición deberá rodear los recorridos
con verificación de archivos, nacimiento y revisión del loader. Dos lecturas
constituyen una observación acotada, no una instantánea atómica del sistema.

**Política de cobertura antes de integrar:** se deberán enumerar todas las
imágenes y segmentos relevantes del candidato, sin listas truncadas. Los rangos
inmutables deberán acreditar cada página. Los rangos modificados por relocación,
datos mutables o COW siguen rechazados hasta definir y probar su política
específica; no se aceptan por UUID/ruta ni se excluyen silenciosamente. Este
módulo recibe rangos, no certifica por sí mismo que el enumerador sea completo.

## Tareas y validación

- [x] **CI-T1 / CI01–04:** implementar dominios acotados y lectura desde el mismo
  descriptor; probar límites exactos, bundle intacto, lectura >256 MiB, EOF,
  error/cambio durante hash, reemplazo, fork y SHA conocido.
- [x] **CI-T2 / CI06–09:** implementar recorrido exhaustivo de rangos; probar
  límites parciales, página intermedia ausente/COW, offsets, cambio entre
  pasadas, continuidad y salida vacía terminal con fuentes instrumentadas.
- [x] **CI-T3 / CI05,10:** ejecutar Debug/Release/ASan+UBSan/cobertura, negativos
  compilados y sonda de hashes de archivos reales sin copiarlos. Publicar
  custodia, presupuesto y limitaciones; mantener abierta la integración total.
- [ ] **CI-T4 / CI05,09:** fijar el manifiesto esperado del lanzador para el candidato,
  enumeración completa de sus imágenes y política de rangos transformados;
  medir el coste de adquisición/revalidación antes de introducirlo en el
  coordinador; integrar con NC solo tras verificar todas las imágenes requeridas.
