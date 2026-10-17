# F02.07 — Estado en fronteras de llamada del ejecutable europeo

Fecha: 2026-10-17. Instancia `camera-caller-boundary-eu` completada como investigación
estática acotada. **No se ha demostrado un vínculo con un recurso de cámara.**
F02.07/Q05/G02 permanecen abiertos. Sigue `camera-runtime-observation-plan-eu`.

## Resultado

El argumento de A se forma en el delay slot del llamador: una copia soportada lleva
GPR6 a GPR4 antes de entrar. Por tanto, seguir únicamente el GPR4 anterior a la
llamada no describe su argumento de entrada. La procedencia de GPR6 sigue abierta:
la ventana alcanza una referencia externa y una frontera sin predecesor conocido.
La referencia externa procede de una posición posterior a la llamada; no es por sí
sola otro llamador ni una función identificada. No se obtuvo una carga con identidad
de recurso demostrable.

En B no se probó la conservación de GPR16 en ninguna de las dos llamadas. El primer
destino encuentra una operación cuyo efecto no está soportado; el segundo alcanza
un delay slot no soportado. Ambos permanecen como barreras, sin asumir registros
preservados por convenio. No se atribuyó semántica a las operaciones desconocidas.

| Frontera | Ventana llamador / destino | Estados del destino | Resultado |
|---|---:|---:|---|
| A, GPR4 | 524 / 4096 bytes | 169 | Entrada desde GPR6; efecto al retorno sin demostrar |
| B, primera llamada, GPR16 | 524 / 4096 bytes | 2 | Efecto desconocido detiene exploración |
| B, segunda llamada, GPR16 | 524 / 4096 bytes | 2 | Slot no soportado detiene exploración |

El destino de A alcanza una misma posición de retorno con dos estados abstractos:
en uno se conserva la identidad y en el otro no puede probarse. Esto no prueba dos
retornos ejecutados ni dos valores distintos. Quedan 14 estados repetidos por
convergencia/ciclo. No se agotaron presupuestos; tampoco se obtuvo un resumen global
de preservación. Las ventanas son límites de inspección, no tamaños de funciones.

Las tres consultas por frontera distinguen estado anterior a llamar, entrada después
del slot y continuación hipotética tras retorno. Las llamadas conservan su barrera
en los informes anteriores. Las direcciones concretas, referencias y hashes de
ventanas están exclusivamente en metadatos locales ignorados.

## Contrato e implementación

[CB01-CB08](../../schemas/camera-boundary-v1.md) se escribieron antes del código.
La implementación separa tres responsabilidades:

- `callee_flow`: explora control e identidad de los 32 bits bajos de GPR; sin I/O.
- `call_boundary`: selecciona fronteras, lee mediante puerto, consulta procedencia
  y registra puntos de observación privada.
- `camera_boundary`: reconcilia evidencia, compone ISO/perfil y publica el resultado.

Se fija el hash de ambas copias del sondeo anterior y se exige igualdad. Se regenera
la cadena consumidor → punteros desde la ISO, y se compara todo el informe canónico
antes de utilizar sus posiciones. El coordinador reutiliza contratos existentes;
no modifica los inspectores históricos, el extractor ni el runtime.

El nivel interprocedural es uno: no se entra en llamadas anidadas. El destino explora
ramas normales y likely con sus slots, saltos directos y JR GPR31 cuando conserva
la procedencia del retorno antes del slot. Otros indirectos, efectos desconocidos,
slots de control, salidas de ventana, estados repetidos y límites impiden declarar
preservación global. Solo las copias soportadas conservan identidad; otras escrituras
pueden conservar el valor real, pero el análisis no lo demuestra.

Guardar un registro y cargarlo desde memoria no acredita preservación: no existe
modelo de alias ni del contenido de memoria. Los fixtures comprueban expresamente
que esa secuencia permanece desconocida. No se simulan excepciones, condiciones de
ramas, los 128 bits completos del GPR ni ejecución PS2.

Presupuestos: 16 fronteras; 524 bytes por ventana del llamador; hasta 4096 por destino
y lectura; 1024 estados y profundidad 256 por destino. Las referencias y trazas del
llamador heredan los límites CP02-CP06. No se infieren límites de función por saltos
vecinos. Los segmentos RWX pueden contener datos: coincidencia sintáctica y PF_X no
acreditan ejecución.

Se revalidaron las fuentes primarias de codificaciones y transferencias
[MIPS/binutils fijadas por commit](https://github.com/MIPS/binutils-gdb/tree/9decc44bc67d9fb4248c2afe4fde77174e8abf80/opcodes).
No se añadió dependencia, descargó otra biblioteca o incorporó código externo.
Los archivos consultados declaran GPLv3 o posterior; no se afirma clean room.
[Procedencia](../compatibility/camera-boundary-research-evidence.json).

## Repetición y custodia

Las dos salidas `reports/local/f02-07-camera-boundary-v1.json` y
`reports/local/f02-07-camera-boundary-v1-repeat.json` son idénticas byte a byte:
**26.060 bytes**, SHA-256
`dc3db465ca79b45b5e6f052b611027fb573732b15f5f5b251f3ae9a4d961bc6d`.
Cada una contiene tres fronteras, cero preservaciones globales demostradas en el
modelo y cero vínculos de recurso confirmados. Capacidades vacías.

| Entrada verificada | SHA-256 |
|---|---|
| ISO europea completa | `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` |
| Perfil | `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9` |
| Sondeo cámara | `342f0a6323fed67dbf38f18b32938ac0578c5a06345f5d8a4fe5eb137c6dbee9` |
| Consumidor | `64774dc66265cdac6d15b11db42b40890569e043474a6df4e6926407c8caaaeb` |
| Cada copia del sondeo de punteros | `199e9265d65ba86c6977c49afe91c0971193d1e43e143b74a88223d69f90c59f` |
| Ejecutable europeo | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |

Cada ejecución verifica los 3.586.785.280 bytes de ISO, sus 113 rutas y los hashes
individuales de SYSTEM.CNF y ejecutable. No se verifican individualmente los otros
111 miembros ni se releen las dos extracciones. La regeneración conserva los límites
y alcance de los informes anteriores. La publicación es exclusiva y posterior al
cierre estable; no se sobrescriben informes históricos.

Los JSON contienen posiciones, relaciones, categorías, conteos y hashes; no incluyen
instrucciones, bytes, tablas, textos ni constantes originales. No se generaron
nuevas copias de payloads ni se enviaron datos privados a servicios externos.
Comandos, tiempos y salidas: `build/f02-07-camera-boundary/real-execution.json`.
CLI: `python -m tools.inspectors.camera_boundary`, con todos los archivos/hash de
entrada y destino nuevo explícitos.

## Validación

**67 casos nuevos; 1307/1307 pruebas aprobadas.** Cobertura global independiente:
**2510/2549 líneas (98,47 %)** y **912/938 ramas (97,23 %)**. Los dos módulos de
análisis nuevos alcanzan 100 % de líneas y ramas; el coordinador alcanza 56/57
líneas y 15/16 ramas, con la entrada `__main__` ejercida aparte por ambos sondeos reales.

Fixtures propios cubren argumento en slot, lectura del enlace nuevo, valor al retornar,
retornos divergentes, guardado/restauración, likely, destinos fuera de rango, indirectos,
recursión, límites y fallos de lectura. El análisis con fronteras no vacías coincide
en memoria e ISO sintética. CLI, repetición, rechazo de identidad/evidencia modificada,
salida exclusiva y fallo al cerrar también están cubiertos.

Ruff, formato, cobertura independiente y contratos de arquitectura/custodia/enlaces
pasan localmente. El job quality existente descubre estos casos sin originales ni
cambio de pipeline. JUnit, cobertura, manifiesto, entorno y comprobaciones quedan en
`build/f02-07-camera-boundary`. CI remota y hardware no se ejecutaron; C++/ARM no se
recompilaron porque no cambiaron runtime, SDK ni configuración de compilación.

Los 131 archivos de la línea base conservan sus hashes, incluidos los 61 archivos
previos de código/pruebas y los informes históricos. Los cuatro recibos de extracción
también coinciden; sus payloads no se releyeron. Los nuevos JSON mantienen modo 0600
y están ignorados por Git, al igual que la ISO. El manifiesto de 102 fuentes mide
16.877 bytes, SHA-256
`3dd3e239c896c1712177bc8a43cb83ac97926ec002621dfbd7a45e8b46d45761`;
excluye este informe para evitar una referencia circular.

## Siguiente observación

El informe privado incluye un plan inicial, marcado `not_performed`, con puntos
antes de llamar, entrada después del slot, retorno si se alcanza, GPR relevantes
(incluido GPR6 en A), GPR31 y las fronteras desconocidas del destino. Incluye los
rangos de código y SHA-256 esperados para contrastar la versión antes de observar.
No contiene un hash esperado de recurso: su identidad sigue desconocida. El rango
de datos deberá derivarse del puntero observado y del catálogo validado.

`F02.07/camera-runtime-observation-plan-eu` deberá concretar el entorno PS2 disponible,
un contrato de captura privada y su validador, sin afirmar que estos puntos se hayan
alcanzado. La primera evidencia buscada es GPR6 del llamador frente a GPR4 de entrada
en A; para B, comparar GPR16 al entrar y retornar, con flujo observado y versión
identificada. Una igualdad en una ejecución solo prueba esa observación, no todos
los caminos. Después habrá que demostrar la cadena hasta ID/hash del recurso.

Los 285 candidatos, colas y campos 92/108 mantienen el estado anterior. No hay decoder
de cámara, lógica jugable ni dos salas identificadas como consecuencia de este avance.
