# GC01–GC06 — Convenciones de geometría estática MAP

F03.03, instancia estática posterior a MG/MR/MI. Requisitos RF02.05 y RF03.01.
RF04.04 se amplía para el perfil animado en
[GC07–GC11](../docs/specs/sh3-3ds/character-world-conventions.md); no se cierra globalmente.
La [captura MR-T4d](../docs/execution/f03-02-map-draw-state.md) demuestra el
recorrido de dos formas. La [prueba MI-T4](../docs/compatibility/material-inspection.md)
confirma su presentación funcional en New 2DS XL.

## Requisitos EARS

- **GC01** WHEN transforma una posición local MAP THEN SHALL multiplicar el
  vector columna homogéneo `(x,y,z,1)` por el modelo afín almacenado por columnas
  exactamente una vez; SHALL conservar las unidades originales en espacio mundo.
- **GC02** WHEN adapta ese espacio al visor THEN SHALL aplicar `(x,-y,-z)`
  después del modelo; SHALL mantener centrado y escala de inspección separados
  de las coordenadas mundiales, sin atribuir metros a las unidades originales.
- **GC03** WHEN prepara UV para el material verificado THEN SHALL usar
  `(U/32768,V/32768)` con palabras i16 originales, incluido el bit de control
  de U; SHALL conservar explícitamente `(U/32768,1-V/32768)` solo para la vista
  histórica OBJ/checker.
- **GC04** IF el modelo no es afín, contiene valores no finitos o excede los
  límites del perfil, o su determinante es ≤1e-8 THEN SHALL rechazarlo.
  WHEN cambia de base THEN SHALL conservar el winding; SHALL NOT reparar una
  reflexión invirtiendo índices sin un contrato propio.
- **GC05** WHEN valida el pipeline THEN SHALL usar un fixture propio asimétrico
  con resultados numéricos independientes que detecten matriz transpuesta,
  modelo repetido, base aplicada antes del modelo, reflexión, winding invertido,
  V invertida y borrado del bit de U; SHALL ejecutar esos casos en CI sin originales.
- **GC06** WHEN informa cobertura THEN SHALL separar geometría estática,
  inspección y animación; SHALL mantener desconocidas las convenciones de
  huesos, pose, raíz animada, tiempos e interpolación hasta tener evidencia.

## Diseño y límites

| Concepto | Contrato de esta instancia |
|---|---|
| Registros MAP | Posiciones y UV i16 LE; atributos empaquetados se conservan opacos |
| Modelo | 16 números por columnas; última fila `(0,0,0,1)`; traslación en 12–14 |
| Producto | `world[r] = Σ model[c*4+r] * local_h[c]`, con `r=0..2` |
| Límites de modelo | Valores finitos, valor absoluto ≤1.000.000; determinante >1e-8 |
| Base del visor MI | `B=diag(1,-1,-1)`, rotación propia con determinante +1 |
| Composición | `local → M → world → B → centrado/escala/destino de inspección` |
| Unidades | Se conservan; relación con metros sin verificar |
| Triángulos | Índices de MG; paridad por posición de vértice, sin reinicio por omisión |
| UV de material | Palabras originales/32768, sin flip; el tiling STX no cambia V |
| Culling | La política de vidrio exige triángulos planos de normal +Z tras adaptación |
| Precisión | Operaciones host en doble; conversión a float32 en SGM; sin emular VU/GS |
| Pose/tiempo | No definidos por este contrato estático |

`tools/pipeline/geometry_transform.py` concentra producto afín, cambio de base
y UV como funciones puras, sin filesystem ni SDK. `material_inspection.py`
mantiene normalización, orden de dibujo, colores y restricciones del material.
El decoder sigue conservando palabras/atributos originales. No se alteran el
formato SGM/STX, los lectores ni el renderer compilado de la entrega física.

El fixture `tests/fixtures/synthetic/geometry-conventions-v1.json` tiene cuatro
puntos no coplanares, longitudes distintas, UV con signo y modelo con giro,
escala no uniforme, cizalla y traslación. Los resultados se fijan a mano a
partir de `world=(11-3y+z, -7+2x+z, 13+4z)`. El volumen firmado y una cara
orientada detectan cambios de orientación que un rectángulo simétrico oculta.
No es un formato de escena ni una receta para convertir todos los MAP.

## Tareas

- [x] **GC-T1:** aislar operaciones puras y validación; integrar en material
  sin cambiar su salida. Probar matrices inválidas y puntos/UV malformados.
  GC01–GC04.
- [x] **GC-T2:** fixture asimétrico con oráculos independientes y controles
  incorrectos; probar triangulación MG → transformación → UV. GC01–GC05.
- [x] **GC-T3:** regresiones, lint/contratos y cobertura; reproducir en memoria
  la entrega privada y cotejar sus hashes con el build físico. Registrar la
  inclusión automática en el job Python existente. GC05/GC06.
- [x] **GC-T4, perfil `0x0209` / `0x1449`:** definir pose, huesos, raíz, tiempos e interpolación con un
  recurso animado identificado y una captura propia. Depende de la instancia
  de esqueleto/animación de F03.02; no bloquea GC-T1–GC-T3. GC06/RF04.04.
  [SA-T1–SA-T4](../docs/execution/f03-02-skeleton-animation.md) ya decodifican
  una pareja MDL/ANM. [SA-T5a/b/c](../docs/execution/f03-02-skeleton-runtime.md)
  verifican su selección inicial, reloj Q12 y pose en espacio modelo con
  NLERP y producto padre/hijo. SA-T5d verifica continuidad y CM-T4 skinning.
  [GC-T4a–c](../docs/execution/f03-03-character-world.md) añaden 84 observaciones
  de instancia, posición4/normal3 y base conjugada, con límites numéricos
  separados del contraste VU. No generalizar a mezclas, movimiento de raíz,
  daño/muerte, giros o escalas no ejercitados.
- [x] **GC-T5:** [a–f completadas](../docs/execution/f03-03-character-world-inspection.md),
  contrato SCW1 y visor `abe9a7a35464`, ARM/Azahar y prueba física funcional
  f.1 aprobados; métricas f.2 aproximadas reportadas por el usuario.
  El cálculo separado en mundo no satisface todavía
  la tolerancia CM de 0,001 frente a VU; no declarar equivalencia del renderer.

[Ejecución](../docs/execution/f03-03-static-geometry.md): 519 pruebas,
100 % de líneas/ramas del módulo nuevo y entrega privada A/B idéntica
al build físico `764be66e7762`.
