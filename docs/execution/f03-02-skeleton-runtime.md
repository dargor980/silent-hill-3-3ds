# SA-T5 — Selección, reloj y pose en PCSX2

2026-10-20. **SA-T5a/b/c completadas** para la pareja MDL/ANM `0x0209`
de [SA-T1–SA-T4](f03-02-skeleton-animation.md). El juego enlazó ambos recursos
con un actor sin solicitar su carga ni modificar su posición. Se verificaron
la pose inicial y diez evaluaciones controladas del consumidor original.
Los tres clips tienen límites identificados, contador Q12 y composición
jerárquica contrastada con un oráculo matemático independiente.

**SA-T5d permanece abierta:** una [verificación posterior](f03-02-animation-continuity.md)
ya mide una vuelta continua y la selección inicial por IA; faltan las
transiciones de daño y muerte. Los ensayos de este documento
controlados restauran el mismo punto de entrada; no representan una partida
ininterrumpida. Tampoco prueban skinning, transformación a mundo o base 3DS.
Contrato y criterios: [SA08 y SR01–SR06](../../schemas/ps2-skeleton-animation-v1.md).

**Actualización SA-T5d:** el [arranque nuevo y la localización del actor](f03-02-animation-activation.md)
aclaran que esta instancia era de preparación y su slot se reutiliza antes
de la primera escena jugable. La ruta activa se localiza estáticamente en
`amusement_02`, sala `0xEB`, alcanzada en el ensayo posterior enlazado arriba.
Esta precisión no cambia las comparaciones del consumidor descritas aquí.

## Identidades y custodia

Se usa la ISO europea SLES-51434/PAL 1.02 y la pareja ya fijada en SA-T4.
Se verificó el ELF `SLES_514.34`, 3.395.784 bytes, SHA-256
`cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`.
Las direcciones de este informe corresponden a ese ejecutable europeo.

PCSX2: revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, candidato SRC51
existente; ejecutable SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
No se recompiló el emulador. Se crearon dos perfiles privados, con MTVU
desactivado y arranque pausado, BIOS y tarjetas copiadas del perfil anterior.
PINE identifica el proceso y verifica pausa antes de cada intervención.

Evidencia privada bajo `/Users/germancontreras/sh3-private-data/`:

- `f03-02-skeleton-runtime-v1/`: seis estados, selección e inicialización
  espontáneas; ninguna escritura en memoria del huésped.
- `f03-02-skeleton-runtime-v2/`: trece estados, diez controles admitidos,
  solicitudes con valores anteriores/posteriores y copia de la entrada en
  slot 90. Solo se cambian los campos de animación descritos abajo.

Ambos procesos terminaron normalmente con código 0; las comprobaciones de
cierre confirman perfil de origen sin cambios y sockets retirados. No se
copiaron recursos, RAM, BIOS, estados ni matrices del juego al repositorio.

## Asociación observada

Se restauró el estado previo de la primera zona, pausado en `GameMain`
`0x00194870`. La pareja ya estaba cargada. Al continuar, el juego creó el
actor tipo `0x0209`, sin inyección de recursos ni llamada artificial al loader.
Se pausó en el selector de tamaño, en la entrada del consumidor y a su retorno.

| Elemento | Dirección observada / comprobación |
|---|---|
| MDL | `0x0081A000`, 833.712 bytes; hash completo igual a SA-T4 |
| Cabecera del modelo | `0x0081A060` = MDL + 96 |
| ANM | `0x008E6000`, 3.500 bytes; hash completo igual a SA-T4 |
| Actor | `0x004484F0`, tipo `0x0209`, ID de instancia 0 |
| Estructura de animación | `0x00448750` = actor + `0x260` |
| Huesos | `0x004E60D0`, tres elementos de 224 bytes |
| Referencias del actor | +`0x308` → modelo; +`0x30C` → ANM |
| Referencias de animación | +4 → ANM +4; +`0x14` = 46 bytes/muestra |
| Descriptor inicial | `0x003DC52C`, clip `0x1449` |

El código de enlace en `0x0012F5D0` asigna las referencias desde el manager.
El selector `0x001DD0E0` devuelve 46 para este ID; breakpoint en `0x001DD300`.
El inicializador `0x002E0A00` selecciona el descriptor inicial. El consumidor
`0x0013F3E0` recibe `a0=0x00448750`, `a1=0`; su retorno se captura en
`0x001DD444`. Los hashes completos de MDL y ANM siguen coincidiendo en todos
los estados auditados. Se compararon con el ELF 16 ventanas de código.

## Clips y reloj

Los descriptores son registros de 12 bytes `<HHhHHBB>`: ID, cantidad,
velocidad con signo, inicio, final inclusivo, loop y padding.

| Descriptor | Clip | Muestras globales | Cantidad | Loop | Velocidad ELF → RAM |
|---|---|---|---:|---|---|
| `0x003DC52C` | `0x1449` | 0–23 | 24 | Sí | 2048 → 2457 |
| `0x003DC538` | `0x144A` | 24–46 | 23 | No | 2048 → 2457 |
| `0x003DC544` | `0x144B` | 47–75 | 29 | No | 2048 → 2457 |

La inicialización `0x001E2C00` recorre una tabla desde `0x003DBC20`, stride 12,
hasta el ID cero en `0x003DCF4C`; los tres clips ocupan índices 193–195.
Llama a `0x001DEA20`, que calcula `int16(trunc(speed × 60 / 50))`.
La auditoría verifica los **409 descriptores completos** contra el ELF,
admitiendo exclusivamente esa conversión en el campo velocidad. La evaluación
independiente de la secuencia entera coincide para los 65.536 valores i16.
Se comprobó el código y su resultado en RAM; no se capturó la ejecución de
esa inicialización.

El contador es relativo al clip, en unidades de **1/4096 de muestra**. La pose
usa el contador de entrada, antes de avanzar:

```text
current  = start + (counter >> 12)
fraction = (counter & 4095) / 4096
next     = current + 1; al final: start si loop, end si no
increment = (runtime_speed + signed_speed_offset) × ticks
```

`0x0013E170` escribe el incremento en un campo i16 y avanza el contador.
En loop resta la longitud inclusiva; sin loop lo limita a
`(end-start) × 4096` y termina con modo `0xFF`. El alcance verificado es
avance positivo, sin overflow i16, sin mezcla de clips y como máximo un wrap.
En modo de inicialización la pose se calcula pero el contador sigue en cero.
La ruta estática también detiene un clip sin loop cuando el contador de salida
es cero (por ejemplo, inicio con cero ticks); se cubre con fixture sintético,
sin atribuirlo a las capturas con ticks = 2.

`0x0019AC50` lee los ticks de `0x01CFB990`: valor **2** en los controles.
El código `0x0019AB10` limita los ticks a 1–3, con una ruta especial de pausa;
su rama PAL calcula `ticks/50`. En RAM se observaron `0x01CFB970 ≈ 0,04`
segundos y `0x01CFB968 = 25`. Son valores del reloj del juego, **no una
medición de 25 actualizaciones por segundo durante reproducción continua**.

Con offset 0, el incremento observado es 4914; con offset −512, 3890.
Las tasas nominales derivadas de 50 ticks/s serían respectivamente
29,99267578125 y 23,74267578125 muestras/s. No son FPS almacenados en el
ANM ni una frecuencia global para todos los recursos.

La lectura estática de `0x002E0F10`, `0x002E0FA0` y `0x002E1080` identifica
la selección de los tres IDs y llamadas a `0x001DDCE0` con ajuste −512.
Solo `0x1449` fue seleccionado espontáneamente en estas capturas; los otros
dos y el ajuste −512 fueron controles explícitos, no transiciones observadas.

## Composición de pose

`0x0013E2F0`/`0x0013E7A0` decodifican las muestras. `0x0013F340` compara el
producto escalar de cuaterniones y cambia el hemisferio cuando es negativo.
`0x0013EB70` interpola linealmente y normaliza (**NLERP**) antes de componer
las matrices. No se dedujo SLERP desde un importador.

El oráculo propio `tools/qa/animation_pose_oracle.py` opera en doble precisión,
sin importar el decoder, PCSX2, el renderer o filesystem:

- Matrices afines por columnas, vectores columna.
- Dos raíces independientes; jerarquía `[-1,-1,1]`.
- Rotación local desde NLERP de cuaterniones decodificados.
- Raíces: traslación almacenada en ANM. Es constante en esta pareja;
  no se valida aquí interpolación de una traslación variable.
- Hijo sin traslación ANM: offset obtenido de las matrices MDL con
  `R_parentᵀ × (t_child − t_parent)`. Su valor coincide con el offset runtime
  dentro de `1e-3` unidades originales.
- Pose global del hijo en espacio modelo: `pose_parent × local_child`.

Se contrastan los 16 elementos por hueso con la matriz runtime en +`0x10`.
Las filas afines y punteros padre/siguiente también se verifican. La matriz
MDL sirve aquí para recuperar el offset de reposo; eso no demuestra todavía
todo el contrato de bind/inverse-bind ni sus pesos de skinning.

Tolerancias absolutas fijadas antes de admitir resultados: `1e-5` para
rotación/fila afín y `1e-3` para traslación en unidades originales.
Error máximo de los diez controles: **2,31361305e-7** y **1,50094538e-4**,
respectivamente. La pose inicial espontánea también pasa: **1,15483999e-7**
y **9,34596872e-5**.

El control con fracción 0,25 distingue NLERP de SLERP (a mitad de intervalo
pueden coincidir). Los siguientes errores superan el gate:

| Alternativa incorrecta | Error máximo de rotación | Error de traslación |
|---|---:|---:|
| SLERP | 3,44800724e-5 | 0,00613547 |
| Omitir el padre | 1,17991275 | 1.020,31693 |
| Elegir muestra sin interpolar | 0,04693406 | 10,75903352 |

No se ejercitó la rama de producto escalar negativo con este ANM; su evidencia
es código estático más fixture sintético. No se aplica `(x,-y,-z)` en esta
comparación en espacio modelo. El paso a mundo, la base del visor y skinning
necesitan un contrato y controles propios.

## Controles, rechazos y reproducibilidad

Cada control restaura la misma entrada `0x0013F3E0` desde el slot 90 y ejecuta
el consumidor original hasta `0x001DD444`, sin parchear código, reloj o assets.
Los únicos campos autorizados, relativos a la estructura de animación, son:
contador +`0x18`, ajuste i16 +`0x24`, marcador de recarga +`0x2C`,
modo +`0x30` y descriptores +`0x40`/+`0x44`. La solicitud registra únicamente
los valores que cambian. Se exige una transición comprobable desde un bloque
distinto al bloque de entrada para evitar confundir una restauración pendiente.

| Slot v2 | Clip | Contador de entrada | Muestras/fracción evaluadas | Contador de salida |
|---:|---|---:|---|---:|
| 4 | `0x1449` | 2048 | 0 → 1 / 0,5 | 6962 |
| 5 | `0x1449` | 0 | 0 → 1 / 0 | 4914 |
| 6 | `0x1449` | 96256 | 23 → 0 / 0,5 | 2866 |
| 7 | `0x1449` | 51200 | 12 → 13 / 0,5 | 56114 |
| 8 | `0x144A` | 0 | 24 → 25 / 0 | 4914 |
| 9 | `0x144A` | 92160 | 46 → 46 / 0,5 | 90112, detenido |
| 10 | `0x144B` | 0 | 47 → 48 / 0 | 4914 |
| 11 | `0x144B` | 116736 | 75 → 75 / 0,5 | 114688, detenido |
| 12 | `0x1449` | 2048 | 0 → 1 / 0,5, ajuste −512 | 5938 |
| 13 | `0x144A` | 46080 | 35 → 36 / 0,25 | 50994 |

Se conservan los controles rechazados:

- v2 slots 1/2: PC seguía en la entrada; la acción UI no ejecutó instrucciones.
- v2 slot 3: primera restauración indistinguible del estado ya cargado.
  El contador quedó en inicialización; no demuestra el control solicitado.
- v1 slots 5/6: pausas posteriores en espera de BIOS/carga. El contador del
  caballo permaneció en cero; no son evidencia de cadencia continua.

Los recibos v1 01/02 heredaron por error `controlled_stream_request=true`
del helper anterior. No hubo escrituras al huésped; el auditor registra la
corrección sin modificar esos recibos ni los estados originales.

Informe local determinista: `reports/local/f03-02-skeleton-runtime-v1.json`,
11.885 bytes, SHA-256
`f98f79391f29699ca7e868449d2f1ffb32179f9239d35b1dc63db203b95334da`.
Incluye hashes de todas las capturas, solicitudes admitidas, ventanas de
código, errores, rechazos y cierres. No exporta matrices o muestras.

Entrada espontánea v1/03 y baseline v2/90:
`180db1856ae2268d6f4434d489e4a00be6b7a7f6e6766de5a88b20f6bc25a30c`.
Retorno inicial v1/04:
`cf8b6785d3f2163a39c3c1838295ebcc51fdd56b9312140354aa09de1cc99d0e`.
Control discriminante v2/13:
`44cc7fc9457d394fe6bcc2b6d34c26b9e337bd002f338654c8e96c491a522ca1`.

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-runtime/audit_runtime.py
rtk proxy .venv/bin/python -m pytest -q \
  tests/python/test_animation_pose_oracle.py tests/python/test_skeleton_animation.py \
  --cov=tools.qa.animation_pose_oracle \
  --cov-report=json:build/f03-02-skeleton-runtime/coverage.json \
  --junitxml=build/f03-02-skeleton-runtime/pose-tests.xml
```

**108 pruebas aprobadas**, incluidas 31 nuevas con datos analíticos propios.
Cobertura del oráculo: **79/79 líneas y 34/34 ramas**. Comprueban hemisferio,
fracción que distingue interpoladores, producto padre/hijo no conmutativo,
bosque con padre posterior, bucle inclusivo, clamp y validación de entradas.
El job Python existente descubre las pruebas sin originales ni emulador.
No se ejecutó CI remota ni se generó un build ARM en esta tarea.
Ruff, formato, gate independiente de cobertura y contratos del repositorio:
aprobados. Repetir el auditor produce el mismo informe byte a byte.

Manifiesto de 15 fuentes propias, contrato, scripts del experimento y
dependencias directas de inspección:
`build/f03-02-skeleton-runtime/source-manifest.json`, 2.790 bytes, SHA-256
`ed73e716e0f1ea045f20cbede1565c113270d528592ee960b6ce3e4f78404c34`.
Excluye datos privados, referencia externa y este informe.

## Referencia auxiliar y continuación

Se consultó, sin ejecutarlo ni incorporarlo como dependencia,
[anime.c de memory-of-alessa](https://github.com/dreamingmoths/memory-of-alessa/blob/247c7f43fd619aff8d2086ea0b0af291c283ea9d/silent-hill-3/src/Chacter/anime.c)
y cabeceras relacionadas, fijadas en la revisión
`247c7f43fd619aff8d2086ea0b0af291c283ea9d`.
La copia consultada de `anime.c` tiene SHA-256
`98630639a113133e6ef7d77d01d3d406378fd707084664555cfab6cc5b850e7d`.
Las direcciones y layouts relevantes se comprobaron de nuevo en el ELF
europeo y RAM: la cabecera de referencia no coincidía con los offsets reales
de descriptores +`0x40`/+`0x44`.

La siguiente verificación SA-T5d debe obtener una secuencia sin restauraciones
en una escena activa: mismos actor/recurso, contador creciente y wrap,
ticks y ciclos registrados, además de selección de clip por IA cuando ocurra.
El arranque nuevo descrito en [SA-T5d](f03-02-animation-activation.md) ya llega
a juego activo; el pendiente es alcanzar el escenario que instancia `0x0209`,
sin interpretar la residencia de sus archivos como continuidad de un actor.
GC-T4 puede usar ya la composición modelo verificada, manteniendo pendientes
transformación mundo, base 3DS, skinning y mezcla de clips.
