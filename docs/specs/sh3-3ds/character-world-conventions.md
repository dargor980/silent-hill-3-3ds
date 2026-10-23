# GC-T4 — Convenciones del personaje en espacio mundo

Instancia acotada: actor `0x0209`, clip `0x1449`, edición europea verificada.
Continúa SA/CM/CT/LI sin modificar los visores ya aceptados. No cierra F03.03
global ni el contrato de escena SH3P. Definido antes de implementar.

## Requisitos EARS

- **GC07** WHEN transforma un vértice deformado SHALL aplicar la matriz de
  instancia por columnas exactamente una vez al vector homogéneo de cuatro
  componentes, conservando W y las unidades originales; SHALL transformar
  la normal solo por las tres columnas lineales, sin normalizarla.
- **GC08** WHEN adapta a la base de inspección SHALL aplicar
  `B=diag(1,-1,-1,1)` después del modelo. IF expresa también el modelo en esa
  base SHALL usar `B*M*B^-1`; SHALL conservar W, winding y separar centrado,
  escala, cámara y la sustitución W=Z del consumidor VU.
- **GC09** IF recibe una matriz no rígida, reflejada, no afín, no finita o
  fuera del perfil SHALL rechazarla antes de publicar un resultado. El
  perfil SHALL admitir traslación absoluta ≤1.000.000 y error ortonormal
  ≤0,002; no afirma soporte de escala de instancia ni de todos los actores.
- **GC10** WHEN contrasta el contrato SHALL verificar identidad y hashes de
  las capturas conservadas, instancias, recursos y ventanas de código; SHALL
  distinguir lectura de estados archivados de una sesión nueva en PCSX2.
  SHALL documentar por separado el error numérico del nuevo orden de cálculo
  y el de las matrices preparadas por PS2, sin ampliar tolerancias anteriores.
- **GC11** WHEN ejecuta CI SHALL comprobar fixtures propios asimétricos con
  W deficiente, normal no unitaria y traslación; SHALL detectar transposición,
  doble modelo, orden incorrecto, W forzado y normalización indebida, sin ISO
  ni capturas privadas. SHALL mantener pendientes daño/muerte, mezclas,
  movimiento de raíz no observado y selección de luces entre escenas.

## Diseño

`tools/pipeline/character_space.py` será una operación pura e inmutable para
matrices rígidas y vectores homogéneos. No lee recursos, no interpreta actores,
no deforma huesos y no depende de `tools.qa`. El auditor privado conecta los
estados PCSX2 y el oráculo independiente de skinning con este contrato.
No se reutiliza `MapAffine.transform_point`, que introduce W=1 explícitamente.

El resultado es `p_world=M*blend(P_i*H_i*p)` y
`n_world=M3*blend((P_i*H_i)3*n)`. El helper de la influencia primaria es la
identidad. La matriz de mundo se lee de la instancia; la reconstrucción desde
campos de actor se investigará por separado, sin deducir Euler general de
capturas donde solo varía yaw. Una equivalencia algebraica en doble no implica
igualdad bit a bit con el redondeo EE/VU ni con un renderer 3DS.

## Tareas y aceptación

- [x] **GC-T4a** (GC07/GC10): localizar construcción/consumo de la matriz de
  instancia; verificar tres actores en los 28 estados continuos conservados,
  offsets, escala, posición y giro observados, identidad y límites de inferencia.
- [x] **GC-T4b** (GC07–GC09/GC11): implementar operación pura de posición4,
  normal3 y base conjugada; pruebas asimétricas, corrupción, desbordamiento,
  inmutabilidad, orientación y controles negativos en el job Python existente.
- [x] **GC-T4c** (GC10/GC11): contrastar cuatro pares CM conservados y los
  500 vértices VU disponibles; medir por separado cálculo en mundo y paleta
  preparada, registrar controles negativos y consolidar SA/CM/GC.
- [x] **GC-T5 — visor del perfil observado**: [a–f completadas](../../execution/f03-03-character-world-inspection.md),
  contrato propio y visor `abe9a7a35464` con tres colocaciones fijas;
  entrega a SD y aceptación funcional f.1 verificadas; métricas f.2 aproximadas
  reportadas: Skin 14,25, Place 26,9, Submit+wait 35,50 y GPU 2,39 ms.
  No reutilizar el preset fijo de luz como si fuera iluminación de escena.
  Antes de integrarlo, fijar el presupuesto numérico del renderer en unidades
  originales: el cálculo separado en mundo no satisface el umbral CM de 0,001
  frente a VU (máximo 0,009027917 en las muestras). No ampliar ese umbral ni
  declarar equivalencia EE/VU por los resultados del nuevo módulo.

La aceptación funcional LI-T4f.1 permite avanzar; sus tiempos LI-T4f.2 están
«sin medir» y permanecen pendientes de forma independiente.

[Ejecución y límites numéricos](../../execution/f03-03-character-world.md):
84 observaciones de instancia, 500 muestras VU, 246 pruebas y 56 subtests.
GC-T4 cierra la definición del perfil observado; GC-T5 implementa su
[contrato de visor](character-world-inspection.md) con aceptación física funcional y métricas reportadas.
No generalizar este cierre a F03.03 global.
