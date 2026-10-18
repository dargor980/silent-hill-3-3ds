# Consumidores FFmpeg 8.1

Código propio para [FM01–FM08](../../../schemas/pcsx2-ffmpeg-v1.md).
Se enlaza con avcodec, avformat, avutil, swresample y swscale privados.
Los datos de prueba se generan en memoria; WAV y archivos de recuperación
se escriben únicamente en el directorio del consumidor.

| Caso | Oráculo |
| --- | --- |
| `fm_profile` | Versión 8.1, versiones de las cinco bibliotecas coincidentes con headers, 12 encoders/0 decoders, seis muxers y solo protocolo de salida file. |
| `fm_pcm` | 16 muestras extremas/positivas/negativas, bytes independientes little/big endian, PTS/duración, drenaje y EOF. |
| `fm_video` | Tres cuadros propios por encoder FFV1/QTRLE, PTS, keyframe inicial, EOF y dos codificaciones idénticas por bytes. |
| `fm_wav` | Parser RIFF propio: tamaño, formato PCM estéreo 48 kHz/16 bits, byte rate, block align y payload exacto. |
| `fm_scale` | RGB24 4×4 a BGRA 8×8, vecino más próximo, 64 píxeles y alpha exactos. |
| `fm_resample` | S16 estéreo a float planar con canales exactos; mono constante 48 a 24 kHz, drenaje, duración y nivel DC. |
| `fm_errors` | Códec desconocido, ancho cero, frecuencia cero y directorio ausente; recuperación del resampler, scaler e I/O. |
| Cuatro originales | MD5, CRC, SHA y channel_layout, ejecutados sin cambios y stdout idéntico a sus referencias FATE. |

El remuestreo admite 499–501 muestras por cuantización del borde (se observan
500); compara el nivel 0,25 con tolerancia 0,0001 excluyendo 32 muestras por
extremo. Los tests de vídeo comprueban producción y repetibilidad de paquetes;
no decodifican ni acreditan reconstrucción visual. El perfil no incluye
decoders ni demuxers. No se prueban encoders de AudioToolbox/VideoToolbox,
rendimiento, concurrencia ni hardware. Cuatro programas no representan toda
la suite FATE; los ocho archivos originales de programas/referencias quedan
privados y se verifican por hash.

`fixture.hpp` concentra propiedad RAII, comprobación de errores y datos PCM.
Las funciones de codificación, contenedor, transformación y oráculos tienen
responsabilidades separadas. CMake inyecta dependencias mediante targets
importados; no descarga ni compila fuentes externas.

Configurar con `SH3_FFMPEG_HEADERS`, `SH3_FFMPEG_GENERATED` y
`SH3_FFMPEG_LIBROOT`. En el build son fuentes, build y build respectivamente;
después de instalar, include, include y lib del prefijo. Las raíces deben
existir y `find_library` usa `NO_DEFAULT_PATH`. Para los originales, indicar
`SH3_PROVIDER_SOURCE` y `SH3_PYTHON`. Compilar con el mismo toolchain/target
y ejecutar CTest con `--output-on-failure --output-junit`.

El consumidor crea una vista con enlaces a los cinco directorios de headers.
Esto evita que el archivo de texto `version` en la raíz de FFmpeg oculte
`<version>` de C++. El primer intento fallido se conserva; no se altera ninguna
fuente del proveedor. Los headers generados preceden a esta vista.

Antes de instalar se usan las cinco carpetas del build en `DYLD_LIBRARY_PATH`
porque los dylibs ya declaran el identificador del prefijo de instalación.
Después se elimina ese override y se configura un consumidor nuevo. Las
trazas comprueban las cinco rutas cargadas en ambos casos. Logs, JUnit y
supervisión de capacidad permanecen privados y se publican solo sus metadatos.
La ejecución local no implica CI remota ni comportamiento del runtime 3DS.
