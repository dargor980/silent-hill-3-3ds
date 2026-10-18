# Consumidor privado de catálogos Qt

Código propio de [QTR](../../../schemas/pcsx2-qt-translations-v1.md).
No contiene catálogos, mensajes ni tests del proveedor.

`oracle.py` recibe `--source` (directorio de TS originales), `--english`
(TS vacíos generados por CMake) y `--output` (JSON nuevo en ubicación privada).
Lee XML sin Qt y emite los mensajes españoles terminados, además del inventario
de idiomas/dependencias. Solo imprime contadores. No transforma las fuentes.

Configurar CMake con `SH3_QT_CMAKE_ROOT`, `SH3_QM_ROOT` y `SH3_TS_ORACLE`.
Se exige Qt Core 6.11.1 exacto desde la raíz explícita. Compilar el consumidor
con el toolchain host elegido y ejecutar CTest. Repetir en un árbol nuevo
después de instalar los QM; registrar hashes y la carga efectiva de Qt Core.

Los cinco casos comprueban: carga/idioma de cada QM; mensajes españoles
incluyendo plurales 0/1/2/5, comentarios y Unicode; agregación desde dos
dependencias; rechazo de archivo ausente/corrupto y recuperación; dependencia
ausente/parcial y recuperación en un directorio aislado. Comparan salida
directa de QTranslator y sustitución de `%n` por QCoreApplication.
La regla plural del oráculo es exclusivamente española.

No hay tests originales en este archivo fuente de Qt translations. Los
originales TS son entradas privadas, no fixtures sintéticos del repositorio.
Estos casos no prueban la calidad lingüística ni los textos de Silent Hill 3.
No son parte de la CI genérica: requieren las dependencias Qt privadas.
