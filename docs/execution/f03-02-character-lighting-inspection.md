# LI-T4 — Iluminación capturada en el visor animado

2026-10-23. Build **`b27d16a1671e`**, aplicación **SH3 captured lighting**.
**LI-T4a–e y LI-T4f.1 completadas**; métricas **LI-T4f.2 sin medir**.
[EARS LII01–LII06 y subtareas](../specs/sh3-3ds/character-lighting-inspection.md).
[Ecuaciones y capturas de referencia LI-T1–T3](f03-02-character-lighting.md).

## Comportamiento y responsabilidades

El caballo conserva las tres texturas, 1.455 vértices, 1.113 triángulos y el
clip `0x1449`. El dominio de iluminación calcula colores a partir de cada
pose deformada. El presentador ordena skinning, iluminación y dibujo; el
lector comprueba el archivo SCL1 y sus dependencias antes de iniciar GPU.
El renderer recibe colores y UV, sin interpretar luces ni punteros PS2.

Se usa el preset de la captura 10, Q12=89362: transformación rígida al espacio
capturado, ambiente, direccionales y foco tipo 0x10. La luz se recalcula al
animar; mover la cámara de inspección no mueve las luces. **SELECT** alterna
con luz neutra conservando pose y cámara. Se ignora durante suspensión y
hasta soltar controles al regresar. START conserva prioridad.

La normal no se normaliza; la posición conserva su W al transformar.
RGB se limita/trunca a 0..128 y divide por 128 antes de MODULATE. Se calcula
RGBA para contrastar la ecuación, pero el vértice GPU transmite RGB y mantiene
la pasada opaca anterior. No se acredita equivalencia del alfa del framebuffer.

SCL1 tiene 872 bytes y enlaza CRC de SCM/SAN/SCT. Valida matriz rígida,
valores finitos, límites y cobertura de los 15 rangos sin cruces. Un archivo
incorrecto no publica datos; un fallo numérico impide enviar el cuadro y
permite salir. No hay asignación ni lectura de archivos por cuadro.
Scratch nuevo máximo: 24 KiB; texturas GPU: 3 MiB; vértices enviados: 120.204
bytes/cuadro. Se omite el sombreado diagnóstico anterior en el camino texturado.

La pantalla separa **Skin CPU**, **Light CPU**, **Submit+wait** y **GPU previous**.
Submit incluye espera: las cifras no se suman para obtener FPS. La reproducción
sigue siendo una previsualización de 25 evaluaciones/s.

## Verificación local

| Comprobación | Evidencia |
|---|---|
| Python relacionado | 197 tests y 56 subtests aprobados; encoder/preparador 96,41 % combinado de líneas/ramas |
| C++ Release y ASan/UBSan | 139 pruebas render + unidad de material aprobadas en cada configuración |
| SCL1 independiente | Archivo válido, 29 corrupciones, tres fallos I/O, 165 vértices sintéticos contra oráculo Python |
| Cuatro capturas PCSX2 | C++ contra 500 muestras VU: error máximo 0,000072449; tolerancia previa 0,002 |
| Clip completo | 24 poses × 1.455 vértices: error máximo 0,000047427; RGB cuantizado exacto en todas las muestras |
| ARM | Nuevo visor y los dos visores anteriores compilan con SDK fijado, sin red y copia solo de código |
| Shader | Gate PICA aprobado: 12 componentes escritos una vez; mismo SHBIN corregido de CT-T5f |
| Preparación A/B | Mismas ocho salidas y metadatos desde ambas extracciones de malla; SCL coincide con el preset contrastado |
| Azahar 2126.2 Vulkan | Dibujo y controles comprobados; observaciones separadas por 115,297 s capturado y 66,603 s neutro sin bloqueo observado |
| Calidad | Ruff, formato, contratos del repositorio y diff sin errores |

El contraste privado usa los estados conservados: no se escribieron datos en
el invitado ni se restauraron estados nuevos. El error C++ incluye redondeo
f32; los 34.920 vértices de la animación se comparan con un oráculo matemático,
no con 24 capturas nuevas de PS2. No se ejecutó CI remoto.

Auditor local: `build/character-lighting/prepare_viewer_reference.py`, SHA-256
`acbb191d93016ca37760d9b24fdd57d68aadb75b2d0ba0fd38d85632df477a41`.
Contraste privado: `f03-02-character-lighting-inspection-v1/cpp-contrast.json`,
SHA-256 `82c71ba1775dabe8da48bd72016cb42464eb9eeaced4e73f065b51aaf04591d9`.
Informes locales: `build/character-lighting/viewer-pytest.xml`,
`viewer-coverage.json`, `host-release.log`, `arm-build.log`, `arm-regression.log`;
JUnit C++ en `build/host-{release,sanitize}/character-lighting*.xml`.

## Prueba en Azahar

En pausa, L mostró Q12=0; SELECT cambió capturada → neutra → capturada
manteniendo Q12 y cámara 0,55 / 0,35 / 3,00. Los píxeles de la pantalla superior
antes y después de regresar al modo capturado son idénticos; el modo neutro
cambió 17.778 píxeles del mismo recorte. R avanzó a 3686. Cruceta y X/Y cambiaron
encuadre en pausa, B restauró 0,35 / 0,35 / 4,00 y A reanudó. SELECT también
funcionó durante reproducción. START regresó a la lista de aplicaciones.

Se mantuvo reproducción entre las observaciones indicadas, con Q12 distinto
en ambos extremos. No es una captura continua de vídeo. Lecturas ilustrativas
del emulador: Skin 4,99 ms, Light 6,39 ms, Submit+wait 18,59 ms y GPU 0,25 ms
en capturado; Light 0,00 ms y Submit+wait 8,26 ms en neutro. **No son mediciones
de la 2DS XL**, ni se derivan FPS de ellas. El usuario confirmó después
tapa/HOME; el coste físico nuevo queda en LI-T4f.2.

Capturas y recibo privado en `f03-02-character-lighting-native-check-v1/`.
SHA-256 de `ui-receipt.json`:
`8dc28dff9b8b640b5daf67ba50cb0832590f32009de3a4710c8ef5af8f91a911`.
La copia al perfil portátil se verificó por hash y conservó 27 archivos
preexistentes. Se retiró la copia temporal propia al perfil estándar antes
de abrir el programa. No se modificó la configuración del emulador ni la SD física.

Entrega posterior, 2026-10-23: a solicitud del usuario se copió este build a
la SD NO NAME, siete archivos / 3.490.852 bytes verificados por lectura
posterior y expulsión segura confirmada. [Registro de entrega y prueba
física](../compatibility/character-lighting-inspection.md).

**Aceptación funcional posterior, LI-T4f.1:** el usuario confirmó el mismo
día 60 segundos en cada modo, caballo iluminado, SELECT, controles, START,
tapa y HOME. Para Skin CPU, Light CPU, Submit+wait y GPU previous respondió
«sin medir»; LI-T4f.2 permanece abierta. No se infieren valores Q12, conservación
exacta de pose/cámara ni casos separados de suspensión en pausa/reproducción.
La atribución del build procede de la entrega verificada, sin nueva imagen.
Recibo privado `physical-user-confirmation.json`, SHA-256
`3868ac89e4cebee30d2bf9a2f2b45e19c3b33f624dc42ac5cc1fe0c1d76aa7bb`.

## Entrega y límites

Directorio privado:
`/Users/germancontreras/sh3-private-data/f03-02-3ds-character-lighting-v1/`.
El ZIP crea `/3ds/sh3_character_lighting_probe/` con siete archivos. No reemplaza
el visor neutro `ced27c955e41`, ya aprobado funcionalmente por el usuario.

| Artefacto | SHA-256 |
|---|---|
| manifest.json | `247e463e55380046527090f433d4dbc5e3512474f50da2d6d8702a235e2dea66` |
| sd-card.zip (3.493.045 bytes) | `6358e845fc5dccb27cc6c788ed13000b1fc18e5a1e5d950ea6c183574dd7f67e` |
| 3DSX (280.352 bytes) | `4d0978d3bc70234b2bf03d5c8335fda048720e4905b39e68be5e673d7c3e8fee` |
| character.scl | `fb22a0084b06cf92346197545966eee256598ccf7b946738fda8cd04de030a56` |
| character_shader.shbin | `9fac3d2deac79aaaff6468870b17bb3999d94b32a55b23c55edfbaf6ff8dce9c` |

El pipeline ejecuta `scripts/build_character_lighting_probe.sh` y publica
solo binarios de código y metadatos. Los recursos, preset y capturas permanecen
fuera del repositorio y de CI.

Continuación: [GC-T4, personaje en mundo](../specs/sh3-3ds/character-world-conventions.md).
Siguen pendientes selección de luces entre escenas, seguimiento de linterna,
sombras, base mundial definitiva y transiciones de daño/muerte. Este visor
no constituye todavía un circuito jugable. CT-T5e.2 conserva por separado
las métricas pendientes del build neutro anterior.
