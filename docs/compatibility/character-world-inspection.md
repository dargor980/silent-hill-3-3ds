# GC-T5f — Prueba física del visor de colocaciones

**GC-T5f.1 aceptada por el usuario; GC-T5f.2 completada con lecturas aproximadas.**
Build **`abe9a7a35464`**, aplicación **SH3 world placement**.
[Implementación y validación local](../execution/f03-03-character-world-inspection.md).

Paquete privado:
`/Users/germancontreras/sh3-private-data/f03-03-3ds-character-world-v1/sd-card.zip`.
SHA-256 `35c5565945ae6008d247ca99b6c0820b592c24cfc79ebc9ae2f1830dba360615`.
Extraer en raíz SD para crear `/3ds/sh3_character_world_probe/`. No sustituir
carpetas anteriores. Copiado y verificado el 2026-10-23; SD expulsada de
forma segura a las 16:27 (America/Santiago).

## GC-T5f.1 — Aceptación funcional

1. Abrir **SH3 world placement** en Homebrew Launcher y comprobar el build.
2. Confirmar tres caballos texturados, separados y con orientaciones distintas.
   El encuadre incluye a los tres; pueden verse pequeños. X acerca e Y aleja.
   Las colocaciones son fijas y comparten animación; no se espera que recorran
   el carrusel ni que respondan a ataques.
3. Mantener reproducción al menos **60 segundos**: Q12 debe avanzar y el visor
   debe seguir respondiendo, sin bloqueo, desaparición ni corrupción visible.
4. A pausa/reanuda. En pausa, L lleva Q12 a 0 y R avanza una evaluación.
   Cruceta gira la cámara; X/Y cambia distancia; B restablece el encuadre.
5. Cerrar/abrir tapa y salir/regresar con HOME. Comprobar recuperación del
   dibujo y controles, idealmente tanto en reproducción como en pausa.
   Indicar por separado cualquier caso no probado.
6. START debe regresar a Homebrew Launcher. Registrar el resultado observado.

## GC-T5f.2 — Métricas físicas

Durante reproducción, después de al menos 60 segundos, anotar valores
aproximados o rangos de **Skin CPU**, **Place CPU**, **Submit+wait** y
**GPU previous**. Indicar cámara/zoom y si hubo pausas o suspensión.
Submit incluye espera; no sumar esos valores para inferir FPS.
Se admite «sin medir» manteniendo abierta esta subtarea.

| Evidencia física | Estado |
|---|---|
| Entrega a SD y hashes leídos de vuelta | Aprobada; expulsión segura confirmada |
| Tres caballos, texturas y animación ≥60 s | Aprobada por reporte del usuario |
| A/R/L, cruceta, X/Y y B | Controles reportados como funcionales |
| START, tapa y HOME | Aprobada por reporte del usuario |
| Skin / Place / Submit+wait / GPU | 14,25 / 26,9 / 35,50 / 2,39 ms, aproximados |

Azahar pasó dibujo, continuidad observada durante 70,553 s, controles y
START. No sustituye esta prueba ni las métricas físicas. Las aceptaciones
anteriores CT-T5 y LI-T4 corresponden a otros builds y se conservan separadas.

## Registro de entrega — 2026-10-23

Siete archivos, **3.490.287 bytes**, en `/3ds/sh3_character_world_probe/`.
SHA-256 de cada archivo leído de vuelta igual al manifiesto fijado. Se
conservaron por hash **56 archivos** preexistentes de los visores SH3.
Volumen UUID `2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`, dispositivo de esta
sesión `disk12s1`; `diskutil` confirmó la expulsión de `disk12`.
En esta entrega no se modificaron los binarios; la aceptación física posterior
se registra debajo.

Comprobantes privados en `f03-03-character-world-native-check-v1/`:

| Comprobante | SHA-256 |
|---|---|
| sd-copy.json | `33c09181bb1dec9320b19ee0c0761f45b066ad2826f3106c32dc6751c8de3e7f` |
| sd-eject.json | `f41517d4160fcf334155ec628ef5dfac9496337c9386a7f95a4ae7484b48ff27` |

## Aceptación funcional — 2026-10-23

El usuario confirmó 60 segundos en New 2DS XL, tres caballos texturados y
animados, controles, START, tapa y HOME. GC-T5f.1 queda aceptada para el build
entregado `abe9a7a35464`. No se infieren valores Q12 exactos ni casos separados
de suspensión en pausa/reproducción. No hay nueva imagen; la atribución del
build se apoya en la entrega verificada. Las métricas se comunicaron después,
en un comprobante separado que conserva el registro inicial.

Comprobante privado `physical-user-confirmation.json`, SHA-256
`7b4fbdbf8fc0dcfc253439662c9631636cc616b15e66cf36f4316cd60be1cef9`.

## Métricas reportadas — 2026-10-23

| Lectura del usuario | Tiempo aproximado |
|---|---|
| Skin CPU | 14,25 ms |
| Place CPU | 26,9 ms |
| Submit+wait | 35,50 ms |
| GPU previous | 2,39 ms |

**GC-T5f.2 completada.** Son lecturas recordadas del ensayo de 60 segundos,
sin captura ni serie temporal; cámara/zoom y momento respecto de pausa o
suspensión no fueron indicados. Submit incluye espera: estos valores no se
suman para calcular FPS ni acreditan un presupuesto de rendimiento de juego.
Place CPU merece una medición reproducible antes de optimizar. Las métricas
CT-T5e.2 y LI-T4f.2 corresponden a otros builds y siguen pendientes.

Comprobante privado `physical-performance.json`, SHA-256
`8fc49b85c9b98d7f95d8518f3da1c074a49fa611ad6d7f027c749a40baa426ff`.
