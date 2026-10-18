# F02.07 — Baseline PCSX2 del observador host

Unidad: `origin/effective-mapping/instrumented-build/baseline-build`.
Contrato [BB01–BB08](../../schemas/pcsx2-baseline-v1.md),
[evidencia SRC49](../compatibility/pcsx2-baseline-evidence.json).
Fecha: 2026-10-18. Estado: **baseline compilado, tests originales aprobados y
candidato local final verificado visualmente**. Sin instrumentación.

## Preparación y supervisión

Se verificaron nuevamente el commit PCSX2
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, su checkout limpio y los
**5.228 archivos y 70 enlaces** del prefijo SRC48. CMake v19 configura y
genera en una etapa privada nueva, con Apple Clang 21, Xcode 26.6, SDK macOS
26.5 y selección explícita del toolchain Metal. Release x86_64, macOS 11,
LTO, PCH desactivados y FFmpeg enlazado; tests originales habilitados.

El inventario de `compile_commands.json` registra **811 entradas**: 530 C++,
270 C, cinco `.cc`, cinco Objective-C++ y una Objective-C. Incluye targets
excluidos del build predeterminado; no equivale a 811 archivos compilados en
la primera operación. La receta genera traducciones, recursos Qt y tres
versiones de bibliotecas Metal. El postprocesado original usa `macdeployqt`.

El [supervisor propio](../../tools/qa/supervised_process.py) separa límites,
detención del grupo y coordinación; inyecta medición y diario. Conserva
errores de señalización y verifica procesos vivos después de TERM/KILL,
incluso cuando ya terminó el padre. Un fallo de inspección deja cierre
desconocido y rechaza la ejecución. No altera el supervisor histórico de
SRC40 ni convierte los fallos Xcode de SRC48 en éxitos.

La batería incorpora **23 pruebas** sintéticas al job Python existente,
incluidos hijos huérfanos, hijos que ignoran TERM, EPERM posterior a salida,
inspección denegada, límites, plazo y conservación de muestras. Cobertura
del módulo: **100 % de líneas y ramas**. Estos casos validan la lógica y
procesos sintéticos; no reproducen internamente el servicio de Xcode. Tras
la regresión completa se sustituyó una espera fija del test por una señal de
listo del hijo y se repitieron las 23 pruebas: todas pasan con cobertura 100 %.

La política exige 20 GiB antes del build completo, dos jobs de Make, etapa
máxima de 8 GiB, suelo de 10 GiB y 45 minutos. Los 8 GiB son un presupuesto
preventivo dividido entre objetos/LTO, bundle y temporales; no una predicción
del tamaño final. No se descuenta ningún archivo disperso. Los tests
incrementales posteriores comparten el presupuesto de etapa y suelo de
10 GiB; no vuelven a iniciar un build completo.

## Compilación, bundle y pruebas originales

El build completo terminó en **338,397 segundos**; sus 326 muestras registran
un máximo de **328,26 MiB** en la etapa y mínimo de **20,19 GiB libres**.
La compilación de tests tardó 34,038 segundos. Los tres metallib, recursos y
traducciones se generaron. Las 811 órdenes inventariadas contienen x86_64,
LTO y mínimo macOS 11. El checkout y tests originales no requirieron parches.

El empaquetado original devolvió cero, pero escribió errores de firma para
MoltenVK y el bundle. Además, Shaderc conservaba un ID absoluto del prefijo.
Se preservó ese bundle sin promoverlo y se creó una copia con ID relativo
y firma ad hoc. La revisión posterior de LC_RPATH encontró cinco rutas
residuales en JPEG/WebP; se conserva también ese primer candidato.

El **candidato v2** normaliza esas cinco rutas a `@loader_path`, conserva los
entitlements originales y usa firma ad hoc con hardened runtime. La
verificación `codesign --verify --deep --strict` pasa. Son **200 archivos,
112.344.866 bytes y 42 Mach-O x86_64**, con mínimos de sistema no superiores
a 11.0, sin dependencias ni RPATH absolutos del prefijo/Homebrew. Firma local;
no hay Developer ID ni notarización. Ejecutable de **17.708.592 bytes**:

`9fc99e1bf529cfb5afaf3d259a14b502942cc07e2ced8a82231a8a72e3df58ee`

**2/2 programas CTest aprobados: 31 tests common y 82 core**, 113 en total,
sin fallos ni omisiones. El perfil original para Apple Silicon limita los
tests multi-ISA a SSE4; no se afirma probar AVX/AVX2. Los tests son x86_64 y
se ejecutan sobre host ARM64. El log completo original permanece privado;
el JUnit CTest trunca su texto a 1.024 bytes, no se usa como única evidencia
del recuento. No se ejecutan GSRunner, sanitizers ni suites de GPU completas.

## Arranque y observación

Ambos candidatos pasan `-testconfig` y arranque/cierre UI con perfil propio.
El primer comprobador asumía `inis` directamente bajo `-datapath`; la fuente
y log muestran el subdirectorio `PCSX2/inis`. Se corrigió únicamente esa
comprobación posterior; el comando original ya había salido con cero.

En el candidato final se observó el **depurador en español**, restauración
del panel de breakpoints y respuesta al seleccionar Memoria. En el primero
también se observó la ventana principal v2.8.2 con lista vacía. Los controles
de ejecución deshabilitados y desensamblado inválido corresponden a no tener
VM cargada; no se interpretan como lectura real del juego. Cierre mediante
Cmd-Q: código cero y grupo sin procesos restantes en ambos candidatos.
La consulta UI posterior al primer cierre dio timeout al desaparecer la
ventana; la salida del proceso y el supervisor confirmaron el cierre.

DYLD_PRINT_LIBRARIES no produjo trazas en el candidato con hardened runtime;
no se amplían sus permisos para obtenerlas. Una inspección `lsof` del proceso
final identificó **29 archivos del bundle: 26 Mach-O, dos fuentes y una
traducción**, sin mapeos del prefijo de dependencias ni Homebrew. Incluye
Qt, KDDockWidgets, FFmpeg y el plugin Cocoa. No cubre todos los plugins ni
las bibliotecas cargadas solamente al iniciar una VM/GPU. El primer sondeo
de procesos ocurrió entre la salida de `testconfig` y el arranque UI y no
encontró proceso; se repitió con la ventana abierta e identidad comprobada.

Se verifican nuevamente los **5.228 archivos y 70 enlaces** del prefijo,
checkout limpio y los 200 hashes del candidato después de cerrar. Se
conservan símbolos, incluidos `eeMem` y `vtlbdata`, y 33 archivos de licencias
del checkout por hash. Presencia de símbolos no verifica todavía el ABI ni
la captura efectiva. Etapa final: **686,44 MiB**; espacio libre al cierre de
esa comprobación: **20,68 GiB**, sujeto a nueva medición antes de otro build.

## Verificación del repositorio

**1.920 pruebas Python aprobadas**, cobertura total combinada de líneas y
ramas **98,46 %**. El gate separado de líneas/ramas, Ruff y formato pasan.
La comprobación final del repositorio pasa sin errores; `git diff --check`
también pasa. Se contrastan los hashes de artefactos/evidencia y **1.102
enlaces Markdown locales**, sin rutas privadas en los diez archivos públicos
revisados. La CI remota no se ejecutó. Las pruebas añadidas no necesitan código, BIOS ni datos de juego
privados.

## Límites y continuidad

El objetivo de esta unidad es disponer de un emulador host de referencia
compilado desde las fuentes fijadas. La instrumentación, captura del mapa
efectivo, relaciones semánticas y corpus de dos salas siguen pendientes.
F02.07 y Q05/G02 permanecen abiertos; esta unidad no acredita ejecución
de Silent Hill 3 en Nintendo 3DS ni ensayos físicos.

La siguiente unidad es **`instrumented-build/observer-contract-and-patch`**:

1. Contrastar en la revisión fijada el hilo CPU, estado de pausa, base de RAM,
   entradas vmap y guardado de estados; documentar el punto de captura y
   las garantías reales antes de elegir el hook.
2. Extender MP con requisitos EARS de adquisición interna: petición acotada,
   identidad/sesión/secuencia, pausa estable, lectura sin modificar emulación,
   errores y asociación verificable con estado y PINE. Resolver explícitamente
   cómo cambia el mecanismo externo previsto en MP02.
3. Diseñar lector, coordinador y salida privada con responsabilidades separadas
   e interfaces inyectables. Preparar casos sintéticos de rangos, handlers,
   alias, overflow, cambio de sesión/pausa y fallo de publicación.
4. Preparar copia de fuentes y parche mínimo identificado, con observador
   optativo y sin alterar tests originales. Conservar este baseline exacto.
5. Dejar definida la unidad posterior de build instrumentado: revalidar IB02,
   repetir tests/paquete/arranque, verificar ABI interno y luego capturar una
   sesión nueva en entrada, antes/después del par y retorno según MP08.
   Ninguna evidencia sintética sustituye esa sesión ni cierra las dos salas.
