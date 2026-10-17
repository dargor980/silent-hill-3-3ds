# F02.07 — Búsqueda estática del consumidor europeo

Fecha: 2026-10-17. Instancia `F02.07/camera-consumer-eu` completada como
investigación con dos candidatos; **consumidor semántico aún no confirmado**.
F02.07/G02 siguen abiertos. Próxima instancia: `camera-pointer-origin-eu`.

## Resultado

Dos inspecciones de la ISO europea producen informes idénticos y **dos sitios
candidatos**. Su secuencia combina avance de 128 bytes, lectura relativa de 68,
máscara del bit 0 y salto hacia atrás condicionado al resultado cero. Coincide
con una parte de la hipótesis anterior, pero no demuestra que el registro base
apunte a uno de los 285 archivos seleccionados ni que el flujo alcance esos sitios.

No se identificó todavía una función, carga de recurso o relación entre salas.
Los campos 92/108 y las colas de 384/768 bytes continúan sin explicación. No se
modifica el estado `candidate`/`unknown` del sondeo previo ni se versiona un decoder.

El ejecutable tiene 41 entradas PT_LOAD, de las cuales 40 carecen de bytes de
archivo. Varias regiones solo de memoria se solapan; su carga no se resuelve en
esta inspección. El único segmento con bytes está marcado RWX: **esa marca no
separa instrucciones de datos**. Una secuencia de palabras compatible puede ser
un falso positivo; hay pruebas propias que conservan esa incertidumbre.

## Contrato, arquitectura y procedencia

Se creó [CE01-CE08](../../schemas/camera-consumer-v1.md) antes de la implementación.
`elf32` valida estructura y traduce direcciones sobre un puerto mínimo;
`mips_camera` busca una secuencia de seis palabras; `camera_consumer` verifica la
identidad, coordina y publica. Se reutilizan `IsoImage`, carga JSON fijada por hash
y publicación exclusiva existente. No cambian lector privado, extractor ni runtime.

La búsqueda exige ADDIU o DADDIU +128 sobre el mismo registro, NOP, LW +68,
ANDI 1 sobre el resultado, BEQ con zero hacia atrás y NOP en delay slot. Comprueba
registros y destino dentro del mismo segmento. Es una política estrecha, no un
desensamblador R5900 ni un análisis de flujo completo. Puede omitir otros recorridos.
Las direcciones reales, destinos y hashes de ventanas quedan solo en metadatos privados.

El mapeo se basa en la documentación primaria de
[cabecera ELF](https://gabi.xinuos.com/elf/02-eheader.html) y
[program loading](https://gabi.xinuos.com/elf/07-pheader.html). Rechaza rangos ambiguos,
BSS como fuente de bytes, tamaños inválidos y desbordamientos. No certifica el ABI,
la carga de overlays, secciones, símbolos, relocaciones o permisos efectivos de PS2.
Presupuestos: 16 MiB de archivo, 128 program headers, lecturas de hasta 4096 bytes
y 1024 coincidencias; el solape de lectura evita perder patrones entre bloques.

Se consultaron codificaciones y cálculo de destinos en
[MIPS/binutils](https://github.com/MIPS/binutils-gdb/tree/9decc44bc67d9fb4248c2afe4fde77174e8abf80/opcodes).
Las cabeceras de los dos fuentes declaran GPLv3 o posterior; el archivo raíz
COPYING consultado contiene GPLv2 y no sustituye esas declaraciones específicas.
No se incorporó ni ejecutó código externo: implementación propia con `struct` y
stdlib, sin nuevas dependencias ni afirmación de clean room. Los fuentes se leyeron
en un temporal externo; [procedencia](../compatibility/camera-consumer-research-evidence.json).
No se enviaron datos privados a servicios externos ni se ejecutó el binario PS2.

## Evidencia reproducible

| Entrada o resultado | Tamaño / SHA-256 |
|---|---|
| ISO europea completa, releída en cada ejecución | 3.586.785.280 bytes / `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` |
| Perfil identificado | `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9` |
| Sondeo anterior, fijado sin modificar | `342f0a6323fed67dbf38f18b32938ac0578c5a06345f5d8a4fe5eb137c6dbee9` |
| Ejecutable de BOOT2 | 3.395.784 bytes / `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| Cada informe nuevo | 10.618 bytes / `64774dc66265cdac6d15b11db42b40890569e043474a6df4e6926407c8caaaeb` |

En cada ejecución se verifica la imagen completa, el conjunto de 113 rutas del
perfil y, individualmente, SYSTEM.CNF y su ejecutable. La búsqueda recorre
**3.392.384 bytes respaldados de un segmento**, con dos coincidencias sintácticas
y cero consumidores de cámara confirmados. No se vuelven a inspeccionar
individualmente los otros 111 miembros ni las dos extracciones privadas.

Resultados privados: `reports/local/f02-07-camera-consumer-v1.json` y
`reports/local/f02-07-camera-consumer-v1-repeat.json`, comparados byte a byte.
Solo contienen metadatos, sin bytes, instrucciones, cadenas o tablas de recursos.
No se exportó otra copia del ejecutable ni de los recursos.

Comandos exactos, tiempos y códigos de salida: `build/f02-07-camera-consumer/real-execution.json`.
La CLI reproducible es `python -m tools.inspectors.camera_consumer`, con ISO,
perfil, sondeo anterior, sus tres hashes y un destino JSON nuevo explícitos.
La publicación ocurre después del cierre estable de la ISO; un fallo tardío
impide publicar. No se sobrescriben destinos.

## Pruebas y pipeline

**116 pruebas nuevas; 1101/1101 aprobadas.** Cobertura global independiente:
**2039/2074 líneas (98,31 %)** y **692/714 ramas (96,92 %)**. Parser ELF y búsqueda:
100 % de líneas/ramas. Coordinador/CLI: 98,67 % de líneas y 95,83 % de ramas;
el único punto sin cobertura de ese módulo es el entrypoint `__main__`.

Fixtures ELF/MIPS propios: endian, cabeceras/tablas, segmentos, overflow, BSS,
solapes ambiguos, memoria sin bytes, traducción y rangos cruzados; registros,
desplazamientos signados, patrones engañosos, delay slot, bordes de bloque y
segmento, presupuestos, fallos tardíos, hash mezclado y salida exclusiva. Se
compara también el lector en memoria con una ISO sintética. No hay originales en CI.

El job quality existente descubre la suite automáticamente. Se ejecutaron
localmente pytest/JUnit, cobertura y sus umbrales independientes, Ruff/formato y
controles de arquitectura, custodia y enlaces de specs. La CI remota no se ejecutó.
No se recompiló C++/ARM: no cambió runtime, SDK ni configuración de compilación.
Hardware y gameplay siguen sin validarse con esta investigación.

Evidencias de pruebas, comprobación histórica y manifiesto de fuentes bajo
`build/f02-07-camera-consumer/`. El informe anterior y todos los fuentes de código
y pruebas previos permanecen intactos (53 archivos); se añaden tres módulos y un archivo de tests. Los cuatro recibos de extracción, catálogo y sondeos históricos conservan sus hashes. Manifiesto de 88 fuentes: 14475 bytes, SHA-256 `25555d9c960a31e2acb62efd9612700f3300727675a107fde206410093939601`; excluye este informe para evitar hash circular.

## Próxima observación necesaria

`F02.07/camera-pointer-origin-eu` deberá fijar el informe nuevo y estudiar los dos
sitios: comprobar límites de bloques, referencias entrantes y procedencia del
registro base antes de relacionarlo con la carga de un candidato. Registrar las
aristas conocidas y las instrucciones/llamadas sin resolver, respetando delay
slots y límites; no inferir una función por proximidad ni reutilizar direcciones US.

Si ese vínculo se demuestra, contrastar acceso a los campos 92/108 y al tramo
posterior al marcador con los hashes de recursos. Si no, concretar qué observación
estática o dinámica falta. La semántica, doce roles del corpus y par de salas
continúan pendientes; un informe reproducible de candidatos no cierra G02.
