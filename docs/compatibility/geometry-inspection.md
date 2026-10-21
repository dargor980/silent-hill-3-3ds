# Prueba física del visor de geometría

Estado: **aprobada por confirmación del usuario el 2026-10-20**.
New Nintendo 2DS XL, Homebrew Launcher, build `a039c31cb262`.
[Spec GI](../specs/sh3-3ds/geometry-inspection.md) y
[ejecución y hashes](../execution/f03-02-geometry-inspection.md).

El usuario recibió la carpeta `/3ds/sh3_geometry_probe/` en la raíz de la SD
NO NAME. Ante la consulta sobre formas naranja/cian con cuadros, cruceta,
X/Y, B, START, tapa y HOME respondió:

> lo probe y funciona todo, se ven formas rectangulares

| Comprobación solicitada | Evidencia |
|---|---|
| Arranque y formas visibles | Confirmación; describe formas rectangulares |
| Cruceta: órbita y elevación | Incluida en «funciona todo» |
| X/Y: acercar/alejar | Incluida en «funciona todo» |
| B: restablecer cámara | Incluida en «funciona todo» |
| START: salida al launcher | Incluida en «funciona todo» |
| Cerrar/abrir tapa y HOME | Incluida en «funciona todo» |

No se recibieron duración, métricas de rendimiento ni fotografía de esta
ejecución. No se infiere una identidad semántica para las formas. El material
es diagnóstico propio; transformación y material PS2 siguen sin acreditar.
Este resultado cierra GI-T5, sin cerrar los gates de escena o port jugable.

Para repetir: verificar build y hashes, cargar desde Homebrew Launcher,
comprobar la tabla y anotar duración/anomalías. Si aparece error, registrar
código y build antes de salir con START.
