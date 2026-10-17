# Normas de ingeniería y batería de pruebas

La instrucción del usuario del 16-10-2026 hace SOLID obligatorio para toda la solución. Se aplica a C++, herramientas Python, integración y diseño de pruebas. Se añaden RNF11.05-RNF11.09 y RNF07.06-RNF07.09 a la especificación.

## SOLID verificable

| Principio | Regla aplicada | Comprobación |
|---|---|---|
| SRP | Dominio decide; aplicación coordina; adaptador realiza I/O; CLI compone. Un conversor no identifica edición, decodifica y publica en una sola clase | Revisar responsabilidad y motivo de cambio por módulo; probar reglas sin I/O |
| OCP | Añadir una implementación de puerto por plataforma/formato; modificar el dominio solo cuando cambian sus reglas | Núcleo sin ramas `__3DS__`; nuevo adaptador pasa contratos existentes |
| LSP | Mismos resultados, errores, propiedad y semántica al sustituir adaptadores | Misma suite con inspector en memoria/filesystem y log de prueba/circular; contratos adicionales al introducir nuevos puertos |
| ISP | Interfaces por consumidor; no anticipar métodos que obliguen a devolver éxito ficticio | Tres puertos de ciclo de vida y dos de archivos por consumidor; no se implementa un IRenderer completo para un rectángulo |
| DIP | El núcleo define lo que necesita; la composición provee implementaciones por referencia/constructor | Targets separados en CMake, includes restringidos por `tools.qa.check_repository`, doubles host |

Las comprobaciones automáticas detectan dependencias prohibidas; no demuestran SOLID por sí solas. La revisión humana evalúa responsabilidades, contratos y coste. Se prefieren valores, composición y funciones puras antes que jerarquías de herencia innecesarias. Ninguna abstracción se invoca por vértice o muestra solo para cumplir una forma.

## Batería por nivel

| Nivel | Suite actual / extensión prevista | Regla de aceptación |
|---|---|---|
| Unitarias C++ | Tabla de 25 transiciones de ciclo de vida; suspensión repetida; log vacío/saturado/índice fuera de rango | Sin dependencia de SDK ni datos originales; checks activos en Release |
| Contratos C++ | La misma aplicación con log de conteo y log circular | Sustitución sin modificar el consumidor; no renderizar suspendido/detenido |
| Integración C++ | Entrada, estado, vista y log; ejecutable host sintético | Estado final y ausencia de efectos después de salida |
| Contratos del adaptador 3DS en host | Treinta y tres escenarios sobre la composición real, con SDK/Tone sustituidos solo en el target de pruebas | Errores de inicio, geometría/entrada, prioridad START, salida APT, orden de liberación y GPU pendiente; [F01.02](execution/f01-02-diagnostic.md). No acredita GPU/NDSP físicos |
| Contratos NDSP en host | Cinco escenarios sobre tone.cpp real y SDK controlado | PCM, mute inicial, Result/errores, contadores y clear → exit → free; [F01.04](execution/f01-04-audio.md). No acredita escucha ni ejecución DSP |
| Unitarias Python | Perfil, tipos, tamaños, hashes, duplicados, rutas | Rechazo tipado antes de extracción; ninguna escritura sobre entradas |
| Integración Python | Archivos temporales, CLI, falta/alteración, enlaces simbólicos y fallo de lectura | Error diagnosticado y sin rutas privadas en salida |
| Arquitectura/custodia/specs | Includes, índice Git, ubicaciones privadas, enlaces/entradas especiales, referencias EARS y matriz | Pipeline falla si un contrato verificable se rompe; reglas en `tools/qa/custody.py`, [evidencia F00.05](execution/f00-05-profile-custody.md) |
| Opciones y archivos C++ | Codec con bytes esperados, truncamientos y corrupción; selección/recuperación; stdio real y fallos inyectados | Sin éxito ante I/O fallida, sin cambio de memoria antes de verificar y slot anterior conservado; [contrato](../schemas/diagnostic-options-v1.md) |
| Identidad de depuración | Manifiesto ELF/3DSX, ID esperado, hashes/tamaños y archivos inválidos | Rechazar símbolos mezclados antes de depurar; [F01.05](execution/f01-05-debugging.md), separado de breakpoint remoto |
| Gates de automatización | 68 casos de archivos completos/alterados, fallos de herramientas y presets vacío/fallo/éxito con CTest real | Sin recibo ante fallo; ocho salidas obligatorias; cero tests es error. [F01.08](execution/f01-08-builds.md) |
| Inventario de origen | 62 casos nuevos de clasificación conservadora, perfil completo, IDs/offsets, lector sustituible y errores de lectura/escritura | Dos catálogos ISO idénticos; extensión sola no confirma tipo; ninguna extracción ni éxito ante cambio de imagen. [F02.01](execution/f02-01-inventory.md) |
| Sondeo MFA | 73 casos nuevos: bloques/cadenas/rangos, límites, colisiones, B8 desconocido, lectores sustituibles e I/O; payload virtual de 1 GiB sin leerlo | 430 pruebas totales, metadata repetible; parser D8 con 100 % de líneas/ramas. No acredita extracción. [F02.02](execution/f02-02-mfa-candidate.md) |
| Variantes MFA | 63 casos nuevos B8/D8, selección incorrecta/ambigua, contexto de error y codec/round-trip sin aceptación automática | 493 pruebas totales; parser y diagnóstico con 100 % de líneas/ramas. Dos sondeos por layout idénticos; XBG0 pendiente. [F02.03](execution/f02-03-container-variants.md) |
| Recursos y métricas | Adapter SDK real con errores/ceros/valores fuera de rango; ring, calentamiento, p95, rotación y reinicio | UNKNOWN distinto de cero, sin suma de pools ni atribución GPU; [F01.06](execution/f01-06-resources.md) |
| Ciclo de vida y reservados | Hooks en lote, duplicados/salida, entrada bloqueada, held/down y regreso de HOME | Sin entrada/vista suspendida, pausa/mute conservados y espera de liberación; [F01.07](execution/f01-07-lifecycle.md) |
| Sanitizadores host | ASan + UBSan en build separado | Cero hallazgos; UBSan detiene el job |
| Catálogo interno MFA | 89 casos nuevos: selección/identidad, descriptores completos, IDs/offsets/hashes, rangos vacíos, lecturas acotadas y fallos sin catálogo aceptado | 582 pruebas totales; dos catálogos reales idénticos. XBG0 y semántica pendientes. [F02.04](execution/f02-04-asset-catalog.md) |
| Extracción MFA | 104 casos nuevos: copias independientes, identidad/catálogo, streaming, destino, corrupción/relectura, ENOSPC y recibos | 686 pruebas totales; dos copias reales de 1740 recursos verificadas contra el catálogo. [F02.05](execution/f02-05-repeatable-extraction.md) |
| Robustez de extracción | 142 casos nuevos: mutaciones con oráculo exacto, límites, I/O, propiedad de descriptores y cuatro SIGKILL sincronizados | 828 pruebas totales; regresiones previas al arreglo conservadas. [F02.06](execution/f02-06-extraction-hardening.md) |
| Inventario de candidatos | 91 casos propios: evidencia, límites, cambios/enlaces, I/O y publicación de metadatos | 919 pruebas totales; 1740 recursos verificados por copia y dos informes idénticos. [F02.07 parcial](execution/f02-07-slice-corpus.md) |
| Cobertura | Python y bibliotecas C++ portables, límites independientes para líneas y ramas | ≥80 % por métrica; no sustituye casos de borde ni incluye cobertura ficticia de hardware |
| Build 3DS | SDK oficial fijado por digest; ELF, SMDH, 3DSX, hashes y paquetes | Compila sin errores ni warnings del proyecto; no acredita ejecución |
| Chequeo del SDK | Ejemplo oficial en dos directorios nuevos, probe C++17 ARM y guardas de entorno/salida | 3DSX/SMDH idénticos, sin caché copiada y fallo antes de crear evidencia si falta SDK; [F01.01](execution/f01-01-toolchain.md) |
| Hardware manual | Imagen sintética, A/START, tono, pausa, tapa/HOME, retorno y errores | Pendiente de New Nintendo 2DS XL real; se registra build y launcher |
| Diferenciales y campaña | No disponibles todavía | Requieren edición identificada, referencias y gates posteriores |

Los 47 casos CTest se ejecutan en los presets host existentes; `sdk-double` localiza 39 contratos de adaptador/composición y `audio` los cinco casos sobre tone.cpp real. La cobertura portable conserva su alcance y no absorbe ficheros 3DS ni dobles para aparentar cobertura de hardware.

Cada error corregido añade un caso si afecta comportamiento. Lectores y guardados futuros requieren archivos truncados, overflow, referencias inválidas y fallos de escritura por etapa. Fuzzing acotado de lectores se añade cuando exista un formato congelado; no se fuzzearán offsets inventados del original.

## Pipelines

`.github/workflows/ci.yml` define `quality`, `host`, `cpp-coverage` y `nintendo-3ds`. Host cubre Linux/macOS y Release/sanitizadores. El job 3DS depende de calidad, host y cobertura. Los workflows usan acciones fijadas por commit, permisos de lectura y fixtures sintéticos; no hay publicación automática ni credenciales del juego. Los artefactos de CI son diagnósticos de desarrollo.

Las dependencias Python están fijadas con hashes en `requirements-dev.lock`; las versiones directas se mantienen en `requirements-dev.in`. El SDK se fija en `toolchains/devkitpro-image.txt`. Los runners host son imágenes mantenidas por GitHub: su entorno no es hermético; se registra compilador y versión de CMake. Una actualización de pins exige suite completa y actualización del inventario.

GitHub Actions se ejecutará cuando el workflow esté en GitHub. La validación local del mismo comando no demuestra un run remoto. No se modifica la protección de ramas como parte de esta entrega; al configurar el repositorio, los cuatro jobs deben ser controles requeridos para integrar.

El job `nintendo-3ds` ejecuta `check_3ds_toolchain.sh` antes de `build_3ds.sh`; el fallo del primero detiene la secuencia. Conserva logs/hashes incluso si falla, con rutas explícitas que excluyen los fuentes y binarios del ejemplo oficial. Los cinco casos de entorno ausente/incompleto y destino existente se incluyen en pytest del job `quality`. La revisión LIC07 sigue siendo necesaria antes de compartir el diagnóstico propio.

Fuentes técnicas consultadas: [CMake/ejemplos de devkitPro](https://github.com/devkitPro/3ds-examples), [imagen oficial devkitPro](https://github.com/devkitPro/docker), [sintaxis oficial de GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). Los contratos concretos de CMake/libctru se comprobaron además dentro de la imagen fijada.

F01.05 añade build-id y manifiesto de depuración al artefacto 3DS; el script los genera/verifica después del enlace y conserva la evidencia existente rechazando sobrescritura. Los tests Python del verificador se ejecutan en quality. El runtime C++ no cambia; Azahar y GDB se prueban localmente, sin introducir una prueba de escucha ficticia en Actions.

F01.06 añade los targets de recursos y ventana al mismo pipeline CMake/CTest, con etiquetas unit y sdk-double. TimingWindow entra en cobertura portable; ResourceProbe/composición se prueban con dobles y compilan contra SDK ARM. No se cambia el alcance de cobertura para simular pruebas físicas.

F01.07 agrega diez escenarios al target de composición existente y refuerza las pruebas de aplicación/dominio. La CI ejecuta los 47 casos sin jobs nuevos; `ctest --preset host-debug -R "lifecycle|diagnostic_app"` permite localizar las regresiones. El test double avanza botones por bombeo APT y admite varios hooks en una misma llamada, sin representar hardware real.

F01.08 endurece los cuatro presets: error ante cero tests y timeout de 120 segundos por caso, salvo límites específicos menores. El job quality requiere CMake/CTest en PATH para probar esta política. Los jobs conservan logs mediante tee con pipefail y comprueban reportes no vacíos. El script ARM termina verificando el conjunto completo y creando `artifact-check.json`; el upload incluye el recibo. La [hoja física](compatibility/diagnostic-soak.md) exige treinta minutos activos con checkpoints, sin convertir el ring de métricas en una traza continua ni cerrar G01 automáticamente.

F02.01 amplía las pruebas descubiertas por pytest y la cobertura de tools sin modificar el workflow ni sus artefactos. El catálogo real se ejecuta localmente y guarda solo metadatos en reports/local ignorado; CI utiliza ISOs propias temporales. No se añaden dependencias Python ni cambios al runtime C++/ARM. La batería local llega a 357 casos; clasificador y política de inventario tienen 100 % de líneas/ramas, sin convertir esa cobertura en soporte de formatos internos.

F02.02 incorpora el sondeo D8 y lectura exacta por rangos al mismo job quality. La suite completa pasa 430 casos, con 97,01 % de líneas y 95,66 % de ramas; los contrastes de la ISO privada son locales y separados de CI. No hay dependencias nuevas, ejecución del candidato Windows ni cambios C++/ARM. Desconocido de formato y fallo de I/O tienen salidas distintas, comprobadas por pruebas.

F02.03 reutiliza el parser de bloques para B8/D8 con selección fija; añade diagnóstico puro de nombres y 63 casos al mismo job quality. Cobertura total: 97,12 % de líneas y 95,77 % de ramas. Se comprueban las variantes con datos propios; las cuatro inspecciones reales y los metadatos originales permanecen locales/ignorados. No cambia CI, dependencias, SDK ni runtime; la validación remota y física conserva sus pendientes.

F02.04 añade catálogo interno y hashing exacto de rangos al mismo job quality, sin dependencias ni cambios al workflow. Las 582 pruebas pasan con 97,50 % de líneas y 96,02 % de ramas; selección, parser MFA y hashing tienen 100 % en ambas. Las dos inspecciones europeas solo producen metadatos privados. El primer control de custodia coincidió con la creación de un reporte y falló; se conserva ese intento y se repitió toda la suite sobre el árbol estable, sin cambiar reglas. Ejecutar las comprobaciones de custodia después de terminar las escrituras privadas. CI remota y hardware siguen pendientes.

F02.05 incorpora 104 regresiones al job quality existente, con raíces temporales y datos propios; 686 pruebas totales, 97,91 % de líneas y 96,51 % de ramas. Transferencia y adaptador de salida tienen 100 % en ambas. APIs POSIX verificadas localmente en macOS; ejecución remota Linux/macOS pendiente. No cambian dependencias ni workflow, SDK o runtime. Las extracciones reales quedan en raíz externa y sus metadatos de ubicación en reports/local ignorado; no entran en artefactos CI.

F02.06 añade 142 casos al mismo job quality: 828 aprobados, 97,95 % de líneas y 96,55 % de ramas. Los helpers bajo tests/python se incluyen en Ruff. Las pruebas de proceso usan checkpoints explícitos, límites de 15/5 segundos y terminación/recolección en finally; SIGKILL sintético no acredita durabilidad física. No cambia workflow, dependencias ni runtime. Los recibos reales F02.05 conservan su identidad histórica; no se repitió extracción porque parser/rangos/transferencia no cambiaron.

F02.07 añade 91 pruebas al job quality existente: 919 aprobadas, 98,15 % de líneas y 96,68 % de ramas. Lector, coordinador y primitivas POSIX compartidas alcanzaron 100 % de líneas/ramas en la suite. La integración detectó staging con sufijo no permitido y lo corrigió a `.pending.json`, conservando el rechazo y la política. Los originales se releen localmente; CI conserva solo fixtures propios. La compilación C++/ARM no cambia y no se volvió a ejecutar en esta instancia; CI remota y consola siguen pendientes.

F02.07/formato-camera añade 66 casos al mismo job quality: 985 aprobados, 98,20 % de líneas y 96,72 % de ramas globales. Sondeo puro con 100 % de líneas/ramas; incluye falsos positivos que no se promueven a tipo identificado. Dos ejecuciones locales verificaron 285 payloads por copia y generaron informes iguales; no se releen los otros 1455 payloads ni la ISO en este sondeo. CI remota, compilación ARM nueva y hardware no se atribuyen a estas pruebas. [Evidencia](execution/f02-07-camera-probe.md).

F02.07/camera-consumer-eu añade 116 casos al job quality: **1101 aprobados**, **98,31 % de líneas** y **96,92 % de ramas**. ELF y patrón tienen 100 % de ambas métricas; pruebas propias de rangos, BSS, solapes, delay slots, frontera de bloques, falsos positivos y errores tardíos. Dos sondeos de la ISO generan metadatos idénticos. Se verifican localmente Ruff, formato, cobertura independiente y custodia; CI remota y compilaciones C++/ARM no se repiten porque no cambian runtime ni build. [Evidencia](execution/f02-07-camera-consumer.md).

F02.07/camera-pointer-origin-eu añade 139 casos propios al mismo job quality: **1240 aprobados**, cobertura global de **98,40 % de líneas** y **97,12 % de ramas**. Se prueban delay slots/likely, destinos, convergencia, llamadas, efectos desconocidos, límites y publicación tras cierre estable. Dos sondeos reales producen informes idénticos; CI remota/hardware no ejecutados y compilación C++/ARM sin cambios. [Evidencia](execution/f02-07-camera-pointer.md).

F02.07/camera-caller-boundary-eu añade **67 casos propios, 1307 aprobados**; cobertura de **98,47 % de líneas y 97,23 % de ramas**. Los módulos de control/fronteras alcanzan 100 % de ambas métricas. Se prueban slots, retorno/enlace, ramas, guardado/restauración conservador, indirectos/recursión, límites, memoria/ISO y publicación estable. Se reutiliza quality sin modificar jobs de compilación. CI remota/hardware no ejecutados. [Evidencia](execution/f02-07-camera-boundary.md).

F02.07/camera-runtime-observation-plan-eu añade **128 casos propios, 1435 aprobados**; cobertura independiente de **98,60 % de líneas y 97,38 % de ramas**. Plan, contrato y lector privado tienen 100 % de ambas métricas. Se prueban cadena ISO sintética/captura/recibo, sesiones, fases, registros, hashes, límites y cambios/fallos tardíos del filesystem. El job quality existente descubre estos casos sin originales; no requiere PCSX2 ni BIOS. La primera corrida coincidió con generación de reportes y falló el inventario de custodia; tras estabilizar archivos pasó sin cambiar controles. [Evidencia y límites](execution/f02-07-camera-observation.md). CI remota, hardware y compilación C++/ARM no ejecutados en esta instancia.
