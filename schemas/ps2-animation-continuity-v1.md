# SC01–SC06 — Secuencia continua e IA de la pareja 0x0209

Instancia SA-T5d de F03.02; extensión de
[SA08/SR01–SR06](ps2-skeleton-animation-v1.md). Objetivo: observar el reloj,
la pose y la selección de clips del mismo actor desde un arranque normal,
sin restauraciones ni cambios artificiales del estado del juego.

## Requisitos EARS

- **SC01** WHEN inicia el ensayo THEN SHALL usar un perfil privado exclusivo,
  verificar ejecutable/ISO y registrar el arranque sin `statefile`. Durante
  la secuencia SHALL NOT cargar estados, reiniciar la VM ni escribir memoria,
  código, recursos, reloj, posición o estado de IA.
  Una carga normal de partida desde tarjeta MAY preparar el punto inicial
  antes de medir; SHALL registrarla y distinguirla de restaurar un savestate.
- **SC02** WHEN admite puntos de la secuencia THEN SHALL verificar mismo
  proceso/CRC, ciclos crecientes, identidad del actor y sus recursos,
  descriptores y código. SHALL registrar pausas e inputs normales por separado.
  Una pausa de inspección SHALL NOT computarse como tiempo emulado ni servir
  para atribuir una frecuencia de ejecución real.
- **SC03** WHEN verifica continuidad THEN SHALL capturar evaluaciones
  consecutivas del consumidor durante al menos una vuelta del clip,
  contrastar contador/ticks/velocidad y pose, y rechazar huecos no explicados,
  cambios de actor o discontinuidades del contador.
- **SC04** WHEN atribuye una transición a la IA THEN SHALL observar la llamada
  original de selección, ID solicitado, llamador y actor, seguidos del
  descriptor aplicado y avance de la nueva animación. Cambiar el descriptor
  desde el inspector SHALL NOT satisfacer este requisito.
- **SC05** IF el arranque no alcanza una escena activa o no ocurre una
  transición THEN SHALL conservar la evidencia negativa y mantener abierto
  ese subcaso; SHALL NOT convertir ejecución estática, tasa nominal o capturas
  restauradas en evidencia de continuidad.
- **SC06** WHEN publica la verificación THEN SHALL mantener estados y datos
  originales en la raíz privada, publicar solo metadatos y hashes, y probar
  el reconciliador con secuencias sintéticas válidas e inválidas sin emulador.

## Diseño y tareas

El lanzador crea perfil, copias de BIOS/tarjetas y recibo; el capturador solo
lee PINE y guarda slots nuevos. Los puntos de interrupción detienen el
consumidor o el selector de IA sin modificar instrucciones del huésped.
El reconciliador puro comprueba continuidad y delega la pose al oráculo
independiente existente. No se confunde tiempo de pared con ciclos EE.

- [x] **SC-T1:** arrancar la ISO sin estado previo, identificar cualquier
  espera de carga y alcanzar una escena activa; registrar entorno e inputs.
  - [x] **SC-T1a:** perfil exclusivo, recibo de arranque, dos capturas y cierre
    normal; alcanzar la primera zona jugable y verificar lista de actores.
  - [x] **SC-T1b:** localizar la ruta activa de `0x0209` por petición del usuario:
    overlay/sala, registros de instancias, condiciones y selector de clips.
    [Evidencia](../docs/execution/f03-02-animation-activation.md).
  - [x] **SC-T1c:** alcanzar esa sala por progreso normal o carga inicial de
    tarjeta; observar creación, bandera de activación y recursos de un actor
    `0x0209` real. La localización estática no satisface este subcaso.
    [Llegada y activación comprobadas](../docs/execution/f03-02-animation-continuity.md):
    `0xEB`, bandera 1, tres instancias activas `0x018E–0x0190` y hashes
    completos de la pareja MDL/ANM coincidentes.
- [x] **SC-T2:** capturar una vuelta del mismo actor sin saltos/restauraciones,
  comprobar identidad, ciclos, reloj y pose entre evaluaciones consecutivas.
  Capturas 08–35: 28 retornos, 27 avances, una vuelta completa y 27 poses
  contrastadas. La restauración posterior solicitada por el usuario inicia
  una reproducción diagnóstica separada y no amplía esta evidencia.
- [ ] **SC-T3:** observar selección por IA y su aplicación, con la acción
  normal del jugador si hace falta; conservar pendientes las rutas no vistas.
  - [x] **SC-T3a:** selección inicial `0x1449` desde el llamador original,
    actor identificado, descriptor aplicado y avance posterior observado.
    El intervalo de selección a la primera ancla no se admite como continuo.
  - [ ] **SC-T3b:** observar la recepción de un impacto y selección/aplicación
    de `0x144A`; distinguir impacto recibido, daño calculado y transición.
    La comparación 02/03 confirma vida agotada de los once `0x020C` del
    acertijo, no una transición del recurso `0x0209`.
    - [x] **SC-T3b.1:** investigar inscripción y destinatario en `0xEB`.
      [Auditoría de colisión](../docs/execution/f03-02-carousel-collision.md):
      los tres `0x0209` faltan en ambos bancos de personajes de 08–35 y 36;
      tienen geometría de escenario y flags `0x2002`. El recorrido analizado
      exige un propietario registrado para producir el evento de daño.
      Control positivo con once `0x020C` y ocho controles negativos del
      auditor aprobados. Resultado acotado a código y configuración observados.
    - [ ] **SC-T3b.2:** identificar una configuración alcanzable por juego
      normal que registre al destinatario `0x0209`, o una ruta alternativa
      que produzca el evento correspondiente. Exigir evidencia de propietario
      y condiciones antes de definir otra acción manual; no repetir golpes
      en la configuración descartada ni modificar flags para validar SC04.
      [Revisión acotada realizada, resultado negativo](../docs/execution/f03-02-carousel-alternative-routes.md):
      estados de IA/dificultad, consultas de volumen y múltiples impactos,
      origen del daño, flags del overlay y referencias externas no aportan
      una acción admisible. Se contrastaron 28 ventanas de código en 08/35/36
      y cuatro controles negativos. El criterio positivo sigue pendiente;
      no se afirma una prueba exhaustiva de imposibilidad en todo el juego.
    - [ ] **SC-T3b.3:** si existe esa ruta, capturar evento, cálculo de daño,
      llamada original del selector, descriptor aplicado y avance bajo SC01.
      Conservar el subcaso abierto si no se demuestra una ruta accesible;
      no solicitar repeticiones del acertijo por semejanza visual.
  - [ ] **SC-T3c:** observar selección/aplicación de `0x144B`, avance y fin.
    Las rutas investigadas tras una restauración requieren repetición bajo SC01.
- [ ] **SC-T4:** reconciliador y pruebas de discontinuidad, auditoría privada
  reproducible, informe y actualización de SA-T5d según evidencia real.
  - [x] **SC-T4a:** reconciliador puro de retornos de un clip en loop;
    comprobar identidad, orden de reanudaciones, ciclos, contador, incremento,
    muestras y duración acumulada. 32 pruebas sintéticas; no certifican la VM.
  - [x] **SC-T4b:** aplicar el reconciliador y el oráculo de pose a la vuelta
    real, reconciliar selección inicial por IA y publicar alcance y pendientes.
    Ocho controles negativos adicionales; informe y hashes reproducibles.
  - [ ] **SC-T4c:** incorporar las transiciones pendientes y cerrar SA-T5d
    únicamente con evidencia que cumpla SC01–SC06.

## Registro de continuidad

`tools/qa/animation_continuity.py` valida metadatos de retornos consecutivos
y delega el paso de reloj al oráculo independiente. La identidad debe incluir
sesión, actor, direcciones y hashes de recursos/código, y descriptor. El primer
retorno ancla el contador; su pose anterior no se infiere. Un wrap aislado no
completa una vuelta: se exige avance acumulado de al menos la longitud
inclusiva del clip en Q12.

La columna «Ejecuciones» de los breakpoints de ejecución del PCSX2 fijado
muestra `--`; no proporciona un contador de hits. El ordinal del registro
representa cada reanudación/parada observada con el breakpoint habilitado.
Ese registro debe acompañar a las capturas. El reconciliador detecta
inconsistencias entre metadatos; no sustituye la procedencia ni demuestra por
sí solo que nunca hubo modificaciones o evaluaciones omitidas.
