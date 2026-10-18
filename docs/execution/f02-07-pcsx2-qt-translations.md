# F02.07 — Qt translations generado, instalado y validado

Fecha: 2026-10-17. Unidad completada:
`origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-translations`.
Contrato [QTR01–QTR08](../../schemas/pcsx2-qt-translations-v1.md),
[consumidor propio](../../tests/fixtures/pcsx2-qt-translations/README.md) y
[evidencia SRC44](../compatibility/pcsx2-qt-translations-evidence.json).

Qt translations **6.11.1** quedó instalado: **304 QM**, idénticos a una
regeneración independiente, y cinco casos CTest aprobados antes y después.
Se compararon los **4.502 mensajes españoles terminados** contra los TS
originales. Son traducciones de Qt para el observador host; no son textos
extraídos de Silent Hill 3. CMake PCSX2 v14 todavía requiere KDDockWidgets.
La siguiente unidad de receta es **QtApng 1.3.0**.

## Procedencia y configuración

El archivo `qttranslations-everywhere-src-6.11.1.tar.xz` coincide con el
SHA-256 fijado `37c02c81206594c7bb4edca85ac93e8e55a9836b70c960fde6cb0f8623ec5677`.
Contiene 1.684.616 bytes comprimidos, 22.580.230 extraídos y **309 archivos
regulares**. Se validaron las rutas antes de extraer. Originales y copia de
trabajo conservan todos sus hashes; no se aplicaron parches. Cinco archivos
de licencias/reglas permanecen privados. Se verificaron los binarios y el
objeto Qt de SRC40–SRC43, además de capturar el prefijo completo.

Se alcanzan **21/25 archivos de receta verificados**. El helper privado
configuró Release, Qt 6.11.1, `QT_GENERATE_SBOM=OFF`, x86_64/macOS 11.0 y
búsquedas aisladas. El módulo no tiene unidades C/C++ ni enlaces: genera
**datos QM independientes de arquitectura** mediante 304 comandos del
`lrelease` privado de SRC43, cuyo hash se volvió a comprobar.

Los **291 TS suministrados** generan sus QM; CMake agrega **13 TS ingleses
vacíos**, también compilados y verificados. No se omite ningún TS del archivo.
Los avisos por repositorios hermanos ausentes afectan a targets para
actualizar fuentes TS, que no se ejecutaron; la generación QM usa los TS
suministrados. No hay programas de test originales en este archivo fuente.

## Capacidad y generación

QTR03 establece inicio con 14 GiB libres, piso de 12 GiB, máximo de 1 GiB
lógico/asignado de build y dos jobs. Se reutilizó el supervisor de SRC40
tras verificar su hash; sus siete pruebas de control son evidencia previa.

| Medición | Resultado |
|---|---|
| Duración / salida | 11,18 s / 0 |
| Muestras | 14 |
| Libre inicial | 16.865.280.000 bytes |
| Mínimo libre observado | 16.829.939.712 bytes, aproximadamente 15,67 GiB |
| Máximo lógico del build | 18.840.879 bytes |
| Máximo asignado del build | 20.688.896 bytes, aproximadamente 19,73 MiB |
| Intervalo máximo entre muestras | 1,023 s |
| Parada preventiva | Ninguna |

Los temporales quedaron dentro del árbol medido. El muestreo no es una cuota
ni garantiza capturar picos intermedios. La regeneración y los consumidores
son operaciones posteriores separadas. El gate IB general conserva 20 GiB;
este presupuesto solo corresponde a la generación de catálogos.

## Oráculo y pruebas

El lector Python propio interpreta XML sin Qt y genera expectativas privadas.
El consumidor C++ recibe el JSON y la carpeta QM mediante argumentos; carga
Qt Core 6.11.1 desde una raíz explícita. Adquisición, generación, oráculo,
consumo y auditoría están separados. No se añaden catálogos ni textos del
proveedor al repositorio o a la CI.

| Caso CTest | Comprobación por etapa |
|---|---|
| `qtr_catalogs` | Los 304 QM cargan y su idioma coincide con el TS, incluidas dependencias y catálogos vacíos |
| `qtr_spanish` | 4.502 mensajes en 12 catálogos; 20 plurales probados con 0/1/2/5, 32 mensajes desambiguados y 1.853 con Unicode; 4.562 comparaciones |
| `qtr_aggregate` | `qt_es` resuelve `qtbase_es` y `qtmultimedia_es`: 1.647 comparaciones desde el agregador |
| `qtr_recovery` | Archivo ausente y QM corrupto rechazados, sin datos anteriores retenidos; recuperación con 1.532 comparaciones |
| `qtr_missing-dependency` | Agregador aislado sin dependencias y con una sola dependencia rechazado; copia de la segunda permite recuperar 1.647 comparaciones |

Cada comparación de mensaje verifica QTranslator directamente y
QCoreApplication, incluida sustitución de plurales. Se comprueba fallback
ante contexto/mensaje ausente y tras retirar el traductor. Los 13 catálogos
españoles incluyen el agregador sin mensajes propios. El inventario y las
dependencias por catálogo están en SRC44; el contenido del oráculo sigue
privado. Estas comprobaciones no evalúan calidad lingüística humana ni el
significado de las traducciones de otros idiomas.

Una segunda ejecución de lrelease sobre cada entrada, en un directorio
separado, produce los mismos bytes/SHA-256 que CMake para **304/304 QM**.
Las **10 ejecuciones CTest** pasan sin fallos ni skips. Seis ejecuciones
adicionales trazan español, agregación y recuperación de dependencias antes
y después de instalar. Los dos consumidores son x86_64, mínimo declarado
macOS 11.0, cargan Qt Core privado y no enlazan bibliotecas Homebrew.
La configuración con raíz Qt inexistente se rechaza incluso después de
instalar Qt válido.

El primer intento del coordinador buscó los TS ingleses en
`translations/en_ts`; CMake los había generado en `src/translations/en_ts`.
El oráculo falló antes de escribir y el intento de configurar su consumidor
rechazó la entrada ausente. Se conservan ambos logs y el coordinador anterior.
Se corrigió la ruta, se añadió la precondición de oráculo presente y se
repitió en `oracle-v2`/`build-v2-fixture`. No se modificaron fuentes del
proveedor ni expectativas funcionales; ningún test funcional o instalación
se ejecutó en esos intentos fallidos.

## Instalación y continuidad

El manifiesto tiene **305 entradas**: 304 QM, que suman **15.861.801 bytes**,
y `translations/catalogs.json`. Todos coinciden con el build. Los **4.653
archivos regulares y 58 enlaces simbólicos previos** permanecen intactos.
El consumidor nuevo `installed-v1` repite las cinco pruebas y las tres trazas.

`baseline-configure-v14` resuelve Core/Gui/Widgets, sus herramientas y
LinguistTools. Sigue faltando **KDDockWidgets-qt6 2.3.0 requerido**. FFmpeg
también está ausente; el fallback a headers incluidos no acredita su enlace.
`preflight-v14.json` conserva los bloqueos `storage_reserve` y
`pcsx2_configure`, con **15,65 GiB libres** al cierre. Los cuatro checks
C++20/Metal se reutilizan de SRC31, no se vuelven a contar como ejecuciones.

Los logs, JUnit, comandos, entornos, inventarios y muestras permanecen en
la etapa privada y `build/f02-07-pcsx2-qt-translations/`. No se ejecutaron
CI remota, suite Python completa, UI visual, GPU, macOS 11 físico ni Nintendo
3DS. El build completo PCSX2, instrumentación, mapa efectivo, F02.07 y sus
gates de contenido permanecen abiertos.

Los controles del repositorio pasan con **0 errores** y `git diff --check`
no informa problemas. Se verificaron cinco hashes de contrato/fixtures,
48 archivos locales antes del recibo de validación, cinco enlaces locales
y conservación de las evidencias SRC40–SRC43. La evidencia final incluye
el recibo como archivo local adicional.

## Siguiente unidad detallada

**`prerequisites/dependencies-qt-apng`**:

1. **Procedencia y alcance:** verificar `QtApng-1.3.0.tar.gz`, SHA-256
   `f1d3be3489f758efe1a8f12118a212febbe611aa670af32e0159fa3c1feab2a6`;
   conservar originales/licencias y auditar tests suministrados. Verificar
   el parche `qtapng-cmake.patch` de la receta antes de aplicarlo a una copia.
2. **Contrato y presupuesto:** definir EARS, inventariar fuentes y enlaces,
   estimar el espacio del módulo y fijar límites antes de compilar. Comprobar
   Qt Core/Gui y libpng/APNG privados; el parche exige PNG ≥1.6.40 y ZLIB,
   elimina las copias incorporadas y agrega instalación del plugin.
3. **Build:** configurar Release x86_64/macOS 11.0 con búsquedas aisladas;
   comprobar includes, bibliotecas y salida `plugins/imageformats`.
   Construir con supervisor y conservar fallos, sin modificar originales.
4. **Validación funcional:** crear APNG propios con oráculos independientes
   para colores/alpha, dimensiones, número y orden de cuadros, retardos,
   repetición y disposición/composición según soporte real. Probar mediante
   QImageReader/QMovie, archivo truncado/inválido y recuperación. Ejecutar
   los tests originales aplicables sin alterar sus expectativas; registrar
   cualquier limitación del plugin.
5. **Instalación y continuidad:** instalar solo tras aprobar, repetir desde
   consumidor nuevo, demostrar carga del plugin y libpng correctos, auditar
   manifiesto/arquitectura/hashes previos. Repetir CMake/gate y publicar
   metadatos. Después siguen KDDockWidgets, FFmpeg y MoltenVK.
