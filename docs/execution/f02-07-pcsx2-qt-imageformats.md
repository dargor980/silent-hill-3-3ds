# F02.07 — Qt imageformats compilado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-imageformats`.
Contrato [QI01–QI08](../../schemas/pcsx2-qt-imageformats-v1.md),
[fixtures propios](../../tests/fixtures/pcsx2-qt-imageformats/README.md) y
[evidencia SRC42](../compatibility/pcsx2-qt-imageformats-evidence.json).

Qt imageformats **6.11.1** quedó compilado e instalado en el prefijo privado
x86_64. Pasan **8/8 casos antes y 8/8 después de instalar**, incluidos siete
propios y el programa WebP original. Los plugins WebP, TGA, WBMP y TIFF cargan
desde los árboles esperados. CMake PCSX2 v12 sigue detenido en
**Qt6LinguistTools**; continúa **Qt Tools** como siguiente unidad de la receta.

## Procedencia y dependencias

Se verificó `qtimageformats-everywhere-src-6.11.1.tar.xz` contra SHA-256
`b2bf6c6845ac175ed7f819145483ba4676f617aaa6a5012c8efee63c8bbac413`, fijado en
la receta PCSX2. El archivo oficial tiene 2.032.792 bytes comprimidos y
10.230.327 bytes extraídos, en **563 archivos regulares**. Se comprobaron rutas
antes de extraer. Originales y árbol de trabajo permanecen intactos, sin
parches. Se conservan 15 archivos de licencias, avisos, REUSE o atribuciones.

Los binarios Qt Base/SVG previos se contrastaron con SRC40/SRC41 y se tomó un
snapshot del prefijo. Los cinco binarios WebP coinciden tanto con sus hashes
de [SRC32](f02-07-pcsx2-dependencies.md) como con el snapshot inicial y el
prefijo final. Se alcanzan **19/25 archivos de receta verificados**; el plan
inicial y el checkout PCSX2 permanecen sin cambios.

La configuración usa el helper privado, Release x86_64/macOS 11.0,
Apple Clang 21/SDK 26.5, `QT_GENERATE_SBOM=OFF` y
`FEATURE_system_webp=ON`. Se auditaron **59 unidades de compilación** y
**siete enlaces**, sin includes ni bibliotecas objetivo Homebrew.

| Componente | Procedencia y alcance comprobado |
|---|---|
| WebP | libwebp 1.6.0 del prefijo; la copia incorporada en Qt no se compila |
| TIFF | libtiff 4.7.1 incorporada en Qt; 35 unidades compiladas dentro del plugin; zlib del SDK |
| TGA, WBMP, ICNS | Implementaciones del módulo Qt imageformats |
| HEIF y JPEG2000 | Plugins macOS basados en frameworks Apple/ImageIO |
| JasPer y MNG | No disponibles; funciones deshabilitadas |

Que JasPer esté deshabilitado no elimina el plugin JPEG2000 de macOS. ICNS,
HEIF y JPEG2000 se verificaron estructuralmente; no se acredita su ejecución.

## Diseño y build vigilado

El coordinador separa procedencia, configuración, supervisión, pruebas e
instalación. El productor/lector WebP directo es un ejecutable sin Qt.
El consumidor enlaza solamente Qt Gui y accede a los formatos por plugins.
Los oráculos comparten valores de píxeles conocidos; cada camino conserva
una responsabilidad independiente. TGA, WBMP y TIFF se generan desde bytes
propios, sin usar escritores Qt. No se incorporan assets del juego.

QI03 fija un presupuesto específico antes del build: inicio con 16 GiB
libres, dos jobs, máximo de 512 MiB lógicos/asignados y parada si quedan menos
de 14 GiB libres. El supervisor de SRC40 se verificó por hash; sus siete
ensayos sintéticos son evidencia anterior, no pruebas nuevas de este lote.

| Medición | Resultado |
|---|---|
| Duración / salida | 17,52 s / 0 |
| Muestras | 20 |
| Libre inicial | 17.791.725.568 bytes, aproximadamente 16,57 GiB |
| Mínimo libre observado | 17.774.817.280 bytes, aproximadamente 16,55 GiB |
| Máximo lógico | 11.566.167 bytes |
| Máximo asignado | 14.217.216 bytes, aproximadamente 13,56 MiB |
| Intervalo máximo entre muestras | 1,050 s |
| Parada preventiva | Ninguna |

Los temporales se ubicaron dentro del build medido. La vigilancia por
muestreo no es una cuota ni garantiza observar todos los picos. Estos máximos
no incluyen consumidores ni instalación posteriores. La reserva general IB
de 20 GiB permanece vigente para operaciones grandes; QI03 no autoriza por
extensión Qt Tools o PCSX2 completo.

## Pruebas antes y después de instalar

| Caso CTest | Oráculo |
|---|---|
| WebP sin pérdida | Imagen propia 32×24, formato y todos los píxeles RGBA exactos |
| Escalado | QImageReader a 64×48, centros de cuatro cuadrantes, tolerancia máxima de una unidad |
| TGA | Imágenes de 32 bits con origen superior e inferior; todos los píxeles exactos |
| WBMP | Patrón 9×3, alternancia blanco/negro y tratamiento de padding por fila |
| TIFF | Una tira gris 3×2 sin compresión, dimensiones y seis intensidades exactas |
| Truncados/recuperación | Cuatro archivos inválidos rechazados con error; cada lector recupera un archivo válido |
| Escritura WebP | Qt escribe con calidad 100; proceso libwebp separado exige tamaño y todos los valores RGBA conocidos |
| WebP original | Programa `tst_qwebp` completo, sin modificar, con sus recursos privados |

El escalado es el fallback de QImageReader; el plugin WebP no expone una
opción nativa ScaledSize. La tolerancia se aplica solo a los centros de
cuadrantes escalados, evitando bordes. En los demás positivos propios se
exige igualdad exacta.

Los truncados concretos son: WebP cortado a 20 bytes, cabecera TGA a nueve,
WBMP sin el último byte de píxeles y cabecera TIFF a siete. Estos casos no
acreditan rechazo de toda posible corrupción. El lector independiente del
escritor Qt usa libwebp directamente: separa el camino Qt, pero comparte la
biblioteca de códec subyacente. Los valores esperados son conocidos antes
del encode/decode.

El test original ejecuta tres filas de lectura, dos de animación y cuatro
de escritura. Por etapa registra **11 resultados Qt Test aprobados**, al
incluir preparación/cierre, sin fallos, skips ni blacklisted. Su BLACKLIST
afecta VxWorks y no aplica a este host. Esto cubre ese programa WebP, no la
suite completa de imageformats ni el fuzzing de libwebp. La suite global
del módulo permanece deshabilitada.

Las **16 ejecuciones CTest** pasan en `build-v1-fixture` e `installed-v1`,
dos consumidores nuevos. Los nueve archivos sintéticos de entrada tienen
hashes idénticos entre ambas etapas. Se añaden **diez ejecuciones para trazar
carga**: cuatro consumidores de formato y el lector WebP directo por etapa.
Los plugins probados cargan desde el build o instalación correspondiente,
Qt/offscreen y WebP desde el prefijo aprobado, sin bibliotecas Homebrew.
Los seis ejecutables consumidores son x86_64. El consumidor Qt no enlaza
WebP/plugins directamente; el oráculo no enlaza Qt.

La raíz de plugins explícita inexistente fue rechazada después de instalar,
sin permitir que el Qt válido ocultase ese error de configuración.

## Instalación y límites

El manifiesto registra **59 entradas presentes** y **siete plugins Mach-O**
x86_64 con mínimo declarado macOS 11.0. Dependencias y load commands no
contienen rutas del build ni bibliotecas Homebrew. Los **4.218 archivos
regulares y 52 enlaces simbólicos previos** permanecen intactos.

| Plugin | Bytes | Ejecución probada |
|---|---:|---|
| qwebp | 50.672 | Lectura, animación original, escritura y carga |
| qtga | 38.384 | Dos orientaciones, negativo y carga |
| qwbmp | 37.952 | Lectura con padding, negativo y carga |
| qtiff | 521.320 | Gris sin compresión, negativo y carga |
| qicns | 58.200 | No; inventario/arquitectura/dependencias |
| qmacheif | 57.856 | No; inventario/arquitectura/dependencias |
| qmacjp2 | 57.520 | No; inventario/arquitectura/dependencias |

Los hashes binarios completos están en SRC42. Quedan sin evaluar otros
códecs, multipágina y escritura TIFF, todas las variantes TGA/WBMP, ICNS,
HEIF/JPEG2000 en ejecución, sanitizers, fuzzing, rendimiento, ventanas
visibles, GPU y macOS 11 físico. Las pruebas Qt usan offscreen sobre el host.

`baseline-configure-v12` vuelve a encontrar Core/Gui/Widgets y sus herramientas,
pero falta LinguistTools. FFmpeg sigue ausente; el aviso de headers incluidos
no acredita enlace con esa biblioteca. El gate `preflight-v12.json` mantiene
`storage_reserve` y `pcsx2_configure`, con unos **16,54 GiB libres** al medir
el cierre. Los cuatro checks C++20/Metal se reutilizan de SRC31; CMake v12 sí
se ejecutó en esta unidad.

Logs, entornos, comandos, JUnit, muestras e inventarios permanecen en el
directorio privado y `build/f02-07-pcsx2-qt-imageformats/`. No se ejecutó CI
remota ni se repitieron los 1.897 casos Python históricos. Build PCSX2 completo,
instrumentación, mapa efectivo, F02.07 y validación Nintendo 3DS siguen abiertos.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron siete hashes de contrato/fixtures,
45 archivos locales de evidencia previos al recibo de validación y seis
enlaces locales del contrato, README del fixture e informe.

## Siguiente unidad detallada

**`prerequisites/dependencies-qt-tools`**, para resolver LinguistTools:

1. **Fuentes y capacidad:** verificar `qttools-everywhere-src-6.11.1.tar.xz`,
   SHA-256 `8e61835a679c93fa9c6065b142353c2071ba68e297898937c32a03777fcaf50d`;
   conservar originales/licencias, inspeccionar componentes habilitados y
   dimensionar su build antes de establecer capacidad y supervisión propias.
   No reutilizar automáticamente el presupuesto del módulo de imágenes.
2. **Contrato y fixtures:** definir EARS para descubrimiento de LinguistTools,
   lupdate/lrelease y traducciones. Usar C++/TS propios con contexto, español,
   Unicode y plurales; comprobar extracción, generación QM y traducción efectiva
   mediante QTranslator. Añadir TS inválido, archivo ausente y repetibilidad
   donde corresponda, sin usar textos del juego.
3. **Configuración:** helper privado y Qt 6.11.1 exacto, Release x86_64/macOS
   11.0, `QT_GENERATE_SBOM=OFF`. Respetar la receta: designer ON; assistant,
   clang, kmap2qmap, pixeltool, pkg_config, qev, qtattributionsscanner, qtdiag
   y qtplugininfo OFF. Auditar qué herramientas/bibliotecas se construyen
   realmente y sus dependencias; mantener búsquedas aisladas.
4. **Build y pruebas:** compilar con límites medidos. Ejecutar herramientas
   reales y consumidores nuevos, seleccionar tests originales aplicables y
   comprobar Qt6LinguistTools/targets exportados. Si UiTools queda habilitado,
   validar carga de un formulario propio mediante QUiLoader y rechazo de UI
   inválida; no contar la compilación de Designer como prueba visual.
5. **Instalación y continuidad:** solo tras aprobar, instalar y repetir contra
   el prefijo; verificar arquitectura, versiones, carga, manifiesto y hashes
   anteriores. Repetir CMake/gate para observar el siguiente requisito real.
   Mantener translations, QtApng, KDDockWidgets, FFmpeg y MoltenVK pendientes
   hasta disponer de evidencia propia.
