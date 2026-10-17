# F02.01 — catálogo de archivos y contenedores

Fecha: **2026-10-16** (America/Santiago). **Completada para los archivos ISO9660 del perfil europeo.** Dos inspecciones completas produjeron el mismo catálogo de **113 archivos**. No se extrajeron recursos, no se ejecutó código original y no se cierra G02. [Ticket detallado](../specs/sh3-3ds/tasks/F02.md#f0201) y [contrato EARS I01-I08](../../schemas/source-inventory-v1.md).

## Resultado observado

Se volvió a calcular el SHA-256 de toda la imagen en cada ejecución y se compararon todos los tamaños/hashes del perfil canónico antes de clasificar. Imagen: 3.586.785.280 bytes; SHA-256 `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`. Perfil: `ps2-sles-51434-9a94b95e777dae42`, SLES-51434/PAL, revisión 1.02, idiomas en/fr/de/es/it. El perfil conserva su SHA-256 `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9` y capacidades vacías.

| Clasificación | Archivos | Alcance de evidencia |
|---|---:|---|
| Cabecera ELF32 little-endian MIPS | 12 | Cabecera comprobada; ABI/secciones/relocaciones y ejecución no validadas |
| Candidato AFS | 35 | Solo firma inicial; tablas y recursos internos pendientes |
| Configuración de arranque PS2 | 1 | Parseo válido y relación BOOT2 con el ejecutable identificado |
| Tipo desconocido | 65 | 62 con extensión `.mfa`, uno `.dir`, uno `.img` y uno `.bin`; extensión no acredita formato |

Cada entrada conserva ID estable, ruta, origen/perfil, contenedor padre ISO, offset en bytes, tamaño, SHA-256, pista de extensión, clasificación/evidencia, dependencias y soporte. La única dependencia registrada es la relación de arranque; se marca parcial. Las otras 112 listas vacías llevan estado `not_inspected`, no ausencia comprobada de dependencias. Todos los archivos tienen `support=inventory_only`.

Los metadatos completos permanecen privados e ignorados:

- `reports/local/f02-01-inventory.json`.
- `reports/local/f02-01-inventory-repeat.json`.

Ambos archivos tienen **96.660 bytes**, son idénticos byte por byte y comparten SHA-256 **`fad85c1604f223c7c7b28126b41056161a87f60596836c5c9da401057f8da1da`**. No contienen prefijos crudos, payloads ni rutas absolutas del host. La ISO permanece en su ubicación original de lectura. La excepción de metadatos de `reports/local` permite este trabajo sin configurar una raíz de extracción; no se ha creado esa raíz.

## Implementación y SOLID

`tools.inspectors.signatures` clasifica bytes acotados; `inventory` verifica y compone un puerto lector; `IsoImage` implementa lectura/hash/localización/estabilidad; `catalog` compone CLI y escritura exclusiva. Se reutilizan el lector ISO9660, hash por bloques, verificador de perfiles y parser de BOOT2 existentes. No se añade dependencia ni se adopta código de un extractor.

El lector expone offsets de extents contiguos y rechaza atributos extendidos/interleave, además de multi-extent y rangos inválidos. El catálogo exige conjunto exacto de archivos y verifica todos sus hashes antes de cualquier clasificación. Los prefijos se limitan a 4096 bytes por entrada. El ID incluye imagen, perfil y ruta; el orden es estable y se omiten marcas de tiempo del documento determinista. La salida se escribe después de que el context manager comprueba estabilidad de la imagen y nunca reemplaza un informe existente.

La identificación ELF sigue los campos documentados por [ELF gABI](https://refspecs.linuxfoundation.org/elf/gabi4%2B/ch4.eheader.html). Para el candidato AFS se consultó la [documentación del autor de cri-afs](https://github.com/soyjxck/cri-afs), exclusivamente como referencia de la firma inicial; no se instaló ni incorporó su biblioteca. Las comprobaciones concretas y sus límites están en el contrato. MFA sigue sin regla de reconocimiento ni offsets interpretados.

## Batería y automatización

**357/357 pruebas Python aprobadas**, incluyendo **62 nuevas**. Los primeros 99 casos focalizados de inventario/ISO pasaron; después se añadieron cinco casos de fallos de lectura y prefijo acotado antes de ejecutar la batería completa.

- Casos normales: orden invertido con resultado idéntico; IDs distintos para rutas con contenido idéntico; dependencia BOOT2; sustitución lector memoria/ISO; offsets contrastados con los bytes sintéticos originales; dos ejecuciones CLI iguales.
- Casos de error: extensión engañosa, ELF de otra clase/encoding/máquina/versión, firmas truncadas, prefijo corto/excesivo, vacío, perfil parcial/adicional/duplicado, hash/tamaño alterado, rango inválido, ausencia de ejecutable, fallos de lectura y cambio de ISO antes de cerrar. Ninguno produce un catálogo aceptado.
- Custodia: destino existente preservado, enlace de salida rechazado, JSON sin payload ni ruta absoluta; ISO y reportes reales confirmados como ignorados por Git. La CI usa exclusivamente fixtures propios en temporales.

Cobertura Python: **824/853 líneas (96,60 %)** y **332/348 ramas (95,40 %)**. `inventory.py` y `signatures.py` alcanzan 100 % de líneas y ramas. Gate independiente ≥80 % aprobado; Ruff check/format y contratos de arquitectura/custodia/specs aprobados.

Evidencia sintética local: `build/f02-01/python-tests.log`, `pytest.xml`, `python-coverage.{json,xml}`, `quality.log` y `verification.json`. Herramientas: Python 3.14.6, pytest 9.1.1 y pycdlib 1.22.0 fijado. El job `quality` existente descubre las pruebas nuevas y aplica cobertura/custodia; no necesita rutas privadas ni otro job. No se ejecutó Actions remotamente. El runtime C++/ARM no cambió, por lo que sus 47 casos y builds de F01.08 conservan su evidencia anterior y no se repitieron aquí.

## Reproducción y cierre

Desde la raíz del proyecto, con un destino nuevo:

```sh
rtk proxy .venv/bin/python -m tools.inspectors.catalog \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --profile reports/local/europe-profile-identified.json \
  --image-sha256 9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91 \
  --output reports/local/f02-01-inventory.json
```

La repetición utilizó `f02-01-inventory-repeat.json`. Resultado observado en ambas: `status=catalogued`, 113 archivos, `extraction=not_performed`, `nested_inventory=not_performed`. Los comandos y el manifiesto de fuentes de esta entrega están bajo `build/f02-01`; los cambios todavía no están en un commit.

I01-I08 quedan cubiertos por pruebas sintéticas y los dos catálogos reales del nivel ISO. **F02.01 se cierra con ese alcance**. Las entradas internas y dependencias de contenedores pertenecen a F02.02-F02.04; extracción repetible, endurecimiento y corpus pertenecen a F02.05-F02.07. **Q05/G02 siguen abiertos**, al igual que las pruebas físicas G01.

Siguiente tarea: **F02.02 — evaluar extractor MFA candidato**. Comienza con revisión de procedencia y pruebas sintéticas de la herramienta o alternativa; antes de exportar recursos originales necesita la raíz privada externa explícita. Los 62 nombres `.mfa` del catálogo son entradas de investigación, no 62 formatos ya soportados.

## Identidad de fuentes

`build/f02-01/source-manifest.json`: 30 archivos de código, pruebas, locks, CI y documentación; SHA-256 `c35751f86e310f8e2abfe206a630d7df3e2b987a1354af45442f928479ae1b84`. Se excluye este informe para evitar autorreferencia y no se incluyen originales ni los catálogos privados. Los hashes/tamaños del perfil y de los dos informes se verificaron en esta ejecución.
