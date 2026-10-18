# F02.07 — Qt Tools/LinguistTools compilado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-tools`.
Contrato [QTO01–QTO08](../../schemas/pcsx2-qt-tools-v1.md),
[fixtures propios](../../tests/fixtures/pcsx2-qt-tools/README.md) y
[evidencia SRC43](../compatibility/pcsx2-qt-tools-evidence.json).

Qt Tools **6.11.1** quedó compilado e instalado en el prefijo privado x86_64.
Pasaron **8/8 casos antes y 8/8 después de instalar**. PCSX2 ya resuelve
**Qt6LinguistTools**: la configuración v13 avanza hasta **KDDockWidgets-qt6**,
que todavía falta. FFmpeg también permanece ausente. La siguiente unidad
de la receta pendiente es **Qt translations**, antes de QtApng/KDDockWidgets.

## Procedencia y alcance

Se verificó `qttools-everywhere-src-6.11.1.tar.xz` contra SHA-256
`8e61835a679c93fa9c6065b142353c2071ba68e297898937c32a03777fcaf50d` de la receta
fijada. El archivo oficial contiene 10.225.832 bytes comprimidos y 38.147.648
extraídos, en **5.769 archivos regulares**. Se comprobaron las rutas antes
de extraer. Los originales y el árbol de trabajo conservan sus hashes, sin
parches. Permanecen privados 52 archivos de licencias, avisos, REUSE o
atribuciones. El checkout PCSX2 y el plan inicial siguen intactos.

Se contrastaron los binarios Qt Base/SVG/imageformats con SRC40–SRC42 y se
tomó un snapshot del prefijo. Se alcanzan **20/25 archivos de receta
verificados**. La configuración usa el helper privado, Qt 6.11.1 exacto,
Release, x86_64/macOS 11.0, Apple Clang 21/SDK 26.5 y
`QT_GENERATE_SBOM=OFF`, con búsquedas aisladas.

Se respetaron designer ON y assistant, clang, kmap2qmap, pixeltool,
pkg_config, qev, qtattributionsscanner, qtdiag y qtplugininfo OFF. El alcance
efectivo es:

| Componente | Resultado |
|---|---|
| LinguistTools | lconvert, lcheck, lrelease, lrelease-pro, lupdate, lupdate-pro y ltext2id |
| UiTools | Biblioteca de carga de formularios, probada mediante QUiLoader |
| Designer | Aplicación, biblioteca Designer y DesignerComponents; sin prueba visual |
| Linguist GUI | No construida; su condición requiere Qt Quick, ausente |
| Assistant, QDoc, qdbus y demás opciones excluidas | No construidas |

LinguistTools es el paquete de herramientas requerido por PCSX2; no se
confunde con la aplicación gráfica Linguist. Se auditaron **352 unidades
de compilación y 14 comandos de enlace/archivo**, incluidos tres archivos
estáticos internos del build, sin includes ni bibliotecas objetivo Homebrew.

## Build vigilado

QTO03 fija un presupuesto propio: inicio con 15 GiB libres, máximo de 2 GiB
lógicos/asignados, dos jobs y parada si quedan menos de 12 GiB libres.
El supervisor se reutiliza de SRC40 tras verificar su hash. Sus siete
ensayos sintéticos son evidencia previa; no se cuentan como nuevos.

| Medición | Resultado |
|---|---|
| Duración / salida | 160,35 s / 0 |
| Muestras | 153 |
| Libre inicial | 17.326.387.200 bytes, aproximadamente 16,14 GiB |
| Mínimo libre observado | 16.899.477.504 bytes, aproximadamente 15,74 GiB |
| Máximo lógico del build | 391.918.342 bytes |
| Máximo asignado del build | 406.700.032 bytes, aproximadamente 387,86 MiB |
| Intervalo máximo entre muestras | 1,265 s |
| Parada preventiva | Ninguna |

Los temporales se ubicaron dentro del build medido. El muestreo no es una
cuota ni garantiza observar todos los picos. Consumidores e instalación son
operaciones posteriores separadas. El gate IB general conserva su reserva
de 20 GiB para operaciones grandes; QTO03 no autoriza otros builds.

## Diseño y pruebas

El coordinador separa fuentes/configuración, supervisión, herramientas,
consumidores e instalación. Un verificador Python inspecciona el XML de
lupdate y los hashes de lrelease. Un ejecutable Qt Core comprueba las
traducciones reales; otro usa Qt Widgets/UiTools en offscreen. CMake genera
el QM mediante el target exportado `Qt6::lrelease`. Las rutas de herramientas
provienen de esos targets, sin búsqueda implícita en PATH.

| Caso CTest | Comprobación |
|---|---|
| Extracción/actualización | Cinco mensajes C++ con contexto, Unicode, desambiguación y plural; actualización conserva las traducciones del TS |
| QM repetible | Dos ejecuciones lrelease producen bytes y SHA-256 idénticos |
| Errores de herramientas | TS mal formado, TS ausente y C++ ausente rechazados con diagnóstico; lrelease no deja QM de esos fallos |
| Traducción efectiva | Español, emoji, dos sentidos de «Key», plurales 0/1/2/5, contexto ausente y fallback tras retirar el traductor |
| QM inválido/recuperación | QTranslator rechaza contenido inválido y luego carga/traduce el QM válido |
| Formulario | QUiLoader crea controles con texto español, título y señales; botón deshabilitado no emite clic |
| UI inválida/recuperación | XML UI mal formado rechazado con diagnóstico; mismo loader carga luego el formulario válido |
| lrelease original | Siete funciones originales sobre copias privadas de sus datos, sin cambiar expectativas |

`lupdate` y `lrelease` informan versión **6.11.1** antes y después. El QM
propio conserva SHA-256
`0a276d95026e447bca565909e343325d5723c5b82ecf9249a4e68eb2191de398`
entre el pipeline CMake, las dos compilaciones del caso de repetibilidad,
la ejecución con traza y ambas etapas.

El programa original `tst_lrelease` cubre `translate`, `compressed`, `idbased`,
`markuntranslated`, `dupes`, `noTranslations` e `invalidTranslations`.
Registra **9 resultados Qt Test aprobados por etapa**, incluyendo preparación
y cierre, sin fallos ni skips. No es la suite completa Qt Tools.

Los tests originales escriben QM junto a sus TS. CMake copia previamente
su carpeta a cada consumidor privado; se verificaron **nueve entradas
originales intactas por copia**. Un `qt.conf` local selecciona el directorio
de herramientas evaluado para QLibraryInfo. No se cambia código del proveedor
ni se alteran rutas del loader para hacer pasar el test.

En total pasan **16 ejecuciones CTest** entre `build-v1-fixture` e
`installed-v1`. Otras **diez ejecuciones** trazan traducción, UI, lrelease,+lupdate y una función del test original por etapa. Confirman Qt Core/Widgets
y offscreen del prefijo, UiTools del árbol evaluado y el lrelease correcto
incluso cuando lo invoca el proceso hijo del test original. Los seis
consumidores son x86_64, sin bibliotecas Homebrew en enlaces ni trazas.
La raíz Tools inexistente se rechaza aun después de instalar Qt válido.

## Instalación y corrección de auditoría

El manifiesto tiene **384 entradas presentes**. Contiene **ocho ejecutables,
tres dylibs y un archivo objeto Mach-O**, todos x86_64 con mínimo declarado
macOS 11.0. No hay archivos estáticos `.a` instalados; los tres del build
son internos. Los **4.277 archivos regulares y 52 enlaces simbólicos previos**
conservan su contenido/destino.

La primera auditoría esperaba once Mach-O, contando ejecutables y dylibs.
Detectó un duodécimo: el objeto de recursos `qrc_proparser_init.cpp.o` de
QMakeParserCumulative. Se conservó el verificador anterior y el diagnóstico,
y se corrigió la clasificación: ocho `MH_EXECUTE`, tres `MH_DYLIB` y un
`MH_OBJECT` cuya ruta/tipo se exigen explícitamente. No se relajaron las
pruebas de traducción ni las expectativas del proveedor. La auditoría
corregida verificó arquitectura, dependencias, load commands, manifiesto y
conservación completa del prefijo/fuentes.

| Artefacto principal | Bytes | SHA-256 |
|---|---:|---|
| lrelease | 791.336 | `8c756246c6ae580f50a72aee3e7347303428de541eccb02c3df6750c961c3231` |
| lupdate | 1.052.712 | `032a84c7a773ea831163f3bbdaa88472bb338d0a06f7a9daa5620d364e4ff1e0` |
| Qt6UiTools | 618.128 | `8170969fd78a7e01ebe2cb23bd8d393b0ab40bda35dab111626a00c48efa0300` |

SRC43 contiene el resto del inventario binario y el objeto. Designer y
DesignerComponents no tienen prueba de interacción visual; otras herramientas
CLI tampoco quedan cubiertas exhaustivamente. No se ejecutaron sanitizers,
fuzzing, benchmarks, GPU, macOS 11 físico ni runtime Nintendo 3DS.

## Continuidad

`baseline-configure-v13` resuelve Core/Gui/Widgets, sus herramientas y
LinguistTools desde el prefijo. El siguiente error fatal es
**KDDockWidgets-qt6 2.3.0 requerido**. FFmpeg sigue ausente; el aviso de
headers incluidos no acredita su enlace. El gate `preflight-v13.json`
mantiene `storage_reserve` y `pcsx2_configure`, con unos **15,68 GiB libres**
al medir el cierre. Los cuatro checks C++20/Metal se reutilizan de SRC31;
CMake v13 sí se ejecutó en esta unidad.

Logs, entornos, comandos, JUnit, muestras e inventarios permanecen en la
etapa privada y `build/f02-07-pcsx2-qt-tools/`. No se ejecutó CI remota ni se
repitieron los 1.897 casos Python históricos. El build completo PCSX2,
instrumentación, mapa efectivo, F02.07 y validación física siguen pendientes.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron 13 hashes de contrato/fixtures, 49
archivos locales previos al recibo de validación y cinco enlaces locales
del contrato, README del fixture e informe.

## Siguiente unidad detallada

**`prerequisites/dependencies-qt-translations`**:

1. **Procedencia y capacidad:** verificar `qttranslations-everywhere-src-6.11.1.tar.xz`,
   SHA-256 `37c02c81206594c7bb4edca85ac93e8e55a9836b70c960fde6cb0f8623ec5677`;
   conservar originales/licencias, inventariar TS, locales y dependencias de
   catálogos, y dimensionar fuentes/salidas antes de definir su presupuesto.
2. **Contrato y oráculos:** definir EARS para generación y carga de catálogos.
   Elegir mensajes españoles terminados directamente de los TS privados,
   incluyendo Unicode/plurales cuando existan, y comparar QTranslator contra
   esos valores. Separar mensajes sin terminar/obsoletos y módulos ausentes;
   no contar un QM presente como traducción funcional.
3. **Configuración y build:** helper privado, Qt 6.11.1 exacto, Release
   x86_64/macOS 11.0 y `QT_GENERATE_SBOM=OFF`; usar lrelease instalado y
   verificado, sin incorporar textos del juego. Registrar herramientas,
   catálogos generados y salidas deterministas donde aplique.
4. **Validación/instalación:** probar carga y resultados conocidos antes y
   después de instalar, dependencias entre catálogos, negativos de archivo
   ausente/corrupto y recuperación. Comprobar manifiesto, hashes repetidos y
   conservación del prefijo; los QM son datos, no binarios con arquitectura.
5. **Continuidad:** repetir CMake/gate y publicar solo metadatos. Seguir con
   QtApng, después KDDockWidgets, FFmpeg y MoltenVK conforme a la receta.
   Mantener abierto el observador hasta construirlo y verificarlo completo.
