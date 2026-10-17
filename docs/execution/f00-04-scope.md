# F00.04: alcance de contenido por hito

Fecha: 2026-10-16. Unidad: definición documental del alcance europeo v1.0. Responsable de elaboración: agente de desarrollo; selección de idioma/dificultad: usuario. Estado: **completada como definición documental**, con revisión de alcance y comprobación local aprobadas.

## Entradas y resultado

- PDF `SPEC_Silent_Hill_3_PS2_a_3DS_v1.0.pdf`, pp. 3-4, 14, 23-25 y 27-28; versión, identidad y procedencia en [SPEC.md](../SPEC.md).
- Identificación cerrada en [F00.02](f00-02-edition-identification.md): perfil europeo `ps2-sles-51434-9a94b95e777dae42`, versión 1.02. No se vuelve a leer ni modificar la ISO en esta tarea.
- Destino confirmado: New Nintendo 2DS XL con Homebrew Launcher; FBI disponible como opción futura.
- Respuesta expresa del usuario durante F00.04: «Textos en español; acción y acertijos en Normal (recomendado)».

[scope.md v1.0](../scope.md) fija M0-M5, `alpha-es-normal-v1`, los criterios del corpus `slice-es-normal-v1` y SC01-SC15. Incluye ruta inicial de Nueva partida a final/créditos/resultados sin debug, contenido obligatorio, exclusiones temporales y fuera de alcance, responsables de cambio, pruebas y evidencia de aceptación. La primera alpha prioriza la configuración elegida; los demás idiomas, dificultades, ramas, finales y extras presentes en la edición siguen siendo obligatorios para el candidato completo.

Los nombres/IDs concretos del par de salas se obtendrán en F02.07 y el inventario real en F11.01. Esos trabajos no se presentan como hechos. El alcance define cómo aceptarlos y conserva las categorías no investigadas como pendientes. Las variantes posteriores se implementan en F10/F11 y requieren renovar la evidencia G10/G11 antes de M5.

Se sincronizan el contexto de requisitos, registro Q03, ticket detallado F00.04, backlog, validación, índice SPEC, README y comparación de edición. Los 160 criterios EARS existentes y los IDs de las 120 tareas se conservan. La identidad de `GameProfile`, sus capacidades y los pipelines no cambian; la separación SOLID y la batería vigente se incorporan por referencia.

## Revisión documental V13

| Caso | Resultado esperado | Observado en la revisión |
|---|---|---|
| Selección del usuario | Español y Normal/Normal en la primera alpha | Coinciden en alcance, requisitos, decisiones, backlog e índices |
| Escalonamiento | M0-M5 con contenido, gates y evidencia | Seis filas; diagnóstico, datos/lógica, habitación, slice, alpha y candidato separados |
| Categorías RF13.01 | Todas representadas, sin confundir archivos con jugabilidad | SC01-SC14 cubren las categorías, separando acción y acertijos; SC15 conserva extras/repetición |
| Rama/final no elegidos para la alpha | Deben permanecer como obligación posterior | SC13/SC14 obligatorios en M5; su retirada exige decisión registrada |
| Idioma/dificultad no elegidos | Aplazamiento explícito, sin pérdida de cobertura futura | SC10 conserva es/en/fr/de/it; SC11/SC12 exigen todas las variantes presentes |
| Datos todavía desconocidos | No inventar salas, cantidades, formatos ni éxitos | IDs delegados a F02.07/F11.01; estado `sin_inventariar` bloquea declarar candidato completo |
| Madurez y evidencia | Definir alcance no aprueba juego ni gates | G00-G14 pendientes; T13 y pruebas físicas siguen por ejecutar; no hay porcentaje de campaña |
| Control de cambios | Omisiones visibles con responsable y efecto en QA | Versión, unidades afectadas, motivo y decisión requeridos; conserva filas excluidas |

Esta revisión satisface la **definición** pedida por F00.04 para RF13.01/RF13.04. No es el inventario exhaustivo ni la validación de contenido que exigirán esos requisitos en F11/F13.

## Comprobación reproducible

Desde la raíz del repositorio:

```sh
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Esperado y observado: **`Repository checks: PASS (0 errors)`**, salida 0, Python 3.14.6. Comprueba arquitectura, custodia, referencias EARS y enlaces locales de documentación. No ejercita gameplay, hardware ni CI remota. No se repiten las suites C++/Python o la compilación 3DS porque esta tarea solo cambia Markdown.

La comprobación adicional del inventario documental confirma **160 IDs EARS únicos, 120 tareas únicas, seis hitos M0-M5 y 15 categorías SC01-SC15**. La revisión semántica de la tabla anterior es documental; estos recuentos no prueban contenido jugable.

Fuentes sin commit: manifiesto local `build/f00-04-source-manifest.json`, SHA-256 `f7db03f81500c465ad01c21d708d7f18d28e3b7adc7cf6820909953d56b9b9dd`. Identifica nueve archivos Markdown de alcance y referencias; este informe se conserva aparte para evitar autorreferencia del hash. No incluye originales ni modifica artefactos de compilación.

## Estado y siguiente tarea

F00.04/Q03 quedan resueltas como línea base de contenido y el backlog se marca completado para esa definición. G00 permanece abierta por F00.05-F00.07; las pruebas de consola, formatos y campaña siguen en sus fases correspondientes.

Siguiente ticket: **F00.05 — Definir perfil y política de datos**. Revisar conjuntamente el contrato `GameProfile`, inventario de fuentes, excepción de ISO local ignorada y reglas para extracciones/informes privados; completar las evidencias del avance parcial ya implementado.
