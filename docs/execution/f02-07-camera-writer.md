# F02.07 — Primera escritura modificadora observada durante A

2026-10-17 · `camera-resource-link-eu/origin/runtime-writer` ·
[WR01–WR08](../../schemas/camera-writer-v1.md) ·
[metadatos SRC28](../compatibility/camera-writer-evidence.json).

**Avance parcial:** en una sesión nueva se capturó un par coherente con una escritura
SW en el delay slot de BEQ. Escribe cuatro bytes en offset relativo 84; tres cambian,
exactamente `[85,88)`, el primer intervalo observado en SRC27. El resto del rango
de 1.536 bytes permanece igual en ese paso. No se capturó el retorno en esta sesión
ni se demostró la traducción física o el cargador. F02.07/Q05/G02 siguen abiertos.

## Observación y límites

Se restauró una copia fijada de la entrada A de SRC27 en un perfil privado nuevo.
La primera parada coincide en PC y en los 64 bits bajos de los 32 GPR con la copia
restaurada; el rango completo coincide con el hash del recurso candidato. Se conservó
la base de entrada durante las siete paradas. Las lecturas virtuales coinciden con
el rango físico hipotético en los siete estados. Esta igualdad no prueba el mapa.

| Secuencias de la sesión nueva | Evidencia | Resultado |
|---|---|---|
| 1 | Entrada restaurada | 1.536 bytes iguales al candidato |
| 2→3 | Primer hit y paso, SW directa | Sin cambio; auxiliar, falta segunda lectura del código |
| 4→5 | Segundo hit y paso, SW directa | Par validado: escribe en offset 64, cero bytes distintos |
| 6→7 | Tercer hit y paso, BEQ+SW | Par validado: offset 84, tres bytes distintos `[85,88)` |

El tercer watchpoint detuvo el depurador antes de BEQ; su instrucción siguiente
contiene la SW. Se amplió WR04 antes de implementar este caso. Se conservaron ocho
bytes de código y se releyeron en la misma posición tras el paso: ambos hashes son
iguales. El validador exige condición BEQ evaluada con 64 bits, PC posterior esperado,
GPR bajos de 64 bits sin cambios y efecto exacto de la SW dentro del rango completo.
No basta con que el depurador haya alcanzado una dirección ni con comparar solo PC+4.

En esta captura el estado anterior al tercer hit sigue teniendo el hash completo del
recurso. El paso explica tres de los cuarenta bytes que diferían en el retorno de
la captura histórica. La comparación entre sesiones no demuestra que se haya
observado la causa de los otros 37 bytes ni todos sus escritores.

La casilla de desactivación del watchpoint no respondió a las acciones automatizadas.
Se aplicó el cierre parcial permitido por WR08 después del primer cambio, sin
reanudar para simular una cobertura completa. No se midió tiempo de CPU acumulado;
no se acredita el límite de 60 segundos con tiempo de pared. Las capturas corresponden
a tres hits observados. El plan original conserva su estado histórico `not_performed`;
SRC28 registra esta ejecución parcial por separado.

PCSX2 se cerró mediante su menú. Se comprobaron ausencia de proceso/socket,
`EnablePINE=false` y hashes intactos del INI, configuración de breakpoints y ambas
tarjetas del perfil habitual. El perfil temporal utilizó copias de las tarjetas;
archivos nuevos privados quedaron con permisos 0600 y directorios 0700. La BIOS,
ISO, estados históricos y extracciones se conservaron. Estados, registros,
instrucciones y lecturas originales permanecen fuera del repositorio.

## Implementación y procedencia

- `writer_state` reutiliza el lector ZIP/CPU fijado a PCSX2 v2.8.2, añade GPR de 64
  bits bajos y extrae un rango ≤4096 bytes. Mantiene el contrato histórico `EEState`.
- `store_pair` es puro: acepta SW directa o BEQ+SW, evalúa flujo y efecto, rechaza
  instrucciones no soportadas, desalineación, overflow de PC, rango incompleto,
  cambios de GPR y diferencias fuera del store. Distingue escribir y modificar.
- `camera_writer` coordina lectores privados, hashes, orden/sesión/entorno,
  revalidación de estados y publicación exclusiva después del cierre. Importa
  plan/SRC27 por hash; no repite extracción ni la investigación histórica completa.

La captura normalizada vincula siete estados y dos pares. Las declaraciones de
sesión, pausa, paso y cierre no constituyen autenticación independiente: el recibo
mantiene `execution_authentication: not_provided`. No se elevan coincidencias a
`resource_links`, capacidades o semántica de cámara. La prueba real acredita
coherencia de evidencia aportada y la observación descrita en este informe.

Las fuentes oficiales v2.8.2 se consultaron para contrastar comportamiento:
[SW](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/R5900OpcodeImpl.cpp),
[BEQ](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/Interpreter.cpp),
[paso del depurador](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2-qt/Debugger/DebuggerWindow.cpp),
[modelo de breakpoints](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2-qt/Debugger/Breakpoints/BreakpointModel.cpp)
y [PINE](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/PINE.cpp).
URL, hash, tamaño y licencia por archivo están en SRC28. Se usaron como referencia;
no se incorporó su código ni ninguna dependencia nueva al proyecto.

## Reproducción y validación

`reports/local/f02-07-camera-writer-v1.json` y
`reports/local/f02-07-camera-writer-v1-repeat.json`: **6.814 bytes**, SHA-256
`e526f58772c790d471293c288a1b311559cc4a23941c1ff102dca355c443ed20`.
Dos análisis de la **misma captura** producen recibos idénticos; no son dos sesiones
de emulación. Captura normalizada SHA-256
`1f5f7593c9579c0c93f15c9f6b5adb47f46e06c7d790448669f06fb1f4a2e86d`.

La CLI es `rtk proxy .venv/bin/python -m tools.inspectors.camera_writer --help`.
Los argumentos fijados están en `build/f02-07-camera-writer/inputs.json` y la identidad
de ejecución en `session.json` del mismo directorio ignorado. En la raíz privada de
la sesión se preservaron manifiesto, helper de captura, estados, lecturas y cierre.
El helper solicita el guardado asíncrono, espera archivo estable e importable y
comprueba pausa antes/después; la respuesta PINE sola no se acepta como guardado.

**71 pruebas nuevas y 1.720 pruebas Python aprobadas.** Fixtures propios para SW con
y sin cambio, BEQ tomada/no tomada, operandos iguales solo en sus 32 bits bajos,
desplazamientos negativos, registro cero, límites, datos alterados, sesión/orden/CRC
incorrectos, mezcla de estados, código cambiado, error de cierre y publicación.
Cobertura: **3465/3509 líneas (98,75 %)** y **1123/1154 ramas (97,31 %)**;
gate ≥80 %, Ruff y formato aprobados. La validación del repositorio se registra en
SRC28. El job `quality` existente descubre estos tests sin originales.
No se ejecutaron CI remota ni compilación C++/3DS en esta etapa de herramientas Python.

## Siguiente tarea: repetir el par y capturar retorno

`F02.07/camera-resource-link-eu/origin/runtime-writer/repeat-return`:

1. Definir ampliación EARS para retorno y repetición entre sesiones. Conservar SRC28
   como parcial; no rellenar sus eventos faltantes ni modificar la captura histórica.
2. Crear perfil/sesión nuevos desde la entrada fijada. Derivar de nuevo la base y
   configurar antes del arranque watchpoint solo en `[84,88)` más breakpoint de
   retorno. Esto evita depender de desactivar la casilla durante la ejecución;
   observar un subrango no acredita cobertura de todas las escrituras del candidato.
3. Capturar entrada, par BEQ+SW y retorno con los 1.536 bytes, código antes/después,
   hashes y contexto. Si otro hit aparece, conservarlo; detenerse en límites del plan.
4. Extender el coordinador con fixtures propios de retorno erróneo, repetición en
   la misma sesión, captura parcial y diferencias entre ejecuciones. Contrastar el
   par con SRC28 y el retorno con SRC27, manteniendo resultados separados.
5. Investigar el mapa virtual efectivo con evidencia de sus páginas. Si solo hay
   igualdad de contenido, conservar `mapping_verified=false`. La carga anterior a A,
   los otros escritores y los 37 bytes restantes requieren tareas posteriores.

Cierre de esta subetapa: dos sesiones con par comparable y retorno observado en la
nueva, recibos repetibles y calidad aprobada. No cierra F02.07 ni identifica todavía
tipos, semántica de campos o dos salas conectadas del slice.


La continuación quedó completada en [SRC29](f02-07-camera-return.md): par repetido
en otra sesión y retorno completo coincidente. Esta captura SRC28 conserva su
carácter parcial; no se rellenan sus eventos faltantes.
