# Perfil lógico v1

Implementación de referencia: `tools/pipeline/profile.py`. Es un formato propio de identificación, no un formato PS2 ni SH3P.

F00.05 · RF01.01 · [Fuentes e instancia canónica](../docs/compatibility/sources.md). La versión de esquema sigue siendo 1: se precisa el contrato y sus pruebas, sin migrar ni modificar el perfil europeo.

Campos requeridos: `schema_version` = entero 1; `id` minúsculo `[a-z0-9][a-z0-9_-]{0,63}`; `platform` = `ps2` o `synthetic`; `region`, `revision`, `serial`, `language`, `extractor_version` como strings no vacíos de hasta 256 caracteres; `capabilities` como lista sin duplicados de hasta 128 strings no vacíos de hasta 128 caracteres; `files` con entre 1 y 10000 entradas.

| Campo | Significado y límite de interpretación |
|---|---|
| `schema_version` | Versión del contrato propio; booleanos no equivalen a entero 1 |
| `id` | Identificador estable del perfil de origen, no del build ni del hito de campaña |
| `platform` | `ps2` para originales; `synthetic` exclusivamente para datos propios de prueba |
| `region`, `serial`, `revision` | Identidad de la copia con evidencia; revisión `unverified` mientras no esté contrastada |
| `language` | Idioma(s) catalogados del origen; no selecciona el idioma de la alpha ni prueba textos durante ejecución |
| `capabilities` | Capacidades sustentadas por pruebas; lista vacía válida; se rechazan duplicados y strings vacíos o de solo espacios |
| `extractor_version` | Extractor adoptado o marcador explícito de ausencia; no confundir con la versión del inspector del informe |
| `files` | Manifiesto de archivos requeridos; `path`, `size`, `sha256` obligatorios en cada entrada |

Omitir un campo obligatorio de la cabecera o usar un tipo/valor inválido devuelve `INVALID_PROFILE`; una ruta de archivo inválida devuelve `INVALID_PATH` y una versión distinta de 1 devuelve `UNSUPPORTED_SCHEMA`. Campos adicionales se ignoran en la versión 1 y no habilitan capacidades. El contrato no crea archivos ni selecciona ubicaciones privadas.

Cada archivo declara `path` relativo POSIX, sin segmentos vacíos, `.`/`..`, barras inversas, dos puntos o controles; máximo 1024 caracteres. `size` es un entero no booleano entre 0 y 2^63-1. `sha256` tiene exactamente 64 dígitos hexadecimales minúsculos. No se admiten rutas duplicadas, incluso si solo cambia la capitalización. El archivo JSON completo tiene un máximo de 1 MiB.

Los límites son defensas del perfil de herramientas, no límites conocidos del juego. JSON que no es objeto o tiene versión incompatible se rechaza. Identificar todos los archivos con éxito no ejecuta extracción. Los hashes externos de referencia no se usan como sustituto de inspeccionar los originales locales.

El lector `load_profile` aplica el límite de 1 MiB antes de interpretar JSON. `verify_profile` depende del puerto `FileInspector`: compara tamaño y SHA-256 de cada entrada y detiene la verificación ante el primer fallo. `LocalFileInspector` e `IsoImage` son adaptadores de lectura, con pruebas de contrato. El verificador de directorios comprueba los archivos declarados; el CLI ISO comprueba además que la lista coincida con el catálogo completo del disco. No se atribuye esa comprobación de completitud al verificador de una carpeta arbitraria.

El fixture sintético tiene hashes calculados a partir de un texto creado por el proyecto. No se proporciona un perfil PS2 con hashes inventados.

Para una identidad observada, `revision` y `language` pueden contener el literal `unverified`; `capabilities` permanece vacío y no se autoriza extracción específica. El informe ISO registra `system_cnf_ver` por separado: no se transforma automáticamente en revisión comercial. `--profile` comprueba hashes y catálogo completo contra una referencia local; no acredita autenticidad externa.

`--catalog` permite completar revisión e idiomas tras comparar la imagen completa con una [referencia externa fijada](catalog-reference-v1.md). Para listas multilingües, `language` usa códigos de dos letras separados por comas. El informe conserva la procedencia y `language_runtime_verified=false`; la lista no representa una selección de idioma del port.

Instancia canónica actual: `reports/local/europe-profile-identified.json`; 113 entradas, capacidades `[]`, `extractor_version=none-inspection-only-v1`. Su SHA-256 y procedencia se conservan en el inventario SRC04. Está ignorada, no se duplica en `tests/fixtures` y no se rellena con offsets de otra revisión.
