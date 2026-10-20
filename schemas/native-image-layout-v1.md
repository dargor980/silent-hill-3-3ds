# Inventario de segmentos Mach-O — v1

Parte de CI-T4/IP-NATIVE2c2. Precedentes:
[CI](native-cache-integrity-v1.md), [NC](native-inventory-v1.md).

## Requisitos EARS

- **NL01:** CUANDO se observe una imagen, el lector DEBERÁ recorrer exactamente
  todos sus load commands declarados y devolver todos sus segmentos, sin truncar.
- **NL02:** SI faltan bytes, el formato no es Mach-O de 64 bits little endian
  admitido, las cuentas exceden límites o los tamaños/offsets desbordan, el lector
  DEBERÁ devolver fallo con salida vacía.
- **NL03:** CUANDO se adquieran metadatos de memoria, el lector DEBERÁ copiar desde
  el proceso propio a través de un puerto acotado, comprobar dos copias completas
  y rechazar diferencias, PID cambiado o lectura inaccesible.
- **NL04:** CUANDO se interprete un segmento, el lector DEBERÁ conservar nombre,
  dirección, tamaño virtual, rango de archivo, protecciones, flags y cantidad de
  secciones; DEBERÁ rechazar solapamientos virtuales y cabeceras ambiguas.
- **NL05:** CUANDO un segmento tenga cola zero-fill, permisos de escritura,
  protecciones especiales o fixups, el informe DEBERÁ registrarlo explícitamente.
  La clasificación de metadatos SHALL NOT acreditar identidad de sus páginas.
- **NL06:** CUANDO una imagen pertenezca a la caché, el sistema DEBERÁ conservar
  sus offsets declarados sin inferir qué subcaché los respalda; la asociación
  real seguirá requiriendo el kernel y los descriptores verificados.
- **NL07:** CUANDO se inspeccione el candidato, la prueba DEBERÁ distinguir archivo
  conservado, copia instrumentada y proceso propio; solo ejecutará testconfig,
  con perfil privado nuevo y sin solicitar VM/ISO/BIOS.
- **NL08:** SI una sonda no se carga, cambia el inventario o se excede capacidad,
  el informe DEBERÁ registrarlo como cobertura ausente/inestable aunque el proceso
  termine con código cero.
- **NL09:** CUANDO se mida coste, el informe DEBERÁ separar adquisición de archivos,
  enumeración de metadatos y verificación de páginas; no trasladará una operación
  de cien segundos al coordinador por considerarla equivalente a una lectura.
- **NL10:** CUANDO se entregue, DEBERÁ conservar fuentes/etapas/sondas y verificar
  builds, sanitizadores, límites, cambios entre copias y controles de regresión;
  no declarará admisión ni cobertura completa a partir del inventario estructural.

## Diseño

Núcleo portable `read_image_layout(ByteSource&, ImageLayout&)`: header de 32 bytes,
como máximo 4096 comandos, 1 MiB de comandos y 64 segmentos. Copia metadatos en
bloques de hasta 64 KiB; verifica header inicial y dos copias completas. Decodifica
campos little endian sin casts de estructuras/alineación del host. Los comandos
no interpretados conservan su posición en el recorrido, sin afirmar validación
semántica de su payload. No es un parser general de fat Mach-O ni de objetos .o.

Se aceptan x86_64/arm64 y tipos ejecutable/dylib/bundle/dyld. Segmentos de 72 bytes
más 80 bytes por sección; sus tamaños deben concordar con el comando. Los campos
de secciones no se usan para reducir cobertura. El segmento __TEXT debe ser único
y contener la cabecera completa; el resto se conserva incluso vacío o reservado.

`MacOSImageBytes` implementa el puerto con mach_vm_read_overwrite, tamaño recibido
exacto, dirección base del proveedor y PID antes/después. No desreferencia
punteros del cargador directamente ni acepta direcciones desde un cliente.
El lector es una operación sin estado: el consumidor decide el fallo terminal y
la continuidad entre observaciones mediante nacimiento/revisión/inventario.

La sonda del candidato es diagnóstica: prueba primero el artefacto conservado.
Si Hardened Runtime impide cargarla, conserva ese resultado y prepara una copia
privada nueva con el único entitlement adicional para variables DYLD, manteniendo
runtime y el original intactos. La copia tendrá identidad/firma distintas y no
se usará como evidencia de admisión del original. Se contrastan todos los archivos
antes/después y se exige evidencia explícita de que la sonda sí se ejecutó.

## Capacidad del inventario

La sonda inicial registró 556 imágenes y la final 645 en la copia instrumentada.
Este contrato actualiza el límite de NC02/NI para imágenes cargadas a **1024**,
sin truncamiento y con fallo terminal al excederlo. Los manifiestos de archivos
mantienen capacidades distintas: **256 bundle / 32 caché**. El límite de imágenes
es un presupuesto de esta implementación, no una garantía de cualquier host.
Se reejecutan las pruebas de capacidad, agotamiento y composición con ese límite.

## Tareas

- [x] **NL-T1 / NL01–06:** implementar lector portable y puerto nativo, fixtures
  de comandos/segmentos, límites y cambios; integrar al CMake host.
- [x] **NL-T2 / NL07–09:** inventariar los 42 binarios conservados y los procesos
  instrumentados, medir metadatos, clasificar rangos pendientes y comprobar
  capacidad real sin omitir imágenes ni confundir counts con una revisión.
- [x] **NL-T3 / NL10:** ejecutar cuatro configuraciones y negativos compilados,
  publicar custodia y actualizar CI-T4 con el resultado observado.

Después: política de rangos transformados, identidad/cobertura de páginas para
cada imagen, control de revisión y revalidación acotada antes de IP-NATIVE3.
