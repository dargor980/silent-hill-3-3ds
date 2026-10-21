# Visor del clip 0x1449 — EARS, diseño y tareas

2026-10-20. Alcance autorizado: reproducir el clip cuya selección y vuelta
continua están [verificadas](../../execution/f03-02-animation-continuity.md).
Se representan tres huesos mediante ejes y un enlace propios. La malla del
caballo, skinning, colocación mundial y equivalencia visual PS2 quedan pendientes.

## Requisitos EARS

- **AI01** WHEN se prepara una entrega, el preparador SHALL verificar SHA-256
  del manifiesto, esqueleto, animación, referencia de continuidad y build;
  SHALL exportar únicamente las muestras 0–23 de `0x1449`, jerarquía
  `[-1,-1,1]`, traslaciones constantes y cuaterniones unitarios.
- **AI02** WHEN se evalúa un contador Q12, el dominio SHALL usar su muestra y
  fracción entrantes, nlerp de arco corto y composición padre × local por
  columnas; la muestra siguiente a 23 SHALL ser 0. El avance SHALL ser 3686
  (`(2457−614)×2`), módulo `24×4096`.
- **AI03** WHILE reproduce, el visor SHALL avanzar con un reloj de inspección
  de 25 evaluaciones/s independiente del refresco. SHALL identificar esa tasa
  como una elección de preview, sin atribuirla a una cadencia PS2 medida.
  WHEN A se pulsa SHALL alternar pausa; WHEN R se pulsa en pausa SHALL avanzar
  una evaluación; WHEN L se pulsa SHALL reiniciar contador y reloj.
- **AI04** WHILE está suspendido o espera soltar controles, el visor SHALL
  congelar el contador y descartar el tiempo de reanudación; START SHALL salir.
  Cruceta, X/Y y B SHALL conservar las funciones de cámara existentes.
- **AI05** WHEN se carga `animation.san`, el lector SHALL comprobar tamaño
  exacto, perfil, CRC, jerarquía, valores finitos y límites antes de crear GPU.
  WHEN falla SHALL mostrar un error y permitir salir mediante START.
- **AI06** WHEN actualiza geometría dinámica, el adaptador SHALL esperar la
  sincronización GPU antes de escribir y vaciar caché antes de dibujar,
  sin I/O ni asignaciones propias por cuadro. SHALL liberar GPU antes de gfx.
- **AI07** La entrega y CI SHALL distinguir código, datos privados, pruebas
  host/ARM/emulador/consola. Las transiciones `0x144A` (daño) y `0x144B`
  (muerte) SHALL permanecer pendientes y no SHALL simularse como verificadas.

## Diseño

Dominio puro `animation_pose`: clip acotado, nlerp, matrices y representación
propia. Aplicación `AnimationProbe`: reloj, controles y ciclo de vida mediante
composición con `RenderProbe`. Puerto dinámico separado; `SceneRenderer`
conserva sus modos estáticos y sincroniza la sustitución del mismo buffer.
Lector SAN1 con seam stdio existente; preparador privado independiente del SDK.
La referencia de continuidad se vincula por hash, sin reescribir el informe.

SAN1: cabecera LE de 32 bytes: magic `S3ANv1\0\0`, seis u32
(`3`, `24`, `0x1449`, `3686`, `1216`, CRC32 del payload).
Payload: tres padres i32, centro XYZ y escala f32 (16 bytes), tres
traslaciones XYZ f32 (36 bytes), 24×3 cuaterniones XYZW f32 (1152 bytes).
Total 1248 bytes. Perfil deliberadamente acotado al caso verificado.
La traslación del hijo procede de la inversa rígida del padre en reposo;
las de raíces proceden de ANM. No se incluyen los otros 52 cuadros.

La inspección conserva XYZ, centra y escala uniformemente; no aplica la base
del visor estático ni afirma orientación mundial. Ejes locales rojo X, verde Y,
azul Z y enlace gris entre 1 y 2. No se conecta la raíz 0 a la raíz 1.
El encuadre es fijo durante el clip; los ejes son geometría diagnóstica propia.
Se descarta dt no finito/negativo y se limita cada paso a 100 ms para evitar
saltos y recuperación ilimitada tras interrupciones. El primer paso tras
resume no consume tiempo. La pausa manual se conserva al volver de HOME/tapa.

## Tareas y evidencias

- [x] **AI-T1:** conversor y lector SAN1; identidades, límites y controles negativos. AI01/AI05.
- [x] **AI-T2:** dominio C++ y oráculo Python independiente: extremos, fracción,
  cierre 23→0, signo opuesto, jerarquía y comparación del clip privado. AI02.
- [x] **AI-T3:** reloj/pausa/paso/reinicio, suspensión y subida GPU sincronizada;
  pruebas de fallos y ausencia de asignaciones por cuadro. AI03/AI04/AI06.
- [x] **AI-T4:** target/script/CI, build ARM con SDK fijado, paquete privado y
  protocolo físico; registrar por separado cualquier comprobación de emulador. AI07.
- [x] **AI-T5:** prueba física en New 2DS XL: el usuario confirma el 2026-10-20
  ejes animados, A/R/L, cámara, START, tapa y HOME.
  [Alcance de la confirmación](../../compatibility/animation-inspection.md).

Resultados y hashes: [ejecución AI-T1–AI-T5](../../execution/f03-02-animation-inspection.md).

Pendientes de investigación: [SC-T3b/SC-T3c](../../../schemas/ps2-animation-continuity-v1.md),
incluidas las transiciones de daño y muerte. La integración del bucle verificado
no cambia el resultado negativo acotado de la investigación de colisión.
