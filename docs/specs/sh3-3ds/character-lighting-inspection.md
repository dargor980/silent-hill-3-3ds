# LI-T4 — Preset de iluminación para el visor animado

Historia: inspeccionar el caballo animado con las ecuaciones verificadas en
LI-T1–T3 y alternar con luz neutra para comparar en New 2DS XL.

## Requisitos EARS

- **LII01** WHEN prepara la entrega SHALL comprobar SHA-256 de manifiestos,
  SCM/SAN/SCT, malla, preset y referencia LI aprobada; SHALL conservar recursos
  y UV y derivar los 15 rangos y coeficientes de las cabeceras verificadas.
  IF cambia identidad, captura, rango o perfil SHALL rechazar la entrega.
- **LII02** WHEN carga SCL1 SHALL comprobar versión, tamaño exacto, CRC y
  enlaces con los tres payloads antes de crear GPU. SHALL rechazar valores
  no finitos, matrices no rígidas, rangos cruzados y perfiles desconocidos.
  IF falla SHALL conservar el destino y permitir salir con START.
- **LII03** WHILE anima SHALL recalcular iluminación desde posición y normal
  deformadas, sin normalizar la normal, y aplicar clamp/truncamiento RGB PS2
  antes de dividir por 128. SHALL preservar el W deficiente al transformar
  posiciones. No SHALL hornear colores de una pose ni iluminar en las
  coordenadas centradas/escaladas de presentación.
- **LII04** WHEN mueve la cámara de inspección SHALL conservar las luces del
  preset en el espacio capturado. WHEN pulsa SELECT activo SHALL alternar
  preset/neutra sin reiniciar pose ni cámara. WHILE está suspendido o esperando
  soltar controles no SHALL alternar. SHALL conservar A/R/L, cámara, START y
  tapa/HOME; SHALL indicar preset fijo, dos caras y sus límites.
- **LII05** WHILE dibuja no SHALL asignar memoria ni leer archivos por cuadro.
  SHALL calcular una vez por vértice y expandir según índices. SHALL mostrar
  tiempos separados de skinning, iluminación, envío/espera y GPU anterior.
  Un fallo numérico SHALL impedir enviar el cuadro y producir salida recuperable.
- **LII06** WHEN entrega SHALL usar aplicación/carpeta propias y conservar
  los visores anteriores; SHALL validar host Release y sanitizadores,
  contraste independiente, ARM con gate PICA, Azahar y luego consola ≥60 s.
  No SHALL declarar cerrada la prueba física por resultados del emulador.

## Diseño

Dominio `character_lighting`: ecuación pura, perfil acotado, validación y
expansión de colores. Skinning mantiene su responsabilidad y entrega posiciones
y normales crudas. Adaptador SCL1: lectura acotada y comprobación de vínculos.
Presentador de personaje: orden skinning → iluminación → renderer, con tiempo
de cada etapa. El renderer recibe el mismo vértice posición4/color3/UV2 y usa
el shader PICA ya corregido; no interpreta luces ni datos PS2.

Se fija la transformación rígida modelo → espacio de la captura y las luces
de la salida 10, Q12=89362, como **preset de inspección**. Las poses continúan
animándose con SAN1. La cámara orbitante y la rotación/escala de presentación
no entran en la iluminación. La prueba host contrastará también los otros
tres pares con sus propios parámetros, sin presentarlos como selección de
luces entre habitaciones. El preset no implementa seguimiento de linterna.

Color CPU: ambiente + difuso*(direccionales + foco tipo 0x10), con los clamps
verificados. RGB final se trunca a 0..128 y divide por 128 para MODULATE.
El alfa calculado se conserva para contrastar la ecuación, pero el vértice
GPU existente transmite RGB; la presentación opaca mantiene su alfa anterior.
No se declara equivalencia del canal alfa del framebuffer PS2.

El cálculo guarda RGB por vértice (máximo 2048 × 12 = 24 KiB) y expande
3339 índices en el recurso actual. Sin nuevas texturas ni shaders. Distancia
cero al foco es un caso no verificado y falla de forma recuperable.

## SCL1

Archivo LE de **872 bytes**, magic `S3CLv1\0\0`. Cabecera 48 bytes: magic y
10 u32: perfil=1 (modo2/foco0x10), rangos=15, direccionales=3, CRC SCM,
CRC SAN, CRC SCT, vértices, índices, bytes payload=824 y CRC payload.
Payload: u32 Q12 de referencia; matriz de 16 f32 por columnas; ambiente4;
tres pares dirección3/color4; foco posición3/dirección3/color4/atenuación4;
15 rangos de 40 bytes `(primer_v, cantidad_v, primer_i, cantidad_i,
difuso3, ambiente3)`. Los rangos cubren ambos buffers sin huecos, y cada
índice solo referencia vértices de su rango. Las W de material son 1 implícitas.

Límites del perfil: matriz rígida con tolerancia 0,002, traslación ≤100000;
direcciones ≤16; colores de luces y ambiente RGB 0..16, alfa ambiente 0..255;
material RGB 0..128; atenuación absoluta ≤1000000; Q12 <98304. Son límites
del formato de inspección, no una afirmación sobre todos los recursos PS2.

## Tareas

- [x] **LI-T4a** (LII01–LII06): EARS, espacio de coordenadas, responsabilidades,
  SCL1, criterios de fallo y plan de pruebas definidos antes de implementar.
- [x] **LI-T4b** (LII01/LII02): encoder/preparador privado y lector C++;
  probar corrupción, CRC cruzado, límites, EOF, lectura/cierre y no publicación.
- [x] **LI-T4c** (LII03–LII05): iluminación CPU, presentador y SELECT;
  fixtures asimétricos, W deficiente, material por submalla, singulares,
  invariancia de cámara y suspensión, contraste C++/oráculo/capturas.
- [x] **LI-T4d** (LII05/LII06): Release/sanitizadores, pipeline ARM, gate
  PICA, recursos A/B idénticos, hashes y paquete privado independiente.
- [x] **LI-T4e** (LII04/LII06): Azahar, dibujo texturado, alternancia SELECT,
  A/R/L y cámara, continuidad ≥60 s y START; protocolo físico preparado.
- [ ] **LI-T4f** (LII04–LII06): aceptación funcional y registro de rendimiento.
  - [x] **LI-T4f.1**: usuario confirma el 2026-10-23 ≥60 s en cada modo,
    caballo iluminado, SELECT, controles y START/tapa/HOME. Es evidencia
    declarada por el usuario, sin nueva captura ni comprobación de valores Q12.
  - [ ] **LI-T4f.2**: registrar Skin CPU, Light CPU, Submit+wait y GPU previous
    por modo. Respuesta del usuario: «sin medir»; no bloquea GC-T4.

[Implementación, build b27d16a1671e y evidencia local](../../execution/f03-02-character-lighting-inspection.md).
La aceptación física del preset sigue separada de la del visor neutro anterior.
