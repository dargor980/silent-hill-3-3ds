# Vínculo de página con archivo — NP01–NP10

Como investigador quiero identificar el archivo que respalda una página de una
imagen del sistema, incluso cuando el mapping de región está detrás de shadows.
Este vínculo es una pieza de IP-NATIVE2c2; no acredita por sí solo toda la caché.

## Requisitos EARS

- **NP01:** WHEN se vincula una dirección THEN SHALL comparar el objeto de su
  página con el de una referencia mapeada desde un descriptor de archivo retenido.
  Ruta, bytes iguales o UUID SHALL NOT sustituir la identidad del objeto del kernel.
- **NP02:** WHEN se crea la referencia THEN SHALL abrir un archivo regular no
  vacío, rechazar symlinks en todos los componentes y retener descriptor y mapping
  de solo lectura, compartido, en offset cero hasta destruir la referencia.
- **NP03:** WHEN se consulta la página THEN SHALL exigir objeto no nulo, página
  residente y externa, sin marcas dirty/copied/paged-out/fictitious/tainted.
  El adaptador puede leer un byte del proceso propio para resolver su residencia;
  SHALL NOT publicar ese byte ni aceptar direcciones por transporte del cliente.
- **NP04:** WHEN la referencia tiene offset distinto de cero o el offset objetivo
  queda fuera del archivo THEN SHALL rechazar el vínculo sin acceso fuera de rango.
- **NP05:** WHEN se muestrea THEN SHALL leer dos veces referencia y objetivo,
  verificar igualdad de objeto/offset y continuidad del objeto de archivo.
- **NP06:** WHEN cambian archivo, objeto VM u offset, o se pierde una fuente THEN
  SHALL borrar la salida y conservar permanentemente la primera causa del fallo.
- **NP07:** WHEN cambia el proceso propietario, incluida herencia por fork THEN
  SHALL rechazar la reutilización de ancla y consulta. Una instancia nueva solo
  podrá usarse dentro de una nueva evaluación de identidad del proceso.
- **NP08:** WHEN se valida THEN SHALL distinguir mapping del mismo archivo, copia
  con iguales bytes, reemplazo de ruta, escritura copy-on-write, página inaccesible,
  cambio de offset y estados/errores simulados del kernel.
- **NP09:** WHILE solo una dirección se haya vinculado THEN SHALL limitar la
  afirmación a esa página/offset. SHALL NOT extenderla a todos los segmentos,
  subcachés, código AOT, integridad de bytes o completitud del inventario.
- **NP10:** WHEN se ensaya la caché real THEN SHALL conservar por separado el
  resultado observado, el manifiesto/hashes aún ausentes y los casos sintéticos.
  SHALL NOT ampliar los límites NM, ni habilitar admisión o captura.

## Diseño

`PageBinding` recibe una dirección, un `PageFileSource` y un `PageSource`. Compara
dos pares de lecturas y mantiene un resultado terminal. La referencia devuelve
FileObject y PageReading de su mapping en offset cero. El objeto VM es una clave
opaca del kernel, no un inode, una dirección física ni un handle persistente.
La retención de descriptor/mapping evita usar una referencia ya liberada.

`MacOSPageAnchor` posee descriptor, mapping y PID; resuelve la ruta absoluta por
componentes mediante openat/O_NOFOLLOW. Comprueba metadata retenida y resolución
actual antes/después de consultar la referencia. `MacOSPageSource` usa
mach_vm_read_overwrite para un byte y mach_vm_page_info con tamaño de respuesta
exacto. Descarta el byte. Las flags se traducen a propiedades portables; referencias
y recuentos/depth transitorios no forman la identidad estable.

El núcleo es independiente del sistema operativo, no copiable y de propietario
único. El adaptador solo se compila en macOS. No modifica los módulos NB/NI/NM/NC
ni los conecta automáticamente al proveedor. Un resultado positivo no es un hash
del archivo ni prueba de que una página validada por firmas cubra todo el archivo.

## Tareas

- **NP-T1 / NP01,04–06,09:** núcleo, resultados vacíos, continuidad y pruebas de
  equivalencia, offsets, fuentes perdidas y restauración tras fallo.
- **NP-T2 / NP02–03,07–08:** ancla y consultas macOS; probar mappings reales,
  copias, sustitución, COW, symlinks, página inaccesible y fork.
- **NP-T3 / NP08–10:** cuatro modalidades, negativos compilados, cobertura y
  sonda local con las catorce partes x86_64/AOT observadas. Conservar evidencia.
- **Pendiente:** política de integridad de caché y cobertura completa de sus
  rangos e imágenes antes de ampliar InventoryGuard e integrar IP-NATIVE3.
