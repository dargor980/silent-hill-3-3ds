# GC-T5 — Visor de colocaciones del personaje

Historia: observar los tres caballos con las posiciones y orientaciones
capturadas, compartiendo una animación de inspección y las texturas verificadas.
Este visor usa colocaciones fijas y luz neutra. No simula IA ni desplazamientos
del carrusel. Definición anterior a la implementación.

## Requisitos EARS

- **GCI01** WHEN prepara el visor SHALL verificar manifiesto, SCM/SAN/SCT,
  informe GC-T4 y estado fuente por SHA-256; SHALL tomar las tres matrices
  del mismo estado 08 verificado y conservar sus identificadores. IF cambia
  una dependencia o la identidad SHALL rechazar la entrega.
- **GCI02** WHEN coloca la malla SHALL aplicar modelo una vez, conservar W,
  aplicar B después y separar origen común, escala y cámara. SHALL usar
  `R*p+(T-origin)*w` para evitar restar dos posiciones grandes por vértice.
  SHALL fijar antes del contraste un error absoluto máximo de 0,001 unidades
  originales respecto de esa operación en doble sobre los mismos vértices
  deformados. Este límite mide colocación; no sustituye el contraste CM/VU
  ni acredita precisión total de pose, skinning, rasterización o pantalla.
- **GCI03** WHEN carga SCW1 SHALL verificar versión, longitud exacta, CRC,
  enlaces de dependencias, tres IDs distintos, rigidez propia y encuadre.
  IF falla lectura, cierre o validación SHALL conservar el destino, evitar
  iniciar GPU y permitir START.
- **GCI04** WHILE reproduce SHALL deformar una vez y colocar tres copias
  sincronizadas sin asignación ni I/O por cuadro, compartiendo tres texturas.
  SHALL esperar la liberación del buffer GPU antes de modificarlo, validar
  las tres mallas antes de enviar y liberar recursos después de esperar GPU.
- **GCI05** WHEN usa A/R/L, cámara, START, tapa o HOME SHALL conservar el
  comportamiento del visor existente; SHALL indicar colocaciones fijas,
  animación sincronizada y luz neutra, y medir Skin CPU, Place CPU,
  Submit+wait y GPU previous por separado.
- **GCI06** WHEN entrega SHALL usar carpeta/build propios, validar Release,
  ASan/UBSan, contrato binario independiente, precisión privada, ARM con gate
  PICA y Azahar; SHALL mantener la aceptación física pendiente hasta la prueba
  del usuario ≥60 s con controles, START, tapa y HOME.

## Diseño y formato

Dominio `character_world`: validación de tres instancias, origen/escala y
colocación de posiciones deformadas. El lector SCW1 solo interpreta bytes y
dependencias. El presentador conserva skinning separado de colocación.
`CharacterRenderer` admitirá 1..3 bloques completos con el mismo material,
un buffer persistente y una sola pasada de frame; sus llamadas existentes
seguirán usando un bloque. Se comparte el shader corregido, sin nueva salida PICA.

**SCW1**, LE, 264 bytes: cabecera de 40 bytes, magic `S3CWv1\0\0`, ocho u32:
perfil=1, instancias=3, CRC SCM, CRC SAN, CRC SCT, contador fuente, bytes=224,
CRC payload. Payload: origen3/escala f32 (16 bytes), tres registros de
ID u32 + matriz16 f32 (204 bytes), reservado u32=0 (4 bytes).
Contador fuente <98304; reproducción propia parte de Q12=0 y conserva el
incremento 3686; no reconstruye el reloj de la sesión original. Los tres
actores del estado fuente comparten Q12=66220.

Rigidez: tolerancia 0,002, determinante próximo a +1, fila afín exacta;
traslaciones/origen ≤1.000.000. Radio del modelo conservador `1.004*1.4/SCM.scale`; el factor 1,004
cubre la tolerancia admitida en la parte lineal de la matriz rígida.
Origen: centro del AABB de las tres esferas transformadas; escala común con
radio de presentación máximo 1,4. La comprobación de encuadre admite 1,401
para cuantización f32. No escala independiente por caballo.

Se contrastará colocación f32 frente a doble sobre posiciones deformadas
idénticas, incluyendo salida de 24 poses y 28 capturas de colocación; se
informará por separado el error heredado CM/VU. El caso incorrecto que suma
primero T grande debe ser detectado por el fixture y la evidencia privada.
Si el límite falla, se revisará el cálculo antes de integrarlo, sin ampliar
la tolerancia. No se exige igualdad bit a bit de matrices trigonométricas.

## Tareas detalladas

- [x] **GC-T5a** (GCI01–GCI03): contrato, política numérica y extracción
  privada fijada; encoder y dominio puros; contraste de precisión antes de GPU.
- [x] **GC-T5b** (GCI03/GCI04): lector transaccional, fallos/corrupción,
  render de tres bloques con texturas compartidas y pruebas de propiedad GPU.
- [x] **GC-T5c** (GCI04/GCI05): presentador, aplicación/carpeta propia,
  controles/ciclo de vida compartidos y métricas; regresiones anteriores.
- [x] **GC-T5d** (GCI01/GCI06): preparador privado reproducible, pipeline
  ARM, gate PICA, hashes, paquete y contraste de todos los vértices del clip.
- [x] **GC-T5e** (GCI05/GCI06): comprobar tres caballos y controles en
  Azahar ≥60 s, START y protocolo físico; sin atribuir rendimiento físico.
- [x] **GC-T5f.1** (GCI06): usuario confirma ≥60 s, tres caballos, animación,
  controles, START y tapa/HOME en New 2DS XL.
- [x] **GC-T5f.2** (GCI05): registrar métricas físicas; separadas de la
  aceptación funcional y de las métricas LI pendientes.

[Ejecución, hashes y límites](../../execution/f03-03-character-world-inspection.md).
Build `abe9a7a35464`; aceptación funcional física confirmada el 2026-10-23.
Métricas GC-T5f.2 aproximadas reportadas por el usuario: Skin 14,25 ms,
Place 26,9 ms, Submit+wait 35,50 ms y GPU previous 2,39 ms. Cámara/zoom no
indicados; no se infiere FPS. [Registro físico](../../compatibility/character-world-inspection.md).
