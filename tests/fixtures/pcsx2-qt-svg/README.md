# Fixture Qt SVG del observador host

Contrato [QS01–QS08](../../../schemas/pcsx2-qt-svg-v1.md).
Fuentes SVG/XML propias; sin contenido del juego. Renderer, lector de imágenes
e icono se compilan por separado. Los dos últimos enlazan únicamente Qt Gui:
la carga de `libqsvg` y `libqsvgicon` se verifica además mediante trazas del loader.

Cinco casos: dimensiones/viewBox/píxeles, transformación/alpha, XML inválido y
recuperación, QImageReader con escalado/errores, y QIcon desde recurso compilado.
Los píxeles opacos y transparentes son exactos; alpha y canales premultiplicados
admiten una unidad de redondeo. Se comprueban interiores, evitando bordes.

Configurar con Qt 6.11.1 exacto y las raíces explícitas `SH3_QT_CMAKE_ROOT`
y `SH3_QTSVG_CMAKE_ROOT` (directorios `lib/cmake`). Ejecutar CTest con
`QT_QPA_PLATFORM=offscreen` y `QT_PLUGIN_PATH` apuntando primero a los plugins
del módulo evaluado y después a Qt Base. Repetir con consumidores nuevos antes
y después de instalar. Una raíz SVG ausente debe fallar sin fallback.

`SH3_QT_PROVIDER_SOURCE` permite compilar el test original privado de Qt SVG
sin copiarlo al repositorio ni modificarlo. Se ejecutan solo `getSetCheck`,
`testMapViewBoxToTarget`, `constructorQXmlStreamReader`, `loadQXmlStreamReader`,
`transformForElement` y `opacity`; el resto de la suite no queda acreditado.
La aplicación y los tests externos conservan sus licencias originales.

Estos casos prueban renderizado raster offscreen; no prueban ventanas visibles,
GPU, una sesión de PCSX2 ni ejecución en Nintendo 3DS.
