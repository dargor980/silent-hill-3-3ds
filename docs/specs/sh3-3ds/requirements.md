# Requisitos EARS: Silent Hill 3 de PS2 a Nintendo 3DS

Versión documental: 1.0. Fecha: 2026-10-16. Estado: especificación derivada para revisión; implementación y viabilidad no verificadas.

Fuente: `SPEC_Silent_Hill_3_PS2_a_3DS_v1.0.pdf`, 35 páginas. Los números de página corresponden a la numeración impresa del PDF. Se conservan sus identificadores RF01-RF14 y RNF01-RNF12; el sufijo identifica un criterio verificable nuevo.

## Convenciones y alcance

Cada criterio usa EARS: `WHEN evento THEN sistema SHALL respuesta`, `WHILE estado sistema SHALL respuesta`, `IF condición indeseada THEN sistema SHALL respuesta`, `WHERE capacidad opcional sistema SHALL respuesta` o `El sistema SHALL obligación permanente`. `SHALL` significa DEBE. Las conjunciones se limitan a resultados de una misma operación o condición.

Procedencia: **[E]** desarrolla una obligación explícita del PDF; **[P]** conserva una propuesta o meta provisional del PDF; **[D]** introduce una precisión derivada para volver verificable el requisito; **[U]** incorpora la instrucción posterior del usuario de aplicar SOLID, testing y pipelines. [P] y [D] necesitan resolución antes de certificar el comportamiento afectado. Un criterio escrito no es una prueba superada.

El producto previsto es una adaptación nativa de una edición PS2 identificada. El destino confirmado es New Nintendo 2DS XL con Homebrew Launcher mediante `.3dsx`, sin estereoscopía. La copia europea es `SLES-51434`, PAL, versión 1.02, identificada por coincidencia de imagen con Redump 1064; idiomas catalogados en/fr/de/es/it. El usuario confirmó textos españoles, acción Normal y acertijos Normal para la primera alpha; [alcance por hito](../../scope.md). Los demás idiomas y variantes conservan su obligación para el candidato completo. El perfil local es independiente del candidato `ps2-ntsc-u-1.02` del PDF.

No forman parte del primer objetivo: multijugador nuevo, remake visual, cambios de historia, traducciones nuevas, importación automática de guardados PS2/PC, todas las revisiones regionales, Old 3DS ni CIA. Las dos últimas pueden investigarse como perfiles independientes. No se plantea ejecutar PCSX2 en 3DS ni convertir una ISO directamente en una aplicación. Cambiar el origen a PC exige una decisión expresa de alcance. Fuente: pp. 3-6.

Roles: jugador; investigador de formatos y comportamiento; desarrollador del motor y pipeline; responsable de QA; responsable de publicación/mantenimiento. Una persona puede asumir varios roles. La autorización para redactar estas specs no equivale a ejecutar extracción, instalar herramientas, publicar artefactos o implementar el port.

## Requisitos funcionales

### RF01. Identificación y compatibilidad de entradas

**Historia:** Como responsable del pipeline, quiero identificar la edición para evitar conversiones con offsets o recursos de otra revisión.

**Fuente:** pp. 7, 11, 14, 27-29. **Verificación:** V01, T01, T14.

- **RF01.01 [E]** WHEN se registra una edición THEN el pipeline SHALL generar un perfil con ID, plataforma, región, revisión, serial, idioma, capacidades, versión del extractor, tamaños esperados y SHA-256 de cada archivo requerido.
- **RF01.02 [E]** WHEN se solicita extraer una copia THEN el pipeline SHALL verificar todos los tamaños y hashes requeridos contra un único perfil antes de interpretar offsets específicos.
- **RF01.03 [E]** IF falta un archivo requerido, cambia su hash o la revisión no coincide THEN el pipeline SHALL detener la extracción específica e identificar la incompatibilidad.
- **RF01.04 [E]** WHEN se identifica una revisión distinta THEN el proyecto SHALL registrarla como perfil independiente sin reutilizar offsets no verificados.
- **RF01.05 [E]** WHEN el motor abre un paquete THEN el cargador SHALL comprobar integridad, esquema, perfil y versión mínima de motor antes de exponer sus recursos.
- **RF01.06 [E]** IF no existe una copia identificada THEN el proyecto SHALL limitar el trabajo dependiente de datos a recursos sintéticos.

### RF02. Inventario y conversión repetible

**Historia:** Como desarrollador del pipeline, quiero reconstruir cada paquete y rastrear sus entradas para corregir formatos y calidad sin operaciones ocultas.

**Fuente:** pp. 7, 9-12, 16-17, 23. **Verificación:** V02.

- **RF02.01 [E]** WHEN se inventaría una entrada THEN el pipeline SHALL registrar ID estable, origen, contenedor, offset cuando corresponda, tamaño, hash, tipo, dependencias conocidas y estado de soporte.
- **RF02.02 [E]** IF una entrada o dependencia no está comprendida THEN el inventario SHALL marcarla como desconocida y bloquear su declaración de soporte cuando sea obligatoria.
- **RF02.03 [E]** WHEN se repite la extracción o conversión en directorios vacíos con idénticas entradas, recetas y versiones THEN el pipeline SHALL producir los mismos hashes de salida.
- **RF02.04 [E]** WHEN se decodifica un recurso THEN el pipeline SHALL conservar una representación intermedia con versión del decodificador, receta y metadatos del juego no representables en el formato de inspección.
- **RF02.05 [E]** WHEN se convierte una malla, esqueleto o animación THEN el pipeline SHALL conservar las convenciones declaradas de ejes, unidades, caras, jerarquía, pose, base temporal, interpolación, raíz y eventos aplicables.
- **RF02.06 [E]** WHEN una receta reduce texturas o geometría THEN el pipeline SHALL registrar dimensiones o complejidad de origen y destino, formato y pérdidas aceptadas, manteniendo la colisión independiente.
- **RF02.07 [E]** WHEN se empaqueta un sector THEN el pipeline SHALL calcular sus dependencias y emitir un reporte de bytes por categoría, recursos pendientes y referencias faltantes.
- **RF02.08 [E]** IF falta un recurso obligatorio THEN el pipeline SHALL fallar con un diagnóstico en vez de sustituirlo silenciosamente por una salida vacía.

### RF03. Escenarios, materiales y presentación

**Historia:** Como jugador, quiero reconocer los escenarios y sus elementos interactivos con una presentación adecuada a la consola.

**Fuente:** pp. 7, 11, 17, 19. **Verificación:** V03, T03.

- **RF03.01 [E]** WHEN se carga un escenario soportado THEN el renderizador SHALL reproducir sus puntos de referencia, proporciones, ejes y orientación de caras conforme al caso comparativo aprobado.
- **RF03.02 [E]** WHEN se dibuja un material THEN el renderizador SHALL aplicar su modo opaco, recorte alpha o transparencia y sus reglas declaradas de muestreo, profundidad y orden.
- **RF03.03 [E]** WHEN una escena requiere luz, niebla o linterna THEN el renderizador SHALL aplicar la representación validada para ese material y registrar las diferencias aceptadas frente al original.
- **RF03.04 [E]** WHEN se adapta el encuadre a la pantalla THEN el motor SHALL usar la política aprobada de bandas o campo de visión sin deformar la relación de aspecto.
- **RF03.05 [E]** WHEN se valida una escena THEN el proyecto SHALL conservar capturas comparables del original y del port con perfil, cámara y criterios de orientación, máscaras y legibilidad identificados.

### RF04. Movimiento, animación y cámara

**Historia:** Como jugador, quiero que el personaje responda de forma coherente con el original aunque varíe la carga gráfica.

**Fuente:** pp. 7, 10, 18, 20, 29. **Verificación:** V04, T04, T05.

- **RF04.01 [E]** WHEN se reproduce una entrada grabada desde un estado de referencia THEN el controlador SHALL producir el estado discreto esperado y posiciones dentro de tolerancias previamente justificadas.
- **RF04.02 [E]** WHEN cambia la cadencia de presentación THEN el motor SHALL conservar velocidad, temporizadores, ventanas de ataque y duración de eventos según la semántica temporal investigada.
- **RF04.03 [E]** WHEN se activa idle, caminar, correr o girar THEN el sistema de animación SHALL ejecutar el clip y la transición correspondientes al estado validado.
- **RF04.04 [E]** WHEN un clip contiene transformación raíz THEN el controlador SHALL aplicar el desplazamiento una sola vez conforme al contrato de animación.
- **RF04.05 [E]** WHEN el personaje cruza una zona de cámara THEN el sistema de cámara SHALL aplicar la cámara, interpolación y restricciones del caso de referencia.
- **RF04.06 [E]** IF un controlador o cámara solo sirve al prototipo THEN el registro de capacidades SHALL identificarlo como provisional sin contabilizarlo como fidelidad implementada.

### RF05. Colisión, habitaciones y activadores

**Historia:** Como jugador, quiero navegar y volver entre habitaciones sin atravesar obstáculos ni perder el estado del mundo.

**Fuente:** pp. 7, 20-21, 23, 29. **Verificación:** V05, T06.

- **RF05.01 [E]** WHEN un movimiento encuentra paredes, esquinas, puertas, escalones o pendientes del corpus THEN el sistema de colisión SHALL resolverlo conforme al recorrido de referencia sin penetración persistente ni atrapamiento.
- **RF05.02 [E]** WHEN se cumple una condición de activación espacial THEN el sistema de eventos SHALL emitir la transición definida con el orden y multiplicidad documentados.
- **RF05.03 [E]** WHEN se vuelve a una habitación visitada THEN el motor SHALL restaurar los objetos, flags y entidades persistentes que correspondan al progreso actual.
- **RF05.04 [E]** WHEN se solicita cambiar de sector THEN el cargador SHALL validar las dependencias del destino antes de reanudar la simulación en ese sector.
- **RF05.05 [D]** IF falla la carga de un destino THEN la aplicación SHALL conservar el último estado recuperable y ofrecer un error controlado sin confirmar una transición incompleta.

### RF06. Objetos, inventario y eventos

**Historia:** Como jugador, quiero recoger y usar objetos para avanzar sin duplicaciones ni consumo indebido.

**Fuente:** pp. 7, 18, 21, 29. **Verificación:** V06, T07.

- **RF06.01 [E]** WHEN el jugador examina, recoge, usa o equipa un objeto válido THEN el dominio SHALL aplicar los efectos de inventario y progreso del caso de referencia.
- **RF06.02 [E]** IF una recogida o uso es inválido THEN el dominio SHALL rechazarlo sin consumir objetos ni alterar flags ajenos a la acción.
- **RF06.03 [E]** WHEN se intenta recoger por segunda vez un objeto único ya recogido THEN el dominio SHALL impedir su duplicación.
- **RF06.04 [E]** WHEN se evalúa una puerta con requisito THEN el dominio SHALL permitir o rechazar el acceso según el objeto y los flags documentados.
- **RF06.05 [E]** WHEN se ejecutan eventos de progreso THEN el sistema de eventos SHALL respetar el orden definido e impedir disparos duplicados no previstos.
- **RF06.06 [E]** WHEN se recarga la partida THEN el dominio SHALL conservar inventario y flags sin repetir secuencias ya completadas.
- **RF06.07 [E]** WHEN se acepta el circuito mínimo de progreso THEN el proyecto SHALL demostrar un objeto clave, un consumible, un texto y una puerta condicionada entre dos habitaciones.

### RF07. Enemigos y combate

**Historia:** Como jugador, quiero combates con estados y consecuencias consistentes, incluida muerte y recuperación.

**Fuente:** pp. 7, 18, 22, 25, 29. **Verificación:** V07, T08.

- **RF07.01 [E]** WHEN un enemigo o jefe soportado percibe, se desplaza, ataca, se interrumpe, recibe daño o muere THEN su controlador SHALL seguir los estados y tiempos del caso validado.
- **RF07.02 [E]** WHEN ocurre un impacto válido dentro de su ventana temporal THEN el combate SHALL aplicar una sola resolución de daño por impacto definido.
- **RF07.03 [E]** IF un ataque falla o coincide con un cambio de estado THEN el combate SHALL resolver hitboxes, reacción, invulnerabilidad y consumo según el orden documentado sin daño duplicado.
- **RF07.04 [E]** WHEN muere el jugador y elige continuar THEN la aplicación SHALL restaurar una partida válida según las reglas de recuperación.
- **RF07.05 [E]** WHEN se prueban ataques simultáneos, enemigos bloqueados o salida de habitación THEN el combate SHALL terminar en estados y recursos equivalentes al caso aceptado.
- **RF07.06 [E]** IF una optimización cambia cantidad de enemigos, dificultad o reglas THEN el proyecto SHALL registrar un cambio de alcance antes de aceptar esa versión.

### RF08. Música, ambiente, voz y efectos

**Historia:** Como jugador, quiero audio continuo que conserve información y sincronía durante juego y transiciones.

**Fuente:** pp. 7, 12-13, 15, 23-24. **Verificación:** V08, T11.

- **RF08.01 [E]** WHEN se convierte audio THEN el pipeline SHALL conservar frecuencia, canales, duración y puntos de loop en la representación intermedia.
- **RF08.02 [E]** WHEN el juego reproduce música, ambiente, voz y efectos THEN el subsistema de audio SHALL respetar sus categorías, loops y prioridades explícitas.
- **RF08.03 [E]** IF la demanda de audio supera los canales o buffers disponibles THEN el subsistema de audio SHALL aplicar la política documentada que prioriza los sonidos esenciales.
- **RF08.04 [P]** WHILE se ejecuta la prueba continua de treinta minutos el subsistema de audio SHALL registrar cero underruns y ausencia de clipping no previsto.
- **RF08.05 [E]** WHEN se suspende y reanuda la aplicación THEN el subsistema de audio SHALL restaurar colas y relojes coherentes con el estado de reproducción.
- **RF08.06 [E]** IF la inicialización del servicio de audio falla THEN el diagnóstico SHALL identificar el fallo y evitar declarar superada la prueba de audio.

### RF09. Narrativa, cinemáticas y subtítulos

**Historia:** Como jugador, quiero entender las secuencias y continuar con el progreso correcto al terminarlas o saltarlas.

**Fuente:** pp. 7, 12-13, 24, 29. **Verificación:** V09, T09.

- **RF09.01 [E]** WHEN se incorpora una secuencia THEN el inventario SHALL clasificarla como tiempo real o prerenderizada y registrar dependencias y condiciones de entrada/salida.
- **RF09.02 [E]** WHEN se reproduce una secuencia en tiempo real THEN el sistema narrativo SHALL ejecutar cámaras, animaciones, visibilidad, audio y eventos según la línea temporal validada.
- **RF09.03 [E]** WHEN se reproduce video THEN el proveedor de video SHALL coordinar imagen, audio y subtítulos con timestamps y un reloj maestro definido.
- **RF09.04 [P]** WHILE se ejecuta una cinemática de certificación el proveedor de video SHALL mantener un desajuste audiovisual absoluto inferior a 100 ms en los eventos de sincronización definidos.
- **RF09.05 [E]** WHEN se salta una secuencia que permite salto THEN el sistema narrativo SHALL dejar flags, posición y progreso equivalentes al final normal cuando así lo establezca el caso de referencia.
- **RF09.06 [E]** IF falta un archivo de secuencia THEN la aplicación SHALL informar el error y salir a un estado controlado sin pantalla negra permanente ni audio bloqueado.
- **RF09.07 [E]** WHEN se muestran subtítulos del idioma soportado THEN la UI SHALL representar tildes, signos y cadenas largas dentro del área visible y con saltos de línea legibles en consola.
- **RF09.08 [E]** IF se omite una secuencia obligatoria en un prototipo THEN el manifiesto de alcance SHALL declarar esa limitación e impedir contabilizarla como soportada.

### RF10. Guardado y recuperación

**Historia:** Como jugador, quiero recuperar mi progreso tras cerrar la aplicación o interrumpirse un guardado.

**Fuente:** pp. 7, 12-13, 21-22, 27-29. **Verificación:** V10, T10, T12, T14.

- **RF10.01 [E]** WHEN se guarda una partida THEN la persistencia SHALL serializar versión, perfil, escena, posición, inventario, flags, entidades pertinentes, dificultad y relojes necesarios.
- **RF10.02 [E]** WHEN se crea un nuevo guardado THEN la persistencia SHALL mantener dos generaciones con secuencia e integridad sin sobrescribir la única generación válida.
- **RF10.03 [E]** WHEN se inicia la recuperación THEN la persistencia SHALL elegir la generación completa y válida con la secuencia más reciente.
- **RF10.04 [E]** IF se interrumpe la creación de una generación THEN la persistencia SHALL recuperar una generación íntegra previa cuando exista.
- **RF10.05 [E]** IF una partida tiene perfil, versión o integridad incompatible THEN la persistencia SHALL rechazarla o aplicar una migración expresamente soportada sin interpretar datos incompatibles.
- **RF10.06 [E]** IF no hay espacio o falla una escritura THEN la persistencia SHALL informar el fallo y conservar la generación válida disponible.
- **RF10.07 [P]** WHEN se ejecutan cien ciclos consecutivos de guardado y carga THEN el motor SHALL restaurar el estado esperado en cada ciclo sin corrupción no controlada.
- **RF10.08 [D]** IF ninguna generación es válida THEN la aplicación SHALL informar que no existe una partida recuperable y conservar los archivos para diagnóstico hasta una acción explícita del usuario.

### RF11. Controles y UI

**Historia:** Como jugador, quiero realizar todas las acciones obligatorias con controles configurables y mensajes legibles.

**Fuente:** pp. 7, 15, 20-21, 24, 27. **Verificación:** V11.

- **RF11.01 [E]** WHEN el jugador configura los controles THEN el sistema de entrada SHALL permitir reasignar movimiento, acción, correr, arma, cámara, mapa, inventario, linterna y pausa.
- **RF11.02 [E]** WHEN se usan combinaciones simultáneas del catálogo de acciones THEN el sistema de entrada SHALL entregar las acciones correspondientes conforme al mapeo validado.
- **RF11.03 [E]** WHILE se ejecuta combate el juego SHALL permitir los controles básicos sin exigir pantalla táctil.
- **RF11.04 [E]** WHEN se define un mapeo THEN el perfil de entrada SHALL respetar las combinaciones reservadas por el sistema.
- **RF11.05 [E]** WHEN se presentan inventario, mensajes, mapa o configuración THEN la UI SHALL permitir leer el contenido y acceder a todas las acciones obligatorias en el tamaño físico de la consola probada.
- **RF11.06 [D]** WHEN el jugador restaura las opciones THEN la configuración SHALL recuperar el perfil predeterminado validado y persistirlo si la escritura finaliza correctamente.

### RF12. Ciclo de vida

**Historia:** Como jugador, quiero pausar, suspender y salir sin dejar el juego o sus recursos en estados inconsistentes.

**Fuente:** pp. 7, 10, 15, 23-24, 27. **Verificación:** V12, T11.

- **RF12.01 [E]** WHEN se pausa el juego THEN la aplicación SHALL detener los relojes de simulación y eventos definidos como pausables y conservar los relojes que correspondan al audio o al sistema.
- **RF12.02 [E]** WHEN se reanuda desde pausa o suspensión THEN la aplicación SHALL restaurar estado y relojes sin adelantar eventos por el tiempo suspendido.
- **RF12.03 [E]** WHEN se solicita suspensión durante juego, combate, carga, audio, secuencia o guardado THEN la aplicación SHALL seguir la política de ciclo de vida validada para esa operación.
- **RF12.04 [E]** WHEN se solicita salida o retorno a menú THEN la aplicación SHALL liberar recursos propios y conservar el progreso ya confirmado.
- **RF12.05 [D]** IF una operación queda incompleta al suspender o cerrar THEN la aplicación SHALL cancelarla o retomarla desde un punto definido sin informar un éxito no confirmado.

### RF13. Campaña y madurez del producto

**Historia:** Como jugador y responsable de QA, quiero saber qué contenido puedo completar y qué exclusiones existen.

**Fuente:** pp. 3-4, 23, 25, 27, 32-34. **Verificación:** V13, T13.

- **RF13.01 [E]** WHEN se declara contenido soportado THEN el manifiesto SHALL enumerar zonas, salas, puertas, eventos, objetos, enemigos, armas, jefes, secuencias, idiomas, dificultades, ramas y finales incluidos.
- **RF13.02 [E]** WHEN se presenta el vertical slice THEN el producto SHALL integrar dos habitaciones conectadas, personaje animado, cámara, colisiones, interacción, enemigo, inventario, audio y persistencia.
- **RF13.03 [E]** WHEN se declara una alpha de campaña THEN QA SHALL demostrar un recorrido de principio a fin del alcance declarado sin atajos de debug y registrar fallos y exclusiones.
- **RF13.04 [E]** WHEN se declara un candidato completo THEN cada elemento obligatorio del alcance SHALL tener prueba asociada y toda omisión SHALL contar con cambio de alcance registrado.
- **RF13.05 [E]** WHEN se certifica la ruta principal THEN QA SHALL completar al menos dos recorridos sin debug y pruebas específicas de todas las ramas y dificultades incluidas.
- **RF13.06 [E]** WHEN se informa cobertura THEN el proyecto SHALL calcularla sobre unidades de contenido definidas y ponderadas sin equiparar archivos extraídos con jugabilidad implementada.
- **RF13.07 [E]** IF G04, G05 o los riesgos críticos de G09 no tienen evidencia suficiente THEN el proyecto SHALL mantener bloqueada la expansión masiva de campaña dependiente de esos resultados.

### RF14. Diagnóstico y evidencia

**Historia:** Como desarrollador y responsable de soporte, quiero localizar fallos sin logs ilimitados ni exposición innecesaria de datos privados.

**Fuente:** pp. 7-8, 15, 28, 30, 33. **Verificación:** V14.

- **RF14.01 [E]** WHEN ocurre un error gestionado THEN el diagnóstico SHALL incluir código de error, build ID y escena o etapa afectada.
- **RF14.02 [E]** WHILE se generan logs el diagnóstico SHALL mantenerlos dentro de la capacidad y política de rotación fijadas en el perfil de diagnóstico.
- **RF14.03 [E]** WHEN se investiga un fallo de prueba THEN el proyecto SHALL asociar el reporte con los símbolos del mismo build.
- **RF14.04 [E]** WHEN se registra una prueba THEN el proyecto SHALL conservar ID, requisitos, hardware, build, edición, estado inicial, entradas, resultados esperado y observado, y ubicación de evidencia.
- **RF14.05 [E]** WHEN se prepara un reporte público THEN el proyecto SHALL excluir rutas personales, originales y dumps completos no autorizados.
- **RF14.06 [E]** WHEN se abre una incidencia THEN la plantilla SHALL solicitar versión, modelo, launcher, perfil, escena, pasos, resultado esperado y log mínimo sin assets.

## Requisitos no funcionales

### RNF01. Frame y medición temporal

**Historia:** Como jugador y responsable de rendimiento, quiero una cadencia medible que conserve las reglas del juego.

**Fuente:** pp. 3, 13, 19-20, 23, 26. **Verificación:** V15.

- **RNF01.01 [P]** WHEN se diseña para el perfil inicial de 30 FPS THEN el presupuesto SHALL usar un intervalo nominal de 1000/30 ms y una meta aproximada de 26,7 ms de trabajo crítico como margen de diseño.
- **RNF01.02 [P]** WHEN se certifica cada escena obligatoria con tres recorridos de diez minutos en hardware THEN al menos el 99 % de los frames SHALL alcanzar su objetivo de presentación de 30 FPS, considerando la variación del refresco previamente caracterizada.
- **RNF01.03 [P]** WHEN se evalúa cada recorrido de certificación THEN el p99 de trabajo crítico SHALL ser inferior a 33,33 ms.
- **RNF01.04 [P]** WHILE transcurre un recorrido fuera de transiciones registradas el motor SHALL evitar pausas inexplicadas superiores a 100 ms.
- **RNF01.05 [E]** WHEN se genera un benchmark THEN el informe SHALL separar simulación, animación, envío gráfico, espera GPU, carga/descompresión y audio sin sumar tiempos solapados como seriales.
- **RNF01.06 [E]** WHEN se cambia compilador, LTO, precisión o perfil CPU THEN el proyecto SHALL repetir las regresiones temporales y medir la configuración exacta, incluida la reanudación.

### RNF02. Memoria y residencia

**Historia:** Como responsable del motor, quiero presupuestos basados en la memoria disponible de la aplicación.

**Fuente:** pp. 11, 13, 19-20, 23, 26. **Verificación:** V16, T06, T12.

- **RNF02.01 [E]** WHEN se establece un perfil de ejecución THEN el diagnóstico SHALL medir B_app y los límites observables de heap, memoria lineal y GPU en ese modelo y launcher.
- **RNF02.02 [P]** WHILE se ejecuta el perfil inicial el pico_app SHALL ser menor o igual que 0,80 × B_app, incluida la base del motor y toda residencia temporal de transiciones.
- **RNF02.03 [E]** WHEN se contabiliza memoria THEN el informe SHALL controlar por separado los límites de pools aplicables sin contar dos veces una misma asignación.
- **RNF02.04 [E]** IF no cabe la coexistencia de sectores THEN el cargador SHALL usar una transición explícita que libere recursos de forma segura antes de construir el destino.
- **RNF02.05 [P]** WHEN se completan cien transiciones tras calentamiento THEN el crecimiento de memoria retenida SHALL ser como máximo 1 MiB salvo una causa documentada y aprobada.
- **RNF02.06 [E]** WHEN se liberan recursos compartidos THEN el motor SHALL esperar a que terminen los trabajos GPU/audio que los utilizan y evitar duplicaciones de residencia sin control.
- **RNF02.07 [E]** WHEN se fijan límites de polígonos, huesos, influencias, entidades o draw calls THEN el perfil SHALL vincular cada límite a mediciones del corpus y hardware correspondientes.

### RNF03. Estabilidad y errores recuperables

**Historia:** Como jugador, quiero completar sesiones y reconocer cuándo una carga o un fallo necesita atención.

**Fuente:** pp. 7, 13, 15, 20, 23, 26-27. **Verificación:** V17, T12, T13.

- **RNF03.01 [P]** WHEN se ejecuta el diagnóstico temprano de treinta minutos THEN la aplicación SHALL completar la prueba sin cierre inesperado.
- **RNF03.02 [E]** WHEN se valida navegación durante treinta minutos THEN el motor SHALL completar el recorrido previsto sin penetración, atrapamiento ni cambio de velocidad debido al renderizado.
- **RNF03.03 [P]** WHEN se certifica cada perfil durante dos horas THEN el motor SHALL terminar sin cierres, bloqueos de progreso ni picos de memoria inexplicados.
- **RNF03.04 [E]** IF faltan la SD, archivos, memoria o almacenamiento THEN la aplicación SHALL informar el fallo y liberar recursos parciales conservando el estado recuperable disponible.
- **RNF03.05 [E]** WHILE se carga un sector la aplicación SHALL presentar un estado visible que distinga carga, finalización y error.
- **RNF03.06 [E]** WHEN se cierra F09 THEN el informe SHALL medir carga fría y caliente en una SD identificada y fijar el máximo aceptado para el perfil antes de certificarlo.

### RNF04. Dominio portable

**Historia:** Como desarrollador, quiero contrastar lógica fuera de PS2 y 3DS para separar fidelidad de plataforma.

**Fuente:** pp. 8-10, 18. **Verificación:** V18.

- **RNF04.01 [E]** El núcleo de dominio SHALL compilar sin cabeceras de 3DS, SDL, OpenGL ni acceso al filesystem del host.
- **RNF04.02 [E]** WHEN se integra código recuperado THEN el módulo SHALL registrar procedencia, revisión, módulo original, ABI, entradas, salidas, efectos y dependencias de plataforma.
- **RNF04.03 [E]** IF una dependencia requiere ensamblador PS2, VU, GS, IOP, overlays o direcciones fijas THEN el catálogo SHALL asignarle una estrategia explícita de adaptación o reimplementación antes de declarar soporte.
- **RNF04.04 [E]** WHEN se cierra G04 THEN el arnés host SHALL ejecutar lógica real de movimiento, una transición de estado y una operación de inventario con comparaciones diferenciales.

### RNF05. Reproducibilidad de herramientas y builds

**Historia:** Como mantenedor, quiero reconstruir un resultado a partir de versiones y recetas identificables.

**Fuente:** pp. 1, 5-6, 8, 15, 17, 28, 31. **Verificación:** V19, V02.

- **RNF05.01 [E]** WHEN se adopta una dependencia THEN el inventario SHALL fijar versión o commit, entorno, licencia y evidencia de compatibilidad.
- **RNF05.02 [E]** WHEN se construye desde un checkout limpio THEN el procedimiento documentado SHALL producir los builds host y 3DS usando el inventario fijado y datos sintéticos en CI pública.
- **RNF05.03 [E]** WHEN un recurso requiere una operación manual THEN el pipeline SHALL registrarla y bloquear su declaración de conversión automatizada hasta convertirla en una receta reproducible.
- **RNF05.04 [E]** IF una herramienta necesaria no funciona en macOS THEN el proyecto SHALL documentar un entorno compatible autorizado o un adaptador propio verificado sin trasladar esa dependencia al runtime.
- **RNF05.05 [E]** WHEN se actualiza una dependencia THEN el proyecto SHALL probarla de forma aislada antes de cambiar la versión fijada.

### RNF06. Robustez de datos

**Historia:** Como desarrollador, quiero rechazar datos inválidos antes de provocar lecturas fuera de rango o reservas excesivas.

**Fuente:** pp. 8, 10-11, 16-17, 27, 29. **Verificación:** V20, T02, T12, T14.

- **RNF06.01 [E]** WHEN se lee una entrada binaria THEN el lector SHALL verificar versión, rangos, offsets y tamaños antes de leer o reservar memoria.
- **RNF06.02 [E]** IF existen solapamientos no permitidos, IDs duplicados, referencias ausentes o tamaños descomprimidos excesivos THEN el lector SHALL rechazar el paquete con un error controlado.
- **RNF06.03 [E]** IF una malla o animación contiene índices inválidos, huesos inexistentes o valores no finitos THEN el validador SHALL rechazar el recurso afectado.
- **RNF06.04 [E]** IF una ruta extraída es absoluta o escapa del directorio de destino THEN el extractor SHALL rechazarla sin escribir fuera de dicho directorio.
- **RNF06.05 [E]** WHEN se serializa un formato propio THEN el escritor SHALL usar tamaños enteros y endianess explícitos, offsets relativos y ausencia de punteros o dependencia de padding nativo.
- **RNF06.06 [E]** WHEN se inicia la implementación del lector SH3P THEN el proyecto SHALL disponer de especificación binaria exacta, límites y fixtures compartidos con el escritor.
- **RNF06.07 [D]** IF un cálculo de offset más tamaño desborda el rango representable THEN el lector SHALL rechazarlo antes de acceder al archivo.

### RNF07. Calidad y cierre por evidencia

**Historia:** Como responsable de QA, quiero distinguir trabajo demostrado de soporte aparente.

**Fuente:** pp. 1, 8, 27, 29-30, 33. **Verificación:** V21.

- **RNF07.01 [E]** WHEN se cierra una tarea THEN el registro SHALL incluir implementación o investigación revisada, pruebas reproducibles, documentación y evidencia ligada al build o commit.
- **RNF07.02 [E]** IF una capacidad depende de un stub de éxito, recurso omitido o caso desactivado THEN el registro SHALL impedir declararla implementada.
- **RNF07.03 [E]** WHEN se corrige una regresión THEN el proyecto SHALL incorporar una prueba que reproduzca el fallo.
- **RNF07.04 [E]** IF permanece un P0 o P1 abierto THEN el proceso SHALL bloquear integración del fallo crítico y aceptación del candidato final.
- **RNF07.05 [E]** WHEN una prueba falla o no puede ejecutarse THEN el reporte SHALL conservar su estado fallido o bloqueado sin convertirlo en aprobado por ausencia de ejecución.
- **RNF07.06 [U]** WHEN se propone integrar un cambio THEN los pipelines SHALL compilar host y 3DS y ejecutar las comprobaciones automáticas aplicables con fallo bloqueante.
- **RNF07.07 [D]** WHEN se valida código portable o herramientas Python THEN la suite SHALL alcanzar al menos 80 % de cobertura de líneas y ramas en el alcance implementado, documentando exclusiones sin presentar el adaptador 3DS como probado por cobertura host.
- **RNF07.08 [U]** WHEN se implementa una capacidad THEN su batería de pruebas SHALL cubrir comportamiento normal, límites, errores, contratos de adaptadores e integración aplicables con trazabilidad al requisito.
- **RNF07.09 [D]** WHEN un pipeline genera un artefacto THEN el reporte SHALL identificar toolchain, fuentes y checksums y distinguir compilación de ejecución real y de publicación.

### RNF08. Custodia y publicación revisada

**Historia:** Como responsable del repositorio, quiero separar datos privados y artefactos revisados durante todo el proyecto.

**Fuente:** pp. 3, 6, 8-9, 14, 28, 33. **Verificación:** V22.

- **RNF08.01 [E]** WHEN se almacenan originales, extracciones, conversiones privadas, savestates o dumps THEN el proyecto SHALL ubicarlos fuera del checkout mediante configuración explícita, salvo ISO locales en `binaries` solicitadas por el usuario, cuya exclusión de Git SHALL verificarse antes de aceptar la custodia.
Nota de cambio 2026-10-16: RNF08.01 incorpora la ubicación `binaries` indicada por el usuario; prevalece sobre la ubicación externa original del PDF. No habilita versionar originales.

- **RNF08.02 [E]** WHEN se ejecuta CI pública THEN el proyecto SHALL usar exclusivamente recursos sintéticos o expresamente aptos para esa distribución.
- **RNF08.03 [E]** WHEN se prepara una publicación THEN el responsable SHALL revisar procedencia y condiciones de cada componente, incluidos código recuperado, generado, dependencias, binarios y recursos.
- **RNF08.04 [E]** IF la redistribución de un componente no está aclarada THEN el paquete público SHALL excluirlo hasta completar su revisión específica.
- **RNF08.05 [E]** WHEN se cierra G14 THEN el candidato SHALL coincidir con el manifiesto de checksums y contener solo archivos revisados y documentados.
- **RNF08.06 [E]** IF se propone enviar originales a un servicio externo THEN el proyecto SHALL exigir permiso y evaluación de las condiciones aplicables antes de enviarlos.
- **RNF08.07 [E]** El proyecto SHALL desarrollar sin dependencia de SDK comerciales filtrados ni presuponer disponibilidad del código original de Konami.

### RNF09. Fidelidad y diferencias declaradas

**Historia:** Como jugador e investigador, quiero saber qué comportamientos están verificados y qué adaptaciones difieren del original.

**Fuente:** pp. 3-4, 8, 18-26, 29, 31. **Verificación:** V23.

- **RNF09.01 [E]** WHEN se compara comportamiento THEN la prueba SHALL exigir igualdad exacta para datos discretos y una tolerancia justificada por variable para valores continuos.
- **RNF09.02 [E]** WHEN se acepta una diferencia de imagen, audio o comportamiento THEN el registro SHALL identificar caso, motivo, impacto, responsable y criterio de aceptación.
- **RNF09.03 [E]** IF se modifica una meta o alcance THEN el proyecto SHALL versionar la decisión y conservar resultados anteriores sin alterar retroactivamente el test para ocultar fallos.
- **RNF09.04 [E]** WHEN se cambia código compartido, lector o receta de materiales THEN el proyecto SHALL repetir las regresiones de contenido previamente aceptado afectado por el cambio.

### RNF10. Operación offline

**Historia:** Como jugador, quiero jugar y guardar sin conectividad ni cuentas externas.

**Fuente:** p. 8. **Verificación:** V24.

- **RNF10.01 [E]** WHILE el juego se ejecuta el motor SHALL permitir las funciones soportadas sin cuenta, servidor ni telemetría remota obligatorios.
- **RNF10.02 [D]** WHEN se ejecuta el recorrido offline con conectividad deshabilitada THEN el juego SHALL permitir iniciar, jugar, guardar y cargar sin esperar respuestas de red.

### RNF11. Mantenibilidad y contratos

**Historia:** Como mantenedor, quiero sustituir servicios de plataforma sin reescribir reglas del juego.

**Fuente:** pp. 8-10. **Verificación:** V25.

- **RNF11.01 [E]** El diseño SHALL separar dominio, aplicación, puertos, adaptadores de plataforma, código recuperado y herramientas offline.
- **RNF11.02 [E]** WHEN la aplicación necesita gráficos, audio, entrada, assets, guardados, reloj o logs THEN la aplicación SHALL acceder mediante el contrato de sistema correspondiente.
- **RNF11.03 [E]** WHEN se construye una aplicación host o 3DS THEN el punto de composición SHALL proporcionar dependencias explícitas sin singletons globales que las oculten.
- **RNF11.04 [E]** WHEN un subsistema adquiere recursos propios THEN su implementación SHALL declarar propiedad y vida útil y liberarlos mediante un mecanismo RAII adecuado.
- **RNF11.05 [U]** WHEN se diseña un módulo THEN su contrato SHALL declarar una responsabilidad y un motivo de cambio identificable, separando reglas, orquestación y efectos de plataforma (SRP).
- **RNF11.06 [U]** WHEN se añade un adaptador de un servicio existente THEN la implementación SHALL extender ese contrato sin introducir condiciones de plataforma en el dominio (OCP).
- **RNF11.07 [U]** WHEN se sustituye un adaptador por otro THEN ambos SHALL cumplir las mismas precondiciones, resultados y errores observables mediante pruebas de contrato (LSP).
- **RNF11.08 [U]** WHEN un consumidor necesita un servicio THEN su interfaz SHALL incluir únicamente las operaciones requeridas por ese consumidor sin obligar a implementar métodos vacíos (ISP).
- **RNF11.09 [U]** WHEN se compone un caso de uso THEN sus dependencias SHALL inyectarse mediante contratos del núcleo y las reglas de arquitectura SHALL impedir dependencias de dominio hacia infraestructura (DIP).

### RNF12. Compatibilidad explícita y soporte

**Historia:** Como jugador, quiero conocer exactamente qué consola, edición y modalidad han sido probadas.

**Fuente:** pp. 3-6, 8, 13-15, 26-28. **Verificación:** V26.

- **RNF12.01 [E]** WHEN se publica compatibilidad THEN la matriz SHALL identificar modelo, launcher, entorno, configuración CPU, revisión, idioma y perfil gráfico probados con su evidencia.
- **RNF12.02 [P]** WHEN se prepara el primer entregable ejecutable THEN el proyecto SHALL producir un `.3dsx` para el perfil confirmado de la familia New.
- **RNF12.03 [E]** WHERE se incorpore CIA u Old 3DS el proyecto SHALL tratarlos como perfiles separados con mediciones y pruebas independientes.
- **RNF12.04 [E]** WHEN se publica una actualización THEN la documentación SHALL definir compatibilidad motor-paquetes, migración de guardados y procedimiento de reversión.
- **RNF12.05 [E]** IF una combinación de hardware, launcher, edición o idioma no se ha probado THEN el proyecto SHALL identificarla como no verificada sin anunciar soporte.

## Condiciones pendientes de concretar

Los límites de carga, capacidad de logs, tick de simulación, tolerancias numéricas y visuales, codec, esquema binario y presupuestos por pool se resuelven mediante Q01-Q14 en [decisions.md](decisions.md). Los requisitos que dependen de ellos conservan estado pendiente hasta fijar el perfil; no se interpretan como aprobados. Los procedimientos y la matriz de cobertura están en [validation.md](validation.md).
