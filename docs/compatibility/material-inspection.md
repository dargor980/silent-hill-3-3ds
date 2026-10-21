# Prueba física — SH3 material inspection

Preparado el 2026-10-20 para New 2DS XL con Homebrew Launcher.
Build **`764be66e7762`**, aplicación `sh3_material_probe.3dsx`.
Estado: **aprobada por confirmación del usuario el 2026-10-20**.
La [ejecución](../execution/f03-02-material-inspection.md) conserva por separado
las comprobaciones host, ARM y Azahar.

Copiado el 2026-10-20 a la SD física «NO NAME», en
`/3ds/sh3_material_probe/`, con `.3dsx`, `.smdh`, `geometry.sgm`,
`texture.stx` y `LEEME.txt`. Tamaños y SHA-256 de los cinco archivos
verificados tras la escritura; visores anteriores conservados.
El usuario confirma tras probar la entrega:

> Lo probé en la 2DS XL: se ven ambos paneles con transparencia y funcionan los controles, START, tapa y HOME.

| Comprobación en New 2DS XL | Estado |
|---|---|
| Build de la entrega probada: `764be66e7762` | Identificado por entrega y copia verificada; sin transcripción de pantalla |
| Ambos paneles visibles con transparencia | Confirmado por el usuario |
| Cruceta, X/Y y B | Incluidos en «funcionan los controles» |
| START vuelve al launcher | Confirmado |
| Cerrar/abrir tapa y HOME | Confirmado |
| Duración y métricas de rendimiento | No informadas |
| Comparación de orientación, costuras y píxeles con PS2 | Sin medición física específica |

Se cierra MI-T4 como prueba funcional del visor. No se recibieron fotografías
ni duración; no se infiere equivalencia visual cuantitativa o estabilidad prolongada.
Para repetir: expulsar la SD de forma segura, abrir **SH3 material inspection**
desde Homebrew Launcher y comprobar build, aspecto, controles y ciclo de vida.

Los cuadros grandes son el fondo de prueba, no el material de los paneles.
La perspectiva y escala son de inspección. Luz y niebla corresponden a la
captura de referencia y no cambian al mover la cámara. La precisión de PICA
no acredita equivalencia de píxeles con el GS.
