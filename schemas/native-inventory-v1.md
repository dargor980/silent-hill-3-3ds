# Composición del inventario nativo — NC01–NC10

Como investigador quiero que nacimiento, archivos y mappings pertenezcan a una
misma observación estable antes de usarlos en el diagnóstico IP. Esta unidad
compone las pruebas NB/NI/NM disponibles; no acredita todavía la caché de macOS.

## Requisitos EARS

- **NC01:** WHEN se inicia una observación THEN SHALL comprobar nacimiento y
  nonce mediante ProcessBirth, el manifiesto completo mediante ManifestGuard y
  el inventario mediante un puerto de eventos del cargador del proveedor.
- **NC02:** WHEN un inventario contiene cero imágenes, más que el límite activo
  del loader (2.048 según [LC](image-capacity-v2.md)), direcciones
  nulas/duplicadas o revisión cero/agotada THEN SHALL descartarlo sin truncarlo.
- **NC03:** WHEN se comprueba cada imagen THEN SHALL exigir una región de
  cabecera válida, offset cero y correspondencia inequívoca con un objeto del
  manifiesto verificado. Una imagen desconocida o inaccesible SHALL invalidar
  el conjunto entero; una ruta, UUID o pertenencia al sistema SHALL NOT omitirla.
- **NC04:** WHEN se adquiere el inventario THEN SHALL leer dos veces todos sus
  mappings y verificar nuevamente el manifiesto, el cargador y el nacimiento.
  Cualquier diferencia SHALL descartar la observación, sin reintentos locales.
- **NC05:** WHEN cambia la revisión del cargador THEN SHALL descartar el resultado
  aunque el conjunto de direcciones vuelva al original. El orden de enumeración
  sin cambios de revisión SHALL NOT alterar la identidad canónica del conjunto.
- **NC06:** WHEN se resumen los objetos y las imágenes THEN SHALL usar SHA-256,
  dominios distintos y campos explícitos en little endian, sin padding nativo,
  rutas absolutas ni punteros serializados como texto.
- **NC07:** WHEN una observación difiere de la primera en proceso, objetos,
  mappings o revisión THEN SHALL conservar la primera causa terminal y devolver
  únicamente salida vacía. Nuevas llamadas SHALL NOT consultar los puertos.
- **NC08:** WHEN falta configuración o falla el hash THEN SHALL rechazar la
  observación. La identidad del manifiesto esperado SHALL proceder del lanzador
  confiable y no de un mensaje del cliente.
- **NC09:** WHILE no exista evidencia del vínculo de caché/subcachés/AOT con
  archivos THEN SHALL mantener la integración completa pendiente. Resultados
  parciales y fixtures SHALL NOT anunciarse como inventario real acreditado.
- **NC10:** WHEN se valida la composición THEN SHALL cubrir cargas/descargas con
  retorno al estado previo, sustituciones, cambios durante el muestreo, fallos
  terminales y rechazo del inventario real no cubierto, distinguiendo dobles.

## Diseño

`InventoryGuard` depende de ProcessBirth, ManifestGuard, MappingSource,
ImageSnapshotSource y DigestEngine. Cada componente conserva su responsabilidad:
nacimiento/entropía, lectura anclada, mapping, eventos y algoritmo respectivamente.
El núcleo no llama al sistema operativo ni conoce rutas o mensajes de transporte.
Es de propietario único y no copiable. Sus puertos tienen que sobrevivirlo.

Secuencia: nacimiento inicial → cargador inicial → manifiesto → dos pasadas de
mappings → manifiesto final → hashes → cargador final → nacimiento final.
ManifestGuard hace dos pasadas internas por llamada. El cierre del cargador cubre
también el cálculo de hashes. No equivale a suspender todos los escritores;
IP-NATIVE3 debe retener el alcance del coordinador y volver a comprobarlo.

Los mappings cubren la región de cabecera definida por NI, no todos los segmentos
ni la igualdad entre bytes de memoria y disco. Un archivo del manifiesto puede
no estar cargado; toda imagen cargada sí debe quedar cubierta. Dos nombres del
manifiesto que correspondan al mismo dispositivo/inodo se rechazan como ambiguos.
El adaptador macOS de eventos existente se usa sin introspección privada.

Formato de objetos: ASCII `SH3:file-objects:v1` sin terminador; SHA-256 de evidencia
del manifiesto (32 bytes); cantidad u64; por entrada en el orden del manifiesto:
índice u64, device/inode/size/modified_seconds/changed_seconds/modified_ns/changed_ns
como siete u64, SHA-256 del archivo (32 bytes). Tiempos válidos no negativos según NI.

Formato de imágenes: ASCII `SH3:loaded-images:v1` sin terminador; digest de objetos
(32 bytes); revisión u64; cantidad u64; por cabecera en orden numérico ascendente:
dirección, tamaño, offset e índice del objeto, todos u64. Todos los u64 son little
endian. El resultado también conserva ProcessKey, revisión y cantidad; aún no es
la Observation completa con épocas y generaciones de IP.

No se añade un puerto que permita declarar arbitrariamente «caché confiable».
La futura cobertura de caché necesita un contrato y pruebas propios antes de
ampliar esta clasificación. No se aumentan los límites de NM para archivos de
caché de varios GiB ni se introduce una allowlist de UUID.

## Tareas

- **NC-T1 / NC01–09:** implementar composición, validación y codificación canónica
  en `tools/observer/inventory.cpp` y su interfaz. Mantener el cierre terminal.
- **NC-T2 / NC02–10:** pruebas portables de fronteras/fallos y pruebas macOS con
  fixtures cargadas de archivos anclados, cambio real del cargador y rechazo del
  inventario completo. Validar la codificación con un vector independiente.
- **NC-T3 / NC09–10:** ejecutar Debug, Release, ASan/UBSan y cobertura; conservar
  sondas fallidas/inconclusas y controles negativos. Publicar evidencia reproducible.
- **Pendiente IP-NATIVE2c2:** resolver procedencia de caché, subcachés y AOT antes
  de dar por completa la identidad nativa o integrar el proveedor de PCSX2.
