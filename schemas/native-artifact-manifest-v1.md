# Manifiesto nativo de archivos — NM01–NM10

Incremento de IP-NATIVE2c tras [NI01–NI11](native-image-identity-v1.md).
El investigador necesita contrastar bytes e identidad de cada archivo esperado
sin reabrir una ruta para calcular el hash de un objeto distinto del anclado.

## Requisitos EARS

- **NM01:** WHEN se configura un manifiesto THEN SHALL fijar una copia propia
  de nombres relativos ordenados, tamaños y SHA-256 esperados, antes de observar.
  SHALL NOT recibir esos valores de una solicitud del cliente como acreditación.
- **NM02:** IF el manifiesto está vacío, excede 256 archivos, tiene duplicados,
  nombres absolutos/no normalizados/control/escape, digest cero, archivo vacío,
  archivo mayor que 256 MiB o total mayor que 512 MiB THEN SHALL rechazar sin IO.
- **NM03:** WHEN se calcula un digest THEN SHALL leer el descriptor anclado en
  bloques de hasta 64 KiB, contrastar tamaño y EOF, y comprobar identidad antes y
  después. IF hay error, lectura corta, crecimiento o cambio THEN SHALL rechazar.
- **NM04:** WHEN se verifica un manifiesto THEN SHALL comprobar todos sus archivos
  dos veces, contrastar hashes/tamaños esperados y exigir estabilidad de objetos
  y bytes entre pasadas y frente a la primera verificación de esa instancia.
- **NM05:** IF falta un archivo, cambia aunque conserve sus bytes, falla el hash o
  se pierde la fuente THEN SHALL vaciar el resultado y fallar permanentemente,
  conservando la primera causa incluso si se restaura la ruta/contenido.
- **NM06:** WHEN el adaptador macOS resuelve un nombre THEN SHALL partir de una
  raíz anclada, usar componentes sin symlinks y mantener descriptores propios.
  WHEN revalida THEN SHALL contrastar raíz y archivo retenidos con la resolución
  actual. SHALL NOT exponer ni transferir sus descriptores al consumidor.
- **NM07:** WHEN la fuente declara una versión de datos de caché THEN SHALL leer
  solamente campos presentes en esa versión. Un UUID/nombre/base por sí solo
  SHALL NOT acreditar archivos de caché, subcachés, traducción AOT o sus imágenes.
- **NM08:** WHILE faltan acreditación de caché y composición con mappings,
  nacimiento y revisión del cargador THEN SHALL mantener IP-NATIVE2c abierto,
  sin Observation, admisión, capacidades ni acceso a RAM del juego.
- **NM09:** WHEN se prueba THEN SHALL incluir vectores SHA-256 independientes,
  bloques/EOF, errores de lectura/hash, sustitución con bytes iguales/distintos,
  symlinks en componentes, raíz sustituida, manifiesto ausente/incorrecto y
  terminales; SHALL distinguir dobles y archivos/procesos reales.
- **NM10:** WHEN se entrega THEN SHALL compilar Debug/Release/ASan-UBSan/cobertura,
  integrar tests al pipeline host y conservar etapas, fuentes, fallos y recibos.

## Diseño y decisiones

`AnchoredDigest` usa puertos estrechos de identidad, bytes y algoritmo. El bucle
está acotado por tamaño y bloque; una lectura corta se rechaza conservadoramente
sin reintento. `ManifestGuard` conserva la configuración y compara dos pasadas
completas, incluyendo todos los archivos declarados aunque no estén cargados.
Los dos objetos son de un propietario y de fallo terminal. Ninguno consulta dyld
ni considera que un archivo esperado implica una imagen efectivamente cargada.

`MacOSArtifactFiles` posee una raíz de directorio y los descriptores de archivos.
Resuelve componentes mediante openat/O_NOFOLLOW/O_DIRECTORY, con nombres
acotados; fstat comprueba tipo e identidad, y pread lee sin modificar el offset
compartido del descriptor. También vuelve a resolver la raíz absoluta sin
symlinks. El adaptador SHA-256 usa CommonCrypto del sistema; no se implementa
criptografía propia. Cada archivo vuelve a hashearse en cada pasada.

El manifiesto recibe nombres, tamaños y hashes de evidencia fijada por el
investigador/lanzador, **no del proceso que se intenta acreditar ni del cliente**.
Los tests sintéticos usan valores conocidos; una prueba del candidato usará el
inventario SRC89/SRC92 previamente custodiado. Que sus archivos coincidan en disco
no verifica que una instancia de PCSX2 los esté ejecutando.

No se enumeran aquí archivos adicionales del bundle ni se rechaza por sí solo un
archivo extra sin cargar. La futura composición debe rechazar cualquier imagen
cargada sin correspondencia acreditada, incluso si todo el manifiesto coincide.
No se promete exclusión de escrituras ni inmunidad a manipulación maliciosa de
memoria dentro del propio proveedor. No se produce un hash de inventario completo.

## Caché del host

La sonda x86_64 local obtuvo TASK_DYLD_INFO y copió la estructura propia mediante
mach_vm_read_overwrite. La versión informada fue 17; los campos sharedCacheFSID
y sharedCacheFSObjID están documentados en el SDK desde la versión 18. El primer
intento rechazó ese requisito y se conserva como resultado negativo. La versión
17 permite observar UUID/base y AOT, pero eso no sustituye el vínculo con objetos.

La [descripción de Apple de la caché](https://github.com/apple-oss-distributions/dyld/blob/main/doc/CacheLayout.md)
explica su distribución en varios archivos y mappings. Es una referencia de
diseño, no prueba de que esa fuente coincida con el dyld instalado. No se importa
su código. La política sigue siendo rechazar evidencia incompleta.

## Tareas

1. **NM-T1:** implementar digest acotado y comparador de manifiesto, con dobles
   para fallos y cambios en cada pasada (NM01–05,09).
2. **NM-T2:** implementar raíz/descriptores y CommonCrypto; probar filesystem
   real y cotejar vectores independientes y candidato custodiado (NM03–06,09).
3. **NM-T3:** conservar sondas de caché, validar builds/tests/negativos y publicar
   límites sin cerrar la composición del inventario (NM07–10).
