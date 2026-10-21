# Prueba física del corte 3D sintético

Estado: **validación física parcial**, comunicada por el usuario el 2026-10-20:
arranque, cámara con cruceta y botones X/Y, B y START funcionan en su New Nintendo
2DS XL. El ensayo local en Azahar está
registrado en el [informe de ejecución](../execution/f05-01-synthetic-render.md).
No es una habitación de Silent Hill 3.

## Preparación y arranque

1. Usar el `.3dsx` y `.smdh` del mismo build. La identidad de entrega está en el
   informe; contrastar `SHA256SUMS` antes de copiar.
2. Con la consola apagada, copiar ambos archivos a
   `/3ds/sh3_render_probe/` de la SD. No necesita ISO, BIOS, texturas externas,
   `probe.txt` ni cambios de configuración de la consola.
3. Expulsar la SD de forma segura, volver a colocarla y abrir **SH3 synthetic 3D**
   desde Homebrew Launcher. Esta entrega no genera CIA para FBI.
4. Registrar modelo, versión de Homebrew Launcher, ID mostrado, hora y resultado.

## Recorrido de comprobación

| Acción | Resultado esperado |
|---|---|
| Arranque | Suelo gris, paredes azul/turquesa/verde y cubo amarillo con cuadros; marcador rojo en la textura |
| Observar oclusión | El suelo y la pared del fondo no pintan encima del cubo |
| Cruceta izquierda/derecha | Órbita acotada, sin que una pared oculte el centro del cubo |
| Cruceta arriba/abajo | Elevación acotada; escena estable |
| X / Y | Acercar / alejar con límites |
| B | Cámara `0.35 0.35 7.00` |
| Cerrar/abrir tapa y regresar de HOME | Recuperar imagen; soltar botones antes de mover; sin salto acumulado de cámara |
| START, también tras regresar | Volver al launcher sin bloqueo |

Mantener cinco minutos alternando controles y dos ciclos de tapa/HOME como
comprobación inicial. Esto no sustituye el ensayo de treinta minutos de G01 ni
un benchmark representativo de G05. Si HOME no permite retorno en ese launcher,
registrar el comportamiento observado en vez de marcarlo aprobado.

## Registro — 2026-10-20

Fuente: confirmación del usuario en el chat, sin captura ni medición directa
por el agente. Primero informó: «funciona en la 2ds, con las flechas puedo mover
la camara». Al consultar X/Y, B, START y regreso de tapa/HOME, respondió:
«si, funcionan todos los botones».

- Modelo: New Nintendo 2DS XL, identificado previamente por el usuario.
- Launcher / versión: Homebrew Launcher previsto para esta entrega; versión y
  ruta efectivamente usada no indicadas en este ensayo.
- Build de referencia: `9cc454db81bf`, entregado inmediatamente antes del ensayo;
  asociación por contexto de conversación, sin cotejo explícito del ID mostrado
  o del SHA-256 en la consola.
- Arranque: funciona, confirmado por el usuario. Textura, marcador rojo y
  oclusión: inspección detallada pendiente.
- Cámara con cruceta, zoom X/Y y restablecimiento B: funcionamiento confirmado
  por el usuario; límites y valores numéricos no cotejados explícitamente.
- START / retorno: funcionamiento confirmado en respuesta a la consulta sobre
  volver al launcher.
- Tapa / HOME / liberación de botones: la respuesta confirma los botones;
  no describe los ciclos de suspensión, recuperación de imagen ni ausencia de
  salto de cámara. Ese recorrido sigue pendiente.
- Duración y fallos: duración no indicada; el usuario no comunicó fallos.

SR-T5 permanece abierta hasta completar el recorrido y la identificación.
Esta evidencia corresponde al corte gráfico; no cierra la validación del
diagnóstico F01 ni acredita treinta minutos de estabilidad o rendimiento G05.

Ante `Render probe failed`, registrar etapa e ID y salir con START. No presentar
un reinicio forzado como salida correcta. El texto de pantalla
`Physical 2DS XL: NOT VERIFIED` refleja el estado al generar la entrega.
Se conserva ese build para mantener su identidad; la confirmación física
posterior y sus límites se registran aquí.
