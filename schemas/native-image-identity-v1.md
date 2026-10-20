# Identidad nativa de imágenes — NI01–NI11

Desarrollo de IP-NATIVE2 bajo [IP02–05](process-diagnostic-v1.md). El investigador
necesita distinguir el objeto que respalda un mapping del archivo que ahora
ocupa su ruta, y detectar cambios del cargador aunque restaure el conjunto inicial.

## Requisitos EARS

- **NI01:** WHEN se vincula una imagen de archivo THEN el núcleo SHALL contrastar
  identidad de archivo anclado y región obtenida del kernel del proceso propio.
  Una ruta, nombre de dyld o hash del cliente SHALL NOT acreditar el mapping.
- **NI02:** WHEN se abre un ancla THEN SHALL conservar el descriptor y exigir
  archivo regular, ruta absoluta sin symlink final, dispositivo/inodo no nulos,
  tamaño y tiempos válidos; WHEN se revalida THEN SHALL contrastar descriptor y
  ruta. Sustitución por otro objeto con bytes iguales SHALL invalidar el ancla.
- **NI03:** WHEN se acepta el vínculo THEN SHALL exigir dos lecturas coincidentes
  del archivo y del mapping, cabecera en inicio de región, offset cero y región
  válida sin overflow. Este primer perfil SHALL limitarse a Mach-O delgado con
  cabecera en offset cero; SHALL NOT aceptar un slice universal por aproximación.
- **NI04:** IF falta una lectura, cambia el objeto/región o se pierde el vínculo
  THEN SHALL devolver salida vacía, conservar la primera causa y rechazar para
  siempre esa instancia, incluso si vuelve el estado anterior.
- **NI05:** WHEN dyld notifica una imagen THEN SHALL mantener un inventario
  acotado de direcciones y avanzar una revisión por cada carga/descarga. WHEN el
  conjunto vuelve al anterior THEN SHALL conservar una revisión distinta.
- **NI06:** IF hay duplicado, descarga desconocida, dirección nula, capacidad
  agotada o revisión agotada THEN SHALL invalidar el inventario sin wraparound.
- **NI07:** WHILE funcionan las notificaciones THEN SHALL serializar acceso al
  registro, sin IO, asignaciones explícitas ni llamadas a dyld en callbacks; una
  lectura SHALL copiar solo números, sin desreferenciar imágenes descargables.
  WHEN un hijo hereda el registro por fork THEN SHALL rechazar antes de bloquear.
- **NI08:** IF una imagen del sistema no tiene evidencia suficiente del objeto
  que la respalda THEN SHALL quedar sin acreditar. La pertenencia por nombre a la
  caché de dyld SHALL NOT equivaler a verificar esa caché o aprobar la imagen.
- **NI09:** WHEN se entrega esta unidad THEN SHALL probar sustitución real por
  bytes iguales/diferentes, pérdida de ruta, dependencia nueva, descarga/recarga,
  errores/parciales de API y terminales; SHALL distinguir pruebas nativas y dobles.
- **NI10:** WHEN se verifica THEN SHALL ejecutar Debug, Release y ASan/UBSan,
  conservar fuentes y recibos y añadir los tests al pipeline host existente.
- **NI11:** UNTIL exista manifiesto aprobado, digest del descriptor, evidencia
  de todas las imágenes y muestreo coordinado THEN SHALL mantener IP-NATIVE2
  abierto y SHALL NOT producir Observation, habilitar admisión o leer RAM.

## Diseño

`ImageBinding` compara puertos `FileIdentitySource` y `MappingSource`; no conoce
syscalls, dyld, hashes, PCSX2 ni transporte. Conserva una sola identidad inicial
y pasa de vacío a válido o a fallo terminal. `FileObject` incluye dispositivo,
inodo, tamaño y mtime/ctime con nanosegundos. No es un digest del contenido.

`MacOSFileAnchor` abre una vez con O_RDONLY/O_CLOEXEC/O_NOFOLLOW. Mantiene el
descriptor hasta su destrucción; fstat y lstat deben coincidir entre sí y con el
objeto inicial. No resuelve symlinks intermedios como política de confianza; el
manifiesto futuro deberá anclar raíces y hashes. `MacOSMappingSource` consulta
PROC_PIDREGIONPATHINFO con getpid, valida respuesta exacta, PID estable y vnode
regular. No usa el nombre devuelto como prueba. Una respuesta sobre una región
posterior o sin vnode se rechaza en el adaptador/núcleo.

El vínculo acredita el **archivo que respalda la región de cabecera**. No afirma
que todos los segmentos, relocations o bytes de memoria sean idénticos al disco.
No resiste manipulación maliciosa dentro del propio proceso. Lecturas dobles no
constituyen exclusión de escritores ni retienen imágenes; la integración deberá
rodearlas con revisión del cargador, nacimiento y coordinador del proveedor.

`ImageLedger` es un núcleo sin asignaciones y de un propietario: hasta 256
direcciones, revisión positiva y terminales. `MacOSImageEvents` lo encapsula en
un registro de vida de proceso, porque dyld no ofrece desregistro. Registra
primero descargas y después cargas (incluida enumeración inicial); un evento no
reconciliable durante arranque falla cerrado. pthread_once serializa registro;
un mutex protege únicamente el ledger y la copia. Ninguna llamada dyld se hace
con ese mutex tomado. Un PID atómico permite rechazar fork antes de once/mutex.
El consumidor recibe una copia, nunca un puntero al registro ni memoria de imagen.

## Decisión sobre caché del sistema

La sonda local x86_64 obtuvo vnode para su ejecutable y dev/inodo cero para las
imágenes de caché, incluida libRosetta. Por eso este incremento no introduce una
allowlist por /usr/lib o /System. Se requiere investigación adicional de identidad
de caché y política explícita antes de acreditar el inventario completo.

## Tareas y aceptación

1. **NI-T1 / NI01–04,09:** ancla, adaptador de mapping y núcleo; dobles para
   inestabilidad/errores y pruebas reales con dylib propia y reemplazo por rename.
2. **NI-T2 / NI05–07,09:** ledger y callbacks nativos; pruebas de capacidad,
   agotamiento, dependencia nueva, unload/reload real y fork heredado.
3. **NI-T3 / NI08–11:** builds, sanitizadores, cobertura diagnóstica y custodia;
   documentar límites y mantener pendientes manifiesto/digest/caché/integración.
