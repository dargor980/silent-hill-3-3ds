# F02.07 — Comparación completa y primer intervalo de modificación

2026-10-17 · `camera-resource-link-eu/origin` · [OR01–OR08](../../schemas/camera-origin-v1.md).

**Comparación completada:** los 1.536 bytes del candidato coinciden por completo con
el rango físico hipotético en la entrada de A. Al retornar A difieren 40 bytes; el
rango permanece idéntico en las seis observaciones posteriores. Dos ejecuciones
producen informes idénticos. Esto acota el intervalo observado de modificación,
pero no identifica aún la instrucción escritora, el cargador ni la traducción efectiva.
F02.07/Q05/G02 y el vínculo de origen siguen pendientes.

## Resultado contrastado

Se conserva la base GPR4 de la entrada A, validada contra su estado. El GPR4 del
retorno no se reutiliza como base. Se examina esa misma posición física hipotética
en ocho estados de la captura `bdaad9edb3134b5fa876ae7ba60d0d99`.

| Secuencia | Punto | Diferencias frente al recurso | Diferencias frente al estado anterior comparado |
|---|---|---:|---:|
| 2 | Entrada A | 0 | — |
| 3 | Retorno A | 40 | 40 |
| 4 | Antes de B1 | 40 | 0 |
| 5 | Entrada B1 | 40 | 0 |
| 6 | Retorno B1 | 40 | 0 |
| 7 | Antes de B2 | 40 | 0 |
| 8 | Entrada B2 | 40 | 0 |
| 9 | Retorno B2 | 40 | 0 |

Candidato de SRC26: ID
`asset:f8328806a743597779f6bfa4b32167d33d52456a8da0d71b7f9edf38cf41e58b`,
SHA-256 completo `2d2737c5cd1f2f1f7ebada1dd9e9e67617a39a6ac171842c9da6028619900bfb`.
Se comprobaron sus bytes completos en ambas extracciones y se reprodujo previamente
la búsqueda RL completa de 1.740 recursos/1.562.367.840 bytes por copia, en cada ejecución.

Las diferencias son 16 intervalos, expresados sin bytes ni direcciones: para cada
`i = 0…7`, `[85 + 128i, 88 + 128i)` y `[98 + 128i, 100 + 128i)`. Los extremos son
offsets relativos con final excluido. La periodicidad de 128 bytes es observable;
no basta para atribuir tipos, punteros, significado de campos ni transformaciones.
Los campos 92/108 permanecen sin semántica demostrada.

La primera divergencia capturada está entre las secuencias 2 y 3. No se observaron
instrucciones intermedias: A, sus llamadas o actividad concurrente podrían contribuir.
La igualdad de estados posteriores tampoco demuestra ausencia de escrituras que
dejen el mismo valor o que se reviertan entre observaciones. Una coincidencia completa
con el archivo no demuestra por sí sola qué operación lo llevó a memoria.

## Implementación y contrato

El contrato OR se escribió antes del código. `origin_memory` valida CPU/evento fuente,
conserva una base inmutable y exige sesión, entorno, orden y CPU/evento destino.
Lee como máximo 4096 bytes desde RAM normal de 32 MiB, con validación CRC completa
del miembro ZIP y rechazo de alias/rangos fuera del límite. La sesión procede de
la captura CO validada; los estados no autentican por sí mismos una sesión de ejecución.

`origin_compare` es una comparación pura que devuelve hashes, igualdad, conteos e
intervalos contiguos; no devuelve bytes. `resource_origin` compone plan fijado,
reproducción RL, lectores privados, comparaciones y publicación exclusiva.
El adaptador del candidato reutiliza la verificación de archivo y estabilidad hasta
cierre. Todos los estados se releen antes del cierre; errores tardíos impiden publicar.
El lector RL v1 y sus muestras de 64/256 bytes conservan su significado.

El plan exige un hit RL de 256 bytes en offset cero del candidato y compara el archivo
entero de 256–4096 bytes. Acepta de 2 a 16 estados ordenados, incluyendo primero la
fuente. Se procesa un ZIP ≤64 MiB y RAM ≤32 MiB por vez; no se exporta RAM al disco.
Las responsabilidades de formato, comparación, I/O y coordinación están separadas.
No cambian parser MFA, dependencias ni runtime 3DS.

## Traducción de memoria: evidencia que sigue faltando

El lector compara offsets de `eeMemory.bin`; no decodifica el TLB ni observa el mapa
virtual efectivo. PCSX2 guarda TLB junto a estructuras internas y su preparación tras
cargar un estado ajusta entradas que difieren del contexto anterior. Por ello se
requiere evidencia de la nueva ejecución al restaurarlo.
[Fuente: SaveState.cpp v2.8.2](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/SaveState.cpp).

Las operaciones de mapeo/desmapeo pueden cambiar las páginas. Las lecturas del
depurador EE utilizan la lectura segura virtual, que consulta `vmap` por página.
Esto ofrece una vía para contrastar contenido en una sesión pausada; una igualdad
de contenido, por sí sola, no acredita identidad de la página física subyacente.
[COP0.cpp](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/COP0.cpp),
[DebugInterface.cpp](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/DebugTools/DebugInterface.cpp),
[vtlb.cpp](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/vtlb.cpp).

Se consultaron esas fuentes oficiales fijadas a v2.8.2, GPL-3.0+, como documentación
de comportamiento. URL/hash/tamaño están en [SRC27](../compatibility/camera-origin-evidence.json).
Sus copias temporales permanecen fuera del repositorio; no se incorporó código externo.
El informe mantiene `mapping_verified: false` y `origin_status: pending`.

## Reproducción y pruebas

Informes: `reports/local/f02-07-camera-origin-v1.json` y
`reports/local/f02-07-camera-origin-v1-repeat.json`, **19.343 bytes** cada uno,
SHA-256 `0a08d220a0913719deecab4bcc12ebda038f73c7dc0aa5a427f940180c9cea95`.
Tiempos 9,70 y 9,63 segundos, sin interpretación de benchmark. La CLI es
`rtk proxy .venv/bin/python -m tools.inspectors.resource_origin --help`.
Argumentos, hashes, códigos de salida y duración están en
`build/f02-07-camera-origin/{inputs,real-execution,real-execution-repeat}.json`.

Se fijan nueve documentos y la captura: seis entradas RL, sus dos informes finales
y el plan OR. No se recalculó la ISO ni se regeneró el catálogo; se reconcilian sus
identidades históricas. PCSX2 no se abrió; estados, capturas y extracciones originales
no se modificaron. Los datos reales se leyeron exclusivamente desde la raíz privada.

**66 pruebas nuevas; 1.649 pruebas Python aprobadas.** Cubren base de retorno cambiada,
sesión/entorno/orden, PC/GPR/delay slot, CRC de identidad, alias, límites, fragmentación,
evidencia de candidato insuficiente, discrepancia entre copias y cambios/cierres tardíos.
La CLI se prueba con cadena sintética completa, dos informes idénticos y conservación
de origen pendiente incluso cuando los estados comparados son iguales.

Cobertura global independiente: **3318/3361 líneas (98,72 %)** y
**1110/1140 ramas (97,37 %)**; gate ≥80 % aprobado. Los módulos puros nuevos tienen
cobertura completa; el entrypoint del coordinador se ejerció en las dos ejecuciones
reales. Ruff, formato y controles del repositorio aprobados. JUnit y cobertura están
en `build/f02-07-camera-origin`.
El job `quality` existente incorpora los fixtures sin originales. No se ejecutó CI
remota ni compilación C++/3DS: esta etapa solo añade herramientas Python.

## Plan concreto de continuación

Se preparó `reports/local/f02-07-camera-origin-writer-plan-v1.json`, estado
`not_performed`, 2.568 bytes, SHA-256
`396c05cf8d5e2c339d7498537134128bdf1602ea33d4870a52f608d7acaea45a`.
Es un plan de observación, no una captura ni una configuración ya aplicada.

1. Crear una sesión privada nueva y preservar el estado histórico de entrada A por
   su hash. Registrar versión/binario/BIOS/configuración; reimportar PC y GPR4 después
   de restaurar. No añadir eventos a la captura histórica.
2. Verificar la traducción efectiva de todas las páginas que cubran los 1.536 bytes.
   Registrar evidencia del mapa y del rango leído virtualmente en el mismo punto;
   si falta la primera, mantener la hipótesis explícita aunque coincidan los hashes.
3. Observar escrituras al rango completo desde entrada hasta retorno A. Usar los
   16 intervalos como prioridades; derivar direcciones solo en el entorno privado.
   Detenerse al retorno, 256 hits o 60 segundos de ejecución, lo que ocurra primero;
   alcanzar un límite deja la observación incompleta.
4. Por hit, registrar PC/contexto de delay slot, dirección efectiva, ancho y hashes
   antes/después. Demostrar solapamiento real con el rango; el PC de parada por sí
   solo no identifica una escritura. Distinguir stores de CPU de otros escritores.
5. Repetir en otra sesión y contrastar el resultado completo de retorno. Después
   localizar la carga anterior a A y enlazar rango del contenedor/recurso con destino.
   Restaurar la entrada A comienza después de la carga y no puede demostrarla.
6. Antes del lector de esa nueva evidencia, fijar contrato EARS y fixtures de
   traducción ausente, escrituras fuera de rango, eventos mezclados y fallos tardíos.
   Mantener capacidades vacías hasta una cadena de origen reproducible.
