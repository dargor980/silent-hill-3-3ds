# F02.07 — KDDockWidgets del observador host

Estado: **unidad completada con una corrección de empaquetado**.
[Contrato KDW01–KDW08](../../schemas/pcsx2-kddockwidgets-v1.md),
[consumidor propio](../../tests/fixtures/pcsx2-kddockwidgets/README.md) y
[evidencia SRC46](../compatibility/pcsx2-kddockwidgets-evidence.json).
El build completo de PCSX2 y el mapa efectivo siguen pendientes.

## Procedencia y configuración

KDDockWidgets **2.4.1**, tag v2.4.1 de KDAB, archivo de **4.321.566 bytes**,
SHA-256 `5cd9495d9316cf6cc937bb328a7fd491c3248ef2469cfa42511f1039f6148aca`.
Se verificó contra la receta PCSX2 fijada: **23 de 25 archivos** descargados
y contrastados hasta esta unidad. La extracción validó rutas/tipos antes de
escribir: 8.504.850 bytes, **793 originales intactos**, nueve archivos de
licencias/avisos inventariados. No se incorporan archivos del proveedor al repo.

Build Release, x86_64, mínimo macOS 11.0, Qt **6.11.1** del prefijo privado;
`KDDockWidgets_QT6=true`, `KDDockWidgets_EXAMPLES=false`,
`KDDockWidgets_FRONTENDS=qtwidgets`. Se verificó Qt WidgetsPrivate, requerido
por esta versión con Qt 6.10 o superior, y los comandos de compilación/enlace.
Se usan KDBindings y nlohmann JSON incorporados; spdlog/fmt no se encontraron
ni se enlazaron. No hay includes ni bibliotecas objetivo Homebrew.
Developer mode, Qt Quick, Python, ejemplos y documentación están desactivados.

El pipeline local separa fuentes/configuración, supervisión, consumidor,
trazas, instalación y auditoría. Los tests usan `KDAB::kddockwidgets` y raíces
CMake explícitas. Un hook propio exporta el target existente para probar el
árbol de build antes de instalar; no modifica su código ni opciones funcionales.
Las responsabilidades del escenario, aserciones y persistencia permanecen
separadas. La automatización detiene pasos dependientes ante un fallo.

## Capacidad y corrección

Cada build de esta unidad se supervisó con dos jobs, inicio de **14 GiB**,
piso de **12 GiB**, máximo de **1 GiB** lógico/asignado y límite previo de
500 unidades/256 MiB de fuentes. El supervisor SRC40 se verificó por hash;
sus siete controles históricos no se volvieron a ejecutar.

El build final tiene **80 unidades**, **62.69 s**,
**65 muestras**, máximo asignado
**33.77 MiB** y mínimo libre
**16.41 GiB**.
Las muestras y los seis intentos de compilación, incluido el fallido,
quedan registrados. El muestreo no es una cuota ni garantiza detectar picos.
El gate general IB conserva su reserva de **20 GiB**.

La primera batería contra el build aprobó ocho casos. Tras instalar, el
programa original `includes_test` falló al compilar porque el paquete omitía
`kddockwidgets/qtwidgets/Platform.h`. Se conservó `installed-v1` y se prepararon
fuentes/build nuevos. Una única regla en `src/CMakeLists.txt` instala esa
cabecera sin modificarla. El parche privado tiene SHA-256
`2a28ede48422802af4fea1625de48293dc3b4b3f919c09a82dc5f0b9aac9b3dc`.
Los C++ originales y los tests no cambian; las bibliotecas de build v1/v2
son idénticas por hash. Los 793 originales se conservan; en la copia final
solo cambia ese CMakeLists.

También se conservan dos fallos del verificador: asumía que una variable
CMake normal estaría en la caché, y que instalar no cambiaría el hash Mach-O.
Se corrigieron contrastando raíz explícita/enlace/carga y reproduciendo la
transformación `install_name_tool -id` de CMake sobre una copia temporal.
La copia transformada coincide byte a byte con la biblioteca instalada.
No se alteraron expectativas de las pruebas para superar estos fallos.

## Pruebas finales

| Caso | Resultado observado |
| --- | --- |
| Acoplamiento | Contenido propio, grupos separados, ventana compartida, flotar y reacoplar. |
| Pestañas | Grupo compartido y selección de pestaña en ambas direcciones. |
| Ciclo de vida | Cierre y reapertura preservan contenido y acoplamiento. |
| Memoria | Serialización JSON y restauración después de cambiar estados. |
| Archivo | Guardado y restauración desde un temporal propio. |
| JSON inválido | JSON roto y objeto incompleto rechazados; recuperación válida posterior. |
| Archivo ausente | Rechazo y recuperación desde un archivo válido. |
| `includes_test` original | Compila, enlaza y ejecuta sin cambios, incluidas las cabeceras Qt Widgets. Su main no realiza pruebas funcionales. |

Las restauraciones verifican los tres IDs, estados abierto/acoplado/flotante,
relación de pestañas, pestaña activa, ventana asociada, contenido, lista de
paneles restaurados y finalización del restore. **8/8 casos antes y 8/8 después
de instalar: 16 ejecuciones CTest finales**, sin fallos ni omisiones.
Se conservan además los ocho éxitos iniciales, separados del resultado final.

**Seis trazas finales** comprueban la biblioteca del árbol seleccionado,
Qt Core/Gui/Widgets y plugin offscreen del prefijo privado. Hay tres trazas
históricas adicionales. Los cuatro ejecutables finales son x86_64/macOS 11.0.
Dos configuraciones negativas rechazan raíces KDD/Qt ausentes después de
instalar, aunque el prefijo real esté disponible.

Offscreen valida estados y eventos; no valida arrastre físico, foco nativo,
apariencia ni geometría exacta. No se ejecutó la suite gráfica completa del
proveedor, que exige su perfil developer y APIs adicionales de testing.

## Instalación y continuidad

**99 entradas de manifiesto, 98 rutas únicas**
(una cabecera se enumera dos veces por las reglas originales). Una dylib
`lib/libkddockwidgets-qt6.2.4.1.dylib`, **2,329,704 bytes**,
SHA-256 `be30435867527a3fcba331edda30f25ba1e9fd0ca226eb39e7126f4f2d2c1728`. Arquitectura y mínimo macOS verificados;
no tiene rutas del build en sus load commands. CMake cambia su identificador
`@rpath` por el prefijo privado; esa transformación se comprobó exactamente.
Los **4.959 archivos regulares y 58 enlaces previos** conservan sus hashes
u objetivos, incluidos Qt, plugins y traducciones anteriores.

La nueva configuración **v16** resuelve KDDockWidgets y alcanza la generación;
se detiene porque falta **`FFMPEG::avcodec`** con `USE_LINKED_FFMPEG=ON`.
También advierte que MoltenVK no está disponible. Qt/LinguistTools siguen
resueltos. El gate mantiene `storage_reserve` y `pcsx2_configure`, con
**16.28 GiB libres** al cierre. Los cuatro checks C++20/Metal se
reutilizan de SRC31; CMake v16 sí se ejecutó en esta unidad.

Comandos, entornos, logs, JUnit, manifiestos y parches se conservan en la
etapa privada y `build/f02-07-pcsx2-kddockwidgets/`. La evidencia publica
código propio y metadatos. No se ejecutó CI remota ni la suite Python completa.
No hay prueba física de macOS 11, Nintendo 3DS ni build completo de PCSX2.
Observador instrumentado, mapa efectivo, dos salas y F02.07 permanecen abiertos.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron cinco hashes de contrato/fixtures,
72 archivos locales antes del recibo de validación, cinco enlaces locales
y conservación de las seis evidencias Qt previas. Los nuevos artefactos
públicos no contienen rutas privadas absolutas ni espacios finales.
El recibo añade un archivo local a la evidencia final.

## Siguiente unidad detallada

**`prerequisites/dependencies-ffmpeg`**:

1. **Procedencia y alcance:** verificar `ffmpeg-8.1.tar.xz` contra el SHA-256
   de receta `b072aed6871998cce9b36e7774033105ca29e33632be5b6347f3206898e0756a`;
   conservar originales/licencias y examinar `configure`, tests y requisitos
   NASM. Inventariar el prefijo antes de escribir y comprobar sus hashes.
2. **Contrato y capacidad:** definir EARS para codificación/muxing, conversión
   de imagen y remuestreo con datos propios, errores y liberación de recursos.
   Estimar fuentes, unidades, temporales y pruebas; fijar presupuesto antes
   de compilar sin trasladar automáticamente el límite pequeño de KDW.
3. **Build:** reproducir el perfil x86_64/macOS de la receta con autodetección
   y componentes generales desactivados, shared y cinco bibliotecas activas:
   avcodec, avformat, avutil, swresample, swscale. Mantener encoders/muxers y
   protocolo file fijados, Audiotoolbox/Videotoolbox según disponibilidad real.
   Auditar toolchain, NASM, includes, enlaces y límites durante el build.
4. **Batería:** ejecutar tests originales aplicables y consumidores propios
   de las cinco bibliotecas, antes/después de instalar. Usar cuadros/PCM
   sintéticos para codificación, contenedor, conversión y remuestreo; comprobar
   metadatos, contenido esperado, errores y recuperación. Distinguir funciones
   software de hardware/frameworks y no prometer decodificación si el perfil
   de receta no incluye decoders. Exigir rechazo de raíces ausentes y trazas.
5. **Cierre:** auditar binarios, arquitectura, mínimo macOS, manifiesto y prefijo;
   repetir configuración PCSX2/gate en salidas nuevas y detallar MoltenVK como
   unidad siguiente. Conservar pendientes build completo e instrumentación.
