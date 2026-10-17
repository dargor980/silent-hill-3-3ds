# F00.05: perfil, fuentes y custodia de datos

Estado: **completada**. Fecha: 2026-10-16. Unidad: contrato de perfil v1, inventario de fuentes y controles de ubicación de datos. Responsable: agente de desarrollo. Requisitos RF01.01/RNF08.01; V01/V22/V25, T01 y normas RNF07/RNF11.

## Resultado

Se completaron el [contrato del perfil](../../schemas/game-profile-v1.md), el [inventario SRC01-SRC09](../compatibility/sources.md) y la [política de datos v1.1](../private-data.md). El perfil europeo canónico conserva los mismos 113 archivos, idiomas del origen, capacidades vacías y ausencia de extractor; el español y Normal/Normal de la alpha permanecen en el alcance del producto.

La validación del contrato y la igualdad entre el perfil canónico y `profile` del informe de contraste de F00.02 pasan. El SHA-256 del JSON de 17.037 bytes es `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9`. Esta tarea leyó los metadatos locales y comprobó ubicación/índice; **no recalculó los hashes de la ISO**, no extrajo recursos ni modificó originales. La evidencia de identidad completa sigue en [F00.02](f00-02-edition-identification.md).

El escaneo anterior podía aceptar archivos no ISO en `binaries`, datos en `reports/local` sin verificar exclusión, enlaces rotos/de directorio y archivos bajo una carpeta anidada llamada `build` o `.venv`. También el inspector de directorios resolvía una raíz enlazada antes de rechazarla. Se reprodujeron esos casos con datos propios: 17 casos fallaron antes de corregirlos.

`tools/qa/custody.py` ahora decide ubicaciones a partir de metadatos, inspecciona Git y recorre sin seguir enlaces. Las excepciones de entorno tienen rutas concretas; `build` ya no oculta ISO/MFA/AFS. El verificador rechaza raíces enlazadas, y el perfil rechaza capacidades de solo espacios. Se añadieron exclusiones Git para AFS/IRX/IMG como respaldo, sin autorizar guardarlos en el checkout.

Separación SOLID: reglas del perfil sin filesystem; verificación por `FileInspector`; adaptador de directorios separado; decisiones de custodia sin nombres/hashes del juego; adquisición de metadatos y composición explícitas. La revisión de procedencia/licencias sigue en F00.06 y la revisión de un release en G14.

## Pruebas ejecutadas

Entorno local: Python 3.14.6, pytest 9.1.1, herramientas fijadas en los locks. Todos los casos de error usan datos sintéticos y repositorios Git temporales; no se añadió ni retiró nada del índice del proyecto.

| Comprobación | Esperado | Observado |
|---|---|---|
| Perfil completo y campos omitidos/tipos/tamaño/hash | Aceptar el contrato válido y rechazar entradas inválidas con error tipado | Pasa; incluye campos obligatorios y capacidades de solo espacios |
| Datos PS2 internos/ancestros, raíces y entradas enlazadas | Rechazo antes de aceptar identidad | Pasa con fixtures y ambas plataformas en el caso de raíz enlazada |
| Custodia adversarial | Rechazar ubicación indebida, enlace normal/roto, FIFO, reporte no ignorado, `git add -f` y fallo Git/recorrido | Pasa; el FIFO se inspecciona sin abrirlo |
| Custodia válida | Aceptar ISO regular ignorada, reportes de metadatos ignorados y builds sintéticos permitidos | Pasa sin reducir las reglas para carpetas anidadas |
| Batería Python completa | Cero fallos y cobertura ≥80 % de líneas y ramas por separado | **180/180 pasan**, sin omisiones; **576/602 líneas = 95,68 %**, **235/248 ramas = 94,76 %** |
| Ruff y formato | Cero errores | Pasa |
| Comprobador de repositorio | Arquitectura, custodia, EARS y enlaces correctos | `Repository checks: PASS (0 errors)` |
| CLI de fixture propio | Identificado, sin extracción | `synthetic-v1`, 1 archivo, `extraction=not_performed` |
| Custodia del checkout | ISO e informes regulares, ignorados y sin seguimiento Git | 1 ISO de 3.586.785.280 bytes y 7 informes; todos cumplen |

Comandos desde la raíz:

```sh
rtk proxy .venv/bin/python -m ruff check tools tests/python
rtk proxy .venv/bin/python -m ruff format --check tools tests/python
rtk proxy .venv/bin/python -m pytest -q --cov=tools \
  --cov-report=json:build/f00-05-python-coverage.json \
  --cov-report=xml:build/f00-05-python-coverage.xml \
  --cov-report=term-missing --junitxml=build/f00-05-pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/f00-05-python-coverage.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy .venv/bin/python -m tools.pipeline.verify \
  --profile tests/fixtures/synthetic/game-profile.json \
  --data-root tests/fixtures/synthetic
```

Artefactos locales: `build/f00-05-pytest.xml`, `build/f00-05-python-coverage.json` y `build/f00-05-python-coverage.xml`. El job `quality` ya ejecuta las mismas suites y el comprobador; no se cambia el workflow. No se ejecutó CI remota ni se reconstruyó C++/3DS: el runtime no cambió. No hay evidencia nueva de ejecución física.

Fuentes sin commit: `build/f00-05-source-manifest.json`, **37 archivos** de herramientas, pruebas, contratos, documentación, configuración y locks; SHA-256 `50e73e171f7ffef58c4ad7d490245f2446e8ea72f2cdc7de6beb6e430eee52d7`. Excluye originales y este informe para evitar autorreferencia; los reportes de pruebas se conservan aparte.

## Límites y continuidad

El escaneo usa ubicación, índice, tipo de entrada y extensión; no detecta todo original renombrado ni valida el contenido de cada JSON. No debe ejecutarse sobre un árbol que otro proceso esté modificando. Las rutas excluidas son entornos de desarrollo, no almacenes de originales. Estas limitaciones y la revisión del artefacto final quedan explícitas en la política.

F00.05 se cierra con perfil, inventario, política y regresiones. G00 permanece abierta por **F00.06 — Revisar procedencia inicial** y F00.07. La próxima tarea es completar la matriz de versiones, licencias, origen y estado de adopción de las herramientas actuales y candidatas; la extracción sigue pendiente de sus puertas y directorio privado explícito.
