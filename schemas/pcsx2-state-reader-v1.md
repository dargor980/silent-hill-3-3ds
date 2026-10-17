# Lector acotado de estados PCSX2 v2.8.2

F02.07 · complemento de CO02–CO06 · formato host, sin cambios al runtime 3DS.

## Requisitos EARS

- **PS01:** CUANDO se importe un estado, el lector DEBERÁ aceptar únicamente el
  contenedor ZIP acotado y la identidad exacta `0x9A590000`/`v2.8.2`; otra versión,
  ZIP64, cifrado, duplicados o estructura truncada DEBERÁN producir rechazo.
- **PS02:** CUANDO se decodifiquen registros EE, el lector DEBERÁ comprobar las
  etiquetas BIOS/cpuRegs, longitud de ruta ELF, indicador de ejecución y CRC esperado,
  y devolver PC, estado de delay slot y los 32 bits bajos de los 32 GPR sin imprimirlos.
- **PS03:** CUANDO se soliciten registros para un punto CO, el lector DEBERÁ exigir
  PC exacto, ausencia de delay slot y selección explícita de registros únicos 0–31.
  Deberá devolver solo esos registros, con ocho dígitos hexadecimales minúsculos.
- **PS04:** SI se exceden 64 MiB de archivo, 64 entradas ZIP, 64 KiB de directorio
  central, 1 MiB de estructuras internas o 1024 bytes de ruta ELF, el lector DEBERÁ
  rechazar antes de la operación que pueda exceder el presupuesto correspondiente.
- **PS05:** CUANDO se lea un archivo privado, el adaptador DEBERÁ exigir raíz externa
  al checkout, directorio 0700, archivo regular 0600 sin enlaces y SHA-256 esperado;
  un cambio de identidad durante lectura/cierre DEBERÁ impedir devolver el resultado.
- **PS06:** SI el Python host no admite la compresión del miembro, el lector DEBERÁ
  informar un error explícito sin instalar dependencias ni extraer archivos al disco.
- **PS07:** CUANDO una lectura sea válida, el resultado DEBERÁ conservar carácter
  privado y no acreditar por sí mismo pausa, orden de invocaciones, sesión, identidad
  del binario host o ejecución auténtica. El validador CO sigue siendo obligatorio.

## Diseño y límites

`pcsx2_state.py` separa validación del ZIP, decodificación pura de la estructura y
selección para un punto. `state_files.py` posee exclusivamente custodia POSIX e I/O;
reutiliza el recorrido de directorios anclado existente. No hay CLI que imprima GPR,
no hay conexiones al emulador y no se modifican los contratos de captura previos.

La estructura está fijada al layout little-endian x86_64 de la versión instalada.
Se consultaron `SaveState.cpp/.h`, `VMManager.cpp` y `R5900.h` oficiales v2.8.2,
registrados en [SRC24](../docs/compatibility/camera-runtime-attempt-evidence.json).
El lector usa hechos del formato; no incorpora esos archivos ni declara clean room.
La identidad dentro del ZIP es una declaración modificable, no autenticación.

El ZIP debe tener EOCD final sin comentario, un disco y directorio central contiguo;
las cabeceras locales/centrales no admiten campos extra ni versión ZIP64.
Antes de construir `ZipFile` se cuentan las entradas centrales reales y se validan
sus presupuestos, sin confiar solo en el contador declarado. Solo se descomprimen los
miembros de versión y estructuras; se comprueban sus tamaños y CRC ZIP completos.
Otros miembros no se interpretan ni se descomprimen. No se certifica la integridad
semántica del estado completo ni se leen `eeMemory.bin`/recursos originales.

El bloque comienza con etiqueta BIOS de 32 bytes, checksum de 4 y descripción de 256;
siguen CRC ELF, longitud/ruta y un booleano de un byte. Tras la etiqueta cpuRegs,
cada GPR ocupa 16 bytes; PC está a 680 y delay slot a 676 desde el inicio de cpuRegs.
No se busca la etiqueta por coincidencia libre ni se acepta un archivo de otra
versión por tener bytes parecidos. El resto de la estructura permanece opaco.

## Tareas y aceptación

1. Implementar decodificador puro y selección explícita (PS01–PS04/PS07).
2. Implementar custodia privada sin ampliar límites de `PrivateCaptureReader` (PS05).
3. Probar fixtures propios: endian/anchura, PC/slot, CRC/versión, truncamientos,
   bombas declaradas, duplicados, ZIP corrupto, compresión no disponible, symlinks,
   hardlinks, permisos, cambios tardíos y hash incorrecto (PS01–PS07).
4. Contrastar el control privado conocido de entrada del ELF, sin publicarlo como
   evento CO; ejecutar regresión, cobertura y custodia. La captura real sigue abierta
   hasta obtener y validar invocaciones completas en la sesión del depurador.

## Evidencia de cierre

Implementación y 82 pruebas propias completadas; 1.517 pruebas de regresión aprobadas.
Los dos módulos alcanzan 100 % de líneas y ramas. Control privado en entrada del ELF
y nueve estados reimportados, con selección exacta de PC/GPR. Las tres invocaciones
se validaron con dos recibos CO idénticos. [Resultado y límites](../docs/execution/f02-07-camera-runtime-capture.md).
