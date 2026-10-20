# F02.07 — Integridad de archivos y rangos de caché (SRC96)

CI-T1–3 implementa [CI01–CI10](../../schemas/native-cache-integrity-v1.md): hash
completo desde el mismo descriptor que respalda la referencia de página y
verificación exhaustiva de los rangos declarados. IP-NATIVE2c2 continúa abierto
hasta integrar la política y el inventario completo del candidato.

## Implementación

- `AnchoredDigest` y `ManifestGuard` reciben un dominio del proveedor, con bundle
  por omisión. Bundle conserva 256 MiB/archivo, 512 MiB totales y 256 entradas.
  Caché tiene una política separada de 2 GiB/archivo, 16 GiB totales y 32 entradas.
  Se rechazan dominios desconocidos antes de leer bytes.
- `MacOSPageAnchor` implementa puertos separados para identidad, bytes y página;
  mmap y pread usan el mismo descriptor privado. Mantiene comprobaciones de ruta,
  metadatos, fork, RAII y fallo terminal. El hash utiliza bloques de 64 KiB.
- `CacheRangeGuard` posee el digest esperado y una copia de rangos ordenados;
  valida límites/alineación y recorre cada página en dos pasadas completas,
  con referencia antes/después. Una página intermedia inaccesible, modificada,
  de otro objeto o con offset incorrecto invalida toda la salida.

La identidad no se deduce de la ruta. Los bytes del juego no intervienen. El
adaptador SHA utiliza CommonCrypto; no se introduce otro algoritmo criptográfico.
El guard de rangos no enumera imágenes ni sustituye el cierre de nacimiento,
archivos y revisión de loader que deberá realizar la composición.

## Validación ejecutada

| Comprobación | Resultado |
| --- | --- |
| Debug / Release / ASan+UBSan / cobertura, x86_64 macOS | 166 escenarios por configuración; 664 ejecuciones correctas |
| Escenarios conservados | 144 |
| Escenarios nuevos | 12 portables y 10 nativos |
| Núcleo de rangos | 100% líneas y ramas: 65/65 y 82/82 |
| Digest/manifiesto | 100% líneas, 97,69% ramas |
| Adaptador de páginas/bytes | 98,92% líneas, 84,33% ramas |
| Regresiones compiladas | Cuatro detectadas con salida 1 |
| Python de compatibilidad/diagnóstico | 122 pruebas correctas |
| Ruff | Sin errores; 139 archivos con formato correcto |

Los negativos omiten una página, ignoran el offset, omiten la segunda pasada y
amplían indebidamente el límite del bundle. Los fixtures nativos verifican hash
conocido, reemplazo/escritura durante pread, fork, errores de lectura y una página
intermedia COW o sin acceso. Los límites de 2 GiB se recorren con una fuente
sintética sin crear archivos gigantes. Las sondas reales sí leen todos los bytes
de los archivos grandes del host.

Los tests se incorporaron al CMake del pipeline host existente. Esta evidencia
es local: no se ejecutaron CI remoto, Linux, arm64 ni detección de fugas.

## Caché real y procedencia del manifiesto

La primera sonda Release retuvo las catorce partes x86_64/AOT observadas: siete
`dyld_shared_cache_x86_64*` y siete `aot_shared_cache.*`. Total:
**11.845.999.933 bytes**. Calculó una línea base y la contrastó en dos pasadas
completas adicionales desde los descriptores retenidos, sin copiar archivos.

Después, el investigador fijó nombres, tamaños y SHA-256 en un manifiesto de
metadatos con procedencia y hash del log anterior. Un segundo proceso recibió
ese manifiesto como constantes del driver, antes de observar sus archivos, y lo
contrastó en dos pasadas. No lo recibió del cliente ni lo recalculó para sustituir
valores esperados. La sonda inicial tardó 161,94 s y la verificación fijada 106,44 s en este host.
Este coste todavía no es apropiado para una comprobación por frame ni para
bloquear el coordinador de CPU durante cada diagnóstico. La integración deberá
definir y medir adquisición/revalidación manteniendo las garantías del contrato.
La procedencia es adquisición local custodiada; no demuestra
firma del fabricante ni garantiza portabilidad a otra versión de macOS.

Ambos procesos vincularon las bases de caché/AOT y 44 imágenes del sistema con
archivos retenidos. Para el recorrido de rangos se verificaron **solo los primeros
64 KiB de cada una de 28 regiones**: 448 consultas de página por pasada,
1.835.008 bytes en total, sin fallos. Las regiones completas suman
11.249.516.544 bytes. La sonda declara explícitamente `complete_ranges=0` y
`complete_inventory=0`; ni la cobertura de prefijos ni el hash completo del
archivo sustituyen la cobertura de todos sus mappings.

## Custodia y siguiente dependencia

Se conserva `native-cache-integrity-stage-v1` en la carpeta privada autorizada:
fuentes propias, cuatro builds, perfiles, fixtures, negativos, drivers y logs.
Los scripts/recibos están en `build/f02-07-native-cache-integrity/`. Los límites
supervisados son 10 GiB libres al iniciar y como piso, 512 MiB por etapa,
compilación de hasta 120 s, tests de hasta 60 s y 300 s para cada sonda de lectura.
Los archivos del sistema se leen; no cuentan como copias dentro de la etapa.

Las cinco transiciones respecto de SRC95 son explícitas: cabecera/implementación
del digest, cabecera/implementación del ancla macOS y ampliación de CMake. Se
conservan y verifican los snapshots anteriores; sus hashes históricos no se
reinterpretan como hashes del código actual. PCSX2, el candidato conservado,
CMake raíz y CI anterior se mantienen idénticos a la evidencia precedente.

Sigue **CI-T4 / IP-NATIVE2c2-integridad**: fijar el perfil del lanzador para el
candidato, enumerar todas sus imágenes/segmentos y resolver los rangos que sufren
relocación o COW sin omitirlos. Después se compondrán los rangos con nacimiento,
revisión y manifiestos antes/después. No hay Observation completa, peer
verificado, admisión, captura ni ejecución de la VM en esta entrega.
