# CT-T5 — Malla animada con material: EARS, diseño y tareas

Historia: probar las tres texturas verificadas por CT-T4 sobre el caballo
animado en New 2DS XL, manteniendo la entrega anterior y sus controles.

## Requisitos EARS

- **CTI01** WHEN se prepara el paquete SHALL verificar manifiestos, SCM/SAN,
  malla, imágenes y referencia CT-T4 por SHA-256; SHALL conservar los tres
  grupos 0–5, 6–8 y 9–14, UV originales y selector cero. IF una referencia,
  estado GS o identidad difiere SHALL rechazar la entrega.
- **CTI02** WHEN se carga el material SHALL validar versión, tamaño exacto,
  CRC, enlace con el payload SCM, tres rangos contiguos de triángulos y alfa
  PS2 ≤128 antes de iniciar GPU. IF falla SHALL mostrar error y permitir START.
- **CTI03** WHEN dibuja SHALL usar tres texturas 512×512, bilineal, clamp,
  escritura y comparación GEQUAL de profundidad con la proyección existente,
  mezcla ONE/ZERO y prueba alfa desactivada. SHALL conservar W y UV/4096 sin
  invertir V. El modo de inspección SHALL declarar luz neutra y dos caras;
  no SHALL atribuir iluminación dinámica o descarte VU a este resultado.
- **CTI04** WHEN sube texturas SHALL convertir RGBA superior-izquierda a
  ABGR/Morton sin invertir filas y alfa mediante round(255*a/128). WHILE
  reproduce no SHALL asignar memoria ni leer archivos por cuadro. SHALL esperar
  GPU antes de reutilizar buffers y liberar GPU antes de gfx.
- **CTI05** WHILE se usa SHALL conservar A/R/L, cruceta, X/Y, B, START,
  tapa/HOME, reloj y métricas de CM-T5. SHALL mostrar build y material/luz usados.
- **CTI06** WHEN entrega SHALL distinguir pruebas sintéticas, build ARM,
  emulador y estado real de la confirmación física. SHALL mantener carpeta/aplicación
  independientes del visor anterior y generar un manifiesto reproducible.
- **CTI07** WHEN compila los shaders de inspección SHALL comprobar en el
  SHBIN que cada componente de los registros de salida declarados se escribe
  exactamente una vez. IF faltan escrituras, se duplican o el programa usa
  instrucciones fuera del perfil verificable SHALL detener la compilación.

## Diseño

SCM1 y SAN1 permanecen iguales. SCT1 agrega un archivo vinculado al CRC del
payload SCM: cabecera LE de 32 bytes `S3CTv1\0\0`, seis u32 (rangos=3,
ancho=512, texturas=3, CRC SCM, bytes payload, CRC payload). Payload: tres
tuplas u32 `(primer índice, cantidad, textura)` de 12 bytes, seguidas por tres
imágenes RGBA originales de 1.048.576 bytes. Tamaño total 3.145.796 bytes.
Los rangos cubren todos los índices sin huecos, en orden de textura 0,1,2.
CRC protege integridad local; el pipeline verifica identidad con SHA-256.

Dominio: rangos y UV del vértice expandido; skinning y pose existentes.
Adaptador de archivos: carga SCT1 acotada y conversión de textura. Renderer:
tres texturas GPU y tres draws con un buffer dinámico compartido. La entrada
CPU de píxeles se libera después de subir: pico adicional de carga 3 MiB CPU
+ 3 MiB GPU; persistencia de texturas GPU 3 MiB. Vértice GPU: posición4,
color3, UV2, 36 bytes. No se cambia la deformación para incorporar material.

La luz neutra equivale a color de vértice PS2 128 y permite examinar el atlas.
No se copia el color de una pose capturada como solución de iluminación. La
presentación conserva el giro de 180° X y dos caras del visor anterior.
La receta de transparencia no se reutiliza del material de vidrio del MAP.

## Tareas

- [x] **CT-T5a** (CTI01/CTI02): encoder SCT1, preparación privada, lector C++,
  vínculo SCM y oráculo independiente con corrupción y fallos de stdio.
- [x] **CT-T5b** (CTI03–CTI05): UV, materiales GPU, luz neutra, carga/liberación,
  tres draws y controles conservados; pruebas de fallos y sincronización.
- [x] **CT-T5c** (CTI04/CTI06): regresión host Release/sanitizadores, fixtures
  asimétricos, compilación ARM sin red y CI de código sin datos originales.
- [x] **CT-T5d** (CTI03/CTI05/CTI06): inspección Azahar, preparación A/B idéntica,
  protocolo físico y paquete privado listo para SD.
- [x] **CT-T5e.1** (CTI05/CTI06): confirmación funcional del usuario en New
  2DS XL, build `ced27c955e41`, texturas, avance Q12, controles, START,
  tapa/HOME y 60 segundos sin bloqueo, recibida el 2026-10-22.
- [ ] **CT-T5e.2** (CTI05/CTI06): registrar varias lecturas Skin CPU,
  Submit+wait y GPU previous del build corregido durante al menos 60 s.
  No reutilizar los valores del visor anterior ni del build que falló.

Referencias: [material verificado](../../execution/f03-02-character-material-runtime.md),
[visor previo](character-inspection.md), [tareas CT](../../../schemas/ps2-character-materials-v1.md).

Ejecución: [build 3fde5682ed11, pruebas y entrega](../../execution/f03-02-character-material-inspection.md).
CT-T5e falló con v1; la repetición funcional del reemplazo está aprobada.
El registro numérico de rendimiento permanece pendiente.

## Corrección tras prueba física fallida

El usuario reportó ausencia del caballo y bloqueo de la consola con el build
`3fde5682ed11`; fue necesario apagarla. La foto muestra Q12=0, Sample=0,
Skin CPU=16,53 ms, Submit+wait=16,98 ms y GPU previous=0,00 ms. CT-T5e
**falló**; la validación anterior de Azahar no acredita funcionamiento físico.

El SHBIN declara `o2.xyzw` pero escribe únicamente `o2.xy`. Se completará
la escritura como en el shader de escena ya probado. Un verificador del
binario, independiente del SDK simulado, admitirá solo el perfil rectilíneo
MOV/DP4/NOP/END de estos visores y rechazará programas que no pueda analizar.
La prueba de regresión debe rechazar el SHBIN anterior y aceptar el nuevo.
No se alteran las texturas, la malla, la pose ni los estados del material.

- [x] **CT-T5f.1** (CTI07): completar salida UV, comprobar máscaras y escrituras
  del SHBIN, pruebas sintéticas de omisiones/duplicados y gate CMake/CI.
- [x] **CT-T5f.2** (CTI06/CTI07): compilar ARM, demostrar rechazo del binario
  anterior, preparar paquete privado nuevo con hashes y revisar en Azahar.
- [x] **CT-T5e.1, repetición** (CTI05/CTI06): dibujo, continuidad ≥60 s,
  controles, START, tapa y HOME confirmados por el usuario en New 2DS XL.

Resultado: [CT-T5f, build ced27c955e41 y evidencia](../../execution/f03-02-character-material-gpu-fix.md).
