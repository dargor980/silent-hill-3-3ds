# F03.02 — Inspección privada de textura en 3DS

Historia: como desarrollador necesito presentar la muestra decodificada en la
GPU de destino para comprobar transferencia, orientación y controles. Instancia
preparatoria de RF02.05/RF03.02, posterior a PX01–PX07. No identifica el material
original ni sustituye su comparación en PS2; G02/G03/G05 permanecen abiertos.

## Requisitos EARS

- **TI01** WHEN se inicia `sh3_texture_probe` THEN el visor SHALL leer una sola
  textura de `sdmc:/3ds/sh3_texture_probe/texture.stx`, verificar cabecera, tamaño
  exacto y CRC32 antes de mostrarla.
- **TI02** IF falta el archivo, está truncado, tiene bytes adicionales, versión,
  dimensiones, formato o CRC incorrectos, o falla lectura/cierre THEN el visor
  SHALL mostrar un error y permitir salir con START, sin sustituir la imagen.
- **TI03** WHEN la textura es válida THEN el visor SHALL mostrar sus colores RGB
  sobre un panel blanco propio, con nearest, UV completas y sin mezcla alpha.
  SHALL indicar que es inspección opaca, sin fidelidad de material acreditada.
- **TI04** WHILE dibuja THEN SHALL reutilizar textura/VBO sin I/O ni asignaciones
  propias por frame, respetando suspensión, liberación de controles y salida de
  SR02–SR05.
- **TI05** WHEN se prepara una entrega privada THEN el pipeline SHALL verificar
  el manifiesto de decodificación por SHA-256, la paleta elegida explícitamente
  y el build; normalizar alpha mediante `min(255,2*A_PS2)`; producir archivos
  exclusivos fuera del checkout con hashes y ZIP listo para SD.
- **TI06** WHEN CI compila o prueba THEN SHALL usar únicamente datos sintéticos
  y producir el ejecutable sin textura del juego. La demo sintética SHALL
  conservar su ejecutable independiente.
- **TI07** WHEN se registra evidencia THEN SHALL separar host, ARM, emulador,
  consola y fidelidad al material original.

## Contrato de inspección STX1

Formato propio transitorio, **no SH3P ni formato del juego**. Cabecera de 24 bytes:
magic de 8 bytes `S3TXv1\0\0`; ancho y alto u16 LE, ambos 256; formato u32 LE = 1
(RGBA8 normalizada); longitud u32 LE = 262144; CRC32 IEEE del payload u32 LE
(compatible con zlib). Sigue exactamente ese payload, sin padding/trailer.
Tamaño total 262168 bytes. Filas de arriba abajo, columnas de izquierda a derecha.
CRC detecta corrupción accidental; el manifiesto SHA-256 conserva procedencia.

El adaptador transforma una vez RGBA lineal en ABGR/Morton 8×8 de PICA.
Conserva las filas al transferir: el patrón asimétrico en Azahar verifica la
primera fila canónica en el borde superior (V=1) del panel. Un primer ensayo con
inversión de filas quedó invertido verticalmente y se corrigió.
El panel usa seis vértices, color blanco y UV 0..1, centrado en el objetivo
de la cámara existente. Estas convenciones son del visor, no del juego.
El alpha normalizado viaja en la textura; esta inspección lo muestra opaco y no
acredita ecuaciones de mezcla, alpha test o paleta de un material PS2.

## Diseño y validación

El lector stdio acotado usa la interfaz de I/O sustituible existente; no incorpora
SDK ni asignación oculta. El llamador reserva un buffer temporal de 256 KiB.
La transformación de píxeles es pura. El renderer recibe una vista prestada,
valida antes de adquirir recursos y copia a su textura propia. El buffer temporal
se libera tras inicializar. La aplicación y el puerto de presentación se reutilizan.
La composición selecciona el visor al compilar un target separado.

El empaquetador host verifica procedencia y crea STX/ZIP; el writer privado común
conserva escritura exclusiva y manifiesto al final. CI no llama al empaquetador
con originales. Tests: formato y fallos de I/O, patrón asimétrico con oráculo
Morton inverso, lector C++ alimentado por encoder Python, RAII con dobles SDK,
regresión de escena sintética, Release/sanitizadores y build ARM fijado.

## Tareas

- [x] **TI-T1:** lector STX y transferencia pura; probar cabecera, CRC, límites,
  lectura/cierre, orientación y canales. TI01–TI03.
- [x] **TI-T2:** panel y target separado; probar adquisición/liberación,
  presentación, ausencia de trabajo por frame y regresión sintética. TI03/04/06.
- [x] **TI-T3:** empaquetador privado verificable, script y artefactos CI;
  probar integridad, repetibilidad y negativa ante salida existente. TI05/06.
- [x] **TI-T4:** compilar ARM, contrastar imagen asimétrica y muestra privada en
  emulador, preparar ZIP e informe con límites explícitos. TI01–TI07.
- [x] **TI-T5:** usuario prueba ZIP identificado en New 2DS XL: textura visible,
  cruceta, X/Y, B, START y suspensión. Conservar comparación PS2 pendiente. TI07.
  Confirmada por el usuario el 2026-10-20 para el build `a6a45e73a03d`, tras
  corregir la ubicación del paquete en SD; tapa y HOME incluidos.

Evidencia: [ejecución local](../../execution/f03-02-texture-inspection.md) y
[protocolo físico](../../compatibility/texture-inspection.md).
