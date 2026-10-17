# Silent Hill 3: specs del port PS2 a Nintendo 3DS

Versión 1.14 · 17 de octubre de 2026 · Estado: F00 completada; G00 aprobada; entorno y diagnóstico F01 en curso.

Especificación basada en `SPEC_Silent_Hill_3_PS2_a_3DS_v1.0.pdf`, aplicando las fases de requisitos, diseño y tareas de `spec-driven-development`. El objetivo es una adaptación nativa de la edición PS2 identificada, con la New Nintendo 2DS XL como destino confirmado y un primer ejecutable `.3dsx`.

Ver también: [normas SOLID/testing](engineering.md), [avance de ejecución](execution/foundation.md) y [guía de build](../README.md).

## Documentos

| Documento | Contenido |
|---|---|
| [Requisitos EARS](specs/sh3-3ds/requirements.md) | 160 criterios con IDs estables, agrupados en los 14 RF y 12 RNF del PDF; historias de usuario, fuente y verificación |
| [Diseño](specs/sh3-3ds/design.md) | 13 componentes, arquitectura, puertos, modelos lógicos, errores, flujos y decisiones propuestas |
| [Tareas](specs/sh3-3ds/tasks.md) | Las 120 tareas fuente F00.01-F14.09 en 15 fases, dependencias, rutas previstas, criterios de cierre y relación con B001-B012 |
| [Validación y trazabilidad](specs/sh3-3ds/validation.md) | Matriz de los 160 criterios, 26 familias de verificación, T01-T14, presupuestos, G00-G14 e hitos M0-M5 |
| [Decisiones e incertidumbres](specs/sh3-3ds/decisions.md) | D01-D10, 14 incógnitas con evidencia de cierre, riesgos, plantilla ADR y referencias S01-S20 |
| [Alcance por hito](scope.md) | F00.04/Q03: M0-M5, alpha en español y Normal/Normal, ruta inicial, corpus del slice y obligaciones de contenido |
| [Fuentes y custodia](compatibility/sources.md) | F00.05: origen y ubicación de entradas, perfil canónico y evidencia; vincula el contrato del perfil y la política de datos |
| [Procedencia y licencias](compatibility/licenses.md) | F00.06: versiones, origen, SDK/runtime, host/CI y candidatos S01-S20; pendientes LIC01-LIC09 y evidencia consultada |

Orden de lectura: requisitos → diseño → tareas. Consultar validación y decisiones antes de aceptar una tarea o una fase. Los documentos enlazan criterios con implementación futura y pruebas; no existe una segunda lista independiente de avance.

## Interpretación de los requisitos

Las palabras `WHEN`, `IF`, `WHILE`, `WHERE`, `THEN` y `SHALL` delimitan la sintaxis EARS; el resto está redactado en español. Cada criterio tiene una marca de procedencia:

- **[E]**: 133 criterios que desarrollan obligaciones explícitas del documento fuente.
- **[P]**: 12 criterios que conservan propuestas o umbrales provisionales del PDF.
- **[D]**: 8 criterios derivados que precisan una respuesta verificable y requieren revisión antes de su aceptación.
- **[U]**: 7 criterios añadidos por la instrucción posterior del usuario de aplicar SOLID, testing y pipelines.

Las marcas no expresan resultados de pruebas. El perfil de 30 FPS, margen de memoria, tiempos de prueba y sincronía audiovisual son metas propuestas; su escritura no confirma que la consola pueda cumplirlas.

## Alcance y decisiones pendientes

El PDF propone avanzar desde prueba técnica a habitación jugable, vertical slice, alpha y candidato completo. Para ampliar la campaña primero se exige evidencia de lógica portable y margen de renderizado en G04 + G05, seguida de integración y caracterización de riesgos en G09.

El usuario confirmó New Nintendo 2DS XL y Homebrew Launcher, con FBI disponible para la ruta CIA futura, y seleccionó español con acción Normal/acertijos Normal para la primera alpha. [F00.04](execution/f00-04-scope.md) concreta contenido por hito; el candidato completo conserva todos los idiomas y variantes de la edición. Permanecen pendientes las versiones del entorno físico, inventario de unidades reales, cobertura de formatos, tick, tolerancias, memoria utilizable y condiciones de publicación. La copia europea SLES-51434/PAL, versión 1.02 y lista de idiomas en/fr/de/es/it quedaron identificadas por coincidencia con el catálogo; ver [F00.02](execution/f00-02-edition-identification.md). Los contratos binarios SH3P y de guardado son diseños por concretar, no formatos existentes descubiertos en los originales.

El usuario autorizó comenzar la ejecución y exigió SOLID, batería de tests y pipelines. Se implementó una fundación sintética; el estado comprobado y las limitaciones figuran en el [informe de ejecución](execution/foundation.md). F02.05 ya verificó dos extracciones del subconjunto MFA aceptado, conservadas en una raíz privada externa. No se implementó lógica del juego.

[F00.05 completada](execution/f00-05-profile-custody.md): perfil, inventario y custodia con regresiones sintéticas verificadas. [F00.06 completada](execution/f00-06-provenance.md): revisión inicial de procedencia/licencias y pendientes por componente. [F00.07 completada](execution/f00-07-decisions.md): Q01-Q14 consolidadas y G00 aprobada por evidencia de identificación, alcance y custodia. [F01.01 completada](execution/f01-01-toolchain.md): ejemplo oficial reproducible, C++17 ARM y build propio limpio; [F01.02](execution/f01-02-diagnostic.md) tiene implementación, 14 casos CTest y build ARM comprobados; queda pendiente el arranque físico. [F01.03](execution/f01-03-files.md) tiene archivos/opciones, errores de I/O, 21 casos CTest y build ARM comprobados; la SD real sigue pendiente. [F01.04](execution/f01-04-audio.md) tiene tono/errores/contadores, 31 casos CTest y build ARM comprobados; escucha pendiente. [F01.05](execution/f01-05-debugging.md) añade manifiesto ELF/3DSX, rechazo de mezclas y breakpoints alcanzados en Azahar; consola y refresco tras reconexión pendientes. [F01.06](execution/f01-06-resources.md) incorpora recursos observables y protocolo de tiempos/retención; B_app y entorno físicos siguen pendientes. [F01.07](execution/f01-07-lifecycle.md) corrige entrada suspendida y protege reanudación/controles, con 47 casos CTest; hardware pendiente. [F01.08](execution/f01-08-builds.md) verifica builds completos y fallos de CI, con 295 casos Python y 47 CTest; protocolo físico de treinta minutos preparado. [F02.01](execution/f02-01-inventory.md) completó dos catálogos ISO idénticos de 113 archivos, con IDs/offsets/tipos y desconocidos; batería de 357 tests Python aprobada. [F02.02](execution/f02-02-mfa-candidate.md) evaluó el candidato MFA y verificó una alternativa de inspección D8, con 430 tests Python: B0/MV0 pasan estructura, 60 archivos permanecen desconocidos. [F02.03](execution/f02-03-container-variants.md) amplió B8: unión de 61 contenedores/1740 entradas estructurales, 493 pruebas, XBG0 con codificación no resuelta. [F02.04](execution/f02-04-asset-catalog.md) produjo dos catálogos idénticos: 1740 recursos con IDs/offsets/SHA-256, tipos y dependencias semánticas pendientes; 582 pruebas aprobadas. [F02.05](execution/f02-05-repeatable-extraction.md) verificó dos copias de los 1740 recursos contra el catálogo, con 686 pruebas aprobadas y destinos externos. [F02.06](execution/f02-06-extraction-hardening.md) verificó mutaciones, errores de I/O y SIGKILL sintético; corrigió limpieza/propiedad de descriptores y estado final, con 828 pruebas aprobadas. [F02.07](execution/f02-07-slice-corpus.md) completó contrato, lectura e inventario inicial de 1740 candidatos; dos informes idénticos y 919 pruebas aprobadas. [La investigación de cámara](execution/f02-07-camera-probe.md) añadió un sondeo de hipótesis repetible para 285 candidatos, con discrepancias en 154 archivos y 985 pruebas aprobadas. [La inspección estática del ejecutable](execution/f02-07-camera-consumer.md) localizó dos sitios candidatos sin vínculo de recurso demostrado, con dos informes iguales y 1101 pruebas aprobadas. [El seguimiento del puntero](execution/f02-07-camera-pointer.md) registró una referencia externa y dos fronteras de llamada, con dos informes iguales y 1240 pruebas aprobadas. [El análisis de fronteras](execution/f02-07-camera-boundary.md) separa entrada/retorno en tres llamadas, con 1307 pruebas aprobadas y dos informes iguales; conservación y recurso siguen sin demostrar. [El plan y validador de captura](execution/f02-07-camera-observation.md) producen dos planes idénticos (tres fronteras/25 puntos), con 1435 pruebas aprobadas. [PCSX2 y BIOS principal configurados](execution/f02-07-ps2-boot.md), con carga del ejecutable europeo comprobada por logs; captura/validación visual pendientes. Sigue `camera-runtime-capture-eu`; vínculo de recurso, doce categorías y par de salas permanecen pendientes. G01 permanece pendiente de consola y G02 de cobertura de formatos/corpus. Estas revisiones no acreditan extracción completa, semántica de recursos, ejecución en consola ni una distribución concreta.

## Fuente y trazabilidad documental

- Documento: `SPEC_Silent_Hill_3_PS2_a_3DS_v1.0.pdf`.
- Versión y fecha declaradas: 1.0, 16 de octubre de 2026.
- Extensión: 35 páginas, consultadas íntegramente mediante extracción de texto y revisión visual de las páginas renderizadas.
- SHA-256 del PDF leído: `079a8da1074e182c34a8dce99c4dc78761c48255129337d339d64a4f0c0fb33a`.
- El PDF original permanece fuera del repositorio. Las referencias por página y los IDs RF/RNF/F/G/T/B/D/S conservan la relación con esa versión.
- S01-S20 conservan las referencias del PDF. La ejecución posterior verificó y fijó el subconjunto de herramientas recogido en el [inventario](compatibility/toolchain.md); los demás candidatos permanecen pendientes.

## Verificación de esta entrega

Se comprobó la unicidad y secuencia de los 160 IDs EARS, su cobertura por la matriz y su presencia en tareas. Se comprobó que las 120 tareas del PDF aparecen una vez, que todas las referencias internas existen y que los enlaces Markdown locales resuelven.

La primera entrega contenía solo documentación. La ejecución posterior añade código, tests y builds sintéticos. G00 está aprobada documentalmente; G01-G14 siguen pendientes. Los resultados host y de compilación no acreditan ejecución ni rendimiento en consola. Consulte el [registro de evidencia](execution/foundation.md).

Con F00 cerrada, continuar F01 desde el primer ticket pendiente y conservar sus subcasos físicos sin aprobar. F02 exige además herramientas verificadas para la operación y ubicación privada externa antes de escribir derivados. Aplicar la [custodia actualizada](private-data.md): ISO local en `binaries` ignorada por Git, evidencia local ignorada y extracciones externas al checkout.
