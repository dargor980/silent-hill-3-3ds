# Inventario de candidatos v1 — F02.07

Primera instancia de F02.07; RF02.02/RF02.08/RF13.02, RNF06.01/.04/.07,
RNF07.06-.09 y RNF11.05-.09; V02/V20/T02. No es el manifiesto del corpus elegido.

## EARS

- **C01** WHEN recibe catálogo y recibo THEN el inspector SHALL comprobar sus SHA-256 fijados por el operador, versiones y concordancia de origen, selección, recursos, dos inventarios y exclusiones antes de leer payloads. No SHALL sustituir esos hashes por los calculados de una entrada desconocida.
- **C02** WHEN abre una copia THEN SHALL exigir una raíz externa explícita, recorrer componentes sin enlaces, anclar el directorio a un descriptor y comprobar el conjunto exacto de archivos por ID. No SHALL crear ni modificar payloads.
- **C03** WHEN solicita un rango THEN SHALL validar enteros, tamaño, offset y longitud (máximo 4096 bytes), verificar primero el SHA-256 del archivo completo por bloques, leer exactamente el rango y comprobar identidad/estabilidad antes de devolver bytes. IF falta, cambia, contiene enlaces o falla I/O THEN SHALL rechazar con código y sin bytes/rutas privadas en stdout.
- **C04** WHEN registra un candidato THEN SHALL conservar ID, hash, tamaño, origen, método/versiones y estado de evidencia. En v1 todos SHALL permanecer `candidate`, tipo `unknown`, dependencias `not_inspected` y capacidades vacías.
- **C05** WHEN compara recursos THEN SHALL distinguir igualdad de contenido completo y coincidencia de un prefijo acotado; ninguna SHALL implicar dependencia, formato, sala ni conexión. Una extensión SHALL figurar solo como indicio privado sin validar.
- **C06** WHEN genera el inventario THEN SHALL incluir todas las categorías obligatorias, el par de salas y bloqueos aun sin selección; SHALL conservar F02.07/G02 pendientes. Un array de dependencias vacío SHALL no afirmar independencia.
- **C07** WHEN repite con el mismo conjunto verificado THEN SHALL producir bytes JSON deterministas, independientemente de la copia y orden de entradas. El método v1 SHALL observar solo los primeros min(64, tamaño) bytes y almacenar su longitud/hash, nunca bytes, hex, base64 ni texto del payload.
- **C08** WHEN publica metadatos THEN SHALL crear un archivo nuevo exclusivamente después del cierre satisfactorio del lector; SHALL no sobrescribir evidencia ni anunciar éxito ante error previo. CI SHALL usar solo fixtures propios y no ejecutar la inspección real.

## Diseño y modelo

`private_files` comparte primitivas POSIX de propiedad/recorrido ya probadas en
F02.06. `VerifiedPrivateReader` posee I/O, identidad y límites; el coordinador
`candidates.collect_candidates` recibe un puerto de lectura y aplica evidencia,
agrupación y política de categorías. No se añade parser de formato, dependencia
externa ni acceso al filesystem desde el runtime.

Entrada: catálogo F02.04 fijado por hash y `verified.json` F02.05 fijado por hash.
Se contrasta su relación, no se regenera la ISO: la autenticidad depende de hashes
previamente registrados. Cambiar ambos documentos y sus hashes no constituye una
verificación del disco. La CLI requiere `--private-copy` explícita y comprueba el
contenido contra ese recibo; la ruta de copia no se usa como prueba de identidad.

Salida: `schema_version=1`, scope `candidate_inventory`, herramienta/métodos v1,
hashes de evidencia, source/selection, exclusiones y candidatos ordenados por ID.
Cada candidato incluye `observations.prefix` (offset, longitud, SHA-256),
`name_hint` (solo sufijo privado no validado), estado/tipo/dependencias y SHA-256
de su archivo. `content_groups` agrupa tamaño+hash completos; `prefix_groups`
agrupa longitud+hash de prefijos no vacíos, solo grupos con al menos dos IDs.
Los grupos son observaciones numéricas, no recursos semánticos compartidos.

Categorías: scene, character, animation, alpha_material, collision, camera,
spanish_text, sound, sequence, interaction_inventory, enemy, progress. Todas
incluyen estado, IDs vacíos, razón y siguiente investigación. `room_pair` queda
sin seleccionar; `corpus_id=slice-es-normal-v1` vincula el objetivo, no cobertura.

Estados reservados: `candidate` admite observaciones sin tipo probado;
`identified` requerirá contrato estructural, procedencia y fixture negativo;
`decoded` requerirá una representación comprobada; `validated` requerirá el
oráculo pertinente (incluido comportamiento cuando corresponda). v1 no produce
los tres últimos estados. Una futura versión debe especificar sus evidencias.

No se registran timestamps/rutas de copia para no introducir diferencias
accidentales. Los comandos y copia leída se anotan separadamente en evidencia
local. Los JSON privados permanecen en `reports/local` ignorado; la publicación
usa staging exclusivo `.pending.json` y enlace final sin reemplazo, con modo 0600. Un staging
sin archivo final no acredita éxito y se conserva para diagnóstico.

## Límites y pruebas

Lecturas completas usan bloques de 1 MiB, rangos retornados ≤4096 bytes;
metadatos ≤128 MiB y recursos ≤100000. Los arrays de grupos son lineales en
número de IDs, sin matriz de parejas. El lector rechaza hardlinks, enlaces
simbólicos y especiales; verifica directorio antes/después y archivo abierto
frente al nombre. Requiere árbol bajo control del operador: comprobaciones
finitas no garantizan inmutabilidad frente a un escritor concurrente posterior.

Fixtures propios: copias iguales, recursos de mismo contenido en posiciones
distintas, prefijos iguales con colas distintas, archivos vacíos, nombres que
parecen formatos, errores de evidencia, truncamiento, límites, enlaces,
sustituciones, I/O y publicación. Suite y cobertura independientes de líneas y
ramas ≥80 %; Ruff, custodia y trazabilidad en el job quality existente.
