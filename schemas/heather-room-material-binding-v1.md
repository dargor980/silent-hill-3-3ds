# HRB01–HRB06 — Materiales originales de hp34

HM-T4c.3.2. Verificación host, sin cambiar el renderer ni el build de consola.

- **HRB01** WHEN se audita evidencia privada THEN el auditor SHALL anclar el
  inventario A/B, estados, volcado GS y ventanas del consumidor europeo por
  SHA-256, releer las fuentes antes de publicar y producir solo metadatos.
- **HRB02** WHEN verifica una asignación THEN SHALL seguir contexto → banco →
  gestor → cabecera original y mesh.selector → referencia TEX0. SHALL comprobar
  cada descriptor y todos los rangos de vértices de sus cadenas DMA, incluso
  las cadenas preparadas pero omitidas. No basta el orden del inventario.
- **HRB03** WHEN verifica consumo GS THEN SHALL asociar la geometría mediante
  XYZ y STQ, sin usar el material para elegir la forma; exigir una coincidencia
  única por paquete y rechazar contradicciones. El límite XYZ es dos unidades
  fijas GS (1/8 píxel), UV 1/4 de una unidad fuente Q15, fijados antes del cotejo.
- **HRB04** WHEN valida texturas consumidas THEN SHALL comprobar los bytes de
  las transferencias de índices/CLUT y su vigencia en el momento del dibujo,
  incluyendo reutilización de direcciones. SHALL registrar TEX0/TEX1/CLAMP,
  PRIM/TEST/ALPHA/ZBUF y color/niebla efectivos, conservando alfa PS2.
- **HRB05** WHEN informa cobertura THEN SHALL distinguir asignación preparada,
  envío GS, omisión DMA y resultado de píxeles. SHALL conservar visibilidad y
  orden originales; un estado omitido no se presenta como visible ni como
  material desconocido. No acredita una partida normal ni fidelidad 3DS.
- **HRB06** IF falta evidencia o hay límites, ciclos, referencias, transferencias
  o estados contradictorios THEN SHALL rechazar la aceptación completa.
  Ejecuciones normal y `-O` SHALL producir informes idénticos. Los fixtures
  públicos SHALL ser inventados y comprobar fallos, no incluir bytes del juego.

La lectura es específica del subperfil europeo observado. No es un emulador
DMA/VIF/GS general. La integración y el presupuesto final pertenecen a
HM-T4c.3.3; HM-T5 permanece aplazado.
