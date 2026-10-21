# F05.01 — Corte gráfico sintético

## Requisitos EARS

Historia: como desarrollador del port, necesito una escena 3D propia ejecutable en
3DS para comprobar la cámara, el muestreo y la profundidad antes de integrar los
formatos del juego. Esta instancia prepara RF03.01/RF03.02 y RNF05.02; no acredita
fidelidad al original ni cierra F05.01, F05.02 o G05.

- **SR01** WHEN se inicia el ejecutable THEN el sistema SHALL mostrar suelo,
  paredes y un cubo con textura procedural, perspectiva y profundidad opaca.
- **SR02** WHEN se mantienen los controles de cámara THEN la aplicación SHALL
  modificar una cámara orbital acotada con tiempo finito y paso máximo de 0,1 s.
  WHEN se pulsa B THEN SHALL recuperar la cámara inicial.
- **SR03** WHILE la sesión está suspendida THEN la aplicación SHALL omitir
  movimiento y presentación. WHEN se reanuda THEN SHALL esperar la liberación de
  botones y descartar el primer intervalo. WHEN se solicita salir THEN SHALL
  detenerse antes de actualizar o dibujar.
- **SR04** IF falla la inicialización o una presentación THEN el adaptador SHALL
  informar un resultado distinto de éxito y liberar únicamente recursos adquiridos,
  esperando al trabajo GPU antes de liberar buffers, textura o shader.
- **SR05** WHILE se presentan frames THEN el código de la escena SHALL reutilizar
  buffers y textura sin asignaciones propias por frame.
- **SR06** WHEN se compila el artefacto THEN el pipeline SHALL generar ELF, SMDH,
  3DSX, identidad, inventario del SDK y hashes sin recursos originales.
- **SR07** WHEN se informa una validación THEN el informe SHALL distinguir pruebas
  host, compilación ARM, emulador y consola física.

## Diseño

Se conserva el diagnóstico 2D como ejecutable independiente. `sh3_render_probe`
compone valores de escena y cámara del dominio, un controlador de aplicación y
un puerto de presentación. El adaptador Citro3D posee target, shader, VBO y
textura; el punto de entrada posee gfx y el hook APT. No hay dependencias SDK en
dominio/aplicación, carga de ISO, datos del juego, audio ni simulación de Heather.

Una malla fija de 60 vértices describe suelo, tres paredes y seis caras del cubo.
Cada vértice contiene posición, UV y color. Una textura RGBA8 de 64×64 con patrón
propio utiliza bloques Morton de 8×8; el empaquetado se prueba independientemente
del SDK. PICA200 aplica una matriz perspectiva-vista y modula textura con color.
La cámara mira al centro del cubo desde el frente abierto de la habitación:
Y arriba, convención diestra, FOV vertical 60°, near 0,1 y far 30.
Estas convenciones no se atribuyen a Silent Hill 3.
El giro queda entre −0,55 y +0,55 radianes para mantener la línea de visión al
cubo dentro del frente abierto; elevación 0,1–0,8 y distancia 3–9 unidades.

La prueba usa nearest/repeat, material opaco, escritura de profundidad invertida
de Citro3D (`GREATER`, clear 0), sin culling de caras. No introduce transparencias,
luces, niebla, skinning ni decisiones de encuadre del juego. Los recursos son
inmutables durante los frames. RAII libera el target (sincroniza GPU) antes de
textura/VBO/programa y termina Citro3D antes de gfx.

La aplicación depende de `IRenderScene`, cuyo contrato distingue presentación,
frame ocupado, cámara inválida y error. Se valida la misma aplicación con un
presentador de prueba; el adaptador se compila contra dobles SDK para fallos y
orden de liberación. Esos dobles no demuestran ejecución de GPU.

## Tareas y aceptación

- [x] **SR-T1 — Congelar el corte y los límites.** Definir SR01–SR07,
  responsabilidades, controles y qué gates permanecen abiertos.
- [x] **SR-T2 — Construir escena y controlador portables.** Añadir malla propia,
  cámara orbital y puerto; probar límites, valores no finitos, suspensión,
  reanudación, salida y sustitución del presentador. Requisitos SR01–SR03.
- [x] **SR-T3 — Implementar adaptador PICA200.** Shader, textura procedural,
  VBO persistente, target con profundidad, errores y RAII. Probar empaquetado,
  fallos de adquisición y frames rechazados. Requisitos SR01, SR04, SR05.
- [x] **SR-T4 — Integrar build y comprobar ejecución.** Añadir target y script
  sin sobrescribir evidencia previa, artefactos de CI, Release/sanitizadores,
  SDK ARM fijado y observación en Azahar. Requisitos SR06, SR07.
- [ ] **SR-T5 — Validar New Nintendo 2DS XL.** Copiar el 3DSX a Homebrew Launcher;
  comprobar textura, oclusión, controles, B, START, HOME y tapa; registrar ID,
  launcher y resultados. La instalación CIA/FBI no forma parte de este corte.
  Avance del 2026-10-20: el usuario confirma arranque, cámara con cruceta, X/Y,
  B y START. Identificación, inspección visual detallada, duración y recorrido de
  suspensión pendientes; véase el [registro físico](../../compatibility/synthetic-render-probe.md).

Controles: cruceta izquierda/derecha orbita; arriba/abajo eleva/baja; X acerca,
Y aleja; B restablece; START sale. La pantalla inferior identifica el corte como
sintético y muestra cámara y frames presentados.
