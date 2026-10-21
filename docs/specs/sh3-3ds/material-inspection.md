# F03.02 — Material y modelo en el visor

Historia: inspeccionar en New 2DS XL las dos formas verificadas por MR-T4d,
con su textura, transformación y transparencia, antes de integrar una escena.

## Requisitos EARS

- **MI01** WHEN prepara la entrega THEN SHALL verificar por SHA-256 geometría,
  textura, referencia de captura y build; rechazar referencias con otra textura,
  forma, matriz inválida o un estado de material no soportado.
- **MI02** WHEN convierte la geometría THEN SHALL aplicar primero el modelo
  afín por columnas y después una transformación de inspección documentada;
  conservar los UV originales sin invertir V, color por vértice y orden de dibujo.
- **MI03** WHEN presenta el material THEN SHALL usar filtrado lineal, clamp,
  mezcla por alpha fuente, sustitución de alpha destino, comparación de
  profundidad sin escritura y cara frontal comprobada.
- **MI04** WHEN inspecciona transparencia THEN SHALL dibujar primero un fondo
  propio opaco y después las formas; SHALL conservar los controles y el ciclo
  de vida del visor anterior, sin I/O ni asignación propia por cuadro.
- **MI05** IF falta o falla el archivo de geometría o textura THEN SHALL mostrar
  el error y permitir START sin adquirir recursos GPU.
- **MI06** WHEN entrega el build THEN SHALL identificarlo, conservar los visores
  anteriores y separar pruebas host/ARM/emulador de la comprobación física.
  CI SHALL compilar y probar con fixtures propios sin incorporar recursos del juego.

## Diseño

Se reutilizan SGM1 y STX1, sus lectores acotados/CRC y el puerto IRenderScene.
El preparador host verifica los manifiestos MG/textura y una referencia privada
de MR-T4d con hash explícito: matriz modelo, colores RGBA por vértice, niebla,
orden de formas y hashes del MAP, textura y volcado GS. No interpreta atributos
empaquetados como iluminación sin evidencia.

El conversor puro aplica modelo → cambio de base `(x,-y,-z)` → centrado de AABB
mundial → escala uniforme → destino `(0,0.75,-2)`. El cambio de base es una
rotación de 180° sobre X, determinante positivo, para observar desde +Z la cara
que PCSX2 observó desde −Z. La cámara orbital es de inspección.

Esta entrega usa iluminación capturada y niebla negra constante F=227:
el color SGM es `RGBv/128 × 227/256`. Solo admite RGBv ≤128, alpha de
vértice 127 y ese estado de niebla. STX convierte alpha PS2 0..128 a
`round(A×255/128)`; el adaptador modula con alpha constante `253/255`,
aproximación de `127/128`. PICA realiza el filtrado y la mezcla. No se promete
reproducir el redondeo STQ, filtrado de 4 bits ni los truncamientos intermedios
del GS. No cambia la niebla/iluminación al mover la cámara; no es un renderer
general de materiales SH3 ni una cámara de juego.

El renderer conserva RAII y copia única de buffers prestados. Un módulo de
estado Citro3D separa fondo opaco de material transparente. El fondo es una
cuadrícula de colores propia, sin textura adicional. La composición carga ambos
archivos antes de construir el renderer. El preparador y el writer privado son
independientes de los lectores/renderer de consola.

## Tareas

- [x] **MI-T1:** conversor, validación de procedencia y paquete privado; probar
  matrices no triviales, UV asimétricos, alpha 0/64/128, orden y rechazos. MI01/02.
- [x] **MI-T2:** composición y estado Citro3D, copia de malla/textura, fondo,
  mezcla, culling y profundidad; probar fallos y ausencia de asignación por
  cuadro con dobles SDK, conservando regresiones. MI03–MI05.
- [x] **MI-T3:** target/script/CI, Release y sanitizadores, build ARM con SDK
  fijado, entrega identificada y protocolo para New 2DS XL. MI06.
- [x] **MI-T4:** comprobar textura sobre ambas formas, fondo visible a través
  del material, orientación, cruceta, X/Y, B, START, tapa y HOME en consola;
  registrar build y diferencias sin declarar equivalencia completa PS2. MI02–MI06.
  El usuario confirma ambos paneles con transparencia, controles, START,
  tapa y HOME el 2026-10-20, tras recibir `764be66e7762`.
  Sin duración, fotografía ni comparación física cuantitativa de orientación.

[Ejecución y entrega](../../execution/f03-02-material-inspection.md).
[Protocolo físico](../../compatibility/material-inspection.md).
