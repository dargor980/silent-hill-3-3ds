# HM-T4c.3.3 — materiales originales de hp34

Extiende HRS/HRR sin modificar contactos, SRI2, cámara ni controles. La evidencia
de asignación es HRB v4, SHA-256
`5ebe66786a34543c058451b7e9637b0e528ed50b3a07109c850cde1078ac5073`.

- **HRM01**: al preparar A/B, el conversor debe autenticar HRS y HRB; reconstruir
  nueve imágenes RGBA8 512×512 de las siete texturas originales y las paletas
  seleccionadas; cotejar sus hashes antes de normalizar alfa PS2 0..128 a 0..255.
  Las imágenes no cambian de orientación. GPU: RGBA8, bilineal, repetición U/V.
- **HRM02**: el conversor debe conservar posiciones, UV, triangulación y orden de
  las 31 formas; debe omitir los offsets 149504, 222736 y 245648 como en HRB.
  Las 26 formas internas enviadas conservan su orden, incluida la mezcla alfa.
  Las dos formas de vidrio conservan el tratamiento anterior junto con el pelo.
- **HRM03**: modo 0 reemplaza color, sin prueba alfa; modo 3 prueba alfa >0;
  modo 1 mezcla SrcAlpha/OneMinusSrcAlpha. Los tres escriben profundidad GEQUAL,
  sin descarte de caras. Alfa de vértice: 0/127/127 PS2, convertido a 0/253/253.
  Cada transición debe fijar explícitamente el estado, sin herencia accidental.
- **HRM04**: RGB y niebla negra se fijan a la captura GS autenticada, por vértice
  de origen, comprobando cobertura, solapamientos y estado de cada paquete.
  Se almacena RGB/128 × fog/256. Es iluminación fija de inspección: interpolar
  este producto aproxima la combinación GS; no promete equivalencia por píxel,
  iluminación dinámica PS2 ni visibilidad de otros estados de juego.
- **HRM05**: el lector debe rechazar longitudes, CRC, índices, estados y rangos
  inválidos antes de publicar; error o cierre fallido conserva la escena previa.
  Cada textura debe validarse antes de publicar y antes de subirla a GPU.
- **HRM06**: el presupuesto incluye nueve MiB adicionales, todos los recursos
  simultáneos y la reserva de reemplazo. Límites: texturas 32 MiB, total 64 MiB;
  ninguna reserva de heap por frame. Validar host, fallos, ARM y A/B antes del ZIP.

## SRM2

Little endian. Cabecera 32 bytes: magic `S3RMv2\0\0`, u32 número de formas,
número de vértices, bytes de payload, CRC32 payload, CRC32 vidrio, versión 2.
Payload: `formas × 24` bytes (u32 offset, first, count, glass, material, visible),
exactamente nueve registros de material de 16 bytes (u32 width, height, CRC32,
RoomPass: 4 opaco, 5 recorte, 6 mezcla), luego vértices de 36 bytes
`local_xyzw_rgb_uv_f32`. Material 0 y visible 1 para vidrio. Visibilidad 0/1.
Cada material tiene 512×512 píxeles en `room-texture-00.rgba`..`08.rgba`.
SRM1 sigue admitido como perfil diagnóstico anterior. SRR1 mantiene su estructura
y autentica el nuevo SRM2 con su CRC. El paquete no incluye fuentes privadas.
