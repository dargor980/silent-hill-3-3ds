# F02.07 — FFmpeg del observador host

Estado: **FFmpeg 8.1 instalado y validado; CMake PCSX2 configura y genera**.
[Contrato FM01–FM08](../../schemas/pcsx2-ffmpeg-v1.md),
[consumidores propios](../../tests/fixtures/pcsx2-ffmpeg/README.md) y
[evidencia SRC47](../compatibility/pcsx2-ffmpeg-evidence.json).
El build completo y el observador instrumentado continúan pendientes.

## Procedencia y perfil

Archivo oficial `ffmpeg-8.1.tar.xz`, **11.702.216 bytes**, SHA-256
`b072aed6871998cce9b36e7774033105ca29e33632be5b6347f3206898e0756a`,
contrastado contra la receta PCSX2 fijada. Son **24 de 25 archivos de receta**
verificados. Extracción con validación de rutas/tipos: 88.121.289 bytes,
**10.107 archivos originales**, intactos tanto en originales como en la copia
de trabajo. No hay parches de FFmpeg. Cinco archivos de licencia se conservan
privados. NASM host **3.02 arm64** coincide por hash con SRC32; su versión se
volvió a ejecutar, sus 301 tests históricos no se repitieron.

Target **x86_64/macOS 11.0**, Apple Clang 21/SDK de Xcode, cinco bibliotecas
shared y autodetección desactivada. Los flags de receta `-Os` quedan seguidos
por `-O3` en configure: **O3 es la optimización efectiva**, con símbolos de
depuración en el build. El perfil efectivo contiene:

- **12 encoders:** FFV1, QTRLE, PCM S16 LE/BE; AAC, ALAC, iLBC, PCM A-law/μ-law
  mediante AudioToolbox; H.264, HEVC y ProRes mediante VideoToolbox.
- **Seis muxers:** AVI, Matroska, MOV, MP3, MP4 y WAV; solo protocolo file.
- **Cero decoders, demuxers y programas de consola.** Los componentes auxiliares
  que selecciona la receta incluyen parser AC3 y tres bitstream filters.
- Cinco bibliotecas: avcodec, avformat, avutil, swresample y swscale. Los
  frameworks Apple se enlazan, sin ejecutar sus encoders en esta batería.

`FRAME_THREAD_ENCODER` es una opción interna de configure; no cuenta como
encoder público. El consumidor contrasta el inventario público en ejecución.
No se mezclan includes/bibliotecas objetivo Homebrew; NASM host ensambla Mach-O
x86_64. La presencia del código general de red no agrega protocolos de red
al perfil file ni constituye una prueba de conectividad.

## Pipeline y capacidad

Coordinación separada para fuente/configuración, build supervisado, pruebas,
trazas, instalación y auditoría. El consumidor inyecta raíces de headers y
bibliotecas; RAII gestiona contextos, frames, paquetes y resamplers. El oráculo
RIFF y los bytes PCM se calculan independientemente de FFmpeg.

Presupuesto específico: **14 GiB iniciales**, parada bajo **12 GiB libres**,
máximo de **2 GiB** lógicos/asignados por build, dos jobs y auditoría previa
hasta 2.000 objetos/512 MiB de fuentes. El supervisor SRC40 se verificó por
hash; sus siete tests de control son evidencia histórica, no se repitieron.
La reserva general IB de **20 GiB** no cambia.

Plan: **318 objetos, 23 de ensamblador**. Build del módulo aprobado en
**42.49 s**, **45 muestras**, máximo asignado
**24.85 MiB**, mínimo libre
**15.93 GiB**. Se conservan cuatro builds
supervisados, incluido el primer consumidor fallido. El muestreo no es una
cuota y no garantiza observar picos. El plan previo de instalación comprobó
que `make install` no tenía compilación pendiente.

El consumidor inicial falló porque la raíz de FFmpeg contiene un archivo
`version` que ocultaba la cabecera estándar C++ `<version>`. Se conservó el
log/salida y se creó una vista de cabeceras con solo los cinco directorios
`lib*`. La batería se repitió en `build-v2-fixture`; no se modificaron fuentes,
tests originales ni expectativas para superar el fallo.

## Batería y carga

| Caso | Comprobación |
| --- | --- |
| Perfil | Versión 8.1; versiones de cinco bibliotecas contra headers; encoders, muxers, exclusiones y protocolo. |
| PCM | Bytes exactos LE/BE de 16 muestras, timestamps/duración, drenaje y EOF. |
| Vídeo | Tres cuadros por FFV1/QTRLE, PTS ordenados, primer keyframe, EOF y dos ejecuciones idénticas por bytes. |
| WAV | Contenedor escrito por avformat; parser propio verifica RIFF, chunks, formato y payload PCM completo. |
| Escala | RGB24 4×4 a BGRA 8×8, 64 píxeles exactos con alpha y vecino más próximo. |
| Remuestreo | Canales float planar exactos; señal DC de 48 a 24 kHz, drenaje y 500 muestras observadas. |
| Errores | Códec desconocido, ancho/frecuencia cero y directorio ausente; recuperación posterior e I/O con contenido verificado. |
| Originales | MD5, CRC, SHA y channel_layout sin cambios; stdout idéntico a las cuatro referencias FATE. |

**11/11 antes y 11/11 después: 22 ejecuciones CTest aprobadas**, cero fallos
u omisiones finales. Los cuatro programas originales y sus cuatro referencias
privadas conservan sus hashes. No es la suite FATE completa.

**Diez trazas adicionales** comprueban las cinco bibliotecas cargadas desde
el árbol previsto. Antes de instalar, `DYLD_LIBRARY_PATH` apunta a sus cinco
carpetas de build porque los IDs ya señalan al prefijo final. Después de
instalar se elimina ese override y se usa un consumidor nuevo. Los diez
binarios de consumidores son x86_64 con mínimo macOS 11.0.

Cuatro configuraciones negativas rechazan headers ausentes, headers generados
ausentes, raíz de bibliotecas ausente y raíz vacía. La raíz vacía se rechaza
aunque el prefijo real esté disponible: no hay fallback global.

El vídeo no se decodifica; producir paquetes repetibles no acredita fidelidad
visual. En el remuestreo se acepta 499–501 por el borde; se observaron 500,
y el nivel DC 0,25 se compara con tolerancia 0,0001 omitiendo 32 muestras por
extremo. No hay pruebas de AudioToolbox/VideoToolbox en hardware, rendimiento,
concurrencia, sanitizers, macOS 11 físico ni Nintendo 3DS.

## Instalación

Inventario por comparación del prefijo: **172 archivos regulares y 10 enlaces**
nuevos. Incluye cinco dylibs, **136 headers**, cinco metadatos pkg-config y
26 archivos de ejemplos. Los ejemplos se instalan como fuentes; no se
compilaron ni ejecutaron. Su Makefile procede de `Makefile.example` según el
log de instalación; se corrigió la comparación inicial contra `Makefile` y
los 26 archivos coinciden con sus fuentes reales.

| Biblioteca | Bytes instalados | SHA-256 |
| --- | --- | --- |
| avcodec | 509448 | `b9819f72042fcfb5654b07383607823cb3b85630eb6e649d7eea9a806b247cb0` |
| avformat | 497792 | `436f2ae12f84a22b4fea3a3ae8070ed4625cb6968ad4cfdc04dcdd3ed844b95b` |
| avutil | 817224 | `531ff918cd82980c735b5dfd576c1d9281342a7504eea24bcb257282f9e09bc7` |
| swresample | 136232 | `412d8231d8f4a6473c92722c0044f5bf07e0339bf468071fa088ea299424e3ef` |
| swscale | 1483760 | `4c4db6c55016e6d21d6d9686cb98929214b7ddd26ba9494666ec5ff3137b0c67` |

Las cinco dylibs y sus dependencias/arquitectura/mínimo macOS están verificados.
El `strip -x` de instalación se reprodujo sobre copias temporales: sus hashes
coinciden exactamente con los instalados. No quedan rutas del build en los
load commands. Los headers coinciden con fuentes o headers generados, y los
pkg-config declaran el prefijo privado. **5.055 archivos y 60 enlaces previos**
conservan sus hashes/objetivos, incluido todo Qt y KDDockWidgets.

## Continuidad

**`baseline-configure-v17` termina con exit 0 y genera el Makefile de PCSX2.**
Resuelve FFmpeg 8.1 y sus cinco componentes desde el prefijo privado, conserva
Qt/LinguistTools/KDDockWidgets y deja de usar el fallback de headers FFmpeg.
Persiste el aviso **MoltenVK ausente**. El checkout PCSX2 sigue limpio.

El gate IB elimina `pcsx2_configure`; queda **`storage_reserve`**, con
**15.88 GiB libres** al cierre. Los cuatro checks
C++20/Metal se reutilizan de SRC31. CMake v17 sí se ejecutó; no se inició la
compilación completa del emulador. Una configuración correcta no demuestra
que el ejecutable compile, arranque o capture el mapa efectivo.

Logs, argumentos, entornos, muestras, JUnit e inventarios se conservan en el
área privada y `build/f02-07-pcsx2-ffmpeg/`. El repo contiene código propio y
metadatos. No se ejecutó CI remota ni la suite Python completa. Instrumentación,
mapa efectivo, dos salas conectadas y F02.07 siguen pendientes.

La comprobación del repositorio termina **PASS, cero errores**; `git diff
--check` no detecta problemas. Se verificaron seis artefactos propios, 62
archivos de evidencia local previos al recibo de QA, la evidencia anterior
SRC46 y 455 enlaces Markdown locales. No se encontraron rutas privadas en
los trece archivos públicos examinados. La suite Python completa y la CI
remota no se ejecutaron en esta unidad.

## Siguiente unidad detallada

**`prerequisites/dependencies-moltenvk`**:

1. **Procedencia:** verificar `MoltenVK-1.4.1.tar.gz` con SHA-256
   `9985f141902a17de818e264d17c1ce334b748e499ee02fcb4703e4dc0038f89c` y
   conservar originales/licencias. Inspeccionar `ExternalRevisions`, fetch,
   proyectos Xcode y pruebas antes de descargar dependencias transitivas;
   registrar cada revisión y evitar reemplazar el prefijo ya validado.
2. **Contrato/capacidad:** definir EARS para carga Vulkan/MoltenVK, identidad,
   capacidades y un ensayo sintético mínimo. Estimar fuentes, dependencias,
   DerivedData/temporales, arquitecturas y concurrencia; fijar presupuesto
   propio antes del build sin heredar el pequeño consumo de FFmpeg.
3. **Parches/configuración:** verificar y aplicar a una copia los dos parches
   de receta (`4cf93f0f16b1503580cdb7ffdedb056321446677.patch` y
   `mvk-texture-swizzle.patch`) y los ajustes de fetch/Makefile. Auditar que
   Xcode respete x86_64/macOS, SDK/Metal y las opciones
   `MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS=0` y `MVK_CONFIG_USE_METAL_PRIVATE_API=1`.
4. **Build/pruebas:** construir bajo supervisión; ejecutar pruebas originales
   aplicables y consumidor propio con negativas/carga efectiva. Separar
   consultas de API y compilación de shaders de trabajo GPU realmente
   ejecutado; no declarar render válido por cargar una dylib.
5. **Instalación/cierre:** solo tras resultados aprobados, instalar la dylib
   privada, repetir consumidor nuevo y verificar arquitectura, load commands,
   manifiesto/prefijo. Repetir CMake/gate; detallar después el build completo
   PCSX2 y su observador. La configuración v17 no elimina su reserva general.
