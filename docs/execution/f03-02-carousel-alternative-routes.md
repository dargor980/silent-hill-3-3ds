# SC-T3b.2 — Investigación de rutas alternativas de daño

2026-10-20. **No se identificó una ruta accesible por juego normal que permita
dañar a las tres instancias `0x0209`, `0x018E–0x0190`, de la sala `0xEB`.**
La revisión amplía la [auditoría de colisiones](f03-02-carousel-collision.md)
a estados de IA, dificultad, consultas alternativas de ataque, procedencia
del daño y referencias externas del escenario.

Es un resultado negativo acotado al código europeo y las rutas examinadas,
no una demostración de que toda ejecución posible del juego sea incapaz de
dañarlos. No hubo interacción con PCSX2, nuevas acciones del jugador,
restauraciones ni escritura de memoria. No se solicita volver al acertijo.

## Criterio para admitir una alternativa

Conforme a SC01/SC04/SC05, una candidata debe establecer una cadena verificable:
condición alcanzable por juego normal → propietario `0x0209` del impacto o
productor alternativo del daño → receptor compatible → selección original
y aplicación de la animación. Encontrar un ID, un setter o un clip en código
no satisface ese criterio. Tampoco lo hace escribir flags desde el inspector.

## Hipótesis examinadas

| Candidata | Evidencia revisada | Resultado |
|---|---|---|
| Esperar un cambio de IA | Inicializador y los cinco destinos de la tabla `0x004159E0` | El estado inicial reproduce `0x1449`; no hay inscripción de colisión. Los estados de reacción también llaman a la rutina vacía. |
| Cambiar dificultad | Ramas de `0x002E0860–0x002E09F4` | Ajustan vida y regeneración; no proporcionan un registrador de colisión alternativo. Revisión estática, sin partidas nuevas en otras dificultades. |
| Cambiar forma de ataque | Consultas de volumen y múltiples resultados | Ambas familias obtienen el propietario del mismo registro de personajes ausente para `0x0209`. |
| Hacer que otro enemigo lo golpee | Receptor `0x001E06F0` | Filtra el origen frente a Heather después de normalizar ciertos IDs de ataque. No se demostró una excepción aplicable ni una colisión receptora. |
| Activar otra bandera de la sala | Inicialización `0x01EE16C0`, actualización `0x01EE2774` y accesores | La bandera de activación ya vale 1; la máscara de vida de los tres actores ya vale 7. No apareció otro cambio que inscriba colisiones o emita daño. |
| Usar las referencias externas a `0x0209` | Sitios `0x002DC2AC/0x002DC2F4` y sus consumidores | Añaden tipo/ID a una lista de exclusión consultada en la ruta de dibujo; no son golpes ni cambios de vida. |
| Aprovechar la inicialización anterior a `0x1449` | Inicializador, registro de IA y creación genérica | No registra formas de personaje antes de activar el bit de exclusión. No se estableció una ventana de ataque reproducible. |

Ninguna candidata produjo una acción normal que cumpla el criterio de admisión.
No se interpreta este resultado como prueba de contenido descartado ni de
intención de los desarrolladores.

## IA: recibir daño es una precondición, no una transición por tiempo

El inicializador `0x002E0860` instala la IA `0x002E0A70` y fija el estado de
animación en 1 mediante `0x00214850`. La tabla de cinco destinos es:

| Estado en IA `+0x15A` | Destino | Comportamiento relevante |
|---:|---|---|
| 0 | `0x002E0F00` | Pasa al estado 1 |
| 1 | `0x002E0F10` | Selecciona `0x1449`, activa máscara `0x0002` y llama al auxiliar vacío |
| 2 | `0x002E0FA0` | Selecciona `0x144A`; puede volver al estado 1 o pasar al 3 según fin de clip y vida |
| 3 | `0x002E1080` | Selecciona `0x144B`; su final pasa al estado 4 |
| 4 | `0x002E1140` | Gestiona flags y temporizador posteriores; no añade formas de personaje |

Los cuatro estados 1–4 llaman a `0x002E0EF0`, que retorna inmediatamente.
Las únicas llamadas locales a quitar flags (`0x002142D0`) usan máscaras
8 y 4 en el estado posterior; no desactivan la máscara `0x0002`.

La recepción `0x001E06F0` limpia el ID de ataque en actor `+0x170` cuando
no recibe eventos de tipo 4. La clasificación `0x001E2750` para ID 0 es 0;
esa entrada de la tabla `0x0043B130` salta a `0x002E0DF0`, donde se limpia
el daño pendiente mediante `0x002142A0`. Desde el estado observado
`[0, 0, 1, 2]` en IA `+0x156…+0x15C`, el recorrido sin evento conserva
la animación inicial. La regeneración no constituye una fuente de impactos.

Las ramas que seleccionan reacción presuponen una clasificación de ataque
recibida. El temporizador del estado 4 ocurre después de la cadena de muerte;
no es una vía de entrada a ella desde el reposo. Esto es una lectura del
flujo de código, no la ejecución observada de los clips pendientes.

## Las consultas alternativas conservan la exigencia de propietario

La consulta de volumen `0x001A7110`, alcanzada por
`0x001A68A0/0x001A6B40`, recorre el banco opuesto al selector de
`0x01D0A7E8`, exige la forma de personaje y copia su propietario al resultado
en `0x001A72E8`.

Las ramas de múltiples resultados de `0x001A2EC0` llaman a
`0x001A4C90/0x001A5100`. Ambas llegan a `0x001A5470`, que vuelve a recorrer
los bancos de personajes y copia el propietario al resultado en
`0x001A55EC`. La conversión `0x001A3C70` crea el evento de tipo 4 con ese
propietario en `0x001A3E64–0x001A3E68`. No obtiene un actor a partir de
la apariencia del polígono de escenario.

Así, esas familias no evitan la ausencia de inscripción ya comprobada.
No se asignan nombres de armas a los IDs sin contrastar su tabla y sus
llamadores: no se ha probado cada arma dentro del juego.

El receptor también limita el daño entre enemigos. Para IDs menores que
`0x53`, normaliza el origen a Heather; después, `0x001E07E4` descarta
los eventos cuyo origen sigue siendo diferente antes del cálculo de daño.
Esta normalización impide afirmar inmunidad universal al daño entre enemigos
solo por ese filtro. No se encontró una combinación que además proporcione
el propietario y la colisión que faltan.

## Referencias del escenario que no son una fuente de daño

Los sitios `0x002DC2AC` y `0x002DC2F4` llaman a `0x0023D810` con tipo
`0x0209`. Esa función recorre actores y añade sus pares tipo/ID a la lista
`0x01EA31B0`. Su consulta `0x0023D8B0` se consume en `0x0023D548`:
una coincidencia hace devolver cero a `0x0023D4C0`. En `0x001D3944` se
consulta ese filtro y una devolución cero omite la ruta posterior de dibujo.
Esta cadena no modifica vida, no inscribe colisiones ni publica un evento de
daño. Su presencia no justifica golpear al actor en otro momento del combate.

Otras coincidencias literales revisadas tampoco aportan un productor:
`0x0012F12C` conduce al registro genérico de IA; `0x001DD1B4` selecciona
el valor de recurso `0x2E`; `0x0013624C` modifica parámetros temporales de
las formas preparadas por `0x00137780`, cuyo propietario no se sustituye por
el tipo comparado. La rama `0x0017C630` escribe una clasificación 6 en una
salida temporal del llamador `0x00186E44`, que abandona su operación al verla.
`0x001C5F8C` pertenece a selección de buffers, no a creación de un impacto.
No se convierte una coincidencia numérica en evidencia de daño.

En `amusement_02`, el setter de activación solo tiene una llamada directa
en el texto revisado, `0x01EE16C8`, con valor 1. La inicialización establece
la máscara `0x01EEE3D0` en 7; la IA retira sus bits cuando la vida ya llegó
a cero. La máscara es una consecuencia en esa ruta, no un evento de daño.
Las capturas 08, 35 y 36 confirman respectivamente activación 1, máscara 7
y los tres actores en el mismo estado inicial de IA.

## Procedencia, comprobaciones y límites

Se contrastaron 28 ventanas nuevas/relevantes de código, dos tablas de despacho
y la entrada cero de clasificación de ataques contra el ELF europeo y la RAM
de las capturas 08, 35 y 36. También se verificó el
texto completo del overlay, identidad/recursos y registros de colisión con
el auditor anterior. La captura 36 conserva su etiqueta diagnóstica tras
restauración; no se concatenó a 08–35 ni se repitió una prueba de continuidad.

La herramienta separa referencias directas, anclas de instrucciones,
procedencia de snapshots y emisión de metadatos. Cuatro controles negativos
rechazan cambios en copia de propietario, tipo de evento, filtro de origen
y rama del filtro de dibujo. Alteran solo la lectura sintética del auditor.

```sh
rtk proxy .venv/bin/python build/f03-02-skeleton-continuity/audit_carousel_alternative_routes.py
```

Requiere los auxiliares y el corpus privado local; no incorpora datos originales
al repositorio ni al pipeline público. Informe local:
`reports/local/f03-02-carousel-alternative-routes-v1.json`, SHA-256
`1fb3f1828a5ffb392d04ca92ceb25b6461d3bef222233319e71d5130a26bd3a5`.
Incluye hashes del ELF/overlay, ventanas, snapshots y referencias examinadas.
El informe anterior de colisión mantiene SHA-256
`21b2f80f3158941cec2a17974e9136cbd2f810443726f9d87b7e09fc107e6d35`.

Los inventarios de saltos/llamadas directas y literales sirven para localizar
candidatos: no son un análisis exhaustivo de alias de memoria, llamadas
indirectas, todos los scripts y todas las partidas posibles. No hubo un ensayo
nuevo en PCSX2 ni una modificación del port 3DS.

## Estado de SC-T3b.2

La revisión acotada de alternativas queda realizada con resultado negativo.
**SC-T3b.2 permanece abierto en su criterio de identificar una ruta admisible**,
y SC-T3b.3 no dispone de una acción manual justificada. SC-T3b/c y SA-T5d
no se cierran con esta evidencia, conforme a SC05.

Una futura reapertura debe aportar un candidato concreto: un productor de
daño distinto, un cambio normal que registre al actor o una observación nueva
de selección original `0x144A/0x144B`. Entonces se verificará la cadena bajo
SC01. Repetir el acertijo de `0x020C`, probar golpes sin destinatario o forzar
flags no resuelve esta condición. La vuelta `0x1449` ya verificada conserva
su validez y su informe no se modifica.
