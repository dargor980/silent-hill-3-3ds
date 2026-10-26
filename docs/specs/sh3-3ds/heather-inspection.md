# Heather original: identificación, conversión y visor

F03.02/F05/F06, instancia HI. Objetivo solicitado: mostrar a Heather con su
atuendo original de partida normal, texturada y animada en el visor de New
2DS XL. No se seleccionan trajes desbloqueables ni variantes de Extra New Game.
Los visores aceptados del caballo conservan sus perfiles y pruebas.

## Requisitos EARS

- **HI01** WHEN se seleccionen recursos THEN el preparador SHALL fijar ISO,
  contenedor, descriptor, ordinal, tamaño y SHA; SHALL distinguir nombre
  candidato, identidad binaria y asociación observada en el juego. SHALL
  seleccionar el modelo original solicitado y registrar variantes descartadas.
- **HI02** WHEN aparezcan huesos, helpers, morphs o materiales fuera del perfil
  anterior THEN el decoder SHALL usar un contrato explícito con límites y
  pruebas; SHALL conservar campos desconocidos y rechazar variantes no cubiertas.
- **HI03** WHEN se convierta una animación THEN el pipeline SHALL comprobar
  ID, tamaño de muestra, pistas, jerarquía y reconstrucción exacta; SHALL
  distinguir un segmento de inspección de un clip identificado en el juego.
- **HI04** WHEN se prepare la malla THEN el pipeline SHALL conservar grupos,
  pesos, paletas, referencias morph y particiones de material; SHALL declarar
  las expresiones o capas aún no aplicadas sin atribuir equivalencia visual.
- **HI05** WHEN se integre el visor THEN el motor SHALL admitir el perfil por
  contratos separados de lectura, pose, deformación y presentación, con
  límites de memoria y errores recuperables; SHALL preservar controles,
  START, tapa y HOME, y mantener identificables los visores anteriores.
- **HI06** WHEN se entregue el build THEN el informe SHALL separar pruebas
  sintéticas, conversiones privadas A/B, contraste con PCSX2, emulador 3DS y
  validación física. SHALL mantener pendientes los resultados no ejecutados.
- **HI07** WHEN el usuario pulse SELECT THEN el visor de Heather SHALL alternar
  entre encuadre de cuerpo y de cara; WHEN use X/Y THEN SHALL permitir una
  distancia mínima de 0,45 unidades de inspección con ajuste fino cercano;
  WHEN pulse B THEN SHALL recuperar el encuadre inicial de cuerpo. El cambio
  SHALL respetar pausa, START y la liberación de botones tras suspensión.

## Diseño y secuencia

Los lectores puros producen datos independientes del filesystem/GPU. La
adquisición usa el lector ISO de solo lectura y el parser MFA existente;
los derivados permanecen en la raíz privada autorizada. Se fijarán recetas
nuevas sin aceptar implícitamente cualquier ID o reutilizar la acreditación
de skinning del caballo como acreditación de Heather.

- [x] **HI-T1 — Identificar el conjunto original.** Recorrer el MFA, comparar
  candidatos de Heather y seleccionar MDL/ANM/texturas por identidad. Buscar
  asociación con estados privados y registrar las diferencias entre archivos
  de jugador, copias de item y trajes. Salida: selección fijada y reporte.
- [x] **HI-T2 — Esqueleto y animaciones.** Definir receta de 73 huesos y
  muestras candidatas de 264 bytes; comprobar todas las muestras, pistas
  ausentes y conservación de bits; añadir fixtures propios y negativos.
  Identificar un segmento inicial utilizable sin inventar límites o frecuencia.
- [x] **HI-T3 — Malla y materiales.** Investigar morphs, referencias de
  submallas, paletas y texturas; validar límites/solapamientos con fixtures;
  convertir y comparar dos salidas privadas, incluidos datos no aplicados.
- [x] **HI-T4 — Pose y dibujo.** Contrastar jerarquía, composición, selección
  de grupos y estado del material en la referencia PS2; acotar las diferencias
  permitidas para una inspección inicial y conservar los resultados fallidos.
- [x] **HI-T5a — Visor y entrega preparada.** Implementar perfil acotado de Heather,
  pruebas host/lectores/renderizador, build ARM y revisión en emulador.
  Preparar entrega privada y protocolo físico de 60 segundos. Mostrar modelo,
  segmento y límites reales en el visor; no anunciar movimiento jugable.
- [x] **HI-T5b — Validación física funcional.** Copiar y releer hashes del paquete en
  SD, comprobar 60 segundos en New 2DS XL, atuendo/texturas/animación,
  A/R/L, cámara, START y tapa/HOME. Registrar métricas y prueba funcional
  por separado; corregir y repetir cualquier fallo antes de aceptar el perfil.

[Ejecución HI-T1–T5a](../../execution/f03-02-heather-inspection.md): modelo
`chhaa.mdl`, máscara `0x3021`, clip `0x65`; 36 huesos activos, 6.943 vértices,
5.522 triángulos y 13 texturas. Build `9719469ff6bb`, 64 segundos en Azahar,
paquete privado verificado. La acreditación de pose es acotada; frecuencia
nativa completa, expresiones, luz PS2 y locomoción permanecen pendientes.
Contrato [SRI1](../../../schemas/rig-inspection-v1.md) y
[protocolo físico](../../compatibility/heather-inspection.md).

Estas tareas no requieren terminar las particularidades de los bancos
dinámicos del carrusel. CF-T9c conserva su estado y evidencia independiente.

## Extensión de cámara HI-T6

Diseño: la cámara transporta su objetivo; la política de distancia mínima se
configura por visor. El valor por defecto mantiene 3 unidades en los visores
anteriores. Heather habilita 0,45 y SELECT aplica un preset de inspección
centrado en la cabeza, sin modificar malla, pose, textura ni SRI. El preset
es fijo para este clip de espera; no equivale a seguimiento facial general.

- [x] **HI-T6a:** implementar zoom y objetivo por cámara; probar límites,
  entradas inválidas, reset, pausa y regreso con SELECT retenido.
- [x] **HI-T6b:** compilar ARM, observar cara/cabello a distancia mínima y
  verificar alternancia, controles y salida en Azahar; publicar nuevo ZIP.
- [x] **HI-T6c:** confirmar encuadre cercano y controles en la 2DS XL.

El primer plano reveló texturas verticalmente invertidas en PICA. La corrección
se aplica al upload del visor SRI, con anclas sintéticas asimétricas; los
recursos RGBA, UV y paquetes SRI originales se conservan byte a byte.
[Resultado HI-T6](../../execution/f03-02-heather-camera.md): build
`f25a2d9bb316`, 88 segundos en Azahar a distancia mínima y paquete privado
v2; HI-T6c e HI-T5b funcional confirmadas por el usuario el 2026-10-24:
60 s, rostro, SELECT/zoom/controles, START y tapa/HOME. Se conserva como
no detallada la reapertura y no se atribuyen dos intervalos de 60 s.
Métricas aproximadas: Skin+sort 60,7 ms, Submit+wait 49 ms, GPU previous
4,36 ms; baja fluidez reportada. [HP](heather-performance.md) aborda el
rendimiento antes de verificar reloj nativo y selección de locomoción.

**Actualización HP-T4, 2026-10-24:** build `8f778b6e4960` confirmado en New
2DS XL durante 60 s en cuerpo y 60 s en cara, mayor fluidez, controles,
START y tapa/HOME. Lectura conjunta: 29,9 FPS submit, New fast y
10,27/23,1/6,34 ms (Skin+sort/Submit+wait/GPU previous). Se retoma el
reloj nativo y la selección de locomoción; reapertura no detallada.
