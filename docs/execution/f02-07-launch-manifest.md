# F02.07 — Manifiesto previo y composición PT v2 (SRC104)

Se completa PT-T4 mediante [LM01–LM07](../../schemas/platform-launch-manifest-v1.md):
configuración fijada por el lanzador, adquisición autenticada por SHA-256 esperado,
archivos por raíces y composición de nacimiento/eventos/orígenes/manifiesto/PT v2
en PCSX2 testconfig. La integración productiva, peer y captura siguen en PT-T5.

## Implementación y expectativa previa

`decode_launch_manifest` valida un buffer canónico de hasta 1 MiB; el lector
obtiene exactamente esos bytes, comprueba EOF, identidad antes/después y hash
esperado. Exige raíces absolutas distintas, claves ordenadas, tamaños/hashes
válidos, raíces utilizadas e índice principal existente. Los límites son ocho
raíces, 256 archivos, 256 MiB por archivo y 512 MiB total.

`MacOSLaunchFiles` conserva su configuración y PID, traduce claves exactas a
proveedores `MacOSArtifactFiles` con descriptor retenido y hace terminal cualquier
fallo de lectura, clave o PID. El parser, adquisición y proveedor mantienen
responsabilidades separadas. Se reutilizan los guards previos sin modificarlos.

El lanzador usa el censo SRC103 para elegir nombres y fija los hashes completos
antes de ejecutar. El manifiesto contiene 26 archivos: 24 del bundle de PCSX2,
la nueva biblioteca observadora y `libobjc-trampolines`. Incluye por tanto el hash
del propio observador sin introducir una dependencia circular en su binario.
Los 200 archivos del candidato coinciden con la referencia antes y después de
cada ejecución. La configuración externa usa tres raíces explícitas.

Un helper x86_64 obtiene el UUID esperado mediante el adaptador de orígenes ya
validado. La política referencia el snapshot del contrato LM anterior a marcar
sus tareas completas; la evidencia de plataforma referencia SRC103. El hash del
manifiesto completo pasa a `application_evidence`. Ruta/hash llegan solo desde
el lanzador privado; no se añade una selección remota ni un comando productivo.
Ese hash expresa confianza en el lanzador, no una firma ni autenticación de peer.

## Resultado y coste

La ejecución positiva tomó tres muestras de una sesión al arrancar y tres de una
sesión nueva al salir. Dentro de cada sesión se mantuvieron nacimiento, nonce,
revisión y hashes. PID/nacimiento coinciden entre fases; el nonce nuevo distingue
las sesiones, y las imágenes/revisión cambian legítimamente entre arranque/salida.

| Sesión | Archivos esperados | Aplicación / caché | Preparación | Primera muestra | Revalidaciones |
| --- | ---: | ---: | ---: | ---: | ---: |
| Arranque | 26 | 23 / 534 | 249 ms | 875 ms | 864 / 840 ms |
| Salida | 26 | 26 / 621 | 532 ms | 855 ms | 832 / 835 ms |

Los 26 archivos suman 56387192 bytes (53,78 MiB). Cada muestra lee cuatro veces
el conjunto completo: 104 lecturas de archivo y 225548768 bytes (215,10 MiB).
Las seis muestras positivas acumulan 1353292608 bytes (1,26 GiB), sin contar
metadata, EOF, configuración ni cabeceras. El lector verifica hashes completos
en cada pasada: el coste no se sustituye por timestamps.

Estas seis muestras de un equipo y una ejecución, con cachés del sistema sin
purgar, no describen un percentil, peor caso o presupuesto para ejecución por
frame. El coste medido es demasiado grande para repetirlo por frame. Para PT-T5
se fija como presupuesto provisional de aceptación 5 s para preparación+muestra
inicial y 2 s por revalidación; las muestras observadas caben, pero aún falta
implementar el deadline/cancelación y ensayar excedencias en el integrador.
No se habilita el coordinador con esa condición pendiente. El supervisor de
laboratorio conserva su límite externo de 60 s por proceso.

## Rechazos y pruebas

Cuatro ejecuciones adicionales del mismo candidato comprueban:

- Hash de configuración alterado: rechazo de la adquisición en ambas fases.
- Digest esperado del ejecutable incorrecto: fallo de manifiesto terminal.
- Plugin de estilo omitido: arranque válido y rechazo por archivo no cubierto
  cuando aparece al salir. No se aprende ni agrega el archivo desde el proceso.
- Índice principal apuntando a una biblioteca: rechazo terminal de imagen principal.

La nueva consulta tras un fallo del inventario permanece fallida con perfil vacío.
No hay fallback, reinicio del guard ni permiso implícito. Los procesos testconfig
terminan con código cero incluso en estos negativos; el lanzador valida los
resultados internos y no confunde ese exit code con inventario válido.

| Validación local macOS x86_64 | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan y cobertura | 323 escenarios × cuatro modos = 1292 ejecuciones correctas |
| Escenarios nuevos / anteriores conservados | 19 / 304 |
| Parser/adquisición LM | 85/85 líneas, 150/164 ramas |
| Proveedor nativo por raíces | 22/22 líneas, 18/20 ramas |
| Regresiones deliberadas | Cuatro detectadas: hash esperado, identidad, EOF y orden |
| Compatibilidad Python | 153 pruebas correctas |

Incluye truncación en cada byte, capacidades, nombres/raíces inválidos, múltiple
bloque de lectura, digest independiente Python/CommonCrypto, sustitución con los
mismos bytes, unlink, modificación, raíz sustituida, symlink, fork y configuración
copiada. Los targets se incorporan al pipeline host mediante CMake. No se ejecutó
CI remoto, Linux ni arm64; ASan mantiene la configuración previa sin detectar fugas.

## Incidencias conservadas

La primera suite Debug pasó las 19 pruebas nuevas pero terminó con timeout en
`macos_slices_universal` y `macos_slices_replace`, ambas anteriores. CTest informa
71,02 s de pared frente a 37,855 s monotónicos del supervisor; no se atribuye una
causa confirmada. Se conserva la etapa. La repetición con las mismas 79 fuentes y
límites pasó, evitando suspensión por inactividad durante cada suite mediante
`caffeinate -i`, que termina al salir el comando.

El primer helper no compiló porque el SDK no declara `_dyld_get_shared_cache_uuid`.
Se conserva el error y se utiliza el adaptador ya validado en una nueva etapa.
La primera etapa de sonda no ejecutó PCSX2. La segunda ejecutó los cinco casos.

`llvm-cov` conserva quince avisos de hash cero para definiciones inline no emitidas
en algunos tests. Se registran nombres de helpers de fixtures y un accessor;
ningún archivo `.cpp` medido figura entre esos avisos. No se regeneraron perfiles
para esconderlos. La [evidencia](../compatibility/launch-manifest-evidence.json)
conserva métricas, hashes, límites y resultados negativos.

## Alcance y siguiente tarea

Se acredita el perfil de cabeceras de aplicación: archivos completos esperados,
objetos abiertos y cabeceras residentes, bajo confianza explícita en macOS y dyld.
No equivale a verificar payload de todas las páginas, fixups/COW, AOT, Rosetta ni
caché de plataforma; tampoco es snapshot atómico ni excluye ABA.

Sigue **PT-T5**: contrato tipado de diagnóstico/peer, selección explícita de perfil,
identidad del interlocutor, presupuesto y cancelación fuera del hilo de emulación,
negativos de versión/perfil y conservación de gates de JIT/DMA/escritores/ciclo de
vida. No se ejecutaron ISO, BIOS, VM ni adquisición; captura sigue cerrada.

La custodia queda bajo `build/f02-07-launch-manifest/` y la carpeta privada
acordada. Reserva/piso 10 GiB y máximo 512 MiB por etapa; configure 45 s, build
120 s, suite/sonda 60 s e individual 15 s. Se verifican 79 fuentes y 120 binarios
finales x86_64. No se recompiló PCSX2 ni se modificó la aplicación instalada.
