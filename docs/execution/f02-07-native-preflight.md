# F02.07 — Causa del rechazo de preflight en VM

Fecha: 2026-10-19. Contrato [PF01–PF07](../../schemas/native-preflight-diagnostic-v1.md).
Evidencia [SRC118](../compatibility/native-preflight-evidence.json).

## Resultado

**RT-T3a queda completo:** el registro de módulos alcanza sus **1.024 entradas**
y se invalida ante otro intento de alta, con revisión **1.025**. Después,
`MacOSImageEvents::read` falla y el preflight rechaza por `first_read` antes de
inspeccionar cualquier encabezado. La segunda copia diagnóstica reproduce la
misma secuencia en dos arranques con perfiles independientes.

El control sin VM de esa copia también registra `capacity` con los mismos
contadores, después de `SH3_RT_END reason=9`: el servicio había cerrado sin
adquirir inventario, pero el registro de proceso seguía recibiendo eventos.
La medición posterior debe cubrir también el frontend normal de PCSX2.

Esto identifica la condición que rechaza; **no hay corrección de capacidad,
inventario válido ni muestras aceptadas**. La comprobación de capacidad ocurre
antes de buscar duplicados: no se ha medido el total de imágenes del proceso ni
demostrado que el alta adicional tenga una dirección nueva. No se aumenta el
límite ni se omite un evento para permitir la adquisición.

## Diagnóstico y separación de responsabilidades

La primera copia sustituye solo `preflight()` y su include de salida en código
propio. Registra API/rango, snapshot inicial, lectura/header, bit de caché fuera
de rango y diferencias del snapshot final. Dos VM devuelven `first_read`.

La segunda conserva esa traza y añade información a las transiciones a fallo
de `ImageLedger`: revisión inicial/exhausta, dirección nula, capacidad, alta
duplicada y retirada desconocida. No modifica su ABI ni estado. La traza del
registro usa un buffer local de 192 bytes y una escritura; no añade estructuras
dinámicas, contadores compartidos ni recuperación del registro.

Ambos fixtures son diagnósticos privados. La biblioteca pública, contratos del
socket, dueño IO, Host/VMManager y criterios de admisión conservan sus bytes de
SRC117. La salida local puede afectar el tiempo observado; no prueba estabilidad
temporal ni rendimiento del candidato sin instrumentación.

## Validación

- Primera iteración: **20 casos × 3 modos = 60**; segunda: **46 × 3 = 138**.
  Total **198 ejecuciones** en Debug, Release y ASan/UBSan. Incluyen bit de caché
  falsificado, límites del registro, duplicados, retirada desconocida, fork y
  eventos concurrentes. Todas pasan y se comprueban las etiquetas de rechazo.
- Dos copias privadas de **3.040 archivos**; cambian uno y dos archivos propios
  respectivamente. Cada cuerpo sustituido permite reconstruir exactamente el
  anterior. La comparación de hashes conserva SRC117 y la primera iteración.
- Enlaces completos con flags originales x86_64/ThinLTO; se reutilizan **469**
  y **468** entradas verificadas. Parten de **20,65 GiB** y **20,16 GiB** libres,
  duran **22,153 s** y **21,198 s**, y respetan IB02 y el suelo de 10 GiB.
- Cada paquete tiene **200 archivos regulares y 42 Mach-O**; firma ad hoc,
  dependencias y rutas de frameworks verificadas. Ambos pasan `-testconfig` y
  el control sin VM, que devuelve `unavailable` y termina con código cero.
- **Cuatro arranques de VM** en total, dos por candidato. Todos tienen PINE
  activo, rechazo de inventario, cierre de IO y salida cero. Identifican
  SLES-51434, revisión 1.02, CRC 5088CCDB y BIOS Europa 2.00; registran cero
  segundos de juego y liberación de memoria al salir.
- Se validan los enlaces, custodia y arquitectura del repositorio al publicar.
  No se repiten las 2.132 ejecuciones de SRC117 ni sus 16 TSan y 113 tests
  originales; su evidencia se conserva. No se ejecuta CI remota, Linux ni 3DS.

La primera auditoría de publicación suponía que el control sin VM no registraba
ningún fallo del ledger y se detuvo ante la traza real. Esa expectativa se
corrige en una versión nueva del auditor, preservando el intento anterior;
no se modifica ni se repite el resultado observado para ocultarlo.

SHA-256 del segundo ejecutable:

`095e7a96e399db8e7251569fda3efe005a59ba1ee6e461ec8401889a3eeeb1db`

## Siguiente corrección

1. Medir la demanda de módulos con un censo separado que no conceda inventario:
   distinguir un alta nueva de una duplicada cuando el registro está lleno,
   observar altas/bajas y repetir con el mismo perfil de VM y el frontend sin VM.
2. Derivar una capacidad explícita y su presupuesto de memoria/tiempo de esa
   medición; revisar todos los consumidores del límite y probar el borde y
   exceso. No basta con cambiar una constante y obtener un arranque exitoso.
3. Construir un candidato nuevo con los inputs fijados y comprobar muestras
   positivas, sin asumir cubiertos lifecycle, JIT, caché, DMA u otros escritores.

**RT-T3b/RT-T3c, RS-T3/RB-T3/DW-T3 y captura siguen abiertos.** Identificar el
rechazo permite preparar la corrección; no habilita capacidades ni ejecución
admitida. ISO, BIOS, perfiles, logs y paquetes permanecen privados.
