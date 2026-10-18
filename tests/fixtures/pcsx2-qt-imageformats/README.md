# Fixture Qt imageformats del observador host

Contrato [QI01–QI08](../../../schemas/pcsx2-qt-imageformats-v1.md).
Siete casos propios y el programa original WebP del proveedor, ejecutados
antes y después de instalar. No contiene imágenes externas ni del juego.

`qi_oracle` genera WebP sin pérdida mediante libwebp 1.6.0, comprueba sus
píxeles y genera TGA 2.0 (dos orientaciones), WBMP (ancho no múltiplo de ocho)
y TIFF básico (gris sin compresión) desde bytes propios. `qi_images` enlaza
solo Qt Gui y decodifica mediante plugins. Comprueba todos los píxeles sin
escalado y centros de cuadrantes con escalado 2x; únicamente este último
permite una unidad de redondeo. El escalado es fallback de QImageReader,
no capacidad nativa del plugin WebP.

Los negativos son WebP cortado a 20 bytes, cabecera TGA cortada a nueve,
WBMP sin su último byte de píxeles y cabecera TIFF cortada a siete. Cada
lector debe rechazar y recuperarse con un archivo válido. El caso de escritura
usa calidad 100 (sin pérdida); un proceso separado libwebp exige dimensiones
y todos los valores RGBA conocidos, sin usar el lector Qt como oráculo.

CMake requiere raíces explícitas `SH3_QT_CMAKE_ROOT` (Qt lib/cmake),
`SH3_WEBP_CMAKE_ROOT` (share/WebP/cmake) y `SH3_IMAGEFORMATS_PLUGIN_ROOT`
(plugins). La raíz de plugins ausente debe fallar aun con Qt instalado.
Ejecutar CTest con `QT_PLUGIN_PATH` apuntando primero al módulo evaluado y
luego a los plugins de Qt Base, además de `QT_QPA_PLATFORM=offscreen`.
Verificar la carga real mediante trazas del loader; la mera enumeración
de formatos no acredita decodificación.

`SH3_QT_PROVIDER_SOURCE` compila el original privado `tst_qwebp`, con sus
cinco imágenes originales también privadas. Ejecuta las nueve filas de
lectura, animación y escritura (más preparación/cierre). Su BLACKLIST afecta
solo a VxWorks y no se aplica a este host. No se ejecutan los restantes
programas originales de imageformats. Los casos propios no prueban ICNS,
HEIF o JPEG2000; sus plugins solo se inventarían estructuralmente. TIFF no
queda validado para otros códecs, multipágina ni escritura, ni TGA/WBMP para
todas sus variantes. No hay pruebas de UI visible, GPU o Nintendo 3DS.
