# Fixtures Qt Base 6.11.1

Contrato [QB01–QB08](../../../schemas/pcsx2-qtbase-v1.md). Datos propios,
independientes de BIOS, juego, estados y runtime 3DS. Seis casos funcionales:

| CTest | Oráculo definido antes de ejecutar | Requisito |
|---|---|---|
| `qb_signals` | señal diferida recibida una vez con valor 37; no entrega síncrona; desconexión evita una segunda llamada; timeout de 3 s | QB04 |
| `qb_json` | UTF-8 y objeto JSON se conservan; JSON inválido devuelve documento nulo y diagnóstico | QB04 |
| `qb_resources` | recurso compilado por rcc coincide byte a byte; ruta ausente rechazada | QB04/QB05 |
| `qb_png` | imagen 8×8 con colores/alpha distintos conserva todos los píxeles; PNG corrupto rechazado | QB05 |
| `qb_jpeg` | imagen 8×8 uniforme conserva dimensiones y cada canal queda a ≤12 del original con calidad 95; JPEG corrupto rechazado | QB05 |
| `qb_widgets` | uic conserva texto Unicode; click actualiza contador; botón deshabilitado no lo actualiza; rehabilitarlo permite otro click | QB06 |

`Emitter` exige moc real; `resources.qrc` exige rcc real y `panel.ui` exige uic
real. No se versionan sustitutos generados. Los casos de imágenes y widgets
exigen plataforma `offscreen`, con timeout CTest de 15 s. No prueban ventanas
Cocoa visibles, accesibilidad, GPU, Metal, render del emulador ni macOS 11 físico.
El entorno del pipeline debe fijar `QT_PLUGIN_PATH` al directorio `plugins` del
árbol evaluado y comprobar la carga efectiva.

El subconjunto original opcional contiene `qversionnumber` y `qscopeguard`,
de `tests/auto/corelib/tools/` del archivo verificado. Se compilan sus fuentes
sin modificaciones, usando Qt Test y, para versiones, Qt TestPrivate como en
su CMake original. Se mantienen sus asserts mediante `-UNDEBUG`. El adaptador
CMake de esta carpeta es propio; no equivale a ejecutar toda la suite Qt.
Sus fuentes siguen privadas y conservan los avisos del proveedor.

## Pipeline reproducible

1. Preparar/configurar Qt según QB; comprobar capacidad IB02 antes de compilar.
2. Compilar Qt con dos jobs. Verificar herramientas `moc`/`rcc`/`uic` 6.11.1 y
   arquitecturas de herramientas, bibliotecas y plugins.
3. Configurar este consumidor con `SH3_QT_CMAKE_ROOT=<build-qt>/lib/cmake`,
   `SH3_QT_PROVIDER_SOURCE=<fuentes-qt-verificadas>`, arquitectura x86_64 y
   SDK/compiladores fijados; compilar y ejecutar CTest con JUnit.
4. Tras aprobar, instalar Qt en el prefijo privado y repetir desde un build
   consumidor nuevo con `SH3_QT_CMAKE_ROOT=<prefijo>/lib/cmake`.
5. Configurar con una raíz explícita ausente: debe fallar con
   `Set SH3_QT_CMAKE_ROOT`, aunque exista otro Qt instalado.
6. Contrastar cache/órdenes de enlace, carga efectiva, manifiesto y hashes del
   prefijo antes/después; repetir CMake PCSX2/gate.

El [informe SRC39](../../../docs/execution/f02-07-pcsx2-qtbase.md) conserva la
preparación histórica. [SRC40](../../../docs/execution/f02-07-pcsx2-qtbase-build.md)
completa ocho casos antes/después de instalar y registra la resolución explícita
de TestPrivate añadida tras el primer fallo de configuración del consumidor.
El chequeo de sintaxis por sí solo no acredita moc, rcc, uic, enlace ni ejecución. No incorporar
este build privado completo a CI pública; los controles públicos del repositorio
siguen separados de esta validación local de la herramienta de investigación.
