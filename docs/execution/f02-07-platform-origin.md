# F02.07 — Origen nativo de imágenes de plataforma (SRC102)

Implementación de [PO01–PO07](../../schemas/native-platform-origin-v1.md),
detalle de PT-T3. `MacOSPlatformOrigins` compone eventos, mapping y llamadas
inyectables a dyld. Clasifica cada cabecera cargada como miembro exacto de la
caché o archivo externo. El núcleo PT y las garantías NC/CI/AP no se modifican.
PO-T1–2 completas; PT-T3/PO-T3 siguen parciales por el mapping universal descrito
abajo. No se habilita el perfil en el proveedor productivo.

## Implementación y límites

El adaptador resuelve la SPI dinámicamente, valida funciones/PID y prepara una
sola sesión. Libera snapshots y proceso en orden inverso, copia valores de cada
callback y conserva un catálogo ordenado de hasta 32768 cabeceras, con máximo
256 segmentos por imagen. `__TEXT` debe ser único, legible, no vacío y estar
contenido en el rango coherente de caché. UUID vacío, duplicados, errores o exceso
de capacidad invalidan la instancia.

Cada consulta exige pertenencia al ledger cargado y compara revisión/conjunto/PID
antes y después. Solo la intersección exacta con el catálogo produce plataforma.
Una imagen externa debe tener mapping regular de cabecera con offset cero;
todavía necesitará el manifiesto PT-T4. Carga/descarga, dirección desconocida o
fallo de mapping invalidan toda la sesión. La salida queda vacía y futuras
consultas no vuelven a usar puertos. No hay selección por ruta, nombre o flag.

El catálogo se considera inmutable bajo la confianza explícita en dyld. No se
certifican sus bytes, los de Rosetta/AOT ni páginas de datos. La API enumeradora
no expone estado final: no se garantiza detectar una API que termine en silencio
sin entregar todos los miembros; una omisión aún necesitaría mapping y manifiesto
de aplicación. Las comparaciones no son atómicas ni excluyen ABA. Las llamadas
del sistema se limitan externamente por el supervisor, sin cancelación interna.

## Fallos encontrados y conservados

1. La primera compilación rechazó la indentación de un bucle doble del test con
   `-Werror`. Se corrigió el test y se conservó el snapshot y log originales.
2. La fixture con install name `/usr/lib/libsqlite3.dylib` y flag
   `MH_DYLIB_IN_CACHE` falsificado antes de crear el snapshot provocó un aborto
   `Dyld.AtlasError.missingPlist` en la SPI instalada. Se añadió preflight: copia
   acotada de cabeceras mediante el kernel y rechazo del flag fuera del rango que
   informa dyld, antes de crear proceso y cada snapshot. Ese intervalo solo sirve
   para rechazar una contradicción; no acredita membresía. La prueba conserva
   tanto el nombre imitado como el flag alterado antes de construir el adaptador.
   Una sesión ya preparada sigue clasificando esa fixture como externa. La
   comprobación no garantiza protección frente a cualquier corrupción concurrente.
3. ASan rechazó su propia biblioteca universal: `proc_pidinfo` devolvió 1272/1272
   bytes, inicio exacto y offset 16384. Dos sondas privadas identificaron el objeto
   y la causa. El test final comprueba que es la imagen que contiene `__asan_init`,
   que el kernel informa offset no cero y que la sesión queda cerrada. No se
   relajó PT03 ni el proveedor para aceptar ese archivo. Los builds sin ASan
   exigen clasificación completa; el build ASan prueba este rechazo previsto.

## Validación

La suite incorpora pruebas de todas las funciones ausentes, errores parciales
de snapshot/cache, limpieza, PID/fork, revisión/conjunto, mapping incompleto,
catálogo vacío/duplicado/excesivo, segmento inválido y cabecera cargada dentro
del rango pero ausente del catálogo. Conserva los 254 escenarios previos.

| Validación local macOS x86_64 | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan, cobertura | 274 escenarios × 4 = 1096 ejecuciones correctas |
| Escenarios nuevos | 20 |
| Adaptador | 141/141 líneas (100%); 170/188 ramas (90,43%) |
| Regresiones deliberadas | Cuatro detectadas |
| Compatibilidad Python | 122 pruebas correctas |

Los cuatro controles negativos omiten la pertenencia al ledger, su revisión,
la segunda frontera o la comprobación de duplicados. El target host se incorpora
al pipeline existente. La ejecución local usa macOS x86_64; no acredita CI remoto,
Linux, arm64 ni detección de fugas.

## Diagnóstico en PCSX2 y siguiente tarea

Dos copias nuevas de 200 archivos del candidato diagnóstico se ejecutaron con
testconfig y perfiles privados nuevos. Se verifican antes/después contra el
manifiesto previo; no se recompiló PCSX2 ni se cargaron ISO, BIOS o VM. Ambas
clasifican 557 cabeceras al arrancar: 534 de plataforma y 23 externas, catálogo
de 3606, dos pasadas y ledger estable. Preparación 189–207 ms; observación total
215–224 ms con logging. Son medidas de dos sondas, no un presupuesto de producción.

dyld no figura en el ledger y su consulta estricta de mapping devuelve false;
queda expresamente bajo la plataforma asumida. No se inserta en el conjunto como
aplicación verificada ni se certifican sus páginas.

Ambas sondas rechazan la salida en el índice 642 por mapping. La segunda identifica
`/usr/lib/libobjc-trampolines.dylib`, archivo de 248480 bytes, cabecera exacta,
región de 53248 bytes y offset 16384. El primer launcher descartó el resultado al
faltar la observación final; se conserva. La segunda registra ese rechazo previsto,
sin convertir la salida parcial en inventario válido.

La inspección acotada del archivo real confirma FAT32, tres slices con cabeceras
thin coherentes: x86_64/subtipo 3 (offset 16384), x86_64/subtipo 8 (98304) y
arm64/subtipo 2147483650 (180224). Esto explica el contraejemplo; aún no implementa
una vinculación segura entre archivo/slice/mapping ni selecciona por arquitectura.

**Sigue PO-T3b:** contrato y parser acotado de Mach-O universal, relación explícita
del offset observado con el slice esperado, negativos y nueva validación completa
del candidato. PT v1 conserva offset cero mientras tanto. PT-T4 (manifiesto/costes)
y PT-T5 (diagnóstico/peer) siguen posteriores; captura permanece cerrada.

## Referencias y custodia

Se consultan [introspección de dyld](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/include/mach-o/dyld_introspection.h#L249)
y la [implementación del rango de caché](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld/libdyldGlue.cpp#L645).
Las declaraciones opacas y adaptadores son propios; no se copian implementaciones
de Apple. No se infiere que el commit consultado identifique la versión instalada.

Etapas y scripts bajo `build/f02-07-platform-origin/`, con snapshots y binarios
en la carpeta privada autorizada. Reserva/piso 10 GiB, máximo 512 MiB por etapa;
configure 45 s, build 120 s, pruebas/sondas 60 s y timeout individual 15 s. Los
primeros tres builds y las dos sondas de diagnóstico se conservan. Las pruebas
no acreditan JIT del emulador, DMA, ciclo de vida, peer ni permiso de captura.
El snapshot final conserva 63 fuentes propias y 100 binarios de tests/fixtures
comprobados como x86_64. La evidencia registra por hash la transición del CMake
y la anotación de estado del contrato PT anterior, sin alterar su semántica.
