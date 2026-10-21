# F03.02 — Inspección privada de geometría en 3DS

Historia: presentar el grupo MAP decodificado por MG01–MG07 en la GPU destino,
para comprobar topología, UV y controles con un material de diagnóstico propio.
Esta entrega no acredita transformación, material ni escena PS2.

## Requisitos EARS

- **GI01** WHEN inicia el visor THEN SHALL leer únicamente
  `sdmc:/3ds/sh3_geometry_probe/geometry.sgm`, validar formato, longitud, CRC,
  límites numéricos y triángulos antes de adquirir recursos GPU.
- **GI02** IF falta el archivo, hay corrupción, datos no finitos, triángulos
  degenerados o falla I/O THEN SHALL mostrar el error y permitir salir con START.
- **GI03** WHEN recibe geometría válida THEN SHALL dibujar los triángulos
  conservando el orden y UV del decoder, con checker propio y colores por forma.
  SHALL indicar que la transformación es de inspección y el material sintético.
- **GI04** WHILE dibuja THEN SHALL reutilizar VBO/textura sin I/O ni asignaciones
  propias por frame y conservar controles, suspensión y salida de SR02–SR05.
- **GI05** WHEN prepara el paquete THEN SHALL verificar manifiesto MG y archivos
  por SHA-256, reconstruir los registros y contrastar la topología, normalizar
  uniformemente el grupo y escribir una entrega privada exclusiva y repetible.
- **GI06** WHEN ejecuta CI THEN SHALL probar con geometría sintética y publicar
  únicamente código compilado. SHALL conservar los otros visores independientes.
- **GI07** WHEN informa resultados THEN SHALL separar host, ARM, emulador y
  consola física, manteniendo pendiente la fidelidad PS2.

## Diseño y contrato SGM1

Formato transitorio propio, no SH3P. Cabecera de 24 bytes: magic de ocho bytes
`S3GMv1\0\0`; count u32 LE; stride u32 LE = 32; bytes u32 LE = count × 32;
CRC32 IEEE del payload u32 LE. Count múltiplo de 3 entre 3 y 3072. Sigue
exactamente el payload, sin trailer. Cada vértice: ocho float32 IEEE754 LE
`x,y,z,u,v,r,g,b`. Posiciones absolutas ≤4; UV absolutas ≤2; colores 0..1;
todos finitos. Ningún triángulo puede tener producto vectorial nulo.

Host comprueba el JSON contra su manifiesto y contra la decodificación de sus
registros reconstruidos. Por cada grupo centra la AABB y multiplica por
`4 / max(extensiones)`, después traslada a `(0,0.75,-2)`. No rota ni refleja ejes.
No modifica UV ni aplica matrices o iluminación del juego. Expande índices
en triángulos; colores alternos cian/naranja por ordinal de forma, checker propio.
El informe conserva centro/escala y rangos de vértices por forma.

El lector usa StdioApi, reserva del llamador de 96 KiB y conversión LE explícita.
Publica count solo tras validar y cerrar. La vista prestada de vértices se copia
una vez a memoria lineal GPU; el llamador libera su buffer. SceneRenderer añade
una entrada de malla sin alterar el puerto IRenderScene. Aplicación, cámara,
hooks APT y destrucción RAII se reutilizan. Codificador, lector, renderer y
writer privado tienen responsabilidades independientes.

## Tareas

- [x] **GI-T1:** implementar contrato SGM, validación numérica y lector acotado;
  probar corrupción, límites, I/O, degeneración y oráculo Python → C++. GI01/02.
- [x] **GI-T2:** constructor de malla prestada, composición y target separados;
  probar copia, fallos GPU, liberación, controles y regresiones. GI03/04/06.
- [x] **GI-T3:** verificar procedencia MG, normalizar, empaquetar SD, script
  reproducible y artefactos CI sin originales; probar rechazo y repetibilidad.
  GI05/06.
- [x] **GI-T4:** compilar Release/sanitizadores y ARM, inspeccionar muestra
  privada en emulador y preparar entrega identificada. GI01–GI07.
- [x] **GI-T5:** probar en New 2DS XL las formas visibles, cruceta, X/Y, B,
  START, tapa y HOME; registrar build y observaciones. GI07.
  Usuario confirma «funciona todo, se ven formas rectangulares» para
  `a039c31cb262` el 2026-10-20. Sin métricas ni duración física registradas.

Evidencia: [ejecución](../../execution/f03-02-geometry-inspection.md) y
[prueba física](../../compatibility/geometry-inspection.md).
