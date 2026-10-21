# F03.02 — Geometría MAP presentada en New 2DS XL

Fecha: 2026-10-20. [GI01–GI07](../specs/sh3-3ds/geometry-inspection.md),
GI-T1–GI-T5 completadas. El build `a039c31cb262` presenta desde SD las dos
formas del grupo 304: 56 vértices fuente, 32 triángulos, expandidos a 96
vértices de dibujo. El usuario confirma «lo probe y funciona todo, se ven
formas rectangulares» en respuesta al protocolo de formas, cruceta, X/Y, B,
START, tapa y HOME. [Registro físico](../compatibility/geometry-inspection.md).

La geometría y sus UV proceden del decoder MG. El checker y los colores
cian/naranja son propios. Se centra y escala el grupo para inspección, sin
matrices del juego. La apariencia rectangular no identifica el objeto ni
demuestra el material PS2. MP-T4/MG-T4, integración de escena y G03/G05 siguen
abiertos en sus restantes criterios.

## Implementación

- `geometry_inspection.py`: encoder SGM y transformación uniforme explícita.
- `prepare_geometry_probe.py`: verifica SHA-256 de manifiesto/JSON/build,
  reconstruye registros y contrasta topología, conteos y campos conservados.
- `inspection_inputs.py` / `inspection_archive.py`: lectura acotada y ZIP
  determinista compartidos con el visor de textura, cuya regresión se prueba.
- `inspection_geometry.cpp`: lector stdio sin asignación interna, máximo
  3072 vértices; rechaza NaN/Inf, límites inválidos y triángulos degenerados.
  Count queda en cero si falla incluso el cierre; CRC común extraído.
- `SceneRenderer`: vista prestada validada y copiada a memoria lineal propia.
  Mantiene aplicación, cámara, hooks APT, cache flush y destrucción RAII.
- `sh3_geometry_probe`: composición separada, error con ruta y START;
  `build_geometry_probe.sh` y artefactos CI exclusivamente de código.

No se lee la SD ni se asignan buffers propios por frame. El temporal del
lector ocupa 96 KiB y se libera después de inicializar; el VBO de esta muestra
ocupa 3072 bytes y usa el checker existente de 64×64.

## Validación

| Nivel | Resultado | Evidencia local |
|---|---|---|
| Python seleccionado | 276/276, incluye 77 casos nuevos GI y regresiones | `build/geometry-inspection/python-final.xml` |
| Python de los cinco módulos medidos | 238/240 líneas; 94/96 ramas; gate aprobado | `python-coverage.json` en el mismo directorio |
| C++ Release macOS | 224/224 | `host/test-results.xml` |
| C++ ASan/UBSan macOS | 224/224, UBSan con halt-on-error | `sanitize/test-results.xml` |
| C++ GCC Linux | 224/224 | `ci-source/build/host-coverage/test-results.xml` |
| Cobertura C++ portable | 1123/1131 líneas (99,3 %), 1070/1104 ramas (96,9 %) | `ci-source/build/coverage-summary.json` |
| Lector de geometría | 69/69 líneas, 100/102 ramas | mismo informe |
| ARM | ejecutable 3DSX, ELF, SMDH y hashes correctos | `ci-source/build/geometry-probe/` |
| Azahar 2126.2 / Vulkan | formas visibles, cámara, ambos zooms, B y START | capturas privadas |
| New 2DS XL / Homebrew Launcher | usuario confirma formas y todos los controles solicitados | protocolo físico |

Las rutas relativas de la tabla, salvo la primera, parten de
`build/geometry-inspection/`. La suite C++ incorpora 22 entradas nuevas: lector,
oráculo Python→C++ y 20 escenarios del renderer con malla prestada. Comprueba
liberación del buffer del llamador, fallos de adquisición, cache flush,
presentación y orden de destrucción, con regresiones de los otros visores.
Los fixtures no contienen datos del juego.

En Python, encoder y archive alcanzan 100 % de líneas/ramas. Las dos líneas
no cubiertas del conjunto son el rechazo de cambio de tamaño durante lectura
y el dispatcher `__main__` de preparación, este último ejecutado por el CLI
real al generar la entrega. No se declara cobertura completa del repositorio
Python ni una ejecución remota de GitHub Actions.

En Azahar se verificaron separadamente `MISSING` y `VERIFY_FAILED` al omitir
el archivo y alterar un byte de payload. START volvió a la lista de aplicaciones
en ambos casos y en el arranque válido. La cámara pasó de `(0.35,0.35,7.00)` a
`(0.55,0.10,5.55)`, alejó a distancia 6.45 y B restauró el estado inicial.
Las capturas de frames/FPS del emulador no constituyen medición en consola.
Tapa/HOME se acreditan por confirmación del usuario en hardware.

## Procedencia y entrega

Manifiesto MG de entrada:
`6714a2c7f96c4c168cdd0fe02583041f42876f3f84fab351cb35bf9248053318`.
Preparar desde las dos extracciones independientes produce los mismos archivos
y el mismo informe. Normalización: centro local `(-0.5,-1000.5,-796)`,
escala `0.0034393809114359416`, destino `(0,0.75,-2)`, sin cambios de ejes.
Cada forma aporta 48 vértices de dibujo. Cabecera/CRC se contrastaron aparte.

SDK fijado: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`,
GCC ARM 16.1.0. Contenedor sin red, montando copia de fuentes, sin originales.
El manifiesto de 629 archivos de código/fixtures y configuración es
`build/geometry-inspection/source-manifest.json`, SHA-256
`141acc20ec638c78c22baf843574244b517e586d1756ea02e79a48cd939bdd9f`.
Se verificó que esos archivos coinciden con el árbol usado en la entrega.

Directorio privado: `f03-02-3ds-geometry-v1/` bajo la raíz externa autorizada.
Manifiesto de entrega SHA-256:
`f8c563b3c1013d6f8fb1b4f4aff678d2eb536f797263c0b4c9f3ddbe99f9d7b0`.
Su estado `physical_2ds_xl=pending` corresponde al momento de preparación y
se conserva inmutable; el resultado posterior está en el protocolo enlazado.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `geometry.sgm` | 3096 | `9700205482f78d1c0f113d8d6aa325ad575feed9fc50c8796e2a7e9a67125926` |
| `sh3_geometry_probe.3dsx` | 204236 | `c248cdb224c9d3816b48b002df3490fa289f8013fa1c6cabe048169032523172` |
| `sh3_geometry_probe.smdh` | 14016 | `37e1a6f2de9e1ee4632fc70dff703412a0f3479eb69f58eafb43eab28451338e` |
| `LEEME.txt` | 571 | `183eb9ff253e230c865ffd205a53e85d83118cfe3324d2954465fa408841726b` |
| `sd-card.zip` | 223086 | `e683d18cfef8b0ebe7e3e63e18f6c2427267971afb2279855d60a0b4bbde4273` |

Los cuatro archivos se copiaron en una carpeta nueva
`/Volumes/NO NAME/3ds/sh3_geometry_probe/`, con fsync y lectura/hash posterior.
Se conservaron los visores anteriores. Capturas, comprobación independiente
y recibo de copia: `f03-02-geometry-native-check-v1/`, fuera del checkout.
Índice local de metadatos:
`reports/local/f03-02-geometry-inspection-execution-v1.json`.

Siguiente tarea: MP-T4/MG-T4, identificar y contrastar matriz, selección de
textura y CLUT en el consumidor o dibujo PS2 antes de combinar materiales
originales con esta geometría. La equivalencia visual continúa pendiente.
