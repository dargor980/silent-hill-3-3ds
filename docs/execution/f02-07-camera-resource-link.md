# F02.07 — Muestras de memoria frente al catálogo europeo

2026-10-17 · `camera-resource-link-eu` · [RL01–RL08](../../schemas/camera-resource-link-v1.md).

**Búsqueda exacta completada:** diez muestras de cinco puntos, 1.740 recursos y
1.562.367.840 bytes verificados en cada copia; seis hits sobre un único recurso.
Dos informes finales idénticos. El recurso es candidato: falta demostrar la carga,
el mapeo efectivo y las modificaciones que conectan esos datos con el consumidor.
La instancia de vínculo de origen y F02.07/Q05/G02 permanecen abiertas.

## Resultado

| Punto observado | Muestra de 64 bytes | Muestra de 256 bytes |
|---|---|---|
| A, entrada después del slot | Coincide en offset 0 | Coincide en offset 0 |
| B1, entrada | Coincide en offset 0 | Sin coincidencias exactas |
| B1, retorno | Coincide en offset 0 | Sin coincidencias exactas |
| B2, entrada | Coincide en offset 0 | Sin coincidencias exactas |
| B2, retorno | Coincide en offset 0 | Sin coincidencias exactas |

Los seis hits son **seis contextos/tamaños de muestra sobre un recurso**, no seis
recursos distintos. El candidato tiene 1.536 bytes:

- ID: `asset:f8328806a743597779f6bfa4b32167d33d52456a8da0d71b7f9edf38cf41e58b`.
- SHA-256 completo: `2d2737c5cd1f2f1f7ebada1dd9e9e67617a39a6ac171842c9da6028619900bfb`.

Las cuatro muestras de 256 bytes de B son iguales entre sí. El GPR4 de entrada de A
y los GPR16 de esos cuatro puntos B también son iguales en sus 32 bits bajos; esa
comparación auxiliar se hizo sobre la captura privada fijada por hash, sin publicar
direcciones. Por tanto, bajo la hipótesis del mapeo directo, el contenido observado
difiere entre la entrada de A y B en algún lugar dentro de offsets 64–255, aunque
el valor base sea el mismo. Esto **no identifica todavía el escritor ni un campo**.

No se compararon los 1.536 bytes completos en RAM ni se trazó la carga. No se
decodificó el TLB: los offsets bajos se interpretan conforme al mapeo inicial de
PCSX2, una hipótesis explícita que debe comprobarse para afirmar el vínculo.
Las muestras negativas no descartan bytes transformados, otros rangos o recursos
fuera del subconjunto MFA, incluidos XBG0/AFS. Los campos 92/108 y la semántica de
cámara siguen pendientes; `resource_links` y `capabilities` permanecen vacíos.

## Implementación y límites

`state_memory` toma PC/registros del mismo estado que contiene `eeMemory.bin`, exige
CRC ELF, versión fijada, ausencia de delay slot y coincidencia exacta con el evento
CO. Acepta solo RAM normal de 32 MiB y muestras de 64/256 bytes en el rango físico
bajo. Rechaza alias, memoria extendida, scratchpad, punteros nulos y rangos cruzados.
El CRC ZIP de la RAM completa se comprueba aunque el daño quede fuera de la muestra.

El lector ZIP y la custodia PS01–PS07 se reutilizan: el lector de CPU sigue leyendo
solo sus dos miembros; la nueva función de inspección recibe un decodificador y
conserva los mismos controles de hash, permisos, enlaces y estabilidad. No exporta RAM.

`resource_match` busca en streams con bloques de 1 MiB y solapamiento de hasta 255
bytes. Detecta hits entre bloques y solapados sin duplicarlos. Calcula el SHA-256 del
recurso completo; `VerifiedResourceScanner` conserva descriptores, valida archivo y
raíz y vuelve a verificar identidades y conjunto de archivos al cerrar. El coordinador
`resource_link` reconcilia catálogo/recibo de extracción, revalida CO, importa los
nueve estados, selecciona muestras y compara ambas copias antes de publicar.

Límites: diez patrones, 4 GiB por copia, 100.000 recursos y 128 hits por patrón en
total. Un exceso falla sin publicar éxito. Un patrón uniforme queda explícitamente
`non_discriminating`; si todos lo son, no se informa una búsqueda negativa. En la
ejecución real los diez patrones resultaron buscables y no se alcanzó ningún límite.

Responsabilidades de formato, I/O, búsqueda y coordinación permanecen separadas.
No cambian dependencias, parser MFA, contratos CO históricos ni runtime 3DS.
Las fuentes oficiales de PCSX2 se consultaron como hechos del formato; URL, versión,
hash y licencia están en [SRC26](../compatibility/camera-resource-link-evidence.json).
No se incorporó código externo ni se declara clean room.

## Ejecución y reproducibilidad

La sesión original es `bdaad9edb3134b5fa876ae7ba60d0d99`. Se conservaron sus estados,
captura y configuraciones. **PCSX2 no se abrió** ni se alteraron originales. El índice
que vincula secuencias y estados se creó en una carpeta privada nueva 0700, archivo
0600; su ubicación y todos los argumentos están en
`build/f02-07-camera-resource-link/inputs.json`.

Se fijaron seis documentos por hash: plan, ambos recibos CO, catálogo, recibo final
de extracción e índice de estados. Se contrastó la captura privada con CO y se
releyeron nueve estados antes de seleccionar muestras y nuevamente antes del cierre.
Cada informe verifica las dos copias completas. Se reconcilia evidencia histórica;
no se recalculó la ISO ni se regeneró el catálogo desde ella en esta etapa.

Informes finales:
`reports/local/f02-07-camera-resource-link-v1-final.json` y
`reports/local/f02-07-camera-resource-link-v1-final-repeat.json`.
Ambos tienen **7.642 bytes**, SHA-256
`30611f6f1af92a1c5363474af0b76a5805222824c8a50065aa1d93daf3a62842`.
Duraciones finales: 9,62 y 8,88 segundos. No se interpretan como benchmark.
Los informes preliminares se conservaron y tienen los mismos bytes; los finales
repiten el experimento tras añadir la detección de archivos extra antes del cierre.

La CLI es `rtk proxy .venv/bin/python -m tools.inspectors.resource_link --help`.
Exige rutas/hashes explícitos y rechaza salidas existentes. Argumentos, código de
salida y duración se conservan en `build/f02-07-camera-resource-link/real-execution-final.json`.
Publicación y chequeo de custodia se ejecutan secuencialmente.

## Pruebas y pipeline

**1.583 pruebas Python aprobadas**, incluidas 66 nuevas. Cubren RAM de tamaño real
con datos propios, PC/GPR/CRC incorrectos, alias y límites, CRC fuera de muestra,
lecturas cortas, coincidencias entre bloques/solapadas, mismos bytes en contextos
distintos, muestras uniformes, presupuesto global, hash/permisos/enlaces, cambios
tardíos y fallo de cierre. La CLI se prueba con evidencia sintética positiva y
negativa, resultados distintos entre copias y ausencia de publicación tras error.

Se corrigió un import faltante en un fixture positivo; no hubo relajación de la
validación para pasar esos casos. La suite completa se ejecutó después de finalizar
las publicaciones reales. Cobertura: **98,70 % de líneas / 97,42 % de ramas**; gate
independiente ≥80 % aprobado. Ruff check/format y controles del repositorio aprobados. Cobertura y JUnit quedan en
`build/f02-07-camera-resource-link/coverage.json` y `pytest.xml`.

El job `quality` existente incorpora estas pruebas automáticamente, sin estados ni
recursos reales. Los fixtures usan ZIP stored/deflate; la ejecución privada usa el
soporte Zstandard del Python 3.14.6 local. No se ejecutó CI remota ni compilación 3DS:
la implementación de esta etapa solo afecta herramientas Python de investigación.

## Continuación necesaria

La próxima subtarea es `camera-resource-link-eu/origin`: ampliar el contrato para
comparar los 1.536 bytes del candidato, localizar diferencias entre estados sin
publicarlas, comprobar el mapeo y seguir el escritor/cargador. Empezar por el intervalo
entre entrada A y entrada B1; el retorno de A ya está preservado, pero su GPR4 cambió,
por lo que la comparación deberá conservar explícitamente la base de entrada.
La [tarea detallada](../specs/sh3-3ds/tasks/F02.md) mantiene este criterio de cierre.
