# F02.07 — Selección de catálogo y apertura

Unidad: `origin/load-provenance/LP-C`. Fecha: 2026-10-18.
Estado: **investigación estática y adaptador de selección/apertura completados;
driver, posición y ejecución real pendientes**.
Contrato [CA01–CA09](../../schemas/catalog-open-v1.md).
[Evidencia SRC58](../compatibility/catalog-open-evidence.json).

## Hallazgos contrastados

Se verificaron de nuevo la ISO completa, el contenedor, su índice MFA, el
rango del recurso y su hash; el ELF y el estado coinciden con las entradas
fijadas en SRC55/SRC57. Entre **1.704 registros** del directorio en memoria
hay **una entrada** que coincide en contenedor, nombre, offset y tamaño con
el candidato. Las cadenas pertenecen al área del directorio. Este registro
está en un estado posterior a la carga; su presencia no prueba su selección
durante una llamada nueva.

Se fijaron **nueve ventanas y 2.288 bytes**, iguales entre ELF y estado:
resolver, wrapper de apertura, comparación de registros/cadenas, clasificación
de separadores, copia acotada, búsqueda de marcador y despacho de apertura.
Once instrucciones anclan las decisiones investigadas. Para offset no
negativo, el resolver trunca la solicitud en el marcador del contenedor y
devuelve su rango. La reescritura alternativa de ruta queda fuera del contrato.
El despacho subyacente contiene conversión de letras ASCII a mayúsculas,
conversión de separadores y tratamiento de versión ISO; no se generaliza ese
comportamiento a otros dispositivos o rutas.

Dos análisis producen un informe idéntico de **3.227 bytes**, SHA-256
`c39933647ccd2035f40817afc052ac36d0a68aa5d1d733724ede38ce8b90b55b`.
Los lectores se cierran antes de publicar y se revalidan estado, catálogo,
evidencia y plan previos. El plan nuevo se guarda sin sobrescribir, con
directorio privado 0700 y archivo 0600. No se abrió PCSX2 en esta unidad.

## Adaptador y límites

[catalog_open](../../tools/inspectors/catalog_open.py) recibe un origen y un
perfil privados más cuatro pausas LF: selección, llamada de apertura, retorno
y descriptor generado. Usa **22 rangos, distribuidos 7/5/5/5**, contra cuatro
estados diferentes. La coordinación real sigue a cargo de SRC57.

El origen exige hashes, ruta ISO ASCII canónica, nombre acotado y rango dentro
del contenedor. En la selección se comprueba que la CPU señale una fila del
directorio observado y que sus referencias apunten a cadenas dentro de su
área. Solicitud, contenedor, nombre y rango deben concordar; compartir tamaño
y offset con otro archivo no basta.

El adaptador compara las ventanas suministradas y decodifica JAL/delay slot
de la llamada. Comprueba PC, marco de pila, argumentos, flags y modo fijados,
mapas compartidos, identidad, secuencias y ciclos. La fila debe permanecer
reservada durante la apertura y abrirse con el identificador devuelto, una
generación adicional y el token/rango que valida `archive_descriptor`.

Los flags y modo del plan privado son restricciones previstas, todavía no
observadas en una nueva carga. La comparación de código no interpreta todo
el cuerpo ni autentica un perfil arbitrario. El origen se suministra al
adaptador puro; este no relee ISO/MFA. El análisis operativo sí verificó los
originales mediante los lectores existentes.

El recibo declara consistencia entre la entrada suministrada y las pausas de
apertura, **sin acreditar todavía la identidad del objeto del driver, posición,
lectura de disco o ejecución real**. No genera `Read`, vínculos ni capacidades.
Solo publica hashes, tamaños, conteos y etiquetas; cadenas, direcciones y
registros se mantienen privados.

La interpretación queda separada de la adquisición, custodia, origen ISO/MFA
y publicación, reutilizando LF/DA sin cambiar sus módulos. No se añadieron
dependencias ni se modificó el ejecutable de PCSX2 o el runtime Nintendo.

## Validación

**96 casos propios** cubren pertenencia al directorio/área de cadenas,
contenedores distintos con igual rango, solicitudes/nombres parecidos,
aperturas fallidas, reserva, reciclado, tamaños, código/mapas alterados,
mezcla de procesos, cuatro slots, límites de ciclos y secuencia regional 256
con su primer exceso. También se prueba que hashes suministrados se conserven
sin presentarlos como una relectura del origen.

El primer ensayo tuvo 91 aprobados y un fallo de oráculo: confundía la etiqueta
genérica de un rango con una ruta privada. Se corrigió para distinguir una
clave de ruta de la etiqueta y se añadieron cuatro casos de límites y mapas.
El ensayo final aprueba 96/96. La regresión completa aprueba **2.632 pruebas,
sin fallos ni omisiones**, en 44,583 segundos según JUnit. Las publicaciones
operativas finalizaron antes de iniciar la regresión.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| catalog_open | 106/106 (100 %) | 20/20 (100 %) |
| Todas las herramientas | 4.804/4.849 (99,07 %) | 1.361/1.394 (97,63 %) |

Gate independiente 80/80 y Ruff/formato aprobados en los 124 archivos del
alcance Python de CI. El job existente descubre estos casos sin originales.
Los controles finales de repositorio, enlaces, custodia, hashes y diff se
registran en SRC58. Los archivos fijados en SRC55/SRC56/SRC57 permanecen
iguales. No se ejecutó CI remota ni una nueva compilación C++/3DS.

## Siguiente tarea: objeto del driver y posición

1. **Identificador subyacente:** seguir desde el resultado de apertura hasta
   la tabla/objeto que usa el despacho de lectura. Fijar su forma de búsqueda,
   cierre/reutilización, tabla de funciones, tamaño y referencia al archivo.
   Entregable: ventanas privadas y contrato EARS. Aceptación: distinguir un
   identificador activo de un índice coincidente o de un objeto residual.
2. **Posición y ruta:** observar posición antes/después y solicitud/retorno;
   comprobar la función elegida y recortes al final del archivo. Para caché,
   probar el origen previo del sector y el ABI de copia; para lectura, fijar
   su finalización. Entregable: adaptador puro con casos de objeto ajeno,
   reciclado, posición errónea, retorno corto y caché sin origen.
3. **Direcciones dinámicas:** definir cómo obtener bajo guardia las referencias
   de la pausa actual para construir sus planes multirrango. No reutilizar
   punteros de este estado posterior. Cualquier estado de sondeo o solicitud
   auxiliar debe contar dentro del presupuesto; cuatro estados de evidencia
   no equivalen necesariamente a cuatro guardados totales de la sesión.
4. **LP-D:** completar el plan antes de ejecutar, manteniendo ≤48 estados,
   ≤256 solicitudes regionales/hits, 60 segundos activos, 3.600 de pared,
   8 GiB de etapa y 10 GiB libres mínimos. Iniciar antes de la carga con
   español/Normal/Normal, sin restauraciones intermedias; conservar rechazos,
   reimportar dos veces y verificar cierre/custodia.

LP-C sigue parcial. Procedencia real, semántica de cámara, F02.07/Q05/G02,
dos salas conectadas y validación física en New Nintendo 2DS XL siguen pendientes.
