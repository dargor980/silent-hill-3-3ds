# Referencia de catálogo v1

Contrato propio de herramientas host; no es el formato DAT de Redump. La referencia es JSON de metadatos públicos revisados y fijados en el repositorio. El inspector no descarga URLs ni interpreta campos como comandos. Implementación: `tools/pipeline/catalog.py` y `--catalog` en `tools.pipeline.inspect_iso`.

| Campo | Contrato |
|---|---|
| `schema_version` | Entero 1, no booleano |
| `id` | `[a-z0-9][a-z0-9_-]{0,63}` |
| `source_url` | URL HTTPS con autoridad; procedencia documental, nunca se visita desde el inspector |
| `retrieved_on` | Fecha ISO válida |
| `serial` | `[A-Z]{4}-[0-9]{5}` |
| `region`, `revision` | Texto no vacío, hasta 256 caracteres |
| `languages` | 1–32 códigos de dos letras minúsculas, sin duplicados |
| `image.size` | Entero 1..2^63−1, no booleano |
| `image.sha1`, `image.md5`, `image.crc32` | Hexadecimal minúsculo de 40, 32 y 8 caracteres, respectivamente |

El JSON de entrada tiene un máximo de 64 KiB. Los campos de texto tienen un máximo de 256 caracteres. Los campos adicionales se ignoran. Los hashes externos están en `image` de la referencia; los calculados localmente están en `image` del informe, incluido SHA-256, que no se atribuye al catálogo.

Para adoptar metadatos deben coincidir tamaño, SHA-1, MD5, CRC-32, serial, versión de arranque y región declarada cuando exista. Si cualquiera difiere, se produce `CATALOG_MISMATCH` y no se genera un informe aceptado. Los algoritmos antiguos sirven para comparar con el catálogo; no sustituyen los SHA-256 del manifiesto propio.

Cuando la comparación pasa, `profile.revision` recibe la versión del catálogo y `profile.language` sus códigos separados por comas, en el orden de la referencia. `catalog.evidence=complete_image_checksum_match` declara la evidencia; `catalog.language_runtime_verified=false` conserva el límite. Las capacidades permanecen vacías y la compatibilidad del port sin verificar. Si se aporta además un perfil previo, sus archivos deben coincidir y sus metadatos conocidos no pueden contradecir el catálogo.

La revisión de un catálogo es una identificación de contenido; no identifica la caja, disco físico, tirada o reimpresión cuando varias ediciones comparten bytes. Una lista de idiomas identificada por catálogo no acredita traducciones probadas en el port.
