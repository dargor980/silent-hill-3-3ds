# F02.07 — Inventario de candidatos y bloqueos del corpus

Fecha: 2026-10-17. Completadas las instancias `contrato-inventario`, `lectura` y
`candidatos`, con repetibilidad y calidad para ese alcance. **F02.07 permanece
pendiente**: ningún tipo semántico, dependencia ni par de salas está demostrado.
Siguiente instancia: `F02.07/formato-camera`.

## Alcance y contrato

[Ticket](../specs/sh3-3ds/tasks/F02.md#f0207), [C01-C08 EARS](../../schemas/candidate-inventory-v1.md)
y [slice-es-normal-v1](../scope.md). Se usan exclusivamente las copias externas
aceptadas en [F02.05](f02-05-repeatable-extraction.md), conservando las garantías
probadas en [F02.06](f02-06-extraction-hardening.md).

El lector verifica tamaño/SHA-256 completo por bloques antes de devolver un rango
de hasta 4096 bytes; esta inspección observa los primeros min(64, tamaño) bytes.
Solo registra longitud/hash del prefijo. No decodifica ni imprime bytes, textos,
nombres internos o previews. El sufijo del nombre es un indicio privado sin validar.

`private_files` comparte las primitivas POSIX antes incluidas en `private_output`,
sin cambiar sus algoritmos. `VerifiedPrivateReader` separa I/O, confinamiento y
estabilidad; `candidates` recibe un puerto de lectura y aplica concordancia de
evidencias, agrupación y política de categorías. La CLI publica JSON nuevo después
del cierre del lector. No se modifica runtime, SDK, parser MFA ni transferencia.

## Entradas y resultado real

El catálogo y recibo conservaron los hashes registrados previamente:

| Evidencia | SHA-256 |
|---|---|
| Catálogo F02.04, 1.838.826 bytes | `39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d` |
| Recibo final F02.05, 1.848.367 bytes | `74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943` |
| Cada inventario final v1, 1.970.573 bytes | `d5e6de2d1c03f053cedeb488390b5d250f5129aba804ab4fbac54eaeb81a3c57` |

Se comparan esquema, herramientas, origen/perfil, selección, recursos, inventarios
de ambas copias y exclusiones antes de inspeccionar. El origen conserva el perfil
europeo canónico. Esta ejecución no relee la ISO: la procedencia depende de las
evidencias fijadas de F02.04/F02.05, y cada payload extraído sí se vuelve a leer.

| Observación | Resultado |
|---|---:|
| Recursos verificados por copia | 1740 |
| Bytes de payload por copia | 1.562.367.840 |
| Archivos vacíos | 54 |
| Contenidos distintos por tamaño/SHA-256 | 1667 |
| Grupos de contenido idéntico | 15 (88 IDs en esos grupos) |
| Grupos con prefijo no vacío coincidente | 72 |
| Tipos identificados / categorías resueltas | 0 / 0 |
| Categorías obligatorias pendientes | 12 |

Dos ejecuciones finales, una por copia, generaron JSON idénticos. Los informes
`reports/local/f02-07-candidates-v1.json` y
`reports/local/f02-07-candidates-v1-repeat.json` quedan ignorados. Comandos, copia
y duración están en `reports/local/f02-07-execution-v1.json`; las rutas privadas
no forman parte del manifiesto determinista. No se creó una tercera extracción.

La coincidencia de contenido no demuestra dependencia ni una instancia compartida
en escena. La coincidencia de prefijos tampoco identifica un formato. Los 54
vacíos no se interpretan como ausencia de entidades. XBG0 y los 51 archivos ISO
fuera del alcance interno, incluidos 35 AFS, conservan sus exclusiones.

## Corpus pendiente y siguiente instancia

El manifiesto mantiene pendientes escena, personaje, animación, material con
alpha, colisión, cámara, texto español, sonido, secuencia, interacción/inventario,
enemigo y progreso. El par A/B está sin seleccionar; dependencias vacías significan
`not_inspected`. El perfil de alpha sigue español y acción/acertijos Normal.

Para orientar `formato-camera` hay 285 entradas con indicio `.cam`, ninguna vacía,
entre 512 y 3328 bytes y con 19 tamaños distintos. Esto **no confirma cámaras**.
Se preparó una selección privada por tamaño: mínimo, mediana, máximo y un recurso
con otro sufijo como control exploratorio. Ese control tampoco se presume inválido.
Los cuatro IDs/hashes y motivos están en
`reports/local/f02-07-camera-triage-v1.json`, vinculados al hash del inventario.
Ese JSON de 3465 bytes tiene SHA-256
`83e933df589061d02c9b9c1b84ca4a56ff35610aa155d5f0997ddbeb149c0586`.

La próxima instancia debe:

1. Buscar evidencia primaria del formato y registrar procedencia, versión y licencia
   de cualquier herramienta candidata; mantener las hipótesis aparte del contrato.
2. Contrastar las muestras con lecturas verificadas y acotadas. Documentar campos,
   límites, referencias y variantes solo cuando se puedan demostrar; no adivinar
   ejes, unidades o referencias a salas por similitud de nombres.
3. Construir fixtures propios válidos y estructuralmente inválidos antes del parser.
   Separar la validación de estructura de la interpretación de coordenadas/comportamiento.
4. Aplicar el contrato a los 285 candidatos, registrando aceptados/desconocidos sin
   relajar controles. Si no hay evidencia suficiente, conservar el resultado de
   investigación y el siguiente experimento concreto.
5. Repetir manifiestos y calidad; solo elevar el estado cuando se cumpla la evidencia
   del contrato. El cierre de cámaras no cerrará automáticamente salas, corpus o G02.

## Pruebas, integración y límites

Se añadieron **91 casos** propios. La suite final aprobó **919/919** pruebas.
Los nuevos casos cubren concordancia de recibos y origen, nombres engañosos,
prefijos iguales con contenidos distintos, límites, vacíos, corrupción,
truncamiento, enlaces, sustituciones, errores de I/O, limpieza y publicación.
Las pruebas anteriores de extracción y sus interrupciones siguen aprobadas.
Cobertura: **1748/1781 líneas (98,15 %)** y **582/602 ramas (96,68 %)**.
Lector, coordinador y primitivas POSIX compartidas: 100 % en ambas métricas.

La primera suite completa encontró un fallo de custodia: staging terminado en
`.pending` dentro de informes locales. Se corrigió a `.pending.json` y se añadió
una comprobación contra la política existente; no se relajó el escáner. Los dos
staging iniciales, que eran JSON de metadatos, se renombraron conservando bytes;
se preservó el log del rechazo y se generó un par final nuevo. La primera prueba
focalizada también corrigió la expectativa de código para un directorio: `fdopen`
lo rechaza como I/O antes de la comprobación de archivo regular.

El job quality existente descubre estas pruebas y aplica Ruff, cobertura y
custodia sin originales ni dependencias nuevas. Las evidencias locales se guardan
en `build/f02-07`: log/JUnit, cobertura, comandos, controles y manifiesto de fuentes.
La ejecución remota de CI y las pruebas de consola permanecen pendientes. No se
repiten compilaciones C++/ARM porque no cambiaron runtime ni cadena de compilación.

Ruff, formato de 50 archivos Python, umbral independiente de cobertura y controles
de arquitectura/custodia/trazabilidad: **aprobados localmente**. El manifiesto de
75 fuentes mide 12.276 bytes, SHA-256
`d0c375df2a2b4ea634d1e55e9082d392aaf964412504d87086fbf58d790aa19f`;
excluye este informe para evitar un hash circular. Se comprobaron sin cambios los
cuatro recibos F02.05 y nueve módulos de formatos/identidad/transferencia frente
al manifiesto F02.06. Esa comparación histórica es distinta de la relectura real
de payloads efectuada por los dos inventarios finales.

Las comprobaciones POSIX requieren un árbol bajo control del operador y no
garantizan inmutabilidad posterior frente a escritores concurrentes. Esta instancia
no acredita contenido jugable, rendimiento, dos salas conectadas ni decodificación.
G01 sigue pendiente de hardware; Q05/G02 siguen abiertos por formatos y corpus.
