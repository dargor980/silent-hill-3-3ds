# F02.07 — Perfil de aplicación con plataforma asumida (SRC101)

Se continúa con la opción A de la [decisión de plataforma](f02-07-platform-trust-decision.md).
PT-T1 y PT-T2 implementan y prueban el núcleo de
[PT01–PT10](../../schemas/platform-inventory-v1.md). El resultado separa archivos
de aplicación verificados por sus puertos y plataforma asumida; el proveedor
PCSX2 todavía no usa este perfil. NC/CI y AP conservan sus implementaciones.

## Implementación

`PlatformInventoryGuard` depende de los verificadores existentes de nacimiento,
manifiesto, eventos del loader y SHA, y de un puerto estrecho de origen por
cabecera. La configuración inmutable incluye perfil/version, tres identidades
de evidencia, UUID esperado de caché y vínculo de la imagen principal. Un perfil
vacío/desconocido falla antes de IO; no hay selección remota ni fallback.

Las imágenes de aplicación deben corresponder a archivos del manifiesto, con
mapping de cabecera válido y offset cero. Las de caché reciben un testigo del
puerto confiable: cabecera exacta, base/tamaño y UUID. El núcleo comprueba sus
invariantes y coherencia, pero el testigo requiere un proveedor nativo que pruebe
membresía; sus campos por sí solos no la acreditan. Tipos desconocidos, datos de
ambas ramas mezclados, main ausente/incorrecto o cualquier archivo ajeno rechazan
el inventario. El perfil aplica los límites de archivos de aplicación.

La secuencia rodea dos pasadas de orígenes con manifiesto, revisión/conjunto del
loader y nacimiento. Una diferencia con la primera observación es terminal.
La salida de error queda vacía y la instancia deja de consultar puertos.
Los hashes canónicos incluyen perfil y evidencias en dominios propios.
`PlatformInventoryResult` es un tipo distinto de `InventoryResult`: no se puede
convertir implícitamente ni presentar como la antigua garantía exhaustiva.

El alcance explícito es `application_headers`, con `platform_assumed=true` y
conteos separados. No afirma identidad de páginas modificables, caché/AOT,
regiones anónimas, peer ni permiso de captura. Confiar en Rosetta como plataforma
no acredita el JIT de EE/VU/IOP ni exclusión de DMA/escritores del emulador.

## Validación ejecutada

| Comprobación local macOS x86_64 | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan, cobertura | 254 escenarios × 4 = 1016 ejecuciones correctas |
| Escenarios añadidos | 25 portables y uno con SHA-256 nativo; conserva 228 previos |
| Núcleo PT | 145/146 líneas (99,32%); 249/266 ramas (93,61%) |
| Regresiones compiladas | Cuatro detectadas |
| Compatibilidad Python | 122 pruebas correctas |

Se prueban mezcla de perfiles/evidencias, ramas contradictorias, main, límites,
archivos desconocidos, sustituciones, eventos del loader y cambios dentro de
una muestra o después de fijar la línea base. El vector independiente codifica
los campos desde la especificación; se compara byte a byte con el serializador
y se verifican ambos hashes con CommonCrypto. Los dobles de puertos no prueban
un inventario real de PCSX2.

Los controles negativos eliminan la segunda pasada, ignoran el archivo principal,
aceptan un UUID de caché distinto u omiten la evidencia de política del digest.
Todos fallan en el escenario previsto. El CMake host incorpora automáticamente
los nuevos tests al pipeline existente. No se ejecutó CI remoto, Linux, arm64
ni detección de fugas.

## Preparación del origen nativo

Una sonda aislada consulta la interfaz de introspección de dyld, resuelta
dinámicamente. Recorre el catálogo de la caché del snapshot y extrae las direcciones
exactas de `__TEXT`; después las cruza con las cabeceras realmente notificadas
por el loader. Tiene capacidad 32768, rechaza exceso/duplicados/fallos y comprueba
revisión y conjunto antes/después. Prepara dependencias de la SPI antes de tomar
la observación, sin repetir hasta obtener un resultado favorable.

| Medida | Resultado |
| --- | ---: |
| Imágenes en el catálogo de caché | 3606 |
| Imágenes cargadas en la sonda | 345 |
| Coincidencias exactas de cabecera en caché | 343 |
| Imágenes externas con vnode de cabecera | 2 |
| Cambios del ledger durante la observación | 0 |

Una de las imágenes externas es una biblioteca propia con install name
`/usr/lib/libsqlite3.dylib`. El sistema confirma que ese nombre existe en caché,
pero su cabecera cargada no coincide con ningún miembro: no se clasifica como
plataforma por el nombre. La otra imagen externa es el ejecutable de la sonda.
El primer intento, con nombre libSystem, no enlazó porque la fixture dependía de
esa misma biblioteca. Se conserva el error y la segunda etapa usa libsqlite3.

Se consultaron las [declaraciones de Apple](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/include/mach-o/dyld_introspection.h#L249)
y la [implementación de introspección](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld_introspection/dyld_introspection.cpp#L263).
El catálogo incluye imágenes no cargadas, por lo que se exige la intersección
por cabecera con el ledger. La SPI también puede materializar metadata desde
disco: esta prueba no certifica bytes residentes ni identifica la revisión
instalada de dyld. No se copian headers/implementaciones de Apple al repositorio.

## Custodia y siguiente tarea

Cuatro etapas privadas conservan snapshot de 60 archivos propios, builds, perfiles,
fixture, dos intentos de sonda y negativos. Los 92 binarios de tests/fixtures de
los cuatro builds se comprueban como x86_64. Scripts y recibos están bajo
`build/f02-07-platform-inventory/`; reserva/piso de 10 GiB, máximo 512 MiB por
etapa, configure 45 s, build 120 s y tests/sondas 60 s.

Se mantiene el snapshot original de la propuesta de confianza que SRC100 fijó
por hash. La evidencia actual registra esa transición documental y la ampliación
del CMake host; código de NC/AP y configuración productiva no se cambian.

**Sigue PT-T3:** convertir la sonda en un adaptador nativo con errores acotados,
vida de snapshot/callbacks y comprobación de PID; probar imagen externa y flags
imitados, llamadas incompletas y cambios. Validarlo dentro del candidato en
testconfig, incluyendo dyld y bibliotecas fuera de caché. Después PT-T4 compone
el manifiesto real y mide costes; PT-T5 integra diagnóstico/peer. La sonda aislada
no completa PT-T3 y no ejecutó PCSX2, VM, ISO, BIOS ni captura.
