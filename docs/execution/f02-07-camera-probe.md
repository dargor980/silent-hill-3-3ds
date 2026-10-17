# F02.07 — Investigación y sondeo de cámara

Fecha: 2026-10-17. Completada la investigación inicial y el sondeo
`sh2-road128-reference-v1` dentro de `F02.07/formato-camera`.
**La interpretación del formato SH3 sigue pendiente**; no se cierra F02.07/G02.
Siguiente instancia: `F02.07/camera-consumer-eu`.

## Resultado y decisión

Los **285 candidatos** de la edición europea coinciden con la hipótesis numérica
de registros de 128 bytes terminados por una bandera. Esto permite delimitar un
prefijo repetible, pero **154 archivos presentan valores fuera de los rangos de
la referencia SH2**. Se conserva `candidate`/`unknown` para todos: no se trasladan
semántica, coordenadas ni comportamiento por analogía entre juegos.

La referencia primaria es la definición `VC_ROAD_DATA` y su recorrido de SH2 en
[vc_main.h](https://github.com/dreamingmoths/memory-of-alessa/blob/89c61883dd2ad5390223ba37d9bbacc62783d371/silent-hill-2/src/view/vc_main.h)
y [vc_main.c](https://github.com/dreamingmoths/memory-of-alessa/blob/89c61883dd2ad5390223ba37d9bbacc62783d371/silent-hill-2/src/view/vc_main.c).
La bandera ocupa offset 68 y el consumidor de esa referencia se detiene ante su
bit 0. El proyecto advierte que su investigación está en curso y su objetivo
SH3 usa otra región; no demuestra el consumidor de SLES-51434.

También se consultó [sh3redux](https://github.com/Palm-Studios/sh3redux/blob/50d10aef1b9afbfbf2ae5946a511a2c5e0a2f106/include/SH3/camera/camera.hpp)
y su [discusión de formatos](https://github.com/Palm-Studios/sh3redux/issues/131):
la clase de cámara no aporta un lector `.cam` completo y la interpretación de
esos archivos se describe como pendiente. Los comentarios sobre SH2 se usan
solo como orientación, no como documentación normativa de SH3.

Se revisaron además índices públicos de Sparagas, Murugo, SH3-Modding y
sh3-modlib, sin localizar un parser de cámara en los árboles examinados. No se
afirma que no exista otra implementación. Las nueve fuentes descargadas para
lectura quedaron en un temporal externo; el repositorio conserva únicamente
[URLs, commits, tamaños, hashes y finalidad](../compatibility/camera-research-evidence.json).
No se ejecutó ni incorporó código externo y no se enviaron archivos privados.
Las licencias declaradas consultadas son MIT para memory-of-alessa y texto
GPLv3 para sh3redux; no se atribuyen esos términos a recursos del juego.

## Contrato e implementación

[CAM01-CAM08](../../schemas/camera-probe-v1.md), ligados al
[ticket F02.07](../specs/sh3-3ds/tasks/F02.md#f0207). El sondeo puro no recibe nombres
ni rutas; el coordinador valida evidencia y usa el puerto del lector privado
existente. La CLI reutiliza publicación exclusiva de JSON. Se mantienen separados
I/O, observación y decisión sobre soporte; no cambia el runtime ni el extractor.

La hipótesis utiliza little endian, bloques de 128 bytes, primer marcador y
finitud de las primeras 16 interpretaciones float32 de los registros anteriores.
Los rangos comparados proceden de SH2. El campo de offset 80 queda sin comparar
porque la referencia expresa incertidumbre sobre su enum. No se inventan ejes,
unidades, FOV, referencias a salas ni etiquetas para valores adicionales.

El marcador y todo lo posterior permanecen opacos. Solo se guardan longitud/hash
de la cola, conteos e IDs; no registros, cadenas, coordenadas, hex/base64 ni bytes.
Una coincidencia estructural puede darse en datos ajenos: un fixture propio lo
demuestra y comprueba que no se eleva a cámara identificada. La extensión solo
selecciona el experimento. Presupuesto: 4096 bytes por candidato, máximo 32 bloques.

## Evidencia real

Se fijaron y comprobaron las entradas históricas antes de interpretar:

| Entrada | SHA-256 |
|---|---|
| Catálogo F02.04 | `39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d` |
| Recibo final F02.05 | `74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943` |
| Inventario inicial F02.07 | `d5e6de2d1c03f053cedeb488390b5d250f5129aba804ab4fbac54eaeb81a3c57` |
| Cada sondeo nuevo, 277.784 bytes | `342f0a6323fed67dbf38f18b32938ac0578c5a06345f5d8a4fe5eb137c6dbee9` |

El coordinador contrasta las identidades de los 1740 recursos del inventario con
catálogo/recibo y comprueba el conjunto de archivos de la copia. Relee y verifica
íntegramente los **285 seleccionados por copia**; no vuelve a verificar el contenido
de los otros 1455 ni la ISO en esta instancia. No se creó otra extracción.

| Observación bajo la hipótesis | Resultado |
|---|---:|
| Candidatos examinados / coincidencias | 285 / 285 |
| Registros anteriores al primer marcador | 934 |
| Archivos con marcador en el primer bloque | 18 |
| Archivos con cola opaca de 384 bytes | 261 |
| Archivos con cola opaca de 768 bytes | 24 |
| Discrepancias de rango, offset 72 / 76 | 0 / 0 |
| Discrepancias de rango, offset 92 / 108 | 12 / 284 |
| Archivos con al menos una discrepancia | 154 |
| Tipos semánticos identificados | 0 |

Los 18 prefijos vacíos no se interpretan como ausencia de cámaras. Las colas no
se declaran padding. Los conteos por campo pueden coincidir en un mismo registro;
no equivalen a cantidades de cámaras ni a unidades del corpus confirmado.

Los informes `reports/local/f02-07-camera-v1.json` y
`reports/local/f02-07-camera-v1-repeat.json` son idénticos; comandos/copias/duración
están en `reports/local/f02-07-camera-execution-v1.json`. Todos son metadatos
ignorados. El control exploratorio previo de otro sufijo no entra en la selección
y excede el presupuesto del sondeo: no se presume un negativo estructural.

## Validación y pipeline

**66 casos nuevos; 985/985 pruebas aprobadas.** Cobertura global:
**1857/1891 líneas (98,20 %)** y **619/640 ramas (96,72 %)**. Sondeo puro: 100 %
en ambas métricas; coordinador/CLI: 98,73 % de líneas y 95,83 % de ramas.

Pruebas propias: fronteras de presupuesto/alineación, endian, marcador ausente,
marcadores posteriores opacos, bandera combinada, no finitos antes/después,
rangos SH2, falsos positivos conservadores, documentos mezclados, IDs duplicados,
lector defectuoso, alteración/hash y publicación. No se modificó el lector privado;
sus pruebas existentes y las de extracción/SIGKILL permanecen aprobadas.

El job quality existente descubre las nuevas pruebas sin originales ni nuevas
dependencias. Evidencias locales en `build/f02-07-camera`: pytest/JUnit, cobertura,
comandos y controles. La ejecución remota de CI y hardware siguen pendientes.
No se recompiló C++/ARM: no cambió runtime, SDK ni configuración de compilación.

Ruff, formato de 53 archivos Python, umbrales independientes de cobertura y
controles de arquitectura/custodia/trazabilidad: **aprobados localmente**.
Se conservaron sin cambios los 50 archivos previos de código/pruebas y los cuatro
recibos F02.05; también catálogo, inventarios iniciales e informe histórico.
El manifiesto nuevo de 81 fuentes mide 13.289 bytes, SHA-256
`22abeaccb4b8f13a2c0dbe0f083274c4c78f679bdcd9c1088ac9f1967ca51e04`.
Excluye este informe para evitar hash circular. La comprobación histórica de
metadatos no se presenta como relectura de los payloads fuera de esta selección.

## Próxima instancia: consumidor europeo

1. Fijar identidad del ejecutable PS2 europeo desde el perfil y leerlo con custodia
   y límites. Su investigación debe tener contrato propio aunque figure fuera del
   subconjunto MFA. No copiar direcciones de la edición estadounidense.
2. Preparar inspección estática reproducible, con fixtures ELF/MIPS propios para
   traducir direcciones/rangos y rechazar offsets inválidos. Registrar versión y
   procedencia de cualquier herramienta antes de incorporarla; no ejecutar el
   binario PS2 como programa host ni exportar instrucciones originales al repo.
3. Localizar evidencia de las lecturas del bloque y la bandera, y cómo se usa el
   tramo posterior. Distinguir funciones candidatas de referencias demostradas;
   resolver primero 384 frente a 768 bytes y los campos 92/108.
4. Solo tras comprobar el consumidor, versionar el contrato SH3 y añadir fixtures
   por variante. Mantener por separado estructura, unidades/ejes, relaciones a salas
   y comportamiento. Si falta evidencia, registrar el siguiente experimento preciso.

Los doce roles del corpus y el par de salas continúan pendientes. Q05/G02 siguen
abiertos; coincidencias y cobertura de tests no demuestran gameplay ni hardware.
