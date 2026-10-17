# Datos privados y procedencia

Versión 1.1 · 2026-10-16 · F00.05. [Inventario de fuentes](compatibility/sources.md); [contrato del perfil](../schemas/game-profile-v1.md). Los datos del perfil identifican entradas y no anuncian compatibilidad de gameplay.

El usuario indicó el 2026-10-16 que su ISO europea está en `binaries`. Se conserva allí como **entrada local privada ignorada por Git**, sin moverla ni modificarla. Esta decisión actualiza la regla inicial del PDF que exigía todos los originales fuera del checkout. Solo se admite esa excepción para ISO: extracciones, conversiones, dumps y savestates siguen en un directorio privado externo.

`binaries/.gitignore` contiene `*` y `!.gitignore`; el `.gitignore` raíz también excluye su contenido. No añadir originales con `git add -f`. `tools.qa.check_repository` compone el escaneo de `tools.qa.custody`: permite una ISO local únicamente si es archivo regular, Git la reconoce como ignorada y no es un enlace simbólico. Rechaza otros archivos de esa bandeja salvo `binaries/.gitignore`, cualquier contenido versionado de `binaries` salvo ese archivo, binarios privados/generados versionados incluso en `build`, y reportes privados versionados en `reports/local`.

## Ubicaciones permitidas

| Contenido | Ubicación | Regla de aceptación |
|---|---|---|
| ISO original | Externa o excepción local `binaries` | Regular y sin enlaces; si es local, ignorada por Git; nunca modificar sus bytes |
| Perfil completo e informes privados de identificación | `reports/local` o directorio privado externo | Dentro del repositorio, solo metadatos regulares ignorados con extensión `.json`, `.txt`, `.md`, `.csv` o `.xml`; no originales ni exportaciones |
| Extracciones, conversiones, savestates, dumps y capturas del juego | Directorio privado externo pasado explícitamente a la herramienta | No puede ser el checkout, un descendiente ni un ancestro suyo; conservar trazabilidad de origen/receta |
| Fixtures propios | Texto/JSON en `tests/fixtures/synthetic`; binarios generados en temporales de tests | Procedencia propia comprobable; no relabelar contenido del juego como sintético; el nombre de carpeta no exime del escaneo |
| Builds y resultados de tests sintéticos | `build` | Generados, no versionados; binarios de desarrollo permitidos `.bin`, `.cia`, `.3dsx`, `.elf`, `.smdh`; una extensión permitida no convierte un original en build propio |
| Resúmenes de compatibilidad y fuentes públicas | `docs/compatibility` | Metadatos mínimos revisados, sin recursos ni dumps; fuentes e incertidumbres visibles |

F02.05 usó la raíz privada externa indicada por el usuario, registrada en `reports/local/f02-05-extraction.json`. Cada ejecución sigue exigiendo ese argumento explícito; no se crea una raíz dentro del repositorio por omisión. La excepción de informes permite metadatos de identificación, no paquetes convertidos ni bytes exportados con extensión de texto.

## Controles implementados

El escaneo comprueba el índice Git y los metadatos `lstat` de entradas locales, incluidos archivos ignorados; no abre el contenido de la ISO. Rechaza enlaces de archivos/directorios —también rotos— y entradas especiales como FIFO en el árbol inspeccionado. Si Git o el recorrido no se pueden comprobar, devuelve un error. Las extensiones detectadas son `.iso`, `.mfa`, `.afs`, `.irx`, `.img`, `.bin`, `.p2s`, `.sav`, `.cia`, `.3dsx`, `.elf` y `.smdh`, sin distinguir mayúsculas.

Las únicas rutas de entorno excluidas del recorrido son `.git`, `.venv`, `.pytest_cache`, `.ruff_cache` y `build/linux-venv`, relativas a la raíz. El índice Git se revisa aunque los archivos estén en esas rutas. Una subcarpeta llamada `build`, `.git` o `.venv` en otra ubicación no obtiene una excepción. En `build` se inspeccionan los datos y se rechazan, por ejemplo, ISO/MFA/AFS; solo se permite el conjunto de binarios de desarrollo indicado en la tabla. Los entornos excluidos tampoco son ubicaciones autorizadas para originales.

`tools.pipeline.inspect_iso` abre un archivo regular en modo `rb`, recorre ISO9660, calcula hashes por bloques y comprueba identidad/tamaño/mtime/ctime antes de aceptar la lectura. Escribe solo un JSON nuevo en el destino explícito, sin exportar bytes de los archivos del disco. La región es declarada por el operador; serial, modo de vídeo y `VER` proceden de `SYSTEM.CNF`. La revisión comercial y los idiomas no se infieren del nombre del archivo. El informe de esta copia se guarda en `reports/local/europe-disc.json`; el perfil completo y la segunda verificación también permanecen ignorados en esa carpeta.

La herramienta de directorios `tools.pipeline.verify` sigue exigiendo extracciones PS2 externas al repositorio. Rechaza perfiles inválidos, diferencias de tamaño/hash, rutas absolutas/traversal, la raíz de datos recibida si es un enlace, enlaces en las entradas bajo esa raíz y raíces PS2 que coincidan con, contengan o estén dentro del repositorio. `synthetic` identifica únicamente fixtures propios; no permite reclasificar originales.

La CI utiliza ISOs pequeñas generadas en directorios temporales a partir de bytes propios. No necesita la ISO privada ni publica `binaries` o `reports/local`; los artefactos del workflow tienen rutas explícitas. El job `quality` ya ejecuta el escaneo y sus regresiones, por lo que adopta estas reglas sin añadir otro workflow. La ejecución remota permanece pendiente.

El control por ubicación/extensión no reconoce todos los originales renombrados ni inspecciona el contenido de un JSON: la revisión de contenido/procedencia permanece como condición de publicación. Tampoco garantiza protección frente a modificaciones concurrentes del filesystem durante el escaneo; la custodia se verifica en un árbol estable y se revisa el archivo final antes de publicar. No se han enviado originales a servicios externos.

La opción `--catalog` usa una referencia pública JSON fijada en `docs/compatibility/catalogs/`, sin acceder a la red. Los hashes se calculan localmente. El cierre de identificación está en `reports/local/europe-disc-catalog.json` y el perfil actualizado en `reports/local/europe-profile-identified.json`; ambos siguen ignorados. Solo se consultaron metadatos públicos durante la investigación, sin enviar la imagen.

F02.01 añade `tools.inspectors.catalog`: exige hash completo previo y perfil, verifica todos los archivos y produce únicamente metadatos de inventario. Los catálogos nuevos permanecen en `reports/local`, sin prefijos binarios, tablas internas ni payloads exportados. Los offsets son posiciones de archivos dentro de la ISO; no son offsets MFA interpretados. Esta inspección no necesita raíz de extracción porque no exporta originales; la raíz externa continúa siendo obligatoria antes de cualquier exportación en F02.02 y tareas posteriores. [Evidencia](execution/f02-01-inventory.md).

## Verificación y tratamiento de un rechazo

```sh
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy .venv/bin/python -m tools.pipeline.verify \
  --profile tests/fixtures/synthetic/game-profile.json \
  --data-root tests/fixtures/synthetic
```

Ante un rechazo, detener la operación dependiente y registrar la causa. Revisar ubicación, exclusión Git o fuente; no borrar, mover ni sobrescribir originales automáticamente ni sustituir el fallo por éxito. Un archivo añadido por fuerza debe retirarse del índice preservando sus bytes antes de continuar; esta tarea solo comprueba el índice y no lo modifica. Las pruebas de casos inválidos usan repositorios temporales y datos propios.

F02.02 incorpora `tools.inspectors.mfa_probe`: aplica la misma verificación de identidad y solo escribe estadísticas/rangos estructurales. Sus dos informes privados bajo `reports/local` omiten nombres internos, prefijos y payloads; tampoco contienen rutas del host. El sondeo no requiere raíz externa ni realiza extracción. La revisión del candidato conservó fuentes externas en un temporal fuera del checkout; dentro solo hay metadatos de procedencia y código propio. [Evidencia](execution/f02-02-mfa-candidate.md). La obligación de raíz externa sigue vigente antes de exportar originales.

F02.03 mantiene la inspección sin exportación. Los informes v2 indican la selección fija B8/D8 y, ante un nombre no admitido, solo posición/longitud, conteos de bytes y resultados booleanos de codecs. No incluyen cadenas crudas ni su codificación en hexadecimal/base64. Los nuevos metadatos están ignorados bajo `reports/local`; no reemplazan evidencia F02.02. [Resultado y límites](execution/f02-03-container-variants.md).

F02.04 incorpora el catálogo interno: permite nombres ASCII de recursos como metadatos únicamente en los JSON privados ignorados de `reports/local`, junto con IDs, offsets, tamaños y hashes. No guarda payloads ni tablas crudas y no crea rutas a partir de nombres internos. La salida pública/CI contiene resúmenes y fixtures propios; XBG0 conserva solo diagnóstico acotado. Selección y dos catálogos se comprobaron ignorados con el árbol estable. [Evidencia](execution/f02-04-asset-catalog.md). Una futura exportación por ID también requiere raíz privada externa: cambiar el nombre no modifica la custodia de los bytes.

F02.05 exporta únicamente a una sesión nueva en raíz externa existente, recorrida sin enlaces y anclada a descriptores POSIX. Archivos por ID con modo 0600, directorios nuevos 0700, sin sobrescribir ni borrar resultados anteriores. Relee cada copia y el par; recibos verificados se publican exclusivamente después del cierre estable. Los archivos de preparación de recibo son metadatos privados, no aceptación. Ausencia de verified.json indica sesión incompleta/fallida. El perfil de inspección permanece intacto; el recibo registra extractor v1. [Resultado y garantías](execution/f02-05-repeatable-extraction.md).

F02.06 usa exclusivamente fixtures y temporales propios para mutaciones e interrupciones. No escribió originales; comprobó los hashes de recibos F02.05 sin presentarlo como nueva relectura de payloads. Los fallos de transferencia a stream o limpieza ya conservan propiedad/error primario; tras un recibo final publicado, un error de cierre de directorios produce estado verificado con advertencia explícita, no un rechazo contradictorio. No se reintentan cierres ambiguos ni se borran parciales. [Evidencia y límites](execution/f02-06-extraction-hardening.md).

F02.07 relee las dos copias externas sin crear ni modificar payloads. Valida el conjunto exacto por ID, regularidad sin enlaces, tamaño/hash completo y estabilidad antes de devolver rangos ≤4096 bytes. Los inventarios guardan únicamente metadatos: hashes/longitudes de los primeros 64 bytes e indicios de sufijo sin validar. No almacenan prefijos crudos, hex/base64 ni texto del payload. El staging exclusivo termina en `.pending.json`, permitido como metadato ignorado; el archivo final se enlaza tras la escritura completa y el cierre del lector. La raíz/copia se exige explícitamente y nunca se deriva de nombres internos. [Evidencia parcial y límites](execution/f02-07-slice-corpus.md).

El sondeo de cámara F02.07 usa tres metadatos fijados por SHA-256 (catálogo, recibo e inventario) y relee solo los 285 seleccionados por sufijo en cada copia, con verificación completa antes de analizar. Guarda conteos, discrepancias respecto a una referencia de otro juego y hashes/longitudes de colas; no exporta registros, coordenadas, cadenas ni payloads. Las fuentes públicas se consultaron sin enviar datos privados; solo sus referencias/hashes se incorporan al repo. [Resultado y alcance](execution/f02-07-camera-probe.md).

La búsqueda estática `camera-consumer-eu` relee la ISO completa para SHA-256 y verifica individualmente SYSTEM.CNF y su ejecutable; no revisa individualmente otros 111 miembros ni las extracciones. Lee rangos <=4096 y conserva solo metadatos privados (segmentos, sitios, destinos y hashes), sin desensamblado ni bytes del juego. Reutiliza publicación exclusiva después del cierre estable. Dos informes idénticos, sin nuevas copias de originales; [alcance](execution/f02-07-camera-consumer.md).

`camera-pointer-origin-eu` fija y regenera la evidencia del consumidor desde la ISO verificada, luego inspecciona dos ventanas de 888/1836 bytes y referencias de segmentos respaldados. Los informes privados guardan posiciones, categorías y hashes; no instrucciones, bytes o constantes originales. No se modifica ni relee la extracción privada; el hash completo de la ISO y hashes individuales de BOOT2/ejecutable se verifican de nuevo. [Alcance y resultados](execution/f02-07-camera-pointer.md).

`camera-caller-boundary-eu` fija ambas copias del sondeo anterior y regenera su cadena desde la ISO. Inspecciona tres fronteras con ventanas acotadas y publica solo metadatos/hashes, incluido un plan privado de observación marcado no ejecutado. No captura registros reales, memoria, savestates o instrucciones, ni escribe nuevos payloads. Los futuros dumps requerirán la raíz privada externa y un contrato de sesión/identidad. [Resultado](execution/f02-07-camera-boundary.md).

`camera-runtime-observation-plan-eu` publica dos planes idénticos con puntos/rangos/hashes, sin registros reales o bytes. El contrato de captura exige raíz externa, archivos privados sin enlaces, lecturas limitadas y cierre estable. PCSX2 v2.8.2 usa una carpeta dentro de la raíz privada autorizada mediante el acceso PCSX2 SH3; BIOS, snapshots, savestates, logs y futuras capturas permanecen fuera del checkout. [BIOS principal configurada y arranque comprobado por logs](execution/f02-07-ps2-boot.md); la captura de cámara sigue pendiente. El recibo omite valores GPR/direcciones de datos y no autentica ejecución. [Protocolo](compatibility/camera-runtime-capture.md), [resultado](execution/f02-07-camera-observation.md).
