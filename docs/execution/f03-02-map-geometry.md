# F03.02 — Primer grupo de geometría MAP decodificado

2026-10-20. Completadas MG-T1–MG-T3 del
[contrato MG01–MG07](../../schemas/ps2-map-geometry-v1.md).
El grupo 304 del [mapa candidato](f03-02-map-material-candidate.md) produce
**dos formas, 56 vértices y 32 triángulos, sin degenerados**. La lectura
independiente del OBJ coincide con posiciones, UV y caras del JSON.
Las dos extracciones privadas generan archivos idénticos.

Esta evidencia corresponde a geometría local inspeccionada en el host.
No demuestra todavía objeto/sala, matriz del juego, asignación de textura,
normales, colores, alpha ni presentación de esta geometría en 3DS.
MP-T4, MG-T4 y F03.02 global permanecen abiertas.

Actualización: [MR-T1–MR-T3](f03-02-map-render-metadata.md) localizan la matriz
base y corrigen el nombre heredado de +20: el valor 1 de ambas formas es una
palabra de modo, no un índice directo de matriz. Los bundles históricos siguen
conservando ese campo como no verificado; no se les aplica una transformación.

## Datos observados

| Forma, offset | Vértices | Triángulos | Omisiones de strip | Rango leído |
|---:|---:|---:|---:|---|
| 448 | 26 | 16 | 10 | 512 / 416 bytes |
| 928 | 30 | 16 | 14 | 992 / 480 bytes |

Las posiciones forman dos superficies rectangulares subdivididas, separadas
en X; todos sus vértices tienen Z local = −796. Se inspeccionaron la proyección
X/Y y los trazados UV de cada forma. La vista UV contiene trazados superpuestos;
no se corrigieron ni se dedujo su uso material. La imagen es un diagnóstico
geométrico sin textura, no una captura del juego.

Ambas formas conservan el índice de transformación 1, candidato CLUT 0 y
campos opacos de malla `[1,0,1]`. No se aplica la matriz del importador de
referencia ni se interpreta el flag como transparencia: eso requiere comprobar
el consumidor PS2. La paleta 0 usada anteriormente en el visor de textura sigue
siendo una elección de inspección, no una asociación probada con estas caras.

## Implementación y conservación de datos

Decoder puro con dataclasses inmutables, sin filesystem ni SDK. Cada registro
se separa en posición i16, palabras UV i16 y tres atributos empaquetados i16.
La reconstrucción de los ocho componentes reproduce exactamente los 16 bytes
originales de cada registro; no se elimina el bit de omisión de U.

La triangulación sigue la convención de las referencias fijadas en MP: el
bit 0 de U omite el triángulo que termina en ese vértice; la paridad avanza por
índice y se reinicia por forma. Se rechaza una cara antes del tercer vértice.
Los triángulos degenerados se conservan y cuentan mediante área entera exacta.
No se sueldan vértices ni se fabrican caras para formas sin triángulos.

El coordinador vuelve a recorrer el MAP y verifica el presupuesto del grupo
antes de leer sus payloads, en fragmentos de hasta 4096 bytes. Reutiliza el
catálogo/recibo fijados y el adaptador que comprueba SHA-256 completo por rango.
El exportador OBJ es independiente: índices `v/vt` globales desde 1,
un objeto por forma y sin material, textura ni normales inventadas.
Posiciones locales sin giro/escala; UV de vista `(U/32768, 1-V/32768)`.

El writer privado compartido añade un conjunto cerrado de dos archivos:
`geometry.json` e `inspection.obj`. Verifica escrituras, conserva parciales
ante fallo y publica el manifiesto al final, después de cerrar el lector.
Archivos 0600 y directorios 0700, fuera del repositorio.

## Validación

**253/253 pruebas aprobadas**, incluidas **45 nuevas**:
geometría 45, MAP 72, decoder de textura 57, visor/empaquetado 44 y repositorio 35.
Se prueban signos y extremos i16, paridad tras omisiones, separación de formas,
caras prematuras, degenerados, reconstrucción, conteos inválidos, límite 65536,
lecturas fragmentadas, presupuesto previo, integridad, selección ausente,
conjunto modificado, salida ocupada y fallo de publicación.

Los tres módulos nuevos y el writer compartido alcanzan **191/192 líneas
(99,48 %) y 59/60 ramas (98,33 %)**. Decoder puro, OBJ y writer: 100 %.
La línea restante es el despachador `__main__`, ejecutado mediante subprocess
y las dos conversiones privadas. Gate de líneas/ramas, Ruff y contratos del
repositorio aprobados.

Informes: `build/f03-02-geometry/tests-final.xml`, `coverage-final.json`.
El manifiesto de las fuentes y dependencias locales transitivas contiene 24
archivos: `build/f03-02-geometry/source-manifest.json`, SHA-256
`456df3c40e18c3bab81f23402b5d228ec43db78e67cd472552f8c781740a54c4`.
Metadatos de ejecución: `reports/local/f03-02-geometry-execution-v1.json`.
El primer pase de 216 pruebas se conserva; el pase final incorpora casos de
fragmentación y conteo corto, más los contratos del repositorio.
CI recoge los tests por su job Python existente, sin datos originales ni red.
No se atribuye ejecución remota de CI ni recompilación ARM a esta instancia.

## Evidencia privada y repetición

Sesiones relativas a la raíz privada autorizada:
`f03-02-geometry-a-v1/` y `f03-02-geometry-b-v1/`.
Los dos archivos y sus manifiestos coinciden byte a byte:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `geometry.json` | 20364 | `c0a002d48a0c98caaaa99ebc546ef8b157b82778549c2f572b7f331e094146b4` |
| `inspection.obj` | 3700 | `dca3ec27ac86db2464ea27e8d69529bb4a2f2b7c9b9deee6c50e53b01499d39b` |
| `manifest.json` | 2617 | `6714a2c7f96c4c168cdd0fe02583041f42876f3f84fab351cb35bf9248053318` |

El script local `build/f03-02-geometry/inspect_geometry.py` compara ambos
bundles y parsea el OBJ sin usar el encoder de producción. Coinciden 56
posiciones, 56 UV y 32 caras, incluidas las referencias entre objetos.
Resultado: `build/f03-02-geometry/independent-inspection.json`.
La inspección PNG se generó con Pillow del runtime de documentos, sin nuevas
dependencias del pipeline; se abrió y comprobó visualmente.
Ruta privada: `f03-02-geometry-inspection-v1/geometry-preview.png`, SHA-256
`8f3324fc421b071e70b00393eb7280cf073a3e4a06f0cd3c0ee79bb2110d4867`.
Ni OBJ, JSON de vértices ni imagen se incorporan al checkout/CI.

```sh
rtk proxy .venv/bin/python -m tools.pipeline.decode_map_geometry \
  --catalog reports/local/f02-04-asset-catalog.json \
  --catalog-sha256 39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d \
  --receipt /raiz/privada/f02-05/verified.json \
  --receipt-sha256 74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943 \
  --private-copy /raiz/privada/f02-05/copy-a \
  --private-root /raiz/privada \
  --resource-id asset:464325b2533b0e0a0702d4ad52f7050d41e9a02ba308dea7bce2a3268e83d4ae \
  --group-offset 304 --run-id nueva-geometria
```

Sustituir la raíz por la autorizada y usar otro run-id para copy-b.
Continuidad: [GI-T1–GI-T5](f03-02-geometry-inspection.md) presentan esta
geometría con material diagnóstico, ya confirmada por el usuario en New 2DS XL. Para fidelidad al juego siguen pendientes
el rastreo de selección textura/CLUT y una captura de dibujo identificada en
PS2; el aspecto plausible de las superficies no cierra esa comparación.
