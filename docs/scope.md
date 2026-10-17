# Alcance de contenido por hito

Versión **1.0** · 2026-10-16 · Línea base de F00.04/Q03. Este documento fija qué se debe implementar y probar. El estado de ejecución permanece en el [backlog](specs/sh3-3ds/tasks.md); ninguna fila de alcance acredita jugabilidad implementada.

## Decisiones y procedencia

| Decisión | Valor | Fundamento |
|---|---|---|
| Destino principal | **New Nintendo 2DS XL**, Homebrew Launcher, `.3dsx` | Modelo y launchers confirmados por el usuario; FBI disponible para una futura ruta CIA opcional |
| Origen único | PS2 Europa/PAL, **SLES-51434, 1.02**; perfil `ps2-sles-51434-9a94b95e777dae42` | [F00.02](execution/f00-02-edition-identification.md): imagen completa identificada y manifiesto de 113 archivos |
| Primera alpha | **Textos en español; acción Normal; acertijos Normal** | Selección expresa del usuario el 2026-10-16 |
| Ruta inicial | Nueva partida, progreso ordinario de campaña hasta su final, créditos y resultados | Concreción de desarrollo del recorrido de principio a fin exigido por RF13.03; contrato detallado abajo |
| Objetivo final | Todo el contenido jugable de esa edición, incluidos los cinco idiomas catalogados, dificultades, ramas, finales y extras presentes | Alcance conservado del proyecto; la prioridad de la alpha no elimina obligaciones del candidato completo |
| Audio e historia | Conservar las voces y contenido narrativo presentes en la edición | Sin doblaje, traducción ni historia nuevos; idiomas de texto y pistas de voz se registrarán en inventarios separados |
| Madurez actual | Fundación sintética, identificación del disco y alcance documental | No hay lógica de SH3 portada ni validación física del diagnóstico |

La selección de español y Normal/Normal está confirmada. La descomposición en hitos y los criterios de selección del corpus son decisiones de desarrollo basadas en el PDF, no afirmaciones de una prueba del juego. La lista `en/fr/de/es/it` tiene evidencia de catálogo; su disponibilidad y corrección durante ejecución deben comprobarse en F10/F11/F13. Los nombres, cantidades e IDs de variantes aún no investigadas no se inventan.

Fuente: PDF v1.0, pp. 3-4, 14, 23-25 y 27-28; identidad del documento en [SPEC.md](SPEC.md). Trazabilidad principal: RF13.01-RF13.07, V13 y T13; [pruebas y puertas](specs/sh3-3ds/validation.md).

## Contenido y aceptación de M0 a M5

Los hitos son acumulativos. «Obligatorio» significa condición de aceptación futura. G00 está aprobada para identificación, alcance y custodia; G01-G14 siguen pendientes.

| Hito / puertas | Contenido obligatorio | Evidencia que permite usar la etiqueta | Límite de soporte en ese hito |
|---|---|---|---|
| **M0 — Entorno y edición**, G00-G01 | Perfil europeo, custodia y alcance; diagnóstico sintético con gráficos, entrada, SD, tono y ciclo de vida | Build limpio identificado; diagnóstico 30 minutos en New Nintendo 2DS XL y error simbolizado; entorno/launcher registrados | Ninguna sala ni campaña de SH3; compilar el `.3dsx` no cierra G01 |
| **M1 — Datos y lógica**, G02-G04 | Corpus mínimo del slice, inventario de desconocidos, conversión repetible y paquete; movimiento, transición e inventario reales ejecutándose en host | Referencias del mismo perfil, contratos binarios, pruebas adversariales/diferenciales y estrategia para dependencias críticas | Infraestructura y lógica parcial; no permite anunciar una habitación jugable |
| **M2 — Habitación jugable**, G05-G06 | Primera sala del corpus, personaje animado, cámara, movimiento y colisiones; ajustes Normal/Normal para las reglas presentes | Navegación 30 minutos sin atrapamiento/deriva, capturas comparables y coste CPU/GPU/memoria medido en consola | Una habitación; combate, progreso entre salas y campaña aún no certificados |
| **M3 — Vertical slice**, G07-G09 | Dos salas conectadas, interacción con progreso, inventario, un enemigo, audio y guardar/cerrar/continuar; textos españoles del segmento | Circuito integrado 30 minutos, 100 transiciones, combate/recuperación, persistencia y micropruebas de cargas difíciles; decisión de viabilidad favorable para expandir | Solo el segmento identificado; no acredita campaña, otros idiomas ni variantes |
| **M4 — Primera alpha**, G10-G11 para `alpha-es-normal-v1` | Ruta inicial completa en español y Normal/Normal; todas sus salas, puertas, objetos necesarios, enemigos, jefes, acertijos, secuencias, final, créditos y resultados | Recorrido sin debug hasta el final, matriz por unidad, pruebas asociadas, defectos y exclusiones temporales visibles | Otros idiomas, dificultades, rutas/finales alternativos y extras pueden seguir sin soporte; todos conservan obligación en M5 |
| **M5 — Candidato completo**, G12-G14 y G11 vigente para todo el alcance | Todo el contenido de la edición identificado en la matriz, incluidos variantes, idiomas y extras; opciones, guardados, recuperación y funcionamiento offline | Inventario sin obligatorios pendientes; pruebas por unidad, al menos dos recorridos principales sin debug, pruebas de ramas/dificultades, mediciones físicas y cero P0/P1 según G13 | Solo perfil europeo y destino/launcher certificados; publicación requiere la revisión del candidato exacto de G14 |

La implementación de idiomas y variantes posteriores a la primera alpha continúa en **F10/F11**. Antes de certificar M5 se repiten G10/G11 y las regresiones afectadas sobre el alcance completo; F12/F13 no sustituyen esa integración. Un G11 registrado para `alpha-es-normal-v1` no se reutiliza como evidencia de todos los finales. Cada informe de gate identifica versión de alcance y build.

## Ruta inicial `alpha-es-normal-v1`

Preparación: perfil europeo validado, instalación limpia, textos españoles, acción Normal y acertijos Normal. Empezar desde el menú con **Nueva partida**, sin importar un guardado PS2/PC, desbloqueos externos ni estados de debug. Mantener las reglas y recursos que corresponden a esa configuración del original.

1. Completar la introducción jugable y los eventos de entrada a la campaña que correspondan a Nueva partida.
2. Recorrer en su orden de progresión original todos los segmentos necesarios hasta el desenlace. Incluir retornos, cambios de estado de zonas, puertas, llaves, acertijos, encuentros y jefes que condicionan ese progreso; no reemplazarlos por saltos de escena.
3. Presentar las secuencias y textos de esa ruta, con los efectos de estado correctos tanto al terminar como al saltar una secuencia cuando el original lo permita. Registrar los caminos de ejecución de ambos casos.
4. Alcanzar el final que corresponde a esa primera partida bajo sus reglas originales, mostrar créditos/resultados y comprobar la persistencia de finalización cuando exista en la edición. No forzar flags ni elegir un final mediante un menú de depuración.
5. Durante QA, guardar, cerrar y continuar; probar muerte/reintento y vuelta a zonas visitadas. Las repeticiones parciales con checkpoints sirven para diagnóstico y no sustituyen el recorrido completo T13.

F11.01 convierte este recorrido en una lista ordenada de unidades con sus IDs reales, dependencias y estados esperados. Antes del ensayo de aceptación se fija el itinerario reproducible y sus acciones; el informe identifica el final observado y su referencia en la edición. El contrato de F00.04 es conservar todo lo necesario de principio a fin; la ausencia de un nombre de sala o un ID en esta fase no autoriza omitirlo. No se declara hoy un número de salas, acertijos o finales verificado.

## Corpus inicial `slice-es-normal-v1`

F02.07 debe elegir dos salas **realmente conectadas en la edición identificada** y registrar sus IDs, recursos y estados iniciales/finales. Hasta esa inspección, «sala A» y «sala B» son roles del corpus, no nombres originales ni archivos que se den por encontrados.

| Unidad del corpus | Criterio de selección y prueba | Trabajo / casos |
|---|---|---|
| Sala A y personaje | Geometría, animación, cámara y colisión representativas; candidata a la habitación M2 | F02.07, F05-F06; V03-V05, T03-T05 |
| Conexión A ↔ B | Transición y retorno con progreso persistente; cargas fallidas recuperables; 100 transiciones | F07/F09; V05/V16, T06/T12 |
| Interacción e inventario | Objeto y condición de progreso reales; recoger, examinar/usar, rechazo antes de cumplir condición y ausencia de duplicación | F07; V06, T07 |
| Enemigo | Encuentro original que ejercite detección, ataque, daño, muerte y recuperación; sin introducir enemigos ajenos a la sala | F08/F09; V07, T08 |
| Audio, texto y persistencia | Audio propio del segmento, texto español y guardar/cerrar/continuar con estado equivalente | F07/F09; V08/V10/V11/V12, T10/T11 |
| Riesgos fuera del segmento | Microprueba de carga pesada y muestra audiovisual representativa cuando no aparezcan en A/B | F09/F10; V09/V15-V17; PERF-AV/PERF-MEM |

El investigador de assets propone el par y el responsable de comportamiento/QA verifica sus dependencias. Seleccionar por cobertura de sistemas y riesgos, no solo por coste visual. Si el corpus no permite el circuito requerido, F02.07 permanece pendiente y se busca otro par o se documenta la muestra complementaria necesaria sin simular que pertenece al recorrido. G09 sigue exigiendo integración de los sistemas del slice y caracterización de los riesgos críticos.

## Matriz de obligaciones de contenido

Esta es la matriz de **alcance**, previa al inventario de recursos. Cada fila debe expandirse en F02/F11 en unidades reales con identificador, dependencias, prueba y evidencia. Ninguna fila está validada como contenido del port actualmente.

| ID de alcance | Categoría RF13.01 | Primera alpha M4 | Candidato completo M5 | Verificación principal |
|---|---|---|---|---|
| SC01 | Zonas | Todas las necesarias para la ruta inicial | Todas las zonas jugables de la edición, incluidas variantes de estado | F11.01/F11.03; V05/V13, T13 |
| SC02 | Salas | Todas las necesarias, con sus retornos | Todas las salas del inventario jugable | F11.03; V03-V05/V13 |
| SC03 | Puertas/conexiones | Accesos, bloqueos y transiciones de la ruta | Todas las conexiones y condiciones originales | F07/F11; V05/V06, T06/T07 |
| SC04 | Eventos/acertijos | Progresión completa en Normal/Normal | Todos los eventos y variantes por dificultad/ruta | F07/F11; V06/V13, T07/T13 |
| SC05 | Objetos | Objetos necesarios y los que el itinerario declara utilizables | Todos los objetos obtenibles, incluidos opcionales/desbloqueables | F07/F11; V06/V10, T07 |
| SC06 | Enemigos | Tipos y encuentros de la ruta; reglas de acción Normal | Todos los tipos, estados y variantes presentes | F08/F11; V07, T08 |
| SC07 | Armas | Las usadas en el itinerario y sus estados | Todas las armas obtenibles y condiciones de acceso | F08/F11; V06/V07 |
| SC08 | Jefes | Todos los que requiere la ruta | Todos los jefes y sus variantes incluidas en la edición | F08/F11; V07/V13, T08/T13 |
| SC09 | Secuencias/audio | Todas las secuencias de la ruta, sus clases y pistas necesarias | Todas las secuencias y pistas de contenido soportado, incluidos desenlaces alternativos | F09/F10/F11; V08/V09, T09/T11 |
| SC10 | Idiomas de texto | **Español (`es`)**, interfaz, subtítulos y textos de juego de la ruta | **Español, inglés, francés, alemán e italiano (`es/en/fr/de/it`)** con los textos originales disponibles | F10.07/F11/F13; V09/V11 |
| SC11 | Dificultad de acción | **Normal** | Todas las opciones y niveles desbloqueables presentes en la edición, con condiciones originales | F04/F08/F11/F13; V07/V13 |
| SC12 | Dificultad de acertijos | **Normal** | Todas las opciones presentes, soluciones y textos correspondientes | F07/F10/F11/F13; V06/V09/V13 |
| SC13 | Ramas/rutas | Itinerario de primera partida; las otras ramas se registran como pendientes | Todas las ramas jugables y condiciones de acceso, incluso las que requieren completar previamente el juego | F11/F13; V13, T13 |
| SC14 | Finales | Final alcanzado por la ruta de primera partida conforme al original | Todos los finales presentes y sus condiciones de activación | F10/F11/F13; V09/V13, T09/T13 |
| SC15 | Extras y repetición | No son condición del primer recorrido salvo que este los necesite | Modos, recompensas, opciones y contenido desbloqueable presentes en la edición | F11/F13; V06/V10/V13 |

En M4, todo elemento no probado de SC01-SC15 se registra como no soportado en esa alpha; no basta con decir «el resto pendiente». El inventario F11 debe enumerar esos elementos individualmente antes de anunciarla. Objetos y armas opcionales que no entren en el itinerario inicial conservan obligación M5. «Presente» exige evidencia del perfil europeo: no implica incluir contenido descartado/inaccesible descubierto entre los archivos ni contenido exclusivo de otras ediciones.

## Evidencia, testing y pipeline

F11.01 debe registrar por unidad: ID estable, categoría SC, referencia al perfil y recurso/escena, condición de acceso, dependencias, idioma/dificultad, primer hito obligatorio, estado, casos V/T, build, resultado y enlace a evidencia. Los datos privados se conservan según la [política de custodia](private-data.md). Una categoría aún sin enumerar se marca `sin_inventariar`, nunca `no_aplica` por falta de investigación.

Estados de trabajo previstos: `sin_inventariar`, `identificado`, `convertido`, `integrado`, `validado`, `bloqueado` y `excluido_por_decision`. Solo `validado` cuenta como soporte, dentro del build/perfil/idioma/dificultad probado. Una prueba de variante no valida automáticamente las demás; cambios compartidos activan F11.06. Pesos y denominador de cobertura se fijan en F11.08 antes de medir; hoy no se publica un porcentaje de campaña a partir de los 113 archivos.

- **Alpha:** al menos un recorrido completo de `alpha-es-normal-v1` sin debug y pruebas de cada unidad obligatoria; guardar/cargar, pérdida de vida, transiciones y secuencias incluidos. Los defectos conocidos no pueden impedir llegar al final declarado.
- **Candidato completo:** al menos dos recorridos completos de la ruta principal sin debug, más casos específicos para cada rama, final, dificultad de acción/acertijos y extra del inventario. Probar también las condiciones de desbloqueo; disponer de una partida preparada no demuestra que el desbloqueo se alcance correctamente.
- **Idiomas:** comprobar todas las cadenas incluidas y su asociación al evento, caracteres, desbordamientos, selección/persistencia y legibilidad física; probar variantes de acertijos que cambien textos. El plan F13 registra combinaciones efectivamente ensayadas y riesgos de combinaciones restantes; no atribuye recorridos completos en cinco idiomas a un único ensayo en español.
- **Regresión técnica:** conservar SOLID y la [batería de ingeniería](engineering.md): unitarias, contratos, integración, diferenciales, sanitizadores, cobertura de líneas y ramas y compilación host/3DS. CI trabaja con fixtures sintéticos; los resultados privados y físicos se registran por separado. Una compilación o un workflow verde no valida campaña.

F00.04 se verifica por consistencia documental con RF13/V13, conservación de obligaciones y enlaces; no requiere modificar runtime ni inventar tests de juego. La implementación futura mantiene identificación (`GameProfile`), manifiesto de contenido, lógica del dominio y adaptadores de plataforma como responsabilidades separadas. Este alcance no añade capacidades al perfil ni mezcla la política de publicación con reglas de gameplay.

## Exclusiones y cambios de alcance

| Exclusión | Tipo y fundamento | Condición de revisión |
|---|---|---|
| Otros idiomas/dificultades, finales alternativos y extras en la primera alpha | **Aplazamiento**, SC10-SC15 obligatorios para M5; selección inicial del usuario | Integración posterior en F10/F11 y pruebas antes de M5 |
| Otras revisiones regionales, origen PC y otros modelos de consola | Fuera de esta línea base; origen/destino confirmados | Decisión de producto y perfil/evidencia independientes |
| CIA mediante FBI | Ruta opcional posterior; `.3dsx` es la condición inicial | Decisión específica, build y pruebas del launcher separados |
| Estereoscopía, multijugador nuevo, remake visual, cambios de historia y traducciones/doblajes nuevos | Fuera del objetivo de esta versión, conforme al PDF pp. 3-4 | Nueva decisión de producto con requisitos y evaluación de coste |
| Importar automáticamente partidas PS2/PC | Fuera del objetivo del PDF; no afecta al guardado nativo obligatorio del port | Contrato de conversión y pruebas independientes si se solicita |
| Recursos descartados/inaccesibles o de otras ediciones | No son contenido jugable de la edición seleccionada | Evidencia de uso real obliga a revisar su clasificación |

No se excluye ninguna rama, jefe, final o secuencia obligatoria del objetivo completo por rendimiento o falta de herramienta. Si un requisito no es viable, se informa el resultado y se propone un cambio explícito; mientras tanto sigue pendiente y bloquea su gate.

El responsable de desarrollo puede ordenar tareas y escoger el corpus cumpliendo estas reglas. El responsable de QA acepta resultados contra el alcance vigente. El usuario, como responsable de producto, decide reducciones de contenido o cambios de origen/destino. Son responsabilidades del proyecto, no asignaciones a personas adicionales. Cada cambio registra versión anterior/nueva, razón, unidades SC afectadas, impacto en pruebas y gates, responsable y evidencia de decisión; las unidades retiradas permanecen en la matriz con su motivo. Plantilla en [decisions.md](specs/sh3-3ds/decisions.md).

[F00.07](execution/f00-07-decisions.md) completó el registro Q01-Q14 y la evaluación que aprueba G00; [F00.05](execution/f00-05-profile-custody.md) completó perfil, fuentes y custodia, y [F00.06](execution/f00-06-provenance.md) completó el inventario inicial de procedencia/licencias con pendientes por componente. G01 y posteriores mantienen las pruebas pendientes. La expansión masiva sigue condicionada a G04/G05 y decisión favorable de G09. Esta línea base no autoriza publicar originales ni releases; la custodia y revisión G14 se aplican al artefacto concreto.
