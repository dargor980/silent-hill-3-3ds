# F02.07 — Preparación de Qt Base

Fecha: 2026-10-17. Unidad preparada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qtbase`.
Contrato [QB01–QB08](../../schemas/pcsx2-qtbase-v1.md); evidencia
[SRC39](../compatibility/pcsx2-qtbase-evidence.json).

Qt Base **6.11.1** tiene fuentes verificadas, tres parches aplicados,
configuración x86_64 aprobada y fixtures preparados. Se compiló y ejecutó
únicamente la herramienta auxiliar `syncqt` para generar headers. **Bibliotecas
Qt, moc/rcc/uic, instalación y tests funcionales siguen pendientes.** La
preparación no completa Qt Base, PCSX2 ni el mapa efectivo de F02.07.

## Procedencia y parches

Se descargó el [archivo oficial fijado por la receta](https://download.qt.io/archive/qt/6.11/6.11.1/submodules/qtbase-everywhere-src-6.11.1.tar.xz):
**50.648.500 bytes**, SHA-256
`d9594a31228aa23ad6b531719a29b45f0f3989fe6c136d45767ea179f233c1ac`.
Contiene **22.859 archivos regulares**, sin symlinks, con **275.949.217 bytes**
descomprimidos. Se comprobaron rutas/tipos antes de extraer. Originales y copia
de trabajo permanecen separados en la raíz privada autorizada.

La receta PCSX2 conserva el commit `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`
y su SHA-256 histórico. Se aplicaron, sin fuzz, fallos ni offsets informados:

| Parche | Resultado |
|---|---|
| `qt-macos11compat.patch` | Seis archivos: mínimo de macOS, diagnóstico de disponibilidad y guardas/adaptaciones de APIs Apple |
| `qt110-xcode264.patch` | Cambio de orden de intrínsecos en `qyieldcpu.h`; aplicable a estas fuentes 6.11.1 |
| Inline `macdeployqt` | Extraído literalmente de la receta; incluye todos los plugins de formatos de imagen |

Hay exactamente **ocho archivos modificados**. El diff final tiene SHA-256
`f468ff1b82e5e6232b4d3987a0c08340f4d9a0767337f41c2a923af07b4b4825`.
El primer verificador detectó seis archivos `.orig` creados por `patch`;
la comprobación posterior confirmó que cada uno coincide con su original.
Se conservaron los backups y el resultado inicial. No hubo correcciones locales
adicionales al código Qt y el checkout PCSX2 permanece limpio.

Se inventariaron **192 archivos de licencias/avisos/REUSE**, incluidos 38 en
`LICENSES/`. Las fuentes contienen alternativas LGPL/GPL/comercial y avisos
de terceros; los dos tests originales seleccionados declaran
`LicenseRef-Qt-Commercial OR GPL-3.0-only`. Se conservan los textos por archivo,
sin interpretar una licencia única para todo el conjunto ni cerrar LIC08.
Van **17/25 archivos de receta verificados**; el snapshot inicial permanece intacto.

## Configuración y aislamiento

CMake termina con salida 0 en **28,61 s**: Apple Clang 21, SDK 26.5, destino
macOS 11.0, `MinSizeRel`, dylibs x86_64 y `CMAKE_APPLE_SILICON_PROCESSOR=x86_64`.
Se conserva `Unix Makefiles` de la receta. Qt advierte que el generador
oficialmente soportado es Ninja; esta configuración exitosa no elimina esa
limitación del build posterior. La [documentación oficial de compilación](https://doc.qt.io/qt-6/macos-building.html)
también señala ese límite; las opciones concretas se verificaron en el archivo 6.11.1.

| Dependencia | Resolución observada |
|---|---|
| PNG 1.6.58, JPEG 3.2.0 | Dylibs y headers privados ya validados |
| FreeType 2.14.3, HarfBuzz 14.2.0 | Targets/headers privados ya validados |
| Zstandard 1.5.7 | Paquete privado |
| zlib 1.2.12 | Headers y stub `libz.tbd` del SDK Apple |
| PCRE2, DoubleConversion, libb2, md4c | Copias incluidas por Qt según su resumen |

`system_*` significa usar componentes externos a Qt: zlib **no** es una
biblioteca privada recién compilada. Core/Gui/Widgets/Test y los targets de
plugins Cocoa/offscreen están configurados. No se requirió un segundo Qt host:
`QT_HOST_PATH` queda vacío; la ejecución posterior de herramientas x86_64 debe
comprobarse individualmente. `syncqt` ya ejecutó correctamente.

Se inspeccionaron **1.170 órdenes de compilación** y **55 de enlace**:
sin referencias Homebrew de target, y todas las compilaciones con `-arch x86_64`.
CMake y Python son herramientas host separadas. Los flags MinSizeRel incluyen
`-Oz`; la línea genérica del resumen sobre optimización no sustituye esos flags.
`QT_FEATURE_opengl=OFF` y no se exporta Qt6OpenGL, aunque la capacidad detectada
`opengl_desktop=ON` aparece en el resumen. Metal está configurado, sin prueba GPU.

Tests/examples completos se fijaron en OFF. La variable adicional
`FETCHCONTENT_FULLY_DISCONNECTED` resultó **no utilizada**: no se presenta como
aislamiento de red. Los componentes utilizados están en el archivo o prefijo;
no se ejecutó la receta completa ni ningún descargador de dependencias posterior.
SBOM está habilitado por Qt; las salidas opcionales que requieren paquetes
Python no quedan acreditadas por esta configuración.

## Diagnósticos y batería preparada

El primer chequeo de Core falló porque faltaba el header de reenvío `QObject`.
Se comprobó el grafo de los targets de sincronización y se construyó solo
`syncqt` (una unidad C++, sin enlace Qt), seguido de headers Core/Gui/Widgets/Test.
El paso terminó en **6,64 s**. El ejecutable es x86_64, pesa **314.152 bytes** y
tiene SHA-256 `24b1a86274425f1b8b92da00de93ee8b5539dc41e4f419b1b9669f2def5787b5`.
No se fabricaron headers moc/uic ni se usó otro Qt instalado.

| Comprobación ejecutada | Resultado |
|---|---|
| Sintaxis C++20 Core, con warnings como errores | Aprobada tras generar headers |
| Sintaxis C++20 imágenes, con warnings como errores | Aprobada |
| XML de formulario/recursos y bytes del mensaje propio | Aprobados |
| Consumidor CMake con raíz Qt explícita ausente | Rechazo esperado con diagnóstico específico |
| Inventario CTest Qt | Cero casos registrados: suite desactivada, no aprobación |
| Originales, parches y prefijo anterior | 22.859 originales y 426 archivos regulares del prefijo intactos, incluidas 21 dylibs |

Los [fixtures propios](../../tests/fixtures/pcsx2-qtbase/README.md) definen seis
casos: señales/eventos con timeout y desconexión, JSON/Unicode y errores,
recursos incorporados, PNG exacto, JPEG con tolerancia declarada y widgets
generados mediante uic. Se seleccionaron además `qversionnumber` y `qscopeguard`
del proveedor, con fuentes sin modificar y dependencias Qt Test/TestPrivate
declaradas en su CMake original. Los ocho casos de ejecución siguen pendientes;
Widgets requiere uic real y aún no tiene ensayo de sintaxis completo.

El pipeline local separa preparación, compilación, consumidor antes de instalar,
instalación condicionada a tests y consumidor nuevo instalado. La raíz explícita
evita aceptar otro Qt por fallback. Logs, argv, entorno, inventarios y hashes
quedan privados o bajo `build/f02-07-pcsx2-qtbase/`; SRC39 publica metadatos.
No se ejecutó CI remota ni se repitió la batería Python histórica de 1.897 casos.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron los hashes de 11 entradas de contrato/fixtures,
26 archivos locales de evidencia y siete enlaces locales de esta documentación.

## Capacidad y siguiente unidad

La etapa ocupa **632.165.017 bytes lógicos** y **792.293.376 asignados**,
por debajo del presupuesto de preparación de 1 GiB. El directorio de build,
incluido `syncqt` y headers, ocupa unos 29,14 MB lógicos; **no** predice el
tamaño final de Qt. El control de capacidad registró **19.353.075.712 bytes
libres**, aproximadamente **18,02 GiB**, frente a los **20 GiB** de IB02.
El espacio fluctúa con otras aplicaciones y debe medirse justo antes de compilar.
El build completo no se inició; no se reutilizó la excepción de Shaderc.

Sigue **`prerequisites/dependencies-qtbase/build-and-validate`**:

1. Volver a verificar hashes del contrato/fixtures/parches y espacio disponible.
   Con al menos 20 GiB, ejecutar el build ya configurado con dos jobs. Conservar
   el primer fallo, sin modificar opciones para ocultar dependencias.
2. Verificar moc/rcc/uic 6.11.1, dylibs y plugins x86_64. Configurar consumidor
   nuevo contra el build y ejecutar seis casos propios más dos originales con
   JUnit; comprobar plugin offscreen y bibliotecas cargadas desde esa etapa.
3. Solo tras pasar, instalar; repetir desde otro consumidor del prefijo privado,
   comprobar manifiesto, arquitectura, carga efectiva y conservación de los
   426 archivos previos. Repetir negativo con prefijo ausente.
4. Ejecutar CMake PCSX2 en `baseline-configure-v10` y reevaluar IB. Qt Base no
   contiene LinguistTools: mantener pendientes Qt Tools, SVG, imageformats,
   translations, QtApng, KDDockWidgets, FFmpeg y MoltenVK según la receta.
5. Publicar evidencia de ejecución separada de SRC39. Build completo PCSX2,
   instrumentación, mapa, corpus, F02.07/Q05/G02 y pruebas 3DS siguen pendientes.

No se repite CMake PCSX2 durante esta preparación, porque aún no hay Qt instalado;
el diagnóstico v9 de SRC38 sigue siendo el último del emulador.
