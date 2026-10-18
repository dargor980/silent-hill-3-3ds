# F02.07 — Qt Base compilado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qtbase/build-and-validate`.
Contratos [QB01–QB08](../../schemas/pcsx2-qtbase-v1.md) y
[QL01–QL05](../../schemas/pcsx2-qtbase-bounded-build-v1.md); evidencia
[SRC40](../compatibility/pcsx2-qtbase-build-evidence.json).

Qt Base **6.11.1** está compilado, probado e instalado en el prefijo privado
x86_64. Pasan **8/8 casos antes y 8/8 después de instalar**. PCSX2 resuelve
Core/Gui/Widgets y sus herramientas; el siguiente error fatal es
**Qt6LinguistTools**, perteneciente a Qt Tools. FFmpeg también permanece
ausente. Build PCSX2 completo, instrumentación, mapa efectivo y F02.07 siguen
pendientes de sus evidencias propias.

## Intento vigilado y capacidad

Al continuar había 18,22 GiB libres. La reserva genérica de 20 GiB había
detenido el build en [SRC39](f02-07-pcsx2-qtbase.md). Se definió una excepción
**específica para Qt Base**, antes de compilar: inicio con 18 GiB, dos jobs,
máximo 4 GiB de archivos de build y parada si el volumen baja de 12 GiB.
El alcance es una arquitectura, MinSizeRel, sin ejemplos ni suite completa,
sin WebEngine ni otros módulos Qt. La excepción no habilita automáticamente
MoltenVK ni PCSX2 completo; el gate IB conserva 20 GiB.

El coordinador separa medición, política y administración de procesos. Siete
ensayos sintéticos comprobaron éxito, salida 7, rechazo inicial, límite de
tamaño, mínimo libre simulado, error de medición y violación en la muestra
final. Las pruebas de parada también comprobaron terminación de un proceso
hijo. El primer ensayo no pudo consultar `ps` dentro del sandbox; la repetición
con acceso autorizado completó los siete casos. No se llenó el disco.

| Medición del build Qt | Resultado |
|---|---|
| Duración | 480,36 s, aproximadamente ocho minutos |
| Muestras | 395 |
| Libre inicial | 19.584.212.992 bytes |
| Mínimo libre observado | 18.167.316.480 bytes, aproximadamente 16,92 GiB |
| Máximo lógico del build | 1.108.728.148 bytes |
| Máximo asignado del build | 1.178.103.808 bytes, aproximadamente 1,10 GiB |
| Intervalo máximo entre muestras | 1,635 s |
| Salida / parada preventiva | 0 / ninguna |

Los temporales del compilador se ubicaron dentro del build medido. La pausa
nominal entre muestras fue un segundo, además del tiempo de medición. Esto
es vigilancia por muestreo, no cuota ni garantía contra picos intermedios.
La variación del espacio del volumen no se atribuye íntegramente al build.
La instalación y consumidores posteriores son operaciones separadas del tamaño
máximo registrado para la compilación de Qt.

## Fuentes y configuración

Se verificaron los insumos de SRC39 antes de iniciar: archivo, originales,
contrato/fixtures, parches y prefijo previo. No hubo nuevas descargas. Se
conservan Apple Clang 21/SDK 26.5, MinSizeRel, macOS 11.0, x86_64, dylibs,
opciones de receta y búsquedas aisladas. Los tres parches originales no
requirieron correcciones durante el build.

Los **22.859 originales** permanecen intactos. El árbol de trabajo contiene
los ocho cambios esperados y seis backups `.orig` idénticos a sus originales.
El diff final conserva SHA-256
`f468ff1b82e5e6232b4d3987a0c08340f4d9a0767337f41c2a923af07b4b4825`.
El checkout PCSX2 sigue limpio. Se mantienen 17/25 archivos de receta
verificados y el snapshot inicial inalterado.

## Pruebas y corrección del consumidor

`moc`, `rcc` y `uic` ejecutaron con versión **6.11.1**. El primer consumidor
falló al generar CMake: faltaba solicitar explícitamente el paquete
`Qt6TestPrivate`, aunque su target figuraba en el enlace de `qversionnumber`.
Se corrigió únicamente el CMake propio: resolución exacta de TestPrivate y
CorePrivate desde la raíz Qt explícita. Se conservan archivo anterior, hash,
diagnóstico y directorio fallido. El consumidor corregido usa un directorio
nuevo. No se modificaron las fuentes de tests originales ni sus expectativas.

| Caso | Evidencia antes y después de instalar |
|---|---|
| Señales/eventos | Entrega diferida única del valor 37, desconexión y timeout |
| JSON/Unicode | Ida/vuelta exacta; JSON inválido rechazado con diagnóstico |
| Recursos | Mensaje incorporado por rcc exacto; ruta ausente rechazada |
| PNG | Dimensiones, colores y alpha exactos; datos corruptos rechazados |
| JPEG | Dimensiones y tolerancia ≤12 por canal; datos corruptos rechazados |
| Widgets | Formulario generado por uic, texto español y contador con botón habilitado/deshabilitado |
| `qversionnumber` original | 532 resultados Qt Test aprobados por ejecución |
| `qscopeguard` original | 9 resultados Qt Test aprobados por ejecución |

Son ocho casos CTest distintos y **dieciséis ejecuciones aprobadas**, sin
fallos ni skips. Los conteos de Qt Test incluyen sus filas de datos y
preparación/cierre; no son la suite completa del proveedor. El proyecto Qt
mantiene `QT_BUILD_TESTS=OFF`: su inventario global vacío no se cuenta como
aprobación. Los seis [fixtures propios](../../tests/fixtures/pcsx2-qtbase/README.md)
ejercitan moc/rcc/uic reales. Imágenes y Widgets usan `offscreen`.

También se realizaron seis ejecuciones adicionales para trazar carga: Core,
imágenes y Widgets contra build e instalación. Cada una carga Qt desde su
árbol esperado; offscreen y JPEG cargan sus plugins correspondientes. No hay
bibliotecas Homebrew en esas trazas ni enlaces de los consumidores. Los diez
ejecutables de prueba son x86_64. El prefijo explícito ausente sigue rechazado
después de instalar un Qt válido.

No se probaron ventanas Cocoa visibles, GPU, Metal en ejecución, accesibilidad,
impresoras, red/TLS, rendimiento, sanitizers ni macOS 11 físico. Que el plugin
Cocoa compile no acredita esas funciones. No se ejecutó el juego con este Qt.

## Instalación y continuidad

El manifiesto tiene **3.703 entradas presentes**. Se verificaron **40 binarios
Mach-O** x86_64 con mínimo de sistema declarado 11.0 y **ocho archivos estáticos**
x86_64. Los **426 archivos regulares previos**, incluidas **21 dylibs**,
conservan sus hashes. La instalación añade ocho dylibs principales:

| Biblioteca | Bytes | SHA-256 |
|---|---:|---|
| Qt6Core | 7.353.912 | `ec33970adfed85e24ec60dd14c59f5b9b28daec2a9b466c564cef46cff423ef1` |
| Qt6Gui | 7.452.160 | `c7867022100fa4aef612156fa693da8adb1c978a11fb32d265cb6ada0ca33f67` |
| Qt6Widgets | 7.494.224 | `8d3670bbc1c9e1a5954e8ba4e06ad0daabed57126d9c869f6476636ade210769` |

Concurrent, Network, Xml, Test y PrintSupport completan el conjunto. SRC40
incluye el inventario binario y hashes; el manifiesto completo queda local.
Fuentes, avisos, parches y artefactos se conservan privados. La instalación
local no cierra LIC08 para un eventual bundle ni sustituye su revisión.

`baseline-configure-v10` resuelve los seis paquetes Core/CoreTools,
Gui/GuiTools y Widgets/WidgetsTools del prefijo. Qt6_FOUND continúa falso
porque falta **LinguistTools**; no se ocultó el requisito deshabilitando la UI.
FFmpeg sigue sin encontrarse: el aviso de headers incluidos no acredita enlace
FFmpeg. KDDockWidgets y otros requisitos posteriores conservan estado pendiente.

El gate `preflight-v10.json` conserva `storage_reserve` y `pcsx2_configure`.
Quedaban aproximadamente 16,86 GiB tras la instalación; debe medirse de nuevo
antes de otro build. Sus cuatro checks C++20/Metal se reutilizan de SRC31;
CMake v10 sí se ejecutó ahora. El éxito de Qt no aprueba el build completo.

Logs, argv, entornos, JUnit, mediciones y verificadores quedan en la etapa
privada y `build/f02-07-pcsx2-qtbase-build/`. No se ejecutó CI remota ni se
repitieron los 1.897 casos Python históricos.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se contrastaron hashes de 12 entradas de contrato/fixtures,
42 archivos locales de evidencia, nueve enlaces locales y el SRC39 histórico
sin modificaciones.

## Siguiente unidad detallada

Sigue **`prerequisites/dependencies-qt-svg`**, respetando la receta antes de
imageformats y Qt Tools:

1. **Procedencia:** verificar `qtsvg-everywhere-src-6.11.1.tar.xz`, SHA-256
   `7f3cf02f4824bf03c2c5859ea6db173bf1482a1daf24e6cdf7bc78cfa26a8a94`;
   conservar originales/licencias y medir tamaño/capacidad. Definir su alcance
   de build y presupuesto propio: QL no se extiende automáticamente.
2. **Contrato y diseño:** definir EARS para QSvgRenderer y los plugins de imagen
   e iconos. Fixtures SVG propios con dimensiones, rectángulos/colores conocidos,
   transformaciones/transparencia y XML inválido; no imágenes del juego.
   Diferenciar render directo, QImageReader y QIcon para observar cada entrada.
3. **Build:** usar el `qt-configure-module` privado, Qt 6.11.1 exacto, x86_64,
   opciones Release de la receta y `QT_GENERATE_SBOM=OFF` según ese paso;
   conservar búsquedas aisladas, logs y paralelismo acotado.
4. **Pruebas/instalación:** seleccionar tests originales aplicables, comprobar
   consumidores/plugins antes de instalar y repetir desde un consumidor nuevo;
   verificar píxeles/oráculos, rechazo de datos inválidos, arquitectura,
   carga efectiva, manifiesto y conservación del prefijo anterior.
5. **Continuidad:** registrar evidencia y preparar Qt imageformats, luego Qt
   Tools para LinguistTools. Mantener pendientes translations, QtApng,
   KDDockWidgets, FFmpeg y MoltenVK. No anunciar cerrado PCSX2/F02.07/Q05/G02
   ni compatibilidad 3DS con estos resultados host.
