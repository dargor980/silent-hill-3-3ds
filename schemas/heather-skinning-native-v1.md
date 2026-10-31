# HSN v1 — paletas y vectores del prototipo híbrido

Contrato HS-T2, 2026-10-30, **specified_not_integrated**. Implementación
posterior HS-T3; entrega ARM HS-T4 y ejecución GPU/medición física HS-T5.
No cambia HM-T5 adicional, que continúa aplazada. [Alcance HS](../docs/specs/sh3-3ds/heather-skinning.md).

Continuidad: [HS-T3 ya implementa y verifica este contrato en host](../docs/execution/f06-03-heather-skinning-prototype.md).
El fixture conserva su estado histórico congelado y su hash; no implica
aceptación GPU. Las obligaciones de ejecución enumeradas abajo tienen
evidencia host en ese informe. Entrega ARM y medición física siguen pendientes.

## HSN01: identidad y fronteras

Se conserva el recurso SRI2 perfil 2 de `0188790baedd`, sus cinco clips,
materiales y hp34. La entrada por cuadro es la `RigPose` ya publicada y la
instancia HM. El render no decide clips, tiempo, raíz, contactos ni controles.
Los vértices/materiales originales no se normalizan ni simplifican.
Se exige primero la validación SRI2 vigente, incluidos huesos activos,
auxiliares e índices; las capacidades de este contrato no la amplían.
La instancia se aplica una sola vez. El cabello y el vidrio siguen en CPU,
con el mismo cálculo y orden total de `PreparedRoomScene::frame`.

Fixture público: `tests/fixtures/synthetic/heather-skinning-native-v1.json`.
SHA-256: `89bc59bd630ee62d38a9ad64523eb5f0dbd91c1e0426c1a891bbf8f3301fc520`.
Solo contiene datos inventados, referencias a vectores HG públicos y una
sonda de shader propia. No contiene malla, poses o texturas originales.

## HSN02: identidad y partición de matrices

- Identidad global primaria: `0..72`; auxiliar: `73 + helper`, hasta 200.
  El 73 procede de la capacidad de `RigPalette`, no de los 36 huesos activos.
- `P[bone] = pose[bone]`; `P[73+h] = pose[target[h]] * helper[h]`, con el
  producto binary32 actual, orden columna/fila/k y sin contracción FMA.
  Auxiliares distintos conservan identidad aunque tengan el mismo target.
- Cada lote opaco tiene **1..30 matrices**, ordenadas por identidad global.
  El índice local es su posición en esa lista. No se omite una influencia
  activa de peso cero; se validan igualmente sus referencias.
- Recorrer materiales e índices originales en orden. Agregar triángulos al
  lote hasta que el siguiente supere 30 identidades distintas, y abrir otro
  lote en ese punto. Nunca cruzar una frontera de material ni dividir un
  triángulo. Un triángulo inviable invalida el plan completo.
- Para dibujo indexado, crear un vértice GPU por pareja `(lote, vértice SRI)`
  en orden de primera aparición. Los índices `uint16` referencian ese VBO
  global; su secuencia reproduce exactamente los índices originales de
  cada lote. No se deduplican por posición ni entre lotes con remapeo distinto.
  Cota estructural: ≤18000 vértices GPU y ≤18000 índices; ambos cuentan en
  el presupuesto antes de reservar. `C3D_DrawElements(GPU_TRIANGLES, count,
  C3D_UNSIGNED_SHORT, indices + first)` consume cada intervalo.

El shader usa tres influencias siempre. Para las inactivas: peso cero y fila
base cero, referencia válida a la primera matriz del lote; nunca 255 ni −1.

## HSN03: matriz de habitación y representación

Las entradas son binary32 finitas. Pose: afín, magnitud ≤1000000;
helper: afín, ≤100000; instancia: las comprobaciones de `instance_ok`
vigentes (afín, rotación propia ortonormal dentro de 0,0001, determinante
>0,9999, elementos ≤1000000). Rechazar NaN, infinito, referencias fuera
de rango y una matriz no afín antes de iniciar el envío.

`O = (100000,0,140000)`, `s = float32(0.002)`, `sign = (1,-1,-1)`.
Para cada matriz `P` del lote, se guardan tres filas `B`:

```text
B[r,c] = float32(sign[r] * double(s) * sum_k(double(I[r,k])*P[k,c]))  c<3
B[r,3] = float32(sign[r] * double(s) *
                ((double(I[r,3])-O[r]) + sum_k(double(I[r,k])*P[k,3])))
```

`k=0,1,2` en ese orden; iniciar el acumulador con cero o `I[r,3]-O[r]`
y sumar tres productos binary64. Sin FMA/reasociación. Se redondea una vez
a binary32 al publicar cada coeficiente. `P` e `I` nativos son column-major;
`B` describe filas lógicas XYZW. La resta del origen se realiza en CPU,
antes de llevar coeficientes al shader, evitando trasladar coordenadas
globales del orden de 140000 a los cálculos GPU.

La GPU calcula la suma ponderada de las posiciones transformadas por B.
El cuarto componente se entrega explícitamente como suma Q12/4096. Así la
traslación y el origen reciben el mismo peso deficiente que la geometría;
no se divide por W antes de vista/proyección. Esta reagrupación algebraica
puede cambiar el redondeo de XYZ; se contrasta con HSN06, no por igualdad
bit a bit de los opacos. La ruta CPU de transparencias permanece exacta.

## HSN04: ABI de vértice y uniformes

Un vértice es **64 bytes**, alineación C++ 4. Cuatro atributos consecutivos
`GPU_FLOAT`, cuatro componentes cada uno, `v0..v3`, permutación `0x3210`.
VBO e índices residen en memoria apta para GPU y respetan su propiedad.

| Offset | Atributo, orden en memoria del VBO |
| ---: | --- |
| 0 | `(position_q4.x/16, y/16, z/16, 1)` |
| 16 | `(weight0/4096, weight1/4096, weight2/4096, sum(weights)/4096)` |
| 32 | `(3*local0, 3*local1, 3*local2, 0)` |
| 48 | `(uv_q12.u/4096, v/4096, 0, 1)` |

Posición/UV usan int16 original. Pesos: enteros `0..4096`, 1..3 influencias,
inactivas cero; suma entre `4097-count` y 4096. Las bases de fila son
enteros exactos representados como float, múltiplos de tres `0..87`.
Cada acceso suma 0/1/2 y permanece en la paleta `c0..c89`.

| Uniformes | Reserva |
| --- | --- |
| `c0..c89` | `palette[90]`: 30 × 3 filas B |
| `c90..c93` | `clip_from_room[4]`: misma vista/proyección del baseline |
| `c94` | Sin uso; no escribir |
| `c95` | Constante de shader `(0,1,0,0)` |

Hay 95 registros ocupados. Con 31 matrices harían falta 98. Los uniformes
se construyen con campos lógicos/FVec4_New: **`C3D_FVec` almacena W/Z/Y/X**.
No reinterpretar la fila XYZW como `C3D_FVec`. El VBO sí conserva XYZW.
El objeto ARM de la sonda comprueba tamaños, offsets y enums del SDK real.

Antes de escribir, exigir localización `palette=0`, `clip_from_room=90`,
`id>=0`, `size>0`, `id+size<=96` y ausencia de solapamiento con c94/c95.
`C3D_FVUnifWritePtr` no comprueba estos límites. Subir exactamente `3*n`
filas activas y las cuatro filas de vista/proyección. Nunca leer una fila
inactiva aunque haya valores de un lote anterior en el registro.

## HSN05: instrucciones, dibujo y fallos

Sonda: `tests/fixtures/synthetic/heather-skinning-v1.v.pica`. El SHBIN fijado
tiene 28 instrucciones y 12 descriptores: MOV, MOVA, DP4, MUL, ADD y END,
sin bucles ni ramas. Usa r0..r4; los tres MOVA quedan separados por cálculo.
Se copian entradas a temporales antes de combinarlas para evitar la
restricción de dos registros de entrada distintos en una instrucción.
Todos los componentes de posición, color y texcoord se escriben exactamente
una vez; color blanco, texcoord Z/W=0/1. No usar `--no-nop`.
SHBIN de 408 bytes, SHA-256
`08997532a98f04f44e978e1a17e0906e120897cdd55fc19a4bd21ffdc34e1b6b`.

Orden del cuadro: rangos originales de habitación con shader CPU, lotes
opacos de Heather con shader de skinning, y orden global CPU cabello/vidrio.
Antes de transparencias se restauran programa, atributos, buffer, estados
de material **y uniformes de cámara** del shader CPU: cambiar solo el
programa no restaura los c0..c3 sobrescritos por la paleta. Mantener blend,
alpha/depth, texturas, culling y visibilidad de los rangos originales.
Empates transparentes: profundidad descendente, material ascendente,
primer índice ascendente, como en HM/HG.

Preparación de recursos y publicación del plan son atómicas. Reservar al
cargar, con tamaños comprobados; no reservar por cuadro. Validar todas las
filas de todos los lotes antes de `FrameBegin`; publicar una instantánea
completa por pose/instancia. Si falla la preparación GPU, conservar una
ruta CPU completa. No publicar medio plan ni mezclar poses de dos pasos.
Espera de propiedad antes de copiar/flush y sincronización antes de liberar.

HS-T3 debe conservar también la validación de posiciones del baseline.
Hasta demostrar y probar una cota conservadora que implique su finitud/rango
para los opacos, se mantiene la comprobación CPU. Su coste debe aparecer
en el benchmark; no se acredita su eliminación por compilar el shader.
Si una cota no permite decidir, usar la validación/ruta CPU, no relajar el
límite de `valid_room_vertex`. Esta condición forma parte de la aceptación
del prototipo, no está implementada por estos vectores.

## HSN06: referencias y aceptación numérica

1. **Enteros y bytes:** identidad/orden de lotes, índices, pesos, UV,
   remapeo, campos del VBO y filas binary32/WZYX deben coincidir exactamente
   con los vectores. W intermedio debe ser exactamente `sum/4096`.
2. **Referencia matemática:** el oráculo conserva como racionales exactos
   las matrices binary32 de entrada; primero deforma, después aplica I y
   cambio de base. No usa las filas B para calcular la referencia.
3. **Ensayo host de instrucciones:** error absoluto XYZ ≤`2e-5` unidades de
   habitación. El evaluador del SHBIN usa binary32; **no emula el redondeo
   PICA de 24 bits ni acredita una ejecución GPU**.
4. **Candidato GPU:** por componente XYZ,
   `abs(actual-ref) <= 2e-4 + 2e-4*abs(ref)`; W intermedio exacto. Ningún
   NaN/infinito. Además, error de proyección ≤**0,25 píxel por eje** en
   viewport físico 240×400, usando la misma matriz de cámara. El giro de
   presentación no cambia esta distancia. Ambas condiciones son obligatorias.
5. El cociente proyectado solo se compara cuando ambas W de clip son
   ≥0,02. Un caso no proyectable se registra como tal, no como aprobado;
   clipping/fronteras necesitan comprobación separada en HS-T3/T4. Las
   clasificaciones de recorte/visibilidad no pueden cambiar silenciosamente.
6. Cabello/vidrio: misma posición CPU, profundidad/orden y atributos del
   baseline; no aplicar la tolerancia GPU para justificar una regresión CPU.

Son umbrales fijados antes del ensayo GPU, no una garantía de que el shader
los cumpla en consola. Si falla, revisar representación/candidato manteniendo
evidencia de la versión anterior; no ampliar tolerancias para declarar éxito.

## HSN07: cobertura congelada y trabajo posterior

- 54 casos numéricos: 13 geométricos, 15 ventanas de los cinco clips y
  26 poses publicadas esperadas de espera↔giro HG. Las poses son sintéticas;
  se vinculan por hash, arco/beta o clip/fase al fixture HG intacto.
- 6 particiones: vacío, mínimo, 30 exactas, corte al introducir la 31,
  reutilización y triángulo indivisible rechazado.
- 14 rechazos declarados, 4 casos de proyección y empate global de
  cabello/vidrio; adicionales no finitos, matrices inválidas, truncaciones y
  alteraciones de shader se ejercitan en pytest.
- Controles negativos: W=1, normalización de pesos, uniformes XYZW
  mal reinterpretados como WZYX y colapso de auxiliares del mismo target.
- Sonda SDK: aceptación/rechazo en fronteras de registros/uniformes,
  atributos incompatibles y ABI ARM. No se invoca el render en consola.

Los errores de asignación/propiedad, atomicidad nativa, recuperación,
pausa/R/reinicio/HOME/tapa, presupuesto real y temporización quedan como
obligaciones explícitas de HS-T3. El fixture los enumera como pendientes;
estos ensayos del contrato no simulan ni declaran su aceptación.
