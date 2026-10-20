# F02.07 — Slices Mach-O y perfil PT v2 (SRC103)

Se implementa [MS01–MS09](../../schemas/macho-slice-binding-v1.md) para vincular
cabeceras residentes con el slice exacto de un archivo thin/FAT32/FAT64. El
adaptador nativo admite el offset real comprobado y el perfil explícito
`macos_platform_slices_v2` lo incorpora al inventario. PT v1 conserva su contrato,
su restricción de offset cero y sus vectores. La clasificación completa de PCSX2
al inicio y al cierre completa PO-T3b, PO-T3 y PT-T3; sigue PT-T4.

## Implementación

El parser portable usa arreglos fijos, admite hasta 32 slices y archivos de hasta
256 MiB. Recorre dos veces toda la tabla y las cabeceras; comprueba endianidad,
límites, alineación, reserved, solapamientos, duplicados y coincidencia exacta de
CPU/subtipo. La selección exige además el offset observado por el kernel.

El binder compara los 32 bytes residentes con la cabecera del slice, repite la
lectura residente y verifica identidad del archivo antes/después. El adaptador
nativo retiene el descriptor mediante `MacOSPageAnchor`, contrasta vnode/PID al
terminar y queda invalidado tras un error. La ruta del loader solo localiza el
archivo. El mapping puede incluir padding de páginas; se vincula la cabecera,
no se afirma que toda la región tenga bytes inicializados dentro del slice.

El puerto `SliceBindingSource` separa análisis, adquisición nativa y clasificación.
`MacOSPlatformOrigins` conserva su constructor anterior y añade el que recibe este
puerto. PT v2 exige testigo en cada imagen externa, prohíbe testigos en la rama de
caché y usa dominios de hash v2 con formato/offset/tamaño/cabecera. El manifiesto
sigue verificando el archivo completo; el slice no sustituye esa autorización.

## Validación local

Se conservan los 274 escenarios anteriores y se añaden 30: parser/binder, perfil
v2 y adaptador macOS. Incluyen extremos aritméticos, tabla truncada, arquitectura
no seleccionada inválida, subtipo completo, cambios entre lecturas, inyección de
errores de hash, versiones cruzadas, vector Python/CommonCrypto independiente,
archivo sustituido o retirado, COW, fork y catálogo real bajo ASan. La fixture
universal contiene código propio y una cabecera a offset 16384; el proveedor v1
continúa rechazándola.

| Comprobación | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan, cobertura | 304 escenarios por modo; 1216 ejecuciones correctas |
| Regresiones deliberadas | Cuatro detectadas: offset, subtipo, segunda lectura y cabecera residente |
| Compatibilidad y supervisor Python | 153 pruebas correctas |
| Parser/binder | 103/103 líneas; 186/196 ramas |
| Adaptador de slices | 33/33 líneas; 35/48 ramas |
| Ruff y contrato del repositorio | Correctos |

Las métricas detalladas de cobertura y los hashes están en la
[evidencia](../compatibility/macho-slice-evidence.json). El CMake host incorpora
los targets al pipeline existente; no se ejecutaron CI remoto, Linux ni arm64.
ASan mantiene desactivada la detección de fugas, como el pipeline previo.

La combinación de perfiles de cobertura emitió nueve avisos de hash cero:
helpers inline de fixtures y el accessor `catalog_size`, definidos pero no
emitidos en dos binarios. El diagnóstico conserva los nombres exactos y el aviso;
los archivos `.cpp` medidos no figuran entre esas definiciones. El primer lector
del resumen rechazó el prefijo textual; se corrigió la extracción sin regenerar
perfiles ni ocultar el diagnóstico.

Se conservan tres incidencias de ejecución sin reescribir sus etapas:

- El primer Debug detectó dos expectativas erróneas de tests: longitud de los
  dominios y selección fuera del archivo en el caso de tabla truncada. Solo se
  corrigieron esas expectativas; los archivos de implementación son iguales.
- El primer ASan completó 303 escenarios y el supervisor lo detuvo a los 60 s
  durante el último. Se repitió con dos procesos CTest en otra etapa, conservando
  límite global de 60 s e individual de 15 s; Debug/Release aprobados se reutilizan.
- Seis pruebas Python de supervisión fallaron porque el sandbox bloqueó `/bin/ps`.
  La repetición con inspección local autorizada pasó los 153 escenarios.

## PCSX2 testconfig

Una nueva copia privada del candidato, con sus 200 archivos verificados antes y
después, ejecutó testconfig con perfil nuevo y la biblioteca diagnóstica propia.
No se recompilaron ni modificaron PCSX2 o la aplicación instalada.

| Observación | Cabeceras | Externas | Caché | Preparación / total con logging |
| --- | ---: | ---: | ---: | ---: |
| Arranque | 557 | 23 | 534 | 214,5 / 248,1 ms |
| Salida | 647 | 26 | 621 | 40,2 / 77,3 ms |

Ambas observaciones completan dos pasadas con ledger estable y catálogo de 3606.
La salida incluye `libobjc-trampolines.dylib`: FAT32 de 248480 bytes, slice x86_64
subtipo 3 a offset 16384 y tamaño 72576; la región del kernel mide 53248 bytes.
Su archivo conserva el SHA-256 registrado en SRC102. El adaptador vincula sus
bytes de cabecera con el archivo, sin excepción por ruta ni máscara de subtipo.

dyld queda fuera del ledger y bajo plataforma asumida; no se incorpora como
imagen de aplicación acreditada. Los tiempos son una sola ejecución y excluyen
el manifiesto completo: no constituyen presupuesto de producción.

## Alcance y continuación

La sonda acredita clasificación y vínculo de cabeceras. No acredita identidad
del inventario completo: falta componer el manifiesto esperado desde el lanzador,
medir adquisición/revalidación e integrar el perfil en diagnóstico y peer. Tampoco
verifica comandos/segmentos completos, firma, fixups, COW de datos, caché del
sistema, AOT o Rosetta. No promete snapshot atómico ni exclusión ABA.

**Sigue PT-T4:** inventariar todos los archivos externos observados, fijar sus
hashes antes de lanzar, componer manifiesto/nacimiento/eventos/PT v2, medir costes
y rechazar faltantes o sustituciones. Después PT-T5, peer y gates del emulador.
No se ejecutaron ISO, BIOS, VM ni captura; no se habilitan modos de ejecución.

Los scripts quedan en `build/f02-07-macho-slices/` y los snapshots/binarios en la
carpeta privada autorizada. Reserva/piso 10 GiB, máximo 512 MiB por etapa;
configure 45 s y build 120 s. Se verifican 72 fuentes y 112 binarios finales
x86_64. La evidencia registra por hash las extensiones del núcleo PT/PO y de sus
contratos; NC/CI/AP y los vectores v1 permanecen iguales.

Se consultan las declaraciones oficiales [FAT32 de XNU](https://raw.githubusercontent.com/apple-oss-distributions/xnu/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/EXTERNAL_HEADERS/mach-o/fat.h)
y [FAT32/FAT64 de cctools](https://raw.githubusercontent.com/apple-oss-distributions/cctools/main/include/mach-o/fat.h).
El SDK instalado, incluido `mach-o/fat.h`, queda fijado por hash. No se copian
implementaciones de Apple ni se distribuyen archivos del juego o del sistema.
