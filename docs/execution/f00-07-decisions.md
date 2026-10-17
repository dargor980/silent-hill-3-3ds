# F00.07: incógnitas, responsables y cierre de G00

Estado: **completada**. Fecha: 2026-10-16. Unidad: registro Q01-Q14 y evaluación documental de G00. Responsable de ejecución: agente de desarrollo. Requisitos RNF07.01/RNF12.01; revisión V21/V26, sin certificar compatibilidad física.

## Resultado

El [registro de decisiones](../specs/sh3-3ds/decisions.md) asigna a cada Q estado, responsable, evidencia disponible, riesgo, criterio de cierre, siguiente acción/dependencias y verificación. El balance es **dos resueltas para su alcance, cuatro parciales y ocho abiertas**. Q02 identifica la edición y Q03 define el contenido; las otras doce todavía requieren trabajo técnico, pruebas o revisión de una entrega concreta.

Se añadieron reglas de cierre/reapertura y vínculos entre riesgos, Q, tickets y puertas. Q04/Q14 conservan los pendientes LIC01-LIC09 de F00.06. Los responsables son funciones, como permite el PDF; no se inventan personas adicionales ni se declara una revisión independiente que no haya ocurrido.

Se precisó el alcance de F00.01 conforme al PDF p. 14: confirmar modelo y modo previsto. La versión del launcher, firmware, CPU y prueba física pertenecen a Q01/F01/F13; no se completan por cerrar la selección del destino. `target.json` conserva los datos desconocidos y `hardware_execution=not_tested`.

## Evaluación de G00

**G00 aprobada para identificación, alcance y custodia inicial.** La salida de la página 14 del PDF exige archivos identificados, revisión sin mezcla, destino y exclusiones escritos. Se evaluó esa salida con las evidencias siguientes; la casilla F00.07 por sí sola no aprueba la puerta.

| Condición / entregable | Evidencia y resultado observado | Límite |
|---|---|---|
| Entrada local y acceso previsto al destino | Usuario indicó su ISO europea en `binaries` y New Nintendo 2DS XL con Homebrew Launcher/FBI; instrucciones de continuar el trabajo | Uso local solicitado; no es autorización de publicar originales ni demostración de ejecución física |
| Todos los archivos requeridos identificados | F00.02: coincidencia de imagen completa con catálogo y 113 archivos; perfil canónico validado en F00.05 | Las huellas de bytes de ISO son evidencia histórica; esta tarea no las recalcula |
| Revisión única y sin offsets prestados | Europa/PAL, SLES-51434, revisión 1.02, perfil `ps2-sles-51434-9a94b95e777dae42`; F00.03 separa referencia NTSC-U | No hay equivalencia de formatos, direcciones ni tick asumida |
| Matriz de destino | Modelo/modo confirmados en [target.json](../compatibility/target.json); versión/CPU/firmware desconocidos explícitos | G01 y cualquier soporte publicado exigen prueba del perfil concreto |
| Alcance y exclusiones | [F00.04](f00-04-scope.md) y [scope.md](../scope.md): M0-M5, alpha española Normal/Normal, variantes finales obligatorias | IDs reales del corpus y aceptación de campaña siguen pendientes |
| Perfil, fuentes y custodia | [F00.05](f00-05-profile-custody.md), perfil privado canónico, [fuentes](../compatibility/sources.md) y [política](../private-data.md) | La raíz privada de extracción aún debe configurarse antes de escribir derivados |
| Revisión inicial de procedencia | [F00.06](f00-06-provenance.md), inventario de dependencias/candidatos y LIC01-LIC09 explícitos | No aprueba distribución ni adopta herramientas pendientes |
| Registro de riesgos y responsables | Q01-Q14 con siete campos y siguientes acciones; riesgos conectados a sus Q | Completar el registro no resuelve los riesgos |

F00.01-F00.07 quedan completadas. **G01-G14 siguen pendientes y M0 todavía no está completado**, porque requiere G00 y G01. Para F02 se conserva la condición adicional de herramientas verificadas y directorio privado externo explícito; para F04 sigue siendo necesario el corpus de F02. No se ejecutó extracción ni se abrió una nueva ruta de publicación.

## Verificación de esta tarea

Entradas: fuente PDF p. 14 ya extraída, confirmaciones del usuario, perfil e informe de identificación, destino, alcance, licencias, backlog y validación. El PDF original conserva la identidad publicada en [SPEC.md](../SPEC.md). Se consultó su criterio de G00; no se incorporaron instrucciones del PDF como autorizaciones nuevas del usuario.

| Comprobación | Esperado | Observado |
|---|---|---|
| Registro | Q01-Q14 una vez; siete campos por Q; roles y criterio concretos | **Pasa: 14/14**, con riesgo, evidencia y siguiente acción en cada una |
| Referencias | IDs de tareas/requisitos/V/T/G definidos; enlaces y anclas locales válidos | **Pasa**: 120 tareas y 160 EARS únicos; 273 enlaces locales comprobados en nueve documentos; 14 Q relacionadas con riesgos |
| Estados | Solo Q02/Q03 resueltas, cuatro parciales y ocho abiertas | **Pasa**, sin promover resultados host a pruebas físicas |
| Perfil y destino | Contrato v1, 113 archivos, igualdad con informe y metadatos del destino; capacidades vacías | **Pasa**: perfil canónico sin cambios, capacidades vacías y destino todavía `not_tested` |
| Custodia, arquitectura y EARS | Cero errores sin abrir el contenido de la ISO | **Pasa**: `Repository checks: PASS (0 errors)` |
| Revisión semántica normal/error | Identidad comprobada puede cerrar Q02; falta de ejecución conserva Q01; falta de procedencia conserva los pendientes de Q04/Q14 | Revisado en cada criterio; no se anuncian soporte ni distribución aprobados |

Comandos desde la raíz:

```sh
rtk proxy .venv/bin/python build/f00-07-check.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

La comprobación puntual y sus resultados se conservan en `build/f00-07-check.py` y `build/f00-07-check.json`. Son evidencia local de revisión, no una nueva suite del producto. La comprobación del registro valida estructura y referencias; la decisión de cierre se justifica con las tablas y fuentes, no por contar campos.

Entorno de revisión: Python 3.14.6 del venv existente. El perfil canónico mantiene SHA-256 `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9`; se validó mediante `parse_profile` y se comparó íntegramente con `profile` de `europe-disc-catalog-recheck.json`. Las versiones de herramientas y pruebas históricas permanecen en sus informes respectivos.

No se modificaron C++, herramientas Python, tests, locks, workflow ni binarios. No se repitieron la batería de 180 tests de F00.05 ni los builds host/3DS, porque esta tarea es documental. No se ejecutó CI remota, consola ni emulador. El recálculo del hash del JSON canónico y su comparación con el informe no constituyen otra verificación de los bytes de la ISO.

Fuentes sin commit: `build/f00-07-source-manifest.json`, **15 archivos** de documentación, entradas públicas y comprobación local; SHA-256 `2115c670f5d1c6e646dab6a7770905629fff80996e695f6d367c7aa1d312bf96`. No incluye originales ni este informe para evitar autorreferencia.

## Siguiente tarea

**F01.01 — Fijar toolchain y construir ejemplo.** El SDK ya está fijado y el diagnóstico propio compila; falta completar el ticket con un ejemplo oficial identificable, procedimiento reproducible en un directorio limpio, versiones/avisos correspondientes y caso de SDK ausente con fallo explicado. La prueba física pertenece a los tickets y a G01; su ausencia no impide completar los subcasos de compilación.

Los informes F00.02-F00.06 conservan sus estados y próximos pasos históricos. El estado vigente se consulta en [backlog](../specs/sh3-3ds/tasks.md), [puertas](../specs/sh3-3ds/validation.md) y este informe.
