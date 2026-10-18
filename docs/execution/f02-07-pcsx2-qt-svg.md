# F02.07 — Qt SVG compilado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-svg`.
Contrato [QS01–QS08](../../schemas/pcsx2-qt-svg-v1.md),
[fixtures](../../tests/fixtures/pcsx2-qt-svg/README.md) y evidencia
[SRC41](../compatibility/pcsx2-qt-svg-evidence.json).

Qt SVG **6.11.1** quedó compilado e instalado en el prefijo privado x86_64.
Pasaron **6/6 casos CTest antes y 6/6 después de instalar**. El renderer,
QImageReader y QIcon cargan las bibliotecas/plugins esperados. La configuración
PCSX2 v11 continúa detenida en **Qt6LinguistTools**; FFmpeg también falta.
El siguiente módulo de la receta es **Qt imageformats**.

## Procedencia, diseño y configuración

Se descargó el archivo oficial `qtsvg-everywhere-src-6.11.1.tar.xz` y se
verificó SHA-256 `7f3cf02f4824bf03c2c5859ea6db173bf1482a1daf24e6cdf7bc78cfa26a8a94`
contra la receta fijada de PCSX2. Tiene 2.336.944 bytes comprimidos y
7.054.115 bytes extraídos, distribuidos en 634 archivos regulares. Se
validaron rutas antes de extraer. Los originales y el árbol de trabajo
mantienen todos sus hashes, sin parches. Los 13 archivos de licencias,
avisos o REUSE inventariados permanecen privados con las fuentes.

Se verificaron los binarios instalados de [SRC40](f02-07-pcsx2-qtbase-build.md)
y se tomó un snapshot de archivos/enlaces del prefijo. El inventario de
descargas verificadas llega a **18/25**; el plan inicial permanece intacto.

La configuración usa `qt-configure-module` del prefijo privado, Qt 6.11.1,
Release, x86_64, mínimo macOS 11.0 y `QT_GENERATE_SBOM=OFF`, como indica este
paso de la receta. Se mantienen Apple Clang 21, SDK 26.5, registros de
paquetes desactivados y búsqueda aislada. Sus **34 unidades de compilación**
y **cuatro enlaces** usan la arquitectura y mínimo de sistema esperados,
sin includes ni bibliotecas objetivo de Homebrew.

El coordinador separa procedencia, configuración, supervisión e instalación.
Tres ejecutables separan el renderer de los consumidores de plugins; lector
e icono enlazan solamente Qt Gui, lo que permite comprobar carga dinámica
sin que un enlace directo a Svg oculte un problema. Comparten únicamente
comprobaciones de errores y oráculos de píxeles. CMake genera los recursos
con el rcc privado; no se incorporan imágenes ni código del juego.

## Build vigilado

QS02 fija un presupuesto propio para este módulo pequeño: inicio con
16 GiB libres, dos jobs, máximo de 512 MiB lógicos o asignados en el build,
y parada si quedan menos de 14 GiB. Se verificó el hash del supervisor de
SRC40 antes de reutilizarlo. Sus siete ensayos de control son evidencia
previa; no se anuncian como pruebas nuevas de este lote.

| Medición | Resultado |
|---|---|
| Duración / salida | 21,46 s / 0 |
| Muestras | 24 |
| Libre inicial | 17.961.345.024 bytes, aproximadamente 16,73 GiB |
| Mínimo libre observado | 17.824.739.328 bytes, aproximadamente 16,60 GiB |
| Máximo lógico | 122.277.680 bytes |
| Máximo asignado | 126.943.232 bytes, aproximadamente 121,06 MiB |
| Intervalo máximo entre muestras | 1,036 s |
| Parada preventiva | Ninguna |

Los temporales se ubicaron dentro del build medido. La vigilancia por
muestreo no es una cuota ni garantiza observar picos intermedios. El tamaño
máximo corresponde al build del módulo; consumidores e instalación son
operaciones posteriores separadas. La reserva IB general de 20 GiB sigue
vigente para operaciones grandes.

## Pruebas antes y después de instalar

| Caso CTest | Comprobación |
|---|---|
| Renderer básico | SVG válido, tamaño 32×24, viewBox y píxeles rojos/transparentes conocidos |
| Transformación/alpha | Rectángulos trasladado y rotado; posición y color; alpha semitransparente |
| XML inválido | Rechazo y renderer inválido; recuperación cargando el SVG válido |
| QImageReader | Plugin SVG, formato/tamaño, píxeles, escalado 64×48, error y recuperación |
| QIcon | Recurso compilado, plugin SVG de iconos, pixmap 64×48 con DPR 1 y píxeles |
| Test original seleccionado | Seis funciones de `tst_qsvgrenderer`, sin modificar sus fuentes |

Los píxeles opacos y transparentes son exactos. Alpha/canales premultiplicados
permiten una unidad de redondeo, declarada antes de ejecutar. Se evitan bordes
antialias. Los XML inválidos se comprueban por rechazo efectivo, no por una
simple detección del encabezado del formato.

Las seis funciones originales son `getSetCheck`, `testMapViewBoxToTarget`,
`constructorQXmlStreamReader`, `loadQXmlStreamReader`, `transformForElement`
y `opacity`. Cada ejecución registra **8 resultados Qt Test aprobados**,
incluyendo preparación/cierre, sin fallos ni skips. No equivale a la suite
completa: `QT_BUILD_TESTS=OFF` y los casos no seleccionados siguen sin evaluar.

El primer CMake del consumidor falló por un nombre incorrecto en
`qt_add_resources` del fixture propio. Se corrigió el nombre para coincidir
con el target creado y se repitió en `build-v2-fixture`, conservando archivo
anterior, diagnóstico y directorio fallido. No se modificaron tests externos
ni expectativas para obtener aprobación. El consumidor instalado es otro
directorio nuevo, `installed-v1`.

Además de las **12 ejecuciones CTest aprobadas**, se realizaron seis
ejecuciones para trazar carga. Se verificaron Qt Core/Gui y offscreen del
prefijo, Svg del árbol evaluado, `libqsvg.dylib` en el lector y
`libqsvgicon.dylib` en el icono. Ninguna traza ni enlace de consumidor usa
bibliotecas Homebrew. Los ocho ejecutables de prueba son x86_64. La raíz
SVG explícita inexistente fue rechazada aun después de instalar Qt válido.

## Instalación y estado general

El manifiesto contiene **106 entradas presentes** y cuatro Mach-O x86_64
con mínimo declarado macOS 11.0. Sus dependencias/rutas fueron comprobadas;
los artefactos instalados no conservan la ruta del build en sus load commands.

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| Qt6Svg | 663.552 | `f4e218a22d5352a15a2f102f22e29c822a46cdf8542226b7aa3d96f700cc84af` |
| Plugin de iconos SVG | 69.936 | `d3f5c36af66d2a9e37f93dca00429f4798ce38d6a9a7e7b480ba89725fc03103` |
| Plugin de imágenes SVG | 40.096 | `5c9f76abe8bd172f442685c63cfd4cd0152692fa559cccfb72b0de14f9b79df4` |
| Qt6SvgWidgets | 65.512 | `ea07330928fe73a6faa19776d89b156394979e4b3ec8a69be5cd4bed682ef88d` |

Los **4.116 archivos regulares y 48 enlaces simbólicos previos** permanecen
intactos. SvgWidgets quedó instalado y verificado estructuralmente; no se
probó su comportamiento como widget. Tampoco se probaron animaciones,
filtros, fuentes SVG, fuzzing, sanitizers, rendimiento, ventanas visibles,
GPU ni macOS 11 físico. Las pruebas son raster/offscreen sobre el host.

`baseline-configure-v11` vuelve a encontrar Core/Gui/Widgets y sus
herramientas del prefijo, y falla en LinguistTools. El aviso de headers
FFmpeg incluidos no acredita enlace con FFmpeg. `preflight-v11.json`
conserva `storage_reserve` y `pcsx2_configure`, con unos 16,61 GiB libres
al medir el cierre. Los cuatro checks C++20/Metal se reutilizan de SRC31;
la configuración v11 sí se ejecutó en esta unidad.

Logs, comandos, entornos, JUnit, muestras y verificadores quedan en el
directorio privado y `build/f02-07-pcsx2-qt-svg/`. SRC41 publica hashes y
metadatos. No se ejecutó CI remota ni se repitió la batería histórica de
1.897 casos Python. El build completo de PCSX2, la instrumentación, el mapa
efectivo, F02.07 y las pruebas en Nintendo 3DS siguen pendientes.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron los hashes de diez entradas de contrato/
fixtures y 43 archivos locales de evidencia, además de los 7 enlaces locales
del contrato, README del fixture e informe.

## Siguiente unidad detallada

**`prerequisites/dependencies-qt-imageformats`**, antes de Qt Tools:

1. **Procedencia y alcance:** verificar `qtimageformats-everywhere-src-6.11.1.tar.xz`
   contra `b2bf6c6845ac175ed7f819145483ba4676f617aaa6a5012c8efee63c8bbac413`;
   conservar originales/licencias, inventariar plugins y medir capacidad antes
   de elegir un presupuesto propio. QS02 no se aplica automáticamente.
2. **EARS y diseño:** separar generación de imágenes propias, consumidor Qt
   y comprobación del loader. Definir decodificación WebP sin pérdida con
   tamaño/color/alpha conocidos, escalado donde sea soportado y rechazo de
   truncados con recuperación. Seleccionar otros formatos según los plugins
   realmente habilitados; documentar omisiones y capacidades de escritura.
3. **Configuración y build:** usar `qt-configure-module` privado, Qt 6.11.1
   exacto, Release x86_64/macOS 11.0, `QT_GENERATE_SBOM=OFF` y
   `FEATURE_system_webp=ON`. Verificar que WebP procede del prefijo aprobado;
   inspeccionar qué otras bibliotecas son incorporadas o externas. Mantener
   aislamiento, logs y paralelismo acotado.
4. **Pruebas e instalación:** consumidores nuevos antes/después; imágenes
   sintéticas, negativos y tests originales aplicables. Comprobar carga de
   plugins y WebP, arquitectura, manifiesto y conservación del prefijo. Una
   mera lista de formatos reconocidos no sustituye decodificación efectiva.
5. **Continuidad:** repetir CMake/gate y publicar evidencia. Seguir con
   Qt Tools/LinguistTools, translations, QtApng, KDDockWidgets, FFmpeg y
   MoltenVK según la receta; no cerrar el observador ni F02.07 con pruebas
   aisladas de plugins.
