# CM-T5 — Visor de malla animada: EARS, diseño y tareas

2026-10-20. Historia: inspeccionar la malla de `0x0209` deformada por el clip
`0x1449` en New 2DS XL antes de incorporar actores al runtime del port.
[CM-T4](../../execution/f03-02-character-runtime.md) verificó dos submallas;
la entrega incluye las 15 de la misma variante decodificada y conserva ese
límite de evidencia. Material propio de inspección; daño/muerte pendientes.

## Requisitos EARS

- **CI01** WHEN se prepara la entrega, el pipeline SHALL verificar manifiestos,
  recursos, referencia CM-T4, referencia de continuidad y build por SHA-256;
  SHALL conservar pesos enteros, helpers almacenados e índices candidatos.
  SHALL escribir datos y derivados únicamente en una carpeta privada nueva.
- **CI02** WHEN se evalúa una pose, el dominio SHALL componer
  `Pose_target × StoredHelper`, mezclar posiciones Q4 y normales Q12 con
  pesos Q12 sin normalizar y conservar W. La transformación de presentación
  SHALL aplicar sus traslaciones multiplicadas por W; el shader SHALL recibir
  las cuatro componentes. Las normales originales no SHALL normalizarse en
  el skinning; el material propio puede normalizarlas solo para sombreado.
- **CI03** WHEN se cargan los archivos, el lector SHALL validar tamaño exacto,
  versión, CRC, finitud, contadores, matrices afines, referencias y pesos antes
  de iniciar GPU. IF falla SHALL mostrar el error y permitir START para salir.
- **CI04** WHILE se reproduce, el visor SHALL reutilizar el reloj y los controles
  A/R/L, cámara, START, tapa y HOME del visor de ejes, incluyendo congelación,
  descarte del tiempo suspendido y espera de soltar controles al regresar.
- **CI05** WHEN se actualiza la malla, el adaptador SHALL esperar GPU antes de
  reutilizar su buffer y vaciar caché antes del dibujo. No SHALL asignar memoria
  ni leer archivos por cuadro. SHALL liberar recursos GPU antes de gfx.
- **CI06** El visor SHALL mostrar build, contador, recuentos, tiempo CPU de
  deformación, envío incluyendo espera y tiempo GPU anterior, identificando
  el material como inspección y sin confundir espera con coste puro de subida.
  La entrega SHALL distinguir métricas de emulador y hardware; el protocolo
  físico SHALL registrar al menos 60 segundos de reproducción y controles.
- **CI07** WHEN se publica el resultado, SHALL separar validación sintética,
  contraste privado, compilación ARM, emulador y prueba física pendiente.
  No SHALL atribuir texturas, iluminación PS2, mundo, daño o muerte al éxito.

## Diseño

Dominio puro `character_skinning`: modelo acotado, paletas, posiciones4 y
normales3; buffers prestados. El puerto `IPoseScene` desacopla `AnimationProbe`
de la representación de huesos. Un adaptador de ejes conserva el visor previo;
el nuevo adaptador combina skinning puro con un renderer de posiciones4.
La composición raíz/hijo y el reloj siguen siendo los de AI02–AI04.

SCM1: cabecera LE de 32 bytes, magic `S3CMv1\0\0`, seis u32: vértices,
índices, helpers=3, stride=28, bytes de payload y CRC32. Payload: centro3/escala
f32 (16 bytes), tres destinos de helper u32 (12), tres matrices de 16 f32
(192), vértices y finalmente índices u16. Vértice: posición3 i16, normal3 i16,
UV2 i16, pesos3 u16, hueso primario u8, cantidad u8, helpers2 u8 y reservado
u16=0. Influencias no usadas: peso=0/helper=255. Límite 2048 vértices y 4608
índices, múltiplo de tres; hasta tres influencias y tres huesos.

El clip permanece en SAN1. El encuadre usa una esfera conservadora válida
para cualquier rotación interpolada del clip, no solo sus keyframes; centra/escala uniformemente y rota 180 grados
sobre X para presentar Y hacia arriba (determinante +1). También aplica esa
rotación a la normal de sombreado y suma el objetivo de cámara multiplicado
por W. La primera inspección en Azahar motivó esta conversión; la deformación
modelo y sus normales se conservan antes de ella. Esto es inspección local, no la base mundial final del port. Se preserva
el orden de índices y se usa dibujo de dos caras para inspección; no se
atribuye a Citro3D el descarte por orientación visto en CM-T4. El sombreado
direccional propio permite ver volumen sin reclamar equivalencia de material.

## Tareas detalladas

- [x] **CM-T5a — paquete y lectura** (CI01/CI03): conversor SCM1, identidad
  cruzada con SAN/CM-T4, límites, CRC, errores de lectura/cierre, wire oracle
  independiente y dos preparaciones idénticas desde los recursos A/B.
- [x] **CM-T5b — deformación y presentación** (CI02/CI04): núcleo C++ y puerto
  de pose, regresión de ejes, casos analíticos asimétricos y contraste privado
  de todos los vértices en extremos/fracciones/cierre, conservando W y normales.
- [x] **CM-T5c — GPU y presupuesto** (CI05/CI06): shader float4, buffer
  sincronizado, fallos por etapa, ausencia de asignaciones por cuadro,
  métricas CPU/GPU y recuentos de memoria/transferencia/draw calls.
- [x] **CM-T5d — build y entrega** (CI07): target, script, CI de código sin
  originales, Release/sanitizadores, SDK fijado sin red, Azahar (dibujo,
  animación y controles), paquete privado y protocolo físico.
- [ ] **CM-T5e — prueba física** (CI04/CI06/CI07): usuario confirma build,
  malla/movimiento, A/R/L, cámara/zoom/reset, START, tapa/HOME y métricas durante
  60 segundos. Este punto solo se cierra con evidencia de New 2DS XL.
  - [x] **CM-T5e.1 — aceptación funcional**: usuario confirma caballo animado,
    A/R/L, cámara, START, tapa y HOME en la consola; vínculo al build entregado.
  - [ ] **CM-T5e.2 — registro complementario**: duración de 60 s, tiempos
    CPU/GPU, identificador mostrado y detalles de controles/pausa. No bloquea
    investigación estructural de materiales; no atribuir métricas no medidas.
    Lecturas físicas recibidas: Skin CPU ≈14 ms, Submit+wait ≈12 ms, GPU anterior
    1,1 ms. Duración, distribución y demás detalles sin confirmar.

Evidencia de CM-T5a–d: [ejecución y entrega](../../execution/f03-02-character-inspection.md),
build `757b48fd1746`. [Protocolo físico CM-T5e](../../compatibility/character-inspection.md).
La confirmación funcional se añade al protocolo sin reemplazar sus registros
históricos. Las métricas de emulador no cierran CI06 en hardware; CI07 conserva
expresamente esa separación.
