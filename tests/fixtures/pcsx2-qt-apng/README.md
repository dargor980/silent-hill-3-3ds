# Consumidores QtApng host

Código propio de [QAP](../../../schemas/pcsx2-qt-apng-v1.md), sin datos del
juego ni fixtures externos. El generador Python no usa Qt ni libpng: escribe
chunks, CRC y datos zlib y guarda un oráculo de cuadros RGBA explícitos.

```sh
python generate.py /ruta/privada/nueva
```

Configurar CMake con `SH3_QT_CMAKE_ROOT`, `SH3_DATA`, `SH3_PLUGIN_ROOT` y,
para ejecutar el programa original sin modificarlo, `SH3_PROVIDER_SOURCE`.
La raíz Qt exige Core/Gui/Test 6.11.1 exacto. El consumidor recibe las rutas
como argumentos y limita la búsqueda de plugins a la raíz probada.
Ejecutar CTest antes y después de instalar con consumidores nuevos.

Ocho casos propios verifican composición (SOURCE/OVER, alpha, NONE/BACKGROUND/
PREVIOUS), repeticiones finitas, denominador cero, imagen inicial oculta,
PNG estático, archivos inválidos/truncados/vacíos y firmas incompletas con
recuperación, reproducción real QMovie y aislamiento
del plugin. QMovie usa CacheAll y un bucle de eventos offscreen; verifica
orden, píxeles, cantidad de cuadros y finalización para una y dos pasadas.
El timeout solo limita la prueba; no mide rendimiento. La lectura explícita
desactiva autodetección para impedir fallback PNG. El programa original se
copia a cada consumidor privado, incluidos sus recursos, sin editarlo.

Las convenciones de cuadros y retardos siguen la
[especificación PNG/APNG del W3C](https://www.w3.org/TR/2025/REC-png-3-20250624/#11acTL).
Qt informa repeticiones adicionales mediante
[QMovie::loopCount](https://doc.qt.io/qt-6/qmovie.html#loopCount);
se contrastó además el comportamiento de la versión local 6.11.1.

Estos casos no cubren exhaustivamente interlazado, perfiles de color,
dispositivos secuenciales, CacheNone, límites extremos o rendimiento. Requieren
dependencias privadas; no se ejecutan en la CI genérica ni prueban Nintendo 3DS.
