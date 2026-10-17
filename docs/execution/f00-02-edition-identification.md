# F00.02: identificación de la edición europea

Estado: **completada para identificación de la copia**. Fecha: 2026-10-16. Responsable: agente de desarrollo. Criterios: RF01.01/RF01.02, T01; regresiones RF01.03/RNF06.04 y normas RNF07/RNF11. Destino del proyecto: New Nintendo 2DS XL, Homebrew Launcher; esta ejecución es host y no certifica consola.

## Resultado y fundamento

La imagen local coincide en tamaño y todos los checksums publicados con [Redump, registro 1064](https://redump.info/disc/1064). Ese registro identifica contenido europeo SLES-51434, versión 1.02 y los idiomas inglés, francés, alemán, español e italiano. El perfil se completa por esa coincidencia de la imagen entera; `VER=1.02` y el nombre del archivo por sí solos no habrían sido suficientes.

| Dato | Valor local | Comparación |
|---|---|---|
| Tamaño | 3.586.785.280 bytes | Coincide |
| CRC-32 | `121f94a6` | Coincide |
| MD5 | `3914c8a0cf593276a55c22db090650b5` | Coincide |
| SHA-1 | `aecd86c7b15446e5061afb9ea58e3d04f3a2649a` | Coincide |
| SHA-256 | `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` | Medición local; conservada desde la inspección previa |
| Archivos requeridos | 113 | Todos coinciden con el manifiesto local previo |

El serial y la versión se contrastan también con `SYSTEM.CNF`. El perfil mantiene el ID `ps2-sles-51434-9a94b95e777dae42`; cambia `revision` de `unverified` a `1.02` y `language` a `en,fr,de,es,it`. Los hashes y tamaños de sus archivos no cambian. Originales abiertos únicamente en lectura, sin montar la imagen, exportar recursos ni ejecutar contenido del disco.

La lista de idiomas tiene evidencia de catálogo ligada al contenido completo. Se cierra Q02 a ese nivel; la selección del idioma del port pertenece a Q03/F00.04 y la validación de textos/interfaz durante ejecución sigue en F10/F13. No se ha probado el menú de idiomas ni una campaña localmente. La tirada comercial concreta no se deduce cuando varias tiradas comparten contenido; no es necesaria para identificar los bytes de este perfil.

## Implementación y evidencia reproducible

Referencia pública fijada: [redump-1064.json](../compatibility/catalogs/redump-1064.json), con URL y fecha de consulta. [Contrato](../../schemas/catalog-reference-v1.md). La herramienta no necesita acceso a red; solo recibe el JSON local revisado.

```sh
.venv/bin/python -m tools.pipeline.inspect_iso \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --region Europe \
  --profile reports/local/europe-profile.json \
  --catalog docs/compatibility/catalogs/redump-1064.json \
  --output reports/local/europe-disc-catalog.json
```

Esperado y observado: `status=matched_catalog`, 113 archivos, `extraction=not_performed`. El destino debe ser nuevo; los informes anteriores se conservan. El perfil completo actualizado está en `reports/local/europe-profile-identified.json`. Esos archivos son locales e ignorados por Git. El resumen publicable está en este informe y en [target.json](../compatibility/target.json).

Una segunda ejecución con el perfil actualizado produjo `reports/local/europe-disc-catalog-recheck.json`: coincide íntegramente con el primer informe, incluidos hashes de imagen, los 113 archivos y metadatos identificados.

Separación SOLID: `hashing.py` calcula huellas sobre un stream acotado; `IsoImage` controla acceso y estabilidad del archivo; `catalog.py` valida y compara metadatos sin filesystem ni red; `inspect_iso.py` compone los componentes y escribe el informe. La política no contiene nombres ni hashes específicos de Silent Hill 3; el registro es un dato reemplazable.

## Validación y cierre

- Unitarias: vector conocido `abc`, lectura por bloques, tamaños inconsistentes, catálogo inválido y desacuerdo de cada checksum, serial, región o versión.
- Integración: ISO sintética completa, aplicación de metadatos tras coincidencia, perfil previo, contradicción de metadatos y disco modificado con el mismo serial. Un fallo no crea un informe aceptado.
- Prueba local: comparación completa de la ISO y verificación del manifiesto de 113 archivos. Se conserva SHA-256 junto a los checksums usados por el catálogo.

La suite CI existente incorpora estas pruebas automáticamente y sigue usando solo datos sintéticos. No se añaden dependencias. La ejecución remota permanece pendiente; los tests y la inspección descritos se ejecutaron localmente. No cambió el runtime C++/3DS, por lo que esta entrega no repite ni amplía sus resultados anteriores.

F00.02 queda cerrada. G00 permanece abierta: todavía deben completarse alcance, custodia/procedencia y sus evidencias de cierre según el backlog. La siguiente tarea en orden es **F00.04 — Delimitar contenido por hito**; F00.03 ya estaba completada.

Resultado final local: **144/144 pruebas pasan**; Ruff/formato y comprobaciones de arquitectura, custodia y trazabilidad pasan. Cobertura Python: 530/555 líneas (95.50 %) y 213/226 ramas (94.25 %), con umbral de 80 % en ambas. `catalog.py` y `hashing.py` tienen 100 % de líneas y ramas. Entorno: Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0. Reportes locales en `build/pytest.xml` y `build/python-coverage.{json,xml}`.

Fuentes sin commit: manifiesto `build/f00-02-source-manifest.json`, SHA-256 `6ca891db2f93d4e2f9a069eef0fcb211ed737e3f65a0971a61ea535505550633`. Incluye herramientas, tests, referencia pública y contrato del catálogo; no incluye originales.
