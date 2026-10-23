# CP01–CP15 — Decoder de polígonos CLD indexados

2026-10-23. **Contrato CF-T4 definido; implementación CF-T5 pendiente.**
Perfil `ps2-cld-polygons-v1`. RF02.04/RF02.05, RNF06.01–RNF06.03,
RNF07.06–RNF07.09 y RNF08.01. Continúa
[CF-T1–T3](../docs/execution/f03-04-collision-shapes-research.md) y
[su plan EARS](../docs/specs/sh3-3ds/collision-shapes-research.md).

## Alcance y decisiones

Se interpreta **un recurso indexado completo**, con los grupos poligonales
0–3 y el grupo 4 vacío. No se admiten listas dinámicas del overlay, RAM
completa, registros IR-T7 ni fragmentos de un recurso. No hay detección por
extensión o magic: el llamador selecciona explícitamente este decoder.
Una aceptación estructural no identifica la edición, sala o procedencia.

La variante activa de 48 bytes queda **fuera del perfil**: se rechaza todo
el recurso, sin devolver solo los polígonos y aparentar una conversión completa.
El inventario fijado CF-T1–T3 contiene 233 recursos con grupo 4 vacío y 52
con formas activas de 48 bytes. Esto es una preselección por evidencia previa,
no el resultado de ejecutar el futuro decoder. Ambos recursos identificados
en el carrusel pertenecen al primer conjunto.

Se conservan cabeceras opacas, vectores, orden de referencias, alias, colas
compartidas y registros sin referencias. No se normalizan los campos que solo
coincidían en el corpus —por ejemplo la palabra 4 en `forma+0x04`—. No se
aplican escalas, origen X/Z, transformaciones, filtros ni triangulación.
Geometría degenerada, no plana o de winding desconocido se conserva; este
lector no decide si producirá un contacto físico válido.

## Requisitos EARS

Como implementador del port, necesito una vista acotada y fiel del recurso
para incorporar después su estructura al intermedio sin inventar física.

- **CP01:** CUANDO recibe una entrada, el decoder DEBERÁ aceptar únicamente
  `bytes` y comprobar el presupuesto global antes de leer cabeceras.
- **CP02:** CUANDO recorre los cinco grupos, DEBERÁ comprobar tamaños, alineación,
  límites, orden, contigüidad y terminadores antes de exponer un resultado.
- **CP03:** SI el grupo 4 declara registros además de su terminador, DEBERÁ
  rechazar el recurso como variante no soportada, sin salida parcial.
- **CP04:** CUANDO interpreta una forma activa de 80 bytes, DEBERÁ distinguir
  variante 0 de tres puntos y variante 1 de cuatro, conservando los cuatro
  vectores en ambos casos; otra variante DEBERÁ rechazarse explícitamente.
- **CP05:** CUANDO lee cabeceras de formas, DEBERÁ conservar exactamente los
  enteros opacos y la palabra de filtro, sin convertirlos en materiales,
  propietarios, conteos de vértices ni categorías de gameplay.
- **CP06:** CUANDO lee coordenadas, DEBERÁ conservar las palabras f32 originales
  y su vista numérica, incluidos cero negativo y subnormales finitos; SI
  cualquier componente u origen es NaN o infinito, DEBERÁ rechazarlo.
- **CP07:** CUANDO recorre una de las 80 listas, DEBERÁ resolver su offset
  relativo dentro de la región de índices y terminar en `0xFFFFFFFF`, sin
  usar el siguiente puntero como límite implícito.
- **CP08:** CUANDO una lista contiene índices repetidos, compartidos, fuera
  de orden o una cola compartida, DEBERÁ conservarlos en orden; SI un índice
  apunta al terminador o fuera de las formas activas de su grupo, DEBERÁ rechazarlo.
- **CP09:** CUANDO existan formas sin referencias, grupos vacíos o una palabra
  de selección no nula, DEBERÁ conservarlos sin eliminar datos ni simular consultas.
- **CP10:** SI el número de formas o referencias excede un límite del perfil,
  DEBERÁ rechazar antes de añadir el elemento excedente; los alias DEBERÁN
  contar por cada aparición en la vista expandida.
- **CP11:** CUANDO termina con éxito, DEBERÁ producir colecciones propias y
  deterministas, sin mutar la entrada ni compartir colecciones mutables entre
  celdas o invocaciones; el llamador DEBERÁ conservar los bytes originales.
- **CP12:** SI hay un error, DEBERÁ emitir un código tipado estable sin payloads,
  rutas privadas ni salida parcial; las validaciones DEBERÁN funcionar con `-O`.
- **CP13:** MIENTRAS decodifica, DEBERÁ operar solo sobre el buffer recibido,
  sin I/O, red, subprocess, emulador, reloj, dependencias del SDK ni registro global.
- **CP14:** CUANDO se acepte CF-T5, la batería DEBERÁ comparar casos sintéticos
  con expectativas independientes del decoder y exigir al menos 80 % de
  líneas y ramas en su módulo, además de los controles globales existentes.
- **CP15:** CUANDO se evalúen recursos privados, el coordinador DEBERÁ verificar
  identidad e integridad por separado, conservar rechazos y distinguir
  estructura, enlace en RAM y respuesta física; DEBERÁ mantener `capabilities=[]`
  hasta contar con contratos y pruebas de capacidades adicionales.

## Layout admitido

Todos los enteros son unsigned LE; cada f32 se lee también como u32 LE.
No hay aritmética circular de u32 ni punteros absolutos en esta vista.

| Offset del recurso | Campo |
|---|---|
| `0x00`, `0x04` | `origin_words[2]` y vista `origin_xz[2]`; no se suman a los vectores. |
| `0x08 + 4*g`, g=0..4 | Tamaño en bytes del grupo, incluido su terminador. |
| `0x1C` | `selection_word`, conservada como u32. La selección del juego omite el recurso cuando no es cero; el decoder no lo elimina. |
| `0x20 + 0x40*g + 4*c`, c=0..15 | Offset de la lista de índices de la celda c del grupo g. |
| `0x160 + 4*g` | Offset al primer registro del grupo g. |
| `[0x174, data_offsets[0])` | Región de listas y bytes no interpretados; puede tener huecos, alias y colas compartidas. |

Los cuatro primeros grupos tienen stride `0x50`; el último, `0x30`.
Cada tamaño es al menos un stride y múltiplo de él. Todos los offsets de
grupo están alineados a 16 y el primero es al menos `0x180`.
`offset[g]+size[g] == offset[g+1]` para g=0..3, y el final del grupo 4 es
exactamente el tamaño del buffer. Grupos reordenados, solapados, huecos entre
grupos y bytes añadidos al final no pertenecen a v1. Esta restricción del
perfil se apoya en el corpus investigado; no afirma que otras ediciones
deban organizarse igual.

El último registro de cada grupo debe ser **completamente cero**, no solo
su primer byte. Los registros anteriores de los grupos 0–3 son activos y
deben comenzar con 1; un cero interior no recorta el grupo. El número de
formas es `size//stride - 1`. En grupo 4, tamaño exactamente 48, terminador
cero y dieciséis listas vacías. Una lista vacía apunta a una palabra
`0xFFFFFFFF` dentro de la región de índices; no usa puntero nulo.

| Offset de forma | Representación |
|---|---|
| `+0x00` | `present`, u8, exactamente 1. |
| `+0x01` | `variant`, u8: 0 → `point_count=3`; 1 → `point_count=4`. |
| `+0x02` | `word_02`, u16 opaco; cualquier valor representable. |
| `+0x04` | `word_04`, u32 opaco; **no** se exige 4. |
| `+0x08` | `filter_word`, u32 conservado; no se restringen los bits. |
| `+0x0C` | `word_0c`, u32 opaco. |
| `+0x10 + 16*v`, v=0..3 | Cuatro palabras y cuatro f32, en orden X/Y/Z/W. |

Se valida finitud en los dieciséis componentes, incluido el cuarto vector
de un triángulo y todos los W. W no tiene que valer 1. No se calcula área,
normal, orientación, convexidad, planos, máscara efectiva ni comportamiento
de daño. La existencia de la vista numérica host no implica precisión VU0.

## Límites de trabajo y orden de errores

Son límites del perfil v1, no máximos demostrados del juego:

| Límite | Valor inclusivo | Justificación |
|---|---:|---|
| Buffer | 752–65.536 bytes | Mínimo: `0x180 + 4*80 + 48`. Mayor recurso del sondeo: 48.784 bytes. |
| Grupos / celdas | 5 / 16 por grupo | Tablas verificadas; siempre 80 celdas. |
| Polígonos por grupo 0–3 | 512 | Máximo observado de un grupo: 330. |
| Polígonos totales | 768 | Máximo de todas las formas observado por recurso: 568. |
| Referencias por lista | 512 | Máximo observado: 330; se cuentan duplicados. |
| Referencias totales | 4.096 | Máximo observado por recurso: 568. Contar cada alias de cada celda. |

Para comprobar rangos se usa `offset <= N-size` tras validar `size <= N`;
sumar u32 no puede envolver y los contadores se comprueban antes de reservar
o expandir. El recorrido de una lista es lineal en palabras, nunca recursivo.
Una caché por offset solo puede reutilizar datos inmutables y no omitir el
conteo global por celda. No se asigna memoria según un u32 sin validarlo.

El decoder evalúa etapas en este orden. Dentro de un recorrido se usa orden
creciente de grupo, registro, celda y componente; el primer fallo gana.

1. Tipo exacto `bytes` → **CP_INPUT**. `bytearray`, `memoryview`, subclases,
   `None`, texto, números y objetos con `__bytes__` no se convierten implícitamente.
2. Longitud → **CP_SIZE**.
3. Dos f32 de origen, X antes de Z → **CP_ORIGIN**.
4. Por grupo: tamaño/stride → **CP_GROUP_SIZE**; alineación →
   **CP_GROUP_ALIGNMENT**; rango completo/primer offset → **CP_GROUP_RANGE**.
   Tras los cinco rangos: contigüidad/final exacto → **CP_GROUP_LAYOUT**.
5. Cantidad por grupo y total de polígonos → **CP_POLYGON_BUDGET**.
6. Tamaño del grupo 4 distinto de 48 → **CP_NONPOLYGON_UNSUPPORTED**.
   No se interpreta su payload. No afirma que una entrada malformada sea
   una variante válida: solo que no puede aceptarse como recurso poligonal v1.
7. Terminador completo de cada grupo → **CP_TERMINATOR**.
8. Por forma de los grupos 0–3: byte de presencia → **CP_RECORD_PRESENT**;
   variante → **CP_VARIANT_UNSUPPORTED**; dieciséis f32 → **CP_COORDINATE**.
9. Por grupo/celda: offset alineado a cuatro y
   `0x174 <= p <= data_offsets[0]-4` → **CP_LIST_OFFSET**. Antes de leer cada
   palabra, comprobar que cabe antes del grupo 0 → **CP_LIST_TERMINATOR**.
   Si es `0xFFFFFFFF`, terminar. Si no, validar índice `< count[g]` →
   **CP_INDEX**, y luego los límites por lista/total antes de añadir →
   **CP_REFERENCE_BUDGET**. El terminador no consume presupuesto de referencias.

Un índice negativo representado como `0xFFFFFFFE` es fuera de rango; solo
`0xFFFFFFFF` es terminador. Un índice al registro final cero es inválido.
Un terminador hallado en el grupo de formas no salva una lista truncada.
Los códigos `*_UNSUPPORTED` distinguen una exclusión del perfil de un
resultado aceptado; no se intenta otra interpretación automáticamente.

## API y diseño SOLID

Módulo previsto: `tools/pipeline/decoders/ps2_cld_polygons.py`.

```python
class CollisionPolygonError(ValueError):
    code: str

def decode_polygons(raw: bytes) -> dict:
    ...
```

La excepción expone `code` y `str(error) == code`, sin bytes de entrada en
el mensaje. No se filtran `struct.error`, `IndexError` o resultados parciales
por una entrada inválida. Se usan condiciones explícitas, no `assert`.

Salida con claves exactas:

| Nivel | Claves y tipos |
|---|---|
| Recurso | `profile` = `ps2-cld-polygons-v1`, `source_size` int, `origin_words` list[2]int, `origin_xz` list[2]float, `selection_word` int, `data_offsets` list[5]int, `data_sizes` list[5]int, `groups` list[5]dict. |
| Grupo | `index` int, `offset` int, `size` int, `stride` int, `records` list[dict], `cells` list[16]dict. Grupo 4 conserva su terminador/offset/tamaño y `records=[]`. |
| Forma | `index`, `offset`, `present`, `variant`, `point_count`, `word_02`, `word_04`, `filter_word`, `word_0c` como int; `vector_words` list[4]list[4]int; `vectors_xyzw` list[4]list[4]float. |
| Celda | `index`, `offset`, `terminator_offset` int; `indices` list[int] en orden original. |

No se incluye SHA, sala, nombre de archivo, actor, estado de publicación ni
`capabilities` en la vista pura. El coordinador externo verifica las fuentes
y construirá el manifiesto. `source_size` es el número de bytes recibido.
Cada offset de salida es relativo al mismo recurso.

La vista **no reemplaza el buffer original**: la región no referenciada entre
cabecera y formas puede contener bytes opacos. El llamador conserva `raw`
inmutable para una futura exportación fiel. No se implementará un escritor
que reconstruya esos bytes inventando padding. El decoder no declara un
round-trip de archivo a partir de la vista sola.

Responsabilidades separadas:

- Decoder: límites, lectura, validación y vista; solo biblioteca estándar.
- Constructor de fixtures: datos propios y ensamblado; no importa el decoder.
- Oráculo: lector independiente para los buffers/expectativas de prueba;
  no importa el decoder, sus constantes o el constructor.
- Coordinador privado e intermedio: identidad, I/O, custodia y conservación
  de `raw`; implementación posterior al decoder y a su verificación.
- Runtime/visor/solver: fuera de CF-T4/CF-T5. No se añade código a esos módulos.

## Fixtures y pruebas sintéticas definidas

[Vectores propios v1](../tests/fixtures/synthetic/collision-polygons-v1.json)
contiene bytes en hex de dos fixtures base, expectativas explícitas y casos
materializados con tamaño/hash. Son datos inventados; no contienen bytes
de la ISO, capturas, coordenadas del juego ni código desensamblado.
Los casos de fallo conservan el código esperado y la mutación que lo provoca.
Las pruebas del decoder se escribirán en CF-T5 contra estos vectores; no hay
tests omitidos ni una implementación ficticia para declarar aprobación ahora.

Fixture principal: tres formas en grupo 0, de las cuales una degenerada queda
sin referencias. Celdas 0/1 comparten `[1,0,1]`; celda 2 comparte su cola `[1]`;
el resto está vacío. Tiene cabeceras opacas no constantes, cuarto vector de
triángulo distinto de cero, W distinto de 1, origen con cero negativo y padding
propio no nulo. El segundo fixture es el recurso mínimo con todos los grupos
vacíos y sus 80 offsets apuntando al mismo terminador.

### Batería de aceptación de CF-T5

| Familia | Casos y resultado obligatorio | Requisitos |
|---|---|---|
| Valores conocidos | Comparar todas las claves/tipos/offsets, palabras y f32 del fixture principal; no aplicar el origen. | CP04–CP06, CP11 |
| Referencias | Duplicados `[1,0,1]`, dos offsets iguales, cola compartida, lista vacía, celda 15 y alias entre grupos válidos; conservar orden y grupos. | CP07–CP10 |
| Preservación | Forma sin referencias, degenerada, geometría no plana, W arbitrario finito, campos opacos cambiados, selección no nula, padding no nulo; vista/raw coherentes sin filtrado. | CP05/CP06/CP09/CP11 |
| f32 | Cero negativo, subnormal positivo/negativo y máximo finito preservados por palabras. Rechazar NaN, +Inf y -Inf tanto en ambos orígenes como en cada uno de los 16 componentes de una forma, incluidos W y el cuarto vector del triángulo. | CP06 |
| Tipos/tamaño | Rechazar los tipos de CP_INPUT sin ejecutar `__bytes__`; probar mínimo, mínimo−1, máximo y máximo+1, header corto y truncamiento de cada sección. | CP01/CP12 |
| Grupos | Tamaño cero/no múltiplo/enorme; offsets bajo header, fuera, desalineados o susceptibles de overflow u32; hueco, superposición, reordenamiento y bytes finales. | CP02 |
| Terminadores | Corromper cada byte del registro final en cada grupo; cero interior entre formas activas; presencia distinta de 1; variante 2/3/255 en grupo poligonal. | CP02/CP04 |
| Grupo 4 | Recurso con un registro de 48 bytes más terminador: rechazo completo; lista no vacía de un grupo 4 vacío: índice inválido. | CP03/CP08 |
| Índices malformados | Puntero nulo/header/datos/final/desalineado, índice igual al conteo o enorme, falta de terminador y sentinel situado solo dentro de formas; sin bucle ni lectura fuera. | CP07/CP08/CP12 |
| Presupuestos | Por grupo 512/513, total 768/769; por lista 512/513; total 4096/4097 contando alias. Construir cada par manteniendo válidas las etapas anteriores. | CP10 |
| Estado y aislamiento | Dos invocaciones iguales; mutar la vista no altera entrada, otras celdas ni próxima salida. Comprobar bytes antes/después. Intercalar entrada inválida entre válidas no deja estado. | CP11/CP13 |
| Precedencia y optimización | Varias corrupciones simultáneas con primer código según etapas; mismo resultado/error bajo Python normal y `-O`; no depender de aserciones. | CP12 |
| Metamórficas | Trasladar región de datos y ajustar offsets/tamaño preserva formas e índices; cambiar solo padding no cambia la vista salvo `source_size`/offsets si corresponde; reordenar una lista cambia solo esa celda o sus alias explícitos. | CP07/CP11 |
| Oráculo y sensibilidad | Oráculo stdlib separado, expectativas fijas y lectura directa de bytes; demostrar detección de eliminar duplicados, tomar `word_04` como conteo, perder cuarto vector, aplicar origen y contar un alias solo una vez. | CP04/CP08/CP10/CP14 |

Los vectores materializados son semillas de esta batería; no sustituyen sus
barridos de campos y fronteras. El oráculo comparará enteros/tipos exactos y
palabras f32 exactas, usando signo para el cero numérico. No habrá tolerancia
geométrica: el decoder solo lee, no transforma.

## Pipeline y secuencia de implementación

CF-T5 creará `tests/python/test_cld_polygons.py` y
`tests/cld_polygon_wire_oracle.py`, con constructor de fixtures independiente.
El job `quality` existente descubre los tests; se añadirá el oráculo a Ruff
y formato, y el módulo a `coverage_gate --files` sin retirar el gate global
ni el de IR-T7. CI usa únicamente los fixtures propios. La ejecución privada
queda separada y no es requisito de acceso para un colaborador o CI.

Comandos previstos, **todavía no ejecutables por falta de implementación**:

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_cld_polygons.py --cov=tools.pipeline.decoders.ps2_cld_polygons --cov-branch --cov-report=json:build/cld-polygons/coverage.json --junitxml=build/cld-polygons/pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/cld-polygons/coverage.json --files tools/pipeline/decoders/ps2_cld_polygons.py
```

| Tarea | Entrega y criterio de cierre |
|---|---|
| **CF-T4 — completada** | Este contrato, vectores sintéticos con expectativas, diseño SOLID, errores, presupuestos, oráculo y batería/pipeline definidos. No se atribuyen pruebas al decoder ausente. |
| **CF-T5a — pendiente** | Decoder puro con API exacta y errores tipados. Casos de layout/valores/terminación/finitud y subconjunto poligonal, sin I/O. CP01–CP09/CP12/CP13. |
| **CF-T5b — pendiente** | Oráculo independiente, barridos/fronteras/metamórficas/aislamiento y `-O`; controles de sensibilidad. CP10–CP14; todos los casos de la tabla pasan, no solo las semillas JSON. |
| **CF-T5c — pendiente** | Integrar gate por módulo y oráculo en CI; pruebas del perfil, regresión relevante, Ruff, custodia y trazabilidad. ≥80 % líneas y ramas por módulo. |
| **CF-T6 — pendiente** | Cotejo privado A/B con pins y registro de aceptados/no soportados/errores; comparar los dos recursos ligados a RAM, sin relajar el perfil para obtener 285 aceptados. CP15. |
| **CF-T7 — pendiente** | Definir y después implementar extensión del intermedio que conserve fuente completa y vista, publicación exclusiva y reconstrucción A/B con oráculo. IR-T7 sigue inalterado. |

La variante de 48 bytes, las listas dinámicas superpuestas, inicialización/
sobrescritura, alta/baja desde el cargador y respuesta física requieren sus
propias tareas y evidencias. No se cierra F03.04 global, G02/G03 ni daño/muerte.
