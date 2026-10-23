# F03.04 / CF-T4 — Contrato poligonal y vectores sintéticos

2026-10-23. **CF-T4 completada.** Entrega:
[CP01–CP15, layout, API, errores y batería](../../schemas/ps2-cld-polygons-v1.md),
[vectores propios](../../tests/fixtures/synthetic/collision-polygons-v1.json).
El decoder de producción y sus tests corresponden a CF-T5 y siguen pendientes.

## Decisiones concretas

El perfil `ps2-cld-polygons-v1` recibe un recurso indexado completo. Conserva
los grupos poligonales 0–3, tres/cuatro puntos, cuatro vectores por registro,
palabras opacas, listas compartidas, duplicados y formas no referenciadas.
El grupo 4 debe estar vacío. Un recurso que declara formas de 48 bytes se
rechaza entero como `CP_NONPOLYGON_UNSUPPORTED`, sin ocultar datos mediante
una conversión parcial.

La palabra `forma+0x04` no se toma como conteo; la selección no nula no
elimina el recurso. Los cuatro vectores se conservan incluso en un triángulo.
W finito distinto de 1, cero negativo, subnormales, geometría degenerada y
campos opacos no constantes tienen expectativas positivas explícitas.
No se aplica origen, transformación, filtro físico o reparación geométrica.

Los límites se fijan antes de implementar: 752–65.536 bytes, 512 polígonos
por grupo, 768 totales, 512 referencias por lista y 4.096 referencias totales
contando cada alias de cada celda. El contrato define 17 códigos de error y
su precedencia, API pura sin I/O, propiedad de las colecciones y conservación
del buffer fuente fuera de la vista. La vista sola no permite reconstruir
padding o datos no referenciados: no se promete ese round-trip.

El diseño separa decoder, constructor sintético, oráculo y coordinador
privado. Quedan especificados el gate individual de líneas/ramas ≥80 %, la
incorporación al job `quality` existente y la regresión pertinente. No se
cambió CI para apuntar a un módulo todavía inexistente.

## Evidencia utilizada

Se relee y verifica el comprobante CF-T1–T3 de 1.694.054 bytes, SHA-256
`80315f08d6d055d048c84a20dfd483f5be806d94bf9a67d4efe4ffeb16cfe11a`.
Su conteo distingue 233 recursos sin formas activas del grupo 4 y 52 con
ellas. Los máximos del inventario —48.784 bytes, 568 formas totales y 568
referencias por recurso, 330 por lista/grupo— orientan los presupuestos.

Estos conteos describen el inventario conservado. **No son 233 aceptaciones
del futuro decoder**. CF-T4 no volvió a ejecutar el sondeo de las 570 copias
ni a adquirir RAM; no presenta esa evidencia histórica como prueba nueva.
Las fuentes, paquetes IR-T7, visor y runtime permanecen sin cambios en esta tarea.

## Vectores preparados

Se crean **dos fixtures base** y **50 casos materializados**: diez con vista
aceptada esperada y cuarenta con código de rechazo esperado. Cada entrada
contiene bytes hex, tamaño y SHA-256; las positivas incluyen la vista completa
esperada con los tipos y palabras f32. Todos los datos son propios, generados
sin abrir fuentes privadas ni importar código de producción.

- Principal, 1.008 bytes: triángulo, cuadrilátero y forma degenerada sin
  referencias; listas `[1,0,1]` compartidas, cola `[1]`, cabeceras opacas
  no constantes, selección no nula, cero negativo y padding propio no nulo.
- Mínimo, 752 bytes: cinco grupos sin formas activas y 80 listas vacías que
  comparten un terminador.
- Casos adicionales: celda 15, cuadrilátero no plano, máximo f32 finito,
  subnormal negativo y padding; errores de tamaño/rango/stride/alineación,
  terminadores incompletos, variantes, NaN/Inf, índices, grupo 4 activo y
  precedencia de errores.
- Fronteras de referencias materializadas: 512 frente a 513 por lista,
  y 4.096 frente a 4.097 totales. Ocho alias de una lista de 512 cuentan como
  4.096, aunque todos señalen a los mismos bytes.

Los casos no materializados todavía —barridos de cada componente/byte,
512/513 y 768/769 formas, tipos Python, máximo global de archivo, aislamiento,
metamórficas y ejecuciones con `-O`— están enumerados como aceptación obligatoria
de CF-T5. Las semillas no sustituyen esa batería.

## Comprobación de consistencia realizada

Un verificador local separado vuelve a leer los bytes de los vectores,
recorre sus offsets y contrasta las vistas esperadas campo por campo. No
importa el constructor, un decoder, herramientas del proyecto ni fuentes
privadas. Compara tipos, enteros, palabras y f32 exactos, incluido el signo
del cero; reproduce los cuarenta códigos de rechazo según las etapas del
contrato. Anclas literales de cabecera, índices, padding y conteo de alias
complementan el recorrido.

Resultado: **dos bases, diez expectativas positivas y cuarenta negativas
coherentes con el contrato**. Es una auditoría de los vectores, no una prueba
de un decoder de producción ni una medición de cobertura del mismo. El
comprobante declara `production_decoder_tests_executed=false`.

| Artefacto | Tamaño / SHA-256 |
|---|---|
| `tests/fixtures/synthetic/collision-polygons-v1.json` | 459.135 bytes; `f9218e872e29383dca73b03b895d746c991ee9c7e282d01de82a3863c1eb6b42` |
| Verificador local `build/collision-shapes/verify_contract_vectors.py` | `f553c9504336831df77e3111d61cc9e7460e25aa899c217f058d72faa459cde6` |

Comprobante de metadatos:
`reports/local/f03-04-collision-polygons-contract-v1.json`.
La repetición verifica que el contenido del comprobante existente coincide;
no lo reemplaza. Reproducción local:

```sh
rtk proxy .venv/bin/python build/collision-shapes/verify_contract_vectors.py
```

Los vectores públicos contienen su propio buffer y expectativas; su consumo
en CF-T5 no dependerá del generador o verificador locales bajo `build/`.

La validación documental `tools.qa.check_repository` pasa con cero errores;
`git diff --check` no encuentra problemas de whitespace. No se ejecutaron
pruebas del decoder ni un build ARM: esta entrega define el contrato y sus
vectores, sin implementar o modificar el runtime.

## Siguiente tarea

**CF-T5a:** implementar `decode_polygons` y `CollisionPolygonError` con el
contrato CP01–CP15, usando primero los vectores propios. **CF-T5b/c:** ampliar
la batería completa y el oráculo público independiente, verificar `-O`,
aislamiento y fronteras, e integrar el gate individual en CI. Después se
realizará el cotejo privado A/B de CF-T6 y se definirá la extensión del
intermedio de CF-T7.

No se habilita respuesta física; siguen abiertas la variante de 48 bytes,
las listas dinámicas superpuestas, daño/muerte, F03.04 global y G02/G03.
