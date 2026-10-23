# LI — Iluminación del personaje europeo, perfil de investigación v1

## Historia y alcance

Tras la aprobación física funcional de CT-T5e.1 (`ced27c955e41`), identificar
cómo el juego ilumina la malla `0x0209`, clip `0x1449`. El visor conserva luz
neutra hasta contar con ecuaciones contrastadas. Esta fase usa capturas
inmutables de CM-T4/CT-T4; no necesita cargar estados ni alterar el juego.
No cubre selección de luces de todas las escenas, sombras, reflexión,
transiciones de daño/muerte ni la transformación mundial definitiva.

## Requisitos EARS

- **LI01** WHEN se audita una captura SHALL comprobar SHA-256 del estado,
  malla, ELF y microprograma, actor, pose y PC; SHALL conservar el vínculo
  entrada/salida y distinguir los parámetros previos de los preparados por
  la llamada de dibujo. IF una identidad difiere SHALL rechazar la auditoría.
- **LI02** WHEN se identifica iluminación SHALL enlazar modo de submalla,
  llamadas EE, bloques VIF y entradas VU con la salida de color. SHALL
  separar rutas observadas de ramas presentes solo en el ejecutable.
- **LI03** WHEN se calculan colores SHALL usar un oráculo matemático puro
  independiente del renderer, con normales deformadas, posiciones y luces
  explícitas; SHALL declarar precisión, orden, saturación y cuantización.
  IF un perfil no está verificado SHALL rechazarlo o declararlo pendiente.
- **LI04** WHEN se valida una ecuación SHALL comparar al menos cuatro poses
  y separar color VU previo a saturación de color consumido por GS. SHALL
  fijar tolerancias antes de la aceptación y exigir controles negativos
  sensibles a luces, materiales y normalización; no SHALL ajustar tolerancias
  para ocultar errores de atribución o de fórmula.
- **LI05** WHEN se documenta SHALL conservar datos originales fuera del
  repositorio, incluir pruebas sintéticas en CI y distinguir resultados
  estáticos, capturas, emulador y consola. La luz neutra aprobada SHALL seguir
  identificada como tal hasta la entrega y validación de otro build.

## Diseño y límites de responsabilidad

El adaptador de investigación lee y verifica capturas privadas. El oráculo
QA recibe únicamente vectores y coeficientes, no archivos, direcciones de RAM
ni objetos GPU. La aplicación de luces al visor, su paquete y su contrato
de archivo se diseñarán después de la verificación numérica. El dominio de
skinning no seleccionará luces ni leerá estados GS; el renderer no resolverá
punteros PS2. Esto mantiene separadas deformación, iluminación, adquisición
y presentación conforme a SOLID.

## Tareas detalladas

- [x] **LI-T1 — ruta y procedencia** (LI01/LI02/LI05): verificar los cuatro
  pares conservados, identificar modo de las 15 submallas, contadores/tipos
  de luces, buffers preparados y entradas VU; documentar ramas no ejercidas
  y publicar un informe de metadatos reproducible sin recursos originales.
- [x] **LI-T2 — ecuaciones y oráculo** (LI03/LI04): reconstruir la ruta
  observada, implementar cálculo puro con rechazo de entradas inválidas y
  fixtures asimétricos; probar atenuación, normales no unitarias, canales
  independientes, alfa, saturación y truncamiento. El perfil inicial no es
  un emulador de coma flotante PS2.
- [x] **LI-T3 — contraste VU/GS** (LI01/LI04/LI05): contrastar cuatro poses
  de las submallas retenidas y los paquetes GS atribuibles de CT-T4;
  publicar máximos de error y controles negativos, dejando visibles fallos
  y restricciones. Tolerancia fijada antes del contraste: color VU absoluto
  0,002 unidades PS2; canales GS enteros exactos. Se obtuvo coincidencia
  exacta sin introducir excepciones por fronteras de truncamiento.
- [ ] **LI-T4 — contrato de visor** (LI03/LI05): solo después del contraste,
  fijar EARS, espacio de coordenadas y formato versionado de luces; preparar
  integración CPU/GPU, pruebas de carga y suspensión, build ARM con gate
  PICA, Azahar y prueba física ≥60 s con métricas. No cerrar con luz horneada
  de una única pose ni declarar selección dinámica de escena sin verificarla.

CT-T5e.2 permanece abierto para las métricas del visor neutro aprobado.

Resultado: [LI-T1–T3, procedencia y ecuaciones](../docs/execution/f03-02-character-lighting.md).
Oráculo puro con 17 tests/56 subtests, cobertura de líneas y ramas 100 %;
210 tests relacionados aprobados. Error VU máximo 0,000061603 unidades;
1.712/1.712 colores GS exactos en 428 paquetes. LI-T1–T3 no cambian el renderer.

Integración posterior [LI-T4 / SCL1](../docs/specs/sh3-3ds/character-lighting-inspection.md):
build `b27d16a1671e`, preset recalculado por pose y SELECT capturada/neutra.
[Evidencia y entrega](../docs/execution/f03-02-character-lighting-inspection.md).
LI-T4f.1 aceptada por el usuario el 2026-10-23: 60 s por modo, iluminación,
SELECT, controles y START/tapa/HOME. LI-T4 permanece abierta por las métricas
LI-T4f.2, respondidas «sin medir»; no bloquean GC-T4.
