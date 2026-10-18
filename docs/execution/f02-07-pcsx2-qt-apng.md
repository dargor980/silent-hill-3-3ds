# F02.07 — QtApng instalado y validado con correcciones de compatibilidad

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-apng`.
Contrato [QAP01–QAP08](../../schemas/pcsx2-qt-apng-v1.md),
[fixtures propios](../../tests/fixtures/pcsx2-qt-apng/README.md) y
[evidencia SRC45](../compatibility/pcsx2-qt-apng-evidence.json).

QtApng **1.3.0**, con el parche de receta y un parche local de compatibilidad,
quedó instalado como plugin x86_64/macOS 11.0. Pasaron **9/9 casos antes y
9/9 después de instalar**, incluidos ocho casos propios y el programa original
completo. Los tests originales no se modificaron. La configuración PCSX2 v15
sigue requiriendo KDDockWidgets; la próxima unidad es **KDDockWidgets 2.4.1**.

## Procedencia, dependencias y capacidad

`QtApng-1.3.0.tar.gz` coincide con SHA-256
`f1d3be3489f758efe1a8f12118a212febbe611aa670af32e0159fa3c1feab2a6`.
Contiene 3.456.119 bytes comprimidos, 9.768.109 extraídos y **794 archivos**.
Se validaron las rutas y se conservan todos los originales privados intactos,
incluidos nueve archivos de licencias/avisos. El LICENSE principal declara
BSD-3-Clause. Las copias incorporadas de PNG y ZLIB conservan sus avisos,
pero no se compilan. Se alcanzan **22/25 archivos de receta verificados**.

El parche `common/qtapng-cmake.patch` de la receta fija tiene SHA-256
`8570862a54fb3f85a7ead44582185a739c4331d5aee2e6a95cc7bb2f0ea753b9`.
Se aplicó sin fuzz en una copia y cambió cuatro archivos CMake. El archivo
FindZLib queda vacío al aplicar este parche con la herramienta local.
El parche adicional final cambia tres archivos C++ y tiene SHA-256
`2b11a3a91f7d131f8759e213a224b9e9cd957cbe699565bfc82f0c818cdd51fc`.
Diffs, scripts y hashes anteriores/posteriores se conservan privados.

La configuración usa Release, Qt Core/Gui **6.11.1**, cuatro unidades C++,
un enlace de plugin y libpng/APNG **1.6.58** privada, verificada contra SRC31.
ZLIB se resuelve desde `usr/lib/libz.tbd` del SDK 26.5. No hay includes ni
bibliotecas objetivo Homebrew. APNG_QT6 está ON; APNG_TESTS/APNG_EXAMPLES
quedan OFF como en la receta, y el programa original se compila por separado.
El archivo upstream conserva `project(VERSION 0.1.0)`; la versión 1.3.0
identifica el archivo/tag fijado, no un cambio de esa declaración.

QAP03 fija 14 GiB libres al iniciar, piso de 12 GiB, máximo de 512 MiB de
build y dos jobs. Se verificó por hash el supervisor SRC40; sus siete ensayos
de control son evidencia previa y no se cuentan como nuevas ejecuciones.

| Build conservado | Duración | Muestras | Máximo asignado | Mínimo libre |
|---|---:|---:|---:|---:|
| v1, receta | 6,06 s | 9 | 2,09 MiB | 15,56 GiB |
| v2, primer ajuste | 5,07 s | 8 | 2,11 MiB | 15,64 GiB |
| v3, final | 4,06 s | 7 | 2,14 MiB | 15,58 GiB |

Los tres builds finalizaron con salida 0, sin parada preventiva. El intervalo
máximo observado del final fue 1,016 s y su máximo lógico 1.926.150 bytes.
Los temporales están dentro del build medido. El muestreo no es una cuota
ni garantiza capturar picos; consumidores e instalación son operaciones
posteriores. Este presupuesto no sustituye el gate IB general de 20 GiB.

## Fallos detectados y corregidos

Los APNG propios se generan con Python, chunks/CRC/zlib y cuadros RGBA
esperados explícitos, sin depender de Qt/libpng. La semántica de reproducción,
retardos, imagen inicial y composición se contrastó con
[PNG/APNG del W3C](https://www.w3.org/TR/2025/REC-png-3-20250624/#11acTL),
y las API con el código Qt 6.11.1 local y
[QMovie](https://doc.qt.io/qt-6/qmovie.html#loopCount).

| Hallazgo | Corrección local |
|---|---|
| Una pasada APNG informaba un bucle adicional; QMovie emitía cuatro cuadros en vez de dos | Convertir reproducciones totales a repeticiones adicionales: `plays - 1`; cero mantiene repetición indefinida |
| Denominador de retardo cero producía −2.147.483.648 ms | Interpretar el denominador cero como 100 |
| Imagen inicial oculta se contaba como cuadro animado | Excluirla del recuento entregado por la libpng/APNG utilizada; verificar también los píxeles de ambos cuadros |
| El test original esperaba UnsupportedFormatError para contenido que no era PNG, pero recibía UnknownError | Rechazar firmas no válidas durante selección del plugin; exigir firma completa para lectura |

El primer ajuste de firma bloqueó el dispositivo vacío usado por
`QMovie::supportedFormats()`. Se preservó ese fallo y se permitió el sondeo
de capacidades, manteniendo rechazo de lectura real de archivos vacíos y
firmas incompletas. Los casos propios y el programa original pasan juntos.

El test propio de aislamiento también necesitó corregirse: Qt podía leer
el primer cuadro con su lector PNG estático cuando faltaba el plugin.
Se desactivó autodetección en los lectores explícitos. El caso de aislamiento
ahora exige rechazo y una traza sin QtApng. Esta corrección no cambia los
oráculos de APNG válidos.

Se conservan íntegramente `build-v1-fixture` (**3/9 aprobados**) y
`build-v2-fixture` (**1/9 aprobado**), sus logs/JUnit, fuentes y binarios.
Los dos fallos históricos del programa original son visibles; no se
suprimieron funciones, filas ni expectativas. El árbol final es nuevo:
`qtapng-work-v3`, `qtapng-v3`, `build-v3-fixture`. Todos los datos/oráculos
previos conservan sus hashes; se agregaron negativos vacío/firma incompleta.

## Batería final

| Caso | Evidencia |
|---|---|
| Composición | Cinco cuadros, RGBA exacto, offsets, SOURCE/OVER, alpha transparente/parcial y disposición NONE/BACKGROUND/PREVIOUS |
| Finito | Una y dos pasadas, metadatos de bucles, cuadros y retardos correctos |
| Retardos | Denominador cero: 30 ms; segundo cuadro: 50 ms |
| Imagen inicial oculta | Dos cuadros animados; el PNG inicial azul queda fuera de la animación |
| Estático | PNG propio leído mediante el plugin, dimensiones y RGBA exactos |
| Errores/recuperación | Inválido, truncado, vacío y firma incompleta rechazados con diagnóstico; el mismo QImageReader se recupera al cambiar a entrada válida |
| QMovie | Bucle de eventos offscreen, CacheAll, orden/píxeles y finalización; dos eventos para una pasada y cuatro para dos |
| Aislamiento | Carpeta de plugins vacía rechaza APNG sin fallback; proceso nuevo antes y después de instalar |
| Original QtApng | Programa completo sobre ocho entradas privadas sin cambios; **11 resultados Qt Test aprobados por etapa**, sin fallos ni skips finales |

Se generaron seis entradas válidas con **14 cuadros**, cuatro negativas y un
JSON de oráculos. Dos generaciones finales son idénticas por hash. Las
**18 ejecuciones CTest finales** y **ocho trazas adicionales** pasan.
Las trazas demuestran Qt Core/Gui y offscreen privados, QtApng del árbol
evaluado y libpng privada; el aislamiento no carga QtApng. Los cuatro
consumidores son x86_64/macOS 11.0. Una raíz Qt ausente se rechaza después
de instalar, sin recurrir a otra instalación.

El timeout de QMovie limita la prueba; no acredita rendimiento. No se cubren
exhaustivamente interlazado, perfiles de color, dispositivos secuenciales,
CacheNone, conteos extremos ni sanitizers.

## Instalación y continuidad

El manifiesto contiene una entrada: `plugins/imageformats/libqapng.dylib`,
**61.424 bytes**, SHA-256
`9c93b89635627cd74bbc71952f615acd5aad43a5978353d24c2d68ea6cbc8317`.
Coincide con el build final. Arquitectura, mínimo macOS y dependencias están
verificados, sin rutas del build en sus load commands. Los **4.958 archivos
regulares y 58 enlaces previos** permanecen intactos; los 304 QM se
contrastaron también con SRC44.

CMake `baseline-configure-v15` mantiene Qt/LinguistTools resueltos y todavía
falla por **KDDockWidgets-qt6 2.3.0 requerido**. FFmpeg también sigue ausente.
El gate mantiene `storage_reserve` y `pcsx2_configure`, con aproximadamente
**15,56 GiB libres** al cierre. Los cuatro checks C++20/Metal se reutilizan
de SRC31; CMake v15 sí se ejecutó en esta unidad.

Comandos, entornos, logs, JUnit, inventarios y parches están en la etapa
privada y `build/f02-07-pcsx2-qt-apng/`. Se publica código propio y metadatos.
No se ejecutó CI remota, suite Python completa, UI visible, GPU, macOS 11
físico ni Nintendo 3DS. El build completo PCSX2, instrumentación, mapa efectivo
y F02.07 siguen pendientes.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron cinco hashes de contrato/fixtures,
81 archivos locales antes del recibo de validación, cinco enlaces locales
y conservación de SRC40–SRC44. El recibo es un archivo local adicional
en la evidencia final.

## Siguiente unidad detallada

**`prerequisites/dependencies-kddockwidgets`**:

1. **Procedencia:** verificar `KDDockWidgets-2.4.1.tar.gz`, SHA-256
   `5cd9495d9316cf6cc937bb328a7fd491c3248ef2469cfa42511f1039f6148aca`,
   desde el tag v2.4.1 fijado en receta; conservar originales/licencias,
   inventariar dependencias, opciones CMake y tests disponibles.
2. **Contrato y capacidad:** definir EARS para el frontend Qt Widgets,
   contenedores y persistencia/restauración de disposición. Estimar fuentes,
   compilación y pruebas para fijar presupuesto antes del build; verificar
   los hashes del prefijo anterior y no asumir que basta el presupuesto QAP.
3. **Build:** Release x86_64/macOS 11.0 y Qt 6.11.1 privado;
   `KDDockWidgets_QT6=true`, `KDDockWidgets_EXAMPLES=false`,
   `KDDockWidgets_FRONTENDS=qtwidgets`; auditar includes/enlaces y compilar
   bajo supervisión sin incorporar frontends o dependencias innecesarios.
4. **Pruebas:** ejecutar los tests originales aplicables y un consumidor
   propio del paquete/target exportado. Verificar creación de docks, cambios
   de estado, cierre/reapertura y guardado/restauración, con negativos y
   recuperación según API real. Separar offscreen de interacción visual.
5. **Instalación y continuidad:** repetir con consumidor nuevo, verificar
   carga, arquitectura, manifiesto y prefijo; volver a configurar PCSX2 y
   ejecutar el gate. Detallar FFmpeg/MoltenVK y conservar abiertos el build
   completo y la instrumentación hasta verificar sus resultados.
