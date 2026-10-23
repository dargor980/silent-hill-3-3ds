# F03.04 — Intermedio de malla, esqueleto y animación

2026-10-23. **IR-T1–IR-T4 completadas** para `ps2-character-0209-v1`.
[Contrato EARS IR01–IR06 y tareas](../../schemas/intermediate-v1.md).
Continúa después de [GC-T5](f03-03-character-world-inspection.md), cuya prueba
física y métricas fueron reportadas por el usuario. F03.04 global y G02/G03
siguen abiertos; el perfil inicial no incluye materiales ni escenas. La
[ampliación IR-T5](f03-04-character-render-intermediate.md) conserva este
perfil e incorpora materiales, luces y colocaciones por composición.

## Resultado y responsabilidades

`intermediate.json` conserva todos los campos de los documentos decodificados
de malla, esqueleto y animación, más los manifiestos originales completos.
Incluye las **76 muestras ANM**, campos desconocidos, flags, orden de caras,
grupos, palabras originales y pesos con déficit. Las versiones de perfil,
convertidor, contratos de decodificación y convenciones quedan explícitas.
Los estados históricos de los manifiestos se conservan; no se reescriben
como si las verificaciones posteriores ya existieran al crearlos.

Desde ese archivo se regeneran **animation.san y character.scm idénticos al
build físico `abe9a7a35464`**, sin consultar los documentos originales ni ISO.
SAN mantiene el recorte de inspección 0..23; el resto de los datos permanece
en el sidecar. Se conserva la representación lógica JSON, incluidos tipos
numéricos y cero negativo, no el espaciado de los originales ni el MDL binario.
Los SHA de procedencia describen las entradas históricas; el manifiesto nuevo
protege los bytes exportados. No constituyen una firma del recurso original.

El codec `intermediate_json` valida JSON y presupuestos sin I/O; el adaptador
`character_intermediate` comprueba identidad, esqueleto y convenciones, y
reutiliza las recetas existentes. `prepare_character_intermediate` coordina
lecturas fijadas y comparación de reconstrucción. El writer privado existente
publica en una carpeta exclusiva, conserva salidas previas y termina con el
manifiesto. No se añade lógica de conversión al renderer ni al dominio C++.

## Verificación sintética

**167 tests aprobados**: intermedio y regresiones de animación, personaje y
colocaciones. Cobertura de los tres módulos nuevos: **97,58 % de líneas**,
**95,95 % de ramas**, **97,07 % combinada**; gate independiente ≥80 % aprobado.
El adaptador tiene 100 % de líneas/ramas cubiertas. Informes locales:
`build/character-intermediate/pytest.xml` y `coverage.json`.

Se ejercitaron extensiones desconocidas, último sample conservado aunque no
se exporta en SAN, tipos/cero negativo, igualdad determinista y reconstrucción
después de retirar los archivos de origen sintéticos. Los negativos cubren
versiones, identidad, hashes/tamaños, esqueleto incompatible, datos inválidos,
duplicados JSON, números no finitos, profundidad/nodos/texto excesivos,
symlinks y salida preexistente. No se borraron entradas privadas.

Comando de la suite:

```sh
.venv/bin/python -m pytest \
  tests/python/test_character_intermediate.py \
  tests/python/test_animation_inspection.py \
  tests/python/test_character_inspection.py \
  tests/python/test_character_world_inspection.py \
  --cov=tools.pipeline.intermediate_json \
  --cov=tools.pipeline.character_intermediate \
  --cov=tools.pipeline.prepare_character_intermediate \
  --cov-report=json:build/character-intermediate/coverage.json \
  --cov-report=term-missing \
  --junitxml=build/character-intermediate/pytest.xml -q
.venv/bin/python -m tools.qa.coverage_gate build/character-intermediate/coverage.json
```

El job Python existente descubre estos tests sintéticos y mide `tools`; no
requiere datos privados ni cambios de pipeline. No se ejecutó CI remoto ni
se recompiló ARM: esta entrega no modifica el visor ni sus SAN/SCM.

Ruff y formato pasan en el alcance exacto del job de CI (234 archivos),
así como el gate de arquitectura/custodia/trazabilidad y `git diff --check`.
Una comprobación exploratoria más amplia sobre todo `tests` encontró 37
avisos de lint y siete archivos por formatear en fixtures históricos fuera
del alcance de ese job. Los archivos con avisos de lint coinciden con HEAD;
no se modificaron. Registro local `build/character-intermediate/broad-lint.json`.

## Conversión privada A/B y reconstrucción

Se convirtieron las dos extracciones previamente conservadas en carpetas
nuevas `f03-04-character-intermediate-{a,b}-v1`, bajo
`/Users/germancontreras/sh3-private-data/`. Cada lectura de entrada fue acotada
y verificada contra el manifiesto fijado. No se extrajo nuevamente la ISO.

| Entrada | SHA-256 del manifiesto, igual en A/B |
|---|---|
| f03-02-skeleton-{a,b}-v1 | `4a53411124334fbcd7379a549f3ed0876b644a1b6a7910cb40c1077113405536` |
| f03-02-character-mesh-{a,b}-v1 | `2a360854c7becb493a4b84a4ff25811ab20f4b97d196d870ff0b2e573df2703f` |

Ejemplo A; para B se cambian ambos directorios de entrada y el run-id:

```sh
.venv/bin/python -m tools.pipeline.prepare_character_intermediate \
  --skeleton-source /Users/germancontreras/sh3-private-data/f03-02-skeleton-a-v1 \
  --skeleton-sha256 4a53411124334fbcd7379a549f3ed0876b644a1b6a7910cb40c1077113405536 \
  --mesh-source /Users/germancontreras/sh3-private-data/f03-02-character-mesh-a-v1 \
  --mesh-sha256 2a360854c7becb493a4b84a4ff25811ab20f4b97d196d870ff0b2e573df2703f \
  --private-root /Users/germancontreras/sh3-private-data \
  --run-id f03-04-character-intermediate-a-v1
```

Para repetir, usar run-id nuevo: el comando rechaza sobrescribir una entrega.
Las dos salidas y manifiestos son idénticos; lectura posterior verifica tamaños
y hashes. Un auditor separado compara todos los árboles de origen usando la
biblioteca JSON estándar y reconstruye desde el sidecar guardado. Los SAN/SCM
coinciden con la entrega GC-T5 cuyo manifiesto fijado es
`98a0a130b1d4bec9df09655c37f4a63bc12944e2e30422b02e6cc6cc58321f53`.

| Salida | Bytes | SHA-256 |
|---|---:|---|
| intermediate.json | 309.807 | `1be28b72967da804a670dfa67a78a5446e5375e45c0864e2f1e399fa6fa62892` |
| animation.san | 1.248 | `8adbe5e59f05923c65d0813e2acfc6d88c9364db1d7e18641bdec27f6ac89381` |
| character.scm | 47.670 | `3ccf6bbbce726ccedd0b481cd7667ebe95213acc1a2f1dcdf3b27c5a2f792479` |
| manifest.json | — | `3a7d4388fdaa4c88567b413d0e0b3a604c8017a768f6f4a25bad108108f66698` |

Auditor local `build/character-intermediate/audit.py`, SHA-256
`6efa244fdbb56ab2c82fba2f8cae931e73321d796dd938dd18453de7498927b1`.
Comprobante privado `f03-04-character-intermediate-check-v1/roundtrip.json`,
SHA-256 `dfa22ce2be59a5b5f99962175ce9584f644d8492b608b288a3a220d65ccff0fb`.
Incluye hashes de la implementación usada. El alcance físico sigue siendo
el build GC-T5 ya probado, sin atribuir una nueva prueba de hardware.

## Siguiente alcance

**[IR-T5 completada posteriormente](f03-04-character-render-intermediate.md):**
materiales/texturas, iluminación y colocaciones, estados GS y metadatos
conservados; SCT/SCL/SCW idénticos a los visores. Sigue IR-T6, geometría estática
y material de mapa, y después colisión, cámara y audio antes del cierre
global. SH3P requiere su propio contrato F03.05. Daño/muerte, selección de
luces entre escenas y un circuito jugable permanecen pendientes.
