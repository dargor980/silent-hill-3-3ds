# F02.07 — Inventario de segmentos del candidato (SRC97)

NL-T1–3 completa el lector estructural y el censo de CI-T4 bajo
[NL01–NL10](../../schemas/native-image-layout-v1.md). La última sonda enumeró
**645 imágenes y 3.020 segmentos** en una copia privada instrumentada de PCSX2,
sin errores de lectura y con revisión estable dentro de cada observación.
Esto identifica cobertura pendiente; no acredita todavía todas las páginas.

## Cambios y pruebas

El lector portable recorre todos los comandos Mach-O declarados, verifica límites,
solapamientos, segmentos y la cabecera __TEXT. Lee dos copias completas de los
metadatos en bloques de hasta 64 KiB y rechaza cambios. El puerto macOS copia
memoria del proceso propio y comprueba PID, tamaño recibido y direcciones.
Las secciones no se usan para excluir rangos; los comandos desconocidos se
recorren estructuralmente, sin afirmar validación semántica de su payload.

El censo inicial detectó 556/645 imágenes, superando el límite anterior de 256.
El ledger y la composición admiten ahora **1024 imágenes**, con rechazo al exceder
capacidad. Se separó ese presupuesto de los manifiestos: permanecen **256 archivos
por bundle y 32 por caché**, sin cambiar sus límites de tamaño.

| Validación | Resultado |
| --- | --- |
| Debug / Release / ASan+UBSan / cobertura, x86_64 macOS | 189 escenarios por configuración; 756 ejecuciones finales correctas |
| Primera etapa conservada | 188 × 4 = 752 ejecuciones correctas |
| Escenarios nuevos finales | 17 portables y 6 nativos; se conservan los 166 anteriores |
| Lector portable | 100% líneas (92/92), 96,72% ramas (118/122) |
| Puerto macOS | 100% líneas (14/14), 96,88% ramas (31/32) |
| Regresiones compiladas | Cuatro detectadas con salida 1 |
| Binarios conservados del candidato | 42 archivos / 169 segmentos; hashes antes/después idénticos |
| Compatibilidad Python | 122 pruebas correctas |
| Ruff | Sin errores; 139 archivos con formato correcto |

Los negativos omiten el último comando, aceptan solapamientos, ignoran cambios
entre copias y amplían indebidamente el número de archivos del bundle. El último
caso usa 257 nombres válidos para probar la separación real de capacidades.
La etapa inicial se mantiene; la final añade ese test explícito. CMake integra
los casos al pipeline host. No se ejecutaron CI remoto, Linux, arm64 ni detección
de fugas. El parser soporta thin Mach-O de 64 bits; no es un lector de fat files.

## Ejecución del candidato y procedencia

La primera prueba del candidato original terminó testconfig con código cero,
pero la sonda no se cargó: el log no contiene sus marcadores. Se conserva como
**ausencia de censo**, no como éxito de instrumentación. El ejecutable mantiene
Hardened Runtime y carece del entitlement de variables DYLD.

Se creó una copia privada independiente y se añadió únicamente
`com.apple.security.cs.allow-dyld-environment-variables` a sus entitlements,
conservando runtime y verificando su firma. Esta opción permite instrumentación
mediante variables del cargador según la
[documentación de Apple](https://developer.apple.com/documentation/BundleResources/Entitlements/com.apple.security.cs.allow-dyld-environment-variables).
El único archivo cuyo hash cambia frente al bundle original es el ejecutable;
la copia tiene otra identidad y no sustituye al candidato conservado.

Todas las ejecuciones usan `-datapath` privado nuevo y `-testconfig`. La ruta de
fuente comprobada retorna después de InitializeConfig, antes de iniciar el hilo
CPU. No se pidió ISO/BIOS/VM ni se modificó la aplicación instalada. Los perfiles
creados por testconfig no se promueven al perfil de admisión.

El censo exploratorio de la copia observó 556 imágenes al inicio y 645 al salir.
Las dos primeras sondas con el lector validado observaron 556/644 y la última
556/645. Son procesos distintos; cada censo verificó la revisión del cargador
antes/después. No se promete un número fijo entre procesos o fases.

## Resultado de la última sonda

| Medida | Inicio | Salida |
| --- | ---: | ---: |
| Imágenes / segmentos | 556 / 2.588 | 645 / 3.020 |
| Imágenes con flag de caché | 533 | 619 |
| Metadatos copiados por pasada | 1.967.600 B | 2.408.496 B |
| Tiempo acumulado del lector | 24,87 ms | 5,99 ms |
| Tiempo de consultas puntuales de página | 72,59 ms | 16,56 ms |
| Sonda completa, incluidas referencias y logs | 146,59 ms | 63,00 ms |
| Puntos asociados a referencias retenidas | 1.114 | 1.292 |
| Puntos que no cumplen respaldo limpio/externo/residente | 88 | 263 |
| Puntos con objeto distinto de las referencias | 1.385 | 1.464 |
| Reservas sin lectura / errores de API | 1 / 0 | 1 / 0 |

Estos tiempos corresponden a esta medición; no son un SLA. Leer metadatos en
milisegundos **no reemplaza** los 106 s de rehash completo de SRC96. Las consultas
son a la primera página de cada segmento, no a todas sus páginas. No se volvió
a hashear toda la caché ni se acreditaron los mappings AOT fuera de las imágenes.

La segunda sonda identificó la imagen externa restante como
`/usr/lib/libobjc-trampolines.dylib`. El lanzador fijó su SHA-256 sobre un descriptor
con metadatos estables; la tercera sonda contrastó sus **248.480 bytes** en dos
pasadas en cada fase y añadió su referencia. Quedan 58 referencias disponibles
(14 partes de caché, 42 binarios de la copia, sonda y biblioteca externa).
No se concede una excepción general por ruta, UUID o pertenencia al sistema.

En la última salida los 1.464 puntos sin asociación corresponden a __DATA_CONST
(602), __DATA (512), __DATA_DIRTY (349) y __CTF (1), agrupados en 14 objetos del
kernel. No se los considera fiables por estar limpios. El criterio de los 263
puntos rechazados combina residencia, externalidad y modificación; no permite
atribuirlos todos exclusivamente a COW. Estos resultados conservan el rechazo.

Las sumas de tamaños declarados incluyen regiones compartidas repetidas (por
ejemplo __LINKEDIT) y la reserva __PAGEZERO. **No representan RAM física ni bytes
únicos a recorrer**. La integración necesita unir intervalos y conservar qué
imágenes dependen de cada uno, sin esconder segmentos ni contar aliases como
archivos nuevos.

## Custodia y siguiente tarea

Se conservan dos etapas de build, dos censos exploratorios, tres sondas con el
lector y el recorrido de archivos, con scripts en `build/f02-07-native-layout/`.
Las etapas están en la carpeta privada autorizada. Las cinco pasadas completas
de caché de SRC96 no se repiten en este paso. Los presupuestos supervisados son
10 GiB libres iniciales/piso, 512 MiB por etapa, compilación hasta 120 s y tests/
sondas hasta 60 s. El original, los 200 archivos del bundle, las fuentes PCSX2
y la evidencia anterior se vuelven a comprobar.

Transiciones públicas declaradas respecto de SRC96: límite del ledger, capacidad
separada del manifiesto (cabecera e implementación) y CMake host. Las fuentes
históricas y todos sus resultados permanecen conservados.

Sigue **CI-T4: asociación de segmentos transformados y unión de rangos**. Debe
explicar los 14 objetos de datos sin referencia, cubrir colas zero-fill y AOT,
resolver los aliases y probar el rechazo de cualquier omisión. Solo después se
integrará una revalidación con coste acotado y cobertura completa. NL-T1–3 no
habilita Observation, peer, admisión, captura ni ejecución de SH3.
