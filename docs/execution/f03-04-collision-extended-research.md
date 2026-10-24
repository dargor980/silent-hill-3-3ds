# F03.04 / CF-T8 — Variante de 48 bytes y listas dinámicas

2026-10-23. **CF-T8a–CF-T8c completadas como investigación estática y cotejo
de capturas conservadas.** [Requisitos y tareas](../specs/sh3-3ds/collision-shapes-research.md).
La variante de 48 bytes tiene una interpretación geométrica sustentada por su
consumidor: cilindro vertical finito. Las colas de las listas dinámicas se
pueden reconstruir desde fuentes de la fase anterior. Falta observar las
llamadas geométricas y las escrituras del cambio de fase antes de atribuir
comportamiento físico al port.

No se modifica CP/CPI, sus paquetes privados ni el runtime. No hay nuevo build
3DS, solver, daño ni cierre de F03.04 global o G02/G03.

## Evidencia y alcance

- 285 CLD por copia A/B, 2.690.720 bytes por copia: igualdad íntegra y cotejo
  con catálogo y recibo de extracción. Los 52 recursos con grupo 4 activo
  contienen 293 registros; los 293 están referenciados por sus listas.
- 30 estados fijados: control 02, continuidad 08–35 y diagnóstico restaurado
  36. Se verifican estado/recibo, PC/ciclo, sala, etapa y procedencia. No se
  ejecutó PCSX2 ni se escribieron o restauraron estados durante esta tarea.
- 16 ventanas de código del ELF comparadas con RAM en los 30 estados;
  texto del overlay, las dos tablas y sus 24 secuencias fuente también
  coinciden. Los miembros ELF/overlay se releen al final.
- 647 archivos de entrada reverificados después del análisis. El comprobante
  contiene pins, conteos y resultados; no guarda los buffers originales.
- CP v1 sigue dando **233 aceptados / 52 no soportados / 0 otros rechazos**.
  Interpretar el consumidor no convierte esos 52 recursos en aceptados.

ELF europeo: `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`;
overlay 2: `414142dad62fefc1cbd0d6684c05ba5d3331dd445949a11e5301470250683bde`.
Para interpretar COP2 se contrastan las tablas del archivo local de PCSX2
`DebugTools/DisR5900asm.cpp`, SHA-256
`c78ffeb90c60f9c4fc06ade98d9ef10236c50c1d08c11b225eaeed08a5927cbb`.
No se confunden las tablas de instrucciones macro con las de microprogramas VU.

## Variante de 48 bytes

La selección está en `0x001A6DD0`. La lista contiene índices u32; el cálculo
en `0x001A6E1C`–`0x001A6E28` selecciona `base + índice * 48`. La llamada
`0x001A6E2C → 0x0019F2C0` pasa dos vectores de consulta y `registro + 0x10`.
La sublista termina en `0xFFFFFFFF`, no en la cabecera de la forma.

| Campo relativo al registro | Uso demostrado en esta ruta | Corpus fijado |
|---|---|---|
| `+0x10`, f32 | Centro radial X | −106.600 a 102.541 |
| `+0x14`, f32 | Límite Y numéricamente mayor | −1.400 a 198,9040 |
| `+0x18`, f32 | Centro radial Z | −100.386,5 a 101.500 |
| `+0x1C`, f32 | Componente W del primer vector; sin uso geométrico en esta ruta | Siempre 1 |
| `+0x20`, f32 | Componente X del segundo vector; sin uso geométrico en esta ruta | Siempre 0 |
| `+0x24`, f32 | Límite Y numéricamente menor | −5.106,3501 a −200 |
| `+0x28`, f32 | Componente Z del segundo vector; sin uso geométrico en esta ruta | Siempre 0 |
| `+0x2C`, f32 | Radio | 8,25 a 329,8653 |

Todos los valores son finitos; en los 293 registros el radio es positivo y
el límite Y mayor supera al menor. Estos son invariantes del corpus observado,
no reglas nuevas de aceptación del decoder ni una decisión sobre unidades.
Los nombres mayor/menor evitan presuponer la orientación vertical del mundo.

La interpretación geométrica se apoya en operaciones concretas:

- `0x0019F2D8` / `0x0019F2DC`: centro X/Z ± W del segundo vector para acotar
  el radio; `0x0019F2E8` / `0x0019F2EC` incorporan los dos límites Y.
- Desde `0x0019F328`: resta del centro X/Z, cuadrados y suma radial;
  `0x0019F33C` calcula radio². La ruta continúa con raíces e interpolación
  entre los dos puntos de consulta.
- `0x0019F58C` / `0x0019F590` y comparaciones siguientes: comprueban Y frente
  a ambos límites. Las ramas `0x0019F5D4` / `0x0019F5E4` calculan un punto
  en el plano del límite; `0x0019F610`–`0x0019F638` comprueba su distancia
  radial. Hay pruebas laterales y de los planos extremos del cilindro.

Esto permite nombrar los parámetros y la geometría, pero no acredita todavía
equivalencia numérica para tangencia, segmento interno, longitud cero, direcciones
degeneradas o tolerancias. Hace falta comparar entradas/salidas reales y después
un oráculo y contrato sintéticos propios.

### Resultado de consulta y rutas diferentes

`0x0019F2C0` devuelve una indicación de impacto y escribe el punto cuando
lo acepta. La ruta observada pone su W a cero en `0x0019F588`; no se debe
reinterpretar automáticamente como punto afín con W=1.

El llamador indexado compara distancia XYZ al primer punto de consulta con
el mejor resultado. Si lo sustituye, escribe tipo 2 en `resultado+0`, punto
en `+0x10`, **16 bytes cero en `+0x20`** y puntero a la forma en `+0x30`.
Esta ruta no entrega una normal utilizable en ese bloque ni implementa por
sí misma deslizamiento, gravedad o resolución de penetración.

El consumidor indexado de grupo 4 no consulta los 16 bytes de cabecera de cada
forma antes de llamar a la prueba geométrica. Por tanto, el filtrado de flags
descrito para polígonos en CF-T1–T3 no debe extenderse a esta ruta. La cabecera
y los tres componentes sin uso aquí permanecen opacos y deben conservarse.

También llaman a `0x0019F2C0` los sitios `0x001A5524` y `0x001A6FAC`. Usan
otro pool: base `0x01D05FE0`, bancos de `0x2400`, registros de `0x120`,
parámetros geométricos en `+0x40`, propietario en `+0x60` y habilitación en
`+0x112`. Seleccionan por `0x01D0A7E8` y producen tipo 3. Compartir una prueba
geométrica no convierte ese pool de actores en la lista dinámica de polígonos
ni demuestra que todos sus usos equivalgan a daño.

Los CLD del carrusel ya identificados, `tp1e.cld` y `tp1d.cld`, tienen grupo 4
vacío. Las capturas actuales no pueden acreditar una llamada a una forma de
48 bytes del escenario. El recibo enumera los 52 candidatos; por ejemplo,
`tp1f.cld` tiene dos y `us1e.cld` uno, sin atribuirles una escena cargada por
su nombre.

## Ciclo de vida de las listas dinámicas

| Operación | Evidencia estática | Efecto delimitado |
|---|---|---|
| Reset `0x0019FB30` | Escrituras `0x0019FB90` / `0x0019FB98` | Pone a cero los contadores de ambos bancos. Esta función no limpia los buffers apuntados ni escribe el selector de estas listas. |
| Avance `0x0019FC00` | Selector en `0x0019FCB8`–`0x0019FCC4`; contador en `0x0019FCDC` | Alterna el selector y vacía el contador del banco seleccionado; conserva los punteros y las formas anteriores. |
| Registro `0x001A0B70` | Banco `0x01D04560 + selector * 0x44` | Añade el puntero e incrementa el contador; no escribe formas ni terminadores. |
| Copia `0x001A0CD0` | Avance 80; prueba del byte inicial; salto final al registro | Copia cabecera, suma el vector a los cuatro vectores y registra el comienzo. **No copia el terminador.** |
| Consulta `0x001A49D0` | Selector `0x01D045E8` | Consulta el banco opuesto, avanza 80 bytes por forma y termina por byte inicial cero. |

Los dos selectores son distintos: el de las listas del mundo y el siguiente
banco del overlay (`0x01EEA020`). En las 29 muestras posteriores,
`banco_mundo = 1 − siguiente_overlay`; la consulta usa el opuesto al primero.
Esta relación observada no se presume válida en cada instrucción intermedia.
El control 02 sigue separado: solo tiene un puntero registrado por banco.

### Procedencia de las colas

La tabla anterior en `0x01EE9C40` contiene doce filas de 20 bytes. Su quinto
u32 selecciona `0x01EE3CD0 + índice * 80`. Las doce fuentes tienen ocho formas.
Los sitios `0x01EE1E00` y `0x01EE2178` llaman al copiador con esas fuentes y
la fórmula de destino que también usa la fase posterior. Parte de esta ruta
es condicional: no se afirma que escriba todas las filas en cada frame.

La tabla posterior en `0x01EE9D30` tiene doce filas de 16 bytes. Sus cantidades
son `13, 5, 1, 13, 13, 13, 13, 13, 13, 13, 13, 9`. El destino sigue siendo:

```text
0x01EEA030 + fila * 0x5A0 + banco * 0x2D0
```

La distancia entre destinos equivale a nueve formas, pero nueve fuentes
escriben trece. Además del solapamiento ya identificado, las fuentes de cinco
y una formas dejan colas de las antiguas fuentes de ocho:

| Fila posterior | Formas escritas | Cola conservada por banco | Fuente de la cola |
|---:|---:|---:|---|
| 1 | 5 | 3 | `0x01EE3E60`–`0x01EE3F00`, paso 80 |
| 2 | 1 | 7 | `0x01EE5670`–`0x01EE5850`, paso 80 |

Son **20 registros entre ambos bancos**. Cada cabecera/X/Z/W coincide con
una única dirección fuente de las listas anteriores. Además, los 1.600 bytes
completos de esas colas, incluidos sus valores Y, tienen el mismo hash en las
29 capturas. La estabilidad de Y no sustituye una referencia independiente
para calcularlo.

### Modelo independiente de ocupación

Se construye una región de 216 registros inicialmente cero; se aplican las
fuentes de la tabla anterior a ambos bancos y después las posteriores en
orden de fila, terminando con el banco más reciente según el selector capturado.
Las entradas del modelo son las tablas y fuentes del overlay, no las formas
transformadas extraídas de la captura que se intenta explicar.

La última escritura del modelo deja 192 registros de fuentes posteriores,
20 de fuentes anteriores y cuatro cero. Se comparan **cabecera y X/Z/W**:
64 bytes por registro, 216 registros × 29 capturas = **400.896 bytes exactos**,
sin diferencias. Se excluyen expresamente los cuatro Y por registro.
La comparación de Y de tres listas de actor hecha en CF-T1–T3 conserva su
alcance anterior; no se amplía aquí a todas las listas.

También coinciden los 24 recorridos por captura, hasta su terminador real:

```text
Banco 0: 26, 8, 8, 162, 144, 126, 108, 90, 72, 54, 36, 18
Banco 1: 17, 8, 8, 153, 135, 117,  99, 81, 63, 45, 27,  9
```

El modelo explica los recorridos de ocho frente a fuentes actuales de cinco
y una, y los recorridos largos que atraviesan destinos contiguos. **No es una
traza capturada del cambio de fase.** No demuestra cuándo se escribieron todas
las fuentes anteriores, ni quién inicializó los cuatro huecos cero. No se
debe corregir o truncar este comportamiento en un futuro port por considerarlo
una anomalía sin investigar primero sus consumidores.

## Verificación y reproducción

Doce controles negativos detectados:

| Modelo incorrecto | Registros distintos frente a la captura 08 |
|---|---:|
| Omitir las fuentes de la fase anterior | 20 |
| Copiar también los terminadores fuente | 14 |
| Truncar cada fuente a nueve formas | 36 |
| Limpiar nueve formas del destino antes de copiar | 20 |

Los otros ocho controles cubren grupo 4 truncado, radio no finito o cero,
límites Y invertidos, tamaño sin múltiplo de 48, terminador ausente, índice
que referencia el terminador y alteración de X. Una alteración de Y deja
deliberadamente intacta la comparación parcial; ese control explicita su límite.
Los controles de dimensiones pertenecen al sondeo del corpus, no a CP v1.

La ejecución y su repetición independiente producen bytes idénticos.
Ruff/formato del auxiliar y control del repositorio aprobados. Esta tarea no
cambia producción ni CI; no vuelve a presentar las 8.829 pruebas históricas
de CF-T7d como una ejecución nueva.

Comprobante local: `reports/local/f03-04-collision-extended-research-v1.json`,
480.127 bytes, SHA-256
`490361a155b550f16842002f2f589d18ef1207c1b19af6b1f72d361ac5285c23`.
Auxiliar: `build/collision-extended/audit_extended.py`, 25.215 bytes, SHA-256
`75774fb1f5540bca8bbe284e9ea2cfa32ecb23455292323fde107b8a83d8a916`.
Ambos son locales y excluidos de Git. El informe público conserva conclusiones
y pins; los recursos privados permanecen externos.

```sh
rtk proxy .venv/bin/python build/collision-extended/audit_extended.py
rtk proxy .venv/bin/ruff check build/collision-extended/audit_extended.py
rtk proxy .venv/bin/ruff format --check build/collision-extended/audit_extended.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Sin `--output`, el auditor solo imprime el resumen. Con `--output RUTA_NUEVA`
escribe un recibo exclusivo de metadatos. Rechaza `-O` porque los cargadores
históricos de ISO usan aserciones; no se anuncia una garantía bajo optimización.

## Siguiente tarea antes de la respuesta física

**CF-T9: captura de consulta y cambio de fase.** Primero preparar adquisición
acotada y seleccionar por identidad completa un CLD cargado con grupo 4 activo.
Luego registrar la entrada a `0x0019F2C0` con retorno esperado `0x001A6E34`:
argumentos, registro de 48 bytes, recurso/grupo/celda/índice, vectores y salida.
Capturar éxito y rechazo sin escribir argumentos del juego. La coincidencia
del recurso en RAM y su registro deben preceder a interpretar el resultado.

Para las listas, capturar antes/después del reset y avance, del copiador en
los dos sitios de fase anterior y los dos posteriores (`0x01EE2998`,
`0x01EE2A70`), y de la consulta. Conservar PC/ciclo, selectores, contadores,
punteros, entradas, vector de traslación y región de destino completa. El
cambio de fase debe ser continuo; una restauración solo podrá aportar un
diagnóstico separado. Hay que observar las escrituras e inicialización y
comparar también Y antes de cerrar el ciclo de vida.

Después vendrán contrato/fixtures del nuevo perfil, decoder puro y oráculo,
intermedio y pruebas de consulta. La respuesta física necesita además reglas
de normal, barrido, penetración, deslizamiento, escalón/gravedad y relación
con el actor controlado; los hallazgos de CF-T8 no las implementan.
