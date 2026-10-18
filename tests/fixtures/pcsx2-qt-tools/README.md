# Fixture Qt Tools del observador host

Contrato [QTO01–QTO08](../../../schemas/pcsx2-qt-tools-v1.md).
Siete casos propios: extracción/actualización TS, QM repetible, errores de
herramientas, traducción efectiva, rechazo/recuperación QM, formulario y
rechazo/recuperación UI. Textos, TS y formularios propios, sin material del juego.

El verificador Python inspecciona XML y hashes; Qt Core comprueba español,
Unicode, desambiguación, plurales 0/1/2/5 y fallback; otro ejecutable usa
QUiLoader con controles, texto y señales reales en offscreen. El build genera
QM mediante el target exportado Qt6::lrelease. Las herramientas se invocan
por rutas exportadas, nunca mediante una búsqueda implícita en PATH.

Configurar con raíces explícitas SH3_QT_CMAKE_ROOT y SH3_TOOLS_CMAKE_ROOT
(directorios lib/cmake), Qt 6.11.1 exacto y Python3. La raíz Tools ausente debe
fallar incluso si hay otro Qt instalado. Repetir desde consumidores nuevos
antes/después de instalar y comprobar carga de Qt/UiTools y herramientas.

SH3_QT_PROVIDER_SOURCE permite compilar `tst_lrelease` original sin modificarlo.
CMake copia su carpeta a la salida privada porque los tests generan QM junto
a los TS. `qt.conf` selecciona el directorio lrelease evaluado para QLibraryInfo;
no altera el enlace dinámico. Se ejecutan sus siete funciones, incluyendo
compresión, IDs, duplicados y errores de validación; el resto de la suite Qt
Tools no queda acreditado. Fuentes/fixtures externos conservan sus licencias
y permanecen privados. Designer no se prueba visualmente ni se valida runtime 3DS.
