# Heather: coste de CPU y medición de cadencia

Instancia HP de F03.02/F05.07, posterior a HI-T5b/HI-T6c. El usuario confirmó
60 segundos, rostro, SELECT, zoom, controles, START y tapa/HOME en New 2DS XL
con `f25a2d9bb316`, pero informó baja fluidez y valores aproximados de
60,7 ms Skin+sort CPU, 49 ms Submit+wait y 4,36 ms GPU previous.
La aceptación funcional no acredita rendimiento. No se suman esos tiempos
ni se convierten en FPS: miden etapas distintas y GPU previous es anterior.

## Requisitos EARS

- **HP01** WHEN se reutilice un vértice en varios triángulos THEN el visor
  SHALL preparar su posición de inspección y UV una vez por evaluación,
  conservando pesos Q12, W, índices, materiales y orden de transparencia.
- **HP02** WHEN se solicite dibujar THEN el visor SHALL rechazar salidas
  inválidas y conservar la espera de propiedad GPU antes de escribir el VBO;
  SHALL mantener memoria acotada sin reservas por cuadro.
- **HP03** WHEN el SDK identifique una consola de la familia New THEN el
  adaptador SHALL solicitar CPU rápida, repetir la solicitud tras restaurar
  y desactivarla al salir. IF no puede identificarla THEN SHALL conservar
  el modo predeterminado. El HUD SHALL distinguir solicitud de medición.
- **HP04** WHEN termine una ventana de al menos un segundo THEN el HUD SHALL
  mostrar presentaciones correctas por segundo transcurrido, incluyendo
  intentos ocupados y coste del HUD. WHEN haya suspensión o retroceso del
  reloj THEN SHALL reiniciar la ventana y mostrar lectura no disponible.
- **HP05** WHEN se entregue el candidato THEN el informe SHALL distinguir
  equivalencia numérica, benchmark host, ARM, emulador y rendimiento físico;
  SHALL conservar el baseline y no atribuir mejora física sin repetirla.

## Diseño

El dominio prepara un `RigVertexScratch` por vértice con posición original
y salida de inspección. La copia por índice y la ordenación estable por
profundidad/ordinal conservan el dibujo. La validación del renderizador y
la transferencia del VBO permanecen como frontera independiente.
El scratch aumenta de 28 a 52 bytes por vértice (192 KiB adicionales en
la capacidad máxima de 8.192); lo posee el presentador fuera de la pila.

`FrameCadence` recibe ticks y resultado de presentación, sin SDK ni reloj
global. Su lectura cuenta envíos de aplicación, no barridos de pantalla ni
muestras de animación. La UI se refresca cada 250 ms o al pulsar un botón.
El adaptador 3DS administra CPU rápida y lifecycle; no altera el reloj de
inspección ni reduce malla, texturas o transparencia para obtener la mejora.

## Tareas y aceptación

- [x] **HP-T1 — Registrar baseline y reducir trabajo repetido.** Conservar
  fuentes anteriores; implementar preparación por vértice y comparar todos
  los atributos con un oráculo escalar, pesos 1/2/3, W deficiente, índices
  compartidos, profundidad empatada y cámaras de cuerpo/cara.
- [x] **HP-T2 — Medición y política de plataforma.** Solicitar CPU rápida
  solo en New; añadir FPS de envíos, pruebas de ocupado/cero/suspensión/
  retroceso y reducir redibujado del HUD. Mantener controles y validaciones.
- [x] **HP-T3 — Validación y entrega.** Release y ASan/UBSan; cotejo privado
  de poses/salidas contra baseline; build ARM y controles en emulador; publicar
  ZIP exclusivo con el mismo SRI y texturas. CI ejecuta los nuevos CTest en
  sus matrices host/sanitizadores/cobertura y compila el target ARM existente.
- [x] **HP-T4 — Medir New 2DS XL.** Repetir 60 s de cuerpo y 60 s de cara;
  anotar FPS submit, modo CPU, Skin+sort/Submit+wait/GPU previous, probar
  controles, START y tapa/HOME. Comparar con baseline sin inferir FPS previos.

Después de HP: verificar reloj nativo y selección de locomoción de Heather,
según [HI](heather-inspection.md), antes de la habitación jugable.

[Ejecución HP-T1–T4](../../execution/f03-02-heather-performance.md): build
`8f778b6e4960`; 353 CTest en ambos presets, 82 Python, equivalencia privada
exacta, ARM y 90 s en Azahar. HP-T4 confirmada por el usuario el 2026-10-24:
60 s en cuerpo y 60 s en cara, mayor fluidez, controles, START y tapa/HOME.
Lectura conjunta: 29,9 FPS submit, CPU New fast, Skin+sort 10,27 ms,
Submit+wait 23,1 ms y GPU previous 6,34 ms. No se asignan métricas distintas
a cada encuadre ni se deducen FPS del baseline; reapertura no detallada.
