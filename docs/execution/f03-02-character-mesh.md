# F03.02 — Malla de 0x0209 y vínculos de huesos

2026-10-20. **CM-T1–CM-T3 completadas**. Tras la confirmación física de
[AI-T5](../compatibility/animation-inspection.md), se decodificó la malla MDL
seleccionada y se contrastaron sus componentes con el recurso de la ISO.
Este informe registra la extracción estructural. La comprobación posterior
[CM-T4 en PCSX2](f03-02-character-runtime.md) verifica una muestra representativa
de skinning; su integración en el visor (CM-T5) sigue pendiente.
[EARS, diseño y tareas](../../schemas/ps2-character-mesh-v1.md).

## Resultado estructural

| Elemento | Resultado |
|---|---:|
| Huesos / raíces | 3 / 2 |
| Helpers | 3: pares 0→1, 0→2 y 1→2 |
| Submallas | 15, todas en la partición sin blend del archivo |
| Grupos de vértices | 44 |
| Vértices, sin deduplicar | 1.455 |
| Triángulos candidatos | 1.113 |
| Comandos de tira | 1.712 |
| Comandos con supresión | 599 |
| Triángulos descartados por índices repetidos | 0 |
| Vértices con 1 / 2 / 3 influencias | 1.216 / 215 / 24 |
| Referencias de textura | 0, 1 y 2; imágenes/materiales aún sin decodificar |

Hay 1.242 vértices con suma de pesos 4096, 189 con suma 4095 y 24 con suma 4094.
El primer intento de exigir suma exacta 4096 rechazó el recurso. La inspección
de los enteros confirmó déficits de una unidad con dos influencias y dos con
tres. CM04 conserva esos valores y limita el déficit a `influencias−1`, sin
renormalizar. La extracción por sí sola no prueba cómo el juego utiliza ese
déficit. CM-T4 confirmó después pesos sin normalización y preservación de la
componente homogénea en la muestra de ejecución de su informe independiente.

El orden de triángulos procede de las direcciones y marcas de la tira. Esta
extracción no acredita orientación frontal, normales correctas en mundo,
ausencia de área cero ni equivalencia GS. CM-T4 contrasta después dos submallas
con salidas VU y paquetes GS. La partición del MDL no acredita por sí sola un
estado de transparencia en ejecución.

## Implementación y separación de responsabilidades

- `ps2_character_vif.py`: loader puro de NOP/STCYCLE y UNPACK sin máscara
  V4-32/V4-16/V3-16/V2-16; RAM de 1024 quadwords, salto de destinos,
  extensión de signo y rechazo de lecturas no escritas. No ejecuta VU.
- `ps2_character_mesh.py`: tablas, matrices auxiliares, paletas, grupos,
  componentes enteros, vínculos y topología. Conserva cabeceras sin interpretar
  campos desconocidos. Rechaza morphs, referencias inválidas y solapamientos.
- `read_pair_payloads`: adquisición reutilizable del par ya seleccionado;
  valida ISO, contenedor completo, descriptor MFA y hash de ambos recursos.
  El decoder previo de esqueleto/animación usa el mismo puerto de lectura.
- `decode_character_mesh.py`: coordina la conversión y el reporte de capacidades
  pendientes. Publica `mesh.json` solo después del cierre y comprobación de ISO,
  mediante el writer privado exclusivo ya existente; no sobrescribe entregas.

No se modificaron el código C++ ni el build `a1629eeace22` probado por el usuario.
No se generó otra entrega para SD en esta tarea.

## Validación

- **87 pruebas nuevas** de malla/VIF/adquisición y salida privada. Fixture propio
  con raíces independientes, mezcla de huesos, posiciones asimétricas, ambos
  bancos VU, ambas particiones, suma de pesos incompleta y matrices con −0.
  Incluye malformed/truncados, tamaño, máscara/comandos no soportados, signed/
  unsigned, NUM=0→256, saltos, memoria ausente, rangos y paletas, tira y pesos.
- **77 regresiones de esqueleto/animación** aprobadas después de extraer el lector
  compartido. La ejecución final añade las 23 pruebas de supervisión: **187/187**.
- Batería general inicial: **4.284 aprobadas y seis fallidas** por la restricción
  del sandbox a `/bin/ps`; se conservó ese JUnit. Las seis pasaron al repetir
  todo `test_supervised_process.py` con acceso a procesos habilitado. Cuatro
  casos de malla se añadieron después de esa batería y están en las 187 finales.
  El fixture final usa triángulos no colineales y sus 87 casos se repitieron:
  87/87. La unión de resultados más recientes por caso deja **4.294 casos
  aprobados entre ejecuciones**, sin presentarlos como una única corrida.
- Cobertura final agregada: **98,31 % líneas / 96,59 % ramas**, gate 80/80 aprobado.
  Ambos decoders puros nuevos: **100 % líneas y ramas**. El coordinador nuevo
  conserva sin cubrir únicamente su entrada `__main__` en pytest; el CLI sí
  se ejecutó en las dos adquisiciones reales.
- Ruff y contratos del repositorio aprobados. Las pruebas entran en el job
  Python de CI existente por descubrimiento; no se afirma ejecución remota.
  No corresponde recompilar ARM/C++ al no cambiar esos componentes.

La auditoría independiente local no importa los decoders MDL/VIF: relee el
descriptor MFA, carga cada componente escalar de los paquetes y lo compara
con el JSON. Contrasta **330 comandos VIF, 13.358 componentes de vértice,
1.712 comandos de tira, cabeceras, vínculos y matrices auxiliares**. Cuatro
controles negativos detectan cambios en posición, peso, orden de triángulo y
matriz auxiliar. Esto acredita fidelidad de extracción; no acredita skinning.

## Procedencia y reproducción

Raíz privada: `/Users/germancontreras/sh3-private-data/`.
Dos lecturas independientes desde ISO: `f03-02-character-mesh-{a,b}-v1/`.
`mesh.json` y `manifest.json` son idénticos byte a byte entre ambas.

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| MDL fuente | 833712 | `120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672` |
| mesh.json privado | 725598 | `f9f4cd9b635c6d776b7dd479dce1f2696363a272a48dfa43b8dd2e01db34f8f7` |
| Manifiesto privado A/B | — | `2a360854c7becb493a4b84a4ff25811ab20f4b97d196d870ff0b2e573df2703f` |
| Auditoría local | — | `7b055256a603046f7d9ce09851837c1972b2cc62b72d8acc1d9d0da0b03b2a78` |

Selección conservada: `reports/local/f03-02-skeleton-selection-v1.json`, SHA-256
`bc81ec9fb2191c5cb434db886e0a6bf1d3c080329d53315e482292257cc264e8`.
Auditoría: `reports/local/f03-02-character-mesh-audit-v1.json`.
Reporte de ejecución y fuentes: `reports/local/f03-02-character-mesh-execution-v1.json`,
SHA-256 `3ae341345a447b06feda70f5ce7d9322cb769fa27f650dfb7b21ce99a2efda1f`.
Auditor local: `build/character-mesh/audit_mesh.py`, SHA-256
`0cf5c403f9e0cd52163122e0a89aa0082ab92c4fac72e640866513caf07e846b`.
JUnit y cobertura: `build/character-mesh/pytest-{full,final}.xml` y
`coverage-{full,final}.json`; el fallo por sandbox se preserva.

Referencia primaria consultada: Murugo/Misc-Game-Research, commit fijado
`c088e878544f25d45ea7cf4215613fb5f9638dd4`, licencia MIT, sin ejecutar el plugin.
[Código MDL/VIF](https://github.com/Murugo/Misc-Game-Research/tree/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3).
`import_mdl.py` SHA-256 `66191680f7bc46602ab7dd4d2f7f912b3a01c95742681d1ddce026b6e9c70963`;
`vu.py` SHA-256 `f27cfef1e1e893c6e955a73bf54f006cc401f21492927a8912d6b1e7c2648273`.
El lector propio usa el bit 14 de USN observado en los paquetes, conserva
componentes ausentes como desconocidos y rechaza variantes fuera del contrato;
no depende de los valores predeterminados del plugin de referencia.

Reproducción del pipeline: `python -m tools.pipeline.decode_character_mesh --help`.
Requiere la selección y su hash, la ISO y un identificador nuevo de salida
privada. Los datos del juego y derivados no forman parte de fixtures ni CI.

## Seguimiento: CM-T4 completada; siguiente CM-T5

[CM-T4](f03-02-character-runtime.md) enlaza matrices y helpers con 500 muestras
de vértices en cuatro poses, rutas de 1/2/3 influencias y orden de 38 paquetes GS.
La muestra contiene 125 vértices de dos submallas; no se generaliza su validación
a las otras 13. Incluye normales, déficit de pesos, componente homogénea y
controles negativos con errores cuantificados.

CM-T5 debe integrar la malla animada, medir costes y validar la conversión de
base del visor antes del nuevo build y prueba física. Las texturas/materiales
del MDL siguen pendientes de verificación independiente, al igual que daño
`0x144A`, muerte `0x144B`, SC-T3b/c y F03.02/G02/G03 globales.
