# SA-T5d — Ruta de colisión de los tres actores de la fase posterior

2026-10-20. **La ruta de impacto de personaje analizada no puede dirigir un
evento de daño a los tres actores `0x0209` con los registros observados.**
Sus instancias `0x018E–0x0190` tienen geometría de colisión del escenario,
pero no figuran como propietarios de colisiones de personajes. Además,
el estado inicial de su IA activa un bit que los excluye de la selección
de objetivos examinada.

Resultado basado en el ELF europeo y las capturas conservadas, sin interactuar
con la VM ni modificar el huésped. No es una prueba de invulnerabilidad
permanente: quedan fuera otras configuraciones, rutas alternativas y cambios
entre las muestras. **No se observaron impactos ni selecciones `0x144A/0x144B`.**

Continúa la [investigación de continuidad](f03-02-animation-continuity.md)
y la corrección que distingue los once caballos `0x020C` del acertijo de
los tres actores del recurso MDL/ANM estudiado.

**Seguimiento SC-T3b.2:** la [investigación de rutas alternativas](f03-02-carousel-alternative-routes.md)
revisa IA, consultas de ataque y referencias externas sin encontrar una
acción normal admisible. Mantiene abierto el criterio de accesibilidad;
no convierte esta ausencia en una prueba universal de invulnerabilidad.

## Contraste de registros en RAM

| Evidencia | Colisiones de personajes, en cada banco | Actores estudiados | Geometría del escenario |
|---|---|---|---|
| Captura 02, sala `0xEA`, acertijo | 23 entradas: Heather y dos por cada uno de los once `0x020C` | Once caballos con vida completa | Una lista por banco |
| Capturas 08–35, sala `0xEB` | Dos entradas: Heather `0x0100` y Alessa `0x0215` | Tres `0x0209`, flags `0x2002`, clip `0x1449`, vida completa | Doce listas por banco |
| Captura 36, reproducción diagnóstica | Las mismas dos entradas, ningún propietario `0x0209` | Las mismas tres instancias, flags `0x2002`, clip `0x1449`, vida completa | Doce listas por banco |

Se inspeccionan **ambos bancos**, no solo el marcado como activo. Las 28
muestras pertenecen al segmento continuo ya reconciliado; contienen los tres
actores y sus hashes completos de modelo y animación coinciden. La captura
36 se conserva aparte: procede de una restauración solicitada por el usuario
y no amplía la evidencia de continuidad de SC01.

La cola de resultados está vacía en los puntos inspeccionados. Esto no prueba
que nunca existiera un evento entre capturas; la conclusión sobre el recorrido
de daño procede de la combinación de registros y código, no de esa ausencia
puntual ni de conservar la vida completa.

## Dos tipos de colisión con funciones diferentes

El registro de personajes se construye mediante `0x001A0120/0x001A0130`.
Mantiene dos bancos de hasta 32 entradas: base `0x01D05FE0`, separación
`0x2400`, entrada de `0x120` bytes, contadores en `0x01D0A7E0` y selector
en `0x01D0A7E8`. Cada entrada conserva el propietario en `+0x60`, dos
formas, indicadores de presencia en `+0x110/+0x112` y callback en `+0x11C`.

Para los caballos del acertijo, `0x00314180` llama al registrador en
`0x00314344` y `0x003143DC`, pasando el actor como propietario. Las 22
entradas observadas por banco corresponden exactamente a esos once actores,
con callback `0x00314410`. Esto aporta un control positivo del registro,
sin convertir las dos capturas de vida anterior/posterior en observaciones
de cada golpe.

Para `0x0209`, la rutina auxiliar `0x002E0EF0` retorna inmediatamente.
La IA la invoca en sus estados, pero esa rutina no registra formas de
personaje. No se encontró una inscripción alternativa en ninguno de los
dos bancos de las muestras examinadas.

La geometría del escenario sigue otro recorrido. El overlay `amusement_02`,
actualización de sala en `0x01EE2774`, transforma listas geométricas mediante
`0x001A0CD0` y las registra con `0x001A0B70`. El registro en `0x01D04560`
contiene dos bancos de contador y hasta 16 punteros, separados por `0x44`;
su selector está en `0x01D045E8`. No es el registro de propietarios anterior.

La tabla del overlay en `0x01EE9D30` asigna las tres instancias a posiciones
concretas; las otras nueve posiciones siguen la rama de objetos del mapa.
Las listas de las doce posiciones están presentes en ambos bancos durante
08–35 y en 36:

| Instancia | Índice en la tabla | Lista del banco 0 | Lista del banco 1 |
|---|---|---|---|
| `0x018F` | 1 | `0x01EEA5D0` | `0x01EEA8A0` |
| `0x0190` | 2 | `0x01EEAB70` | `0x01EEAE40` |
| `0x018E` | 11 | `0x01EEDE10` | `0x01EEE0E0` |

La presencia de estas listas acredita el registro de geometría del escenario;
por sí sola no crea un destinatario de daño de tipo personaje.

## Del ataque al evento de daño

La revisión estática del ELF europeo traza este recorrido:

1. El procesador de ataques `0x001A2EC0` consulta intersecciones mediante
   `0x001A3F00/0x001A4260` y el despachador `0x001A6200`.
2. La rama de personajes llega a `0x001A6EF0`. Recorre el banco opuesto al
   selector, omite al atacante y exige la segunda forma presente. Si la
   intersección es la más cercana, emite un resultado **tipo 3**, cuyo
   propietario se copia de entrada `+0x60` a resultado `+0x10` en
   `0x001A70AC`.
3. `0x001A3980` convierte ese resultado en eventos. En `0x001A3BE0–0x001A3BE8`
   toma el propietario del resultado y crea un **evento tipo 4 dirigido a él**.
   Los resultados de escenario tipo 1/2 siguen otras ramas; no crean por
   esta conversión el mismo evento tipo 4 para un caballo.
4. `0x001A2E30` entrega al consumidor solo los eventos cuyo propietario coincide
   con el actor. `0x001E06F0` los procesa; el punto `0x001E07A8` es la rama
   de tipo 4, anterior al cálculo de daño en `0x001DEF00`.
5. La IA `0x002E0B10` todavía debe aceptar el daño y satisfacer sus condiciones
   antes de cambiar de estado y seleccionar otra animación.

Por tanto, **sin una entrada cuyo propietario sea `0x0209`, la consulta de
personajes descrita no puede producir un resultado dirigido a ese actor**.
Acertar a la geometría del escenario no aporta esa identidad. Esto explica
por qué pedir más golpes visibles no era una prueba suficiente para alcanzar
el breakpoint condicionado a `0x0209`.

La selección de objetivos aporta otra condición independiente: el inicio
de `0x1449` llama a `0x002142C0` con máscara 2 en `0x002E0F50`, activándola
en actor `+0x1C0`. El filtro `0x001E159C–0x001E15CC` acepta esta familia
solo con `0x2000` activo y el bit de máscara `0x0002` apagado. Los tres actores tienen `0x2002`
en todas las muestras posteriores. Se atribuye a ese bit la exclusión de
**este filtro**, no una inmunidad universal ante cualquier ruta de ataque.

## Auditoría reproducible y límites

El auditor local separa carga/procedencia, lectura acotada de tablas,
comprobaciones de fase y emisión de metadatos. Verifica recibos y hashes de
30 estados: control 02, las 28 muestras 08–35 y diagnóstico 36. Contrasta
CRC/PID/PC/ciclos, límites y propietarios de tablas, pertenencia a la lista
de actores, asociación de IA, recursos completos, código de RAM frente al
ELF y texto del overlay. Reutiliza el informe de continuidad sin modificarlo.

Ocho controles negativos rechazan contadores fuera de capacidad, selectores
inválidos, propietario ajeno a la lista, una inscripción contradictoria de
`0x0209`, bit de exclusión apagado y una posición geométrica ausente. Solo
se alteran copias de datos en memoria del auditor. Estas pruebas comprueban
la auditoría; no simulan evidencia de funcionamiento del juego.

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/audit_carousel_collision.py
```

El comando requiere el corpus privado local y los auxiliares de investigación
en `build/`; no se incorpora al pipeline público de fixtures sintéticos.
No exporta estados, instrucciones ni recursos originales al informe.

| Artefacto | SHA-256 |
|---|---|
| ELF europeo `SLES_514.34` | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| Overlay `amusement_02` | `414142dad62fefc1cbd0d6684c05ba5d3331dd445949a11e5301470250683bde` |
| Informe local `reports/local/f03-02-carousel-collision-v1.json` | `21b2f80f3158941cec2a17974e9136cbd2f810443726f9d87b7e09fc107e6d35` |
| Informe previo de continuidad, sin cambios | `ea78b9d400712f07616794b0382da196bf5a9bb57b55d53c9002109a9914163c` |

El informe nuevo contiene hashes individuales de estados y ventanas de código,
tablas de propietarios, flags, procedencia separada y controles rechazados.
La historia previa de la tarjeta importada continúa siendo desconocida.

## Consecuencia para las tareas

La investigación previa de inscripción y destinatario de SC-T3b queda
completada **para la configuración observada**. No se solicita repetir el
acertijo ni golpear de nuevo a los tres actores con esta configuración.

SC-T3b/c y SA-T5d permanecen abiertos conforme a SC05: ni la existencia del
código de daño/muerte ni este resultado negativo prueban selección y aplicación
de `0x144A/0x144B`. Para retomar una prueba manual debe identificarse primero
una configuración alcanzable por juego normal que registre al actor como
destinatario, o una ruta alternativa que produzca el evento correspondiente.
Si aparece, se verificará propietario, evento, cálculo de daño, selector y
descriptor aplicado en un ensayo nuevo bajo SC01. Modificar flags, forzar
colisiones o cargar estados no sustituye esa evidencia.
