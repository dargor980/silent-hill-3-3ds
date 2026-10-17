# Inventario de origen v1 — F02.01

Requisitos padre RF01.02, RF02.01, RNF07.06-RNF07.09 y RNF11.05-RNF11.09. Alcance de esta instancia: archivos del nivel ISO9660 del perfil identificado; no enumera entradas internas de MFA/AFS ni exporta recursos.

## Criterios EARS

- **I01** WHEN se solicita el catálogo THEN la herramienta SHALL verificar SHA-256 de la imagen completa, conjunto exacto de rutas y todos los tamaños/hashes del perfil antes de clasificar contenido.
- **I02** WHEN una entrada se cataloga THEN el informe SHALL registrar ID estable, ruta, origen/perfil, contenedor padre, offset en bytes desde el inicio de la ISO, tamaño, SHA-256, tipo/evidencia y estados de dependencias y soporte.
- **I03** IF solo se conoce la extensión THEN el tipo SHALL permanecer desconocido; la extensión SHALL registrarse únicamente como pista.
- **I04** WHEN una firma se reconoce THEN el informe SHALL distinguir firma candidata de cabecera comprobada y SHALL no atribuir extracción, decodificación ni compatibilidad de runtime.
- **I05** WHEN se repite la operación con la misma imagen/perfil/herramienta THEN las entradas ordenadas y sus IDs SHALL ser idénticos; fechas y rutas locales SHALL no participar en el documento determinista.
- **I06** IF falla una lectura, el perfil es parcial, un rango sale de la imagen o esta cambia durante la operación THEN la herramienta SHALL rechazar el catálogo antes de escribir un resultado aceptado.
- **I07** WHEN se escribe evidencia THEN la salida SHALL ser un JSON nuevo de metadatos, sin prefijos crudos ni contenido exportado; SHALL no sobrescribir evidencia previa ni modificar la ISO.
- **I08** WHILE una dependencia o contenido interno no se ha inspeccionado THEN su estado SHALL permanecer explícitamente pendiente; una lista vacía SHALL no significar ausencia comprobada de dependencias.

## Diseño y contrato JSON

`tools.inspectors.signatures` clasifica prefijos puros; `tools.inspectors.inventory` coordina un puerto lector sin filesystem ni pycdlib; `IsoImage` implementa lectura/hash/offset ISO9660 y estabilidad; `tools.inspectors.catalog` compone CLI y escritura exclusiva. Reutilizar el adaptador y verificador de F00 evita dos implementaciones de ISO o hashing. No se incorpora un extractor de terceros.

Documento: `schema_version=1`, herramienta/versión/pycdlib, `source` (ID `iso:<sha256>`, size, sha256, perfil y su metadata), `scope=iso_files_only`, `entries`, resumen por tipo/reconocimiento, `extraction=not_performed`, `nested_inventory=not_performed`, `capabilities=[]`.

Cada entrada contiene `id`, `path`, `origin` (perfil e imagen), `container_id`, `offset`, `size`, `sha256`, `extension_hint`, `classification`, `dependencies` y `support=inventory_only`. Offset es únicamente la ubicación del archivo en la ISO; no es un offset dentro de un MFA. Se admiten solo extents contiguos sin atributos extendidos/interleave; variantes no soportadas se rechazan.

ID: `entry:` seguido del SHA-256 de UTF-8 de `sh3-inventory-v1`, SHA-256 completo de imagen, ID de perfil y ruta ISO exacta, separados por NUL. Dos rutas con bytes iguales conservan IDs diferentes. Cambiar imagen, perfil o ruta cambia ID. El orden es lexicográfico por ruta. El hash identifica bytes, no procedencia legal ni formato.

Clasificación inicial, con máximo 4096 bytes leídos por entrada después de verificar el perfil:

| Regla | Evidencia exigida | Resultado y límite |
|---|---|---|
| `ps2-boot-v1` | SYSTEM.CNF completo, parseo ASCII/BOOT2/VER/VMODE válido y ejecutable presente | Configuración PS2; única dependencia conocida hacia el ejecutable; resto no inspeccionado |
| `elf32-le-mips-v1` | Magic ELF, clase/endianness/versión, 52 bytes, máquina MIPS, versión del objeto y tamaño de cabecera | Cabecera ELF32 LE MIPS reconocida; no valida secciones, relocaciones, ABI PS2 ni ejecución |
| `afs-magic-v1` | Magic AFS con terminador NUL y al menos ocho bytes | Candidato AFS por firma; no interpreta tabla, offsets, nombres ni payloads |
| `unknown-v1` | Ninguna regla anterior | Tipo desconocido; motivo distingue vacío, firma/cabecera incompleta o variante no soportada |

Una entrada `.mfa` permanece desconocida hasta F02.02; no se deduce formato ni dependencias de su nombre. Una firma AFS en un archivo con otra extensión produce la misma clasificación candidata. `dependencies.status` es `partial` para BOOT2 o `not_inspected` para el resto; `known=[]` nunca certifica que no haya dependencias.

Fuentes de los hechos de formato consultadas el 2026-10-16: [ELF gABI](https://refspecs.linuxfoundation.org/elf/gabi4%2B/ch4.eheader.html), que define magic, clase, encoding, máquina y tamaño de cabecera; [documentación del autor de cri-afs](https://github.com/soyjxck/cri-afs), usada únicamente para la firma inicial y el mínimo de cabecera, sin adoptar su biblioteca ni copiar su código. El resto son límites/políticas propios de esta instancia, no una especificación completa de formatos originales. La regla de configuración reutiliza F00.

## Errores y pruebas

Los errores tipados del perfil/ISO se conservan; la aplicación añade identidad de imagen inválida/no coincidente, conjunto de archivos distinto, offset inválido y prefijo incompleto. El reporte se escribe solo después del cierre estable de la imagen, con creación exclusiva. La CLI imprime únicamente estado, conteos y códigos; el informe completo queda privado.

Fixtures propios: ISO en memoria/temporal, extensión engañosa, firma truncada, ELF de otra clase/máquina, archivos vacíos, rutas distintas con igual contenido, orden de enumeración invertido, perfil incompleto, hashes/tamaños alterados, rangos fuera de imagen, cambio durante lectura, salida existente y fallos de I/O. Comparar el puerto en memoria con ISO real sintético. En la copia europea, dos ejecuciones deben producir JSON idéntico y verificar todos los archivos; desconocidos explícitos no se convierten en soporte.

Los metadatos privados pueden residir en `reports/local` ignorado. Una raíz externa explícita solo se necesita antes de exportar derivados originales; esta operación no los crea. G02 requiere además extracción repetible y corpus de F02.02-F02.07, por lo que completar este catálogo no cierra G02.
