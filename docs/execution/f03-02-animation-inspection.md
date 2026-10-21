# F03.02 — Clip 0x1449 integrado en el visor

2026-10-20. **AI-T1–AI-T5 completadas**, build **`a1629eeace22`**.
El visor reproduce las 24 muestras del clip verificado mediante tres juegos
de ejes y un enlace propios. Funciona en Azahar; el usuario confirma la
[prueba física en New 2DS XL](../compatibility/animation-inspection.md):
ejes animados, A/R/L, cámara, START, tapa y HOME. [Requisitos EARS, diseño y tareas](../specs/sh3-3ds/animation-inspection.md).

**Daño `0x144A` y muerte `0x144B` permanecen pendientes.** No se exportan sus
muestras ni se simulan sus transiciones. Continúan abiertas SC-T3b/SC-T3c;
la [investigación de colisión](f03-02-carousel-alternative-routes.md) conserva
su evidencia negativa acotada. La malla del caballo, pesos/skinning, colocación
mundial y equivalencia visual PS2/3DS tampoco están implementados.

## Implementación

- `animation_inspection.py`: conversión pura acotada al perfil de tres huesos,
  dos raíces y 24 muestras; offset del hijo mediante inversa rígida en reposo.
- `prepare_animation_probe.py`: identidades de fuente, continuidad y build;
  entrega privada reproducible y reporte con pendientes explícitos.
- `inspection_animation.cpp`: lector SAN1 de 1248 bytes, CRC32, límites y
  rechazo de datos parciales o errores de lectura/cierre antes de GPU.
- `animation_pose.cpp`: cuaterniones, nlerp de arco corto, matrices columna y
  composición padre × local; geometría diagnóstica de 40 triángulos.
- `AnimationProbe`: reloj y controles; compone `RenderProbe` para cámara y
  ciclo de vida. `IDynamicScene` separa la subida dinámica del contrato estático.
- `SceneRenderer`: espera `C3D_FRAME_SYNCDRAW`, copia en su buffer persistente,
  vacía caché y dibuja colores de vértice opacos; sin asignaciones propias por cuadro.

El contador entrante determina muestra/fracción; el avance es 3686 Q12,
módulo 98304. Se conserva la traslación constante de cada hueso y el cierre
23→0. La representación mantiene XYZ y usa centrado/escala uniformes de
inspección; no adopta la base del visor estático. El encuadre permanece fijo
durante el movimiento. La cámara inicial es `(0.35,0.35,4.0)`.

Se eligieron **25 evaluaciones/s para preview**, sin afirmar que esa sea una
cadencia PS2 medida. El reloj no depende de los cuadros dibujados; limita dt
a 100 ms y descarta el intervalo de reanudación. A alterna pausa, R avanza
en pausa y L reinicia. Cruceta/X/Y/B conservan cámara/zoom/reset. Tras HOME
o tapa se espera soltar los controles; START conserva la salida.

## Validación

| Capa | Resultado y alcance |
|---|---|
| C++ Release | 252/252; cinco escenarios GPU nuevos y pruebas de dominio/aplicación/oráculo |
| C++ ASan/UBSan | 252/252 |
| Fallos stdio añadidos | Repetidos los dos tests afectados en ambos presets: lectura, lectura corta y cierre; salida sin datos parciales |
| Python | 172/172 de conversión/preparación/build y regresión de geometría/material |
| Cobertura de módulos nuevos | 98,71 % combinando líneas/ramas; conversor puro 100 % |
| Oráculo independiente, clip privado | 383 poses; error máximo de rotación 5,813e-7 y traslación 1,262e-4 en unidades originales; límites 1e-5 / 1e-3 |
| Fuentes independientes A/B | Archivos de entrega y reporte idénticos |
| ARM, GCC 16.1.0 | Nuevo visor y los cuatro visores previos compilan |
| Azahar 2126.2, Vulkan | Tres ejes, movimiento, pausa, paso, reinicio, cámara y START comprobados |
| New 2DS XL | AI-T5 aprobada por el usuario: ejes animados, A/R/L, cámara, START, tapa y HOME; sin medición de duración/FPS |

El test sintético de oráculo incluye cuaterniones de signo opuesto, jerarquía
asimétrica y cierre del bucle. El lector rechaza truncamiento, bytes extra,
perfil diferente, CRC incorrecto, padres incompatibles, NaN y cuaterniones
inválidos. Los dobles SDK comprueban copia/flush después de la sincronización,
ausencia de asignaciones del adaptador por cuadro y liberación tras esperar GPU.
La suite Python completa del repositorio no se repitió en esta tarea.
Ruff y los contratos del repositorio se verifican por separado.

En Azahar se observó `PAUSED Q12:0`, después `3686` con un paso y conservación
de ese contador durante la cámara. La cámara pasó a `(0.55,0.58,3.25)`, después
a `(0.33,0.32,4.05)` y B restauró `(0.35,0.35,4.00)`. A reanudó el movimiento.
El cierre se comprobó en pausa: desde 40546, dieciséis pasos llegaron a 1218,
igual a `(40546+16×3686) mod 98304`. Un envío inicial de 27 pulsaciones sin
intervalo suficiente solo produjo once flancos; se conservó esa captura y
se separaron las pulsaciones mediante observaciones de UI. No se interpretó
el número de eventos enviados como entradas aceptadas por el juego.
START devolvió Azahar a la lista. Los errores de archivo y HOME/tapa se
validaron en host; no se afirma una comprobación de esos casos en Azahar.

## Entrega y procedencia

Directorio privado autorizado: `/Users/germancontreras/sh3-private-data/`.
Entrega final: `f03-02-3ds-animation-v2/`; manifiesto SHA-256
`581b6ee6ce8149fd317a55d9fb8beec84f6aafbff8f616cc68f60e3f6d5cb969`.
La primera revisión queda preservada; la segunda mejora grosor, contraste y
encuadre después de la inspección visual.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| animation.san | 1248 | `8adbe5e59f05923c65d0813e2acfc6d88c9364db1d7e18641bdec27f6ac89381` |
| sh3_animation_probe.3dsx | 209708 | `61364e2f0a6bcb637a3c5b4e922fc49b484f3e2bcd8c2a283df3157d6d4f39fa` |
| sh3_animation_probe.smdh | 14016 | `2022f3b693f9f7e4a49e22b9dcc62261e376117cc1ce90777117c14a437e2936` |
| sd-card.zip | 226866 | `25e2ceed5e51738dd8edc553771ac90b915ea7f0f21327c3f5599cd3c2189eb4` |

Fuente A/B: `f03-02-skeleton-{a,b}-v1`, manifiesto
`4a53411124334fbcd7379a549f3ed0876b644a1b6a7910cb40c1077113405536`.
Referencia de continuidad conservada, SHA-256
`ea78b9d400712f07616794b0382da196bf5a9bb57b55d53c9002109a9914163c`.
Siete capturas privadas: `f03-02-animation-native-check-v1/`.
El reporte local `reports/local/f03-02-animation-inspection-execution-v1.json`
contiene hashes, límites y resultados sin exportar muestras originales.

SDK fijado: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
Compilación sin red desde una copia de 55 fuentes/configuraciones sin originales.
Manifiesto `build/animation-inspection/source-manifest-v2.json`, SHA-256
`def68441588931c16ff0150e4c808d3cfd3ce3fff45a0827a9c46fac41d632e5`.
JUnit y cobertura quedan en `build/animation-inspection/` y los presets host.
CI añade el build y artefactos de código; **no se afirma ejecución remota**.

Reproducción: `bash scripts/build_animation_probe.sh` dentro del SDK fijado;
`python -m tools.pipeline.prepare_animation_probe --help` describe la entrega.
El ZIP coloca cuatro archivos en `/3ds/sh3_animation_probe/`. Se verificó la
copia usada por Azahar. La SD física «NO NAME» no estaba montada al finalizar.

Entrega posterior, 2026-10-20: tras conectarla el usuario, se copió el build
`a1629eeace22` a `/Volumes/NO NAME/3ds/sh3_animation_probe/`. Los cuatro
archivos (225.678 bytes) coinciden en tamaño y SHA-256 tras lectura desde
la SD; los otros visores se conservaron. Solo se eliminaron los auxiliares
`._` generados para la carpeta nueva y sus archivos. SD expulsada con éxito.
Comprobante privado `f03-02-animation-native-check-v1/sd-copy.json`, SHA-256
`279dcafa09b869e3ad76eb4ca9bd2109b004e57de2f21cae505e74d80106393c`.
En el momento de la copia AI-T5 seguía pendiente. La confirmación posterior del
usuario cierra AI-T5; se conservan sin reescribir los reportes y hashes históricos.
