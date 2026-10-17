# F02.07 — Procedencia candidata del puntero europeo

Fecha: 2026-10-17. Investigación acotada `camera-pointer-origin-eu` completada.
**El vínculo con un recurso de cámara continúa sin demostrarse**; F02.07/G02
permanecen abiertos. Siguiente instancia: `camera-caller-boundary-eu`.

## Resultado y alcance

Se construyeron grafos estáticos parciales para los dos sitios anteriores. Dos
ejecuciones sobre la ISO europea generaron informes idénticos. El primer seguimiento
llega a una referencia directa externa a la ventana y a una frontera sin predecesor
conocido; el segundo se detiene en dos llamadas. Estas son observaciones que permiten
concretar el siguiente experimento, no funciones ni rutas de ejecución confirmadas.

| Observación | Sitio A | Sitio B |
|---|---:|---:|
| Bytes en ventana local | 888 | 1836 |
| Palabras / aristas modeladas | 222 / 265 | 459 / 489 |
| Referencias directas hacia la ventana | 49 | 33 |
| Referencias cuyo origen está fuera de la ventana | 19 | 4 |
| Estados de procedencia visitados | 234 | 58 |
| Presupuesto agotado | No | No |
| Vínculos con recurso confirmados | 0 | 0 |

En A, el registro base es GPR4. Una referencia externa y una frontera sin predecesor
conocido aparecen cada una en dos estados, con y sin ajuste aritmético observado.
No equivalen a dos llamadores ni identifican un límite de función. En B, GPR16 queda
sin procedencia anterior atribuible porque dos llamadas son barreras: no se presupone
que un convenio de registros preserve su valor.

Los 49 terminales `revisited_state` son estados deduplicados por convergencia o ciclo,
no 49 bucles ni recursos. Se mantienen 26 y 40 palabras con efectos desconocidos en
las ventanas; ningún resultado constituye un análisis completo. Las condiciones de
ramas no se evalúan, las referencias indirectas no se resuelven y el segmento RWX
puede contener datos. La marca ejecutable y una coincidencia de codificación no
demuestran accesibilidad. Las direcciones concretas quedan en los informes privados.

No se interpretaron los campos 92/108 ni las colas de 384/768 bytes. El sondeo inicial
conserva sus 285 candidatos sin identificación semántica; capacidades y dependencias
del corpus no cambian.

## Contrato e implementación

Se definió [CP01-CP08](../../schemas/camera-pointer-v1.md) antes de implementar.
Tres módulos propios separan responsabilidades:

- `mips_flow`: subconjunto de efectos GPR y transferencias, sin I/O.
- `pointer_graph`: referencias, contextos de delay slot y seguimiento por predecesores
  sobre un puerto de lectura. No delimita funciones por proximidad.
- `camera_pointer`: reconcilia la evidencia, compone el lector ISO y publica metadatos.

Se reutilizan el mapeo ELF, la verificación de perfil/BOOT2, el sondeo del consumidor
y la publicación exclusiva. El informe anterior se regenera desde la ISO y se exige
igualdad canónica completa, incluidos los sitios y sus hashes, antes de seguirlos.
No se modifica el extractor, lector privado, runtime ni pipeline de compilación.

Una rama normal aplica su delay slot a ambas salidas; una rama likely lo aplica a
la tomada. J/JR no generan retorno inventado. La continuación de JAL/JALR es solo una
hipótesis a PC+8 y corta toda procedencia de GPR no cero tras la llamada. Una
transferencia en delay slot corta el camino. La entrada ordinaria a un slot existe
solo cuando hay una referencia directa; no se añade una continuación normal ficticia.

Copias y ajustes soportados propagan el registro sin calcular su valor final.
Cargas, constantes, sobrescrituras y operaciones desconocidas producen terminales
distintos. Las operaciones COP1 escalares concretas que no escriben GPR se modelan
solo con ese efecto; no se simulan números, excepciones ni condiciones FPU. Las demás
siguen desconocidas. No hay seguimiento interprocedural ni ejecución de código PS2.

Límites: 16 sitios, 4096 bytes/ventana y por lectura, 16 MiB de segmentos respaldados,
4096 referencias seleccionadas, 2048 aristas/ventana, 2048 estados y profundidad 512.
Un límite de seguimiento queda como desconocido explícito; identidad, I/O y límites
estructurales abortan sin publicar. El cierre estable precede a la publicación.

Codificaciones y PC relativo consultados en fuentes primarias
[MIPS/binutils](https://github.com/MIPS/binutils-gdb/tree/9decc44bc67d9fb4248c2afe4fde77174e8abf80/opcodes),
con hashes ya fijados y verificados. Se reutilizó esa consulta; no se descargó,
incorporó o ejecutó una biblioteca adicional. Los archivos declaran GPLv3 o posterior;
la implementación es propia y no se afirma clean room.
[Procedencia de esta instancia](../compatibility/camera-pointer-research-evidence.json).

## Evidencia real y custodia

| Entrada o salida | SHA-256 |
|---|---|
| ISO completa | `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` |
| Perfil | `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9` |
| Sondeo de cámara | `342f0a6323fed67dbf38f18b32938ac0578c5a06345f5d8a4fe5eb137c6dbee9` |
| Informe de consumidor anterior | `64774dc66265cdac6d15b11db42b40890569e043474a6df4e6926407c8caaaeb` |
| Ejecutable europeo | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| Cada informe nuevo, 32.892 bytes | `199e9265d65ba86c6977c49afe91c0971193d1e43e143b74a88223d69f90c59f` |

En cada ejecución se vuelve a verificar la ISO completa de 3.586.785.280 bytes,
las 113 rutas y, individualmente, SYSTEM.CNF y su ejecutable de 3.395.784 bytes.
El barrido recorre 3.392.384 bytes respaldados, además de las ventanas locales y
la regeneración del sondeo anterior. Los otros 111 miembros no se verifican
individualmente; las dos extracciones no se releen ni modifican.

Los resultados ignorados `reports/local/f02-07-camera-pointer-v1.json` y
`reports/local/f02-07-camera-pointer-v1-repeat.json` se compararon byte a byte.
Contienen posiciones, categorías, referencias, conteos y hashes, sin instrucciones,
bytes, constantes originales ni tablas de recursos. No se exportó otra copia de
originales ni se enviaron datos privados a servicios externos.

Comandos exactos y tiempos: `build/f02-07-camera-pointer/real-execution.json`.
CLI: `python -m tools.inspectors.camera_pointer`, con ISO, perfil, sondeo de cámara,
informe de consumidor, sus cuatro hashes y destino JSON nuevo explícitos.

## Validación

**139 casos nuevos; 1240/1240 pruebas aprobadas.** Cobertura global independiente:
**2331/2369 líneas (98,40 %)** y **843/868 ramas (97,12 %)**. Subconjunto de efectos:
100 % de líneas/ramas; grafo: 98,78 %/97,50 %; coordinador/CLI: 98,15 %/93,75 %.

Fixtures propios prueban destinos signados y región PC+4, JR/JALR, registros cero,
efectos conservadores, FP escalar, delay slots y likely, control dentro del slot,
entrada directa al slot, diamantes de control, sobrescrituras, llamadas, ciclos,
límites y fallos tardíos. Se compara memoria con ISO sintética y dos publicaciones;
la evidencia alterada se rechaza incluso si cambia solo versión, sitio o resumen.

El job quality existente descubre las pruebas sin originales ni dependencias nuevas.
Ruff/formato, cobertura independiente y contratos del repositorio: aprobados localmente.
JUnit, cobertura, comandos y manifiesto de fuentes quedan en
`build/f02-07-camera-pointer`. CI remota y hardware no se ejecutaron. No se repitieron
builds C++/ARM porque no cambiaron runtime, SDK o configuración de compilación.

Los 57 archivos previos de código/pruebas y el informe histórico del consumidor conservan sus hashes; también los cuatro recibos de extracción y los metadatos anteriores comprobados. El manifiesto de 95 fuentes mide 15676 bytes, SHA-256 `287c5e3a6b7cd495053df08734b3f6756edb81bfc1a5b33b7379841af32eacf5`; excluye este informe para evitar hash circular.

## Siguiente tarea: frontera del llamador

1. Fijar estos informes y revalidar origen, sitios y referencias. Usar las direcciones
   privadas registradas; no deducir funciones por cercanía ni reutilizar direcciones US.
2. Priorizar la referencia externa que alimenta GPR4 de A: seguir sus definiciones
   antes de la transferencia y aplicar el delay slot del llamador antes del estado
   de entrada. Distinguir argumento de entrada, retorno y valor previo.
3. Para B, comprobar en cada una de las dos llamadas el efecto sobre GPR16 con
   evidencia específica. Mantener la invalidación si no se demuestra preservación;
   no reemplazarla por una suposición ABI para desbloquear el análisis.
4. Si se alcanza una carga o tabla, probar la cadena hasta identidad/hash del recurso,
   manteniendo constantes, direcciones de carga y contenidos dinámicos separados.
   Si falta evidencia, definir el punto y captura dinámica necesarios; no afirmar
   que esa ejecución ocurrió. Solo después abordar cola y campos pendientes.

F02.07/Q05/G02 siguen abiertos: este avance concreta fronteras de investigación,
pero no identifica todavía un consumidor semántico, un decoder o un par de salas.
