# Sondeo de cámara v1 — hipótesis road128

Instancia F02.07/formato-camera; RF02.02/RF02.08/RF13.02, RNF06.01/.04/.07,
RNF07.06-.09 y RNF11.05-.09; V02/V20/T02. Amplía investigación, no capacidades.

## Evidencia y decisión

Se consulta la definición pública `VC_ROAD_DATA` de **SH2** y su recorrido en
`vcSetNearRoadAryByCharaPos`, fijados al commit
`89c61883dd2ad5390223ba37d9bbacc62783d371` de
[memory-of-alessa](https://github.com/dreamingmoths/memory-of-alessa/blob/89c61883dd2ad5390223ba37d9bbacc62783d371/silent-hill-2/src/view/vc_main.h).
La definición ocupa 128 bytes y el recorrido termina por el bit 0 del campo de
offset 68. Es una referencia de otro juego, no un contrato confirmado para SH3.
Su [consumidor SH2](https://github.com/dreamingmoths/memory-of-alessa/blob/89c61883dd2ad5390223ba37d9bbacc62783d371/silent-hill-2/src/view/vc_main.c)
no demuestra la interpretación en el ejecutable europeo de SH3.

Los 285 recursos locales seleccionados por sufijo tienen tamaño múltiplo de 128,
un marcador bajo esa hipótesis y un tramo posterior no resuelto. Valores de
algunos campos difieren de los rangos de referencia. Por ello se implementa un
**sondeo numérico**, no un decodificador de cámara. No se copia ni ejecuta código
externo; se atribuye la consulta de formato y no se afirma clean room. Versiones,
licencias declaradas y hashes consultados quedan en
[procedencia](../docs/compatibility/camera-research-evidence.json).

## EARS

- **CAM01** WHEN recibe catálogo, recibo e inventario THEN SHALL comprobar hashes fijados y concordancia de origen, selección e identidades antes de leer. La selección SHALL usar únicamente el indicio `.cam` del catálogo verificado, sin elevarlo a tipo.
- **CAM02** WHEN inspecciona un recurso seleccionado THEN SHALL usar el lector privado existente, comprobar el archivo completo y limitar el rango a 4096 bytes. Un recurso mayor SHALL conservarse desconocido por presupuesto, sin lectura parcial presentada como aceptación.
- **CAM03** WHEN evalúa road128 THEN SHALL exigir bytes completos, tamaño positivo múltiplo de 128 y presupuesto ≤4096; SHALL localizar el primer registro cuyo uint32 little endian en offset 68 tenga bit 0 activo. Sin marcador SHALL devolver desconocido, sin resultado parcial aceptado.
- **CAM04** WHEN examina registros anteriores al marcador THEN SHALL comprobar que sus primeras 16 interpretaciones float32 little endian son finitas. IF esa condición falla THEN SHALL indicar hipótesis no compatible, sin afirmar corrupción del formato SH3.
- **CAM05** WHEN encuentra el marcador THEN SHALL registrar índice, cantidad de registros anteriores, bytes posteriores y hash de ese tramo opaco; SHALL no interpretar el marcador ni el tramo posterior como registros activos, padding, nombres, offsets o cámaras adicionales.
- **CAM06** WHEN compara campos con SH2 THEN SHALL contar discrepancias respecto a los rangos de referencia, conservándolas como evidencia que limita la transferencia de semántica; SHALL no relajar esos rangos ni inventar nombres para nuevos valores de SH3.
- **CAM07** WHEN publica resultados THEN SHALL conservar `state=candidate`, `type=unknown`, dependencias no inspeccionadas, capacidades vacías y corpus pendiente incluso si la hipótesis coincide. El reporte SHALL distinguir fallo de hipótesis de fallo de I/O/identidad; este último aborta la ejecución completa.
- **CAM08** WHEN repite la investigación THEN SHALL producir metadatos deterministas por ID y por copia; SHALL no exportar registros crudos, coordenadas, cadenas ni bytes. Las pruebas/CI SHALL usar fixtures propios, incluyendo un parecido sintético que coincida sin convertirse en cámara identificada.

## Método y límites

`camera_probe` es puro y opera sobre bytes verificados. No recibe nombre ni ruta.
`camera_survey` reconcilia las evidencias, selecciona los IDs, usa el puerto
`CandidateReader` y agrega resultados. CLI reutiliza publicación exclusiva de
metadatos. No cambian extractor, lector privado, inventario histórico ni runtime.

Hipótesis `sh2-road128-reference-v1`: registros de 128 bytes desde offset 0,
bit 0 en uint32 LE de offset 68. La primera coincidencia delimita el prefijo;
datos posteriores quedan opacos aunque contengan otra palabra parecida a bandera.
Una bandera con otros bits no se normaliza: se informa su presencia. Cero
registros anteriores es un resultado numérico válido, no ausencia de cámaras.

Comparación numérica por registro anterior: offset 72 contra 0..3; 76 contra
0..5; 92 contra 0..1; 108 contra 0..5, según la referencia citada. Se usan nombres
por offset, no etiquetas semánticas de SH3. Offset 80 se deja sin comparar porque
la propia referencia expresa incertidumbre sobre su enum. No se imponen
geometría, orden min/max, ejes, unidades, FOV, conexiones o comportamiento.

Salida v1: hashes de entradas, selección por IDs, contadores de registros bajo
hipótesis, histograma de longitudes de cola, discrepancias por offset, resultados
desconocidos tipados y siguiente experimento. Presupuesto máximo 32 registros
por archivo; el límite es de investigación, no una especificación del juego.
Sin formato completo demostrado no se produce `identified`, `decoded` ni
`validated`. Los bytes opacos permanecen exclusivamente en las copias privadas.

## Aceptación de esta instancia

Pruebas propias de límite exacto/exceso, endian, terminador ausente/múltiple,
no finitos antes/después del marcador, rangos de referencia, I/O, evidencias
mezcladas, orden determinista y falso positivo conservador. Dos sondeos reales
idénticos, matriz de pendientes, cobertura independiente ≥80 %, Ruff y custodia.
El cierre del sondeo deja abierta la identificación semántica: el próximo paso
debe contrastar el consumidor del ejecutable PS2 europeo y el tramo opaco.
